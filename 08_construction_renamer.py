import openstudio
import os
import sys
import shutil
import tempfile
import logging
import re
from tkinter import Tk, filedialog

class ModelRenamer:
    """
    Class for post-processing OpenStudio models (.osm),
    focused on renaming Constructions and Materials for better readability.
    """
    def __init__(self):
        # Configure the logging system
        logging.basicConfig(
            filename="model_renamer.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("ModelRenamer initialized.")

    def _rename_constructions(self, model):
        """
        Renames Constructions (building systems) in the model
        based on their 'displayName'.
        """
        renamed_count = 0
        constructions = model.getConstructions()
        self.logger.info(f"Found {len(constructions)} constructions to process...")

        for const in constructions:
            additional_props = const.additionalProperties()
            display_name_obj = additional_props.getFeatureAsString("displayName")
            
            if display_name_obj.is_initialized():
                new_name = display_name_obj.get()
                old_name = const.name().get()
                
                # Remove prefixes like "Basic Roof: ", "Basic Wall: ", "Floor: ", etc.
                cleaned_name = re.sub(r'^[\w\s]+:\s*', '', new_name)
                cleaned_name = cleaned_name.strip()

                if cleaned_name and cleaned_name != old_name:
                    self.logger.info(f"  - Renaming construction '{old_name}' to '{cleaned_name}'")
                    const.setName(cleaned_name)
                    renamed_count += 1
                elif cleaned_name and cleaned_name == old_name:
                    self.logger.debug(f"  - Construction '{old_name}' already has desired name, skipping.")
                else:
                    self.logger.warning(f"  - Could not determine a valid cleaned name for '{old_name}' from '{new_name}'. Skipping.")

        self.logger.info(f"Total of {renamed_count} constructions renamed.")
        return renamed_count

    def _rename_materials(self, model):
        """
        Renames Materials (layers) in the model based on their 'displayName'.
        """
        renamed_count = 0
        all_materials = model.getMaterials()
        self.logger.info(f"Found {len(all_materials)} materials to process...")

        for material_layer in all_materials:
            additional_props = material_layer.additionalProperties()
            display_name_obj = additional_props.getFeatureAsString("displayName")
            
            if display_name_obj.is_initialized():
                new_name = display_name_obj.get()
                old_name = material_layer.name().get()
                
                cleaned_name = new_name.strip()

                if cleaned_name and cleaned_name != old_name:
                    self.logger.info(f"  - Renaming material '{old_name}' to '{cleaned_name}'")
                    material_layer.setName(cleaned_name)
                    renamed_count += 1
                elif cleaned_name and cleaned_name == old_name:
                    self.logger.debug(f"  - Material '{old_name}' already has desired name, skipping.")
                else:
                    self.logger.warning(f"  - Could not determine a valid cleaned name for '{old_name}' from '{new_name}'. Skipping.")

        self.logger.info(f"Total of {renamed_count} materials renamed.")
        return renamed_count

    def _rename_building_stories(self, model):
        renamed_count = 0
        stories = model.getBuildingStorys()
        self.logger.info(f"Found {len(stories)} building stories to process...")

        for story in stories:
            additional_props = story.additionalProperties()
            display_name_obj = additional_props.getFeatureAsString("displayName")

            if display_name_obj.is_initialized():
                new_name = display_name_obj.get().strip()
                old_name = story.name().get()

                if new_name and new_name != old_name:
                    self.logger.info(f"  Renaming building story '{old_name}' to '{new_name}'")
                    story.setName(new_name)
                    renamed_count += 1
                elif new_name and new_name == old_name:
                    self.logger.debug(f"  Building story '{old_name}' already has desired name, skipping.")

        self.logger.info(f"Total of {renamed_count} building stories renamed.")
        return renamed_count

    def _rename_thermal_zones(self, model):
        renamed_count = 0
        zones = model.getThermalZones()
        self.logger.info(f"Found {len(zones)} thermal zones to process...")

        for zone in zones:
            additional_props = zone.additionalProperties()
            display_name_obj = additional_props.getFeatureAsString("displayName")

            if display_name_obj.is_initialized():
                base_name = display_name_obj.get().strip()
                new_name = f"{base_name}_ThermalZone"
                old_name = zone.name().get()

                if new_name != old_name:
                    self.logger.info(f"  Renaming thermal zone '{old_name}' to '{new_name}'")
                    zone.setName(new_name)
                    renamed_count += 1
                elif new_name == old_name:
                    self.logger.debug(f"  Thermal zone '{old_name}' already has desired name, skipping.")

        self.logger.info(f"Total of {renamed_count} thermal zones renamed.")
        return renamed_count

    def _rename_spaces(self, model):
        renamed_count = 0
        spaces = model.getSpaces()
        self.logger.info(f"Found {len(spaces)} spaces to process...")

        for space in spaces:
            additional_props = space.additionalProperties()
            display_name_obj = additional_props.getFeatureAsString("displayName")

            if display_name_obj.is_initialized():
                base_name = display_name_obj.get().strip()
                new_name = f"{base_name}_Space"
                old_name = space.name().get()

                if new_name != old_name:
                    self.logger.info(f"  Renaming space '{old_name}' to '{new_name}'")
                    space.setName(new_name)
                    renamed_count += 1
                elif new_name == old_name:
                    self.logger.debug(f"  Space '{old_name}' already has desired name, skipping.")

        self.logger.info(f"Total of {renamed_count} spaces renamed.")
        return renamed_count

    def process_model(self, model):
        self.logger.info("Starting renaming process in the model.")
        
        renamed_const_count = self._rename_constructions(model)
        renamed_mat_count = self._rename_materials(model)
        renamed_story_count = self._rename_building_stories(model)
        renamed_zone_count = self._rename_thermal_zones(model)
        renamed_space_count = self._rename_spaces(model)
        
        self.logger.info("Renaming process completed.")
        return (renamed_const_count, renamed_mat_count, 
                renamed_story_count, renamed_zone_count, renamed_space_count)
    
    def process_osm_file(self, input_path, output_path):
        """
        Loads an .osm model, applies renaming, and saves the modified model.
        Uses a temporary file for safe processing.
        """
        temp_osm_file_path = None
        try:
            temp_file_handle, temp_osm_file_path = tempfile.mkstemp(suffix='.osm')
            os.close(temp_file_handle)
            shutil.copy(input_path, temp_osm_file_path)

            self.logger.info(f"Loading model from {input_path} (via temp {temp_osm_file_path})")
            
            translator = openstudio.osversion.VersionTranslator()
            model_object = translator.loadModel(openstudio.path(temp_osm_file_path))

            if not model_object.is_initialized():
                error_msg = f"Error Failed to load model from path\n{input_path}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            model = model_object.get()
            self.logger.info("Model loaded successfully.")

            renamed_const_count, renamed_mat_count, renamed_story_count, renamed_zone_count, renamed_space_count = self.process_model(model)

            self.logger.info(f"Saving modified model to {output_path}")
            if not model.save(openstudio.path(output_path), True):
                error_msg = f"Error Failed to save modified model to {output_path}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            self.logger.info(f"Model saved successfully to {output_path}")
            return renamed_const_count, renamed_mat_count, renamed_story_count, renamed_zone_count, renamed_space_count

        except Exception as e:
            error_msg = f"An unexpected error occurred during processing of '{input_path}'\n{e}"
            self.logger.error(error_msg, exc_info=True)
            raise 
        finally:
            if temp_osm_file_path and os.path.exists(temp_osm_file_path):
                os.remove(temp_osm_file_path)
                self.logger.info(f"Temporary file '{temp_osm_file_path}' removed.")

    def run_standalone(self):
        """
        Executes the script in standalone mode with a graphical interface (Tkinter)
        for file selection, but no final pop-up messages.
        """
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True) 

        self.logger.info("Standalone (GUI file selection) mode initiated.")
        print("OpenStudio Model Renamer - Interactive File Selection Mode")
        print("This script renames Constructions, Materials, Stories, Zones and Spaces in .osm files.")
        print("Please select the input and output files using the dialogs.")
        print("Results will be printed to the console and logged to 'model_renamer.log'.\n")

        input_osm_path = filedialog.askopenfilename(
            title="Select the .osm file to process",
            filetypes=[("OpenStudio Models", "*.osm")]
        )

        if not input_osm_path:
            self.logger.info("Operation cancelled by user (input selection).")
            print("Operation cancelled No input file selected.")
            root.destroy()
            return False
        
        output_osm_path = filedialog.asksaveasfilename(
            title="Save modified .osm file as...",
            initialdir=os.path.dirname(input_osm_path),
            defaultextension=".osm",
            filetypes=[("OpenStudio Models", "*.osm")]
        )

        if not output_osm_path:
            self.logger.info("Operation cancelled by user (output selection).")
            print("Operation cancelled No output file specified.")
            root.destroy()
            return False

        try:
            renamed_const, renamed_mat, renamed_story, renamed_zone, renamed_space = self.process_osm_file(input_osm_path, output_osm_path)
            success_message = (f"Process completed successfully!\n"
                               f"- {renamed_const} constructions renamed.\n"
                               f"- {renamed_mat} materials renamed.\n"
                               f"- {renamed_story} building stories renamed.\n"
                               f"- {renamed_zone} thermal zones renamed.\n"
                               f"- {renamed_space} spaces renamed.\n"
                               f"File saved to {output_osm_path}")
            self.logger.info(success_message)
            print("\n" + success_message) 
            return True
        except Exception as e:
            error_msg = f"An error occurred during renaming\n{e}"
            self.logger.error(error_msg)
            print("\n" + error_msg) 
            return False
        finally:
            root.destroy()

    def run_automated(self, input_path, output_path):
        """
        Executes the script in automated mode, receiving input and output paths
        as arguments. No GUI elements are used.
        """
        self.logger.info(f"Automated mode initiated. Input {input_path}, Output {output_path}")
        try:
            renamed_const, renamed_mat, renamed_story, renamed_zone, renamed_space = self.process_osm_file(input_path, output_path)
            success_message = (f"Automated process completed successfully!\n"
                               f"- {renamed_const} constructions renamed.\n"
                               f"- {renamed_mat} materials renamed.\n"
                               f"- {renamed_story} building stories renamed.\n"
                               f"- {renamed_zone} thermal zones renamed.\n"
                               f"- {renamed_space} spaces renamed.\n"
                               f"File saved to {output_path}")
            self.logger.info(success_message)
            print(success_message) 
            return True
        except Exception as e:
            error_msg = f"An error occurred during renaming in automated mode\n{e}"
            self.logger.error(error_msg)
            print(error_msg) 
            return False

def main():
    """
    Main function that manages script execution
    choosing between standalone (GUI file selection) or automated mode
    """
    renamer = ModelRenamer()
    args = sys.argv[1:]
    
    if len(args) == 2:
        success = renamer.run_automated(args[0], args[1])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        success = renamer.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage ")
        print("  For interactive file selection python 08_construction_renamer.py")
        print("  For automated mode python 08_construction_renamer.py <input_path.osm> <output_path.osm>")
        sys.exit(1)

if __name__ == "__main__":
    main()