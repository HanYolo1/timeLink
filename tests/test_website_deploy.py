"""The website workflow's deploy could never run: a Worker name Cloudflare rejects, and secrets nobody set.

Both were silent. The `Website` workflow failed on every push and on its hourly schedule, and a red run that never
works is indistinguishable from a red run that just broke, so it hid real breakage behind an expected one.

1. `website/wrangler.jsonc` had `"name": "timeLink-website"`. Cloudflare Worker names must be alphanumeric and
   lowercase, so wrangler refuses the file outright:
       Expected "name" to be of type string, alphanumeric and lowercase with dashes only but got "timeLink-website".
2. The deploy step had no guard, so with `CLOUDFLARE_API_TOKEN` unset (this repository has never had it) it ran
   anyway and failed on the empty token.

A name is checked here by the same rule wrangler applies, and the deploy step must be gated on a credentials step.

  python -I -B tests/test_website_deploy.py
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
WORKFLOW = ROOT / ".github" / "workflows" / "website.yml"


def deploy_job():
    text = WORKFLOW.read_text(encoding="utf-8")
    return text.split("\njobs:", 1)[1] if "\njobs:" in text else text


class WorkerName(unittest.TestCase):
    def test_the_name_is_one_cloudflare_accepts(self):
        """Alphanumeric and lowercase with dashes, as wrangler requires. A capital letter is a hard failure."""
        text = (SITE / "wrangler.jsonc").read_text(encoding="utf-8")
        # (jsonc may carry comments, so the key is read without a full parse)
        found = re.search(r'"name"\s*:\s*"([^"]*)"', text)
        self.assertIsNotNone(found, "wrangler.jsonc names the Worker")
        name = found.group(1)
        self.assertRegex(name, r"^[a-z0-9][a-z0-9-]*$",
                         'Cloudflare Worker names are lowercase alphanumeric with dashes, and wrangler refuses the '
                         'config otherwise. "%s" is not.' % name)

    def test_the_route_is_not_someone_elses_domain(self):
        """The fork serves nothing on MagicBeanDev's domains, and a route naming one would try to."""
        text = (SITE / "wrangler.jsonc").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"magicbean", "wrangler.jsonc routes or names a domain this fork does not control")


class DeployGuard(unittest.TestCase):
    def test_the_deploy_is_gated_on_the_credentials(self):
        """With no token the step must skip, not fail: a permanently red workflow hides real breakage."""
        job = deploy_job()
        self.assertIn("name: Deploy", job, "the workflow has a deploy step")
        deploy = job.split("name: Deploy", 1)[1].split("\n      - ", 1)[0]
        guard = re.search(r"\n\s+if:\s*(.+)", deploy)
        self.assertIsNotNone(guard, "the deploy step has an if:, so it cannot run with no credentials")
        self.assertIn("steps.", guard.group(1), "the guard reads a step's output")
        self.assertNotIn("CLOUDFLARE_API_TOKEN !=", guard.group(1),
                         "a secret cannot be tested in an if: directly: it resolves to the workflow env, not the step's")

    def test_a_step_turns_the_secrets_into_an_output(self):
        """Whatever the guard reads must be produced by an earlier step from the secrets."""
        job = deploy_job()
        self.assertIn("GITHUB_OUTPUT", job, "a step writes its result to GITHUB_OUTPUT for the guard to read")
        for secret in ("secrets.CLOUDFLARE_API_TOKEN", "secrets.CLOUDFLARE_ACCOUNT_ID"):
            self.assertIn(secret, job, "the workflow names %s" % secret)

    def test_the_skip_says_why_in_the_log(self):
        """A silent skip looks like a broken deploy; the notice says which secrets are missing."""
        job = deploy_job()
        self.assertRegex(job, r"::notice::[^\n]*CLOUDFLARE_API_TOKEN",
                         "the skipped path explains itself with a notice naming the missing secret")


class BuildIsStillChecked(unittest.TestCase):
    def test_the_site_builds_and_checks_even_with_no_credentials(self):
        """The guard is around the upload only: the build and its checks must not depend on Cloudflare."""
        job = deploy_job()
        self.assertIn("npm run build", job)
        self.assertIn("npm run check", job)
        build = job.split("npm run build", 1)[0]
        self.assertNotIn("CLOUDFLARE_API_TOKEN", build.split("Build and check", 1)[-1],
                         "the build step does not need the Cloudflare token")


if __name__ == "__main__":
    unittest.main()
