"""A signed fixture's bytes are part of the format, so a checkout must not rewrite them.

launcher/tests/fixtures/release/ holds a release's SHA256SUMS and its signature, made with the test key by
scripts/release.py. The signature covers SHA256SUMS' *bytes*, and eol conversion changes them: with the repository's
`* text=auto eol=lf` and a Windows `core.autocrlf=true`, SHA256SUMS was checked out with CRLF while the signature had
been made over LF. It verified on Windows and failed on Linux, so the launcher's 990 core checks passed on every
Windows machine and aborted on the first Linux CI run with

  InvalidDataException: The release's SHA256SUMS is not signed by a key this launcher trusts

.gitattributes now marks the fixture `-text`, so git never converts it. This check fails if that marking is lost, and
independently re-verifies the signature over the bytes git actually stores — which is what a Linux checkout gets, and
what Windows gets once the marking holds.
"""
import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "launcher/tests/fixtures/release"


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=str(ROOT), capture_output=True)


class SignedFixtureBytes(unittest.TestCase):
    def attributes(self):
        """The lines of .gitattributes that name the fixture's files"""
        text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        return [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")
                and FIXTURE in line]

    def test_the_fixture_is_never_line_ending_converted(self):
        rules = self.attributes()
        self.assertTrue(rules, "no .gitattributes line names %s: git would convert SHA256SUMS and break its signature"
                        % FIXTURE)
        for name in ("SHA256SUMS", "SHA256SUMS.sig"):
            marked = [r for r in rules if r.split()[0].endswith(name)]
            self.assertTrue(marked, "no .gitattributes line marks %s/%s -text" % (FIXTURE, name))
            self.assertIn("-text", marked[0].split()[1:],
                          "%s/%s is not marked -text, so a Windows checkout rewrites its bytes and the signature "
                          "fails on Linux only" % (FIXTURE, name))

    def test_the_stored_bytes_are_unconverted(self):
        """(git's own idea of the file: with -text the stored and checked-out bytes are the same on every OS)"""
        blob = git("cat-file", "-p", "HEAD:" + FIXTURE + "/SHA256SUMS").stdout
        self.assertTrue(blob, "the fixture is not committed")
        self.assertNotIn(b"\r\n", blob, "the committed SHA256SUMS has CRLF: a signature over it would be newline-specific")
        on_disk = (ROOT / FIXTURE / "SHA256SUMS").read_bytes()
        self.assertEqual(on_disk, blob, "the checked-out SHA256SUMS differs from the committed bytes: git converted it")

    def test_the_signature_covers_the_committed_bytes(self):
        openssl = shutil.which("openssl")
        if not openssl:
            self.skipTest("needs the openssl command line")
        fixture = ROOT / FIXTURE
        blob = git("cat-file", "-p", "HEAD:" + FIXTURE + "/SHA256SUMS").stdout
        signature = base64.b64decode((fixture / "SHA256SUMS.sig").read_text(encoding="utf-8").strip())
        self.assertTrue(signature, "SHA256SUMS.sig is not base64 DER")
        scratch = tempfile.mkdtemp()
        try:
            sums, der = os.path.join(scratch, "SHA256SUMS"), os.path.join(scratch, "sig.der")
            with open(sums, "wb") as f:
                f.write(blob)
            with open(der, "wb") as f:
                f.write(signature)
            r = subprocess.run([openssl, "dgst", "-sha256", "-verify", str(fixture / "test-key.pub.pem"),
                                "-signature", der, sums], capture_output=True, text=True)
            self.assertIn("Verified OK", r.stdout + r.stderr,
                          "the fixture's signature does not cover the bytes git stores, so it verifies on one OS's "
                          "checkout only: %s" % (r.stdout + r.stderr).strip()[:200])
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_the_hashes_name_the_files_the_readme_documents(self):
        """(the README says what the two little files are: keep it and the sums together)"""
        readme = (ROOT / FIXTURE / "README.md").read_text(encoding="utf-8")
        sums = git("cat-file", "-p", "HEAD:" + FIXTURE + "/SHA256SUMS").stdout.decode()
        for line in sums.splitlines():
            digest, name = line.split()
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertIn(name, readme, "SHA256SUMS names %s, which the fixture README does not describe" % name)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    unittest.main()