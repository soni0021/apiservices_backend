#!/bin/bash
# Build script for Render deployment
set -e

echo "Installing dependencies..."
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

echo "Running database migrations..."
alembic upgrade head || echo "Migrations skipped (database may not be ready)"

echo "Build complete!"

