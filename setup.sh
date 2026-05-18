#!/bin/bash

set -e

echo "Installing backend dependencies..."

cd backend

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r ../requirements.txt

cd ../frontend

echo "Installing frontend dependencies..."
npm install

echo "Setup complete."
echo ""
echo "Run backend:"
echo "  ./run_backend.sh"
echo ""
echo "Run poller:"
echo "  ./run_poller.sh"
echo ""
echo "Run frontend:"
echo "  ./run_frontend.sh" 