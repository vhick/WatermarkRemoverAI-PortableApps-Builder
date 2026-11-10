"""Preflight absolute paths passed to pinned NSIS community-installer.nsi.

NSIS uses File /r and has a known Windows MAX_PATH input limit. Moving source
staging into a short runner-temp directory is the fix; this check makes it
fail early and clearly if a future upstream Python/Qt package gets even deeper.

It never renames/removes any application binaries, alters Windows policy, or
changes the shared Package Builder.
"""
import argparse
import os
from pathlib import Path
import sys

DEFAULT_MAX_PATH = 245  # reserve 15 characters below the classic 260 limit


def inspect_paths(source: Path, max_length=DEFAULT_MAX_PATH):
    source = Path(source).absolute()
    if not source.is_dir():
        raise RuntimeError(f"Missing installer source directory: {source}")
    if source.name != 'WatermarkRemoverAIPortable':
        raise RuntimeError(f"Installer source must be WatermarkRemoverAIPortable: {source}")
    if not 100 <= max_length <= 259:
        raise ValueError('MAX_PATH safety threshold must be between 100 and 259')

    longest_len, longest_path, file_count = len(str(source)), source, 0
    for base, dirnames, filenames in os.walk(source, topdown=True, followlinks=False):
        for part in dirnames + filenames:
            path = Path(base) / part
            if path.is_symlink():
                raise RuntimeError(f'Symlink found in installer input: {path}')
            plen = len(str(path))
            if plen > longest_len:
                longest_len, longest_path = plen, path
        file_count += len(filenames)

    if file_count < 1:
        raise RuntimeError(f'Installer source contains no files: {source}')
    if longest_len > max_length:
        raise RuntimeError(
            f'NSIS source path too long: {longest_len} characters (safe limit {max_length}): '
            f'{longest_path}. Use a shorter stage; do not delete Qt/Python files.'
        )
    return longest_len, longest_path, file_count


def main():
    parser = argparse.ArgumentParser(description='Validate NSIS File /r source path budget')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--max-length', type=int, default=DEFAULT_MAX_PATH)
    args = parser.parse_args()
    length, path, count = inspect_paths(args.source, args.max_length)
    print(f'NSIS SOURCE PATHS OK: {count} files; longest absolute path {length} characters (max {args.max_length}): {path}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('NSIS PATH PREFLIGHT FAILED:', exc, file=sys.stderr)
        raise SystemExit(1)
