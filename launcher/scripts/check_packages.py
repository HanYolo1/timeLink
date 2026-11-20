"""Checks every package a launcher publish downloaded against what the repository pins (scripts/package.sh).

A self-contained publish downloads more than the plain build that packages.lock.json records: each system's runtime packs
(Microsoft.NETCore.App.Runtime.<rid>, Microsoft.NETCore.App.Host.<rid>, ...), which NuGet does not lock. package.sh restores
into a package folder of its own, empty before it, and this checks every package left there:

- a package packages.lock.json names must be the version and content hash it records (contentHash);
- any other must be listed, with its content hash, in publish-packages.lock.

The content hash is NuGet's: the SHA-512 of the package without its signature, so a signed package keeps its hash when it is
signed again by the repository. It is read from the <id>.<version>.nupkg.metadata NuGet writes beside every package it
downloads, computed from the downloaded file, the same value packages.lock.json records.

Anything else fails the release, and is printed in publish-packages.lock's format so a reviewed change can add it. Which
runtime packs come in follows the .NET SDK, so CI pins the SDK (scripts/dotnet-sdk.json) and moving it is one change that
updates both files.

    python3 -I scripts/check_packages.py <package folder> <publish-packages.lock> <packages.lock.json>...
"""
import json
from pathlib import Path
import sys


def content_hash(folder):
    """The contentHash NuGet recorded for the package in this <id>/<version> folder, or None."""
    meta = folder / ".nupkg.metadata"
    if not meta.is_file():
        return None
    value = json.loads(meta.read_text(encoding="utf-8-sig")).get("contentHash")
    return value if isinstance(value, str) and value else None


def read_lock_json(path):
    """{(id, version): contentHash} from a packages.lock.json (every target, the per-system ones too)."""
    pins = {}
    for target in json.loads(Path(path).read_text(encoding="utf-8"))["dependencies"].values():
        for name, entry in target.items():
            if entry.get("type") == "Project" or "contentHash" not in entry:
                continue
            pins[(name.lower(), entry["resolved"].lower())] = entry["contentHash"]
    return pins


def read_publish_lock(path):
    """{(id, version): content hash} from publish-packages.lock: '<id> <version> <content hash>' a line, # comments."""
    pins = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"{path}:{n}: not '<id> <version> <content hash>': {line}")
        pins[(parts[0].lower(), parts[1].lower())] = parts[2]
    return pins


def downloaded(folder):
    """[(id, version, folder)] in a NuGet global packages folder (<id>/<version>/, lower case)."""
    found = []
    for idd in sorted(p for p in Path(folder).iterdir() if p.is_dir()):
        for ver in sorted(p for p in idd.iterdir() if p.is_dir()):
            found.append((idd.name, ver.name, ver))
    return found


def check(folder, publish_lock, lock_jsons):
    """The problems, one line each, and the publish-packages.lock lines that would pin what is not pinned."""
    pins = {}
    for path in lock_jsons:
        pins.update(read_lock_json(path))
    extra = read_publish_lock(publish_lock)
    problems, to_add = [], []
    for name, ver, where in downloaded(folder):
        got = content_hash(where)
        if got is None:
            problems.append(f"{name} {ver}: no content hash in its .nupkg.metadata (not a package NuGet downloaded whole)")
            continue
        want = pins.get((name, ver), extra.get((name, ver)))
        if want is None:
            problems.append(f"{name} {ver}: downloaded, but neither packages.lock.json nor publish-packages.lock pins it")
            to_add.append(f"{name} {ver} {got}")
        elif got != want:
            problems.append(f"{name} {ver}: content hash {got}, but the repository pins {want}")
    return problems, to_add


def main(argv):
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    folder, publish_lock, lock_jsons = argv[0], argv[1], argv[2:]
    problems, to_add = check(folder, publish_lock, lock_jsons)
    count = len(downloaded(folder))
    if problems:
        for p in problems:
            print(f"check_packages: {p}", file=sys.stderr)
        if to_add:
            print("check_packages: after checking where they come from, these lines in publish-packages.lock would pin them:",
                  file=sys.stderr)
            for line in to_add:
                print(line, file=sys.stderr)
        return 1
    print(f"check_packages: all {count} packages the publish downloaded are pinned")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
