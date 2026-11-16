"""A push to main must not publish a release: the maintainer wants one release at a time.

The Release workflow used to run on every push to `main` and publish a nightly, so the releases page filled with one
per commit (nightly-237 through 243 in a single afternoon). Each had to be deleted by hand, and the next push made
another. A tag is a release; a nightly is now asked for by hand (Actions > Release > Run workflow).

This checks the trigger, and that the manual path still works: a `workflow_dispatch` run has no tag ref, so the version
job must take the nightly branch, and the input must be read through env rather than interpolated into the shell.

  python -I -B tests/test_release_trigger.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def text():
    return WORKFLOW.read_text(encoding="utf-8")


def trigger_block():
    """The `on:` mapping, up to the next top-level key."""
    body = text()
    start = re.search(r"(?m)^on:\s*$", body)
    if not start:
        raise AssertionError("release.yml has an on: block")
    rest = body[start.end():]
    end = re.search(r"(?m)^[a-z]", rest)
    return rest[:end.start()] if end else rest


class Trigger(unittest.TestCase):
    def test_a_push_to_main_does_not_release(self):
        """The whole point: a commit on main is not a release."""
        block = trigger_block()
        push = re.search(r"(?ms)^\s+push:\s*$(.*?)(?=^\s{2}\w|\Z)", block)
        self.assertIsNotNone(push, "the workflow still has a push: trigger")
        self.assertNotRegex(push.group(1), r"branches:\s*\[?\s*main",
                            "a push to main still triggers a release: that publishes a nightly per commit")

    def test_a_tag_still_releases(self):
        """A tag is the release players download, and must keep working."""
        block = trigger_block()
        push = re.search(r"(?ms)^\s+push:\s*$(.*?)(?=^\s{2}\w|\Z)", block)
        self.assertIsNotNone(push)
        self.assertRegex(push.group(1), r"tags:\s*\[?\s*'v\*'",
                         "a v* tag must still trigger the release")

    def test_a_nightly_can_still_be_asked_for(self):
        """Removing the push trigger must not remove the ability: it is asked for by hand."""
        block = trigger_block()
        self.assertIn("workflow_dispatch:", block, "the workflow can be run by hand")
        self.assertRegex(block, r"(?s)workflow_dispatch:.*?nightly:",
                         "the manual run offers a nightly input")


class ManualRun(unittest.TestCase):
    def test_the_input_is_read_through_env(self):
        """A `${{ }}` inside a bash test is a string, and empty on a tag push: it would read as "no nightly" and skip
        the release. The input goes through env instead."""
        body = text()
        self.assertIn("WANT_NIGHTLY:", body, "the input is passed as an environment variable")
        self.assertNotRegex(body, r"\[\[[^\]]*\$\{\{\s*inputs\.nightly",
                            "the input is interpolated into a bash test, where an empty value reads as false")

    def test_a_manual_run_takes_the_nightly_branch(self):
        """A workflow_dispatch run has no tag ref, so the version job's else branch names the nightly."""
        body = text()
        self.assertIn("nightly-name", body, "the version job can name a nightly")
        self.assertRegex(body, r"GITHUB_REF == refs/tags/\*",
                         "the tag branch is chosen by the ref, so a manual run falls through to the nightly")

    def test_the_header_describes_the_trigger_it_has(self):
        """The comment at the top is the first thing a reader trusts; it must not describe the old behaviour."""
        head = "\n".join(text().splitlines()[:12])
        self.assertNotRegex(head, r"(?m)^#\s+a push to main\s+the nightly",
                            "the header still says a push to main makes a nightly")


if __name__ == "__main__":
    unittest.main()
