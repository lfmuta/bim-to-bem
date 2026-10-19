import openstudio
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import sys
import logging
import argparse
import traceback
from datetime import datetime

class ShadingSurfaceRemover:
    """
    Removes fixed facade shading devices (brises, louvers, overhangs, balconies) from an OpenStudio model (.osm),
    as required for the INI-C reference condition (item C.I.4). Shading surfaces from the surroundings (Site),
    rooftop elements and other building elements are kept in both models.
    Space shading groups are removed. Building and Site shading surfaces are removed only when their names
    contain one of the facade device keywords, or when they are explicitly selected.
    Provides both CLI and GUI usage. Logs process details for debugging and auditing.
    """
    FACADE_DEVICE_KEYWORDS = ["brise", "veneziana", "beiral", "marquise", "sacada", "varanda",
                              "louver", "overhang", "balcony", "shading device"]

    def __init__(self, log_path=None, names_to_remove=None):
        self.model = None
        self.input_file = None
        self.output_file = None
        self.names_to_remove = set(names_to_remove) if names_to_remove is not None else None
        self._walls = None
        log_file = log_path or f"shading_removal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        logging.info("Initialized ShadingSurfaceRemover.")

    def select_input_file_gui(self):
        """Selects input .osm file using GUI dialog."""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select OpenStudio Model (.osm)",
            filetypes=[("OpenStudio Model", "*.osm"), ("All Files", "*.*")]
        )
        root.destroy()
        if file_path:
            return Path(file_path)
        return None

    def select_output_file_gui(self, input_file):
        """Selects output file location via GUI dialog, with empty default filename."""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(
            title="Save Model Without Shading Surfaces",
            defaultextension=".osm",
            filetypes=[("OpenStudio Model", "*.osm"), ("All Files", "*.*")],
            initialdir=input_file.parent,
            initialfile=''  # No suggested filename; user must provide one
        )
        root.destroy()
        if file_path:
            return Path(file_path)
        return None

    def load_model(self, osm_path):
        """Loads the OpenStudio model from file."""
        try:
            logging.info(f"Loading OSM model: {osm_path}")
            translator = openstudio.osversion.VersionTranslator()
            model_handle = translator.loadModel(openstudio.path(str(osm_path)))
            if not model_handle.is_initialized():
                raise ValueError(f"Failed to load model: {osm_path}")
            self.model = model_handle.get()
            logging.info("Model loaded successfully.")
            return True
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            return False

    def analyze_shading(self):
        """Analyzes existing shading surfaces and groups in the model."""
        if not self.model:
            return None
        analysis = {
            "shading_surfaces": [],
            "shading_groups": [],
            "total_surfaces": 0,
            "total_groups": 0
        }
        shading_surfaces = self.model.getShadingSurfaces()
        analysis["total_surfaces"] = len(shading_surfaces)
        for surface in shading_surfaces:
            info = {
                "name": surface.nameString(),
                "type": surface.iddObjectType().valueName(),
                "has_construction": surface.construction().is_initialized(),
                "has_transmittance_schedule": surface.transmittanceSchedule().is_initialized()
            }
            if info["has_construction"]:
                info["construction_name"] = surface.construction().get().nameString()
            if info["has_transmittance_schedule"]:
                info["transmittance_schedule_name"] = surface.transmittanceSchedule().get().nameString()
            analysis["shading_surfaces"].append(info)
        shading_groups = self.model.getShadingSurfaceGroups()
        analysis["total_groups"] = len(shading_groups)
        for group in shading_groups:
            group_info = {
                "name": group.nameString(),
                "type": group.shadingSurfaceType(),
                "surfaces_in_group": [s.nameString() for s in group.shadingSurfaces()]
            }
            analysis["shading_groups"].append(group_info)
        logging.info("Shading surfaces and groups analyzed: %s", analysis)
        return analysis

    def print_analysis(self, analysis):
        """Prints a summary report of current shading objects."""
        print("\n" + "="*50)
        print("SHADING SURFACE ANALYSIS")
        print("="*50)
        print(f"\nTotal Shading Surfaces: {analysis['total_surfaces']}")
        print(f"Total Shading Surface Groups: {analysis['total_groups']}")

    def _exterior_walls(self):
        if self._walls is None:
            self._walls = []
            for surface in self.model.getSurfaces():
                if surface.surfaceType() != "Wall" or surface.outsideBoundaryCondition() != "Outdoors":
                    continue
                space_opt = surface.space()
                if not space_opt.is_initialized():
                    continue
                to_building = space_opt.get().buildingTransformation()
                vertices = [to_building * v for v in surface.vertices()]
                points = openstudio.Point3dVector(vertices)
                align = openstudio.Transformation.alignFace(points)
                local = [align.inverse() * v for v in vertices]
                xs = [p.x() for p in local]
                ys = [p.y() for p in local]
                self._walls.append((align.inverse(), min(xs), max(xs), min(ys), max(ys)))
        return self._walls

    def is_attached_to_facade(self, surface, tolerance=0.15):
        """Returns True when the shading surface touches an exterior wall (brises, overhangs, fins, balconies)."""
        group_opt = surface.shadingSurfaceGroup()
        to_building = group_opt.get().buildingTransformation() if group_opt.is_initialized() else openstudio.Transformation()
        vertices = [to_building * v for v in surface.vertices()]
        for to_local, x_min, x_max, y_min, y_max in self._exterior_walls():
            for v in vertices:
                p = to_local * v
                if abs(p.z()) <= tolerance and x_min - tolerance <= p.x() <= x_max + tolerance and y_min - tolerance <= p.y() <= y_max + tolerance:
                    return True
        return False

    def is_facade_device(self, surface):
        """Returns True when the shading surface is a fixed facade device to be removed in the reference model."""
        if self.names_to_remove is not None:
            return surface.nameString() in self.names_to_remove
        group_opt = surface.shadingSurfaceGroup()
        group_type = group_opt.get().shadingSurfaceType() if group_opt.is_initialized() else ""
        if group_type == "Space":
            return True
        if group_type == "Site":
            return False
        names = surface.nameString().lower()
        if group_opt.is_initialized():
            names += " " + group_opt.get().nameString().lower()
        if any(keyword in names for keyword in self.FACADE_DEVICE_KEYWORDS):
            return True
        return self.is_attached_to_facade(surface)

    def remove_shading(self):
        """
        Removes fixed facade shading devices and empty shading surface groups from the model.
        Returns a report about objects removed and any errors.
        """
        if not self.model:
            return False, "Model not loaded"
        report = {
            "surfaces_removed": [],
            "surfaces_kept": [],
            "groups_removed": [],
            "total_removed": 0,
            "errors": []
        }
        try:
            shading_surfaces = [s for s in self.model.getShadingSurfaces() if self.is_facade_device(s)]
            report["surfaces_kept"] = [s.nameString() for s in self.model.getShadingSurfaces() if not self.is_facade_device(s)]
            logging.info(f"Removing {len(shading_surfaces)} facade shading surfaces. Keeping {len(report['surfaces_kept'])}.")
            for surf in shading_surfaces:
                name = surf.nameString()
                try:
                    surf.remove()
                    report["surfaces_removed"].append(name)
                    report["total_removed"] += 1
                    logging.info(f"Removed shading surface: {name}")
                except Exception as e:
                    msg = f"Error removing surface '{name}': {e}"
                    report["errors"].append(msg)
                    logging.error(msg)
            # Remove empty groups
            shading_groups = self.model.getShadingSurfaceGroups()
            for group in shading_groups:
                group_name = group.nameString()
                if not group.shadingSurfaces():
                    try:
                        group.remove()
                        report["groups_removed"].append(group_name)
                        report["total_removed"] += 1
                        logging.info(f"Removed empty shading group: {group_name}")
                    except Exception as e:
                        msg = f"Error removing group '{group_name}': {e}"
                        report["errors"].append(msg)
                        logging.error(msg)
            return True, report
        except Exception as e:
            logging.error(f"Error during shading removal: {e}")
            return False, str(e)

    def save_model(self, output_path):
        """Saves the modified model to disk."""
        if not self.model:
            return False, "Model not loaded"
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            success = self.model.save(openstudio.path(str(output_path)), True)
            if success:
                logging.info(f"Model saved successfully: {output_path}")
                return True, str(output_path)
            else:
                logging.error(f"Failed to save model (OpenStudio returned False): {output_path}")
                return False, "Failed to save model (OpenStudio returned False)"
        except Exception as e:
            logging.error(f"Error saving model: {e}")
            return False, f"Error saving model: {e}"

    def verify_clean(self):
        """Checks if any facade shading surfaces remain after removal."""
        if not self.model:
            return None
        final_surfaces = [s for s in self.model.getShadingSurfaces() if self.is_facade_device(s)]
        final_groups = self.model.getShadingSurfaceGroups()
        return {
            "surfaces_remaining": len(final_surfaces),
            "groups_remaining": len(final_groups),
            "completely_clean": len(final_surfaces) == 0,
            "remaining_surface_names": [s.nameString() for s in final_surfaces],
            "remaining_group_names": [g.nameString() for g in final_groups]
        }

    def run_pipeline(self, input_file, output_file):
        """
        Runs the tool without UI for pipeline/CLI automation.
        Returns True if successful, else False.
        """
        self.input_file = input_file
        self.output_file = output_file
        print("="*60)
        print("SHADING SURFACE REMOVAL TOOL (Pipeline Mode)")
        print("="*60)
        print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Pipeline run: {input_file} -> {output_file}")
        try:
            if not self.load_model(self.input_file):
                print("ERROR: Failed to load model.")
                return False
            analysis = self.analyze_shading()
            self.print_analysis(analysis)
            success, report = self.remove_shading()
            if not success:
                print(f"ERROR: Error during removal: {report}")
                return False
            saved, save_msg = self.save_model(self.output_file)
            if not saved:
                print(f"ERROR: Error saving model: {save_msg}")
                return False
            verification = self.verify_clean()
            print("\nREMOVAL SUMMARY")
            print("="*35)
            print(f"Original file: {self.input_file}")
            print(f"Output file:   {self.output_file}")
            print(f"Surfaces removed: {len(report['surfaces_removed'])}")
            print(f"Surfaces kept (surroundings and building elements): {len(report['surfaces_kept'])}")
            print(f"Groups removed:   {len(report['groups_removed'])}")
            if verification["completely_clean"]:
                print("SUCCESS: All facade shading surfaces removed.")
            else:
                print("WARNING: Some facade shading surfaces remain:")
                for s in verification["remaining_surface_names"]:
                    print(f"    - {s}")
            print("\nEnd: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print(self.output_file)
            return True
        except Exception as e:
            print(f"ERROR: Unexpected error: {e}")
            logging.error("Exception in pipeline run", exc_info=True)
            return False

    def run_gui(self):
        """
        Complete GUI workflow for interactive usage.
        No dialog interruptions during removal.
        """
        print("="*60)
        print("SHADING SURFACE REMOVAL TOOL (GUI Mode)")
        print("="*60)
        print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            self.input_file = self.select_input_file_gui()
            if not self.input_file:
                print("ERROR: No file selected. Operation cancelled.")
                return False
            if not self.load_model(self.input_file):
                print("ERROR: Failed to load model. Exiting.")
                return False
            analysis = self.analyze_shading()
            self.print_analysis(analysis)
            # No confirmation dialog: proceed directly
            self.output_file = self.select_output_file_gui(self.input_file)
            if not self.output_file:
                print("ERROR: Output location not selected. Operation cancelled.")
                return False
            success, report = self.remove_shading()
            if not success:
                print(f"ERROR: Error during removal: {report}")
                return False
            saved, save_msg = self.save_model(self.output_file)
            if not saved:
                print(f"ERROR: Error saving model: {save_msg}")
                return False
            verification = self.verify_clean()
            print("\nREMOVAL SUMMARY")
            print("="*35)
            print(f"Original file: {self.input_file}")
            print(f"Output file:   {self.output_file}")
            print(f"Surfaces removed: {len(report['surfaces_removed'])}")
            print(f"Surfaces kept (surroundings and building elements): {len(report['surfaces_kept'])}")
            print(f"Groups removed:   {len(report['groups_removed'])}")
            if verification['completely_clean']:
                print("SUCCESS: All facade shading surfaces were removed.")
            else:
                print("WARNING: Some facade shading surfaces remain:")
                for s in verification["remaining_surface_names"]:
                    print(f"    - {s}")
            print("\nEnd: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True
        except Exception as e:
            print(f"ERROR: Unexpected error: {e}")
            logging.error("Exception in GUI run", exc_info=True)
            return False

def main():
    """
    Main entry point - handles command-line arguments and orchestrates the workflow.
    """
    parser = argparse.ArgumentParser(description="Remove fixed facade shading devices from an OpenStudio model (.osm) for the INI-C reference condition.")
    parser.add_argument("-i", "--input", help="Path to the input OSM file.")
    parser.add_argument("-o", "--output", help="Path to save the cleaned OSM file.")
    parser.add_argument("-l", "--logfile", help="Optional: path for the log file.")
    parser.add_argument("-n", "--names", nargs="*", help="Optional: exact names of the shading surfaces to remove. When omitted, Space shading groups, surfaces with facade device keywords and surfaces attached to exterior walls are removed.")
    args = parser.parse_args()

    try:
        print(f"OpenStudio Python bindings version: {openstudio.openStudioVersion()}")
    except Exception:
        print("ERROR: OpenStudio Python bindings not found or not working.")
        print("Install OpenStudio and ensure Python bindings are accessible.")
        sys.exit(1)

    remover = ShadingSurfaceRemover(log_path=args.logfile, names_to_remove=args.names)
    if args.input and args.output:
        # CLI/pipeline mode: fully automated, no dialogs
        input_file = Path(args.input)
        output_file = Path(args.output)
        success = remover.run_pipeline(input_file, output_file)
    else:
        # GUI/interactive mode
        success = remover.run_gui()
    if success:
        print("Shading surface removal completed successfully.")
        sys.exit(0)
    else:
        print("ERROR: Shading surface removal finished with errors.")
        sys.exit(2)

if __name__ == "__main__":
    main()
