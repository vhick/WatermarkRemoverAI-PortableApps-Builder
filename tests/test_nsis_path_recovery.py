"""Regression tests for b1r1 NSIS MAX_PATH error and ZIP-only recovery."""
from pathlib import Path
import tempfile
import unittest

from scripts.check_nsis_paths import inspect_paths
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from repackage_from_ziponly import TAG_RE

ROOT = Path(__file__).resolve().parents[1]


class TestNSISPaths(unittest.TestCase):
    def test_short_portable_tree_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'WatermarkRemoverAIPortable'
            path = root / 'App' / 'WatermarkRemoverAI' / 'file.dll'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'real-file-bytes')
            length, worst, n = inspect_paths(root, 245)
            self.assertEqual(n, 1)
            self.assertEqual(worst, path)
            self.assertLessEqual(length, 245)

    def test_excessive_path_fails_without_deleting_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'WatermarkRemoverAIPortable'
            path = root / 'App' / ('python_' + 'p' * 48) / 'site-packages' / 'PySide6' / 'deep' / 'plugin.dll'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'keep')
            with self.assertRaisesRegex(RuntimeError, 'NSIS source path too long'):
                inspect_paths(root, 125)
            self.assertEqual(path.read_bytes(), b'keep')

    def test_tag_supports_exact_prior_b1r1_and_new_b1r2(self):
        for rev in ('b1r1','b1r2'):
            tag = f'portable-wmrai-v0.68.0-553b9bcfc2-{rev}-ziponly'
            match = TAG_RE.fullmatch(tag)
            self.assertIsNotNone(match)
            self.assertEqual(match.group(3), rev)
        self.assertIsNone(TAG_RE.fullmatch('portable-wmrai-v0.68.0-553b9bcfc2-b1r3-ziponly'))

    def test_workflows_stage_to_runner_temp(self):
        for name in ('build-portableapps.yml', 'installer-from-validated-zip.yml'):
            workflow = (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
            self.assertIn('${{ runner.temp }}\\w\\WatermarkRemoverAIPortable', workflow)
            self.assertIn('check_nsis_paths.py', workflow)
            self.assertNotIn('source-dir: work/', workflow)
            self.assertIn('Portable-Package-Builder@v1.0.0',workflow)


if __name__ == '__main__':
    unittest.main()
