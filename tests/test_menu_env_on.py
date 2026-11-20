"""A Debug row read before the menu loads (gpu/vk/vk_draw.cpp menu_env_on): Descriptor reuse on by default from options_version 4.

The real menu_env_on and desc_reuse_level from gpu/vk/vk_draw.cpp are compiled over a stub game path (the fixture's
folder); each case writes a timeLink_options.ini (or none) and checks the level the game takes for descriptor reuse
(2 the row's On, on by default since options_version 4: an older file wrote its 0 as the off default it then was; 1 its
Off; 0 never) and sampler_cache (off by default, no version rule):

- no file: the default; a file without the line: the default;
- options_version 3 with descriptor_reuse=0: on (the old default, moved); 4 with 0: off (chosen); 4 with 1: on;
- RX_VK_DESC_REUSE over all of it, with the row's values (0/off its Off, 1 its On) and never;
- the rows applying in play (menu_debug_rows): the menu's values over the file's, unless RX_VK_DESC_REUSE holds the level;
- the first reads from 8 threads at once, the options file slowed down: each switch reads the file once and says it is
  ready once (before, every thread that came first at the same time read the file and logged).

python -I -B tests/test_menu_env_on.py [--cxx clang++]
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

RUN_ALL_ARGS = ["--cxx", "g++"]

ROOT = Path(__file__).resolve().parents[1]


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


FIXTURE = r"""
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <thread>
#include <vector>
#include "timeLink_env.h"
using DWORD = unsigned long;
constexpr int MAX_PATH = 260;
static std::atomic<int> file_reads{0}, log_lines{0};
static DWORD game_module_path(char *path, DWORD size) {   // (the options file's read: counted, and slowed for the threads' case)
    file_reads++;
    if (getenv("FIXTURE_SLOW_FILE")) std::this_thread::sleep_for(std::chrono::milliseconds(30));
    return snprintf(path, size, "./timeLink.exe");
}
static void logf(const char*, ...) { log_lines++; }
BODY
LEVEL
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "threads")) {   // (8 threads ask first at once: one read and one line a switch)
        std::atomic<bool> go{false};
        std::vector<std::thread> threads;
        for (int i = 0; i < 8; i++)
            threads.emplace_back([&go] {
                while (!go.load()) std::this_thread::yield();
                (void)desc_reuse_level();
                (void)sampler_cache_on();
            });
        go = true;
        for (auto& t : threads) t.join();
        if (file_reads != 2 || log_lines != 1) {
            fprintf(stderr, "FAIL: 8 threads at once: the options file read %d times (2 expected), %d lines logged (1)\n",
                    file_reads.load(), log_lines.load());
            return 1;
        }
        return 0;
    }
    if (argc != 3) return 2;
    const int reuse = desc_reuse_level();
    const bool sampler = sampler_cache_on();
    if (reuse != atoi(argv[1]) || sampler != (atoi(argv[2]) != 0)) {
        fprintf(stderr, "FAIL: descriptor reuse level %d (want %s), sampler_cache %d (want %s)\n", reuse, argv[1], sampler, argv[2]);
        return 1;
    }
    // (the menu loaded, then each row changed in play: RX_VK_DESC_REUSE holds the level, the rows' values apply otherwise)
    const bool held = getenv("RX_VK_DESC_REUSE") != nullptr;
    for (const int on : {0, 1, 0}) {
        menu_debug_rows(on, !on);
        const int want = held ? reuse : on ? 2 : 1;
        if (desc_reuse_level() != want || sampler_cache_on() != !on) {
            fprintf(stderr, "FAIL: in play, rows %d/%d: level %d (want %d), sampler_cache %d\n", on, !on, desc_reuse_level(), want,
                    sampler_cache_on());
            return 1;
        }
    }
    return 0;
}
"""

# (timeLink_options.ini's text or None for no file, RX_VK_DESC_REUSE or None, descriptor reuse level, sampler cache)
CASES = (
    (None, None, 2, 0),
    ("output_res=1\noptions_version=4\n", None, 2, 0),
    ("descriptor_reuse=0\nsampler_cache=0\noptions_version=3\n", None, 2, 0),
    ("descriptor_reuse=0\nsampler_cache=1\n", None, 2, 1),
    ("descriptor_reuse=0\nsampler_cache=1\noptions_version=4\n", None, 1, 1),
    ("options_version=4\ndescriptor_reuse=1\n", None, 2, 0),
    ("descriptor_reuse=0\noptions_version=4\n", "1", 2, 0),
    ("descriptor_reuse=1\noptions_version=4\n", "0", 1, 0),
    ("descriptor_reuse=1\noptions_version=4\n", "off", 1, 0),
    (None, "0", 1, 0),
    (None, "never", 0, 0),
    ("descriptor_reuse=1\noptions_version=4\n", "never", 0, 0),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()
    draw = (ROOT / "gpu/vk/vk_draw.cpp").read_text(encoding="utf-8")
    body = block(draw, "bool menu_env_on(const char* env_name, const char* ini_key_name, bool def = false, int since = 0) {")
    # (the rows' atomics and menu_debug_rows, outside the file's anonymous namespace, then the level and the sampler cache's switch)
    start = draw.index("std::atomic<int> desc_reuse_row{-1}")
    level = draw[start:draw.index(block(draw, "int desc_reuse_level() {"))] + block(draw, "int desc_reuse_level() {")
    level = level.replace("} // namespace\n", "").replace("namespace {\n", "") + "\n" + block(draw, "bool sampler_cache_on() {")
    with tempfile.TemporaryDirectory(prefix="menu-env-on-") as tmp:
        work = Path(tmp)
        source, exe = work / "fixture.cpp", work / "fixture.exe"
        source.write_text(FIXTURE.replace("BODY", body).replace("LEVEL", level), encoding="utf-8")
        subprocess.run([args.cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-D_CRT_SECURE_NO_WARNINGS", "-pthread",
                        "-I", str(ROOT / "gpu/vk/compat"), str(source), "-o", str(exe)], check=True)
        for text, env_value, reuse, sampler in CASES:
            ini = work / "timeLink_options.ini"
            if ini.exists():
                ini.unlink()
            if text is not None:
                ini.write_text(text, encoding="ascii")
            env = os.environ.copy()
            env.pop("RX_VK_DESC_REUSE", None)
            env.pop("RX_VK_SAMPLER_CACHE", None)
            if env_value is not None:
                env["RX_VK_DESC_REUSE"] = env_value
            subprocess.run([str(exe), str(reuse), str(sampler)], cwd=work, env=env, check=True)
        (work / "timeLink_options.ini").unlink(missing_ok=True)
        env = os.environ.copy()
        env.pop("RX_VK_DESC_REUSE", None)
        env.pop("RX_VK_SAMPLER_CACHE", None)
        env["FIXTURE_SLOW_FILE"] = "1"
        subprocess.run([str(exe), "threads"], cwd=work, env=env, check=True)
    print("PASS: Descriptor reuse on by default and for options files before version 4; a version 4 choice kept; "
          "RX_VK_DESC_REUSE with the row's values, and never; Sampler cache unchanged; both rows in play; read once from 8 threads")


if __name__ == "__main__":
    main()
