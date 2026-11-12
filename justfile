# Lock onto the exact OS directory and store it in $curr to bypass PowerShell's '[' and ']' bugs
set shell := ["powershell.exe", "-NoProfile", "-NoLogo", "-Command", "$curr = [Environment]::CurrentDirectory; Set-Location -LiteralPath $curr;"]

# Define variables for paths
venv := ".venv"
python := venv + "\\Scripts\\python.exe"
openi := venv + "\\Scripts\\openi.exe"

# PyTorch versions
torch_version := "2.14.0"  # make sure to keep the version synced with pyproject.toml
torchvision_version := "0.29.0"
cuda_tag := "cu126"

# Typing 'just' by itself will list all available commands
default:
    @just --list

# Setup the venv install all required dependencies (CPU only)
setup: (_install "cpu")

# Setup the venv install all required dependencies (NVIDIA GPU)
setup-gpu: (_install cuda_tag)

# Sets up the virtual environment, installs dependencies, and configures git hooks
_install backend:
    @Write-Host "-> Creating virtual environment..." -ForegroundColor Yellow
    if (-not [System.IO.File]::Exists("$curr\{{python}}")) { python -m venv "{{venv}}" }
    @Write-Host "-> Upgrading pip..." -ForegroundColor Yellow
    {{python}} -m pip install --upgrade pip --quiet
    @Write-Host "-> Installing PyTorch ({{backend}})..." -ForegroundColor Yellow
    {{python}} -m pip install torch=={{torch_version}} torchvision=={{torchvision_version}} --index-url https://download.pytorch.org/whl/{{backend}}
    @Write-Host "-> Installing OpenI and dev tools..." -ForegroundColor Yellow
    & "$curr\{{python}}" -m pip install -e ".[dev]"
    @Write-Host "-> Configuring pre-commit hooks..." -ForegroundColor Yellow
    & "$curr\{{python}}" -m pre_commit install
    & "$curr\{{python}}" -m pre_commit install --hook-type commit-msg
    @Write-Host "=== Setup Complete! ===" -ForegroundColor Green
    @Write-Host "Activate your environment" -ForegroundColor Red
    @Write-Host "Alternatively, simply use 'just run' or 'just format'" -ForegroundColor Green


# Runs the main OpenI application
run:
    {{python}} -m openi

# Runs Ruff to format and lint the codebase manually
format:
    & "$curr\{{python}}" -m ruff check --fix .
    & "$curr\{{python}}" -m ruff format .

# Installs any new dependencies added to pyproject.toml
sync:
    {{python}} -m pip install -e ".[dev]"

# Completely removes the virtual environment to start fresh
clean:
    @Write-Host "-> Removing virtual environment..." -ForegroundColor Red
    if ([System.IO.Directory]::Exists("$curr\{{venv}}")) { Remove-Item -LiteralPath "$curr\{{venv}}" -Recurse -Force }
