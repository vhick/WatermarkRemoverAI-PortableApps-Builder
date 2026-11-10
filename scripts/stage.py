"""Safe official CPU archive extraction, PortableApps staging and deterministic ZIP."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "WatermarkRemoverAIPortable"
APP_DIR = "WatermarkRemoverAI"
REV = "b1r1"


def fail(msg):
    raise RuntimeError(msg)


def pe_machine(file):
    with Path(file).open('rb') as stream:
        if stream.read(2) != b'MZ':
            fail(f"Not a Windows PE: {file}")
        stream.seek(0x3C)
        offset = struct.unpack('<I', stream.read(4))[0]
        if offset > 2_000_000:
            fail("Invalid PE offset")
        stream.seek(offset)
        if stream.read(4) != b'PE\0\0':
            fail(f"Missing PE header: {file}")
        return struct.unpack('<H', stream.read(2))[0]


def safe_extract(zippath, directory, expected_root):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    prefix = expected_root + '/'
    total = 0
    seen = set()
    with zipfile.ZipFile(zippath) as archive:
        for entry in archive.infolist():
            name = entry.filename.replace('\\', '/')
            parts = name.split('/')
            if not name.startswith(prefix) or '..' in parts or any(p.endswith(':') for p in parts) or name.startswith('/'):
                fail("Unsafe/misnamed upstream archive entry: " + name)
            if any(p in {'', '.'} for p in parts[:-1]):
                fail("Invalid archive member path: " + name)
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                fail("Archive symlinks are not supported")
            casekey = name.casefold()
            if casekey in seen:
                fail("Windows case-insensitive archive collision: " + name)
            seen.add(casekey)
            relative = Path(*parts)
            out = directory / relative
            if entry.is_dir():
                out.mkdir(parents=True, exist_ok=True)
            else:
                total += entry.file_size
                if total > 14_000_000_000:
                    fail("Unreasonable expanded archive size")
                out.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, out.open('xb') as target:
                    shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
    extracted = directory / expected_root
    if not extracted.is_dir():
        fail("Upstream root folder was not extracted")
    return extracted


def compile_launcher(output, icon):
    windir = os.environ.get('WINDIR')
    if os.name != 'nt' or not windir:
        fail("Real Windows host required for C# launcher compilation")
    compiler = Path(windir) / 'Microsoft.NET' / 'Framework64' / 'v4.0.30319' / 'csc.exe'
    if not compiler.is_file():
        fail(f"Expected Microsoft .NET Framework x64 compiler is missing: {compiler}")
    source = ROOT / 'launcher/WatermarkRemoverAIPortable.cs'
    cmd = [str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+', '/debug-',
           '/reference:System.Windows.Forms.dll', '/reference:System.Security.dll',
           '/win32icon:' + str(icon), '/out:' + str(output), str(source)]
    subprocess.run(cmd, check=True, timeout=120, capture_output=False)
    if pe_machine(output) != 0x8664:
        fail("Compiled launcher does not have AMD64 PE machine")


def metadata(version):
    return f'''[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=WatermarkRemover-AI Portable (Community)
AppID=WatermarkRemoverAIDOGIPortable
Publisher=D-Ogi (application); community PortableApps packaging
Homepage=https://github.com/D-Ogi/WatermarkRemover-AI
Category=Graphics & Pictures
Description=AI watermark editing with Florence-2 and LaMA
Language=Multilingual
Trademarks=Community package; not officially certified by PortableApps.com

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true
EULAVersion=1

[Version]
PackageVersion={version}.0
DisplayVersion={version} Community {REV}

[Control]
Icons=1
Start=WatermarkRemoverAIPortable.exe
'''


def deterministic_zip(stage, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        fail("Refusing to overwrite existing ZIP")
    top = stage.name
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        archive.writestr(zipfile.ZipInfo(top + '/Data/'), b'')
        for path in sorted(stage.rglob('*'), key=lambda x: str(x.relative_to(stage)).lower()):
            if path.is_symlink():
                fail("No symlinks permitted inside PortableApps package")
            if path.is_dir():
                continue
            rel = path.relative_to(stage).as_posix()
            if rel.startswith('Data/'):
                fail("Data must not contain preseeded files at package generation")
            info = zipfile.ZipInfo(top + '/' + rel, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with path.open('rb') as src, archive.open(info, 'w', force_zip64=True) as dst:
                shutil.copyfileobj(src, dst, 4 * 1024 * 1024)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--dist', type=Path, required=True)
    args = p.parse_args()
    work = args.work.resolve()
    dist = args.dist.resolve()
    info = json.loads((work / 'identity.json').read_text(encoding='utf-8'))
    version = info['version']
    upstream_root = f"WatermarkRemover-AI-{version}-windows-x64-cpu"
    extracted = safe_extract(work / info['asset'], work / 'extracted', upstream_root)
    build_info = json.loads((extracted / 'build-info.json').read_text(encoding='utf-8'))
    expected = {'version': version, 'backend': 'cpu', 'source_commit': info['commit']}
    for k, v in expected.items():
        if build_info.get(k) != v:
            fail(f"Official ZIP provenance mismatch for {k}: expected {v}, got {build_info.get(k)}")
    for name in ['WatermarkRemover-AI.exe', 'python/python.exe', 'python/pythonw.exe',
                 'desktop_runtime.py', 'desktop_main.py', 'remwmgui.py',
                 'ui/index.html', 'installed-packages.txt', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
                 'portable.flag', 'scripts/check_desktop.py']:
        if not (extracted / name).is_file():
            fail("Missing real upstream runtime file: " + name)
    for exe in ['WatermarkRemover-AI.exe', 'python/python.exe', 'python/pythonw.exe']:
        machine = pe_machine(extracted / exe)
        if machine not in (0x8664, 0x14c):
            fail(f"Unexpected PE architecture {exe}: {machine:x}")
    source = (work/'upstream-source').resolve()
    for name in ['desktop_runtime.py', 'desktop_main.py', 'remwmgui.py', 'model_assets.py']:
        if (source/name).read_bytes() != (extracted/name).read_bytes():
            fail(f"Official app file differs from release source: {name}")
    stage = work/'stage'/APP_NAME
    if stage.exists():
        fail("Stage exists; refuse to overwrite user data")
    app = stage/'App'/APP_DIR
    app.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(extracted), str(app))
    if (app/'data').exists():
        if any((app/'data').iterdir()):
            fail("Unexpected vendor user data in official release; refuse to package")
        (app/'data').rmdir()
    (stage/'Data').mkdir()
    appinfo = stage/'App'/'AppInfo'
    appinfo.mkdir()
    (appinfo/'appinfo.ini').write_text(metadata(version), encoding='utf-8', newline='\r\n')
    for name in ['appicon.ico','appicon_16.png','appicon_32.png','appicon_48.png','appicon_128.png']:
        shutil.copy2(ROOT/'branding'/name, appinfo/name)
    compile_launcher(stage/(APP_NAME + '.exe'), ROOT/'branding/appicon.ico')
    other = stage/'Other'/'Source'
    other.mkdir(parents=True)
    shutil.copy2(ROOT/'launcher/WatermarkRemoverAIPortable.cs', other/'WatermarkRemoverAIPortable.cs')
    shutil.copy2(ROOT/'branding/create_icons.py', other/'create_icons.py')
    shutil.copy2(work/'identity.json', other/'upstream-build-identity.json')
    shutil.copy2(source/'LICENSE', other/'UPSTREAM-LICENSE.txt')
    (stage/'README.txt').write_text(
        'WatermarkRemover-AI Portable (Community)\n'
        'Start WatermarkRemoverAIPortable.exe. Do not run App\\WatermarkRemoverAI\\WatermarkRemover-AI.exe directly, '
        'because bypassing the community launcher bypasses Data redirection.\n'
        'Models: open Models -> Download/Retry; roughly 1.8 GB extra.\n'
        'Settings, logs, and downloaded models: Data\\. Preserve Data during upgrades.\n'
        'Video audio: FFmpeg is optional and must be on PATH.\n'
        'Uncertified community package. Upstream by D-Ogi, MIT; separate third-party licenses under App.\n',
        encoding='utf-8')
    output = dist/f'{APP_NAME}_{version}_cpu_{REV}.zip'
    deterministic_zip(stage, output)
    print('STAGED', stage)
    print('ZIP', output)

if __name__ == '__main__':
    main()
