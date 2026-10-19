import openstudio
import os
import tempfile
import shutil
import logging
import sys
from tkinter import Tk, filedialog # Removed messagebox import

# Import the utility function (or the variable directly)
from surface_mapping_utils import get_surface_mapping # or from surface_mapping_utils import SURFACE_TYPE_MAPPING

class OSMSurfacePropertySetter:
    """
    A class to automate the configuration of surface properties (Outside Boundary Condition,
    Sun Exposure, Wind Exposure) in an OpenStudio model, based on the assigned construction name.
    Supports standalone execution with a GUI and automated execution via command line.
    """
    def __init__(self):
        """
        Initializes the surface property setter and configures logging.
        The mapping dictionary is loaded directly from the utility module.
        """
        logging.basicConfig(
            filename="assign_surface_properties.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        # Get the mapping using the function from the utility module
        self.surface_type_mapping = get_surface_mapping() # or self.surface_type_mapping = SURFACE_TYPE_MAPPING

    def create_temp_copy(self, file_path):
        """Creates a temporary copy of the file to avoid direct modifications to the original."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_path)[1])
        shutil.copy(file_path, temp_file.name)
        self.logger.debug(f"Temporary copy created: {temp_file.name}")
        return temp_file.name

    def set_properties_to_model(self, model):
        """
        Modifies the Outside Boundary Condition, Sun Exposure, and Wind Exposure properties
        of surfaces in an OpenStudio model, based on the assigned construction name.
        Args:
            model (openstudio.model.Model): The OpenStudio model object to be modified.
        Returns:
            int: The number of surfaces whose properties were modified.
        """
        surfaces = model.getSurfaces()
        self.logger.info(f"Starting with {len(surfaces)} surfaces in the model.")
        surfaces_modified_count = 0
        for surface in surfaces:
            surface_name = surface.nameString()
            construction_opt = surface.construction()
            if not construction_opt.is_initialized():
                self.logger.warning(f"Surface '{surface_name}' has no construction assigned. Skipping.")
                continue

            construction = construction_opt.get()
            construction_name = construction.nameString()
            found_surface_type = None
            for type_key in sorted(self.surface_type_mapping.keys(), key=len, reverse=True):
                if type_key in construction_name:
                    found_surface_type = type_key
                    break

            if found_surface_type is None:
                self.logger.debug(
                    f"Construction name '{construction_name}' for surface '{surface_name}' "
                    f"does not contain a recognized Surface Type. Skipping."
                )
                continue

            expected_conditions = self.surface_type_mapping[found_surface_type]
            expected_obc = expected_conditions["outsideBoundaryCondition"]
            expected_se = expected_conditions["sunExposure"]
            expected_we = expected_conditions["windExposure"]

            current_obc = surface.outsideBoundaryCondition()
            current_se = surface.sunExposure()
            current_we = surface.windExposure()

            needs_update = False
            if current_obc != expected_obc:
                self.logger.info(
                    f"Surface '{surface_name}' (Construction: '{construction_name}') "
                    f"Outside Boundary Condition differs: current '{current_obc}', expected '{expected_obc}'."
                )
                needs_update = True
            if current_se != expected_se:
                self.logger.info(
                    f"Surface '{surface_name}' (Construction: '{construction_name}') "
                    f"Sun Exposure differs: current '{current_se}', expected '{expected_se}'."
                )
                needs_update = True
            if current_we != expected_we:
                self.logger.info(
                    f"Surface '{surface_name}' (Construction: '{construction_name}') "
                    f"Wind Exposure differs: current '{current_we}', expected '{expected_we}'."
                )
                needs_update = True

            if needs_update:
                surface.setOutsideBoundaryCondition(expected_obc)
                surface.setSunExposure(expected_se)
                surface.setWindExposure(expected_we)
                surfaces_modified_count += 1
                self.logger.info(f"Properties corrected for surface '{surface_name}'.")
            else:
                self.logger.debug(
                    f"Properties for surface '{surface_name}' are already correct according to the dictionary. "
                    f"No changes made."
                )
        self.logger.info(f"Finished: Properties modified for {surfaces_modified_count} out of {len(surfaces)} surfaces.")
        return surfaces_modified_count

    def process_model(self, osm_path, output_path):
        """
        Loads the OSM model, applies modifications, and saves the resulting model.
        Args:
            osm_path (str): Path to the input OSM file.
            output_path (str): Path to save the modified OSM file.
        Returns:
            bool: True if processing was successful, False otherwise.
        """
        temp_osm = None
        try:
            temp_osm = self.create_temp_copy(osm_path)
            translator = openstudio.osversion.VersionTranslator()
            osm_model_handle = translator.loadModel(openstudio.toPath(temp_osm))

            if not osm_model_handle.is_initialized():
                raise FileNotFoundError(f"Failed to load OSM file: {osm_path}")

            model = osm_model_handle.get()
            modified_count = self.set_properties_to_model(model)

            if not model.save(openstudio.toPath(output_path), True):
                raise IOError("Failed to save the modified OSM model")

            self.logger.info(f"OSM model processed and saved successfully: {output_path}. Total surfaces modified: {modified_count}")
            return True
        except Exception as e:
            self.logger.error(f"Model processing failed: {e}")
            return False
        finally:
            if temp_osm and os.path.exists(temp_osm):
                os.remove(temp_osm)
                self.logger.debug(f"Temporary file removed: {temp_osm}")

    def run_standalone(self):
        """
        Runs the script in standalone mode, presenting dialog boxes for file selection.
        """
        root = Tk()
        root.withdraw() # Hides the main Tkinter window

        osm_path = filedialog.askopenfilename(
            title="Select input OSM file",
            filetypes=[("OSM files", "*.osm")]
        )
        if not osm_path:
            self.logger.info("Input OSM file selection cancelled.")
            root.destroy()
            return False

        output_path = filedialog.asksaveasfilename(
            title="Save modified OSM file as",
            filetypes=[("OSM files", "*.osm")],
            defaultextension=".osm"
        )
        if not output_path:
            self.logger.info("Output file selection cancelled.")
            root.destroy()
            return False
        
        root.destroy() # Destroy root after file dialogs are closed
        self.logger.info(f"Standalone mode: Input OSM '{osm_path}', Output OSM '{output_path}'")
        
        success = self.process_model(osm_path, output_path)
        # No messagebox here, rely on logging and return value
        return success

    def run_automated(self, osm_path, output_path):
        """
        Runs the script in automated mode, using file paths provided as arguments.
        Args:
            osm_path (str): Path to the input OSM file.
            output_path (str): Path to save the modified OSM file.
        Returns:
            bool: True if processing was successful, False otherwise.
        """
        self.logger.info(f"Automated mode: Input OSM '{osm_path}', Output OSM '{output_path}'")
        return self.process_model(osm_path, output_path)

def main():
    """
    Main function to handle script execution (standalone or automated).
    """
    setter = OSMSurfacePropertySetter()
    args = sys.argv[1:]

    if len(args) == 2: # Expects input.osm output.osm
        success = setter.run_automated(args[0], args[1])
        if success:
            print(args[1]) # Prints the output path for script chaining
        sys.exit(0 if success else 1)
    elif len(args) == 0: # No arguments, run standalone mode with GUI
        success = setter.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python assign_surface_properties.py [input.osm output.osm]")
        print("Or run without arguments for GUI mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()
