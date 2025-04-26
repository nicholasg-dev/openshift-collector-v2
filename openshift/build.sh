#!/bin/bash

# Script to build and push the OpenShift Collector v3 container image

# Default values
IMAGE_REPOSITORY="quay.io/yourusername"
IMAGE_TAG="latest"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --image-repo)
      IMAGE_REPOSITORY="$2"
      shift
      shift
      ;;
    --image-tag)
      IMAGE_TAG="$2"
      shift
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --image-repo REPO        Image repository (default: quay.io/yourusername)"
      echo "  --image-tag TAG          Image tag (default: latest)"
      echo "  --help                   Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Navigate to the project root
cd "$(dirname "$0")/.."

echo "Building image: $IMAGE_REPOSITORY/openshift-collector:$IMAGE_TAG"

# Build the container image
docker build -t $IMAGE_REPOSITORY/openshift-collector:$IMAGE_TAG .

# Push the image to the registry
echo "Pushing image to registry..."
docker push $IMAGE_REPOSITORY/openshift-collector:$IMAGE_TAG

echo "Build and push complete!"
