"""Check runnable scripts and destructive-action boundaries without Docker data."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_platform_line_endings_and_powershell_encoding():
    for path in ROOT.rglob('*.sh'):
        if '.git' in path.parts or '.venv' in path.parts:
            continue
        assert b'\r' not in path.read_bytes(), str(path)
        if os.name != 'nt':
            assert path.stat().st_mode & 0o111, str(path)
    for name in ('start.bat', 'stop.bat', 'reset.bat'):
        raw = (ROOT / name).read_bytes()
        assert b'\r\n' in raw
        assert b'\n' not in raw.replace(b'\r\n', b'')
    for name in ('start.ps1', 'prepare-data.ps1'):
        assert (ROOT / 'scripts' / name).read_bytes().startswith(b'\xef\xbb\xbf')


@pytest.mark.skipif(os.name == 'nt' or not shutil.which('bash'), reason='POSIX Bash required')
def test_stop_reset_error_and_cancel_boundaries(tmp_path):
    work = tmp_path / 'path with spaces'
    work.mkdir()
    for name in ('stop.sh', 'reset.sh'):
        shutil.copy2(ROOT / name, work / name)
    fake = work / 'docker'
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> calls.txt\nexit 7\n')
    fake.chmod(0o755)
    env = {**os.environ, 'PATH': str(work) + os.pathsep + os.environ['PATH'], 'CONFIRMATION': 'RESET'}
    result = subprocess.run([str(work / 'reset.sh')], cwd=tmp_path, env=env, input='\n', text=True, capture_output=True)
    assert result.returncode == 0
    assert not (work / 'calls.txt').exists()
    for script, reply in (('stop.sh', ''), ('reset.sh', 'RESET\n')):
        result = subprocess.run([str(work / script)], cwd=tmp_path, env=env, input=reply, text=True, capture_output=True)
        assert result.returncode != 0
        assert 'Đã dừng hệ thống' not in result.stdout
        assert 'đã được đặt lại' not in result.stdout
    assert (work / 'calls.txt').read_text().splitlines() == [
        'compose -f docker-compose.yml stop',
        'compose -f docker-compose.yml down -v --remove-orphans',
    ]
