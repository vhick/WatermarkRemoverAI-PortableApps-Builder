"""Independent static PortableApps ZIP and installer validations; not a GUI test."""
import argparse
import configparser
import hashlib
from pathlib import Path
import re
import struct
import zipfile
from stage import APP_NAME, APP_DIR, pe_machine


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def validate_stage(stage, version):
    stage = Path(stage)
    assert stage.name == APP_NAME, stage
    assert stage.joinpath('Data').is_dir()
    assert not list((stage / 'Data').iterdir()), 'Data must initially be empty'
    app = stage / 'App' / APP_DIR
    for f in ('WatermarkRemover-AI.exe', 'python/python.exe', 'python/pythonw.exe',
              'desktop_main.py', 'desktop_runtime.py', 'remwmgui.py', 'ui/index.html',
              'LICENSE', 'THIRD_PARTY_NOTICES.md', 'portable.flag'):
        assert (app / f).is_file(), f
    assert pe_machine(stage/(APP_NAME+'.exe')) == 0x8664
    assert pe_machine(app/'WatermarkRemover-AI.exe') in (0x8664, 0x14c)
    info = stage/'App'/'AppInfo'
    for fn in ('appinfo.ini','appicon.ico','appicon_16.png','appicon_32.png'):
        assert (info/fn).is_file(), fn
    ini = configparser.ConfigParser(interpolation=None)
    ini.read(info/'appinfo.ini', encoding='utf-8')
    assert ini['Details']['AppID'] == 'WatermarkRemoverAIDOGIPortable'
    assert ini['Control']['Start'] == APP_NAME+'.exe'
    assert ini['Version']['PackageVersion'] == version+'.0'
    assert ini['Format']['Type'] == 'PortableApps.comFormat'
    assert b'WMR_DATA_DIR' in (stage/'Other/Source/WatermarkRemoverAIPortable.cs').read_bytes()
    assert 'WMR_DATA_DIR' in (app/'desktop_runtime.py').read_text(encoding='utf-8')
    assert not (app/'data').exists(), 'User data should be at portable root'
    print('STATIC-VALIDATED stage:', stage)


def validate_zip(zippath, version):
    zippath = Path(zippath)
    expected = APP_NAME+'/'
    with zipfile.ZipFile(zippath) as z:
        bad = z.testzip()
        assert bad is None, f'Bad ZIP entry: {bad}'
        names = z.namelist()
        assert names and all(x.startswith(expected) for x in names)
        assert expected + 'Data/' in names
        assert not any(x.startswith(expected+'Data/') and x != expected+'Data/' for x in names)
        assert expected+'App/AppInfo/appinfo.ini' in names
        assert expected + APP_NAME+'.exe' in names
        assert expected+'App/WatermarkRemoverAI/WatermarkRemover-AI.exe' in names
        assert expected+'App/WatermarkRemoverAI/python/python.exe' in names
        with z.open(expected+APP_NAME+'.exe') as f:
            header = f.read(2)
            assert header == b'MZ'
        with z.open(expected+'App/AppInfo/appinfo.ini') as f:
            content=f.read().decode('utf-8-sig')
            assert 'PackageVersion='+version+'.0' in content
    print('STATIC-VALIDATED ZIP', zippath, sha256(zippath))


def validate_installer(installer):
    installer = Path(installer)
    assert installer.name.endswith('.paf.exe') and installer.stat().st_size > 100_000
    machine = pe_machine(installer)
    assert machine in (0x14c, 0x8664), f'Unexpected installer PE machine {machine:x}'
    print('STATIC-VALIDATED installer PE', installer, sha256(installer))
    print('Installer actual install/upgrade/rollback behavior: NOT YET VERIFIED (manual Windows testing required)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage',type=Path)
    parser.add_argument('--zip',type=Path)
    parser.add_argument('--installer',type=Path)
    parser.add_argument('--version')
    args = parser.parse_args()
    if args.stage:
        if not args.version: parser.error('--version required with --stage')
        validate_stage(args.stage,args.version)
    if args.zip:
        if not args.version: parser.error('--version required with --zip')
        validate_zip(args.zip,args.version)
    if args.installer: validate_installer(args.installer)
    if not (args.stage or args.zip or args.installer): parser.error('Provide --stage, --zip, or --installer')

if __name__ == '__main__':
    main()
