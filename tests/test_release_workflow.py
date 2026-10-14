"""Exercise the actual release shell block without publishing anything."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseWorkflowTests(unittest.TestCase):
    def run_release(self, mode, published_sha='abc123'):
        workflow = (ROOT / '.github/workflows/release.yml').read_text()
        script = workflow.rsplit('        run: |\n', 1)[1]
        script = '\n'.join(line[10:] for line in script.splitlines())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'VERSION').write_text('v1.0.0\n')
            gh = path / 'gh'
            gh.write_text('''#!/bin/sh
case "$1 $2" in
  "release view") [ "$TEST_MODE" != "new" ] ;;
  "api repos/example/repo/git/ref/tags/v1.0.0") printf '%s\\n' "$PUBLISHED_SHA" ;;
  "release create") echo created >> "$CALL_LOG" ;;
  *) echo "unexpected command: $*" >&2; exit 99 ;;
esac
''')
            gh.chmod(0o700)
            log = path / 'calls'
            env = dict(os.environ, PATH=f'{tmp}:{os.environ["PATH"]}',
                       TEST_MODE=mode, PUBLISHED_SHA=published_sha,
                       GITHUB_SHA='abc123', GITHUB_REPOSITORY='example/repo',
                       CALL_LOG=str(log))
            result = subprocess.run(['bash', '-c', script], cwd=tmp, env=env,
                                    capture_output=True, text=True)
            return result, log.read_text() if log.exists() else ''

    def test_new_version_is_published(self):
        result, calls = self.run_release('new')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, 'created\n')

    def test_same_commit_is_safe_noop(self):
        result, calls = self.run_release('existing')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('already released', result.stdout)
        self.assertEqual(calls, '')

    def test_different_commit_is_rejected(self):
        result, calls = self.run_release('existing', 'other456')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('different commit', result.stdout)
        self.assertEqual(calls, '')
