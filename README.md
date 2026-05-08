# UAH-TFG-Logistica_Adrian
## Configuration and Setup

To ensure the correct execution of the API client and avoid dependency conflicts, please follow these configuration steps carefully.

### 1. Prerequisites
* **Python 3.x**
* **Jupyter Notebook** (Note: It is highly recommended to launch Jupyter directly from the command line interface rather than using Anaconda Navigator to prevent environment conflicts).
* **AnyLogistix Account:** An active user account on the target AnyLogistix server with API access privileges.

### 2. Environment Dependencies
The AnyLogistix `openapi-client` has strict version requirements. Specifically, it conflicts with `pydantic >= 2.0`. You must downgrade this library before installing the client to ensure stability.

Open your terminal, navigate to the project root folder, and execute:

```bash
# 1. Install the specific pydantic version required by the API
pip install "pydantic<2,>=1.10.5"

# 2. Install the local AnyLogistix OpenAPI client
pip install -e ./openapi-python-client-3.3.1

3. API Connection Parameters
Once the environment is ready, open the Jupyter Notebooks (.ipynb). In the first execution block, you must configure your specific server and authentication parameters:
# Define the server host
SERVER_IP = "alxserver.aut.uah.es"
SERVER_URL = f"https://{SERVER_IP}:443/api/v1"

# Define your personal API Key (Generated from the AnyLogistix Web Profile)
API_KEY = "YOUR_API_KEY_HERE"
Security Note: The connection scripts include a bypass for SSL verification (configuration.verify_ssl = False) and disable InsecureRequestWarning. This is a required configuration to successfully communicate with the university's server via self-signed certificates.
