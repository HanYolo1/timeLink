"""The GPU-visible ranges survive a failed allocation (host/nvdrv.c hos_gpu_guest_ranges).

hos_gpu_guest_ranges merges the GPU mappings and the native pools into page-aligned ranges for the write-mark scan at
every submission. When their number outgrew its list it grew the list with realloc and used the result unchecked: out
of host memory, the next merge wrote through a null pointer. The function and its sort comparison are cut out of the
source and compiled with a realloc that can be made to fail. Checked: a plain merge (ranges under 16 MB apart are one);
with the list full and realloc failing, the ranges merged before are the answer, nothing is written past them, and the
change stays noted with the mappings' generation moved (a caller that keeps the list by generation asks again); the next
call, with memory again, merges the new mappings.

python -I -B tests/test_guest_ranges_oom.py [--cc gcc]
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

typedef long LONG;
#define LOCK() ((void)0)
#define UNLOCK() ((void)0)
typedef struct { uint64_t va, size, guest; } Map;
static Map maps[128];
static int nmaps;
typedef struct { uint64_t lo, hi; int n; } Tracked;
static Tracked tracked[4];
static int ntracked;
static volatile LONG maps_changed = 1;
static volatile LONG maps_generation = 1;
#define InterlockedIncrement(p) (++*(p))

static int fail_realloc;
static void *test_realloc(void *p, size_t n) { return fail_realloc ? NULL : realloc(p, n); }
#define realloc(p, n) test_realloc(p, n)

@CMP_RANGE@
@GUEST_RANGES@

#undef realloc

static void add(uint64_t guest, uint64_t size) { maps[nmaps++] = (Map){guest, size, guest}; maps_changed = 1; }

int main(void) {
    uint64_t out[128][2];
    /* (two mappings 1 MB apart are one range; one 1 GB away is another) */
    add(0x10000000, 0x1000), add(0x10100000, 0x2000), add(0x50000000, 0x3000);
    int n = hos_gpu_guest_ranges(out, 128);
    if (n != 2 || out[0][0] != 0x10000000 || out[0][1] != 0x10102000 || out[1][0] != 0x50000000 || out[1][1] != 0x50003000) {
        printf("plain merge: %d ranges\n", n);
        return 1;
    }
    /* (more mappings than the list holds (3 + 64), each 1 GB apart, and no memory: the ranges merged before, untouched
       past them) */
    while (nmaps < 100) add(0x100000000ull + (uint64_t)nmaps * 0x40000000ull, 0x1000);
    memset(out, 0xAB, sizeof out);
    const LONG gen_before = maps_generation;
    fail_realloc = 1;
    n = hos_gpu_guest_ranges(out, 128);
    if (n != 2 || out[0][0] != 0x10000000 || out[1][1] != 0x50003000 || out[2][0] != 0xABABABABABABABABull) {
        printf("realloc failed: %d ranges, or other ranges\n", n);
        return 1;
    }
    if (!maps_changed || maps_generation == gen_before) {
        printf("realloc failed: the change was forgotten, or the generation kept: the next call would not merge again\n");
        return 1;
    }
    /* (memory again: every mapping merged) */
    fail_realloc = 0;
    n = hos_gpu_guest_ranges(out, 128);
    if (n != 2 + (nmaps - 3)) {
        printf("after the failure: %d ranges, %d expected\n", n, 2 + (nmaps - 3));
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
    src = (ROOT / "host" / "nvdrv.c").read_text(encoding="utf-8")
    fixture = (FIXTURE.replace("@CMP_RANGE@", block(src, "static int cmp_range("))
               .replace("@GUEST_RANGES@", block(src, "int hos_gpu_guest_ranges(")))
    with tempfile.TemporaryDirectory(prefix="guest-ranges-") as tmp:
        c = Path(tmp) / "fixture.c"
        exe = Path(tmp) / "fixture"
        c.write_text(fixture, encoding="utf-8")
        subprocess.run([a.cc, "-std=c11", "-O1", "-Wall", "-Wextra", "-Werror", str(c), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print("ok: the GPU-visible ranges survive a failed allocation")


if __name__ == "__main__":
    main()
