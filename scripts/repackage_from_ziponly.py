"""Reuse a checksum-verified ZIP-only release to retry NSIS without upstream build.

Only the caller's own prior ZIP-only release is trusted; no arbitrary URLs.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

from resolve_official import fetch_json, download, sha256
from stage import safe_extract, APP_NAME
from validate import validate_stage, validate_zip

TAG_RE = re.compile(r'^portable-wmrai-v(\d+\.\d+\.\d+)-([0-9a-f]{10})-(b1r1|b1r2)-ziponly$')

def out(k,v):
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8', newline='\n') as f:
        f.write(f'{k}={v}\n')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-tag',required=True)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--dist',type=Path,required=True)
    p.add_argument('--stage-destination',type=Path,required=True, help='Short, fresh, temporary NSIS-safe staging base')
    a=p.parse_args()
    tagmatch=TAG_RE.fullmatch(a.source_tag)
    if not tagmatch:
        raise RuntimeError('Only own prior b1r1/b1r2 ZIP-only release tags can be reused')
    version,prefix,revision=tagmatch.groups()
    repository=os.environ.get('GITHUB_REPOSITORY','')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise RuntimeError('GitHub repository identity missing or invalid')
    release=fetch_json(f'https://api.github.com/repos/{repository}/releases/tags/{a.source_tag}')
    if release.get('draft') or 'portable-release-publisher:managed:v2' not in release.get('body',''):
        raise RuntimeError('Source release is not a completed release from the pinned publisher')
    assets={x['name']:x for x in release.get('assets',[])}
    zips=[name for name in assets if name.endswith('.zip')]
    if len(zips)!=1 or 'SHA256SUMS.txt' not in assets:
        raise RuntimeError('Trusted ZIP-only release does not have one ZIP and a checksum manifest')
    work=a.work.resolve();work.mkdir(parents=True,exist_ok=True)
    dist=a.dist.resolve();dist.mkdir(parents=True,exist_ok=True)
    checksum=work/'original-SHA256SUMS.txt'
    download(f"https://api.github.com/repos/{repository}/releases/assets/{assets['SHA256SUMS.txt']['id']}", checksum, assets['SHA256SUMS.txt'].get('size'), auth_asset=True)
    lines=checksum.read_text(encoding='utf-8-sig').splitlines()
    expected=[]
    for line in lines:
        m=re.fullmatch(r'\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*',line)
        if m and m.group(2)==zips[0]:expected.append(m.group(1).lower())
    if len(expected)!=1: raise RuntimeError('ZIP checksum missing/duplicated')
    package=dist/zips[0]
    download(f"https://api.github.com/repos/{repository}/releases/assets/{assets[zips[0]]['id']}", package, assets[zips[0]].get('size'), auth_asset=True)
    if sha256(package)!=expected[0]:raise RuntimeError('Previously published ZIP SHA256 mismatch')
    stage=safe_extract(package, a.stage_destination, APP_NAME)
    identity=json.loads((stage/'Other/Source/upstream-build-identity.json').read_text(encoding='utf-8'))
    if identity.get('version')!=version or not identity.get('commit','').startswith(prefix) or identity.get('package_revision')!=revision:
        raise RuntimeError('Previously published package identity differs from requested release tag')
    validate_stage(stage,version)
    validate_zip(package,version)
    out('target_tag',a.source_tag.removesuffix('-ziponly'))
    out('version',version)
    out('revision',revision)
    print('VALIDATED: trusted, unchanged ZIP-only release reused for installer retry')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        raise
