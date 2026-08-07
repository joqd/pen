#!/usr/bin/env bash
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

echo ""
echo "==> Done. Upload to the server with this tag: ${TAG}"