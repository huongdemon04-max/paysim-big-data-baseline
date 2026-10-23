"""Batch wrappers run in Windows CMD against a native fake docker.exe."""
from pathlib import Path
import os
import subprocess, tempfile, shutil
import pytest

@pytest.mark.skipif(not shutil.which('powershell.exe') or not shutil.which('cmd.exe'), reason='Windows interop unavailable')
def test_stop_failure_reset_cancel_and_reset_failure():
    root=Path(__file__).resolve().parents[1]
    wtmp=subprocess.check_output(['powershell.exe','-NoProfile','-Command','[IO.Path]::GetTempPath()'],text=True).strip()
    ltmp=wtmp if os.name == 'nt' else subprocess.check_output(['wslpath','-u',wtmp],text=True).strip()
    results=[]
    with tempfile.TemporaryDirectory(prefix='paysim batch ',dir=ltmp) as td:
     p=Path(td)
     for file in ['start.bat','stop.bat','reset.bat']:shutil.copy(root/file,p/file)
     
     win=td if os.name == 'nt' else subprocess.check_output(['wslpath','-w',td],text=True).strip()
     source='public class Stub { public static int Main(string[] args) { return 7; } }'
     subprocess.run(['powershell.exe','-NoProfile','-Command',f"Add-Type -TypeDefinition '{source}' -OutputAssembly '{win}\\docker.exe' -OutputType ConsoleApplication"],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
     shutil.copy(p/'docker.exe', p/'powershell.exe')
     for script,inputs,expected in [('start.bat','\n',7),('stop.bat','\n',1),('reset.bat','NO\n\n',0),('reset.bat','\n\n',0),('reset.bat','RESET\n\n',1)]:
      (p/'runner.cmd').write_bytes((f'@echo off\r\nset "CONFIRMATION=RESET"\r\nset "PATH={win};%PATH%"\r\ncall "{win}\\{script}"\r\nexit /b %ERRORLEVEL%\r\n').encode())
      r=subprocess.run(['cmd.exe','/d','/c',win+'\\runner.cmd'],input=inputs.encode(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
      results.append(dict(script=script,input=inputs.strip(),exit_code=r.returncode,expected=expected,output=r.stdout.decode('utf-8',errors='replace')))
      assert r.returncode==expected,results[-1]
    assert len(results) == 5
