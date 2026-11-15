# Re-host timeLink's build tools on GitHub (docs/known-issues.md, blocker 1).
#
# tools.lock's 11 tool lines all point at MagicBeanDev's Forgejo package store first. This downloads each archive from
# the first URL that answers, checks it against the SHA-256 and size tools.lock names, and writes the file under the name
# a GitHub release asset needs: <sha256>-<name>.zip. Nothing is uploaded here: the files are staged for a `tools` release
# on HanYolo1/timeLink, which needs a token this script does not have.
#
#   python -I scripts/rehost_tools.py stage <folder>     download and verify every tool into <folder>
#   python -I scripts/rehost_tools.py lock <folder>      rewrite tools.lock's URLs to the GitHub release, in place
#   python -I scripts/rehost_tools.py check <folder>     verify the staged files against tools.lock, upload nothing
#
# The GitHub URL a tool gets is
#   https://github.com/HanYolo1/timeLink/releases/download/tools/<sha256>-<name>.zip
# and the third-party URLs a line already has stay behind it, so a deleted asset still has a fallback where one exists.
import hashlib
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, "tools.lock")
# (the tools live in a repository of their own, public: a private repository's release assets are not served at
# releases/download/ at all, not even with a token, so the builder's setup and the AppImage could not fetch them)
TOOLS_REPO = "HanYolo1/timeLink-tools"
TAG = "tools"
BASE = "https://github.com/%s/releases/download/%s/" % (TOOLS_REPO, TAG)
# (the hosts a line's own copy lives on: MagicBeanDev's package store, its Cloudflare edge)
FOREIGN = ("git-cdn.magicbean.dev", "git.magicbean.dev")


def fail(message):
    raise SystemExit("rehost_tools.py: " + message)


def tools():
    """[(name, system, sha, size, dest, prefix, urls)] from tools.lock, in file order"""
    out = []
    with open(LOCK, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("tool "):
                continue
            p = line.split()
            if len(p) < 9:
                fail("a tool line is short: " + line.strip())
            out.append((p[1], p[3], p[4], int(p[5]), p[6], p[7], p[8:]))
    return out


def asset_name(sha, name):
    return "%s-%s.zip" % (sha, name)


def github_url(sha, name):
    return BASE + asset_name(sha, name)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url, to, size):
    """url into to, refusing a body that is not size bytes"""
    req = urllib.request.Request(url, headers={"User-Agent": "timeLink-rehost-tools"})
    with urllib.request.urlopen(req, timeout=300) as r, open(to, "wb") as f:
        got = 0
        while True:
            block = r.read(1 << 20)
            if not block:
                break
            got += len(block)
            if got > size:
                fail("%s is larger than the %d bytes tools.lock names" % (url, size))
            f.write(block)
    if got != size:
        fail("%s gave %d bytes, tools.lock names %d" % (url, got, size))


def stage(folder):
    os.makedirs(folder, exist_ok=True)
    for name, system, sha, size, dest, prefix, urls in tools():
        out = os.path.join(folder, asset_name(sha, name))
        if os.path.isfile(out) and os.path.getsize(out) == size and sha256_of(out) == sha:
            print("%-12s %-12s already staged" % (name, system))
            continue
        errors = []
        for url in urls:
            try:
                print("%-12s %-12s %s" % (name, system, url))
                fetch(url, out, size)
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
                errors.append("%s: %s" % (url, e))
                continue
            got = sha256_of(out)
            if got != sha:
                os.remove(out)
                fail("%s: SHA-256 %s, tools.lock names %s" % (url, got, sha))
            print("%-12s %-12s ok (%d MB)" % (name, system, size >> 20))
            break
        else:
            fail("%s (%s): no URL answered\n  %s" % (name, system, "\n  ".join(errors)))


def check(folder):
    bad = []
    for name, system, sha, size, dest, prefix, urls in tools():
        path = os.path.join(folder, asset_name(sha, name))
        if not os.path.isfile(path):
            bad.append("%s (%s): not staged" % (name, system))
        elif os.path.getsize(path) != size:
            bad.append("%s (%s): %d bytes, tools.lock names %d" % (name, system, os.path.getsize(path), size))
        elif sha256_of(path) != sha:
            bad.append("%s (%s): SHA-256 differs" % (name, system))
    for line in bad:
        print("error: " + line, file=sys.stderr)
    if bad:
        fail("%d of %d tools are not staged correctly" % (len(bad), len(tools())))
    print("all %d tools staged and checked" % len(tools()))


def lock(folder):
    """Rewrite each tool line's URLs: the GitHub release first, then the third-party ones it already had"""
    check(folder)
    with open(LOCK, encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    changed = 0
    for line in lines:
        if not line.startswith("tool "):
            out.append(line)
            continue
        p = line.split()
        name, sha = p[1], p[4]
        urls = p[8:]
        # (a line's own copy is MagicBeanDev's; what is left is where the archive came from, which stays as a fallback)
        upstream = [u for u in urls if not any(h in u for h in FOREIGN)]
        new = [github_url(sha, name)] + upstream
        if new != urls:
            changed += 1
        out.append(" ".join(p[:8] + new) + "\n")
    with open(LOCK, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out)
    print("tools.lock: %d of %d tool lines now name %s first" % (changed, len(tools()), BASE))


def main(argv):
    if len(argv) < 2 or argv[0] not in ("stage", "check", "lock"):
        fail("usage: rehost_tools.py stage|check|lock <folder>")
    folder = argv[1]
    {"stage": stage, "check": check, "lock": lock}[argv[0]](folder)


if __name__ == "__main__":
    main(sys.argv[1:])
