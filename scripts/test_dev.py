"""Host-side regression for dev.ps1 using an isolated mock Docker command.

Requires Windows PowerShell, never contacts the real Docker Engine.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which("powershell.exe")

MOCK = r'''
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$global:LASTEXITCODE = 0
function Record($Kind, $Values) {
    @{kind=$Kind; args=@($Values)} | ConvertTo-Json -Compress | Add-Content -Encoding UTF8 $env:SHAD_MOCK_LOG
}
function global:docker {
    $argv = @($args)
    Record 'docker' $argv
    $global:LASTEXITCODE = 0
    if (($env:SHAD_MOCK_FAIL -eq 'engine' -and $argv[0] -eq 'info') -or
        ($env:SHAD_MOCK_FAIL -eq 'up' -and $argv -contains 'up') -or
        ($env:SHAD_MOCK_FAIL -eq 'backend-tests' -and $argv -contains 'run' -and $argv -contains 'api-tests')) {
        $global:LASTEXITCODE = 19
        return
    }
    if ($argv[0] -eq 'info') { Write-Output 'linux' }
    if ($argv.Count -gt 1 -and $argv[1] -eq 'version') { Write-Output 'Docker Compose v2.40.3' }
}
function global:Invoke-RestMethod {
    param($Uri, [int]$TimeoutSec)
    Record 'ready' @($Uri)
    return @{status='ready'}
}
function global:Invoke-WebRequest {
    param($Uri, [switch]$UseBasicParsing, [int]$TimeoutSec)
    Record 'page' @($Uri)
    return @{Content='<div id="app"></div>'}
}
'''


@unittest.skipUnless(SHELL, "Windows PowerShell is required")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / ".tmp" / ("dev-script-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        self.caller = self.directory / "caller"
        self.caller.mkdir()
        for name in ("dev.ps1", ".env.example", "docker-compose.yml"):
            shutil.copyfile(ROOT / name, self.directory / name)
        self.log = self.directory / "calls.jsonl"

    def run_script(self, command="up", failure="", rest=()):
        arguments = [command, *rest]
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        source = MOCK + "\n$ErrorActionPreference = 'Stop'\n$invokeArgs = @("
        source += ",".join(map(quote, arguments)) + ")\n& " + quote(self.directory / "dev.ps1") + " @invokeArgs\n"
        source += "$result = $LASTEXITCODE\nRecord 'cwd' @((Get-Location).Path)\nexit $result\n"
        wrapper = self.directory / "invoke.ps1"
        wrapper.write_text(source, encoding="utf-8-sig")
        env = os.environ.copy()
        # Isolate the settings priority from a caller's unrelated environment.
        for key in ("COMPOSE_PROJECT_NAME", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
                    "POSTGRES_TEST_DB", "CORE_JWT_SECRET", "SHAD_HTTP_PORT", "SHAD_API_PORT", "SHAD_DB_PORT"):
            env.pop(key, None)
        env.update(SHAD_MOCK_LOG=str(self.log), SHAD_MOCK_FAIL=failure)
        return subprocess.run([SHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper)],
                              cwd=self.caller, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=30)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line.lstrip("\ufeff")) for line in self.log.read_text(encoding="utf-8-sig").splitlines()]

    def docker_calls(self):
        return [row["args"] for row in self.calls() if row["kind"] == "docker"]

    def test_up_waits_for_health_checks_http_and_restores_working_directory(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.docker_calls()
        self.assertTrue(any("up" in argv and "--wait" in argv and "--build" in argv for argv in commands))
        self.assertTrue(any(row["kind"] == "ready" for row in self.calls()))
        self.assertTrue(any(row["kind"] == "page" for row in self.calls()))
        self.assertEqual(self.calls()[-1]["args"], [str(self.caller)])
        content = (self.directory / ".env").read_text(encoding="utf-8")
        self.assertNotIn("__GENERATE__", content)
        for key in ("POSTGRES_PASSWORD", "CORE_JWT_SECRET"):
            secret = next(line.split("=", 1)[1] for line in content.splitlines() if line.startswith(key + "="))
            self.assertGreaterEqual(len(secret), 48)
            self.assertNotIn(secret, result.stdout + result.stderr)

    def test_init_preserves_existing_credentials_byte_for_byte(self):
        self.assertEqual(self.run_script("init").returncode, 0)
        path = self.directory / ".env"
        original = path.read_bytes() + b"\n# user preference\n"
        path.write_bytes(original)
        self.assertEqual(self.run_script("init").returncode, 0)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.docker_calls(), [])

    def test_engine_failure_stops_before_config_creation_and_up(self):
        result = self.run_script(failure="engine")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.directory / ".env").exists())
        self.assertFalse(any("up" in argv for argv in self.docker_calls()))

    def test_failed_up_is_not_reported_as_ready(self):
        result = self.run_script(failure="up")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(row["kind"] == "ready" for row in self.calls()))

    def test_down_keeps_volumes(self):
        result = self.run_script("down")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.docker_calls()[-1][-1], "down")
        self.assertFalse(any("-v" in argv or "--volumes" in argv or "prune" in argv for argv in self.docker_calls()))

    def test_check_does_not_require_engine(self):
        result = self.run_script("check", failure="engine")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any("info" in argv for argv in self.docker_calls()))
        self.assertEqual(self.docker_calls()[-1][-2:], ["config", "-q"])

    def test_test_command_runs_both_suites_and_forwards_pytest_filter(self):
        result = self.run_script("test", rest=("-k", "security"))
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.docker_calls()
        backend = next(argv for argv in commands if "run" in argv and "api-tests" in argv)
        self.assertEqual(backend[-6:], ["python", "-m", "pytest", "-q", "-k", "security"])
        self.assertTrue(any("run" in argv and "frontend-tests" in argv for argv in commands))
        self.assertTrue(any("/docker-entrypoint-initdb.d/01-test-database.sh" in argv for argv in commands))
        self.assertFalse(any("" in argv for argv in commands))

    def test_backend_test_failure_is_propagated_without_running_frontend(self):
        result = self.run_script("test", failure="backend-tests")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("run" in argv and "frontend-tests" in argv for argv in self.docker_calls()))

    def test_shared_work_and_test_database_are_rejected(self):
        self.assertEqual(self.run_script("init").returncode, 0)
        path = self.directory / ".env"
        content = path.read_text(encoding="utf-8").replace("POSTGRES_TEST_DB=shad_tutoring_test", "POSTGRES_TEST_DB=shad_tutoring")
        path.write_text(content, encoding="utf-8")
        result = self.run_script("check")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("config" in argv for argv in self.docker_calls()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
