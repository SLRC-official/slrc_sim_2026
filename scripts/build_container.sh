#!/bin/bash
set -e

# Build the container
echo "Building Docker image 'slrc_bridge'..."
# Run from workspace root
cd "$(dirname "$0")/.."
docker build -t slrc_bridge -f docker/Dockerfile .
