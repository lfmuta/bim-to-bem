import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from bs4 import BeautifulSoup
import os
import sys
import logging
import importlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Constants ---
JOULES_TO_KWH = 3.6e6  # 1 kWh = 3,600,000 Joules
PRIMARY_ENERGY_FACTOR_BRAZIL = 1.6  # Primary energy factor for electricity in Brazil

# COP values for different models
COP_REAL_MODEL = 5.5  # CEER of the air conditioning system of the real project (Annex B.II)
COP_REFERENCE_MODEL = 3.24  # CEER and CEEA of the reference condition (Table A.2, Equations C.I.3 and C.I.4)
CEEA_REAL_MODEL = 1.72 + 0.5 * COP_REAL_MODEL  # Heating efficiency for split and window systems (Equation C.I.8)

# Shared INI-C calculation (Equations 8.1 to 8.3 and C.I.3 to C.I.12)
_redcep = importlib.import_module("14_a_redcep")

# --- Utility Functions ---
def select_folder(folder_type: str) -> Path:
    """
    Opens a dialog for the user to select a folder containing the simulation files.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main Tkinter window
    folder_path = filedialog.askdirectory(title=f"Select the {folder_type} folder")
    root.destroy()  # Properly destroy the root window
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

def calculate_pec_and_prpec(real: dict, ref: dict, real_areas: dict, ref_areas: dict) -> dict:
    """
    Calculates CEP and PRPEC (RedCEP, Equation 8.1) for INI-C classification and formats the results for the GUI.
    """
    shared = _redcep.calculate_cep_and_redcep(real, ref, real_areas, ref_areas)
    results = {'prpec': shared['redcep'], 'redcgtt': shared['redcgtt']}
    for key in ('real_model', 'reference_model'):
        r = shared[key]
        total_area = r.get('total_area') or 0
        fce = PRIMARY_ENERGY_FACTOR_BRAZIL
        results[key] = {
            'cooling_eui': r.get('cooling_eui', 0.0),
            'lighting_eui': r.get('lighting_eui', 0.0),
            'equipment_eui': r.get('equipment_eui', 0.0),
            'total_eui': r.get('total_eui', 0.0),
            'cooling_pec': (r['cr'] + r['cae']) * fce,
            'lighting_pec': r['cil'] * fce,
            'equipment_pec': r['ceq'] * fce,
            'total_pec': r['cep'],
            'hvac_area': total_area,
            'total_area': total_area
        }
    return results

def show_results_window(pec_results: dict):
    """
    Creates and displays a user-friendly window with the INI-C classification results.
    """
    # Create main window
    window = tk.Tk()
    window.title("INI-C Classification Results")
    window.geometry("850x750")
    window.configure(bg='#f0f0f0')
    
    # Add protocol to handle window closing properly
    def on_closing():
        window.quit()
        window.destroy()
    
    window.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Create main frame with scrollbar
    main_frame = tk.Frame(window, bg='#f0f0f0')
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title
    title_label = tk.Label(
        main_frame, 
        text="INI-C CLASSIFICATION - RESULTS",
        font=('Arial', 18, 'bold'),
        bg='#f0f0f0',
        fg='#2c3e50'
    )
    title_label.pack(pady=20)
    
    # Determine PRPEC status and color
    prpec = pec_results['prpec']
    if prpec > 0:
        status_text = f"Building is {prpec:.1f}% MORE EFFICIENT than reference"
        status_color = '#27ae60'
        status_icon = "+"
    elif prpec < 0:
        status_text = f"Building is {abs(prpec):.1f}% LESS EFFICIENT than reference"
        status_color = '#e74c3c'
        status_icon = "-"
    else:
        status_text = "Building has SAME EFFICIENCY as reference"
        status_color = '#f39c12'
        status_icon = "="
    
    # PRPEC Result Box (Highlight)
    prpec_frame = tk.Frame(main_frame, bg=status_color, relief=tk.RAISED, borderwidth=3)
    prpec_frame.pack(fill=tk.X, pady=20)
    
    prpec_label = tk.Label(
        prpec_frame,
        text=f"PRPEC = {prpec:.1f}%",
        font=('Arial', 24, 'bold'),
        bg=status_color,
        fg='white',
        pady=15
    )
    prpec_label.pack()
    
    status_label = tk.Label(
        prpec_frame,
        text=status_text,
        font=('Arial', 12),
        bg=status_color,
        fg='white',
        pady=10
    )
    status_label.pack()
    
    # Create notebook for tabs
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Tab 1: Real Model
    real_tab = tk.Frame(notebook, bg='white')
    notebook.add(real_tab, text='Real Model')
    
    create_model_details(
        real_tab, 
        pec_results['real_model'],
        COP_REAL_MODEL,
        "Real Model"
    )
    
    # Tab 2: Reference Model
    ref_tab = tk.Frame(notebook, bg='white')
    notebook.add(ref_tab, text='Reference Model')
    
    create_model_details(
        ref_tab,
        pec_results['reference_model'],
        COP_REFERENCE_MODEL,
        "Reference Model"
    )
    
    # Tab 3: Comparison
    comparison_tab = tk.Frame(notebook, bg='white')
    notebook.add(comparison_tab, text='Comparison')
    
    create_comparison_view(comparison_tab, pec_results)
    
    # Close button
    close_button = tk.Button(
        main_frame,
        text="Close",
        command=on_closing,
        font=('Arial', 11),
        bg='#3498db',
        fg='white',
        padx=30,
        pady=10,
        cursor='hand2'
    )
    close_button.pack(pady=20)
    
    window.mainloop()

def create_model_details(parent_frame, model_data, cop, model_name):
    """
    Creates the detailed view for a model in a tab.
    """
    # Scrollable frame
    canvas = tk.Canvas(parent_frame, bg='white')
    scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg='white')
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Model info
    info_frame = tk.Frame(scrollable_frame, bg='#ecf0f1', relief=tk.GROOVE, borderwidth=2)
    info_frame.pack(fill=tk.X, padx=20, pady=20)
    
    tk.Label(
        info_frame,
        text=f"{model_name} Information",
        font=('Arial', 13, 'bold'),
        bg='#ecf0f1',
        fg='#2c3e50'
    ).pack(pady=10)
    
    tk.Label(
        info_frame,
        text=f"COP Used: {cop}",
        font=('Arial', 11),
        bg='#ecf0f1'
    ).pack(pady=5)
    
    tk.Label(
        info_frame,
        text=f"HVAC Area (Conditioned): {model_data['hvac_area']:.2f} m²",
        font=('Arial', 11),
        bg='#ecf0f1'
    ).pack(pady=5)
    
    tk.Label(
        info_frame,
        text=f"Total Building Area: {model_data['total_area']:.2f} m²",
        font=('Arial', 11),
        bg='#ecf0f1'
    ).pack(pady=10)
    
    # PEC Components as EUI
    pec_frame = tk.Frame(scrollable_frame, bg='white')
    pec_frame.pack(fill=tk.BOTH, padx=20, pady=10)
    
    tk.Label(
        pec_frame,
        text="Primary Energy Use Intensity (EUI)",
        font=('Arial', 13, 'bold'),
        bg='white',
        fg='#2c3e50'
    ).pack(pady=15)
    
    # Create bars for each component (using EUI values)
    components = [
        ("Cooling", model_data['cooling_eui'], '#3498db', model_data['hvac_area']),
        ("Lighting", model_data['lighting_eui'], '#FDB813', model_data['total_area']),
        ("Equipment", model_data['equipment_eui'], '#FF8C00', model_data['total_area'])
    ]
    
    max_value = max(c[1] for c in components) if any(c[1] > 0 for c in components) else 1
    
    for label, value, color, area in components:
        create_bar_chart_item(pec_frame, label, value, max_value, color, area)
    
    # Total PEC
    total_frame = tk.Frame(scrollable_frame, bg='#2ecc71', relief=tk.RAISED, borderwidth=2)
    total_frame.pack(fill=tk.X, padx=20, pady=20)
    
    tk.Label(
        total_frame,
        text="TOTAL PEC (Primary Energy Consumption)",
        font=('Arial', 12, 'bold'),
        bg='#2ecc71',
        fg='white'
    ).pack(pady=10)
    
    tk.Label(
        total_frame,
        text=f"{model_data['total_pec']:,.0f} kWh/year",
        font=('Arial', 16, 'bold'),
        bg='#2ecc71',
        fg='white'
    ).pack(pady=5)
    
    tk.Label(
        total_frame,
        text=f"({model_data['total_eui']:.2f} kWh/m²/year)",
        font=('Arial', 12),
        bg='#2ecc71',
        fg='white'
    ).pack(pady=10)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

def create_bar_chart_item(parent, label, value, max_value, color, area_used):
    """
    Creates a horizontal bar chart item showing EUI.
    """
    item_frame = tk.Frame(parent, bg='white')
    item_frame.pack(fill=tk.X, pady=8)
    
    # Label
    tk.Label(
        item_frame,
        text=label,
        font=('Arial', 10),
        bg='white',
        width=15,
        anchor='w'
    ).pack(side=tk.LEFT)
    
    # Bar container
    bar_container = tk.Frame(item_frame, bg='#ecf0f1', height=25, width=300)
    bar_container.pack(side=tk.LEFT, padx=10)
    bar_container.pack_propagate(False)
    
    # Bar
    if max_value > 0:
        bar_width = int((value / max_value) * 300)
    else:
        bar_width = 0
    
    bar = tk.Frame(bar_container, bg=color, height=25, width=bar_width)
    bar.place(x=0, y=0)
    
    # Value label with area info
    tk.Label(
        item_frame,
        text=f"{value:.2f} kWh/m²/year ({area_used:.0f} m²)",
        font=('Arial', 10, 'bold'),
        bg='white'
    ).pack(side=tk.LEFT, padx=10)

def create_comparison_view(parent_frame, pec_results):
    """
    Creates a comparison view between real and reference models.
    """
    canvas = tk.Canvas(parent_frame, bg='white')
    scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg='white')
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Title
    tk.Label(
        scrollable_frame,
        text="Detailed Comparison",
        font=('Arial', 14, 'bold'),
        bg='white',
        fg='#2c3e50'
    ).pack(pady=20)
    
    # Comparison table - Using EUI values
    comparison_data = [
        ("Cooling (EUI)", 
         pec_results['real_model']['cooling_eui'],
         pec_results['reference_model']['cooling_eui'],
         "kWh/m²/year",
         False),
        ("Lighting (EUI)",
         pec_results['real_model']['lighting_eui'],
         pec_results['reference_model']['lighting_eui'],
         "kWh/m²/year",
         False),
        ("Equipment (EUI)",
         pec_results['real_model']['equipment_eui'],
         pec_results['reference_model']['equipment_eui'],
         "kWh/m²/year",
         False),
        ("TOTAL (EUI)",
         pec_results['real_model']['total_eui'],
         pec_results['reference_model']['total_eui'],
         "kWh/m²/year",
         True),
        ("PRPEC",
         pec_results['prpec'],
         0,  # Reference is always 0% by definition
         "%",
         True)
    ]
    
    # Create table
    table_frame = tk.Frame(scrollable_frame, bg='white')
    table_frame.pack(padx=20, pady=10)
    
    # Header
    headers = ["Component", "Real Model", "Reference Model", "Difference"]
    for col, header in enumerate(headers):
        tk.Label(
            table_frame,
            text=header,
            font=('Arial', 11, 'bold'),
            bg='#34495e',
            fg='white',
            padx=15,
            pady=10,
            relief=tk.RAISED
        ).grid(row=0, column=col, sticky='ew', padx=1, pady=1)
    
    # Data rows
    for row, (component, real_val, ref_val, unit, is_special) in enumerate(comparison_data, start=1):
        # Special handling for PRPEC row
        if component == "PRPEC":
            bg_color = '#fff9e6'  # Light yellow background for PRPEC
            font_weight = 'bold'
            
            tk.Label(
                table_frame,
                text=component,
                font=('Arial', 10, font_weight),
                bg=bg_color,
                padx=15,
                pady=8
            ).grid(row=row, column=0, sticky='ew')
            
            # PRPEC value in Real Model column
            prpec_color = '#27ae60' if real_val > 0 else '#e74c3c' if real_val < 0 else '#95a5a6'
            tk.Label(
                table_frame,
                text=f"{real_val:.2f}%",
                font=('Arial', 10, font_weight),
                bg=bg_color,
                fg=prpec_color,
                padx=15,
                pady=8
            ).grid(row=row, column=1, sticky='ew')
            
            # Reference is 0% by definition
            tk.Label(
                table_frame,
                text="0.00% (baseline)",
                font=('Arial', 10),
                bg=bg_color,
                padx=15,
                pady=8
            ).grid(row=row, column=2, sticky='ew')
            
            # Interpretation
            if real_val > 0:
                interpret_text = f"↓ {real_val:.2f}% more efficient"
                interpret_color = '#27ae60'
            elif real_val < 0:
                interpret_text = f"↑ {abs(real_val):.2f}% less efficient"
                interpret_color = '#e74c3c'
            else:
                interpret_text = "= Same efficiency"
                interpret_color = '#95a5a6'
            
            tk.Label(
                table_frame,
                text=interpret_text,
                font=('Arial', 10, font_weight),
                bg=bg_color,
                fg=interpret_color,
                padx=15,
                pady=8
            ).grid(row=row, column=3, sticky='ew')
            
        else:
            # Regular rows
            diff = real_val - ref_val
            diff_pct = ((real_val - ref_val) / ref_val * 100) if ref_val > 0 else 0
            
            bg_color = '#ecf0f1' if row % 2 == 0 else 'white'
            if is_special:
                bg_color = '#d5e8d4'  # Light green for TOTAL
                font_weight = 'bold'
            else:
                font_weight = 'normal'
            
            tk.Label(
                table_frame,
                text=component,
                font=('Arial', 10, font_weight),
                bg=bg_color,
                padx=15,
                pady=8
            ).grid(row=row, column=0, sticky='ew')
            
            # Format values based on unit
            real_text = f"{real_val:.2f} {unit}"
            ref_text = f"{ref_val:.2f} {unit}"
            diff_text = f"{abs(diff):.2f} {unit}"
            
            tk.Label(
                table_frame,
                text=real_text,
                font=('Arial', 10),
                bg=bg_color,
                padx=15,
                pady=8
            ).grid(row=row, column=1, sticky='ew')
            
            tk.Label(
                table_frame,
                text=ref_text,
                font=('Arial', 10),
                bg=bg_color,
                padx=15,
                pady=8
            ).grid(row=row, column=2, sticky='ew')
            
            diff_color = '#27ae60' if diff < 0 else '#e74c3c' if diff > 0 else '#95a5a6'
            diff_symbol = "↓" if diff < 0 else "↑" if diff > 0 else "="
            
            tk.Label(
                table_frame,
                text=f"{diff_symbol} {diff_text} ({diff_pct:+.1f}%)",
                font=('Arial', 10, 'bold'),
                bg=bg_color,
                fg=diff_color,
                padx=15,
                pady=8
            ).grid(row=row, column=3, sticky='ew')
    
    # Explanation
    explanation_frame = tk.Frame(scrollable_frame, bg='#e8f8f5', relief=tk.GROOVE, borderwidth=2)
    explanation_frame.pack(fill=tk.X, padx=20, pady=20)
    
    tk.Label(
        explanation_frame,
        text="How to interpret the results:",
        font=('Arial', 11, 'bold'),
        bg='#e8f8f5',
        fg='#16a085'
    ).pack(pady=10, anchor='w', padx=10)
    
    explanation_text = """
    • PRPEC (Primary Reduction of Primary Energy Consumption): Overall efficiency metric
    • Positive PRPEC (+): Your building consumes LESS energy than reference (more efficient)
    • Negative PRPEC (-): Your building consumes MORE energy than reference (less efficient)
    • EUI (Energy Use Intensity): Energy consumption per square meter per year
    • PRPEC follows INI-C Equation 8.1: equipment consumption is excluded from both models
    • All EUI values use total building area
    • Values with ↓: Reduction in consumption compared to reference (positive)
    • Values with ↑: Increase in consumption compared to reference (negative)
    """
    
    tk.Label(
        explanation_frame,
        text=explanation_text,
        font=('Arial', 9),
        bg='#e8f8f5',
        justify=tk.LEFT
    ).pack(pady=10, padx=10, anchor='w')
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

def main():
    """
    Main function to execute the INI-C classification script.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='execution_log.log',
        filemode='a'
    )

    try:
        # Log the start of the execution to the file
        logging.info("="*30)
        logging.info("SCRIPT EXECUTION STARTED: INI-C Classification")
        logging.info("="*30)

        print("=== INI-C Classification - PRPEC Calculator ===\n")
        
        # Select folders for real and reference models
        print("1. Select the REAL MODEL folder:")
        real_folder = select_folder("Real Model")
        logging.info(f"Real Model folder selected: {real_folder}")

        print("2. Select the REFERENCE MODEL folder:")
        ref_folder = select_folder("Reference Model")
        logging.info(f"Reference Model folder selected: {ref_folder}")

        # Find required files in both folders
        print(f"\nProcessing files...")
        logging.info("Processing files...")
        real_csv, real_html = find_required_files(real_folder)
        ref_csv, ref_html = find_required_files(ref_folder)
        
        print(f"Real Model Files: {real_csv.name}, {real_html.name}")
        logging.info(f"Real Model Files Found: {real_csv.name}, {real_html.name}")
        
        print(f"Reference Model Files: {ref_csv.name}, {ref_html.name}")
        logging.info(f"Reference Model Files Found: {ref_csv.name}, {ref_html.name}")

        # Extract building areas
        print(f"\nExtracting building areas...")
        logging.info("Extracting building areas...")
        real_areas = extract_building_areas(real_html)
        ref_areas = extract_building_areas(ref_html)
        logging.info(f"Real Model Areas: {real_areas}")
        logging.info(f"Reference Model Areas: {ref_areas}")

        # Calculate EUI for both models
        print(f"\nCalculating consumption for Real Model (CEER = {COP_REAL_MODEL})...")
        logging.info(f"Calculating consumption for Real Model (CEER = {COP_REAL_MODEL})...")
        real_eui = _redcep.calculate_consumption(real_csv, COP_REAL_MODEL, CEEA_REAL_MODEL)
        
        print(f"\nCalculating consumption for Reference Model (CEER = {COP_REFERENCE_MODEL})...")
        logging.info(f"Calculating consumption for Reference Model (CEER = {COP_REFERENCE_MODEL})...")
        ref_eui = _redcep.calculate_consumption(ref_csv, COP_REFERENCE_MODEL, COP_REFERENCE_MODEL)

        if not real_eui or not ref_eui:
            message = "Error: Could not calculate EUI for one or both models."
            print(message)
            logging.error(message)
            return

        # Calculate PEC and PRPEC
        print(f"\nCalculating PEC and PRPEC...")
        logging.info("Calculating PEC and PRPEC...")
        pec_results = calculate_pec_and_prpec(real_eui, ref_eui, real_areas, ref_areas)
        logging.info(f"Final PRPEC result: {pec_results.get('prpec', 'N/A'):.2f}%")

        # Show results in GUI window
        print("\nOpening results window...")
        logging.info("Opening results GUI window...")
        show_results_window(pec_results)

        print("\nScript completed successfully!")
        logging.info("Script completed successfully!")
        logging.info("-" * 50 + "\n")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        logging.error(f"File Not Found Error: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("File Error", str(e))
        root.destroy()

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logging.error("An unexpected error occurred:", exc_info=True)
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
        root.destroy()

if __name__ == "__main__":
    main()