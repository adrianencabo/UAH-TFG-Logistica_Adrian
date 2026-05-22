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
        result_id = getattr(sim_result, 'experiment_result_id', None)
        return result_id if result_id is not None else "Error: No experiment_result_id returned."
    except Exception as e:
        return f"Error: {e}"
@tool
def export_simulation_results(experiment_result_id: int, output_dir: str) -> str:
    """
    Exports all available dashboard pages for a given simulation result ID,
    consolidates them into a single Excel file with multiple tabs, and cleans up the temporary files.
    
    Args:
        experiment_result_id (int): The ID of the simulation result.
        output_dir (str): The directory path where the consolidated Excel file will be saved.
        
    Returns:
        str: The absolute path to the consolidated Excel file, or an error message.
    """
    api_instance = get_api_instance()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    consolidated_path = os.path.join(output_dir, f"Consolidated_Results_{experiment_result_id}.xlsx")
    temp_files = []
    
    try:
        dashboard_pages = api_instance.get_experiment_dashboard_pages(experiment_result_id)
        
        with pd.ExcelWriter(consolidated_path, engine='openpyxl') as writer:
            for page in dashboard_pages:
                safe_page_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', page.name)
                temp_filename = f"temp_{safe_page_name}.xlsx"
                temp_path = os.path.join(output_dir, temp_filename)
                
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
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception as e:
                    pass  # Skip if pandas fails to read the temp file
                    
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
                
        return consolidated_path
    except Exception as e:
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
                
                # Force convert object columns to numeric (coercing metadata strings to NaN)
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                numeric_cols = df.select_dtypes(include='number').columns
                if not numeric_cols.empty:
                    valid_metrics_found = False
                    sheet_summary = [f"--- Dashboard: {sheet} ---"]
                    
                    for col in numeric_cols:
                        # Skip meaningless numeric columns like IDs
                        if str(col).lower() in ['id', 'iteration', 'replication', 'period']:
                            continue
                            
                        # If the column has actual data (not just NaNs from coerced strings)
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
def modify_scenario_excel(original_excel_path: str, decision_index: int, output_dir: str) -> str:
    """
    Applies an AI decision to modify an existing scenario Excel file using Microsoft Excel (xlwings).
    
    Args:
        original_excel_path (str): The absolute path to the base scenario Excel file.
        decision_index (int): 
            0 = Increase Demand by 20%
            1 = Decrease Transport Costs by 15%
            2 = Increase Safety Stock by 10%
        output_dir (str): The directory where the modified Excel file will be saved.
        
    Returns:
        str: The absolute path to the modified Excel file, or an error message.
    """
    # 1. FORCE ABSOLUTE PATHS
    original_excel_path = os.path.abspath(original_excel_path)
    output_dir = os.path.abspath(output_dir)
    
    if not os.path.exists(original_excel_path):
        return "Error: Original Excel file does not exist."
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filename = os.path.basename(original_excel_path)
    if not filename.lower().endswith('.xlsx'):
        filename += '.xlsx'
        
    # 2. UNIQUE FILENAME to prevent Excel from blocking overwrites
    modified_excel_path = os.path.join(output_dir, f"Modified_Decision_{decision_index}_{int(time.time())}_{filename}")
    
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
            # (Tu código original de Increase Demand...)
            ws = wb.sheets['Demand']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            
            headers_row1 = ws.range((1, 1), (1, last_col)).value
            headers_row2 = ws.range((2, 1), (2, last_col)).value
            headers1 = headers_row1 if isinstance(headers_row1, list) else [headers_row1]
            headers2 = headers_row2 if isinstance(headers_row2, list) else [headers_row2]
            
            col7_idx = None
            col10_idx = None
            
            if 'Col 7' in headers1: col7_idx = headers1.index('Col 7') + 1
            if 'Col 10' in headers1: col10_idx = headers1.index('Col 10') + 1
            if not col7_idx and 'Parameters' in headers2: col7_idx = headers2.index('Parameters') + 1
            if not col10_idx and 'Parameters' in headers1: col10_idx = headers1.index('Parameters') + 1 
            if not col7_idx: col7_idx = 7
            if not col10_idx: col10_idx = 10
            
            for r in range(2, last_row + 1):
                if ws.range((r, col7_idx)).value == 'Quantity':
                    current_val = ws.range((r, col10_idx)).value
                    if isinstance(current_val, (int, float)):
                        ws.range((r, col10_idx)).value = current_val * 1.20
                        changes_made += 1
                        
        elif decision_index == 1:
            # (Tu código original de Decrease Transport Costs...)
            ws = wb.sheets['Paths']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            headers_row1 = ws.range((1, 1), (1, last_col)).value
            headers1 = headers_row1 if isinstance(headers_row1, list) else [headers_row1]
            col3_idx = headers1.index('Col 3') + 1 if 'Col 3' in headers1 else 3
            col4_idx = headers1.index('Col 4') + 1 if 'Col 4' in headers1 else 4
            
            for r in range(2, last_row + 1):
                val3 = ws.range((r, col3_idx)).value
                if val3 in ['Cost per unit', 'Cost']:
                    current_val = ws.range((r, col4_idx)).value
                    if isinstance(current_val, (int, float)):
                        ws.range((r, col4_idx)).value = current_val * 0.85
                        changes_made += 1
                            
        elif decision_index == 2:
            # (Tu código original de Increase Safety Stock...)
            ws = wb.sheets['Inventory']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            headers_row1 = ws.range((1, 1), (1, last_col)).value
            headers1 = headers_row1 if isinstance(headers_row1, list) else [headers_row1]
            col5_idx = headers1.index('Col 5') + 1 if 'Col 5' in headers1 else 5
            col6_idx = headers1.index('Col 6') + 1 if 'Col 6' in headers1 else 6
            
            for r in range(2, last_row + 1):
                if ws.range((r, col5_idx)).value == 'Safety stock':
                    current_val = ws.range((r, col6_idx)).value
                    if isinstance(current_val, (int, float)):
                        ws.range((r, col6_idx)).value = current_val * 1.10
                        changes_made += 1
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
    chroma_db_dir = r"C:\Users\Luis\Downloads\TFG\Chatbot\chroma_db"
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
