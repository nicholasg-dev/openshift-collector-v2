# OpenShift Collector v3 - OpenShift Deployment

This directory contains the necessary files to deploy OpenShift Collector v3 on an OpenShift cluster.

## Prerequisites

- Access to an OpenShift cluster with cluster-admin privileges
- Docker installed locally for building the container image
- `oc` command-line tool installed and configured

## Deployment Steps

### 1. Build and Push the Container Image

```bash
# Build and push the container image
./build.sh --image-repo quay.io/yourusername --image-tag v1.0.0
```

Replace `quay.io/yourusername` with your container registry and repository.

### 2. Deploy to OpenShift

```bash
# Deploy to OpenShift
./deploy.sh --namespace openshift-collector --image-repo quay.io/yourusername --image-tag v1.0.0
```

This will:
- Create a namespace (if it doesn't exist)
- Create a service account with necessary permissions
- Create ConfigMap and Secret for configuration
- Create a PersistentVolumeClaim for data storage
- Deploy the application
- Create a Service and Route for access

### 3. Access the Application

After deployment, the application will be accessible at the URL provided by the deploy script.

## Configuration

### ConfigMap

The ConfigMap `openshift-collector-config` contains the following configuration options:

- `collection-interval`: Interval in seconds between data collections (default: 3600)
- `parallel-jobs`: Number of parallel jobs for data collection (default: 4)
- `log-level`: Logging level (default: INFO)
- `namespaces-to-collect`: Comma-separated list of namespaces to collect detailed data for

### Secret

The Secret `openshift-collector-secrets` contains:

- `secret-key`: Flask secret key for session encryption

## Permissions

The application uses a ServiceAccount with a ClusterRole that grants read-only access to various OpenShift resources. Review the `rbac.yaml` file for details on the permissions granted.

## Persistent Storage

The application uses a PersistentVolumeClaim to store collected data and exports. The default size is 5Gi, which can be adjusted in the `pvc.yaml` file.

## Customization

You can customize the deployment by editing the YAML files in this directory before running the deploy script.

## Troubleshooting

If you encounter issues:

1. Check the pod logs:
   ```bash
   oc logs -f deployment/openshift-collector -n openshift-collector
   ```

2. Check the pod status:
   ```bash
   oc get pods -n openshift-collector
   ```

3. Check the service account permissions:
   ```bash
   oc describe clusterrolebinding openshift-collector-rolebinding
   ```
