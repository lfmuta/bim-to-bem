import openstudio
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import json
import subprocess

# Constants
SIMULATION_TIMESTEPS_PER_HOUR = 4
REPORTING_FREQUENCY = "Hourly"

# --- Integrated Utilities Functions ---

def load_osm_model_integrated(osm_path: Path, export_csv=True):
    """Load the OpenStudio model using the appropriate translator."""
    translator = openstudio.osversion.VersionTranslator()
    model = translator.loadModel(openstudio.toPath(str(osm_path)))
    if model.is_initialized():
        print(f"Model successfully loaded from {osm_path}.")
        m = model.get()
        if export_csv:
            out_contr = m.getOutputControlFiles()
            out_contr.setOutputCSV(True)
        return m
    else:
        raise Exception(f"Failed to load the model from {osm_path}.")

def save_model_as_integrated(model, new_filename_path: Path):
    """Save the modified model to a new file."""
    success = model.save(openstudio.toPath(str(new_filename_path)), True)
    if success:
        print(f"Model successfully saved to {new_filename_path}")
    else:
        raise Exception(f"Failed to save the model to {new_filename_path}.")

def prepare_workflow_osw_integrated(model_path: Path, epw_path: Path):
    """Prepares the workflow.osw file for OpenStudio simulation."""
    cwd = model_path.parent
    measures_dir = Path('./measures').absolute()
    steps = []
    if (measures_dir / "openstudio_results").is_dir():
        steps.append({"measure_dir_name": "openstudio_results", "arguments": {}})
    else:
        print("Measure 'openstudio_results' not found in ./measures. Running without the report measure.")
    osws = {
        "weather_file": str(epw_path),
        "seed_file": str(model_path),
        "file_paths": [str(cwd)],
        "measure_paths": [str(measures_dir)],
        "steps": steps
    }
    out_dir_for_osw = model_path.parent
    out_dir_for_osw.mkdir(parents=True, exist_ok=True)
    osw_path = out_dir_for_osw / 'workflow.osw'
    with open(osw_path, 'w') as f:
        f.write(json.dumps(osws, indent=2))
    print(f'Saved workflow file to {osw_path}')
    return osw_path

def run_single_simulation_integrated(osm_path: Path, epw_path: Path):
    """
    Runs a single OpenStudio simulation using the provided OSM and EPW files.
    """
    osw_path = prepare_workflow_osw_integrated(model_path=osm_path, epw_path=epw_path)

    cmd = ["openstudio", "run", "-w", str(osw_path)]
    print(f"Executing command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Simulation failed for {osm_path} with weather file {epw_path}")
        print("STDOUT:\n", res.stdout)
        print("STDERR:\n", res.stderr)
        print("\n\n")
    else:
        print(f"Simulation successful for {osm_path} with weather file {epw_path}")
        # print("STDOUT:\n", res.stdout) # Uncomment to see full stdout on success

# --- Original Functions (modified for _step10) ---

# Function to select a file using Tkinter
def select_file(file_type, file_extension):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title=f"Select {file_type} File",
        filetypes=[(file_type, f"*.{file_extension}")]
    )
    if not file_path:
        raise FileNotFoundError(f"No {file_type} file selected.")
    return Path(file_path)

# Function to select a folder using Tkinter
def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select Folder Containing OSM Files")
    if not folder_path:
        raise FileNotFoundError("No folder selected.")
    return Path(folder_path)

# Function to find all OSM files with "_step10" in the name
def find_osm_files(folder_path):
    return [osm_file for osm_file in folder_path.rglob("*.osm") if "_step10" in osm_file.stem.lower()]

# Function to add output variables to the model
def add_output_variables(model, variables):
    for var in variables:
        output_var = openstudio.model.OutputVariable(var, model)
        output_var.setKeyValue("*")  # Apply to all zones
        output_var.setReportingFrequency(REPORTING_FREQUENCY)

# Simulation settings required by INI-C (items C.I.3.2 and C.I.7)
def apply_inic_simulation_settings(model):
    run_period = model.getRunPeriod()
    run_period.setUseWeatherFileRainInd(False)
    run_period.setUseWeatherFileSnowInd(False)
    model.getTimestep().setNumberOfTimestepsPerHour(SIMULATION_TIMESTEPS_PER_HOUR)

# Main function
def main():
    # Set up the working directories
    current_dir = Path(os.getcwd())
    simulation_dir = current_dir / 'simulations'

    # Select the folder containing OSM files
    osm_folder = select_folder()
    
    # Select the EPW weather file (to be used for all simulations)
    epw_file = select_file("EPW weather", "epw")
    
    # Find all OSM files with "_step10" in their name within the selected folder
    osm_files = find_osm_files(osm_folder)

    if not osm_files:
        print("No '_step10' OSM files found in the selected folder.")
        return

    # Define the specific output variables requested
    requested_output_variables = [
        "Zone Ideal Loads Supply Air Total Heating Energy",
        "Zone Ideal Loads Supply Air Total Cooling Energy",
        "Zone Lights Electricity Energy",
        "Zone Electric Equipment Electricity Energy",
        "Zone People Occupant Count"
    ]

    # Loop through all found OSM files and run simulations
    for osm_file in osm_files:
        print(f"Processing: {osm_file}")

        # --- Model Preparation ---
        model = load_osm_model_integrated(osm_file)
        apply_inic_simulation_settings(model)
        
        # Remove existing output variables and add only the new ones
        [var.remove() for var in model.getOutputVariables()]
        add_output_variables(model, requested_output_variables)
        
        # Save the modified model
        simulation_name = f"{osm_file.stem}-{epw_file.stem}"
        processed_model_path = simulation_dir / simulation_name / f"baseline_{osm_file.name}"
        processed_model_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_model_as_integrated(model, processed_model_path)
        
        # --- Simulation Execution ---
        run_single_simulation_integrated(processed_model_path, epw_file)

        print(f"Simulation completed for: {osm_file}")

if __name__ == "__main__":
    main()
