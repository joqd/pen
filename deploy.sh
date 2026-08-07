#!/usr/bin/env bash
# Run this on your laptop to build and push the image to Docker Hub.
#
# Usage:
#   ./deploy.sh v1.0.0

set -euo pipefail

DOCKERHUB_USERNAME="rodxa"
IMAGE_NAME="pen"
TAG="${1:?Please enter a version, example: ./deploy.sh v1.0.0}"

FULL_IMAGE="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"

echo "==> Building ${FULL_IMAGE}:${TAG} ..."
docker build -t "${FULL_IMAGE}:${TAG}" -t "${FULL_IMAGE}:latest" .

echo "==> Pushing ${FULL_IMAGE}:${TAG} ..."
docker push "${FULL_IMAGE}:${TAG}"

echo "==> Pushing ${FULL_IMAGE}:latest ..."
docker push "${FULL_IMAGE}:latest"

echo "${TAG}" > .version

echo ""
echo "==> Done. Deploy this tag on the server: ${TAG}"
echo "==> Saved to .version"