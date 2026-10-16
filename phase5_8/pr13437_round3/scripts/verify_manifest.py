"""Generate or verify SHA256SUMS for every tracked payload except itself.

Run from any directory: python path/to/scripts/verify_manifest.py [--write]
New payload must be git-added before generation. Output is sorted UTF-8/LF.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='regenerate before checking')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    repo = Path(subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True).strip())
    prefix = root.relative_to(repo).as_posix() + '/'
    tracked = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z', '--', prefix]).decode().split('\0')[:-1]
    unknown = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '--others', '--exclude-standard', '-z', '--', prefix]).decode().split('\0')[:-1]
    if unknown:
        raise SystemExit('Untracked payload: git-add or relocate before checking: ' + repr(unknown))
    names = sorted(Path(p).relative_to(prefix).as_posix() for p in tracked if p != prefix + 'SHA256SUMS.txt')
    expected = ''.join(hashlib.sha256((root / n).read_bytes()).hexdigest() + ' *./' + n + '\n' for n in names).encode('utf-8')
    manifest = root / 'SHA256SUMS.txt'
    if args.write:
        manifest.write_bytes(expected)
    actual = manifest.read_bytes()
    if actual != expected:
        raise SystemExit('FAIL: manifest differs from exact sorted tracked payload; check hashes, paths, coverage, duplicates, self-entry and LF endings')
    print(f'PASS: {len(names)} tracked payload files; zero mismatches/missing/unexpected entries; manifest excluded')
    print('manifest_sha256=' + hashlib.sha256(actual).hexdigest())


if __name__ == '__main__':
    main()
