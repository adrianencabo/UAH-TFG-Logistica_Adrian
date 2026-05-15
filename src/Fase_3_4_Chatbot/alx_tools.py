import os
import time
import shutil
import re
import urllib3
import xlwings as xw
from typing import List, Dict, Any, Union

from langchain.tools import tool

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
def export_simulation_results(experiment_result_id: int, output_dir: str) -> Union[List[str], str]:
    """
    Exports all available dashboard pages for a given simulation result ID as Excel files.
    
    Args:
        experiment_result_id (int): The ID of the simulation result.
        output_dir (str): The directory path where the Excel files will be saved.
        
    Returns:
        List[str]: A list of file paths to the exported Excel dashboards.
        str: Error message if failed.
    """
    api_instance = get_api_instance()
    exported_files = []
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    try:
        dashboard_pages = api_instance.get_experiment_dashboard_pages(experiment_result_id)
        
        for page in dashboard_pages:
            safe_page_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', page.name)
            output_filename = f"Results_{safe_page_name}.xlsx"
            output_path = os.path.join(output_dir, output_filename)
            
            excel_export = api_instance.export_dashboard_page(experiment_result_id, page.id)
            
            if isinstance(excel_export, str) and os.path.exists(excel_export):
                shutil.move(excel_export, output_path)
                exported_files.append(output_path)
            elif isinstance(excel_export, bytes):
                with open(output_path, "wb") as file:
                    file.write(excel_export)
                exported_files.append(output_path)
                
        return exported_files
    except Exception as e:
        return f"Error: {e}"

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
    if not os.path.exists(original_excel_path):
        return "Error: Original Excel file does not exist."
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filename = os.path.basename(original_excel_path)
    modified_excel_path = os.path.join(output_dir, f"Modified_Decision_{decision_index}_{filename}")
    
    try:
        shutil.copy2(original_excel_path, modified_excel_path)
    except Exception as e:
        return f"Error copying file: {e}"
        
    app = xw.App(visible=False)
    try:
        wb = app.books.open(modified_excel_path)
        
        if decision_index == 0:
            # Increase Demand by 20%
            ws = wb.sheets['Demand']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            headers_raw = ws.range((1, 1), (1, last_col)).value
            headers = headers_raw if isinstance(headers_raw, list) else [headers_raw]
            
            if 'Col 7' in headers and 'Col 10' in headers:
                col7_idx = headers.index('Col 7') + 1
                col10_idx = headers.index('Col 10') + 1
                for r in range(2, last_row + 1):
                    if ws.range((r, col7_idx)).value == 'Quantity':
                        current_val = ws.range((r, col10_idx)).value
                        if isinstance(current_val, (int, float)):
                            ws.range((r, col10_idx)).value = current_val * 1.20
                            
        elif decision_index == 1:
            # Decrease Transport Costs by 15%
            ws = wb.sheets['Paths']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            headers_raw = ws.range((1, 1), (1, last_col)).value
            headers = headers_raw if isinstance(headers_raw, list) else [headers_raw]
            
            if 'Col 3' in headers and 'Col 4' in headers:
                col3_idx = headers.index('Col 3') + 1
                col4_idx = headers.index('Col 4') + 1
                for r in range(2, last_row + 1):
                    val3 = ws.range((r, col3_idx)).value
                    if val3 in ['Cost per unit', 'Cost']:
                        current_val = ws.range((r, col4_idx)).value
                        if isinstance(current_val, (int, float)):
                            ws.range((r, col4_idx)).value = current_val * 0.85
                            
        elif decision_index == 2:
            # Increase Safety Stock by 10%
            ws = wb.sheets['Inventory']
            last_col = ws.used_range.last_cell.column
            last_row = ws.used_range.last_cell.row
            headers_raw = ws.range((1, 1), (1, last_col)).value
            headers = headers_raw if isinstance(headers_raw, list) else [headers_raw]
            
            if 'Col 5' in headers and 'Col 6' in headers:
                col5_idx = headers.index('Col 5') + 1
                col6_idx = headers.index('Col 6') + 1
                for r in range(2, last_row + 1):
                    if ws.range((r, col5_idx)).value == 'Safety stock':
                        current_val = ws.range((r, col6_idx)).value
                        if isinstance(current_val, (int, float)):
                            ws.range((r, col6_idx)).value = current_val * 1.10

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
    try:
        import_response = api_instance.import_excel(
            new_scenario_name=new_scenario_name,
            project_id=project_id,
            file=file_path,
            need_to_import_experiments=True
        )
        
        if not import_response.job_id:
            return "Error: No job_id received."
            
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

# Export the tools for LangGraph/LangChain
alx_tools = [
    open_and_get_project,
    get_scenarios_list,
    run_simulation,
    export_simulation_results,
    modify_scenario_excel,
    upload_modified_scenario
]
