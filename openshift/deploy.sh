#!/bin/bash

# Script to deploy OpenShift Collector v3 to an OpenShift cluster

# Default values
NAMESPACE="openshift-collector"
IMAGE_REPOSITORY="quay.io/yourusername"
IMAGE_TAG="latest"
SECRET_KEY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --namespace)
      NAMESPACE="$2"
      shift
      shift
      ;;
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
    --secret-key)
      SECRET_KEY="$2"
      shift
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --namespace NAMESPACE    Namespace to deploy to (default: openshift-collector)"
      echo "  --image-repo REPO        Image repository (default: quay.io/yourusername)"
      echo "  --image-tag TAG          Image tag (default: latest)"
      echo "  --secret-key KEY         Flask secret key (default: randomly generated)"
      echo "  --help                   Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Generate a random secret key if not provided
if [ -z "$SECRET_KEY" ]; then
  SECRET_KEY=$(openssl rand -base64 32)
  echo "Generated random SECRET_KEY"
fi

echo "Deploying OpenShift Collector v3 to namespace: $NAMESPACE"
echo "Using image: $IMAGE_REPOSITORY/openshift-collector:$IMAGE_TAG"

# Create namespace if it doesn't exist
oc get namespace $NAMESPACE > /dev/null 2>&1 || oc create namespace $NAMESPACE

# Apply RBAC, ConfigMap, PVC, Service, and Route
for file in rbac.yaml configmap.yaml pvc.yaml service.yaml route.yaml; do
  echo "Applying $file..."
  cat $file | sed "s|\${NAMESPACE}|$NAMESPACE|g" | oc apply -f - -n $NAMESPACE
done

# Apply Secret with the SECRET_KEY
echo "Applying secret.yaml with SECRET_KEY..."
cat secret.yaml | sed "s|change-me-in-production|$SECRET_KEY|g" | oc apply -f - -n $NAMESPACE

# Apply Deployment with image parameters
echo "Applying deployment.yaml..."
cat deployment.yaml | sed "s|\${NAMESPACE}|$NAMESPACE|g" | sed "s|\${IMAGE_REPOSITORY}|$IMAGE_REPOSITORY|g" | sed "s|\${IMAGE_TAG}|$IMAGE_TAG|g" | oc apply -f - -n $NAMESPACE

echo "Deployment complete!"
echo "Access the application at: https://$(oc get route openshift-collector -n $NAMESPACE -o jsonpath='{.spec.host}')"
