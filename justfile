# Set PowerShell as the default shell for running these commands
set shell := ["powershell.exe", "-NoProfile", "-c"]

# Define variables for paths (use double backslashes for Windows paths)
venv := ".venv"
python := venv + "\\Scripts\\python"
precommit := venv + "\\Scripts\\pre-commit"
ruff := venv + "\\Scripts\\ruff"
openi := venv + "\\Scripts\\openi"

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
    python -m venv {{venv}}
    @Write-Host "-> Upgrading pip..." -ForegroundColor Yellow
    {{python}} -m pip install --upgrade pip --quiet
    @Write-Host "-> Installing PyTorch ({{backend}})..." -ForegroundColor Yellow
    {{python}} -m pip install torch=={{torch_version}} torchvision=={{torchvision_version}} --index-url https://download.pytorch.org/whl/{{backend}}
    @Write-Host "-> Installing OpenI and dev tools..." -ForegroundColor Yellow
    {{python}} -m pip install -e ".[dev]"
    @Write-Host "-> Configuring pre-commit hooks..." -ForegroundColor Yellow
    {{precommit}} install
    {{precommit}} install --hook-type commit-msg
    @Write-Host "=== Setup Complete! ===" -ForegroundColor Green
    @Write-Host "Activate your environment" -ForegroundColor Red
    @Write-Host "Alternatively, simply use 'just run' or 'just format'" -ForegroundColor Green


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
