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

## 8. LLM Benchmarking and Quota Limitations
**Issue:** Selecting the optimal Large Language Model (LLM) for the LangChain agent required extensive benchmarking due to strict tool-calling formatting requirements, context window limitations, and billing constraints.
* *OpenAI / Gemini Pro:* Discarded due to mandatory billing configurations and restricted free-tier quotas.
* *Groq (Llama 3 8B / 70B):* Discarded. The 8B model failed to generate valid JSON structures required for LangChain tool calling (`tool_use_failed` errors) and hit severe Tokens-Per-Minute (6000 TPM) limits. The 70B model formatted correctly but instantly depleted the daily token allowance (100k/day) due to the massive conversation history.
**Solution:** The system architecture was definitively pivoted to **Google Gemini 2.5 Flash**. This model offers a massive 1,000,000 token context window, perfectly handling the extensive chat history and AnyLogistix simulation logs without truncation. The only limitation (20 Requests Per Minute) is programmatically managed by catching the HTTP 429 error, pausing the execution for 60 seconds, and resuming the ReAct reasoning loop.

## 9. Dynamic File Upload and Formatting Strictness
**Issue:** During the implementation of the UI drag-and-drop file upload feature, the AnyLogistix API rejected the modified Excel templates.
**Root Causes & Solutions:**
* *Extension Loss:* Chainlit stored temporary files without the `.xlsx` extension. Since the AnyLogistix API has zero-tolerance for format deviations, the backend logic (`alx_tools.py`) was updated to force the `.xlsx` extension on all uploaded files.
* *Dynamic Headers:* The structural schema of the AnyLogistix tables varies slightly depending on the export. The Python parsing logic was updated to dynamically search for headers across rows 1 and 2, ensuring `xlwings` injects the AI-modified parameters into the exact correct cells regardless of minor structural shifts.
