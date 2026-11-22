"""The textures' pool's blocks made at the start are held by placeholders, and given back near Windows' commit limit.

gpu/vk/texture_reserve.h says why: the blocks were the pool's minBlockCount, which VMA keeps for the whole run, and every VRAM
block is charged to the process's commit on Windows. An RTX 5070 Ti with 32 GB of RAM held 18 blocks (2304 MB) for 161 MB of
textures an hour in, its private commit at 23.7 GB, while the commit rule cut the textures' budget from 6 GB to about 1 GB.

Compiled and run here, no GPU:
- texture_reserve.h itself: the holder, the free space with the placeholders counted as free, and when they go back;
- vk_vma.cpp's own hold_blocks, create_image and texture_held_release, against a stand-in for VMA 3.3.0's block rules (a
  block is made only when nothing has room and NEVER_ALLOCATE is not asked; an emptied block is freed when another is
  empty already, VmaBlockVector::Free): the blocks made at the start take the textures with no block made in play, one
  placeholder at a time; and given back, every empty block goes but one, where the minimum kept them all;
- the wiring in vk_vma.cpp and vk_texture.cpp: the commit rule gives the blocks back before it cuts the budget, and the
  placeholders count as free wherever the blocks VMA kept did.

python -I -B tests/test_texture_reserve.py [--cxx g++]
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

RUN_ALL_ARGS = ["--cxx", "{cxx}"]

ROOT = Path(__file__).resolve().parents[1]


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def need(where, text, needles):
    for n in needles:
        if n not in text:
            raise SystemExit("FAIL: " + where + " no longer has: " + n)


HEADER_TEST = r'''
#include <cstdio>
#include <thread>
#include "texture_reserve.h"
#define CHECK(x) do { if (!(x)) { std::printf("FAIL %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main() {
    const uint64_t B = 128ull << 20;
    texture_reserve::Held<int> h(B);
    CHECK(h.count() == 0 && h.bytes() == 0);
    int got = -1;
    CHECK(!h.take_one(&got) && got == -1);
    for (int i = 0; i < 5; i++) h.add(i);
    CHECK(h.count() == 5 && h.bytes() == 5 * B);
    CHECK(h.take_one(&got) && got == 4 && h.count() == 4);
    auto all = h.take_all();
    CHECK(all.size() == 4 && h.count() == 0 && h.bytes() == 0);
    // (several threads taking at once: each placeholder goes to one of them only)
    for (int i = 0; i < 1000; i++) h.add(i);
    int taken[4] = {};
    std::thread t[4];
    for (int k = 0; k < 4; k++) t[k] = std::thread([&, k] { int a; while (h.take_one(&a)) taken[k]++; });
    for (auto& x : t) x.join();
    CHECK(taken[0] + taken[1] + taken[2] + taken[3] == 1000 && h.count() == 0);
    // (the pool's free space: the placeholders count as free, as the blocks VMA kept empty did)
    CHECK(texture_reserve::free_with_held(18 * B, 161ull << 20, 0) == 18 * B - (161ull << 20));
    CHECK(texture_reserve::free_with_held(18 * B, 9 * B + (161ull << 20), 9 * B) == 18 * B - (161ull << 20));
    CHECK(texture_reserve::free_with_held(2 * B, 2 * B, 2 * B) == 2 * B);
    CHECK(texture_reserve::free_with_held(B, 3 * B, 0) == 0);   // (never below zero)
    // (given back below the reserve, with the headroom known; RX_VK_COMMIT_RESERVE_MB=0 or Linux: never)
    const uint64_t R = 2560ull << 20;
    CHECK(texture_reserve::give_back(true, 2426ull << 20, R));
    CHECK(!texture_reserve::give_back(true, R, R) && !texture_reserve::give_back(true, 9000ull << 20, R));
    CHECK(!texture_reserve::give_back(false, 0, R) && !texture_reserve::give_back(true, 0, 0));
    std::printf("PASS texture_reserve.h\n");
    return 0;
}
'''

# vk_vma.cpp's own functions over a stand-in for VMA 3.3.0's block vector (vk_mem_alloc.h, VmaBlockVector::Allocate and Free)
POOL_TEST = r'''
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <vector>
#include "texture_reserve.h"
constexpr int VK_SUCCESS = 0, VK_ERROR_OUT_OF_DEVICE_MEMORY = -2;
constexpr int VMA_MEMORY_USAGE_AUTO_PREFER_DEVICE = 1, VMA_MEMORY_USAGE_UNKNOWN = 0, VMA_MEMORY_USAGE_AUTO = 2;
constexpr int VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT = 1;
constexpr int VMA_ALLOCATION_CREATE_WITHIN_BUDGET_BIT = 1, VMA_ALLOCATION_CREATE_DEDICATED_MEMORY_BIT = 2;
constexpr int VMA_ALLOCATION_CREATE_NEVER_ALLOCATE_BIT = 4;
#define VK_NULL_HANDLE nullptr
using VkResult = int;
struct PoolTag {};
using VmaPool = PoolTag*;
struct VmaAllocationCreateInfo { int flags{}, usage{}, requiredFlags{}; VmaPool pool{}; };
struct VkMemoryRequirements { uint64_t size{}, alignment{}; uint32_t memoryTypeBits{}; };
struct VkImageCreateInfo { struct { uint32_t width, height, depth; } extent{}; int format{}; };
struct Alloc { int block; uint64_t size; bool in_pool; };
using VmaAllocation = Alloc*;
struct ImageTag {};
using VkImage = ImageTag*;
struct { bool memory_budget = true; } dev;
int vma;
const uint64_t kImageBlock = 128ull << 20;
PoolTag the_pool;
VmaPool texture_pool = &the_pool;
VmaPool textures_pool() { return texture_pool; }
VmaPool images_pool() { return nullptr; }
VmaPool target_images_pool() { return nullptr; }
bool env_on(const char*) { return false; }
void logf(const char*, ...) {}
// (the stand-in: the pool's blocks and what they hold; blocks made in play counted)
std::vector<uint64_t> used;   // (per block; -1 marks a freed block)
std::vector<bool> live;
int blocks_made, outside;
ImageTag an_image;
static int live_blocks() { int n = 0; for (bool b : live) n += b; return n; }
static bool empty_block_but(int except) {
    for (size_t i = 0; i < used.size(); i++) if (live[i] && (int)i != except && used[i] == 0) return true;
    return false;
}
static VkResult pool_alloc(uint64_t size, bool may_make, VmaAllocation* out) {
    for (size_t i = 0; i < used.size(); i++)
        if (live[i] && kImageBlock - used[i] >= size) { used[i] += size; *out = new Alloc{(int)i, size, true}; return VK_SUCCESS; }
    if (!may_make || size > kImageBlock) return VK_ERROR_OUT_OF_DEVICE_MEMORY;
    used.push_back(size), live.push_back(true), blocks_made++;
    *out = new Alloc{(int)used.size() - 1, size, true};
    return VK_SUCCESS;
}
VkResult vmaAllocateMemory(int, const VkMemoryRequirements* req, const VmaAllocationCreateInfo* ai, VmaAllocation* a, void*) {
    return ai->pool ? pool_alloc(req->size, true, a) : VK_ERROR_OUT_OF_DEVICE_MEMORY;
}
void vmaFreeMemory(int, VmaAllocation a) {
    if (!a->in_pool) { delete a; return; }
    const bool had_empty = empty_block_but(a->block);
    used[a->block] -= a->size;
    if (used[a->block] == 0 && had_empty) live[a->block] = false;   // (a second empty block is freed: VmaBlockVector::Free)
    delete a;
}
uint64_t image_size(const VkImageCreateInfo& ci) { return (uint64_t)ci.extent.width * ci.extent.height * 4; }
VkResult vmaCreateImage(int, const VkImageCreateInfo* ci, const VmaAllocationCreateInfo* ai, VkImage* image, VmaAllocation* a, void*) {
    if (ai->flags & VMA_ALLOCATION_CREATE_DEDICATED_MEMORY_BIT || !ai->pool) {
        outside++;
        *a = new Alloc{-1, image_size(*ci), false}, *image = &an_image;
        return VK_SUCCESS;
    }
    const VkResult r = pool_alloc(image_size(*ci), !(ai->flags & VMA_ALLOCATION_CREATE_NEVER_ALLOCATE_BIT), a);
    if (r == VK_SUCCESS) *image = &an_image;
    return r;
}
texture_reserve::Held<VmaAllocation> texture_held(kImageBlock);
std::mutex texture_take_mu;
@FUNCTIONS@
#define CHECK(x) do { if (!(x)) { std::printf("FAIL %d: %s\n", __LINE__, #x); return 1; } } while (0)
static void reset() {
    for (VmaAllocation a : texture_held.take_all()) delete a;
    used.clear(), live.clear(), blocks_made = outside = 0;
}
int main() {
    VkImageCreateInfo tex16{};   // (16 MB: 8 to a block)
    tex16.extent = {2048, 2048, 1};
    VkImage image{};
    VmaAllocation a{};
    std::vector<VmaAllocation> textures;
    // (the blocks made at the start take the textures, a held one let go only when no block has room: no block made in play)
    CHECK(hold_blocks(7, 9) == 9 && blocks_made == 9 && texture_held.count() == 9);
    for (int i = 0; i < 72; i++) {
        CHECK(create_image(tex16, image, a, false, false, true));
        textures.push_back(a);
        CHECK(texture_held.count() == size_t(9 - (i / 8 + 1)));
    }
    CHECK(blocks_made == 9 && outside == 0 && live_blocks() == 9);
    CHECK(create_image(tex16, image, a, false, false, true) && blocks_made == 10 && outside == 0);   // (then as before)
    textures.push_back(a);
    for (VmaAllocation t : textures) vmaFreeMemory(vma, t);
    textures.clear();
    CHECK(live_blocks() == 1);   // (all the textures gone: VMA keeps one empty block, as any pool)
    reset();
    // (near the commit limit: the held blocks go back, every empty one but one; the minimum kept all nine)
    CHECK(hold_blocks(7, 9) == 9);
    for (int i = 0; i < 10; i++) {   // (two blocks of textures)
        CHECK(create_image(tex16, image, a, false, false, true));
        textures.push_back(a);
    }
    CHECK(texture_held.count() == 7 && live_blocks() == 9);
    CHECK(texture_held_release() == 7 * kImageBlock && texture_held.count() == 0);
    CHECK(live_blocks() == 3);   // (the two with textures, and VMA's one empty block)
    CHECK(texture_held_release() == 0);   // (once: nothing left to give)
    CHECK(create_image(tex16, image, a, false, false, true) && blocks_made == 9);   // (into the room left, no block made)
    textures.push_back(a);
    for (VmaAllocation t : textures) vmaFreeMemory(vma, t);
    textures.clear();
    reset();
    // (no room for the blocks at the start: as many as VRAM takes, and textures made in play as before)
    CHECK(hold_blocks(7, 0) == 0 && blocks_made == 0);
    CHECK(create_image(tex16, image, a, false, false, true) && blocks_made == 1);
    vmaFreeMemory(vma, a);
    reset();
    // (the other pools never take a held block)
    CHECK(hold_blocks(7, 2) == 2);
    CHECK(create_image(tex16, image, a, false, true, false) && texture_held.count() == 2 && outside == 1);
    vmaFreeMemory(vma, a);
    reset();
    std::printf("PASS vk_vma.cpp's held blocks over VMA's block rules\n");
    return 0;
}
'''


def check_wiring(vma, tex):
    need("vk_vma.cpp: create_image()", block(vma, "bool create_image("),
         ["if (pool == texture_pool && texture_held.count()) {", "std::lock_guard lk(texture_take_mu);",
          "nai.flags |= VMA_ALLOCATION_CREATE_NEVER_ALLOCATE_BIT;",
          "if (texture_held.take_one(&held)) vmaFreeMemory(vma, held);"])
    need("vk_vma.cpp: texture_held_release()", block(vma, "uint64_t texture_held_release() {"),
         ["texture_held.take_all()", "vmaFreeMemory(vma, a);"])
    need("vk_vma.cpp: vram_usage()", block(vma, "bool vram_usage("), ["f += texture_held.bytes();"])
    need("vk_vma.cpp: vma_log_image_blocks()", block(vma, "void vma_log_image_blocks() {"),
         ["pool == texture_pool ? texture_held.count() : 0", "of the blocks held for later"])
    if "minBlockCount" in block(vma, "VmaPool textures_pool() {"):
        raise SystemExit("FAIL: the textures' pool has a minimum again: VMA keeps those blocks for the whole run")
    rule = tex[tex.index("const uint64_t reserve = commit_reserve();"):]
    rule = rule[:rule.index("// (timelink) the 90% rule")]
    need("vk_texture.cpp: the commit rule", rule,
         ["const bool headroom_known = reserve && commit_headroom(&commit_free);",
          "if (texture_reserve::give_back(headroom_known, commit_free, reserve)) {",
          "if (const uint64_t given = texture_held_release())"])
    if rule.index("texture_held_release()") > rule.index("const uint64_t over = reserve - commit_free;"):
        raise SystemExit("FAIL: the commit rule cuts the textures' budget before it gives the held blocks back")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()
    vma = (ROOT / "gpu/vk/vk_vma.cpp").read_text(encoding="utf-8")
    tex = (ROOT / "gpu/vk/vk_texture.cpp").read_text(encoding="utf-8")
    check_wiring(vma, tex)
    functions = "\n".join(block(vma, m) for m in ("static size_t hold_blocks(", "bool create_image(", "uint64_t texture_held_release() {"))
    flags = ["-std=c++20", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-pthread", "-I", str(ROOT / "gpu/vk")]
    with tempfile.TemporaryDirectory(prefix="texture-reserve-") as tmp:
        for name, code in (("header", HEADER_TEST), ("pool", POOL_TEST.replace("@FUNCTIONS@", functions))):
            src, exe = Path(tmp) / (name + ".cpp"), Path(tmp) / name
            src.write_text(code, encoding="utf-8")
            built = subprocess.run([args.cxx, *flags, str(src), "-o", str(exe)], capture_output=True, text=True)
            if built.returncode:
                raise SystemExit("FAIL: the %s check does not build:\n%s" % (name, built.stderr[-3000:]))
            subprocess.run([str(exe)], check=True)
    print("PASS: the textures' held blocks")


if __name__ == "__main__":
    main()
