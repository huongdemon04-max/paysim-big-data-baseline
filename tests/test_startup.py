"""Readiness and launcher regression checks; no real Docker resources touched."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("healthcheck", ROOT / "hadoop/healthcheck.py")
healthcheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(healthcheck)


class ReadinessTests(unittest.TestCase):
    def test_writable_cluster_with_a_live_datanode(self):
        healthcheck.check_readiness({"beans": [{"Safemode": "", "LiveNodes": '{"datanode:9866": {}}'}]})

    def test_http_success_alone_is_not_readiness(self):
        for payload in (
            {"beans": []},
            {"beans": [{"Safemode": "Safe mode is ON", "LiveNodes": '{"node": {}}'}]},
            {"beans": [{"Safemode": "", "LiveNodes": "{}"}]},
            {"beans": [{"LiveNodes": '{"node": {}}'}]},
            {"beans": [{"Safemode": "", "LiveNodes": "invalid JSON"}]},
        ):
            with self.subTest(payload=payload), self.assertRaises((ValueError, KeyError)):
                healthcheck.check_readiness(payload)


@unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "POSIX Bash harness; Windows uses launcher tests")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(ROOT / "start.sh", self.root / "start.sh")
        (self.root / "scripts").mkdir()
        (self.root / "scripts/prepare-data.sh").write_text("touch data-prepared\n")
        (self.root / "bin").mkdir()
        docker = self.root / "bin/docker"
        docker.write_text('''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open('calls.jsonl', 'a') as f:
    f.write(json.dumps([args, os.environ.get('DOCKER_DEFAULT_PLATFORM'), os.environ.get('COMPOSE_PARALLEL_LIMIT')]) + '\\n')
if args and args[0] == 'compose':
    while '-f' in args:
        index = args.index('-f')
        del args[index:index + 2]
if args == ['info']:
    sys.exit(int(os.environ.get('DAEMON_EXIT', '0')))
elif args[:2] == ['info', '--format']:
    if args[2] == '{{.Architecture}}': print(os.environ.get('ARCH', 'aarch64'))
    elif args[2] == '{{.MemTotal}}': print(os.environ.get('MEMORY', '8000000000'))
    else: print('architecture=aarch64 cpus=4 memory=8000000000')
elif args == ['compose', 'up', '--help']:
    print(('--wait-timeout\\n' + 'help\\n' * 100000) if os.environ.get('LARGE_HELP') == '1' else ('--wait-timeout' if os.environ.get('OLD_COMPOSE') != '1' else '--detach'))
elif args == ['compose', 'config', '--quiet']:
    sys.exit(int(os.environ.get('CONFIG_EXIT', '0')))
elif args[:3] == ['compose', 'up', '-d']:
    if os.environ.get('UP_EXIT') == '1': print('BUILD_FAILURE_SENTINEL', file=sys.stderr)
    sys.exit(int(os.environ.get('UP_EXIT', '0')))
elif args[:3] == ['compose', 'ps', '-aq']: print('test-namenode')
elif args[:2] == ['compose', 'logs']: print('NameNode failure details')
elif args[0] == 'inspect': print('restart=3 OOMKilled=false')
''')
        docker.chmod(0o755)

    def run_launcher(self, **env):
        return subprocess.run(
            ["bash", "start.sh"], cwd=self.root, text=True, capture_output=True,
            env={**os.environ, "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}", **env},
            timeout=15,
        )

    def calls(self):
        return [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]

    def test_native_platform_overrides_forced_foreign_architecture(self):
        for arch, platform in (("aarch64", "linux/arm64"), ("x86_64", "linux/amd64")):
            with self.subTest(arch=arch):
                result = self.run_launcher(ARCH=arch, DOCKER_DEFAULT_PLATFORM="linux/386")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                up = [c for c in self.calls() if "up" in c[0] and "-d" in c[0]][-1]
                self.assertEqual(up[1], platform)
                self.assertIn("--wait", up[0])
                self.assertIn("--wait-timeout", up[0])

    def test_four_gb_uses_light_mode_and_six_gb_uses_standard(self):
        for memory, light in (("3500000000", True), ("4000000000", True),
                              ("5499999999", True), ("5500000000", False),
                              ("8000000000", False)):
            with self.subTest(memory=memory):
                result = self.run_launcher(MEMORY=memory)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                up = [c for c in self.calls() if "up" in c[0] and "-d" in c[0]][-1]
                self.assertEqual("docker-compose.low-memory.yml" in up[0], light)
                if light:
                    self.assertEqual(up[2], "1")
                    self.assertIn("chế độ nhẹ", result.stdout)

    def test_light_mode_failure_uses_same_configuration_for_diagnostics(self):
        result = self.run_launcher(MEMORY="4000000000", UP_EXIT="1")
        self.assertEqual(result.returncode, 1)
        for call in self.calls():
            if "ps" in call[0] or "logs" in call[0]:
                self.assertIn("docker-compose.low-memory.yml", call[0])
        self.assertIn("NameNode failure details", (self.root / "startup-diagnostics.txt").read_text())

    def test_failure_keeps_exit_status_and_collects_evidence(self):
        result = self.run_launcher(UP_EXIT="1")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Hệ thống đã sẵn sàng", result.stdout)
        report = (self.root / "startup-diagnostics.txt").read_text()
        self.assertIn("NameNode failure details", report)
        self.assertIn("restart=3", report)
        self.assertIn("BUILD_FAILURE_SENTINEL", report)
        self.assertIn("Compose startup exit code: 1", report)
        self.assertFalse(any("down" in c[0] for c in self.calls()))

    def test_large_compose_help_does_not_trigger_sigpipe_failure(self):
        result = self.run_launcher(LARGE_HELP="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_preflight_stops_before_downloading_or_starting(self):
        for env in ({"MEMORY": "3499999999"}, {"DAEMON_EXIT": "1"}, {"OLD_COMPOSE": "1"}, {"CONFIG_EXIT": "1"}):
            with self.subTest(env=env):
                result = self.run_launcher(**env)
                self.assertEqual(result.returncode, 1)
                self.assertFalse((self.root / "data-prepared").exists())
                self.assertFalse(any("up" in c[0] and "-d" in c[0] for c in self.calls()))


if __name__ == "__main__":
    unittest.main()
