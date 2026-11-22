// (timelink) The textures' pool's blocks made at the start, held by placeholders so that they can be given back (vk_vma.cpp).
//
// #2438 made 15% of the card's memory (2 to 24 blocks of 128 MB) at the start, so that play makes fewer of them: each is a
// vkAllocateMemory, ~170 ms on AMD's Windows driver (vram_compact::blocks_at_start). They were the pool's minBlockCount, which
// VMA keeps for the whole run and cannot lower after the pool is made. On Windows every VRAM block is charged to the process's
// commit (vk_texture.cpp's commit rule), so near the commit limit the textures' budget came down while those blocks stayed:
// an RTX 5070 Ti with 32 GB of RAM and a 7.7 GB page file, an hour in from the Deku Tree to Castle Town Market, held 18 blocks
// (2304 MB) for 161 MB of textures, its private commit at 23.7 GB of its 10 GB at the start, and the textures' budget cut from
// 6 GB to about 1 GB to keep 2.5 GB of commit free.
//
// Now each block made at the start holds one placeholder allocation of the whole block, and the pool has no minimum. A texture
// first goes where there is room already (VMA_ALLOCATION_CREATE_NEVER_ALLOCATE_BIT); with none, one placeholder is let go and
// its block, empty, takes the texture: no vkAllocateMemory, as before. Below the commit reserve every placeholder is let go at
// once, and VMA gives the empty blocks back but one, as it does any pool's. The placeholders count as free space wherever the
// blocks made at the start did (vram_usage's room in the blocks, textures_pool_usage's free and kept), so nothing else changes.
// Apart from Vulkan so that tests/test_texture_reserve.py runs it without a GPU.
#pragma once
#include <cstdint>
#include <mutex>
#include <vector>

namespace texture_reserve {

/// The placeholders of a pool's held blocks, one block each. A: the allocation handle (VmaAllocation; anything in the test)
template <class A>
class Held {
public:
    explicit Held(uint64_t block) : block_(block) {}
    void add(A a) {
        std::lock_guard<std::mutex> lk(mu_);
        held_.push_back(a);
    }
    /// One placeholder to let go, its block for an image that found no room elsewhere; false when none is held
    bool take_one(A* a) {
        std::lock_guard<std::mutex> lk(mu_);
        if (held_.empty()) return false;
        *a = held_.back();
        held_.pop_back();
        return true;
    }
    /// Every placeholder, to let go: near the commit limit
    std::vector<A> take_all() {
        std::lock_guard<std::mutex> lk(mu_);
        std::vector<A> all;
        all.swap(held_);
        return all;
    }
    size_t count() const {
        std::lock_guard<std::mutex> lk(mu_);
        return held_.size();
    }
    /// The held blocks' bytes: free space for every count that took the blocks made at the start as free
    uint64_t bytes() const { return count() * block_; }

private:
    mutable std::mutex mu_;
    std::vector<A> held_;
    uint64_t block_;
};

/// The pool's free bytes with the placeholders counted as free: its blocks less what the images in them take
inline uint64_t free_with_held(uint64_t block_bytes, uint64_t allocation_bytes, uint64_t held_bytes) {
    const uint64_t images = allocation_bytes - (allocation_bytes < held_bytes ? allocation_bytes : held_bytes);
    return block_bytes - (block_bytes < images ? block_bytes : images);
}

/// Whether the held blocks go back: Windows' commit headroom is known and below the textures' reserve (vk_texture.cpp's commit
/// rule, RX_VK_COMMIT_RESERVE_MB; 0 turns it off, and Linux, which overcommits, never knows its headroom)
inline bool give_back(bool headroom_known, uint64_t commit_free, uint64_t reserve) {
    return reserve && headroom_known && commit_free < reserve;
}

}  // namespace texture_reserve
