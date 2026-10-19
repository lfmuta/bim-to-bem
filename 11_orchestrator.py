import os
import sys
import subprocess
import logging
from datetime import datetime
from tkinter import Tk, filedialog, messagebox

# --- Logging Configuration ---
LOG_FILE = "orchestrator.log"
logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class WorkflowOrchestrator:
    """
    Orchestrates the execution of a series of Python scripts to process XML files
    into OpenStudio models.
    Handles both single file and batch (folder) processing, with interactive
    GUI or command-line arguments.
    """
    def __init__(self):
        logging.info("WorkflowOrchestrator initialized.")

    def _get_simulation_id(self):
        """Generates a unique simulation ID based on the current timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _select_xml_input(self):
        """
        Asks the user whether to process a single file or multiple files (folder)
        and returns the selected mode and path.
        Returns:
            tuple: (mode, path) where mode is "folder" or "file" and path is the selected path.
                   Returns (None, None) if no selection is made.
        """
        root = Tk()
        root.withdraw() # Hide the main Tkinter window.

        process_folder = messagebox.askyesno(
            "Select Processing Mode",
            "Do you want to process multiple files from a folder?\n"
            "Yes = Folder, No = Single File"
        )

        selected_path = None
        mode = None

        if process_folder:
            mode = "folder"
            selected_path = filedialog.askdirectory(title="Select Folder Containing XML Files")
        else:
            mode = "file"
            selected_path = filedialog.askopenfilename(
                title="Select an XML File",
                filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
            )
        root.destroy()
        return mode, selected_path

    def _run_script(self, script_name, args_list):
        """
        Executes a given Python script with the provided arguments.
        Args:
            script_name (str): The name of the script file to execute (e.g., "00_script.py").
            args_list (list): List of arguments to pass to the script.
        Returns:
            subprocess.CompletedProcess: The result of subprocess.run.
        Raises:
            Exception: If the script fails (returns a non-zero exit code).
        """
        cmd = [sys.executable, script_name] + args_list
        logging.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True) # text=True decodes stdout/stderr as strings

        if result.returncode != 0:
            error_detail = (
                f"Script {script_name} failed with exit code {result.returncode}.\n"
                f"--- STDOUT from {script_name} ---\n{result.stdout}\n"
                f"--- STDERR from {script_name} ---\n{result.stderr}\n"
            )
            logging.error(error_detail)
            raise Exception(error_detail)
        else:
            logging.info(f"Script {script_name} completed successfully.")
            if result.stdout:
                logging.info(f"Output from {script_name} (STDOUT):\n{result.stdout}")
        return result

    def _process_single_file(self, input_xml_file):
        """
        Processes a single XML file through the entire workflow (scripts 00 to 10).
        Args:
            input_xml_file (str): Path to the input XML file.
        Raises:
            FileNotFoundError: If a required intermediate file is not found.
            Exception: For any other error during script execution.
        """
        logging.info(f"Starting workflow for XML file: {input_xml_file}")
        base_name = os.path.splitext(os.path.basename(input_xml_file))[0]
        simulation_id = self._get_simulation_id()

        # Create a unique output directory for this simulation
        output_dir = os.path.join("outputs", f"{base_name}_{simulation_id}")
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Output directory created: {output_dir}")

        try:
            # --- Define paths for intermediate and final files ---
            # Output of one script is the input for the next, with the exception of script 03
            corrected_xml_path = os.path.join(output_dir, f"{base_name}_corrected.xml")

            step01_osm_path = os.path.join(output_dir, f"{base_name}_step01.osm")
            step02_osm_path = os.path.join(output_dir, f"{base_name}_step02.osm")
            step03_osm_path = os.path.join(output_dir, f"{base_name}_step03.osm")
            step04_osm_path = os.path.join(output_dir, f"{base_name}_step04.osm")
            step05_osm_path = os.path.join(output_dir, f"{base_name}_step05.osm")
            step06_osm_path = os.path.join(output_dir, f"{base_name}_step06.osm")
            step07_osm_path = os.path.join(output_dir, f"{base_name}_step07.osm")
            step08_osm_path = os.path.join(output_dir, f"{base_name}_step08.osm")
            step09_osm_path = os.path.join(output_dir, f"{base_name}_step09.osm")
            step10_osm_path = os.path.join(output_dir, f"{base_name}_step10.osm") # Final OSM file

            # --- Execute Scripts in Sequence ---

            # Script 00: 00_absorptance_fixer
            # Input: input_xml_file, Output: corrected_xml_path
            self._run_script("00_absorptance_fixer.py", [input_xml_file, corrected_xml_path])
            if not os.path.isfile(corrected_xml_path):
                raise FileNotFoundError(f"Script 00 failed. Corrected XML file not found: {corrected_xml_path}")
            logging.info(f"Script 00 completed. Output: {corrected_xml_path}")

            # Script 01: 01_gbxml_converter (Note: still uses 'gbxml_converter' name but handles .xml)
            # Input: corrected_xml_path, Output: step01_osm_path
            self._run_script("01_gbxml_converter.py", [corrected_xml_path, step01_osm_path])
            logging.info(f"Script 01 completed. Output: {step01_osm_path}")

            # Script 02: 02_schedules_cleaner
            # Input: step01_osm_path, Output: step02_osm_path
            self._run_script("02_schedules_cleaner.py", [step01_osm_path, step02_osm_path])
            logging.info(f"Script 02 completed. Output: {step02_osm_path}")

            # Script 03: 03_loads_enricher
            # Input: corrected_xml_path (from script 00) and step02_osm_path (from script 02), Output: step03_osm_path
            self._run_script("03_loads_enricher.py", [corrected_xml_path, step02_osm_path, step03_osm_path])
            logging.info(f"Script 03 completed. Output: {step03_osm_path}")

            # Script 04: 04_schedules_enricher
            # Input: step03_osm_path, Output: step04_osm_path
            self._run_script("04_schedules_enricher.py", [step03_osm_path, step04_osm_path])
            logging.info(f"Script 04 completed. Output: {step04_osm_path}")

            # Script 07: 07_plenum_disabler
            # Input: step04_osm_path, Output: step05_osm_path
            self._run_script("07_plenum_disabler.py", [step04_osm_path, step05_osm_path])
            logging.info(f"Script 07 completed. Output: {step05_osm_path}")

            # Script 08: 08_construction_renamer
            # Input: step05_osm_path, Output: step06_osm_path
            self._run_script("08_construction_renamer.py", [step05_osm_path, step06_osm_path])
            logging.info(f"Script 08 completed. Output: {step06_osm_path}")

            # Script 09: 09_surface_modifier
            # Input: step06_osm_path, Output: step07_osm_path
            self._run_script("09_surface_modifier.py", [step06_osm_path, step07_osm_path])
            logging.info(f"Script 09 completed. Output: {step07_osm_path}")

            # Script 10: 10_air_boundary_assigner (merges thermal zones, must run before 05 and 06)
            # Input: step07_osm_path, Output: step08_osm_path
            self._run_script("10_air_boundary_assigner.py", [step07_osm_path, step08_osm_path])
            logging.info(f"Script 10 completed. Output: {step08_osm_path}")

            # Script 05: 05_airflow_assigner
            # Input: step08_osm_path, Output: step09_osm_path
            self._run_script("05_airflow_assigner.py", [step08_osm_path, step09_osm_path])
            logging.info(f"Script 05 completed. Output: {step09_osm_path}")

            # Script 06: 06_ideal_loads_assigner
            # Input: step09_osm_path, Output: step10_osm_path
            self._run_script("06_ideal_loads_assigner.py", [step09_osm_path, step10_osm_path])
            logging.info(f"Script 06 completed. Output: {step10_osm_path}")

            print(f"\nFile processed successfully: {input_xml_file}")
            print(f"Final output file: {step10_osm_path}")
            logging.info("Workflow for the file completed successfully.\n")
            return True

        except Exception as e:
            logging.error(f"Workflow failed for file {input_xml_file}: {e}")
            print(f"Workflow failed for file {input_xml_file}: {e}")
            return False

    def run_standalone(self):
        """
        Runs the orchestrator in interactive (GUI) mode, allowing the user to select
        a single file or a folder for processing.
        """
        mode, path = self._select_xml_input()
        if not path:
            logging.error("No file or folder selected. Exiting.")
            return False

        if mode == "folder":
            return self._run_folder_mode(path)
        elif mode == "file":
            return self._process_single_file(path)
        else:
            logging.error("Unknown selection mode. Exiting.")
            return False

    def _run_folder_mode(self, folder_path):
        """
        Processes all XML files found in the specified folder.
        Args:
            folder_path (str): The path to the folder containing XML files.
        Returns:
            bool: True if all files were processed successfully, False otherwise.
        """
        xml_files = [os.path.join(folder_path, f)
                       for f in os.listdir(folder_path)
                       if f.lower().endswith('.xml')]
        if not xml_files:
            logging.error("No XML files found in the selected folder. Exiting.")
            return False

        all_successful = True
        for xml_file in xml_files:
            try:
                if not self._process_single_file(xml_file):
                    all_successful = False
            except Exception:
                # Continue to the next file even if one fails
                all_successful = False
                pass # The error is already logged by _process_single_file
        return all_successful

    def run_automated(self, xml_file_path):
        """
        Runs the orchestrator in automated mode for a single XML file, typically
        when a file path is provided as a command-line argument.
        Args:
            xml_file_path (str): The path to the XML file to process.
        Returns:
            bool: True if the file was processed successfully, False otherwise.
        """
        if not os.path.isfile(xml_file_path):
            logging.error(f"The provided file does not exist: {xml_file_path}")
            return False
        return self._process_single_file(xml_file_path)

def main():
    """
    Main entry point for the orchestrator script.
    Handles command-line arguments for automated processing or
    initiates the interactive GUI mode.
    """
    orchestrator = WorkflowOrchestrator()
    args = sys.argv[1:]
    success = False

    try:
        if len(args) == 1:
            # Automated mode: assume a single XML file is given via command line.
            success = orchestrator.run_automated(args[0])
        elif len(args) == 0:
            # Interactive mode: ask the user to select a folder or a single file.
            success = orchestrator.run_standalone()
        else:
            print("Usage: python orchestrator.py [input_file.xml] or run without arguments for GUI.")
            sys.exit(1) # Incorrect usage
    except Exception as e:
        logging.error(f"The main workflow failed: {e}")
        print(f"The main workflow failed: {e}")
        sys.exit(1) # Exit with error code

    sys.exit(0 if success else 1) # Exit with 0 for success, 1 for failure

if __name__ == "__main__":
    main()
