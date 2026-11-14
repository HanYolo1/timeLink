"""The caches and pools that grew without end now have a bound, and the ones that leaked give their objects back.

Each check reads the source it is about: the maps that were cleared whole at a cap (throwing the recent history away with
the old), the ones that were never pruned at all, the render target pool that took 16 a present however many died, the
tree-shadow mask's history images that were overwritten at a new size, and the guest thread and fiber records that were
never given back.

    python -I -B tests/test_leak_bounds.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def require(text, needle, why):
    if needle not in text:
        raise SystemExit("FAIL: " + why + ": missing " + repr(needle))


def main():
    tex = (ROOT / "gpu" / "vk" / "vk_texture.cpp").read_text(encoding="utf-8")
    draw = (ROOT / "gpu" / "vk" / "vk_draw.cpp").read_text(encoding="utf-8")
    replay = (ROOT / "gpu" / "vk" / "vk_replay.cpp").read_text(encoding="utf-8")
    thread = (ROOT / "host" / "hos_thread.c").read_text(encoding="utf-8")
    mem = (ROOT / "host" / "hos_mem.c").read_text(encoding="utf-8")

    # (the eviction history: the oldest go at the cap, not the whole map)
    for name in ("evicted_at_trim_locked", "evicted_from_memory_trim_locked"):
        require(tex, "void %s(size_t cap)" % name, "the eviction history's bound is gone")
    require(tex, "evicted_at_trim_locked(20000);", "evicted_at is not bounded")
    require(tex, "evicted_from_memory_trim_locked(50000);", "evicted_from_memory is not bounded")
    if "evicted_at.clear()" in tex or "evicted_from_memory.clear()" in tex:
        raise SystemExit("FAIL: an eviction history is still cleared whole at its cap")

    # (the per-texture diagnostic maps: bounded)
    require(tex, "if (told.size() > 4096) told.clear();", "the watch's per-texture map is unbounded")
    require(tex, "if (big.size() > 4096) big.clear();", "the big-upload map is unbounded")

    # (the render target pool drains when it is over its bound, whatever the age sweep's 16 a present)
    trim = block(tex, "size_t pool_trim()")
    require(trim, "pool_bytes <= cap && (n >= most || frame_no - v[i].since <= 120)",
            "the pool does not drain when it is over its bound")

    # (the tree-shadow mask's history: the pair a new size replaced is given back, and the view cache is bounded and keyed
    # by the texture's id, not its recycled VkImage)
    stab = block(draw, "void mask_stabilize(")
    require(stab, "old_hist.push_back({hist[i], hist_mem[i], hist_view[i], texture_frame_no()});",
            "the mask's history images are overwritten at a new size")
    require(stab, "destroy_image(old_hist[i].image, old_hist[i].mem);", "the mask's old history is never destroyed")
    require(stab, "v.id == tex->id && v.level == level && v.layer == layer", "the mask's view cache is keyed by VkImage")
    require(stab, "if (views.size() >= 64)", "the mask's view cache is unbounded")
    require(stab, "vkDestroyImageView(dev.device, views[oldest].view, nullptr);", "the mask's evicted view is not destroyed")

    # (the fallback hold map: swept, not kept for every list ever held)
    hold = block(draw, "static void fallback_list_hold(uint64_t list, bool held)")
    require(hold, "if (fallback_held.size() >= 4096)", "the fallback hold map is unbounded")

    # (the replay's event values: bounded, oldest first)
    require(replay, "void ev_set(uint64_t gpu, uint32_t value)", "the replay's event values have no bound")
    require(replay, "while (ev_order.size() > 4096)", "the replay's event values are unbounded")
    if "ev_values[j.ev_gpu] = j.ev_value;" in replay or "ev_values[e.gpu] = e.mode" in replay:
        raise SystemExit("FAIL: an event value is set without the bound (ev_set)")

    # (a destroyed thread's guest blocks go back, and its record is retired rather than freed under a lookup)
    destroy = block(thread, "void hos_thread_destroy(HosThread *t)")
    for needle, why in (("hos_sys_free(t->tls_block, 0x1000);", "the TLS block is not given back"),
                        ("hos_sys_free(t->tlr, 0x200);", "the TLR is not given back"),
                        ("t->spare = spare_threads, spare_threads = t;", "the record is not retired for reuse")):
        require(destroy, needle, why)
    if "free(t);" in destroy:
        raise SystemExit("FAIL: a destroyed thread's record is freed (a lookup could read it)")
    require(thread, "if ((t = spare_threads)) spare_threads = t->spare;", "a retired record is not reused")
    require(mem, "void hos_sys_free(uint64_t addr, uint64_t size)", "the system region has no free list")
    require(mem, "for (SysFree **p = &sys_free; *p; p = &(*p)->next)", "hos_sys_alloc does not take a freed block")

    # (a finalized fiber's record goes)
    fin = block(thread, "HLE(_ZN2nn2os13FinalizeFiberEPNS0_9FiberTypeE)")
    require(fin, "free(f);", "a finalized fiber's record is never freed")
    require(fin, "if (*p == f) { *p = f->next; break; }", "a finalized fiber stays in the list")

    # (the log queue drops a line rather than writing it on the game thread)
    queue = block(thread, "static int log_queue(const char *line)")
    require(queue, "InterlockedIncrement(&log_dropped);", "a full log queue still writes on the calling thread")
    if "log_flush();" in queue:
        raise SystemExit("FAIL: a full log queue flushes on the calling thread (the disk stall the queue avoids)")

    print("leak bounds and give-backs ok")


if __name__ == "__main__":
    main()
