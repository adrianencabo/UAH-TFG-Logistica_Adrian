# Phase 2: Flat AI Integration and Scenario Modification

## Overview
This phase introduces a rule-based logic system, referred to as "Flat AI," designed to autonomously select predefined logistical decisions (e.g., modifying demand, altering transport costs). The objective is to clone a base scenario, apply the AI's selected modifications, and prepare the modified scenario for simulation.

## Execution Flow
The finalized execution flow, documented in the `ALX_API_ACCESS_TEST ONLY PHASE 2.ipynb` notebook, consists of the following steps:

1. **Flat AI Decision Logic:** The system evaluates predefined options and selects a specific action to alter the supply chain network.
2. **Scenario Cloning:** To preserve the integrity of the original data, the base scenario is cloned using `copy_scenario_synchronously`.
3. **Configuration Retrieval:** The script retrieves the appropriate `SIMULATION` run configurations for the newly cloned scenario.
4. **Data Modification (Excel Import):** The scenario data is updated using a locally modified Excel file, overriding the cloned scenario's tables.

## Technical Pivot: Native API vs. Excel Import
During development, two distinct approaches were evaluated for modifying scenario parameters. The technical challenges encountered dictated a pivot in the methodology.

### Path B: Native API Variation (Discarded)
Initial attempts (documented in the `4.b` notebooks) focused on using native API calls to retrieve specific tables, modify cell values programmatically, and push them back to the server. 
**Failure Context:** This approach was ultimately discarded. The API strictly manages data objects, but more importantly, it does not support exporting a complete scenario into an Excel file natively. The API only permits exporting post-simulation dashboards, making it impossible to perform full native data manipulation and extract the modified tables for offline validation.

### Path A: Excel Import Method (Implemented Solution)
The project pivoted to modifying the scenarios via Excel files (documented in the `4.a` notebooks).
**Technical Constraints & Workarounds:** * **Manual Export Requirement:** Because the API cannot export scenario data, the baseline Excel file must be exported manually from the AnyLogistix graphical interface before the Python script can modify it.
* **Strict Format Validation:** The `import_excel_existing` API method enforces a zero-tolerance policy on format deviations. The imported Excel files must perfectly match the internal AnyLogistix schema. Any structural discrepancy results in immediate API rejection. 

Despite these constraints, Path A was successfully implemented, allowing the Flat AI to push modified Excel files directly into the cloned scenarios to trigger new simulations.

## Directory Structure
To maintain a clear development history, this directory contains both the final working solutions and the deprecated experimental notebooks:

* **Final Implementations:**
  * `ALX_API_ACCESS_TEST ONLY PHASE 2.ipynb`: Streamlined notebook containing only the successful Phase 2 logic (Path A).
  * `ALX_API_ACCESS_TEST PHASE 2.ipynb`: Consolidated notebook merging Phase 1 extraction with Phase 2 modification.
* **Development and Troubleshooting:**
  * `ALX_API_ACCESS_TEST 4.a.*`: Iterations of the Excel import method, detailing the debugging process of strict format validations.
  * `ALX_API_ACCESS_TEST 4.b.*`: Deprecated attempts utilizing the Native API variation method.
* **Documentation:**
  * Corresponding `.pdf` exports for all notebooks to ensure readability without a Jupyter environment.
