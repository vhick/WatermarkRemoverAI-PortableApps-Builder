import sys
from pathlib import Path
import re
import unittest
import zipfile
import tempfile
from scripts.resolve_official import STABLE
from scripts.stage import pe_machine

ROOT = Path(__file__).resolve().parents[1]

class TestBuilder(unittest.TestCase):
    def test_numeric_semver(self):
        versions = ['v0.9.0','v0.12.0','v0.68.0','v0.4.100']
        sorted_versions=sorted(versions,key=lambda v:tuple(map(int,STABLE.fullmatch(v).groups())))
        self.assertEqual(sorted_versions[-1],'v0.68.0')
        self.assertIsNone(STABLE.fullmatch('v0.68.1-rc1'))
    def test_contract_refs(self):
        wf=(ROOT/'.github/workflows/build-portableapps.yml').read_text()
        self.assertIn('Portable-Package-Builder@v1.0.0',wf)
        self.assertIn('portable-release-publisher@v1.1.1',wf)
        self.assertNotIn('official-tool-url:',wf)
        self.assertIn('custom-nsis',wf)
    def test_no_host_cleanup(self):
        source=(ROOT/'launcher/WatermarkRemoverAIPortable.cs').read_text()
        self.assertIn('WMR_DATA_DIR',source)
        self.assertNotIn('Directory.Delete',source)
        self.assertNotIn('RegistryKey',source)
        self.assertIn('App\\WatermarkRemoverAI',source)
    def test_icon_signatures(self):
        self.assertTrue((ROOT/'branding/appicon.ico').read_bytes().startswith(b'\x00\x00\x01\x00'))
        self.assertTrue((ROOT/'branding/appicon_32.png').read_bytes().startswith(b'\x89PNG'))
    def test_no_binary_app_in_kit(self):
        self.assertFalse((ROOT/'App').exists())
        self.assertFalse(any(ROOT.glob('*.exe')))

if __name__=='__main__':unittest.main()

class TestIntegrityAndStaging(unittest.TestCase):
    def test_safe_extract_preserves_empty_dir(self):
        from scripts.stage import safe_extract
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            zpath=base/'upstream.zip'
            with zipfile.ZipFile(zpath,'w') as z:
                z.writestr('OfficialApp/empty/nested/', b'')
                z.writestr('OfficialApp/data.txt', b'tested')
            root=safe_extract(zpath,base/'output','OfficialApp')
            self.assertTrue((root/'empty/nested').is_dir())
            self.assertEqual((root/'data.txt').read_bytes(),b'tested')
    def test_safe_extract_rejects_traversal(self):
        from scripts.stage import safe_extract
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            with zipfile.ZipFile(base/'evil.zip','w') as z:
                z.writestr('OfficialApp/../outside.txt', b'data')
            with self.assertRaises(RuntimeError):
                safe_extract(base/'evil.zip',base/'out','OfficialApp')
            self.assertFalse((base/'outside.txt').exists())
    def test_safe_extract_rejects_case_collision(self):
        from scripts.stage import safe_extract
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            with zipfile.ZipFile(base/'collision.zip','w') as z:
                z.writestr('OfficialApp/a.txt', b'one')
                z.writestr('OfficialApp/A.txt', b'two')
            with self.assertRaisesRegex(RuntimeError,'collision'):
                safe_extract(base/'collision.zip',base/'out','OfficialApp')
    def test_deterministic_zip_and_data_only_empty(self):
        from scripts.stage import deterministic_zip, APP_NAME
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            stage=base/APP_NAME
            (stage/'App').mkdir(parents=True)
            (stage/'Data').mkdir()
            (stage/'App/test.txt').write_text('hello', encoding='utf-8')
            one=base/'one.zip';two=base/'two.zip'
            deterministic_zip(stage,one)
            deterministic_zip(stage,two)
            self.assertEqual(one.read_bytes(),two.read_bytes())
            with zipfile.ZipFile(one) as z:
                self.assertIn(APP_NAME+'/Data/',z.namelist())
                self.assertIn(APP_NAME+'/App/test.txt',z.namelist())
    def test_zip_rejects_injected_user_data(self):
        from scripts.stage import deterministic_zip, APP_NAME
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            stage=base/APP_NAME
            (stage/'Data').mkdir(parents=True)
            (stage/'Data/credentials.dat').write_text('secret',encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'Data must not'):
                deterministic_zip(stage,base/'unsafe.zip')
    def test_latest_skips_unsuitable_versions(self):
        from unittest.mock import patch
        from scripts.resolve_official import select_release
        dataset=[
            dict(tag_name='v0.70.0',draft=False,prerelease=False,assets=[dict(name='release-notes.txt')]),
            dict(tag_name='v0.68.0',draft=False,prerelease=False,assets=[dict(name='WatermarkRemover-AI-0.68.0-windows-x64-cpu.zip'),dict(name='SHA256SUMS.txt')]),
            dict(tag_name='v0.69.0-rc1',draft=False,prerelease=True,assets=[]),
        ]
        with patch('scripts.resolve_official.fetch_json',return_value=dataset):
            self.assertEqual(select_release('latest')['tag_name'],'v0.68.0')
