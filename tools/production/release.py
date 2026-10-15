#!/usr/bin/env python3
"""One command per release step: bump the identity, build and seal, publish.

    release.py bump --version 1.0.0-beta.3
    release.py build --label 52            # copy of the newest build, or --clean
    release.py publish --label 52 --title "Y2Linux 1.0 Beta 3" --notes notes.md --yes

`build` never touches GitHub or a device. It copies the newest build folder
(btrfs reflink), rewrites the absolute build paths in it to the new folder,
resumes the build at the kernel, runs the release checks in parallel lanes,
signs the over-the-air update, scans every image for MediaTek firmware and
assembles the assets under out/release-<label>/. `publish` tags and pushes
both repositories and creates the GitHub release; it re-uploads the large
third-party source archive and the Linux source only when they changed and
links the identical files of the release that carries them otherwise.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
REBORN = PROJECT.parent / 'Y2Reborn'
OUT = PROJECT / 'out'
REPO = 'SchulzCode/Y2Linux'
KEY = Path.home() / '.local/share/y2linux/signing/platform-v1-release-20261015.key'
KEY_ID = 'platform-v1-release-20261015'
STOCK = Path(os.environ.get('Y2_STOCK_PACKAGE', '/home/luca/Dokumente/Code/Y2Player/y2_v3.2.0_FM-20260813'))
# An absolute path of any build folder under out/ (not out/x-build.stdout).
BUILD_PATH = re.compile(re.escape(os.fsencode(OUT)) + rb'/[A-Za-z0-9._-]+-build(?![A-Za-z0-9._-])')


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


class Steps:
    """Run named steps, log each to <folder>/<name>.log and record durations."""

    def __init__(self, logs):
        self.logs = logs
        self.durations = {}

    def run(self, name, argv, env=None, log=None):
        started = time.monotonic()
        with open(self.logs / (log or name + '.log'), 'a') as stream:
            result = subprocess.run([str(a) for a in argv], cwd=PROJECT, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT)
        self.durations[name] = round(time.monotonic() - started, 1)
        if result.returncode:
            raise SystemExit(f'{name} failed ({result.returncode}); see {self.logs / (log or name + ".log")}')


# ---------------------------------------------------------------- bump

def bump(args):
    release = PROJECT / 'tools/production/release.json'
    identity = json.loads(release.read_text())
    old = identity['release_version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(-[a-z]+\.\d+)?', args.version):
        raise SystemExit('version must look like 1.0.0 or 1.0.0-beta.3')
    prefix, minor = identity['rootfs_version'].rsplit('.', 1)
    identity.update(release_version=args.version,
                    rootfs_version=f'{prefix}.{int(minor) + 1}',
                    build_id='Y2LINUX-' + args.version.upper().replace('.', '-'),
                    update_sequence=args.sequence or identity['update_sequence'] + 100)
    release.write_text(json.dumps(identity, indent=2) + '\n')
    config = PROJECT / 'kernel/config/production.config'
    text = config.read_text()
    text, count = re.subn(r'^CONFIG_LOCALVERSION="-y2linux-[^"]+"$', f'CONFIG_LOCALVERSION="-y2linux-{args.version}"',
                          text, flags=re.M)
    assert count == 1, 'CONFIG_LOCALVERSION'
    config.write_text(text)
    receipts = PROJECT / 'tests/test_reborn_receipts.py'
    text = receipts.read_text()
    assert text.count(f"'{old}',") == 1, 'test_reborn_receipts expectation'
    receipts.write_text(text.replace(f"'{old}',", f"'{args.version}',"))
    cargo = REBORN / 'Cargo.toml'
    text = cargo.read_text()
    text, count = re.subn(r'^version = "[^"]+"$', f'version = "{args.version}"', text, count=1, flags=re.M)
    assert count == 1, 'Reborn Cargo.toml version'
    cargo.write_text(text)
    subprocess.run(['cargo', 'update', '--workspace', '--offline'], cwd=REBORN, check=True)
    print(f'{old} -> {args.version}, sequence {identity["update_sequence"]}, root {identity["rootfs_version"]}.\n'
          'Review, run the checks, commit both repositories, then: release.py build --label <N>')


# ---------------------------------------------------------------- build

def newest_build():
    candidates = []
    for folder in OUT.glob('power-final-*-build'):
        config = folder / 'buildroot/.config'
        if (folder / 'versions.json').exists() and config.exists() and \
                'BR2_PER_PACKAGE_DIRECTORIES=y' in config.read_text():
            candidates.append((folder.stat().st_mtime, folder))
    if not candidates:
        raise SystemExit('no build with per-package directories to copy; run with --clean once')
    return max(candidates)[1]


def relocate(folder):
    """Point every absolute build path in text files at `folder`.

    Copies inherit absolute paths (.la, .pc, *-config, Makefiles, CMake and
    libtool files) of the folder they came from, and of that folder's origin:
    Beta 2 still read pkg-config files and libraries of build 34. Like
    Buildroot's relocate-sdk.sh, only text files are rewritten.
    """
    target = os.fsencode(folder)
    listed = subprocess.run(['grep', '-rIlZE', '--exclude-dir=.git', str(PROJECT / 'out') + '/[A-Za-z0-9._-]+-build', '.'],
                            cwd=folder, capture_output=True)
    changed = 0
    for name in filter(None, listed.stdout.split(b'\0')):
        path = folder / os.fsdecode(name)
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        rewritten = BUILD_PATH.sub(target, data)
        if rewritten != data:
            stat = path.stat()
            path.write_bytes(rewritten)
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            changed += 1
    return changed


def firmware_free(images, stock_system):
    sys.path.insert(0, str(PROJECT / 'tools/platform'))
    from y2_platform import radiofw
    files = radiofw.from_system_image(str(stock_system))
    probes = [data[4096:4160] for data in files.values() if len(data) > 8192]
    if not probes:
        raise SystemExit('firmware scan: no probes from the stock system.img')
    result = {}
    for image in images:
        data = image.read_bytes()
        blobs = [data]
        for match in re.finditer(b'\x1f\x8b\x08', data[:64 << 20]):
            try:
                blobs.append(gzip.GzipFile(fileobj=io.BytesIO(data[match.start():])).read())
            except Exception:
                pass
        result[image.name] = any(probe in blob for blob in blobs for probe in probes)
    return result


def deterministic_tar(output, root, members, epoch):
    def normalise(info):
        info.uid = info.gid = 0
        info.uname = info.gname = ''
        info.mtime = epoch
        return info
    with tarfile.open(output, 'w', format=tarfile.PAX_FORMAT) as archive:
        for member in sorted(members):
            for path in sorted([root / member, *(root / member).rglob('*')] if (root / member).is_dir() else [root / member]):
                archive.add(path, arcname=path.relative_to(root.parent).as_posix(), recursive=False, filter=normalise)


def build(args):
    for repo in (PROJECT, REBORN):
        if git(repo, 'status', '--porcelain'):
            raise SystemExit(f'{repo.name}: commit the reviewed source first')
    folder = OUT / f'power-final-{args.label}-build'
    release = OUT / f'release-{args.label}'
    if args.resume_failed:
        if not (folder / 'buildroot/.config').exists():
            raise SystemExit(f'--continue needs an existing {folder.name}')
        shutil.rmtree(release, ignore_errors=True)
    elif folder.exists() or release.exists():
        raise SystemExit(f'{folder.name} or {release.name} already exists')
    release.mkdir(parents=True)
    logs = release / 'receipts'
    logs.mkdir()
    steps = Steps(logs)
    started = time.monotonic()

    previous = None if args.clean or args.resume_failed else (args.source.resolve() if args.source else newest_build())
    if previous:
        steps.run('copy', ['cp', '-a', '--reflink=auto', previous, folder])
        for stale in [*folder.glob('*.log'), folder / 'release-inventory.json', *folder.glob('data-seed-*')]:
            stale.unlink(missing_ok=True) if stale.is_file() else shutil.rmtree(stale, ignore_errors=True)
        shutil.rmtree(folder / 'buildroot/legal-info', ignore_errors=True)
        moment = time.monotonic()
        changed = relocate(folder)
        steps.durations['relocate'] = round(time.monotonic() - moment, 1)
        (logs / 'relocate.log').write_text(f'{previous} -> {folder}: {changed} text files rewritten\n')
    command = ['python3', 'tools/production/build.py', '--output', folder.relative_to(PROJECT), '--public']
    if previous or args.resume_failed:
        command += ['--resume', 'kernel']
    steps.run('build', command, log='build.log')
    versions = json.loads((folder / 'versions.json').read_text())
    version = versions['release_version']
    base = args.base_package.resolve() if args.base_package else previous_package(folder, previous, version)

    update, first = release / 'update', release / 'first-install'
    builder = ['python3', 'tools/build/run.py', '--output', folder.relative_to(PROJECT), '--']
    legal_env = dict(os.environ, PATH=str(PROJECT / '.cache/host-tools') + os.pathsep + os.environ['PATH'],
                     BR2_DL_DIR=str(PROJECT / '.cache/buildroot-dl'), Y2_ARTIFACT_DIR=str(folder), LC_ALL='C', TZ='UTC')
    moment = time.monotonic()

    def legal(name, argv, log=None):
        steps.run(name, argv, env=legal_env, log=log)
    with concurrent.futures.ThreadPoolExecutor(5) as pool:
        lanes = [
            [('production-tests', builder + ['sh', '/project/tools/production/tests.sh'])],
            [('package', ['python3', 'tools/production/system_update.py', '--build', folder, '--base', base,
                          '--fallback-rootfs', base / 'Y2ROOT.img', '--output', update, '--public']),
             ('package-validation', ['python3', 'tools/production/validate.py', update, '--build', folder]),
             ('package-privacy', ['sh', '-c', f'python3 tools/production/privacy.py --tree "{update}" && '
                                  f'python3 tools/production/privacy.py --root-image "{update}/Y2ROOT.img"'])],
            [('elf-closure', ['python3', 'tools/production/check_elf.py', folder / 'buildroot/target']),
             ('installed-arm', ['python3', 'tools/production/check_installed_arm.py', '--build', folder])],
            [('release-inventory', ['python3', 'tools/production/release_inventory.py', '--build', folder,
                                    '--output', folder / 'release-inventory.json'])],
            [('first-install-package', ['python3', 'tools/production/package.py', '--build', folder, '--output', first,
                                        '--stock', STOCK, '--public']),
             ('first-install-validation', ['python3', 'tools/production/validate.py', first, '--build', folder])],
        ]
        futures = [pool.submit(lambda lane=lane: [steps.run(*step) for step in lane]) for lane in lanes]
        # Buildroot's make must not run twice on one output folder at a time.
        futures[3] = pool.submit(lambda inventory=futures[3]: (inventory.result(), legal(
            'legal-info', ['make', '-C', PROJECT / '.cache/sources/buildroot-2026.08', f'O={folder / "buildroot"}',
                           f'BR2_EXTERNAL={PROJECT / "buildroot"}', 'legal-info'])))
        for future in futures:
            future.result()
    steps.durations['checks (parallel)'] = round(time.monotonic() - moment, 1)
    suite = (logs / 'production-tests.log').read_text()
    ran = sum(int(n) for n in re.findall(r'^Ran (\d+) tests?', suite, re.M))
    if re.search(r'^(FAIL|ERROR):', suite, re.M):
        raise SystemExit('production tests reported failures')

    ota = release / 'ota'
    steps.run('ota-sign', ['python3', 'tools/update/package.py', 'candidate', update, '--output', ota,
                           '--private', args.key, '--key-id', KEY_ID, '--rollback-allowed', '--notes', args.notes],
              log='ota-release.json')
    moment = time.monotonic()
    images = [first / name for name in ('Y2ROOT.img', 'BOOTIMG.img', 'RECOVERY.img', 'Y2DATA.img')]
    scan = firmware_free(images, STOCK / 'system.img')
    steps.durations['firmware-scan'] = round(time.monotonic() - moment, 1)
    if any(scan.values()):
        raise SystemExit(f'MediaTek firmware found in {[name for name, hit in scan.items() if hit]}')

    moment = time.monotonic()
    assets = release / 'assets'
    assets.mkdir()
    for path in ota.iterdir():
        shutil.copy2(path, assets / path.name)
    name = f'Y2Linux-{version}-first-install'
    staging = release / name
    shutil.copytree(first, staging)
    # The images barely compress; -6 instead of -9 costs ~1 % size.
    subprocess.run(['zip', '-q', '-r', '-6', assets / f'{name}.zip', name], cwd=release, check=True)
    shutil.rmtree(staging)
    legal_info = folder / 'buildroot/legal-info'
    epoch = int(json.loads((PROJECT / 'buildroot/inputs.lock.json').read_text())['source_date_epoch'])
    own = sorted(path.name for path in (legal_info / 'sources').iterdir()
                 if path.name.startswith(('y2-', 'reborn')))
    third = release / 'third-party.tar'
    deterministic_tar(third, legal_info, [f'sources/{path.name}' for path in (legal_info / 'sources').iterdir()
                                          if path.name not in own] + ['host-sources'], epoch)
    third_name = f'Y2Linux-sources-third-party-{sha256(third)[:12]}.tar'
    third.rename(assets / third_name)
    note = legal_info / 'THIRD-PARTY-SOURCES.txt'
    note.write_text(f'The package sources listed in manifest.csv and host-manifest.csv, except this project\'s own '
                    f'packages (sources/{", sources/".join(own)}), are in {third_name} '
                    f'(SHA-256 {sha256(assets / third_name)}), attached to or linked from this release.\n')
    deterministic_tar(assets / f'Y2Linux-{version}-sources-buildroot-legal-info.tar', legal_info,
                      [path.name for path in legal_info.iterdir() if path.name not in ('sources', 'host-sources')]
                      + [f'sources/{name}' for name in own], epoch)
    linux = sorted((PROJECT / '.cache/downloads').glob('linux-*.tar.xz'))[-1]
    shutil.copy2(linux, assets / linux.name)
    sums = ''.join(f'{sha256(path)}  {path.name}\n' for path in sorted(assets.iterdir()) if path.name != 'SHA256SUMS')
    (assets / 'SHA256SUMS').write_text(sums)
    steps.durations['assets'] = round(time.monotonic() - moment, 1)
    steps.durations['total'] = round(time.monotonic() - started, 1)

    summary = {'label': args.label, 'release_version': version, 'kernel_version': versions['kernel_version'],
               'update_sequence': versions['update_sequence'], 'linux_commit': versions['build_git_commit'],
               'reborn_commit': versions['reborn_source_commit'], 'build': str(folder.relative_to(PROJECT)),
               'copied_from': str(previous.relative_to(PROJECT)) if previous else None,
               'base_package': str(base), 'production_tests': ran, 'firmware_found': scan,
               'images': {path.name: sha256(path) for path in images},
               'assets': {path.name: path.stat().st_size for path in sorted(assets.iterdir())},
               'durations_s': steps.durations}
    (release / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    # Small receipts outlive the pruned build (archive convention since 13).
    receipts = OUT / f'deep-sleep-final/build{args.label}-receipts'
    shutil.copytree(logs, receipts, dirs_exist_ok=True)
    shutil.copy2(release / 'summary.json', receipts / 'summary.json')
    print(json.dumps(summary, indent=2))
    if not args.no_prune:
        prune(args.keep)


def previous_package(folder, previous, version):
    """The sealed update package of the build this one was copied from."""
    if previous:
        label = re.fullmatch(r'power-final-(.+)-build', previous.name).group(1)
        old = json.loads((previous / 'versions.json').read_text())['release_version']
        for candidate in (OUT / f'release-{label}/update', OUT / f'y2linux-{old}-update'):
            if (candidate / 'manifest.json').exists():
                return candidate
    raise SystemExit('pass --base-package: the sealed update package of the previous release')


# ---------------------------------------------------------------- prune

def prune(keep=2, dry_run=False):
    """Keep only the `keep` newest builds and release outputs in out/.

    Builds are out/power-final-*-build; release outputs are out/release-* and
    the older names (y2linux-*, release-NN-assets, candidate packages). Archives
    (deep-sleep-final), REA work and screenshots are never touched. A build
    that a kept build still references by absolute path is not deleted.
    """
    def newest(paths):
        return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)
    builds = newest(path for path in OUT.glob('power-final-*-build') if path.is_dir())
    releases = newest(path for path in OUT.glob('release-*') if path.is_dir() and
                      (path / 'summary.json').exists())
    legacy = [path for pattern in ('y2linux-*', 'release-*-assets', 'release-*')
              for path in OUT.glob(pattern) if path.is_dir() and not (path / 'summary.json').exists()]
    kept, doomed = builds[:keep], builds[keep:]
    kept_releases = releases[:keep]
    if len(kept_releases) < keep:
        # Until two releases exist in the new layout, keep the newest legacy update package.
        packages = newest(path for path in legacy if (path / 'manifest.json').exists() and path.name.endswith('-update'))
        kept_releases += packages[:keep - len(kept_releases)]
    doomed += [path for path in releases[keep:] + legacy if path not in kept_releases]
    # One pass per kept build: which other build folders does it still name?
    referenced = {}
    for build in kept:
        found = subprocess.run(['grep', '-rhoIE', '--exclude-dir=.git', re.escape(str(OUT)) + '/[A-Za-z0-9._-]+-build/', '.'],
                               cwd=build, capture_output=True, text=True).stdout
        for name in {line[len(str(OUT)) + 1:-1] for line in found.split()}:
            referenced.setdefault(name, []).append(build.name)
    removed, skipped = [], []
    for path in sorted(set(doomed)):
        if path in builds:
            users = [user for user in referenced.get(path.name, []) if user != path.name]
            if users:
                skipped.append(f'{path.name} (still referenced by {", ".join(users)})')
                continue
        removed.append(path.name)
        if not dry_run:
            shutil.rmtree(path)
    print(('would remove: ' if dry_run else 'removed: ') + (', '.join(removed) or 'nothing'))
    if skipped:
        print('kept, still in use: ' + '; '.join(skipped))
    return removed, skipped


# ---------------------------------------------------------------- publish

def published_assets():
    """name -> (release tag, download url, digest) for every asset already on GitHub."""
    pages = subprocess.check_output(['gh', 'api', '--paginate', f'repos/{REPO}/releases', '--jq', '.[]|@json'], text=True)
    found = {}
    for release in map(json.loads, pages.splitlines()):
        for asset in release['assets']:
            found.setdefault(asset['name'], (release['tag_name'], asset['browser_download_url'],
                                             (asset.get('digest') or '').removeprefix('sha256:'), asset['size']))
    return found


def publish(args):
    if not args.yes:
        raise SystemExit('publishing is outward-facing: pass --yes once the owner said to publish')
    release = OUT / f'release-{args.label}'
    summary = json.loads((release / 'summary.json').read_text())
    tag = f'baseline-{args.label}'
    for repo in (PROJECT, REBORN):
        if git(repo, 'status', '--porcelain'):
            raise SystemExit(f'{repo.name}: uncommitted changes')
    if git(REBORN, 'rev-parse', 'HEAD') != summary['reborn_commit']:
        raise SystemExit('Y2Reborn HEAD is not the built commit')
    build = summary['linux_commit']
    subprocess.run(['git', 'merge-base', '--is-ancestor', build, 'HEAD'], cwd=PROJECT, check=True)
    after = git(PROJECT, 'diff', '--name-only', build, 'HEAD').split()
    if any(not (name.startswith('docs/') or name == 'readme.md') for name in after):
        raise SystemExit(f'Y2Linux changed more than documentation since the build: {after}')

    assets = release / 'assets'
    existing = published_assets()
    upload, linked = [], []
    for path in sorted(assets.iterdir()):
        known = existing.get(path.name)
        if path.name.startswith('Y2Linux-sources-third-party-') or re.fullmatch(r'linux-[\d.]+\.tar\.xz', path.name):
            if known and known[3] == path.stat().st_size and known[2] in ('', sha256(path)):
                linked.append((path, known))
                continue
        upload.append(path)
    notes = Path(args.notes).read_text().rstrip('\n')
    if linked:
        notes += '\n\n## Sources unchanged since an earlier release\n' + ''.join(
            f'- [`{path.name}`]({url}) (attached to `{where}`), SHA-256 `{sha256(path)}`\n'
            for path, (where, url, _, _) in linked)
    notes_file = release / 'release-notes.md'
    notes_file.write_text(notes + '\n')

    message = f'{args.title} (Baseline {args.label})\n\n{Path(args.notes).read_text().split(chr(10) + chr(10))[0]}'
    for repo in (PROJECT, REBORN):
        if subprocess.run(['git', 'rev-parse', '-q', '--verify', f'refs/tags/{tag}'], cwd=repo,
                          capture_output=True).returncode:
            subprocess.run(['git', 'tag', '-a', tag, '-m', message], cwd=repo, check=True)
        subprocess.run(['git', 'push', 'origin', 'main', tag], cwd=repo, check=True)
    subprocess.run(['gh', 'release', 'create', tag, '-R', REPO, '--title', args.title, '--notes-file', notes_file,
                    '--latest', *upload], check=True)
    served = subprocess.run(['curl', '-sSL', f'https://github.com/{REPO}/releases/latest/download/manifest.json'],
                            capture_output=True, check=True).stdout
    if served != (assets / 'manifest.json').read_bytes():
        raise SystemExit('releases/latest does not serve this manifest yet')
    print(f'published {tag}: uploaded {len(upload)}, linked {len(linked)}; latest serves it')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('bump', help='set the release identity in both repositories')
    p.add_argument('--version', required=True)
    p.add_argument('--sequence', type=int, help='update sequence (default: previous + 100)')
    p = sub.add_parser('build', help='build, check, sign and assemble a release (local only)')
    p.add_argument('--label', required=True, help='baseline number, e.g. 52')
    p.add_argument('--clean', action='store_true', help='build from scratch instead of copying the newest build')
    p.add_argument('--continue', dest='resume_failed', action='store_true',
                   help='resume this label\'s existing build folder after a failure')
    p.add_argument('--source', type=Path, help='build folder to copy (default: the newest)')
    p.add_argument('--base-package', type=Path, help='sealed update package of the previous release')
    p.add_argument('--key', type=Path, default=KEY)
    p.add_argument('--notes', default='', help='notes inside the signed manifest')
    p.add_argument('--keep', type=int, default=2, help='builds and release outputs kept afterwards')
    p.add_argument('--no-prune', action='store_true', help='keep every older build this time')
    p = sub.add_parser('prune', help='remove all but the newest builds and release outputs')
    p.add_argument('--keep', type=int, default=2)
    p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('publish', help='tag, push and create the GitHub release')
    p.add_argument('--label', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--notes', required=True, help='release notes (Markdown file)')
    p.add_argument('--yes', action='store_true')
    args = parser.parse_args()
    if args.command == 'prune':
        prune(args.keep, args.dry_run)
        return
    {'bump': bump, 'build': build, 'publish': publish}[args.command](args)


if __name__ == '__main__':
    main()
