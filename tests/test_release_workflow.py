"""Execute production release logic against a stateful, offline GitHub CLI double."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from scripts.publish_release import publish, ReleaseError


class ReleaseWorkflowTests(unittest.TestCase):
    def run_release(self, tag=None, release=False, annotations=None, error=None,
                    version='v1.0.0', race=False):
        state = {'tag': tag, 'created': [], 'calls': []}
        annotations = annotations or {}
        def gh(command, **kwargs):
            state['calls'].append(command)
            if command[:3] == ['gh', 'release', 'create']:
                self.assertIn('--verify-tag', command)
                state['created'].append(state['tag'])
                return subprocess.CompletedProcess(command, 0)
            self.assertEqual(command[:3], ['gh', 'api', '--include'])
            endpoint = command[3]
            status, data = 200, {}
            if error and endpoint.endswith(error[0]):
                status = error[1]
                if status is None:
                    return subprocess.CompletedProcess(command, 1, '', 'network unavailable')
            elif '/git/ref/tags/' in endpoint:
                if state['tag'] is None: status = 404
                else: data = {'object': state['tag']}
            elif '/git/tags/' in endpoint:
                data = {'object': annotations[endpoint.rsplit('/', 1)[1]]}
            elif '/releases/tags/' in endpoint:
                if not release: status = 404
                else: data = {'draft': False}
            elif endpoint.endswith('/git/refs'):
                if race: status = 422
                else: state['tag'] = {'type': 'commit', 'sha': 'verified_commit'}
            output = f'HTTP/2.0 {status} status\nContent-Type: application/json\n\n' + json.dumps(data)
            return subprocess.CompletedProcess(command, 0 if status < 400 else 1, output, 'error' if status >= 400 else '')
        with patch('scripts.publish_release.subprocess.run', side_effect=gh):
            try:
                publish(version, 'test/repo', 'verified_commit')
                failure = None
            except ReleaseError as exc:
                failure = str(exc)
        return failure, state

    def test_workflow_executes_tested_helper(self):
        workflow = Path('.github/workflows/release.yml').read_text()
        self.assertIn('run: python3 scripts/publish_release.py', workflow)

    def test_new_version_creates_verified_tag_then_release(self):
        failure, state = self.run_release()
        self.assertIsNone(failure)
        self.assertEqual(state['created'], [{'type': 'commit', 'sha': 'verified_commit'}])

    def test_same_commit_is_noop(self):
        failure, state = self.run_release({'type': 'commit', 'sha': 'verified_commit'}, True)
        self.assertIsNone(failure)
        self.assertFalse(state['created'])

    def test_conflicting_tag_rejected_with_or_without_release(self):
        for release in (False, True):
            with self.subTest(release=release):
                failure, state = self.run_release({'type': 'commit', 'sha': 'wrong'}, release)
                self.assertIn('different commit', failure)
                self.assertFalse(state['created'])

    def test_annotated_and_nested_same_commit(self):
        annotations = {'outer': {'type': 'tag', 'sha': 'inner'},
                       'inner': {'type': 'commit', 'sha': 'verified_commit'}}
        for release in (False, True):
            with self.subTest(release=release):
                failure, state = self.run_release({'type': 'tag', 'sha': 'outer'}, release, annotations)
                self.assertIsNone(failure)
                self.assertEqual(len(state['created']), 0 if release else 1)

    def test_annotated_wrong_commit_rejected(self):
        failure, state = self.run_release({'type': 'tag', 'sha': 'outer'}, False,
                                         {'outer': {'type': 'commit', 'sha': 'wrong'}})
        self.assertIn('different commit', failure)
        self.assertFalse(state['created'])

    def test_annotation_cycle_rejected(self):
        failure, state = self.run_release({'type': 'tag', 'sha': 'loop'}, False,
                                         {'loop': {'type': 'tag', 'sha': 'loop'}})
        self.assertIn('Cyclic', failure)
        self.assertFalse(state['created'])

    def test_errors_are_not_absence(self):
        for endpoint in ('test/repo', 'git/ref/tags/v1.0.0', 'releases/tags/v1.0.0'):
            for status in (None, 401, 403, 500):
                with self.subTest(endpoint=endpoint, status=status):
                    failure, state = self.run_release(error=(endpoint, status))
                    self.assertIsNotNone(failure)
                    self.assertFalse(state['created'])

    def test_strict_versions_fail_before_network(self):
        for version in ('v1oops.2bad.3suffix', 'v1.2.3-extra', 'v01.2.3', '1.2.3', 'v1.2.3\nother'):
            with self.subTest(version=version):
                failure, state = self.run_release(version=version)
                self.assertIn('Invalid version', failure)
                self.assertFalse(state['calls'])

    def test_concurrent_tag_creation_fails_closed(self):
        failure, state = self.run_release(race=True)
        self.assertIsNotNone(failure)
        self.assertFalse(state['created'])
