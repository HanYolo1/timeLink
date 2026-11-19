"""The game's name on disk is spelled timeLink, with a capital L, everywhere a path or a program is named.

Linux file names are case-sensitive, so `timelink` and `timeLink` are two different folders. The game writes its saves to
$XDG_DATA_HOME/timeLink (host/hos_main.c saves_dir) and is built as bin/timeLink (nx2/build.py EXE). After the rename
from Longshot, scripts/timeLink_ctl.py installed saves into .../timelink, which the game never read, gpu/vk/vk_dlss.cpp
looked for DLSS in .../timelink/ngx while its own message named .../timeLink/ngx, and dev_packs.py, prof.py and
host/posix/prof.c looked for a program called timelink. Windows hides all of this because its paths ignore case.

This fails on a quoted "timelink" or 'timelink' in code. The few that are deliberately lower case are named below with
the reason; anything else is the bug above coming back.

  python -I -B tests/test_name_case.py
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A quoted string that is exactly timelink (a folder, a program, a key): not a comment's "(timelink)" marker, not a URL.
LITERAL = re.compile(r"""["']timelink["']""")
CODE = (".py", ".c", ".cpp", ".h", ".cs", ".sh", ".ps1", ".ts")

# (file, the text on the line that makes it deliberate)
ALLOWED = [
    ("host/discord_rpc.c", "TIMELINK_DISCORD_IMAGE_DEFAULT"),   # the art asset's key on Discord's side, not a path
    ("scripts/oot_saves.py", "Program(\"timelink\""),          # its id; processes are matched lower case by design
    ("scripts/oot_saves.py", "[\"timelink\"], [])"),           # the process names, lower case by design (see its comment)
    ("launcher/Core/Saves.cs", "new[] { \"timelink\" }, Array.Empty"),   # process names, compared lower case (RunningFrom)
    ("scripts/release.py", "PRODUCT_ALIASES = "),             # an earlier spelling of the product, still taken by --product
    ("scripts/release.py", "earlier names, still taken"),      # the comment naming it
    ("launcher/scripts/release.py", "PRODUCT_ALIASES = "),    # the same file's copy
    ("launcher/scripts/release.py", "earlier names, still taken"),
    ("tests/test_release.py", ""),                             # the aliases, in the release script's tests
    ("tests/test_name_case.py", ""),                           # this file
]


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False)
    if out.returncode == 0 and out.stdout.strip():
        return [ROOT / p for p in out.stdout.splitlines()]
    return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


def allowed(rel, line):
    return any(rel == f and text in line for f, text in ALLOWED)


class NameCase(unittest.TestCase):
    def test_no_lower_case_name_on_disk(self):
        found = []
        for path in tracked():
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith("third_party/") or path.suffix not in CODE and path.name != "AppRun":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if LITERAL.search(line) and not allowed(rel, line):
                    found.append("%s:%d: %s" % (rel, n, line.strip()))
        self.assertEqual(found, [], "spell it timeLink (Linux paths are case-sensitive), or add it to ALLOWED with the "
                                    "reason:\n  " + "\n  ".join(found))

    def test_the_spellings_it_guards_agree(self):
        build = (ROOT / "nx2" / "build.py").read_text(encoding="utf-8")
        self.assertRegex(build, r'(?m)^EXE = "timeLink" if LINUX')
        saves = (ROOT / "host" / "hos_main.c").read_text(encoding="utf-8")
        self.assertIn('"/timeLink"', saves)


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2, exit=False).result.wasSuccessful() is False)
