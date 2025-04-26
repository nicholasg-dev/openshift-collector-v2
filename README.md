# OpenShift Collector v3

A web application for automated collection, documentation, and export of OpenShift 4.x cluster configuration and infrastructure details.

## Overview

OpenShift Collector v3 automates the gathering of both logical and physical configuration data from OpenShift clusters. It provides a web interface and API for collecting, viewing, and exporting comprehensive cluster documentation.

## Key Features

- **Automated Data Collection**: Gathers cluster, node, operator, storage, network, security, metrics, and event data using `oc` commands and APIs.
- **Scheduler**: Background collection jobs with configurable intervals, manual triggers, and persistent history/statistics.
- **Export Functionality**: Generate and download cluster documentation as PDF or JSON, including section-specific exports.
- **Configuration Management**: API and UI for updating/viewing config (kubeconfig, parallel jobs, cloud/SSH collection, etc).
- **Legacy & v2 API Endpoints**: Maintains backward compatibility while supporting new, richer endpoints.
- **Health Check**: `/health` endpoint for monitoring.
- **Extensible Frontend**: Web UI for dashboard, metrics, namespaces, storage, security, export, and more.

## Project Structure

```
├── app/
│   ├── __init__.py            # Flask app factory
│   ├── routes.py              # Web routes and API endpoints
│   ├── scheduler.py           # Background collection scheduler & API
│   ├── export.py              # Export/report generation & API
│   ├── collector/             # Core data collection logic
│   ├── static/                # Static assets (JS, CSS)
│   └── templates/             # Jinja2 HTML templates
├── instance/
│   ├── config.py.example      # Example instance configuration
│   └── config.py              # (User-specific, not version controlled)
├── config.py                  # General app config
├── requirements.txt           # Python dependencies
├── run.py                     # App entrypoint
├── tests/                     # Test stubs
└── README.md
```

## Requirements

- Python 3.8+
- OpenShift CLI (`oc`) configured to access the target cluster
- A valid `kubeconfig` file
- (Optional) Cloud provider CLI/SDKs for cloud infrastructure collection
- (Optional) SSH access for hardware-level data

## Installation & Setup

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd OpenShift Collector v3
   ```
2. **Create a virtual environment (recommended):**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Configure the application:**
   - Copy the example instance configuration:
     ```sh
     cp instance/config.py.example instance/config.py
     ```
   - Edit `instance/config.py` to set your kubeconfig path and other settings (cloud, SSH, etc).
   - Review `config.py` for global settings.

5. **Run the application:**
   ```sh
   python run.py
   ```
   The app will be available at http://localhost:5000

## Usage

- Access the web UI for dashboard, metrics, namespaces, storage, security, and export features.
- Use the API for programmatic access:
  - `/api/v2/cluster`, `/api/v2/nodes`, `/api/v2/operators`, `/api/v2/namespaces`, etc.
  - `/api/v2/collection-status`, `/api/v2/run-collection`, `/api/v2/update-interval`, `/api/v2/configuration`
  - `/api/v2/export/report`, `/api/v2/exports`, `/api/v2/export/<section>`
- Download generated documentation and exports from the web UI or via API endpoints.

## Advanced Features

- **Scheduler**: Configure background collection intervals and view collection history/statistics.
- **Export**: Generate PDF/JSON documentation for the whole cluster or specific sections.
- **Configurable**: Enable/disable cloud or SSH collection, set parallel jobs, and more via config or API.

## Testing & Quality Assurance

- Automated tests are implemented using `pytest` and `pytest-mock`.
- Unit tests cover helper functions, parsing logic, and configuration loading (with subprocess and file I/O mocking).
- Integration tests use Flask's test client to validate API endpoints and workflows, with mocking for external dependencies.
- To run all tests:
  ```sh
  pytest
  ```

## Roadmap & Improvements

- **Transition to Direct API Calls:**
  - The project is migrating from subprocess-based `oc` calls to direct use of the Kubernetes and OpenShift Python clients (`kubernetes`, `openshift`).
  - See `app/k8s_client.py` for the new API-based collection approach.
- **Enhanced Error Handling:**
  - Error handling is being improved across collection, scheduling, export, and API logic.
  - User-facing errors and logs are being made more informative and robust.

## Development Notes

- Legacy API endpoints (`/api/cluster`, `/api/nodes`) are retained for backward compatibility.
- Persistent runtime data (history, exports, collected data) is stored in the `instance/` directory.
- Logging and error handling are improved throughout the codebase.
- Automated testing and mocking are in place to ensure code quality and prevent regressions.
- The codebase is transitioning to direct Kubernetes/OpenShift API usage for improved reliability and maintainability.

## Contributing

Contributions are welcome! Please open issues or pull requests for bugs, features, or improvements.

## License

[Specify your license here]

---
*This application is under active development. Features and documentation will be updated as the project progresses.*
