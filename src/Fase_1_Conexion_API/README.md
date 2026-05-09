# Phase 1: API Connection and Data Extraction

## Overview
This phase establishes the foundational communication between the local Python environment (Jupyter Notebook) and the AnyLogistix Virtual Machine server. The primary goal is to autonomously navigate the server's directory, execute a predefined simulation, and retrieve the generated analytics.

## Execution Flow
The successful execution of this phase, documented in the final Jupyter Notebook (`ALX_API_ACCESS_TEST 1.Final.ipynb`), follows these sequential steps:

1. **Authentication and Project Retrieval:** Bypassing SSL restrictions to authenticate the user and retrieve the list of accessible projects.
2. **Scenario and Run Configuration Selection:** Locating the base scenario (e.g., *P4.2.6 SIM Distribution Network*) and automatically identifying its `SIMULATION` run configuration.
3. **Synchronous Execution:** Triggering the simulation on the server side and waiting for the completion status (`run_experiment_synchronously`).
4. **Data Extraction:** Querying the server for the newly generated Dashboard pages and their dynamic IDs.

## Key Technical Challenge & Resolution: Dashboard Export Limitation
A significant technical limitation was discovered during the final data extraction step. The AnyLogistix API method `export_dashboard_page` does not support exporting a complete scenario's results into a single consolidated Excel workbook. Instead, it strictly allows the exportation of a single dashboard page per API call.

**The Solution:**
To prevent data loss and fully automate the extraction process, the final code block was modified. A loop was implemented to iterate through the `dashboard_pages` array. For each page detected, the script dynamically extracts its specific `page.id`, makes an individual API call, and saves the binary response as a distinct Excel file locally. 

This programmatic approach ensures that all simulated metrics (Financial, Operational, Lead Time, etc.) are successfully downloaded as a collection of separate `.xlsx` files without requiring manual intervention.

## Directory Structure
* `ALX_API_ACCESS_TEST 1.Final.ipynb`: The definitive and fully functional notebook that completes Phase 1 successfully.
* `ALX_API_ACCESS_TEST 1.Final.pdf`: PDF export of the final notebook execution for documentation purposes.
* `ALX_API_ACCESS_TEST 1.pdf`: Previous iteration logging initial connection attempts and early ID errors.
