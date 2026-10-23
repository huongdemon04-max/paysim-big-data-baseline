"""Execute launcher control flow in real PowerShell; Docker calls are a test double."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PS = shutil.which('powershell.exe') or shutil.which('powershell')

@unittest.skipUnless(PS, 'PowerShell is not installed')
class WindowsLauncherTests(unittest.TestCase):
    def test_success_failure_and_resource_selection(self):
        for scenario in ('standard', 'light', 'daemon', 'compose', 'memory', 'build', 'browser'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory(prefix='paysim windows ') as folder:
                root = Path(folder); (root / 'scripts').mkdir()
                shutil.copy(ROOT / 'scripts/start.ps1', root / 'scripts/start.ps1')
                (root / 'scripts/prepare-data.ps1').write_text('exit 0')
                runner = root / 'runner.ps1'
                runner.write_text('''[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$global:Scenario = 'SCENARIO'
function global:docker {
    $a = $args -join ' '
    Add-Content -Path "$PSScriptRoot/calls.txt" -Value $a
    $global:LASTEXITCODE = 0
    if ($a -eq 'info') { if ($global:Scenario -eq 'daemon') { $global:LASTEXITCODE=1 }; return }
    if ($a -eq 'compose up --help') { '--wait-timeout'; return }
    if ($a -like '*Architecture*') { 'x86_64'; return }
    if ($a -like '*MemTotal*') {
        switch ($global:Scenario) { 'light' { '4000000000' } 'memory' { '2000000000' } default { '8000000000' } }; return
    }
    if ($a -like '*config --quiet*' -and $global:Scenario -eq 'compose') { $global:LASTEXITCODE=1 }
    if ($a -like '*up -d*' -and $global:Scenario -eq 'build') { 'BUILD_FAILURE_SENTINEL'; $global:LASTEXITCODE=1 }
    if ($a -like '*logs*') { 'diagnostic log' }
}
function global:Start-Process { if ($global:Scenario -eq 'browser') { throw 'no default browser' } }
& "$PSScriptRoot/scripts/start.ps1"
exit $LASTEXITCODE
'''.replace('SCENARIO', scenario), encoding='utf-8-sig')
                script = str(runner)
                if os.name != 'nt' and PS.endswith('.exe'):
                    script = subprocess.check_output(['wslpath', '-w', script], text=True).strip()
                result = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
                output = result.stdout.decode('utf-8', errors='replace')
                success = scenario in ('standard', 'light', 'browser')
                self.assertEqual(result.returncode, 0 if success else 1, output)
                self.assertTrue((root/'calls.txt').exists(), output)
                calls = (root/'calls.txt').read_text(encoding='utf-8-sig')
                self.assertEqual('up -d' in calls, scenario in ('standard','light','build','browser'))
                if scenario == 'light': self.assertIn('docker-compose.low-memory.yml up', calls)
                if scenario == 'build':
                    report = (root/'startup-diagnostics.txt').read_text(encoding='utf-16')
                    self.assertIn('BUILD_FAILURE_SENTINEL', report)
                    self.assertIn('Compose startup exit code: 1', report)
