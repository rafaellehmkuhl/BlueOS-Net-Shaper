#!/bin/bash
# Multi-architecture build script for BlueOS Net Shaper
# Builds for: AMD64 (desktops), ARM64 (Pi 4/5)

set -e

IMAGE_NAME="rafaellehmkuhl/blueos-net-shaper"
VERSION="${1:-latest}"

echo "Building $IMAGE_NAME:$VERSION for multiple architectures..."

# Try to use multiarch builder, create if it fails
if ! docker buildx use multiarch 2>/dev/null; then
    echo "Creating buildx builder 'multiarch'..."
    docker buildx create --name multiarch --use
    docker buildx inspect --bootstrap
else
    echo "Using existing buildx builder 'multiarch'..."
fi

# Build and push for multiple platforms
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t "$IMAGE_NAME:$VERSION" \
    --push \
    .

echo "✓ Successfully built and pushed $IMAGE_NAME:$VERSION"
echo "  Architectures: linux/amd64, linux/arm64"

