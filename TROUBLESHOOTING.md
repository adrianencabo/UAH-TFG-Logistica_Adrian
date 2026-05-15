# Troubleshooting and Known Issues

This document outlines the primary technical challenges encountered during the development of the AnyLogistix API integration (Phases 1 and 2) and the Chatbot architecture (Phases 3 and 4), along with the implemented solutions. This record serves as a technical reference for environment debugging and API limitation handling.

## 1. Environment and Dependency Conflicts (Dependency Hell)
**Issue:** The AnyLogistix `openapi-client` strictly requires the `pydantic` library to be version `< 2.0` (specifically `>= 1.10.5`). However, modern versions of Anaconda Navigator require `pydantic >= 2.0` to launch the graphical interface. Attempting to satisfy both within the same `base` environment results in a conflict: upgrading `pydantic` breaks the API, while downgrading it breaks the Anaconda Navigator GUI.

**Solution:**
* The API requirement was prioritized to ensure the simulation scripts functioned correctly (`pip install "pydantic<2,>=1.10.5"`).
* To bypass the broken Anaconda Navigator GUI, Jupyter Notebook is launched directly via the Command Line Interface (CLI).
* *Execution:* As documented in the project setup, users must navigate to the working directory (`cd <project_path>`) and execute `jupyter notebook` in the terminal to launch the environment transparently.

## 2. Network and Connectivity Restrictions
**Issue:** Initial connection attempts to the Virtual Machine (`192.168.67.110`) resulted in `ConnectTimeoutError` and `Max retries exceeded`.
**Root Cause:** The university's internal VPN firewall restricted direct API requests to internal subnets from standard student accounts.
**Solution:** The infrastructure was updated to use a public domain (`alxserver.aut.uah.es`). Additionally, strict SSL verification was bypassed in the Python script (`configuration.verify_ssl = False`) to prevent connection drops caused by the university's self-signed certificates.

## 3. Data Extraction Errors (HTTP 500)
**Issue:** During Phase 1, the `export_dashboard_page` method periodically returned an HTTP 500 Internal Server Error (`Cannot invoke... getCharts() because dashboardPage is null`).
**Root Cause:** Early iterations of the script used hardcoded `experiment_result_id` values. Because AnyLogistix generates distinct and unique IDs for every simulation run, the hardcoded IDs quickly became obsolete, resulting in access denial.
**Solution:** The extraction logic was rewritten to dynamically capture the `experiment_result_id` and `dashboard_page.id` immediately after the synchronous simulation completes, ensuring the API always requests currently valid data.

## 4. Scenario Modification Limitations (Excel Import strictness)
**Issue:** During Phase 2, attempts to programmatically modify scenario tables and re-upload them failed with severe type validation errors (e.g., `type_error.none.not_allowed`).
**Root Cause:** The AnyLogistix API `import_excel_existing` method enforces a zero-tolerance format validation. The imported Excel must flawlessly match the platform's internal schema. Furthermore, the Native API does not support exporting full scenarios to Excel, preventing the Python script from generating a valid baseline template autonomously.
**Solution:** A hybrid approach (Path A) was adopted. The baseline scenario Excel must be manually exported via the AnyLogistix graphical interface once. The Python script then securely parses this pristine template, applies the Flat AI modifications, and uploads it via the API to trigger the cloned simulation.

## 5. Local Excel Dependency (xlwings)
**Issue:** The chosen library for modifying the baseline scenario templates (`xlwings`) requires a local installation of Microsoft Excel to function, unlike other lightweight parsing libraries like `pandas`.
**Solution:** It is documented as a system requirement that the machine hosting the chatbot server must have Microsoft Excel installed. This trade-off was accepted because `xlwings` guarantees that the strict internal XML formatting of the AnyLogistix templates remains intact during modification.

## 6. Chainlit Asynchronous Handling
**Issue:** The AnyLogistix simulations are synchronous and computationally heavy. Waiting for a simulation to finish caused the Chainlit web interface to freeze, degrading the user experience.
**Solution:** Asynchronous wrappers and Chainlit's task processing callbacks (`cl.Step`) were implemented. This allows the UI to remain responsive and provide the user with real-time visual logs indicating that the simulation is currently running on the server.

## 7. Credential Security (.env)
**Issue:** Hardcoding the AnyLogistix and LLM API keys in the source files poses a severe security risk when uploading the code to version control repositories like GitHub.
**Solution:** All sensitive credentials were extracted and isolated into a local `.env` file using the `python-dotenv` library. The `.env` file was explicitly added to the `.gitignore` rules to prevent accidental exposure.

## 8. LLM API Billing and Quota Limitations
**Issue:** During the development of the LangChain Agent (Phase 3), initial attempts to integrate OpenAI models (GPT-3.5/GPT-4) or the Google Gemini Pro model failed due to strict billing configuration requirements (credit card mandates) and restricted free-tier quotas.
**Solution:** The system architecture was pivoted to utilize `gemini-flash` (Gemini 1.5 Flash). This model offers a highly generous free tier suitable for academic development while maintaining the necessary speed, context window, and reasoning capabilities required for LangChain tool orchestration.
