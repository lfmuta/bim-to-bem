import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from bs4 import BeautifulSoup
import os

# --- Constants ---
JOULES_TO_KWH = 3.6e6  # 1 kWh = 3,600,000 Joules
PRIMARY_ENERGY_FACTOR_BRAZIL = 1.6  # Primary energy factor for electricity in Brazil

# COP values for different models
COP_REAL_MODEL = 5.5  # CEER of the air conditioning system of the real project (Annex B.II)
COP_REFERENCE_MODEL = 3.24  # CEER and CEEA of the reference condition (Table A.2, Equations C.I.3 and C.I.4)
CEEA_REAL_MODEL = 1.72 + 0.5 * COP_REAL_MODEL  # Heating efficiency for split and window systems (Equation C.I.8)

# Days of occupation for lighting and equipment consumption (educational typology, Table A.2)
OCCUPATION_DAYS_LIGHTING_EQUIPMENT = 200

# Output variables (any reporting frequency)
VAR_COOLING = "Zone Ideal Loads Supply Air Total Cooling Energy [J]"
VAR_HEATING = "Zone Ideal Loads Supply Air Total Heating Energy [J]"
VAR_LIGHTING = "Zone Lights Electricity Energy [J]"
VAR_EQUIPMENT = "Zone Electric Equipment Electricity Energy [J]"

# --- Utility Functions ---
def select_folder(folder_type: str) -> Path:
    """
    Opens a dialog for the user to select a folder containing the simulation files.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main Tkinter window
    folder_path = filedialog.askdirectory(title=f"Select the {folder_type} folder")
    if not folder_path:
        raise FileNotFoundError(f"No {folder_type} folder was selected.")
    return Path(folder_path)

def find_required_files(folder_path: Path) -> tuple:
    """
    Finds the required CSV and HTML files in the specified folder.
    Returns (csv_path, html_path) or raises FileNotFoundError if not found.
    """
    csv_file = None
    html_file = None
    
    # Look for eplusout.csv
    csv_candidates = list(folder_path.glob("eplusout.csv"))
    if csv_candidates:
        csv_file = csv_candidates[0]
    
    # Look for eplustbl.htm
    html_candidates = list(folder_path.glob("eplustbl.htm"))
    if html_candidates:
        html_file = html_candidates[0]
    
    if not csv_file or not html_file:
        missing_files = []
        if not csv_file:
            missing_files.append("eplusout.csv")
        if not html_file:
            missing_files.append("eplustbl.htm")
        raise FileNotFoundError(f"Missing files in {folder_path}: {', '.join(missing_files)}")
    
    return csv_file, html_file

def extract_building_areas(html_path: Path) -> dict:
    """
    Extracts 'Net Conditioned Building Area' and 'Total Building Area' from the EnergyPlus HTML report.
    """
    areas = {'conditioned': None, 'total': None}
    
    try:
        with open(html_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
    except Exception as e:
        print(f"Error opening HTML file {html_path}: {e}")
        return areas
    
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) == 2:
                label = cells[0].get_text(strip=True)
                value_str = cells[1].get_text(strip=True)
                try:
                    value = float(value_str)
                    if "Net Conditioned Building Area" in label:
                        areas['conditioned'] = value
                    elif "Total Building Area" in label:
                        areas['total'] = value
                except ValueError:
                    pass
    
    return areas

def _sum_columns(df, search_string):
    columns = [col for col in df.columns if search_string in col]
    if not columns:
        return 0.0, 0
    return float(df[columns].sum().sum()), len(columns)

def _simulated_occupied_days(df):
    """Counts the days with lighting or equipment consumption in the simulation output."""
    if "Date/Time" not in df.columns:
        return 0
    columns = [col for col in df.columns if VAR_LIGHTING in col or VAR_EQUIPMENT in col]
    if not columns:
        return 0
    daily = df[columns].sum(axis=1)
    dates = df["Date/Time"].astype(str).str.strip().str.split().str[0]
    return int(dates[daily > 0].nunique())

def calculate_consumption(csv_path: Path, ceer: float, ceea: float) -> dict:
    """
    Calculates annual thermal loads and electricity consumption of one model (kWh/year), as described in Annex C.I.7.
    Cooling and heating consumption are the ideal thermal loads divided by CEER and CEEA.
    Lighting and equipment consumption are scaled to the days of occupation of the typology.
    """
    print(f"Reading file: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")
        return None

    cooling_j, n_cool = _sum_columns(df, VAR_COOLING)
    heating_j, _ = _sum_columns(df, VAR_HEATING)
    lighting_j, _ = _sum_columns(df, VAR_LIGHTING)
    equipment_j, _ = _sum_columns(df, VAR_EQUIPMENT)
    if n_cool == 0:
        print("Warning: no ideal loads cooling columns found in the CSV file.")

    simulated_days = _simulated_occupied_days(df)
    days_factor = OCCUPATION_DAYS_LIGHTING_EQUIPMENT / simulated_days if simulated_days > 0 else 1.0

    cgtr = cooling_j / JOULES_TO_KWH
    cgta = heating_j / JOULES_TO_KWH
    results = {
        "cgtr": cgtr,
        "cgta": cgta,
        "cgtt": cgtr + cgta,
        "cr": cgtr / ceer,
        "cae": cgta / ceea if cgta > 0 else 0.0,
        "cil": lighting_j / JOULES_TO_KWH * days_factor,
        "ceq": equipment_j / JOULES_TO_KWH * days_factor,
        "simulated_days": simulated_days,
        "days_factor": days_factor,
        "ceer": ceer,
        "ceea": ceea,
    }
    results["cee"] = results["cr"] + results["cae"] + results["cil"] + results["ceq"]
    results["cep"] = results["cee"] * PRIMARY_ENERGY_FACTOR_BRAZIL
    return results

def calculate_cep_and_redcep(real: dict, ref: dict, real_areas: dict = None, ref_areas: dict = None) -> dict:
    """
    Calculates CEP (Equations 8.2 and 8.3), RedCEP (Equation 8.1) and RedCgTT (Equation C.I.10).
    Equipment consumption is removed from both models in RedCEP, as required by Equation 8.1.
    """
    fce = PRIMARY_ENERGY_FACTOR_BRAZIL
    ref_without_eq = ref["cep"] - ref["ceq"] * fce
    real_without_eq = real["cep"] - real["ceq"] * fce
    redcep = ((ref_without_eq - real_without_eq) / ref_without_eq) * 100 if ref_without_eq > 0 else 0.0
    redcgtt = ((ref["cgtt"] - real["cgtt"]) / ref["cgtt"]) * 100 if ref["cgtt"] > 0 else 0.0

    results = {"real_model": dict(real), "reference_model": dict(ref), "redcep": redcep, "redcgtt": redcgtt}
    for key, model_results, areas in (("real_model", real, real_areas), ("reference_model", ref, ref_areas)):
        total_area = (areas or {}).get("total") or (areas or {}).get("conditioned")
        results[key]["total_area"] = total_area
        results[key]["conditioned_area"] = (areas or {}).get("conditioned")
        if total_area:
            results[key]["cooling_eui"] = (model_results["cr"] + model_results["cae"]) * fce / total_area
            results[key]["lighting_eui"] = model_results["cil"] * fce / total_area
            results[key]["equipment_eui"] = model_results["ceq"] * fce / total_area
            results[key]["total_eui"] = model_results["cep"] / total_area
    return results

def main():
    """
    Main function to execute the INI-C classification script.
    """
    try:
        print("=== INI-C Classification - RedCEP Calculator ===\n")
        
        # Select folders for real and reference models
        print("1. Select the REAL MODEL folder:")
        real_folder = select_folder("Real Model")
        
        print("2. Select the REFERENCE MODEL folder:")
        ref_folder = select_folder("Reference Model")
        
        # Find required files in both folders
        print(f"\nProcessing files...")
        real_csv, real_html = find_required_files(real_folder)
        ref_csv, ref_html = find_required_files(ref_folder)
        
        print(f"Real Model Files: {real_csv.name}, {real_html.name}")
        print(f"Reference Model Files: {ref_csv.name}, {ref_html.name}")
        
        # Extract building areas
        print(f"\nExtracting building areas...")
        real_areas = extract_building_areas(real_html)
        ref_areas = extract_building_areas(ref_html)
        
        # Calculate consumption for both models
        print(f"\nCalculating consumption for Real Model (CEER = {COP_REAL_MODEL}, CEEA = {CEEA_REAL_MODEL:.2f})...")
        real = calculate_consumption(real_csv, COP_REAL_MODEL, CEEA_REAL_MODEL)
        
        print(f"\nCalculating consumption for Reference Model (CEER = CEEA = {COP_REFERENCE_MODEL})...")
        ref = calculate_consumption(ref_csv, COP_REFERENCE_MODEL, COP_REFERENCE_MODEL)
        
        if not real or not ref:
            print("Error: Could not calculate consumption for one or both models.")
            return
        
        # Calculate CEP and RedCEP
        print(f"\nCalculating CEP and RedCEP...")
        cep_results = calculate_cep_and_redcep(real, ref, real_areas, ref_areas)
        
        # Display results
        print(f"\n" + "="*60)
        print(f"                    INI-C CLASSIFICATION RESULTS")
        print(f"="*60)
        
        for label, key in (("REAL MODEL", "real_model"), ("REFERENCE MODEL", "reference_model")):
            r = cep_results[key]
            print(f"\n{label}:")
            print(f"  CEER: {r['ceer']:.2f}  CEEA: {r['ceea']:.2f}")
            print(f"  Cooling load (CgTR):   {r['cgtr']:,.0f} kWh/year")
            print(f"  Heating load (CgTA):   {r['cgta']:,.0f} kWh/year")
            print(f"  Cooling (CR):          {r['cr']:,.0f} kWh/year")
            print(f"  Heating (CAE):         {r['cae']:,.0f} kWh/year")
            print(f"  Lighting (CIL):        {r['cil']:,.0f} kWh/year")
            print(f"  Equipment (CEQ):       {r['ceq']:,.0f} kWh/year")
            print(f"  TOTAL CEP:             {r['cep']:,.0f} kWh/year (primary energy)")
            print(f"  Lighting and equipment days: {OCCUPATION_DAYS_LIGHTING_EQUIPMENT} (simulated: {r['simulated_days']})")
        
        print(f"\nINI-C CLASSIFICATION:")
        print(f"  RedCEP = {cep_results['redcep']:.1f}%  (Equation 8.1, equipment consumption excluded)")
        print(f"  RedCgTT = {cep_results['redcgtt']:.1f}%  (envelope, Equation C.I.10)")
        
        # Classification interpretation
        if cep_results['redcep'] > 0:
            print(f"  Result: Building is {cep_results['redcep']:.1f}% MORE EFFICIENT than reference")
        elif cep_results['redcep'] < 0:
            print(f"  Result: Building is {abs(cep_results['redcep']):.1f}% LESS EFFICIENT than reference")
        else:
            print(f"  Result: Building has SAME EFFICIENCY as reference")
        
        print(f"\n" + "="*60)
        
        # Show success message
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Success", f"INI-C Classification completed successfully!\n\nRedCEP: {cep_results['redcep']:.1f}%")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("File Error", str(e))
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")

if __name__ == "__main__":
    main()
