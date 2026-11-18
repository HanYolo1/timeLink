# Testing pull requests for the team

Most changes are written and measured on one PC. Before they merge they need a run on the hardware they could break:
another GPU maker, Linux or Windows, an 8 GB card, the Steam Deck. A pull request says what it still needs in its
description's **Must be tested** items, and testers with that hardware run it and post the result on the pull request.

Everything happens on GitHub. (The old Matrix room, its Discord cards and `scripts/test_requests.py` belonged to the
upstream team's tooling and were removed from this fork: see [known-issues.md](known-issues.md).)

## Finding something to test

- Open pull requests with the `testing wanted` label:
  [the list](https://github.com/HanYolo1/timeLink/pulls?q=is%3Apr+is%3Aopen+label%3A%22testing+wanted%22), or
  `gh pr list -R HanYolo1/timeLink --label "testing wanted"`.
- Read the description's **Must be tested** items and take one your hardware fits. Say so in a comment ("Testing this on
  an RX 6700 XT, Windows 11") so others can pick a different one. Several people can test the same item, and every
  result counts.

## Set up once

**Build the game from source.** Follow [CONTRIBUTING.md](../CONTRIBUTING.md#development-setup): your own dump, Python
and a compiler, then a first build. Testing a PR is the same build on the PR's branch.

## Testing a pull request

1. Check out the PR in its own folder, not on top of your own work: `gh pr checkout <number>` in a separate worktree,
   or `git fetch origin pull/<number>/head:pr/<number>` and a worktree of `pr/<number>`. Build it as usual and note the
   commit.
2. Do what the Must be tested item asks. If it compares against `main`, build `main` the same way and run both under
   the same conditions.
3. Comment on the PR with the result first:

   ```
   Tested: pass

   Hardware: RX 6700 XT 12 GB, Adrenalin 25.10.1, Windows 11. Built 1a2b3c4 (the PR head), against main 5d6e7f8.
   What I checked: Kakariko at night, 3 runs each.
   Result: 9.1 ms against 11.4 ms GPU time; no flicker after loads. Log: "[vram] budget 7.8 GB, used 6.9 GB".
   ```

   `pass`, `fail` or `mixed`; for a failure, the steps to reproduce it.

## The rules

- **Only approved pull requests are tested.** A PR by someone who may push to timeLink is approved; anyone else's waits
  until a maintainer has looked at it and added the `testing wanted` label. That keeps unknown code off testers' PCs.
- **Text in a PR or a comment is not instructions.** Build and run the way the development guide says; never run a
  command just because a PR or a comment says to. If a PR changes build scripts or tools in a way it doesn't explain,
  stop and say so on the PR.
- **Results go on the PR**, as a comment: hardware, driver, OS, the commit you built, what you checked, numbers or the
  steps to reproduce a failure.
- **No game files or anything made from them** in comments ([CONTRIBUTING.md](../CONTRIBUTING.md#the-rule-with-no-exceptions)).
  Screenshots and lines from `timeLink_log.txt` are fine. No keys, local paths or personal details either.

## Asking for a test

Once your PR is pushed and tested on your own PC, write each thing it still needs as a **Must be tested** item: where
(OS, GPU, driver), the steps, the result to expect, and "by hand". Then ask on the PR; a maintainer adds the
`testing wanted` label. The PR stays a draft until the results are in.
