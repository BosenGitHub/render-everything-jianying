#!/usr/bin/env python3
"""Offline structural/packaging tests; no external API or draft runtime."""
import argparse
import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--skill-path', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
sys.path.insert(0, str(args.skill_path / 'scripts'))
import validate_timeline as validator
import package_draft as packager

class SkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # Structural path fixture only: this test does not decode image pixels.
        self.image = self.root / 'fixture.png'
        self.image.write_bytes(b'structural-path-fixture')
        self.payload = {
            'schema_version': 1, 'title': 'fixture', 'width': 1080,
            'height': 1920, 'fps': 30, 'verified': True,
            'chatcut_project_id': 'fixture-project',
            'chatcut_timeline_id': 'fixture-timeline',
            'tracks': [
                {'name': 'V1', 'type': 'video', 'items': [
                    {'file': str(self.image), 'target_start_us': 0, 'duration_us': 1000000}]},
                {'name': 'captions', 'type': 'text', 'items': [
                    {'text': 'caption', 'target_start_us': 0, 'duration_us': 1000000}]}
            ]}
    def tearDown(self):
        self.temp.cleanup()
    def check(self, payload):
        report = validator.Report()
        result = validator.validate_timeline(payload, report)
        return report, result
    def test_valid_timeline(self):
        report, result = self.check(self.payload)
        self.assertEqual(report.errors, [])
        self.assertEqual(result, (2, 1000000))
    def test_unverified_rejected(self):
        self.payload['verified'] = False
        self.assertTrue(self.check(self.payload)[0].errors)
    def test_overlap_rejected(self):
        item = copy.deepcopy(self.payload['tracks'][0]['items'][0])
        item['target_start_us'] = 500000
        self.payload['tracks'][0]['items'].append(item)
        self.assertTrue(self.check(self.payload)[0].errors)
    def test_primary_start_rejected(self):
        self.payload['tracks'][0]['items'][0]['target_start_us'] = 1
        self.assertTrue(self.check(self.payload)[0].errors)
    def test_relative_path_rejected(self):
        self.payload['tracks'][0]['items'][0]['file'] = 'fixture.png'
        self.assertTrue(self.check(self.payload)[0].errors)
    def test_unknown_field_rejected(self):
        self.payload['unexpected'] = True
        self.assertTrue(self.check(self.payload)[0].errors)
    def test_draft_validation(self):
        draft = self.root / 'draft_content.json'
        draft.write_text(json.dumps({'canvas_config': {'width': 1080, 'height': 1920},
            'duration': 1000000, 'tracks': [{'type': 'video', 'segments': []}],
            'materials': {}}))
        report = validator.Report()
        validator.validate_draft(draft, 1000000, report)
        self.assertEqual(report.errors, [])
    def test_package_deterministic(self):
        draft = self.root / 'draft'
        draft.mkdir()
        (draft / 'draft_content.json').write_text('{}')
        (draft / 'caption.txt').write_text('caption')
        first, second = self.root / 'one.zip', self.root / 'two.zip'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(packager.main([str(draft), '-o', str(first)]), 0)
            self.assertEqual(packager.main([str(draft), '-o', str(second)]), 0)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {'draft_content.json', 'caption.txt'})
    def test_missing_draft_rejected(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(packager.main([str(self.root), '-o', str(self.root / 'missing.zip')]), 1)

if __name__ == '__main__':
    result = unittest.TextTestRunner(stream=io.StringIO()).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SkillTests))
    if result.wasSuccessful():
        print(f'TESTS={result.testsRun} PASS')
    else:
        print(f'TESTS={result.testsRun} FAIL')
        for test, trace in result.errors + result.failures:
            print(test, trace)
    raise SystemExit(0 if result.wasSuccessful() else 1)
