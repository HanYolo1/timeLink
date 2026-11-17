"""Nothing that ships fetches from the upstream project, and nothing that ships fetches from MagicBeanDev at all.

The fork has no connection to the upstream repository: not for a build, not for a tool, not for a release, not for a web
page. What ships is the game, the builder and the launcher, and each is checked here on what it actually
fetches rather than on whether the word appears.

The word itself is not the test. Attribution stays: `MagicBeanDev/timeLink Launcher` names where a vendored file's
licence text lives (the GPL requires it), and "by Team MagicBean" is a copyright notice. What may not stay is a URL: a
host that is not ours, in a file that a player's build reads.

The team's own collaboration tooling is out of scope and named below: it is not shipped and does not reach a player.

  python -I -B tests/test_no_upstream_dependency.py
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A URL on MagicBeanDev's hosts, in any form: the Forgejo, its CDN, its Cloudflare edge, the old docs site, the API.
HOST = re.compile(r"https?://(?:[A-Za-z0-9.-]*\.)?magicbean\.dev\b", re.I)
# The upstream repository's own name, as a URL or an API path: a fetch, not a mention.
UPSTREAM_REPO = re.compile(r"(?:github\.com|api\.github\.com/repos|git\.magicbean\.dev)/MagicBeanDev/(?!timeLink Launcher)", re.I)
# Any fetch of a release asset or API that is not this fork's, in the shapes the code uses.
FOREIGN_API = re.compile(r"api/v1/", re.I)

# What ships. Each entry is a glob and the reason it is in scope.
SHIPPED = [
    "tools.lock",
    "builder/setup/setup.c",
    "builder/linux/AppRun",
    "builder/timeLinkBuilder/Program.cs",
    "builder/**/*.cs",
    "builder/**/*.c",
    "builder/**/*.sh",
    "launcher/**/*.cs",
    "launcher/**/*.ts",
    "launcher/**/*.json",
    "gpu/**/*.c",
    "gpu/**/*.cpp",
    "gpu/**/*.h",
    "host/**/*.c",
    "host/**/*.h",
    "scripts/ngx_sdk.py",          # the DLSS/NGX runtimes: NVIDIA's server, never ours to re-host
    "scripts/tools.py",            # what the builder fetches with
]

# Not shipped, and reaching no player: the release job's own tool, and a one-off that staged the archives.
NOT_SHIPPED = {
    "scripts/rehost_tools.py",     # one-off: staged the archives, records where each came from
    "scripts/release.py",          # the release job's own tool, and its comments record what was removed
    "launcher/scripts/release.py",
}
# Paths whose content is history about what was removed, or a comment explaining it.
HISTORY_OK = ("launcher/VENDORED.md", "docs/", "*.md")


def files():
    """Every shipped file, once, in a stable order."""
    seen = set()
    for pattern in SHIPPED:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in NOT_SHIPPED or rel in seen:
                continue
            if any(part in rel for part in ("/obj/", "/bin/", "/node_modules/", "/dist/", "/third_party/")):
                continue
            if rel.endswith(".md") or rel.startswith("docs/"):
                continue   # (prose: the attribution and the history are wanted)
            seen.add(rel)
            yield rel, path


class ShippedCode(unittest.TestCase):
    def test_nothing_shipped_fetches_from_magicbean(self):
        """A host of MagicBeanDev's in a file that ships is a dependency: the fork does not own it and it can go away."""
        bad = []
        for rel, path in files():
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if HOST.search(line):
                    bad.append("%s:%d: %s" % (rel, n, line.strip()[:120]))
        self.assertEqual([], bad, "shipped code still fetches from MagicBeanDev:\n" + "\n".join(bad))

    def test_nothing_shipped_reads_the_upstream_repository(self):
        """The upstream project is not a source of anything: not a release, not an API call, not a file."""
        bad = []
        for rel, path in files():
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if UPSTREAM_REPO.search(line):
                    bad.append("%s:%d: %s" % (rel, n, line.strip()[:120]))
        self.assertEqual([], bad, "shipped code still reads the upstream repository:\n" + "\n".join(bad))

    def test_nothing_shipped_speaks_another_server_s_api(self):
        """`api/v1/` is Forgejo's and Gitea's shape. GitHub serves `api.github.com/repos/...` with no version segment."""
        bad = []
        for rel, path in files():
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if FOREIGN_API.search(line):
                    bad.append("%s:%d: %s" % (rel, n, line.strip()[:120]))
        self.assertEqual([], bad, "shipped code still calls a Forgejo-shaped API:\n" + "\n".join(bad))

    def test_the_tools_come_from_our_own_repository_first(self):
        """`tools.lock` names timeLink-tools first: a fallback may be the original publisher, never upstream."""
        text = (ROOT / "tools.lock").read_text(encoding="utf-8")
        ours = "https://github.com/HanYolo1/timeLink-tools/releases/download/tools/"
        lines = [l for l in text.splitlines() if l.startswith("tool ")]
        self.assertEqual(11, len(lines), "the 11 tools are still named")
        for line in lines:
            urls = [u for u in line.split() if u.startswith("https://")]
            self.assertTrue(urls, "a tool names where it comes from: " + line[:80])
            self.assertTrue(urls[0].startswith(ours), "a tool's first URL is ours: " + urls[0])
            for url in urls:
                self.assertNotRegex(url, HOST, "a tool still names MagicBeanDev: " + url)
                self.assertNotRegex(url, r"github\.com/MagicBeanDev/", "a tool still names the upstream repository: " + url)

    def test_the_launcher_trusts_only_this_forks_key(self):
        """A launcher of this fork must not take a release from another: one key, and it is this fork's."""
        trust = (ROOT / "launcher" / "Core" / "ReleaseTrust.cs").read_text(encoding="utf-8")
        self.assertIn("774f1dc88462b913", trust, "the release key is the one the published releases are signed with")
        self.assertNotIn("5e18330371d7f5aa", re.sub(r"//.*", "", trust),
                         "the key the launcher was vendored with is gone (a comment may record it)")

    def test_the_dlss_runtimes_come_from_nvidia(self):
        """NVIDIA's licence allows these only as part of an application, so they are fetched from NVIDIA, not re-hosted."""
        text = (ROOT / "scripts" / "ngx_sdk.py").read_text(encoding="utf-8")
        self.assertIn("raw.githubusercontent.com/NVIDIA/DLSS/", text)
        self.assertNotRegex(text, HOST, "the DLSS SDK is not fetched from MagicBeanDev")
        self.assertIn("--accept-nvidia-license", text, "NVIDIA's licence is accepted explicitly")


class Boundary(unittest.TestCase):
    def test_the_team_tooling_is_out_of_scope_on_purpose(self):
        """The exclusion is a decision, not an oversight: the scripts exist, and they are not shipped."""
        for rel in sorted(NOT_SHIPPED):
            self.assertTrue((ROOT / rel).exists(), "the tooling this test excludes is still here: " + rel)

    def test_the_sweep_actually_reads_files(self):
        """A guard that silently matches nothing is worse than no guard."""
        found = list(files())
        self.assertGreater(len(found), 100, "the sweep covers the shipped tree: %d files" % len(found))
        self.assertIn("tools.lock", [rel for rel, _ in found])
        self.assertIn("launcher/Core/ReleaseTrust.cs", [rel for rel, _ in found])


if __name__ == "__main__":
    unittest.main()
