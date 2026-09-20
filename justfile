# Set PowerShell as the default shell for running these commands
set shell := ["powershell.exe", "-NoProfile", "-c"]

# Define variables for paths (use double backslashes for Windows paths)
venv := ".venv"
python := venv + "\\Scripts\\python"
precommit := venv + "\\Scripts\\pre-commit"
ruff := venv + "\\Scripts\\ruff"
openi := venv + "\\Scripts\\openi"

# Typing 'just' by itself will list all available commands
default:
    @just --list

# Sets up the virtual environment, installs dependencies, and configures git hooks
setup:
    @Write-Host "-> Creating virtual environment..." -ForegroundColor Yellow
    python -m venv {{venv}}
    @Write-Host "-> Upgrading pip..." -ForegroundColor Yellow
    {{python}} -m pip install --upgrade pip --quiet
    @Write-Host "-> Installing OpenI and dev tools..." -ForegroundColor Yellow
    {{python}} -m pip install -e ".[dev]"
    @Write-Host "-> Configuring pre-commit hooks..." -ForegroundColor Yellow
    {{precommit}} install
    {{precommit}} install --hook-type commit-msg
    @Write-Host "=== Setup Complete! ===" -ForegroundColor Green
    @Write-Host "Activate your environment" -ForegroundColor Red
    @Write-Host "Alternatively, simply use 'just run' or 'just format'" -ForegroundColor Green

setup-gpu: setup
    @Write-Host "-> Installing CUDA PyTorch..." -ForegroundColor Yellow
    {{python}} -m pip install torch==2.14.0 torchvision==0.29.0 --index-url https://download.pytorch.org/whl/cu126 --force-reinstall --no-deps
    @Write-Host "=== GPU Setup Complete! ===" -ForegroundColor Green

# Runs the main OpenI application
run:
    {{openi}}

# Runs Ruff to format and lint the codebase manually
format:
    {{ruff}} check --fix .
    {{ruff}} format .

# Completely removes the virtual environment to start fresh
clean:
    @Write-Host "-> Removing virtual environment..." -ForegroundColor Red
    if (Test-Path {{venv}}) { Remove-Item -Recurse -Force {{venv}} }
