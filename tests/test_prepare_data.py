"""Download failures must not leave a partial CSV that looks ready."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(os.name == 'nt' or not shutil.which('bash'), reason='POSIX Bash harness')
@pytest.mark.parametrize('case', ['valid_existing', 'invalid_existing', 'download_ok', 'download_failed', 'bad_checksum'])
def test_prepare_data_atomicity(tmp_path, case):
    (tmp_path/'scripts').mkdir(); (tmp_path/'data').mkdir(); (tmp_path/'bin').mkdir()
    shutil.copy(ROOT/'scripts/prepare-data.sh', tmp_path/'scripts/prepare-data.sh')
    data = tmp_path/'data/paysim.csv'
    if case.endswith('existing'):
        data.write_text('valid' if case == 'valid_existing' else 'invalid')
    checksum = '16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b'
    commands = {
        'sha256sum': f'''#!/usr/bin/env python3
import pathlib,sys
print(('{checksum}' if pathlib.Path(sys.argv[1]).read_text() == 'valid' else '0'*64) + '  file')
''',
        'curl': '''#!/usr/bin/env python3
import os,pathlib,sys
pathlib.Path('curl-called').touch()
pathlib.Path(sys.argv[sys.argv.index('-o')+1]).write_text('valid' if os.environ['CASE'] == 'download_ok' else 'partial')
sys.exit(22 if os.environ['CASE'] == 'download_failed' else 0)
''',
    }
    for name, content in commands.items():
        binary = tmp_path/'bin'/name; binary.write_text(content); binary.chmod(0o755)
    result = subprocess.run(['bash', 'scripts/prepare-data.sh'], cwd=tmp_path, capture_output=True,
        env={**os.environ, 'PATH':f'{tmp_path / "bin"}:{os.environ["PATH"]}', 'CASE':case}, timeout=10)
    assert (result.returncode == 0) == (case in ('valid_existing', 'download_ok'))
    assert not (tmp_path/'data/paysim.csv.download').exists()
    if case.endswith('existing'): assert not (tmp_path/'curl-called').exists()
    if case in ('download_failed','bad_checksum'): assert not data.exists()
    if case == 'invalid_existing': assert data.read_text() == 'invalid'
