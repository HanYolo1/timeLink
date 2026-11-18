"""release.py's after_fork() counts the main of a remote that *is* this repository, whatever the remote is called.

It once skipped `origin` by name, from when origin was the upstream repository and the fork's main was `github/main`.
timeLink is a hard fork now: its clones and CI's checkout call it `origin`. On a checkout with no local main (CI's: a
detached merge commit, `origin/main` beside it) it found no main at all and refused every release, so next_tag offered
v0.1.0-rc.1 with v0.1.0-rc.3 already out (tests/test_release_anchor.py, part 2 of CI's Python checks after #5).

A remote that points anywhere else keeps not counting: an upstream repository a clone still carries has its own tags on
its main, real releases of that repository, not of this one.

  python -I -B tests/test_release_fork_main.py
"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COPIES = [load(ROOT / "scripts" / "release.py", "release"), load(ROOT / "launcher" / "scripts" / "release.py", "release_launcher")]


def git(root, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main", *args],
                          cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def commit(root, message):
    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


class ForkMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="release-fork-main-")
        base = Path(self.tmp.name)
        self.upstream_repo, self.repo, self.clone = base / "upstream", base / "timeLink", base / "checkout"
        # (the repository: the fork's first commit, then a release on main)
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        self.anchor = commit(self.repo, "the fork's first commit")
        commit(self.repo, "a change")
        git(self.repo, "tag", "v0.1.0-rc.3")
        # (an upstream repository that took the same history further, with a tag of its own)
        git(base, "clone", "-q", str(self.repo), str(self.upstream_repo))
        commit(self.upstream_repo, "upstream's own change")
        git(self.upstream_repo, "tag", "v3.0.0-rc.4")
        # (CI's checkout: origin is this repository, origin/main beside a detached HEAD, no local main)
        git(base, "clone", "-q", str(self.repo), str(self.clone))
        git(self.clone, "checkout", "-q", "--detach")
        git(self.clone, "branch", "-q", "-D", "main")
        git(self.clone, "remote", "set-url", "origin", "https://github.com/HanYolo1/timeLink")

    def tearDown(self):
        self.tmp.cleanup()

    def test_origin_that_is_this_repository_counts(self):
        for release in COPIES:
            self.assertTrue(release.after_fork("v0.1.0-rc.3", root=str(self.clone), since=self.anchor),
                            "%s: a release on origin/main, origin being this repository, is refused" % release.__name__)

    def test_a_remote_that_is_another_repository_does_not(self):
        git(self.clone, "remote", "add", "upstream", "https://github.com/NotRexed/Longshot.git")
        git(self.clone, "fetch", "-q", str(self.upstream_repo), "+refs/heads/main:refs/remotes/upstream/main",
            "+refs/tags/v3.0.0-rc.4:refs/tags/v3.0.0-rc.4")
        for release in COPIES:
            self.assertFalse(release.after_fork("v3.0.0-rc.4", root=str(self.clone), since=self.anchor),
                             "%s: upstream's tag counts as this repository's release" % release.__name__)
            self.assertTrue(release.after_fork("v0.1.0-rc.3", root=str(self.clone), since=self.anchor))

    def test_the_local_main_still_counts(self):
        git(self.clone, "remote", "set-url", "origin", "https://example.com/elsewhere.git")
        git(self.clone, "branch", "-q", "main", "origin/main")
        for release in COPIES:
            self.assertTrue(release.after_fork("v0.1.0-rc.3", root=str(self.clone), since=self.anchor))

    def test_this_repository_by_its_url(self):
        for release in COPIES:
            for url in ("https://github.com/HanYolo1/timeLink", "https://github.com/hanyolo1/timelink.git",
                        "git@github.com:HanYolo1/timeLink.git", "ssh://git@github.com/HanYolo1/timeLink",
                        "https://x-access-token:abc@github.com/HanYolo1/timeLink.git", "https://github.com/HanYolo1/timeLink/"):
                self.assertTrue(release.this_repository(url), url)
            for url in ("https://github.com/NotRexed/Hookshot.git", "https://github.com/HanYolo1/timeLink-tools",
                        "https://gitlab.com/HanYolo1/timeLink", "https://github.com/HanYolo1/timeLink/extra", "", None):
                self.assertFalse(release.this_repository(url), url)


if __name__ == "__main__":
    unittest.main(verbosity=1)
