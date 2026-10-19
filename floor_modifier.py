import openstudio
import os
import sys
import logging
from tkinter import Tk, filedialog

from reference_construction_utils import ReferenceConstructionBuilder, get_face_absorptances, apply_to_surfaces

class INICFloorModifier:
    def __init__(self):
        logging.basicConfig(
            filename="inic_floor_modifier.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        # Define the target construction name patterns (case-sensitive)
        self.target_construction_terms = [
            "InteriorFloor",
            "ExposedFloor",
            "UndergroundSlab",
            "RaisedFloor",
            "SlabOnGrade"
        ]

    def select_files_via_dialog(self):
        root = Tk()
        root.withdraw()
        input_path = filedialog.askopenfilename(
            title="Select input file (.osm)",
            filetypes=[("OpenStudio Model", "*.osm")]
        )
        if not input_path:
            root.destroy()
            return None, None
        output_path = filedialog.asksaveasfilename(
            title="Select destination for modified model",
            defaultextension=".osm",
            filetypes=[("OpenStudio Model", "*.osm")]
        )
        root.destroy()
        if not output_path:
            return None, None
        return input_path, output_path

    def create_inic_floor_material(self, model):
        """Creates the standard INI-C floor layer specification (Table A.9, component 4: 10cm, 1.75, 2200, 1.00).
        The 10 cm layer is split in two 5 cm layers of the same material, so each face keeps the absorptance of the real model."""
        layer_specs = [
            {"name": "Reference_Component_4_Floor", "thickness": 0.05, "conductivity": 1.75, "density": 2200.0, "specific_heat": 1000.0},
            {"name": "Reference_Component_4_Floor", "thickness": 0.05, "conductivity": 1.75, "density": 2200.0, "specific_heat": 1000.0},
        ]
        logging.info("INI-C floor layers defined: 10cm, 1.75, 2200, 1.00")
        return layer_specs

    def create_inic_floor_construction(self, model, material):
        """Creates INI-C floor construction builder."""
        builder = ReferenceConstructionBuilder(model, "Reference_Floor", material)
        logging.info("INI-C construction builder created for floors.")
        return builder

    def construction_for_surface(self, surface, builder):
        """Both faces keep the absorptance of the real model."""
        original = surface.construction().get() if surface.construction().is_initialized() else None
        outside_face, inside_face = get_face_absorptances(original)
        return builder.get(outside_face, inside_face)

    def get_target_surfaces_by_construction_name(self, model):
        """Identifies surfaces with constructions containing target terms."""
        target_surfaces = []

        for surf in model.getSurfaces():
            construction_opt = surf.construction()

            if not construction_opt.is_initialized():
                continue

            construction = construction_opt.get()
            construction_name = construction.nameString()

            # Check if construction name contains any of the target terms (case-sensitive)
            for term in self.target_construction_terms:
                if term in construction_name:
                    target_surfaces.append(surf)
                    logging.info(f"Found target surface '{surf.nameString()}' with construction '{construction_name}' containing term '{term}'")
                    break

        logging.info(f"{len(target_surfaces)} surfaces found with target construction names")
        return target_surfaces

    def apply_construction_to_surfaces(self, target_surfaces, construction):
        """Applies the reference construction to identified surfaces and keeps interzone pairs (floor and ceiling) consistent."""
        mod_count = apply_to_surfaces(target_surfaces, lambda surface: self.construction_for_surface(surface, construction))
        logging.info(f"Total modified surfaces: {mod_count}")
        return mod_count

    def validate_application(self, model):
        """Checks how many surfaces are now using the INI-C construction."""
        count = 0
        for surf in model.getSurfaces():
            c = surf.construction()
            if c.is_initialized() and "Reference_Floor" in c.get().nameString():
                count += 1
        logging.info(f"Surfaces with INI-C construction: {count}")
        return count

    def process_files(self, input_path, output_path):
        try:
            logging.info(f"Loading model: {input_path}")
            model_opt = openstudio.model.Model.load(openstudio.path(input_path))
            if not model_opt.is_initialized():
                raise FileNotFoundError(f"Could not load file: {input_path}")

            model = model_opt.get()

            target_surfaces = self.get_target_surfaces_by_construction_name(model)

            if len(target_surfaces) == 0:
                print("No surfaces found with target construction names (InteriorFloor, ExposedFloor, UndergroundSlab, RaisedFloor, SlabOnGrade).")
                logging.warning("No target surfaces found for modification.")
                return False

            material = self.create_inic_floor_material(model)
            construction = self.create_inic_floor_construction(model, material)

            modified = self.apply_construction_to_surfaces(target_surfaces, construction)

            print(f"Total modified surfaces: {modified}")

            if modified == 0:
                print("No surfaces were modified (possibly error occurred).")
                return False

            if not model.save(openstudio.path(output_path), True):
                raise IOError(f"Error saving model: {output_path}")

            count_val = self.validate_application(model)
            print(f"Total verified with INI-C construction: {count_val}")
            print("Process completed successfully.")
            return True

        except Exception as e:
            logging.error(f"Error modifying surfaces: {e}")
            print(f"Error: {e}")
            return False

    def run_standalone(self):
        input_path, output_path = self.select_files_via_dialog()
        if not input_path or not output_path:
            print("Execution cancelled by user.")
            return False
        return self.process_files(input_path, output_path)

    def run_automated(self, input_path, output_path):
        return self.process_files(input_path, output_path)

def main():
    modifier = INICFloorModifier()
    args = sys.argv[1:]

    if len(args) == 2:
        success = modifier.run_automated(args[0], args[1])
        if success:
            print(args[1])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        success = modifier.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python inic_floor_modifier.py [input.osm output.osm]")
        print("Or run with no arguments for file dialog mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()
