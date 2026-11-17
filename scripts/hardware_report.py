"""Reading a bug report's hardware fields: the GPU's vendor and class, and the OS.

    python -I scripts/hardware_report.py <report.txt> [...]

The fields are the issue form's (.github/ISSUE_TEMPLATE/1-game-problem.yml): "Graphics card and driver version" and
"CPU, RAM and operating system". tests/test_bug_report.py checks that what the game writes is read back correctly.

This used to count the answers across the team's issues on git.magicbean.dev through the Forgejo API. That repository is
not this fork's, and the fork's issues are on GitHub, so the counting is gone; the reading is what the bug report's own
check needs. Standard library only.
"""
import argparse
import re
import sys


def section(body: str, name: str) -> str:
    m = re.search(r"### " + re.escape(name) + r"[^\n]*\n+(.*?)(\n### |\Z)", body or "", re.S)
    return m.group(1).strip() if m else ""


def classify(gpu: str):
    g = gpu.lower()
    if re.search(r"nvidia|rtx|gtx|geforce", g):
        cls = ("RTX 50" if re.search(r"rtx ?50\d0", g) else "RTX 40" if re.search(r"rtx ?40\d0", g) else
               "RTX 30" if re.search(r"rtx ?30\d0", g) else "RTX 20" if re.search(r"rtx ?20\d0", g) else
               "GTX 10/16 (no mesh shaders)" if re.search(r"gtx ?1[06]\d0", g) else "NVIDIA other")
        return "NVIDIA", cls
    if re.search(r"amd|radeon|\brx ?\d|rdna|780m|680m|890m|860m|8060s|z1|steam deck|legion|ally", g):
        cls = ("AMD APU / handheld" if re.search(r"780m|680m|890m|860m|8060s|z1|steam deck|legion|ally|apu|vega", g) else
               "RX 9000" if re.search(r"9070|9060", g) else "RX 7000" if re.search(r"7900|7800|7700|7600", g) else
               "RX 6000" if re.search(r"6[5-9]\d0|6600|6650|6700|6800|6900", g) else
               "RX 5000 or older (no mesh shaders)" if re.search(r"5[5-7]00|rx ?5[78]0|rx ?4[78]0", g) else "AMD other")
        return "AMD", cls
    if re.search(r"intel|arc\b|iris|uhd", g):
        return "Intel", "Intel"
    return "unknown", "unknown"


def os_of(text: str) -> str:
    t = text.lower()
    if re.search(r"linux|ubuntu|arch|fedora|steamos|bazzite|cachy|nixos|mint|pop!?_os|steam deck", t):
        return "Linux / SteamOS"
    if re.search(r"windows|win ?1[01]", t):
        return "Windows"
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report", nargs="+", help="a report.txt from the game's Bug report")
    a = ap.parse_args()
    for path in a.report:
        with open(path, encoding="utf-8", errors="replace") as f:
            body = f.read()
        gpu = section(body, "Graphics card")
        system = section(body, "CPU, RAM and operating system")
        vendor, cls = classify(gpu)
        print("%s\n  GPU: %s\n  vendor: %s, class: %s\n  OS: %s"
              % (path, gpu or "(none)", vendor, cls, os_of(system + " " + gpu)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
