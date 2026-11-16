"""release.py's fork anchor is a commit SHA, so a history rewrite moves it, and a stale one fails silently.

`PRODUCTS[...]["since"]` is the commit the nightlies count from and the boundary `after_fork()` uses to tell this fork's
tags from upstream's. Nothing in the code notices when that SHA stops being an ancestor of `main`: `git rev-list --count`
still answers, it just counts the whole upstream history instead of the fork's, and `after_fork()` answers False for every
real release. So the nightly number jumps (233 became 2299 in the 2026-11-15 rewrite) and `next_tag` no longer sees the
published release, offering a version that is already out.

Both are silent: no error, no warning, just a wrong number and a duplicate release. This is the check that was missing.

  python -I -B tests/test_release_anchor.py
"""
import importlib.util
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("release", ROOT / "scripts" / "release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def git(*args):
    """Run git in the repository, or "" when it fails (release.git() answers None, which reads the same here)."""
    done = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def is_ancestor(commit, of="HEAD"):
    return git("merge-base", "--is-ancestor", commit, of) is not None and \
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, of], cwd=ROOT).returncode == 0


class Anchor(unittest.TestCase):
    def test_the_anchor_is_a_commit_that_exists(self):
        since = release.PRODUCTS["longshot"]["since"]
        self.assertRegex(since, r"^[0-9a-f]{40}$", "the anchor is a full commit SHA")
        self.assertTrue(git("cat-file", "-t", since) == "commit", "the anchor names a commit that is here")

    def test_the_anchor_is_an_ancestor_of_main(self):
        """A rewrite moves it. A stale anchor does not fail loudly: it counts all of upstream and hides every release."""
        since = release.PRODUCTS["longshot"]["since"]
        self.assertTrue(is_ancestor(since, "HEAD"),
                        "the anchor %s is no longer an ancestor of HEAD: a history rewrite moved it, so the nightly "
                        "number counts upstream history and after_fork() rejects every real release. Find the rewritten "
                        "commit with the same tree and subject and update PRODUCTS['longshot']['since']." % since[:8])

    def test_the_nightly_number_matches_the_last_published_tag(self):
        """The number is commits since the anchor, so it only makes sense while the anchor is right."""
        since = release.PRODUCTS["longshot"]["since"]
        counted = int(git("rev-list", "--count", "%s..HEAD" % since) or 0)
        self.assertGreater(counted, 0, "the anchor is behind HEAD, so the count is real")

        # The newest nightly tag names its own number: nightly-<n>-<short sha>. A stale anchor puts the count far above
        # every real number, so the two stop agreeing.
        #
        # Only tags whose commit is on this fork's main count. A clone that ran `git fetch --tags` also carries
        # upstream's nightlies, which number from upstream's own first commit and run far ahead of ours (324-363
        # against our 240); comparing against those fails on a correct anchor. `after_fork()` is not enough to tell
        # them apart - upstream's tags are *after* the fork anchor, so it accepts them too - but their commits are not
        # ancestors of this fork's main, and ours are.
        #
        # (One tag is excluded even then: `nightly-2300-*`, published by CI while the anchor was stale. Its commit is
        # on main, so it passes the ancestor test, and its number is nonsense. Deleting a published release is not this
        # test's business, so it is ignored rather than compared against - the same reason the check is a broad band
        # and not an equality.)
        nights = []
        for tag in git("tag", "-l", "nightly-*").split():
            parts = tag.split("-")
            if len(parts) != 3 or not parts[1].isdigit():
                continue
            commit = git("rev-list", "-n", "1", tag)
            if not commit or not is_ancestor(commit, "HEAD"):
                continue   # (upstream's: not on this fork's main)
            nights.append(int(parts[1]))
        if not nights:
            self.skipTest("no nightly tag on this fork's main to compare against")
        recent = [n for n in nights if n < 1000] or nights   # (see above: 2300 is the rewrite's leftover)
        last = max(recent)
        self.assertLessEqual(abs(counted - last), 25,
                             "commits since the anchor (%d) are far from the last nightly number (%d): the anchor is "
                             "probably stale after a rewrite" % (counted, last))

    def test_after_fork_accepts_a_real_release(self):
        """The predicate the tag logic leans on: a published release must be this fork's."""
        if not git("tag", "-l", "v0.1.0-rc.1"):
            self.skipTest("v0.1.0-rc.1 is not here (git fetch --tags)")
        self.assertTrue(release.after_fork("v0.1.0-rc.1"),
                        "after_fork() rejects v0.1.0-rc.1, which this fork published: a stale anchor")

    def test_next_tag_does_not_offer_a_version_already_published(self):
        """The consequence of a stale anchor: a duplicate release of a version that is already out."""
        existing = [t for t in git("tag", "-l").split() if t]
        if "v0.1.0-rc.1" not in existing:
            self.skipTest("v0.1.0-rc.1 is not here (git fetch --tags)")
        offered = release.next_tag(existing, 0)
        self.assertNotEqual(offered, "v0.1.0-rc.1",
                            "next_tag offers v0.1.0-rc.1 again, which is already published")
        self.assertEqual(offered, "v0.1.0-rc.2", "the next candidate follows the one that is out")

    def test_the_launcher_has_no_anchor(self):
        """The launcher counts from its repository's first commit, so it has nothing to go stale."""
        self.assertIsNone(release.PRODUCTS["launcher"]["since"])


if __name__ == "__main__":
    unittest.main()
