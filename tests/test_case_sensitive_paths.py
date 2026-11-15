"""Windows does not care about a path's case; Linux does, and CI runs on Linux.

Three defects in this fork were the same bug: a name spelled one way where the file is written and another where it is
read, invisible on Windows and fatal on the first Linux run.

  - launcher/App/Assets/timelink.png was tracked lowercase while the csproj, every .axaml and IconChecks.cs said
    timeLink.png: the launcher would not compile on Linux (MSB4018, file not found).
  - launcher/tests/launcher_core/ScreenChecks.cs wrote usr/bin/timeLinkLauncher while package.sh ships
    usr/bin/TimeLinkLauncher and Toolchains.LauncherProgram names that: the check that refuses a launcher unpacked in
    place of the builder stopped refusing, and aborted the 990 core checks.
  - launcher/tests/fixtures/release/SHA256SUMS was checked out with CRLF while its signature covered LF (that one is
    tests/test_signed_fixture_bytes.py).

This check compares the case of every path a source file names against the case of the file that exists. It reads the
tree, so it catches the class rather than the three instances.
"""
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

# (the files whose path references matter: they name files that ship, or that a check writes and reads back)
SOURCES = [
    "launcher/App/TimeLinkLauncher.csproj",
    "launcher/App/MainWindow.axaml",
    "launcher/App/Views/HomeView.axaml",
    "launcher/Core/Toolchains.cs",
    "launcher/scripts/package.sh",
    "launcher/scripts/make_icon.py",
    "launcher/tests/launcher_core/ScreenChecks.cs",
    "launcher/tests/launcher_core/IconChecks.cs",
    "launcher/tests/launcher_core/Program.cs",
]

# (a path inside a Linux tree the launcher builds or reads: usr/bin/<program>, usr/lib/timeLink/<tool>)
LINUX_TREE = re.compile(r'"usr"\s*,\s*"bin"\s*,\s*"([A-Za-z0-9_.-]+)"')
# (a repo-relative asset the launcher compiles in)
ASSET = re.compile(r'Assets/([A-Za-z0-9_.-]+\.(?:png|ico|ttf))')


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True).stdout
    return set(out.split())


class CaseSensitivePaths(unittest.TestCase):
    def setUp(self):
        self.files = tracked()
        self.by_lower = {}
        for f in self.files:
            self.by_lower.setdefault(f.lower(), []).append(f)

    def test_the_launcher_program_is_spelled_one_way(self):
        """(package.sh writes it, Toolchains names it, and the checks write it: all three must agree)"""
        names = set()
        for rel in ("launcher/scripts/package.sh", "launcher/Core/Toolchains.cs"):
            text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            names.update(re.findall(r"usr/bin/([A-Za-z0-9_.-]+)", text))
        self.assertTrue(names, "no usr/bin program is named by package.sh or Toolchains.cs")
        self.assertEqual(len(names), 1,
                         "the launcher program is spelled more than one way: %s. Linux is case-sensitive, so the "
                         "spelling that is not shipped is a file that does not exist" % sorted(names))
        shipped = names.pop()
        for rel in SOURCES:
            path = ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for spelled in LINUX_TREE.findall(text):
                self.assertEqual(spelled, shipped,
                                 "%s writes usr/bin/%s, but the AppImage ships usr/bin/%s: on Linux the check reads a "
                                 "file that is not there" % (rel, spelled, shipped))

    def test_every_asset_a_source_names_exists_with_that_case(self):
        assets = {f.rsplit("/", 1)[-1] for f in self.files if "/Assets/" in f}
        self.assertTrue(assets, "no launcher assets are tracked")
        for rel in SOURCES:
            path = ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for name in ASSET.findall(text):
                self.assertIn(name, assets,
                              "%s names Assets/%s, but the tracked file is %s: Windows finds it, Linux does not"
                              % (rel, name, sorted(a for a in assets if a.lower() == name.lower()) or "absent"))

    def test_the_self_check_line_is_spelled_one_way(self):
        """(SelfUpdate.CheckLine prints it and build-launcher.yml greps for it: a case difference fails the release)"""
        code = (ROOT / "launcher/Core/SelfUpdate.cs").read_text(encoding="utf-8", errors="replace")
        m = re.search(r'CheckLine\(string tag\)\s*=>\s*"([^"]+)"', code)
        self.assertIsNotNone(m, "SelfUpdate.CheckLine no longer returns a literal")
        printed = m.group(1)
        for rel in ("build-launcher.yml", "release.yml"):
            path = ROOT / ".github" / "workflows" / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for grepped in re.findall(r'grep -qxF "([^"$]+)\$', text):
                self.assertEqual(grepped, printed,
                                 ".github/workflows/%s greps for %r but the launcher prints %r: the release job fails "
                                 "with 'does not answer --self-check'" % (rel, grepped, printed))

    def test_no_workflow_asks_for_a_token_that_does_not_exist(self):
        """(secrets.GITHUB_TOKEN is not a secret GitHub defines: it resolves to empty, and a private repository then
        answers 404 to an unauthenticated API call, which reads as "no releases" rather than "not allowed")"""
        for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertFalse("secrets.GITHUB_TOKEN" in text,
                             "%s uses secrets.GITHUB_TOKEN, which GitHub does not define: use github.token"
                             % path.name)

    def test_no_tracked_path_differs_from_itself_only_by_case(self):
        """(two files whose names differ only by case cannot both exist on Windows, and confuse a Linux checkout)"""
        clashes = {k: v for k, v in self.by_lower.items() if len(v) > 1}
        self.assertEqual(clashes, {}, "paths that differ only by case: %s" % clashes)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    unittest.main()