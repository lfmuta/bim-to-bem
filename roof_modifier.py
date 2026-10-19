import openstudio
import os
import sys
import logging
from tkinter import Tk, filedialog

from reference_construction_utils import ReferenceConstructionBuilder, get_face_absorptances, apply_to_surfaces

class RoofConstructionModifier:
    def __init__(self):
        logging.basicConfig(
            filename="roof_construction_modifier.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        # Define the target construction name patterns (case-sensitive)
        self.target_construction_terms = [
            "Roof"
        ]
        self.reference_outside_face = {"solar": 0.8, "thermal": 0.9, "visible": 0.7}

    def log(self, message):
        logging.info(message)

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
            title="Select output OSM file location",
            defaultextension=".osm",
            filetypes=[("OpenStudio Model", "*.osm")]
        )
        root.destroy()
        if not output_path:
            return None, None
        return input_path, output_path

    def create_inic_roof_materials(self, model):
        """Creates the INI-C roof layer specification (Table A.9)."""
        materials = [
            # Component 5 (external): 0.800cm, λ=0.950, ρ=1900, c=0.840, Absorptance=0.8
            {"name": "Reference_Component_5_External_Roof", "thickness": 0.008, "conductivity": 0.950, "density": 1900.0, "specific_heat": 840.0},
            # Roof air gap: 25.0cm, Rt=0.2100
            {"name": "Reference_Roof_Air_Gap", "air_gap_resistance": 0.2100},
            # Component 6 (internal): 10.0cm, λ=1.75, ρ=2200, c=1.00
            {"name": "Reference_Component_6_Internal_Roof", "thickness": 0.10, "conductivity": 1.75, "density": 2200.0, "specific_heat": 1000.0},
        ]
        self.log("INI-C roof layers defined successfully.")
        return materials

    def create_inic_roof_construction(self, model, materials):
        """Creates the INI-C roof construction builder (one construction per face absorptance combination)."""
        builder = ReferenceConstructionBuilder(model, "Reference_Roof", materials)
        self.log("Construction builder 'Reference_Roof' created.")
        return builder

    def construction_for_surface(self, surface, builder):
        """Exterior face uses the reference absorptance (0.8); the internal face keeps the absorptance of the real model."""
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
                    self.log(f"Found target surface '{surf.nameString()}' with construction '{construction_name}' containing term '{term}'")
                    break
        
        self.log(f"{len(target_surfaces)} surfaces found with target construction names")
        return target_surfaces

    def assign_roof_construction(self, model, construction):
        """Assigns the reference construction to surfaces with target construction names."""
        target_surfaces = self.get_target_surfaces_by_construction_name(model)
        count = apply_to_surfaces(target_surfaces, lambda surface: self.construction_for_surface(surface, construction))
        self.log(f"Roofs modified: {count}")
        print(f"Roofs modified: {count}")
        return count

    def process_files(self, input_path, output_path):
        try:
            self.log(f"Loading model: {input_path}")
            model_opt = openstudio.model.Model.load(openstudio.path(input_path))
            if not model_opt.is_initialized():
                raise FileNotFoundError(f"Unable to load model: {input_path}")
            model = model_opt.get()

            # Check if there are target surfaces before creating materials
            target_surfaces = self.get_target_surfaces_by_construction_name(model)
            if len(target_surfaces) == 0:
                print("No surfaces found with target construction names (Roof).")
                self.log("No target surfaces found for modification.")
                return False

            self.log("Creating INI-C roof materials and construction.")
            materials = self.create_inic_roof_materials(model)
            construction = self.create_inic_roof_construction(model, materials)

            self.log("Assigning construction to target surfaces.")
            modified_count = self.assign_roof_construction(model, construction)

            if modified_count == 0:
                print("No surfaces were modified (possibly error occurred).")
                return False

            self.log(f"Saving new model: {output_path}")
            if not model.save(openstudio.path(output_path), True):
                raise IOError(f"Failed to save model: {output_path}")

            self.log("Process completed successfully.")
            print("Process completed successfully.")
            return True
        except Exception as e:
            logging.error(f"Error during roof modification: {e}")
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
    modifier = RoofConstructionModifier()
    args = sys.argv[1:]
    
    if len(args) == 2:
        # Automated mode (CLI)
        success = modifier.run_automated(args[0], args[1])
        if success:
            print(args[1])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        # Standalone mode (dialog)
        success = modifier.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python ini_c_roof_modifier.py [input.osm output.osm]")
        print("Or run with no arguments for GUI mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()
