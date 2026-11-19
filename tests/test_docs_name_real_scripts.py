"""The docs name scripts that exist.

A guide that says `python -I scripts/forge.py login` is worse than no guide: the reader runs it, gets "No such file or
directory", and has no way to tell whether the tool is missing or they are. That is what happened when the team's
Forgejo tooling was deleted in 25ca5d0a - the scripts went and every page that told an agent to run them stayed.

So: every `scripts/<name>.py` a Markdown file names must be a file. The check reads the prose, not the code, because
the prose is what a person follows.

Two things it deliberately does not do. It does not check that the command would work, only that the file is there. And
it does not read `docs/known-issues.md`, which is the record of what was removed and has to be able to name it.

  python -I -B tests/test_docs_name_real_scripts.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A script the prose tells someone to run. `scripts/` at the start of a path, so a mention of another project's
# `scripts/` is not caught; the name is a Python file, which is what every tool here is.
SCRIPT = re.compile(r"(?<![\w/.-])scripts/([A-Za-z0-9_]+\.py)\b")

# The record of what was removed, which has to be able to name what is gone.
HISTORY = {"docs/known-issues.md"}

# Where a person reads instructions. Not the tests (they name fixtures) and not the vendored tree.
ROOTS = ("README.md", "CONTRIBUTING.md", "AGENTS.md", "RELEASING.md", "docs", "launcher", "builder", ".github")


def pages():
    """Every Markdown page a person or an agent is meant to read, once, in a stable order."""
    seen = set()
    for top in ROOTS:
        top = ROOT / top
        if top.is_file():
            candidates = [top]
        elif top.is_dir():
            candidates = sorted(top.rglob("*.md"))
        else:
            continue
        for path in candidates:
            rel = path.relative_to(ROOT).as_posix()
            if rel in seen or rel in HISTORY:
                continue
            if any(part in rel for part in ("/node_modules/", "/third_party/", "/bin/", "/obj/")):
                continue
            seen.add(rel)
            yield rel, path


class DocsNameRealScripts(unittest.TestCase):
    def test_every_script_a_page_names_exists(self):
        missing = []
        for rel, path in pages():
            text = path.read_text(encoding="utf-8", errors="replace")
            for name in sorted(set(SCRIPT.findall(text))):
                # A page in a subproject means its own `scripts/` first: launcher/README.md's `scripts/translations.py`
                # is launcher/scripts/translations.py, not the root's.
                if (path.parent / "scripts" / name).is_file():
                    continue
                if (ROOT / "scripts" / name).is_file():
                    continue
                missing.append("%s names scripts/%s, which is not there" % (rel, name))
        self.assertEqual([], missing, "\n".join(missing))

    def test_the_sweep_actually_reads_pages(self):
        """A guard that silently matches nothing is worse than no guard."""
        found = list(pages())
        self.assertGreater(len(found), 20, "the sweep covers the docs: %d pages" % len(found))
        self.assertIn("AGENTS.md", [rel for rel, _ in found])
        self.assertIn("docs/workflow.md", [rel for rel, _ in found])

    def test_the_pattern_matches_a_real_reference(self):
        """The regex is the load-bearing part: prove it reads a command, and not a bare word."""
        self.assertEqual(["release.py"], SCRIPT.findall("python -I scripts/release.py next"))
        self.assertEqual(["check_pr_description.py"],
                         SCRIPT.findall("`python -I scripts/check_pr_description.py --pr <n>`"))
        self.assertEqual([], SCRIPT.findall("the scripts/ directory"))
        self.assertEqual([], SCRIPT.findall("launcher/scripts/make_icon.py"))


if __name__ == "__main__":
    unittest.main()
