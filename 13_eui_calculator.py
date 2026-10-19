import pandas as pd
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from bs4 import BeautifulSoup

# --- Constants ---
JOULES_TO_KWH = 3.6e6 # 1 kWh = 3,600,000 Joules
HVAC_REFERENCE_COP = 5.5 # CEER of the real project system (used to convert cooling load to electrical consumption)
HVAC_HEATING_CEEA = 1.72 + 0.5 * HVAC_REFERENCE_COP # CEEA for split and window systems (INI-C Equation C.I.8)
PRIMARY_ENERGY_FACTOR_BRAZIL = 1.6 # Primary energy factor for electricity in Brazil, as used in Brazil

# --- Utility Functions ---

def select_file(file_type_name: str, extension: str) -> Path:
    """
    Opens a dialog for the user to select a specific file.
    """
    root = tk.Tk()
    root.withdraw()  # Hides the main Tkinter window
    file_path = filedialog.askopenfilename(
        title=f"Select the {file_type_name} file (*.{extension})",
        filetypes=[(f"{file_type_name} files", f"*.{extension}")]
    )
    if not file_path:
        raise FileNotFoundError(f"No {file_type_name} file was selected.")
    return Path(file_path)

def extract_building_areas(html_path: Path) -> dict:
    """
    Extracts 'Net Conditioned Building Area' and 'Total Building Area' from the EnergyPlus HTML report (eplustbl.htm).
    Returns a dictionary with the values (float) or None if not found/parsed.
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
                    # Ignore parsing errors for this cell, continue searching
                    pass
    
    print(f"Areas extracted from {html_path}:")
    print(f"  - Net Conditioned Building Area: {areas['conditioned']:.2f} m²" if areas['conditioned'] is not None else "  - Net Conditioned Building Area: Not found")
    print(f"  - Total Building Area: {areas['total']:.2f} m²" if areas['total'] is not None else "  - Total Building Area: Not found")
    
    return areas

def calculate_eui(csv_path: Path, areas: dict, primary_energy_factor: float) -> dict | None:
    """
    Reads the eplusout.csv file, sums the values for specified output variables,
    converts to kWh (applying COP for HVAC), and calculates the Energy Use Intensity (EUI)
    in kWh/year per m² (Site EUI and Primary EUI).
    """
    print(f"Reading file: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")
        return None

    net_conditioned_area = areas.get('conditioned')
    total_building_area = areas.get('total')

    # Initial check to ensure at least one valid area exists
    if (net_conditioned_area is None or net_conditioned_area <= 0) and \
       (total_building_area is None or total_building_area <= 0):
        print("Error: No valid building area (conditioned or total) provided or it's zero/negative. Cannot calculate EUI.")
        return None

    # Define the areas to be used, with fallbacks as per your correction
    area_for_ideal_loads = net_conditioned_area
    area_for_lighting_equipment = total_building_area

    if area_for_ideal_loads is None or area_for_ideal_loads <= 0:
        print("Warning: 'Net Conditioned Building Area' not found or invalid for Ideal Loads. Using 'Total Building Area' as fallback.")
        area_for_ideal_loads = total_building_area
    
    if area_for_lighting_equipment is None or area_for_lighting_equipment <= 0:
        print("Warning: 'Total Building Area' not found or invalid for Lighting/Equipment. Using 'Net Conditioned Building Area' as fallback.")
        area_for_lighting_equipment = net_conditioned_area

    # Final check to ensure calculation areas are not null or zero after fallbacks
    if area_for_ideal_loads is None or area_for_ideal_loads <= 0:
        print("Error: No valid area for Ideal Loads after fallbacks. Cannot calculate EUI for Ideal Loads.")
        return None
    if area_for_lighting_equipment is None or area_for_lighting_equipment <= 0:
        print("Error: No valid area for Lighting/Equipment after fallbacks. Cannot calculate EUI for Lighting/Equipment.")
        return None

    output_variable_map = {
        "Zone Lights Electricity Energy [J]": "Lighting Electricity",
        "Zone Electric Equipment Electricity Energy [J]": "Electric Equipment Electricity",
        "Zone Ideal Loads Supply Air Total Cooling Energy [J]": "Ideal Cooling (Electrical Input)",
        "Zone Ideal Loads Supply Air Total Heating Energy [J]": "Ideal Heating (Electrical Input)"
    }

    eui_results = {}
    total_site_eui_sum = 0.0

    # Iterate over each desired output variable
    for search_string, display_name_base in output_variable_map.items():
        matching_columns = [col for col in df.columns if search_string in col]
        current_area_m2 = None
        area_used_description = ""

        if "Ideal Loads" in search_string:
            current_area_m2 = area_for_ideal_loads
            area_used_description = "Conditioned Area" if net_conditioned_area == current_area_m2 else "Total Area (fallback)"
        else: # Lighting and Electric Equipment
            current_area_m2 = area_for_lighting_equipment
            area_used_description = "Total Area" if total_building_area == current_area_m2 else "Conditioned Area (fallback)"

        if current_area_m2 is None or current_area_m2 <= 0:
            print(f"  - Error: No valid area for '{display_name_base}'. EUI: N/A")
            eui_results[f"{display_name_base} Site EUI"] = "N/A"
            eui_results[f"{display_name_base} Primary EUI"] = "N/A"
            continue # Skip to the next variable if the area is invalid

        if matching_columns:
            total_sum_joules_thermal = df[matching_columns].sum().sum()
            
            # For lighting and equipment, it's direct electrical energy
            if "Electricity Energy" in search_string:
                total_sum_kwh_electrical = total_sum_joules_thermal / JOULES_TO_KWH
            # For heating and cooling, it's thermal energy, so we apply the COP
            elif "Ideal Loads" in search_string:
                total_sum_kwh_thermal = total_sum_joules_thermal / JOULES_TO_KWH
                efficiency = HVAC_HEATING_CEEA if "Heating" in search_string else HVAC_REFERENCE_COP
                total_sum_kwh_electrical = total_sum_kwh_thermal / efficiency
                print(f"  - Applying efficiency of {efficiency:.2f} for '{search_string}'. Thermal energy: {total_sum_kwh_thermal:.2f} kWh -> Electrical energy: {total_sum_kwh_electrical:.2f} kWh")
            else: # In case there are other variables in the future
                total_sum_kwh_electrical = 0 

            site_eui = total_sum_kwh_electrical / current_area_m2
            primary_eui = site_eui * primary_energy_factor

            eui_results[f"{display_name_base} Site EUI"] = site_eui
            eui_results[f"{display_name_base} Primary EUI"] = primary_eui
            total_site_eui_sum += site_eui
            print(f"  - Found {len(matching_columns)} columns for '{search_string}'. Area used: {current_area_m2:.2f} m² ({area_used_description}). Site EUI: {site_eui:.2f} kWh/m²")
        else:
            eui_results[f"{display_name_base} Site EUI"] = 0.0
            eui_results[f"{display_name_base} Primary EUI"] = 0.0
            print(f"  - No columns found for '{search_string}'. EUI: 0.00 kWh/m²")
    
    eui_results["Total Site EUI (All Components - Electrical)"] = total_site_eui_sum
    eui_results["Total Primary EUI (All Components - Electrical)"] = total_site_eui_sum * primary_energy_factor
    return eui_results

# --- Main Execution ---

def main():
    """
    Main function to execute the script.
    """
    try:
        # Select the eplusout.csv file
        csv_file_path = select_file("eplusout CSV", "csv")
        # Select the EnergyPlus HTML report file
        html_file_path = select_file("EnergyPlus HTML Report", "htm")
        
        # Extract building areas from the HTML report
        extracted_areas = extract_building_areas(html_file_path)

        net_conditioned_area = extracted_areas.get('conditioned')
        total_building_area = extracted_areas.get('total')

        # Check if any valid area was found before proceeding
        if (net_conditioned_area is None or net_conditioned_area <= 0) and \
           (total_building_area is None or total_building_area <= 0):
            print("Error: No valid building area (conditioned or total) was found or is zero/negative. Cannot calculate EUI.")
            return

        # Calculate EUI values
        eui_calculation_results = calculate_eui(csv_file_path, extracted_areas, PRIMARY_ENERGY_FACTOR_BRAZIL)

        if eui_calculation_results:
            print(f"\n--- Energy Use Intensity (EUI) Results for {csv_file_path.name} ---")
            print(f"Primary Energy Factor Used (Brazil): {PRIMARY_ENERGY_FACTOR_BRAZIL:.2f}")
            if net_conditioned_area is not None and net_conditioned_area > 0:
                print(f"Net Conditioned Building Area: {net_conditioned_area:.2f} m²")
            if total_building_area is not None and total_building_area > 0:
                print(f"Total Building Area: {total_building_area:.2f} m²")

            for var_name, eui_value in eui_calculation_results.items():
                if isinstance(eui_value, (int, float)):
                    print(f"{var_name}: {eui_value:.2f} kWh/year/m²")
                else:
                    print(f"{var_name}: {eui_value}") # For cases where EUI is "N/A"
        else:
            print("Could not process the CSV file or no EUI data was found.")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
