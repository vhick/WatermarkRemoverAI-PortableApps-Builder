"""Resolve real stable GitHub Releases, verify SHA256SUMS and source tag identity.

The application is obtained ONLY from the developer's release assets, not a mirror.
The stable version is selected with numeric semver ordering.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

OWNER = "D-Ogi"
REPO = "WatermarkRemover-AI"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
RELEASE_ASSET = "WatermarkRemover-AI-{version}-windows-x64-cpu.zip"
STABLE = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def request(url, *, api=False, asset=False):
    headers = {"User-Agent": "WatermarkRemoverAI-PortableApps-Builder-b1r2", "Accept": "application/vnd.github+json" if api else "application/octet-stream"}
    token = os.environ.get("GITHUB_TOKEN") if (api or asset) else None
    if token:
        headers["Authorization"] = "Bearer " + token
    return Request(url, headers=headers)


def fetch_json(url):
    try:
        with urlopen(request(url, api=True), timeout=50) as result:
            return json.load(result)
    except HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError("Requested GitHub release not found (404): " + url) from exc
        raise RuntimeError(f"GitHub API failed HTTP {exc.code}: {url}") from exc


def sha256(path):
    d = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            d.update(chunk)
    return d.hexdigest()


def download(url, dest, expected_size=None, *, auth_asset=False):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    # Deliberately restart a partial download instead of trusting arbitrary bytes.
    for attempt in range(3):
        try:
            with urlopen(request(url, asset=auth_asset), timeout=90) as response, partial.open("wb") as output:
                while True:
                    chunk = response.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            if expected_size is not None and partial.stat().st_size != expected_size:
                raise RuntimeError("Downloaded byte length does not match GitHub asset metadata")
            partial.replace(dest)
            return
        except HTTPError as exc:
            if exc.code in (401, 403, 404, 429):
                raise RuntimeError(f"Release download HTTP {exc.code}: {url}") from exc
            if attempt == 2:
                raise
        except (URLError, OSError, RuntimeError):
            if attempt == 2:
                raise
        time.sleep(3 * (attempt + 1))


def select_release(version):
    if version.lower() != "latest":
        matched = STABLE.fullmatch(version)
        if not matched:
            raise ValueError("Only stable X.Y.Z upstream versions are allowed")
        tag = "v" + ".".join(matched.groups())
        release = fetch_json(f"{API}/releases/tags/{tag}")
        if release.get("draft") or release.get("prerelease"):
            raise RuntimeError("This upstream release is not stable")
        return release
    releases = []
    for page in range(1, 6):
        found = fetch_json(f"{API}/releases?per_page=100&page={page}")
        if not isinstance(found, list):
            raise RuntimeError("GitHub API returned an unexpected releases response")
        for item in found:
            parsed = STABLE.fullmatch(str(item.get("tag_name", "")))
            if parsed and not item.get("draft") and not item.get("prerelease"):
                version = ".".join(parsed.groups())
                names = {a.get("name") for a in item.get("assets", [])}
                if RELEASE_ASSET.format(version=version) in names and "SHA256SUMS.txt" in names:
                    releases.append((tuple(map(int, parsed.groups())), item))
        if len(found) < 100:
            break
    if not releases:
        raise RuntimeError("No suitable stable upstream releases with verified CPU ZIP + SHA256SUMS found")
    return max(releases, key=lambda r: r[0])[1]


def git(*args, cwd=None):
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    result = subprocess.run(["git", *args], cwd=cwd, env=env, encoding="utf-8", errors="replace",
                            capture_output=True, check=False, timeout=300)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr[-2500:]}")
    return result.stdout.strip()


def write_output(name, value):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8", newline="\n") as o:
            o.write(f"{name}={value}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", default="latest")
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--revision", default="b1r2")
    args = p.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    release = select_release(args.version)
    tag = str(release["tag_name"])
    version = tag.lstrip("v")
    source = work / "upstream-source"
    if source.exists():
        raise RuntimeError("Refusing to reuse an existing source checkout")
    git("clone", "--depth", "1", "--branch", tag, "--single-branch",
        f"https://github.com/{OWNER}/{REPO}.git", str(source))
    commit = git("rev-parse", "HEAD", cwd=source)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("Upstream commit is not a full SHA")
    source_version = (source / "VERSION").read_text(encoding="utf-8").strip()
    if source_version != version:
        raise RuntimeError(f"Source VERSION {source_version} != release {version}")
    release_tag = f"portable-wmrai-v{version}-{commit[:10]}-{args.revision}"
    current_repo = os.environ.get("GITHUB_REPOSITORY")
    if current_repo:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", current_repo):
            raise RuntimeError("Invalid calling repository name")
        url = f"https://api.github.com/repos/{current_repo}/releases/tags/{release_tag}"
        try:
            existing = fetch_json(url)
        except RuntimeError as err:
            if "(404)" not in str(err):
                raise
            existing = None
        if existing is not None:
            names = {a['name']: a for a in existing.get('assets', [])}
            zips = [n for n in names if n.endswith('.zip')]
            pafs = [n for n in names if n.endswith('.paf.exe')]
            if (existing.get('draft') or 'portable-release-publisher:managed:v2' not in existing.get('body', '')
                    or len(zips) != 1 or len(pafs) != 1 or 'SHA256SUMS.txt' not in names):
                raise RuntimeError("Conflicting/incomplete existing release; refusing silent overwrite")
            previous_sums = work / 'existing-release-SHA256SUMS.txt'
            download(f"https://api.github.com/repos/{current_repo}/releases/assets/{names['SHA256SUMS.txt']['id']}", previous_sums, names['SHA256SUMS.txt'].get('size'), auth_asset=True)
            sum_lines = previous_sums.read_text(encoding='utf-8-sig').splitlines()
            proven = set()
            for line in sum_lines:
                match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line.strip())
                if match:
                    proven.add(match.group(2).strip())
            if not set(zips + pafs) <= proven or any(names[n].get('size', 0) <= 0 for n in zips + pafs):
                raise RuntimeError("Existing release checksum manifest/asset metadata mismatch")
            write_output('skip', 'true')
            write_output('version', version)
            write_output('source_sha', commit)
            write_output('tag', release_tag)
            print('SKIPPED: complete publisher-managed release already exists:', release_tag)
            return
    write_output('skip', 'false')
    assets = {a["name"]: a for a in release.get("assets", [])}
    filename = RELEASE_ASSET.format(version=version)
    if filename not in assets or "SHA256SUMS.txt" not in assets:
        raise RuntimeError("Stable release lacks its official CPU ZIP or SHA256SUMS.txt; refusing unverified download")
    sums = work / "upstream-SHA256SUMS.txt"
    download(assets["SHA256SUMS.txt"]["browser_download_url"], sums, assets["SHA256SUMS.txt"].get("size"))
    matches = []
    for line in sums.read_text(encoding="utf-8-sig").splitlines():
        match = re.fullmatch(r"\s*([a-fA-F0-9]{64})\s+\*?(.+?)\s*", line)
        if match and match.group(2).replace("\\", "/").removeprefix("./") == filename:
            matches.append(match.group(1).lower())
    if len(matches) != 1:
        raise RuntimeError("Exactly one upstream SHA256SUMS entry required for CPU release")
    downloaded = work / filename
    download(assets[filename]["browser_download_url"], downloaded, assets[filename].get("size"))
    actual = sha256(downloaded)
    if actual != matches[0]:
        raise RuntimeError(f"Official archive checksum mismatch: expected {matches[0]}, received {actual}")
    api_digest = assets[filename].get("digest")
    if api_digest and api_digest != "sha256:" + actual:
        raise RuntimeError("GitHub asset digest differs from signed-off release SHA256SUMS")
    identity = {
        "upstream_owner": OWNER, "upstream_repo": REPO, "tag": tag, "version": version,
        "commit": commit, "asset": filename, "asset_sha256": actual,
        "release_id": release["id"], "package_revision": args.revision,
        "source_requirements_sha256": {n: sha256(source / n) for n in ("requirements.txt", "requirements-core.txt")},
        "python_runtime_manifest_sha256": sha256(source / "packaging/python-runtime.json"),
    }
    (work / "identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    write_output("version", version)
    write_output("source_sha", commit)
    write_output("tag", release_tag)
    write_output("archive", str(downloaded))
    print(json.dumps(identity, indent=2))
    print("Publisher release tag:", release_tag)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
