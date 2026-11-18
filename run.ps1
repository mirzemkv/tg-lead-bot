# Запуск бота на Windows: создаёт окружение, ставит зависимости и стартует.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install --quiet "aiohttp-socks>=0.9"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Создан .env. Впишите BOT_TOKEN и ADMIN_IDS и запустите скрипт снова."
    exit 1
}

& .\.venv\Scripts\python.exe -m app
