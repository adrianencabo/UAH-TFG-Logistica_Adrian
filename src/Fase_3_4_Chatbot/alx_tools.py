import os
import time
import shutil
import re
import urllib3
import xlwings as xw
import pandas as pd
from typing import List, Dict, Any, Union

from langchain.tools import tool
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Assuming openapi_client is available in the environment path or installed.
import openapi_client
from openapi_client.rest import ApiException

# Constants
SERVER_IP = "alxserver.aut.uah.es"
SERVER_URL = f"https://{SERVER_IP}:443/api/v1"
API_KEY = "c184f1ab-9f13-484c-a1c1-3d543502da6e"

SCENARIOS_DIR = r"C:\Users\Luis\Downloads\TFG\FASE 3 Y 4\Chatbot\Archivos"
RESULTS_DIR = r"C:\Users\Luis\Downloads\TFG\FASE 3 Y 4\Chatbot\Resultados_IA"

# Disable warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_api_instance():
    """Helper function to configure and return the AnyLogistix API instance."""
    configuration = openapi_client.Configuration(host=SERVER_URL)
    configuration.api_key['ApiKey'] = API_KEY
    configuration.verify_ssl = False
    api_client = openapi_client.ApiClient(configuration)
    return openapi_client.OpenApiApi(api_client)

@tool
def open_and_get_project(project_name: str) -> Union[int, str]:
    """
    Opens an AnyLogistix project by its name and returns the project ID.
    You must call this before interacting with scenarios to ensure the project is open.
    
    Args:
        project_name (str): The exact name of the project to open (e.g., 'TFG_ADRIAN_ENCABO').
        
    Returns:
        int: The project ID.
        str: Error message if failed.
    """
    api_instance = get_api_instance()
    try:
        project = api_instance.find_and_open_project_by_name(True, project_name)
        return project.id
    except ApiException as e:
        return f"API Exception: {e}"
    except Exception as e:
        return f"Error: {e}"

@tool
def get_scenarios_list(project_id: int) -> Union[List[Dict[str, Any]], str]:
    """
    Retrieves the list of scenarios available within a specific project.
    
    Args:
        project_id (int): The ID of the open project.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing 'id', 'name', and 'type' of each scenario.
        str: Error message if failed.
    """
    api_instance = get_api_instance()
    try:
        scenarios = api_instance.get_scenarios(project_id)
        return [{"id": s.id, "name": s.name, "type": s.type} for s in scenarios]
    except Exception as e:
        return f"Error: {e}"

@tool
def run_simulation(project_id: int, scenario_id: int) -> Union[int, str]:
    """
    Finds the 'SIMULATION' experiment for a given scenario and executes it synchronously.
    
    Args:
        project_id (int): The ID of the open project.
        scenario_id (int): The ID of the scenario to simulate.
        
    Returns:
        int: The experiment result ID, which is needed to export dashboard results.
        str: Error message if failed.
    """
    api_instance = get_api_instance()
    try:
        run_configurations = api_instance.get_experiments(project_id, scenario_id)
        sim_rc = next((r for r in run_configurations if r.type == 'SIMULATION'), None)
        
        if not sim_rc:
            return "Error: No SIMULATION experiment found for this scenario."
            
        sim_result = api_instance.run_experiment_synchronously(sim_rc.id)
        
        # Check if the simulation failed validation before starting
        validation_status = getattr(sim_result, 'validation_status', None)
        if validation_status == 'FAILED' or validation_status == 'ERROR':
            errors = getattr(sim_result, 'validation_errors', [])
            if errors:
                err_msg = "; ".join([getattr(e, 'message', str(e)) for e in errors])
                return f"Error: Simulation failed validation. Reason: {err_msg}"
            return "Error: Simulation failed validation with unknown errors."
            
        result_id = getattr(sim_result, 'experiment_result_id', None)
        return result_id if result_id is not None else "Error: No experiment_result_id returned."
    except Exception as e:
        return f"Error: {e}"

@tool
def export_simulation_results(experiment_result_id: int, scenario_name: str, is_modified: bool = False) -> str:
    """
    Exports all available dashboard pages for a given simulation result ID,
    consolidates them into a single Excel file with multiple tabs, and cleans up the temporary files.
    
    Args:
        experiment_result_id (int): The ID of the simulation result.
        scenario_name (str): The name of the scenario to include in the file name.
        is_modified (bool): Whether the scenario being exported is the AI modified version or the original.
        
    Returns:
        str: The absolute path to the consolidated Excel file, or an error message.
    """
    api_instance = get_api_instance()
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        
    # Clean the scenario name for file saving
    safe_scenario_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', scenario_name)
    version = "Modified" if is_modified else "Original"
    consolidated_path = os.path.join(RESULTS_DIR, f"KPIs_{safe_scenario_name}_{version}_{experiment_result_id}.xlsx")
    temp_files = []
    
    try:
        dashboard_pages = api_instance.get_experiment_dashboard_pages(experiment_result_id)
        
        if not dashboard_pages:
            return "Error: No dashboard pages found for this simulation result. Please configure statistics in AnyLogistix."
            
        # Read all valid dataframes first to avoid opening an empty ExcelWriter
        valid_dfs = {}
        for page in dashboard_pages:
            safe_page_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', page.name)
            temp_filename = f"temp_{safe_page_name}.xlsx"
            temp_path = os.path.join(RESULTS_DIR, temp_filename)
            
            excel_export = api_instance.export_dashboard_page(experiment_result_id, page.id)
            
            if isinstance(excel_export, str) and os.path.exists(excel_export):
                shutil.move(excel_export, temp_path)
                temp_files.append(temp_path)
            elif isinstance(excel_export, bytes):
                with open(temp_path, "wb") as file:
                    file.write(excel_export)
                temp_files.append(temp_path)
            
            try:
                df = pd.read_excel(temp_path)
                sheet_name = safe_page_name[:31]  # Excel limits sheet names to 31 chars
                valid_dfs[sheet_name] = df
            except Exception as e:
                pass  # Skip if pandas fails to read the temp file
                
        if not valid_dfs:
            return "Error: Exported dashboards were empty or unreadable. Please ensure the scenario has active dashboards with data."
            
        with pd.ExcelWriter(consolidated_path, engine='openpyxl') as writer:
            for sheet_name, df in valid_dfs.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
                
        return consolidated_path
    except Exception as e:
        error_str = str(e)
        if "because \\\"run\\\" is null" in error_str or "run is null" in error_str:
            return "Error: The simulation failed on the AnyLogistix server and produced no data. Please verify the scenario is valid and runnable."
        return f"Error: {e}"

@tool
def analyze_kpis(consolidated_excel_path: str) -> str:
    """
    Reads a consolidated simulation results Excel file and extracts key performance indicators (KPIs).
    It returns a text summary of the main metrics found (Service Level, Profit, Lead Time, etc.)
    so the AI can make decisions based on the actual data.
    
    Args:
        consolidated_excel_path (str): The path to the consolidated Excel results file.
        
    Returns:
        str: A summary of the extracted metrics (averages and sums).
    """
    if not os.path.exists(consolidated_excel_path):
        return "Error: File does not exist."
        
    summary = []
    try:
        xls = pd.ExcelFile(consolidated_excel_path)
        
        for sheet in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet)
                
                # Special parsing for ALX dashboards (which have "Statistics name", "Time", "Value")
                if 'Statistics name' in df.values:
                    # Find the header row
                    header_row_idx = df[df.eq('Statistics name').any(axis=1)].index[0]
                    clean_df = df.iloc[header_row_idx+1:].copy()
                    clean_df.columns = df.iloc[header_row_idx]
                    
                    if 'Value' in clean_df.columns and 'Statistics name' in clean_df.columns:
                        clean_df['Value'] = pd.to_numeric(clean_df['Value'], errors='coerce')
                        sheet_summary = [f"--- Dashboard: {sheet} ---"]
                        
                        grouped = clean_df.groupby('Statistics name')['Value'].agg(['mean', 'sum']).reset_index()
                        
                        revenue_sum = 0
                        cost_sum = 0
                        
                        for _, row in grouped.iterrows():
                            stat_name = str(row['Statistics name']).strip()
                            avg_val = row['mean']
                            sum_val = row['sum']
                            sheet_summary.append(f"- {stat_name}: Average = {avg_val:.2f}, Total Sum = {sum_val:.2f}")
                            
                            if stat_name.lower() == 'revenue':
                                revenue_sum = sum_val
                            elif stat_name.lower() == 'total cost':
                                cost_sum = sum_val
                                
                        if revenue_sum > 0 and cost_sum > 0:
                            net_profit = revenue_sum - cost_sum
                            sheet_summary.append(f"- **NET PROFIT (Calculated)**: {net_profit:.2f}")
                            
                        summary.extend(sheet_summary)
                        continue
                        
                # Fallback for generic numeric columns
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                numeric_cols = df.select_dtypes(include='number').columns
                if not numeric_cols.empty:
                    valid_metrics_found = False
                    sheet_summary = [f"--- Dashboard: {sheet} ---"]
                    
                    for col in numeric_cols:
                        if str(col).lower() in ['id', 'iteration', 'replication', 'period']:
                            continue
                            
                        if not df[col].isna().all():
                            avg_val = df[col].mean()
                            sum_val = df[col].sum()
                            sheet_summary.append(f"- Column {col}: Average = {avg_val:.2f}, Total Sum = {sum_val:.2f}")
                            valid_metrics_found = True
                            
                    if valid_metrics_found:
                        summary.extend(sheet_summary)
            except Exception as e:
                pass
                
        return "\n".join(summary) if summary else "No numeric KPIs found."
    except Exception as e:
        return f"Error analyzing KPIs: {e}"

@tool
def modify_scenario_excel(original_excel_path: str, decision_index: int, new_scenario_name: str) -> str:
    """
    Applies an AI decision to modify an existing scenario Excel file using Microsoft Excel (xlwings).
    
    Args:
        original_excel_path (str): The absolute path to the base scenario Excel file.
        decision_index (int): 
            0 = Increase Demand by 20%
            1 = Decrease Transport Costs by 15%
            2 = Increase Safety Stock by 10%
        new_scenario_name (str): The name of the new scenario. Used for the output file name.
        
    Returns:
        str: The absolute path to the modified Excel file, or an error message.
    """
    # 1. FORCE ABSOLUTE PATHS
    original_excel_path = os.path.abspath(original_excel_path)
    
    if not os.path.exists(original_excel_path):
        return "Error: Original Excel file does not exist."
        
    if not os.path.exists(SCENARIOS_DIR):
        os.makedirs(SCENARIOS_DIR)
        
    safe_scenario_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', new_scenario_name)
        
    # 2. UNIQUE FILENAME to prevent Excel from blocking overwrites
    modified_excel_path = os.path.join(SCENARIOS_DIR, f"{safe_scenario_name}_Decision_{decision_index}_{int(time.time())}.xlsx")
    
    try:
        shutil.copy2(original_excel_path, modified_excel_path)
    except Exception as e:
        return f"Error copying file: {e}"
        
    app = xw.App(visible=False)
    # 3. SILENCE POP-UPS THAT FREEZE THE BOT
    app.display_alerts = False 
    app.screen_updating = False
    
    try:
        wb = app.books.open(modified_excel_path)
        changes_made = 0 # Inicializamos
        
        if decision_index == 0:
            ws = wb.sheets['Demand']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            
            for r in range(2, last_row + 1):
                row_vals = ws.range((r, 1), (r, last_col)).value
                if not isinstance(row_vals, list):
                    row_vals = [row_vals]
                    
                for i, val in enumerate(row_vals):
                    if isinstance(val, str) and val.strip().lower() == 'quantity':
                        # We found 'Quantity', now look at the next 5 columns to find its numeric values (Min/Max or Exact)
                        for j in range(i + 1, min(i + 6, len(row_vals))):
                            cell_val = row_vals[j]
                            # Only scale valid demand values (ignore 1.0 which might be Minimum Split Ratio)
                            if isinstance(cell_val, (int, float)) and cell_val > 1.0:
                                ws.range((r, j + 1)).value = cell_val * 1.20
                                changes_made += 1
                        break
        
        elif decision_index == 1:
            ws = wb.sheets['Paths']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            
            for r in range(2, last_row + 1):
                row_vals = ws.range((r, 1), (r, last_col)).value
                if not isinstance(row_vals, list):
                    row_vals = [row_vals]
                    
                for i, val in enumerate(row_vals):
                    if isinstance(val, str) and val.strip().lower() in ['cost', 'cost per unit', 'cost/unit']:
                        if i + 1 < len(row_vals):
                            current_val = row_vals[i + 1]
                            if isinstance(current_val, (int, float)):
                                ws.range((r, i + 2)).value = current_val * 0.85
                                changes_made += 1
                        break
                        
        elif decision_index == 2:
            ws = wb.sheets['Inventory']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            
            for r in range(2, last_row + 1):
                row_vals = ws.range((r, 1), (r, last_col)).value
                if not isinstance(row_vals, list):
                    row_vals = [row_vals]
                    
                for i, val in enumerate(row_vals):
                    if isinstance(val, str) and val.strip().lower() == 'safety stock':
                        if i + 1 < len(row_vals):
                            current_val = row_vals[i + 1]
                            if isinstance(current_val, (int, float)):
                                ws.range((r, i + 2)).value = current_val * 1.10
                                changes_made += 1
                        break

        # 4. SAFETY CHECK IF LOGIC FAILS
        if changes_made == 0:
            return "Error: Excel file opened, but 0 modifications were made. Check if the scenario format is correct."

        wb.save()
        return modified_excel_path
    except Exception as e:
        return f"Error during Excel modification: {e}"
    finally:
        try:
            wb.close()
        except:
            pass
        app.quit()
        # 5. GIVE WINDOWS TIME TO RELEASE THE FILE BEFORE UPLOADING
        time.sleep(1.5)

@tool
def upload_modified_scenario(project_id: int, file_path: str, new_scenario_name: str) -> Union[int, str]:
    """
    Uploads a modified scenario Excel file via the AnyLogistix API to create a new scenario.
    
    Args:
        project_id (int): The ID of the open project.
        file_path (str): The absolute path to the modified Excel file to upload.
        new_scenario_name (str): The name to assign to the newly created scenario.
        
    Returns:
        int: The new scenario ID after successful import.
        str: Error message if failed.
    """
    api_instance = get_api_instance()
    
    # Prevent duplicate name error in AnyLogistix
    unique_scenario_name = f"{new_scenario_name}_{int(time.time())}"
    
    try:
        import_response = api_instance.import_excel(
            new_scenario_name=unique_scenario_name,
            project_id=project_id,
            file=os.path.abspath(file_path),  # <- VERY IMPORTANT
            need_to_import_experiments=True
        )
        
        if not import_response.job_id:
            return "Error: No job_id received from AnyLogistix."
            
        while True:
            import_status = api_instance.get_import_status(import_response.job_id)
            if import_status.status in ['DONE', 'FAILED', 'CANCELED']:
                if import_status.status == 'DONE':
                    return import_status.scenario_id
                else:
                    err = getattr(import_status, 'error', 'Unknown error')
                    return f"Import failed with status {import_status.status}. Error: {err}"
            time.sleep(2)
            
    except Exception as e:
        return f"Error during scenario import: {e}"

@tool
def search_knowledge_base(query: str) -> str:
    """
    Searches the internal knowledge base (RAG) for information about logistics concepts,
    AnyLogistix configuration, or theoretical questions.
    Use this tool whenever the user asks "How to...", "What is...", or requests 
    theoretical guidance about logistics or AnyLogistix features.
    
    Args:
        query (str): The question or concept to search for in the database.
        
    Returns:
        str: Relevant text snippets from the official documentation to answer the query.
    """
    chroma_db_dir = r"C:\Users\Luis\Downloads\TFG\FASE 3 Y 4\Chatbot\chroma_db"
    if not os.path.exists(chroma_db_dir):
        return "Error: The knowledge database has not been built yet."
        
    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma(persist_directory=chroma_db_dir, embedding_function=embeddings)
        
        # Retrieve the top 3 most relevant chunks
        docs = vectorstore.similarity_search(query, k=3)
        if not docs:
            return "No relevant information found in the internal documents."
            
        result = "\n\n".join([f"Source ({doc.metadata.get('source', 'Unknown')}):\n{doc.page_content}" for doc in docs])
        return result
    except Exception as e:
        return f"Error searching the database: {e}"

# Export the tools for LangGraph/LangChain
alx_tools = [
    open_and_get_project,
    get_scenarios_list,
    run_simulation,
    export_simulation_results,
    analyze_kpis,
    modify_scenario_excel,
    upload_modified_scenario,
    search_knowledge_base
]
