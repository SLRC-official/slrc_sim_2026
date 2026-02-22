#!/bin/bash
set -e

cd "$(dirname "$0")/.."

if ! command -v docker &>/dev/null; then
    echo "Docker not found. Installing docker.io..."
    sudo apt-get update
    sudo apt-get install -y docker.io
fi

if ! docker info &>/dev/null 2>&1; then
    echo "Docker daemon not accessible. Using sudo (add yourself to 'docker' group to avoid sudo: sudo usermod -aG docker $USER, then log out and back in)"
    DOCKER="sudo docker"
else
    DOCKER="docker"
fi

if [ ! -d "slrc" ]; then
    echo "Creating Python env 'slrc'..."
    python3 -m venv slrc
fi
echo "Installing Python dependencies..."
./slrc/bin/pip install -r requirements.txt -q

echo "Building Docker image 'slrc_bridge'..."
$DOCKER build -t slrc_bridge -f docker/Dockerfile .
