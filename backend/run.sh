#!/bin/bash

# Video Downloader Backend Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Video Downloader Backend Starting..."

# Check if .env exists, if not create from .env.example
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please update .env with your configuration"
fi

# Create venv if it doesn't exist
if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Create storage directory
mkdir -p ./storage

# Run the application
echo "Starting FastAPI server on http://0.0.0.0:8000"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
