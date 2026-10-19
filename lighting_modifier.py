import openstudio
import os
import sys
import logging
from tkinter import Tk, filedialog

from spacetype_utils import get_space_type_label

class LightingPowerDensityModifier:
    def __init__(self):
        logging.basicConfig(
            filename="lighting_density_modifier.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )

    def select_files_via_dialog(self):
        root = Tk()
        root.withdraw()
        input_path = filedialog.askopenfilename(
            title="Select input OSM file",
            filetypes=[("OpenStudio Model", "*.osm")]
        )
        if not input_path:
            root.destroy()
            return None, None
        output_path = filedialog.asksaveasfilename(
            title="Select output OSM file",
            defaultextension=".osm",
            filetypes=[("OpenStudio Model", "*.osm")]
        )
        root.destroy()
        if not output_path:
            return None, None
        return input_path, output_path

    def set_lighting_density_all_spaces(self, model, target_density, app_only=False):
        count_spaces = 0
        count_lights = 0
        modified_defs = set()

        # Get all light definitions already in model (to avoid duplicates)
        existing_defs = {}
        for ld in model.getLightsDefinitions():
            # Reuse only if already at the target density
            if (ld.designLevelCalculationMethod() == "Watts/Area"
                    and ld.wattsperSpaceFloorArea().is_initialized()
                    and abs(ld.wattsperSpaceFloorArea().get() - target_density) < 0.01):
                existing_defs[target_density] = ld

        target_ld = existing_defs.get(target_density)

        for space in model.getSpaces():
            has_light = False
            lights_list = space.lights()
            if app_only and get_space_type_label(space) != "APP":
                for lights_obj in lights_list:
                    lights_obj.remove()
                continue
            for lights_obj in lights_list:
                has_light = True
                ld = lights_obj.lightsDefinition()
                # Only modify if not already correct
                if (ld.designLevelCalculationMethod() != "Watts/Area" or
                        not ld.wattsperSpaceFloorArea().is_initialized() or
                        abs(ld.wattsperSpaceFloorArea().get() - target_density) > 0.01):

                    # Reuse common definition if exists, otherwise create new and assign
                    if target_ld is None:
                        target_ld = openstudio.model.LightsDefinition(model)
                        target_ld.setName(f"Reference Lights Definition")
                        target_ld.setWattsperSpaceFloorArea(target_density)
                        logging.info(f"Created new LightsDefinition at {target_density} W/m²")
                    lights_obj.setLightsDefinition(target_ld)
                    modified_defs.add(target_ld.handle())

                else:
                    modified_defs.add(ld.handle())

                count_lights += 1
            if has_light:
                count_spaces += 1

        logging.info(f"Spaces with lighting: {count_spaces}")
        logging.info(f"Total Light objects processed: {count_lights}")
        logging.info(f"Unique lighting definitions used: {len(modified_defs)}")
        print(f"Spaces with lighting: {count_spaces}")
        print(f"Total Light objects processed: {count_lights}")
        print(f"Lighting power density set to {target_density} W/m².")

        return count_lights > 0

    def process_files(self, input_path, output_path, target_density=15.5, app_only=False):
        try:
            logging.info(f"Loading OSM file: {input_path}")
            model_opt = openstudio.model.Model.load(openstudio.path(input_path))
            if not model_opt.is_initialized():
                raise FileNotFoundError(f"Unable to load model: {input_path}")
            model = model_opt.get()

            scope = "APP spaces only (lighting system not evaluated)" if app_only else "all spaces with lighting (lighting system evaluated)"
            logging.info(f"Setting lighting density to {target_density} W/m² for {scope}.")
            modified = self.set_lighting_density_all_spaces(model, target_density, app_only)

            if not modified:
                print("No lighting objects found to update.")
                logging.warning("No lighting objects found to update.")
                return False

            logging.info(f"Saving updated model: {output_path}")
            if not model.save(openstudio.path(output_path), True):
                raise IOError(f"Failed to save model: {output_path}")

            print("Process completed successfully.")
            logging.info("Lighting density modification completed successfully.")
            return True

        except Exception as e:
            logging.error(f"Error during lighting density modification: {e}")
            print(f"Error: {e}")
            return False

    def run_standalone(self):
        input_path, output_path = self.select_files_via_dialog()
        if not input_path or not output_path:
            print("Execution cancelled by user.")
            return False
        return self.process_files(input_path, output_path)

    def run_automated(self, input_path, output_path, app_only=False):
        return self.process_files(input_path, output_path, app_only=app_only)

def main():
    modifier = LightingPowerDensityModifier()
    args = sys.argv[1:]

    if len(args) in (2, 3):
        app_only = len(args) == 3 and args[2].lower() == "app_only"
        success = modifier.run_automated(args[0], args[1], app_only)
        if success:
            print(args[1])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        success = modifier.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python ini_c_lighting_modifier.py [input.osm output.osm [app_only]]")
        print("Use app_only when the lighting system is not evaluated (reference DPI only in APP spaces).")
        print("Or run with no arguments for GUI mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()
