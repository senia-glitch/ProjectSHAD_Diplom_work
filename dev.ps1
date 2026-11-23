#requires -Version 5.1
# One-command Docker launcher; no local Python/Node installation is required.
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'stop', 'restart', 'build', 'logs', 'ps', 'test', 'shell', 'psql', 'migrate', 'init', 'check', 'help')]
    [string]$Command = 'up',
    [string]$EnvFile = '.env',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$settingsPath = if ([IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $projectRoot $EnvFile }
$composeBase = @('compose', '--project-directory', $projectRoot, '--env-file', $settingsPath, '-f', (Join-Path $projectRoot 'docker-compose.yml'))

function Invoke-Docker {
    param([string[]]$Arguments)
    $previousPreference = $ErrorActionPreference
    try {
        # Windows PowerShell may wrap native stderr as NativeCommandError.
        # Docker's exit status determines success, including when builds use stderr.
        $ErrorActionPreference = 'Continue'
        & docker @Arguments
        $code = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($code -ne 0) { throw "Команда Docker завершилась с кодом $code." }
}

function Invoke-Compose {
    param([string[]]$Arguments)
    Invoke-Docker -Arguments ($composeBase + $Arguments)
}

function Assert-Compose {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Не найден Docker. Установите Docker Desktop с Docker Compose.'
    }
    Invoke-Docker -Arguments @('compose', 'version') | Out-Null
}

function Assert-Engine {
    Assert-Compose
    try { $engineType = (Invoke-Docker -Arguments @('info', '--format', '{{.OSType}}') | Out-String).Trim() }
    catch { throw 'Docker Engine не отвечает. Запустите Docker Desktop и дождитесь готовности Engine.' }
    if ($engineType -ne 'linux') { throw 'Для проекта нужен Docker Desktop в режиме Linux containers.' }
}

function New-Secret {
    param([int]$Bytes)
    $data = New-Object byte[] $Bytes
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($data) }
    finally { $generator.Dispose() }
    return (($data | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Initialize-Settings {
    if (Test-Path -LiteralPath $settingsPath) { return }
    $content = [IO.File]::ReadAllText((Join-Path $projectRoot '.env.example'), [Text.Encoding]::UTF8)
    $content = $content.Replace('POSTGRES_PASSWORD=__GENERATE__', ('POSTGRES_PASSWORD=' + (New-Secret 24)))
    $content = $content.Replace('CORE_JWT_SECRET=__GENERATE__', ('CORE_JWT_SECRET=' + (New-Secret 32)))
    # CreateNew prevents a concurrent run from replacing existing credentials.
    $stream = New-Object IO.FileStream($settingsPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try {
        $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes($content)
        $stream.Write($bytes, 0, $bytes.Length)
    }
    finally { $stream.Dispose() }
    Write-Host 'Создан локальный файл настроек со случайными секретами. Существующие настройки сохраняются.'
}

function Get-Setting {
    param([string]$Key, [string]$Default = '')
    # Match Compose: process environment takes precedence over the env file.
    $processValue = [Environment]::GetEnvironmentVariable($Key)
    if ($null -ne $processValue) { return $processValue }
    $pattern = '^\s*' + [regex]::Escape($Key) + '\s*=\s*(.*?)\s*$'
    foreach ($line in [IO.File]::ReadAllLines($settingsPath, [Text.Encoding]::UTF8)) {
        if ($line -match $pattern) {
            $value = $Matches[1]
            if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") { return $Matches[1] }
            return ($value -replace '\s+#.*$', '').Trim()
        }
    }
    return $Default
}

function Test-Settings {
    foreach ($key in @('POSTGRES_USER', 'POSTGRES_DB', 'POSTGRES_TEST_DB')) {
        if ((Get-Setting $key) -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw "Некорректное значение $key в настройках." }
    }
    if ((Get-Setting 'POSTGRES_DB') -eq (Get-Setting 'POSTGRES_TEST_DB') -or (Get-Setting 'POSTGRES_TEST_DB') -notmatch 'test') {
        throw 'Тестовая БД должна отличаться от основной, её имя должно содержать test.'
    }
    if ((Get-Setting 'POSTGRES_PASSWORD') -notmatch '^[A-Za-z0-9_.~-]{16,}$') {
        throw 'Задайте POSTGRES_PASSWORD длиной от 16 символов: буквы, цифры или _ . ~ - (для URL подключения).'
    }
    if ([Text.Encoding]::UTF8.GetByteCount((Get-Setting 'CORE_JWT_SECRET')) -lt 32 -or (Get-Setting 'CORE_JWT_SECRET') -eq '__GENERATE__') {
        throw 'CORE_JWT_SECRET должен содержать не менее 32 байт. Существующий файл настроек не перезаписывается.'
    }
    $ports = @()
    foreach ($key in @('SHAD_HTTP_PORT', 'SHAD_API_PORT', 'SHAD_DB_PORT')) {
        $portValue = 0
        if (-not [int]::TryParse((Get-Setting $key), [ref]$portValue) -or $portValue -lt 1 -or $portValue -gt 65535) {
            throw "Некорректный порт $key в настройках."
        }
        if ($ports -contains $portValue) { throw 'Порты frontend, API и БД должны различаться.' }
        $ports += $portValue
    }
}

function Prepare-Compose {
    Initialize-Settings
    Test-Settings
    Invoke-Compose -Arguments @('config', '-q')
}

function Start-Project {
    Assert-Engine
    Prepare-Compose
    Invoke-Compose -Arguments @('up', '--detach', '--build', '--quiet-pull', '--wait', '--wait-timeout', '180')
    $webUrl = 'http://127.0.0.1:' + (Get-Setting 'SHAD_HTTP_PORT')
    $ready = Invoke-RestMethod ($webUrl + '/api/v1/ready') -TimeoutSec 10
    if ($ready.status -ne 'ready') { throw 'Не подтверждена готовность API и PostgreSQL через frontend-прокси.' }
    $page = Invoke-WebRequest $webUrl -UseBasicParsing -TimeoutSec 10
    if ($page.Content -notmatch '<div\s+id="app"') { throw 'Frontend не вернул страницу приложения.' }
    Write-Host ''
    Write-Host "Приложение: $webUrl"
    Write-Host "Документация API: $webUrl/docs"
    Write-Host ('API напрямую: http://127.0.0.1:' + (Get-Setting 'SHAD_API_PORT'))
    Write-Host 'Остановка с сохранением данных: .\dev.ps1 down'
}

function Show-Help {
@'
Запуск из любой папки: <путь к проекту>\dev.ps1 [команда]
  up         собрать и запустить весь проект; команда по умолчанию
  down       удалить контейнеры, сохранив тома PostgreSQL и журналов
  stop       остановить контейнеры
  restart    пересобрать изменённый код и запустить проект с сохранением данных
  build      собрать runtime-образы backend и frontend
  logs       следить за логами app/web; можно указать сервисы: logs db migrate
  ps         показать контейнеры и их состояние
  test       backend с отдельной тестовой БД и frontend; остаток аргументов — pytest
  migrate    отдельно применить проверенные миграции в Docker-БД
  shell      оболочка контейнера backend
  psql       консоль основной PostgreSQL в Docker
  init       создать отсутствующий .env со случайными секретами
  check      проверить конфигурацию Compose (Engine не требуется)
  help       эта справка
  -EnvFile   другой файл настроек; по умолчанию .env в корне проекта

Нужен Docker Desktop с Linux containers. Python и Node на Windows не требуются.
Пример: .\dev.ps1 up
'@ | Write-Host
}

Push-Location $projectRoot
try {
    switch ($Command) {
        'help' { Show-Help }
        'init' { Initialize-Settings; Test-Settings }
        'check' { Assert-Compose; Prepare-Compose; Write-Host 'Конфигурация Compose корректна.' }
        'up' { Start-Project }
        'restart' { Start-Project }
        'build' { Assert-Engine; Prepare-Compose; Invoke-Compose -Arguments @('build', 'app', 'web') }
        'down' { Assert-Engine; Prepare-Compose; Invoke-Compose -Arguments @('down') }
        'stop' { Assert-Engine; Prepare-Compose; Invoke-Compose -Arguments @('stop') }
        'ps' { Assert-Engine; Prepare-Compose; Invoke-Compose -Arguments @('ps', '--all') }
        'logs' {
            Assert-Engine; Prepare-Compose
            $services = if ($Rest -and $Rest.Count) { $Rest } else { @('app', 'web') }
            foreach ($service in $services) {
                if ($service -notin @('app', 'web', 'db', 'migrate', 'api-tests', 'frontend-tests')) { throw "Неизвестный сервис: $service" }
            }
            Invoke-Compose -Arguments (@('logs', '--follow', '--tail', '100') + $services)
        }
        'migrate' {
            Assert-Engine; Prepare-Compose
            Invoke-Compose -Arguments @('up', '--detach', '--wait', 'db')
            Invoke-Compose -Arguments @('run', '--rm', '--build', '--no-deps', 'migrate')
        }
        'test' {
            Assert-Engine; Prepare-Compose
            Invoke-Compose -Arguments @('up', '--detach', '--wait', 'db')
            # Also handles an existing volume without its test database; never resets it.
            Invoke-Compose -Arguments @('exec', '-T', 'db', 'sh', '/docker-entrypoint-initdb.d/01-test-database.sh')
            Invoke-Compose -Arguments @('--profile', 'test', 'build', 'api-tests', 'frontend-tests')
            Invoke-Compose -Arguments (@('--profile', 'test', 'run', '--rm', '--no-deps', 'api-tests', 'python', '-m', 'pytest', '-q') + $Rest)
            Invoke-Compose -Arguments @('--profile', 'test', 'run', '--rm', '--no-deps', 'frontend-tests')
        }
        'shell' { Assert-Engine; Prepare-Compose; Invoke-Compose -Arguments @('exec', 'app', 'sh') }
        'psql' {
            Assert-Engine; Prepare-Compose
            Invoke-Compose -Arguments @('exec', 'db', 'psql', '--username', (Get-Setting 'POSTGRES_USER'), '--dbname', (Get-Setting 'POSTGRES_DB'))
        }
    }
}
catch {
    Write-Error $_.Exception.Message -ErrorAction Continue
    exit 1
}
finally { Pop-Location }
