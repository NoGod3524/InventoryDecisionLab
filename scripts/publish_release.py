"""Publish only an exact verified commit; never replace an existing version."""
import json
import os
from pathlib import Path
import re
import subprocess


class ReleaseError(RuntimeError):
    pass


def api(endpoint, *, missing_ok=False, fields=None):
    command = ['gh', 'api', '--include', endpoint]
    if fields is not None:
        command += ['--method', 'POST']
        for key, value in fields.items():
            command += ['-f', f'{key}={value}']
    result = subprocess.run(command, capture_output=True, text=True)
    # --include exposes the actual HTTP status; connection/auth errors are not absence.
    match = re.match(r'HTTP/\S+ (\d{3})[^\n]*\n(?:[^\n]+\n)*?\n', result.stdout)
    if not match:
        raise ReleaseError(f'No valid HTTP response for {endpoint}: {result.stderr.strip()}')
    status = int(match.group(1))
    if status == 404 and missing_ok:
        return None
    if result.returncode or not 200 <= status < 300:
        raise ReleaseError(f'GitHub API failed ({status}) for {endpoint}: {result.stderr.strip()}')
    try:
        return json.loads(result.stdout[match.end():])
    except ValueError as error:
        raise ReleaseError(f'Invalid JSON response for {endpoint}') from error


def tag_commit(repository, version):
    ref = api(f'repos/{repository}/git/ref/tags/{version}', missing_ok=True)
    if ref is None:
        return None
    obj = ref['object']
    visited = set()
    while obj['type'] == 'tag':
        sha = obj['sha']
        if sha in visited or len(visited) >= 32:
            raise ReleaseError('Cyclic or excessively nested annotated tag')
        visited.add(sha)
        obj = api(f'repos/{repository}/git/tags/{sha}')['object']
    if obj['type'] != 'commit':
        raise ReleaseError('Release tag does not resolve to a commit')
    return obj['sha']


def publish(version, repository, target):
    if not re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ReleaseError('Invalid version: expected vMAJOR.MINOR.PATCH')
    # Verify repository access before interpreting resource-specific 404 responses.
    api(f'repos/{repository}')
    published = tag_commit(repository, version)
    if published is not None and published != target:
        raise ReleaseError('Version tag points to a different commit; refusing to publish')
    release = api(f'repos/{repository}/releases/tags/{version}', missing_ok=True)
    if release is not None:
        if published != target or release.get('draft'):
            raise ReleaseError('Existing release is not a published exact-commit release')
        print('This exact commit is already released; no changes needed.')
        return
    if published is None:
        # Create explicitly; a concurrent conflicting tag causes a safe failure.
        api(f'repos/{repository}/git/refs', fields={'ref': f'refs/tags/{version}', 'sha': target})
    if tag_commit(repository, version) != target:
        raise ReleaseError('Tag changed before publication; refusing to publish')
    subprocess.run(['gh', 'release', 'create', version, '--verify-tag',
                    '--title', f'InventoryDecisionLab {version}',
                    '--notes-file', 'docs/release_notes.md'], check=True)
    if tag_commit(repository, version) != target:
        raise ReleaseError('Published tag no longer matches the verified commit')


def main():
    try:
        publish(Path('VERSION').read_text().strip(), os.environ['GITHUB_REPOSITORY'],
                os.environ['GITHUB_SHA'])
    except (ReleaseError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error


if __name__ == '__main__':
    main()
