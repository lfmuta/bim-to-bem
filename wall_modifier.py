import openstudio
import os
import sys
import logging
from tkinter import Tk, filedialog

from reference_construction_utils import ReferenceConstructionBuilder, get_face_absorptances, apply_to_surfaces

class WallConstructionModifier:
    def __init__(self):
        logging.basicConfig(
            filename="wall_construction_modifier.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        # Define the target construction name patterns (case-sensitive)
        self.target_construction_terms = [
            "InteriorWall",
            "ExteriorWall",
            "UndergroundWall"
        ]
        self.reference_outside_face = {"solar": 0.5, "thermal": 0.9, "visible": 0.7}

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

    def create_inic_materials(self, model):
        """Creates the INI-C wall layer specification (Table A.9)."""
        layer_specs = [
            {"name": "Reference_Layer_1_External", "thickness": 0.025, "conductivity": 1.15, "density": 2000.0, "specific_heat": 1000.0},
            {"name": "Reference_Layer_2_Middle", "thickness": 0.0134, "conductivity": 0.90, "density": 1600.0, "specific_heat": 920.0},
            {"name": "Reference_Air_Gap", "air_gap_resistance": 0.175},
            {"name": "Reference_Layer_2_Middle", "thickness": 0.0134, "conductivity": 0.90, "density": 1600.0, "specific_heat": 920.0},
            {"name": "Reference_Layer_3_Internal", "thickness": 0.025, "conductivity": 1.15, "density": 2000.0, "specific_heat": 1000.0},
        ]
        logging.info("INI-C wall layers defined.")
        return layer_specs

    def create_inic_construction(self, model, materials):
        """Creates the INI-C wall construction builder (one construction per face absorptance combination)."""
        builder = ReferenceConstructionBuilder(model, "Reference_Wall", materials)
        logging.info("Construction builder 'Reference_Wall' created.")
        return builder

    def construction_for_surface(self, surface, builder):
        """Exterior face uses the reference absorptance; internal faces keep the absorptance of the real model."""
        original = surface.construction().get() if surface.construction().is_initialized() else None
        outside_face, inside_face = get_face_absorptances(original)
        if surface.outsideBoundaryCondition() == "Outdoors":
            outside_face = dict(self.reference_outside_face)
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
        """Applies the reference construction to identified surfaces and keeps interzone pairs consistent."""
        count = apply_to_surfaces(target_surfaces, lambda surface: self.construction_for_surface(surface, construction))
        logging.info(f"Total modified surfaces: {count}")
        print(f"Total modified surfaces: {count}")
        return count

    def process_files(self, input_path, output_path):
        try:
            logging.info(f"Loading OSM model: {input_path}")
            model_opt = openstudio.model.Model.load(openstudio.path(input_path))
            if not model_opt.is_initialized():
                raise FileNotFoundError(f"Unable to load model: {input_path}")
            model = model_opt.get()

            # Check if there are target surfaces before creating materials
            target_surfaces = self.get_target_surfaces_by_construction_name(model)
            if len(target_surfaces) == 0:
                print("No surfaces found with target construction names (InteriorWall, ExteriorWall, UndergroundWall).")
                logging.warning("No target surfaces found for modification.")
                return False

            logging.info("Creating INI-C materials and constructions.")
            materials = self.create_inic_materials(model)
            construction = self.create_inic_construction(model, materials)

            logging.info("Applying construction to target surfaces.")
            modified_count = self.apply_construction_to_surfaces(target_surfaces, construction)

            if modified_count == 0:
                print("No surfaces were modified (possibly error occurred).")
                return False

            logging.info(f"Saving new model: {output_path}")
            if not model.save(openstudio.path(output_path), True):
                raise IOError(f"Failed to save model: {output_path}")

            logging.info("Process completed successfully.")
            print("Process completed successfully.")
            return True
        except Exception as e:
            logging.error(f"Error during wall construction modification: {e}")
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
    modifier = WallConstructionModifier()
    args = sys.argv[1:]
    
    if len(args) == 2:
        # Automated mode (CLI arguments)
        success = modifier.run_automated(args[0], args[1])
        if success:
            print(args[1]) # for script chaining
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        # Standalone (dialog/file browser)
        success = modifier.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python ini_c_wall_modifier.py [input.osm output.osm]")
        print("Or run with no arguments for GUI mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()
