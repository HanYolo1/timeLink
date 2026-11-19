"""The write marks' collection keeps its lists between submissions (host/rx_backend.c collect_in, host_collect,
host_free_pages).

At every submission the Vulkan back end collects the pages the game wrote: host_collect asked host/nvdrv.c for the
GPU-visible ranges (its lock and a copy of the merged list) and collect_in allocated a 16 KB list for the pages found,
which the renderer then freed. Now the ranges are asked for again only when the mappings' generation moves, and the
pages' list is collect_in's own, kept per thread and given back with host_free_pages, which frees only other lists.

The four functions are cut out of the source and compiled over a small mark array, a stub ranges source that counts its
calls, and counting allocators. Checked: the pages found are right before and after the list grows past its first 4096;
one allocation for many collections, and host_free_pages frees none of them but frees a list of another's; the ranges
asked for once while the generation stays, again when it moves, and the new ranges' pages found.

python -I -B tests/test_collect_reuse.py [--cc gcc]
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = r"""
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A64_DIRTY_PAGES (1ull << 16)
static uint8_t a64_dirty[A64_DIRTY_PAGES];
static uint64_t hos_guest_size(void) { return A64_DIRTY_PAGES << 12; }

static int mallocs, reallocs, frees;
static void *count_malloc(size_t n) { mallocs++; return malloc(n); }
static void *count_realloc(void *p, size_t n) { reallocs++; return realloc(p, n); }
static void count_free(void *p) { if (p) frees++; free(p); }

/* (the GPU-visible ranges: one range, moved by the test; the calls counted) */
static uint32_t generation = 1;
static uint64_t range_lo, range_hi;
static int range_calls;
static uint32_t hos_gpu_maps_generation(void) { return generation; }
static int hos_gpu_guest_ranges(uint64_t (*out)[2], int max) {
    range_calls++;
    if (max < 1) return 0;
    out[0][0] = range_lo, out[0][1] = range_hi;
    return 1;
}

#define malloc count_malloc
#define realloc count_realloc
#define free count_free
@MARKS_CLEAR@
@FOUND@
@COLLECT_IN@
@HOST_COLLECT@
@HOST_FREE@
#undef malloc
#undef realloc
#undef free

static void mark(uint64_t from, uint64_t count, uint64_t every) {
    for (uint64_t i = 0; i < count; i++) a64_dirty[from + i * every] = 1;
}

static int check(const char *what, int64_t got, int64_t want, const uint32_t *pages, uint64_t first, uint64_t every) {
    if (got != want) {
        printf("%s: %lld pages found, %lld expected\n", what, (long long)got, (long long)want);
        return 1;
    }
    for (int64_t i = 0; i < got; i++)
        if (pages[i] != first + (uint64_t)i * every) {
            printf("%s: page %lld is %u, %llu expected\n", what, (long long)i, pages[i],
                   (unsigned long long)(first + (uint64_t)i * every));
            return 1;
        }
    return 0;
}

int main(void) {
    uint32_t *pages = 0;
    range_lo = 0, range_hi = 0x8000ull << 12;   /* (pages 0 to 0x8000) */

    /* (a few pages, then many collections: one list allocated, none freed) */
    mark(100, 10, 3);
    if (check("first", host_collect(&pages), 10, pages, 100, 3)) return 1;
    uint32_t *const first_list = pages;
    host_free_pages(pages);
    for (int i = 0; i < 1000; i++) {
        mark(200 + (uint64_t)i % 50, 1, 1);
        if (check("again", host_collect(&pages), 1, pages, 200 + (uint64_t)i % 50, 1)) return 1;
        host_free_pages(pages);
    }
    if (pages != first_list || mallocs != 2 || reallocs || frees) {
        printf("1001 collections: %d allocations (2 expected: the ranges' and the pages'), %d grown, %d freed, %s list\n",
               mallocs, reallocs, frees, pages == first_list ? "the same" : "another");
        return 1;
    }

    /* (more pages than the first list holds: grown once, every page found, and kept for the next collection) */
    mark(10, 6000, 4);   /* (pages 10, 14, ... 23,006) */
    if (check("grown", host_collect(&pages), 6000, pages, 10, 4)) return 1;
    host_free_pages(pages);
    if (reallocs != 1 || frees) {
        printf("6000 pages: grown %d times (1 expected), %d freed\n", reallocs, frees);
        return 1;
    }
    mark(7, 3, 1);
    if (check("after growing", host_collect(&pages), 3, pages, 7, 1)) return 1;
    host_free_pages(pages);

    /* (a list that is not collect_in's: freed) */
    uint32_t *other = malloc(64);
    host_free_pages(other);
    if (frees != 1) {
        printf("another list given back: %d freed, 1 expected\n", frees);
        return 1;
    }

    /* (the ranges: asked for once while the generation stays; again when it moves, and only the new range is read) */
    if (range_calls != 1) {
        printf("%d asks for the ranges at one generation, 1 expected\n", range_calls);
        return 1;
    }
    generation++;
    range_lo = 0x9000ull << 12, range_hi = 0xA000ull << 12;
    mark(0x9010, 5, 2);
    mark(50, 1, 1);   /* (outside the new range: not found, and left marked) */
    if (check("new range", host_collect(&pages), 5, pages, 0x9010, 2)) return 1;
    host_free_pages(pages);
    if (range_calls != 2 || !a64_dirty[50]) {
        printf("after the generation moved: %d asks for the ranges (2 expected), page 50 %s\n", range_calls,
               a64_dirty[50] ? "kept" : "taken");
        return 1;
    }
    if (check("same generation", host_collect(&pages), 0, pages, 0, 1) || range_calls != 2) {
        printf("%d asks for the ranges, 2 expected\n", range_calls);
        return 1;
    }
    return 0;
}
"""


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cc", default="gcc")
    a = p.parse_args()
    src = (ROOT / "host" / "rx_backend.c").read_text(encoding="utf-8")
    found = src[src.index("static _Thread_local uint32_t *found_pages;"):src.index("static int64_t collect_in(")]
    fixture = (FIXTURE.replace("@MARKS_CLEAR@", block(src, "static inline int marks_clear_256("))
               .replace("@FOUND@", found)
               .replace("@COLLECT_IN@", block(src, "static int64_t collect_in("))
               .replace("@HOST_COLLECT@", block(src, "static int64_t host_collect(uint32_t **pages) {\n    /* (timelink)"))
               .replace("@HOST_FREE@", block(src, "static void host_free_pages(uint32_t *pages) { if")))
    with tempfile.TemporaryDirectory(prefix="collect-reuse-") as tmp:
        c = Path(tmp) / "fixture.c"
        exe = Path(tmp) / "fixture"
        c.write_text(fixture, encoding="utf-8")
        subprocess.run([a.cc, "-std=c11", "-O1", "-Wall", "-Wextra", "-Werror", str(c), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print("ok: the collection's lists kept between submissions, the ranges asked for only when they change")


if __name__ == "__main__":
    main()
