"""scripts/check_packages.py, with no network: a package folder made here, checked against lock files made here, and the
repository's own publish-packages.lock read as the release reads it.

    python -I tests/test_check_packages.py
"""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_packages", ROOT / "scripts" / "check_packages.py")
check_packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_packages)


def b64sha512(data):
    return base64.b64encode(hashlib.sha512(data).digest()).decode()


class CheckPackages(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.folder = self.tmp / "packages"
        self.lock_json = self.tmp / "packages.lock.json"
        self.publish_lock = self.tmp / "publish-packages.lock"
        self.lock_json.write_text(json.dumps({"version": 2, "dependencies": {
            "net10.0": {
                "Avalonia": {"type": "Direct", "resolved": "12.1.6", "contentHash": b64sha512(b"avalonia")},
                "TimeLinkLauncher.Core": {"type": "Project"},
            },
            "net10.0/win-x64": {
                "SkiaSharp.NativeAssets.Win32": {"type": "Transitive", "resolved": "3.0.0",
                                                 "contentHash": b64sha512(b"skia")},
            },
        }}))
        self.publish_lock.write_text("# comment\n\nMicrosoft.NETCore.App.Runtime.win-x64 10.0.0 "
                                     + b64sha512(b"runtime") + "  # the runtime\n")

    def add(self, name, ver, data):
        """A package as NuGet leaves it: the .nupkg and the .nupkg.metadata with its content hash."""
        d = self.folder / name / ver
        d.mkdir(parents=True)
        (d / f"{name}.{ver}.nupkg").write_bytes(data)
        (d / ".nupkg.metadata").write_text(json.dumps({"version": 2, "contentHash": b64sha512(data), "source": "x"}))

    def run_check(self):
        return check_packages.check(self.folder, self.publish_lock, [self.lock_json])

    def test_everything_pinned_passes(self):
        self.add("avalonia", "12.1.6", b"avalonia")
        self.add("skiasharp.nativeassets.win32", "3.0.0", b"skia")
        self.add("microsoft.netcore.app.runtime.win-x64", "10.0.0", b"runtime")
        self.assertEqual(self.run_check(), ([], []))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check_packages.main([str(self.folder), str(self.publish_lock), str(self.lock_json)]), 0)

    def test_an_unpinned_package_fails_and_prints_its_line(self):
        self.add("microsoft.netcore.app.host.win-x64", "10.0.0", b"host")
        problems, to_add = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("pins it", problems[0])
        self.assertEqual(to_add, ["microsoft.netcore.app.host.win-x64 10.0.0 " + b64sha512(b"host")])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(check_packages.main([str(self.folder), str(self.publish_lock), str(self.lock_json)]), 1)

    def test_another_hash_fails(self):
        self.add("microsoft.netcore.app.runtime.win-x64", "10.0.0", b"tampered")
        self.add("avalonia", "12.1.6", b"not avalonia")
        problems, to_add = self.run_check()
        self.assertEqual(len(problems), 2)
        self.assertTrue(all("but the repository pins" in p for p in problems))
        self.assertEqual(to_add, [])

    def test_another_version_is_not_pinned(self):
        self.add("avalonia", "12.1.7", b"avalonia")
        problems, to_add = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertEqual(len(to_add), 1)

    def test_a_package_without_its_metadata_fails(self):
        (self.folder / "avalonia" / "12.1.6").mkdir(parents=True)
        problems, _ = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("no content hash", problems[0])

    def test_the_hash_is_nugets_not_the_files(self):
        # (a signed package's content hash leaves out its signature: the recorded value is what counts, not the file's)
        self.add("avalonia", "12.1.6", b"avalonia")
        (self.folder / "avalonia" / "12.1.6" / "avalonia.12.1.6.nupkg").write_bytes(b"avalonia, signed again")
        self.assertEqual(self.run_check(), ([], []))

    def test_a_malformed_line_is_an_error(self):
        self.publish_lock.write_text("only two\n")
        self.folder.mkdir()
        with self.assertRaises(ValueError):
            self.run_check()


class TheRepositorysFiles(unittest.TestCase):
    def test_publish_packages_lock_reads(self):
        pins = check_packages.read_publish_lock(ROOT / "publish-packages.lock")
        for (name, ver), digest in pins.items():
            self.assertEqual(len(base64.b64decode(digest, validate=True)), 64, f"{name} {ver}")

    def test_the_lock_files_read(self):
        # (the window's pins Avalonia and what it brings; the core has no packages of its own)
        self.assertIn(("avalonia", "12.1.6"), check_packages.read_lock_json(ROOT / "App/packages.lock.json"))
        self.assertEqual(check_packages.read_lock_json(ROOT / "Core/packages.lock.json"), {})

    def test_the_sdk_is_pinned_exactly(self):
        sdk = json.loads((ROOT / "scripts" / "dotnet-sdk.json").read_text())["sdk"]
        self.assertRegex(sdk["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(sdk["rollForward"], "disable")

    def test_package_sh_runs_the_check(self):
        text = (ROOT / "scripts" / "package.sh").read_text()
        self.assertIn('export NUGET_PACKAGES="$WORK/packages"', text)
        self.assertIn("scripts/check_packages.py", text)
        # (the check comes after the last publish and before the AppImage is packed)
        self.assertLess(text.index('publish linux-x64 "$WORK/linux-x64"'), text.index('check_packages.py" "$NUGET_PACKAGES"'))
        self.assertLess(text.index('check_packages.py" "$NUGET_PACKAGES"'), text.index('"$tool" --no-appstream'))


if __name__ == "__main__":
    unittest.main()
