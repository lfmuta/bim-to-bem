import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import openstudio
except ImportError:
    openstudio = None

from spacetype_utils import get_space_type_label

# Logging setup
LOG_FILENAME = f'skylight_removal_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILENAME, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


class OpenStudioSkylightRemover:
    """
    Removes all skylights (zenithal openings) from an OpenStudio model (.osm).
    Supports both GUI and CLI interfaces.
    All major actions and exceptions are logged.
    """

    def __init__(self, input_path=None, output_path=None, use_gui=False, assume_yes=False):
        self.input_path = Path(input_path) if input_path else None
        self.output_path = Path(output_path) if output_path else None
        self.use_gui = use_gui
        self.assume_yes = assume_yes
        self.model = None

    def is_apt_only_surface(self, surface):
        """Transparent elements of zones composed only of APT keep the real model characteristics (INI-C item C.I.4)."""
        space_opt = surface.space()
        if not space_opt.is_initialized():
            return False
        zone_opt = space_opt.get().thermalZone()
        spaces = zone_opt.get().spaces() if zone_opt.is_initialized() else [space_opt.get()]
        return all(get_space_type_label(space) != "APP" for space in spaces)

    def select_input_file_gui(self):
        """Display a file dialog to choose the input OSM file (GUI mode)."""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select OpenStudio Model (.osm)",
            filetypes=[("OpenStudio Model", "*.osm"), ("All Files", "*.*")],
            initialdir=Path.cwd()
        )
        root.destroy()
        if file_path:
            logging.info(f"Selected input via GUI: {file_path}")
            return Path(file_path)
        return None

    def select_output_file_gui(self, suggested_name="output.osm"):
        """Display a dialog to select the output OSM file name (GUI mode)."""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(
            title="Save Model Without Skylights",
            defaultextension=".osm",
            filetypes=[("OpenStudio Model", "*.osm"), ("All Files", "*.*")],
            initialdir=Path.cwd(),
            initialfile=suggested_name
        )
        root.destroy()
        if file_path:
            logging.info(f"Selected output via GUI: {file_path}")
            return Path(file_path)
        return None

    def load_model(self, path):
        """Load an OpenStudio model from path."""
        try:
            logging.info(f"Loading model: {path}")
            translator = openstudio.osversion.VersionTranslator()
            model_handle = translator.loadModel(openstudio.path(str(path)))
            if not model_handle.is_initialized():
                raise ValueError(f"Failed to load model: {path}")
            self.model = model_handle.get()
            logging.info("Model loaded successfully.")
        except Exception as exc:
            logging.error(f"Error loading model: {exc}")
            raise

    def identify_roof_surfaces(self):
        """Return a list of surfaces that are roof/ceiling type."""
        roof_surfaces = []
        for surface in self.model.getSurfaces():
            if surface.surfaceType().lower() in ("roofceiling", "roof"):
                roof_surfaces.append(surface)
        return roof_surfaces

    def analyze_skylights(self):
        """Return all existing skylights and summary statistics."""
        analysis = {
            'skylights': [],
            'total_skylights': 0,
            'total_skylight_area': 0.0,
            'total_roof_area': 0.0,
        }
        roof_surfaces = self.identify_roof_surfaces()
        for roof in roof_surfaces:
            analysis['total_roof_area'] += roof.grossArea()
            if self.is_apt_only_surface(roof):
                continue
            for subsurface in roof.subSurfaces():
                if subsurface.subSurfaceType().lower() == 'skylight':
                    area = subsurface.grossArea()
                    analysis['skylights'].append({
                        'name': subsurface.nameString(),
                        'parent_surface': roof.nameString(),
                        'area': area
                    })
                    analysis['total_skylight_area'] += area
        analysis['total_skylights'] = len(analysis['skylights'])
        return analysis

    def remove_all_skylights(self):
        """Remove all skylights from the model. Return detailed report."""
        report = {
            "skylights_removed": [],
            "total_removed": 0,
            "total_area_removed": 0.0,
            "errors": []
        }
        try:
            for surface in self.model.getSurfaces():
                if self.is_apt_only_surface(surface):
                    continue
                for subsurface in list(surface.subSurfaces()):
                    if subsurface.subSurfaceType().lower() == 'skylight':
                        try:
                            report["skylights_removed"].append({
                                "name": subsurface.nameString(),
                                "parent_surface": surface.nameString(),
                                "area": subsurface.grossArea()
                            })
                            report["total_area_removed"] += subsurface.grossArea()
                            subsurface.remove()
                            report["total_removed"] += 1
                        except Exception as exc:
                            msg = f"Error removing skylight '{subsurface.nameString()}': {exc}"
                            logging.error(msg)
                            report["errors"].append(msg)
        except Exception as exc:
            logging.error("Critical error while removing skylights.", exc_info=True)
            raise
        return report

    def save_model(self, out_path):
        """Save the OpenStudio model to the specified file path."""
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            success = self.model.save(openstudio.path(str(out_path)), True)
            if not success:
                raise IOError("OpenStudio returned False on save.")
            logging.info(f"Model saved to: {out_path}")
        except Exception as exc:
            logging.error(f"Error saving model: {exc}")
            raise

    def show_gui_summary_and_confirm(self, analysis):
        """Display a summary before removal and get user confirmation (GUI mode)."""
        root = tk.Tk()
        root.withdraw()
        if analysis['total_skylights'] == 0:
            messagebox.showinfo(
                "No Skylights Found",
                f"No skylights present.\nTotal Skylight Area: {analysis['total_skylight_area']:.2f} m²"
            )
            root.destroy()
            return True
        msg = (f"Total Skylights: {analysis['total_skylights']}\n"
               f"Total Skylight Area: {analysis['total_skylight_area']:.2f} m²\n"
               "Do you want to remove ALL skylights?")
        confirmed = messagebox.askyesno("Confirm Skylight Removal", msg, icon="warning")
        root.destroy()
        return confirmed

    def print_cli_summary(self, analysis):
        """Print out a summary before removal in CLI mode."""
        print("="*65)
        print("Skylight Analysis")
        print("="*65)
        print(f"Total Skylights: {analysis['total_skylights']}")
        print(f"Total Skylight Area: {analysis['total_skylight_area']:.2f} m²")
        print(f"Total Roof Area: {analysis['total_roof_area']:.2f} m²")
        if not analysis['total_skylights']:
            print("Model already has PAZ = 0% (no skylights).")
        else:
            print("\nFound skylights:")
            for sky in analysis['skylights']:
                print(f" - {sky['name']} (Area: {sky['area']:.2f} m²), on Surface: {sky['parent_surface']}")
        print("="*65)

    def run_gui(self):
        """Complete process in GUI mode."""
        try:
            self.input_path = self.select_input_file_gui()
            if not self.input_path:
                print("No input file selected. Operation cancelled.")
                return False
            suggested_name = f"no_skylights_{self.input_path.stem}.osm"
            self.output_path = self.select_output_file_gui(suggested_name)
            if not self.output_path:
                print("No output file selected. Operation cancelled.")
                return False

            self.load_model(self.input_path)
            analysis = self.analyze_skylights()
            if not self.show_gui_summary_and_confirm(analysis):
                print("Operation cancelled by user.")
                return False
            report = self.remove_all_skylights()
            self.save_model(self.output_path)
            if report['errors']:
                msg = f"Completed with some errors. {len(report['errors'])} skylights not removed."
                print(msg)
                messagebox.showerror("Partial Success", msg)
                for error in report['errors']:
                    print("Error:", error)
                return False
            else:
                msg = "All skylights removed. PAZ = 0% achieved!"
                print(msg)
                messagebox.showinfo("Success", msg)
                print(str(self.output_path))
                return True
        except Exception as exc:
            logging.error("Unhandled exception in GUI run.", exc_info=True)
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", str(exc))
            root.destroy()
            print(f"Error: {exc}\nSee log file for details.")
            return False

    def run_cli(self):
        """Complete process in CLI mode."""
        try:
            if not self.input_path or not self.input_path.exists():
                print("Input file not specified or doesn't exist.")
                return False

            if not self.output_path:
                out_name = f"no_skylights_{self.input_path.stem}.osm"
                self.output_path = self.input_path.parent / out_name

            self.load_model(self.input_path)
            analysis = self.analyze_skylights()
            self.print_cli_summary(analysis)
            if not analysis['total_skylights']:
                print("No skylights found, no action needed.")
                self.save_model(self.output_path)
                print(str(self.output_path))
                return True

            # Confirmation step
            if not self.assume_yes:
                user_input = input("Remove all skylights? (y/n): ").lower()
                if user_input not in ("y", "yes"):
                    print("Operation aborted by user.")
                    return False

            report = self.remove_all_skylights()
            self.save_model(self.output_path)
            if report['errors']:
                print(f"Completed with errors: {len(report['errors'])} skylights not removed.")
                for error in report['errors']:
                    print("Error:", error)
                print("Output file:", str(self.output_path))
                return False
            else:
                print("All skylights removed successfully. PAZ = 0% achieved!")
                print(str(self.output_path))
                return True
        except Exception as exc:
            logging.error("Unhandled exception in CLI run.", exc_info=True)
            print(f"Error: {exc}\nSee log file: {LOG_FILENAME}")
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove all skylights from an OpenStudio (.osm) model.",
        add_help=True
    )
    parser.add_argument("-i", "--input", help="Path to input .osm model file.")
    parser.add_argument("-o", "--output", help="Path to output .osm model file (default: auto-named in input folder).")
    parser.add_argument("--gui", action="store_true", help="Launch GUI (overrides CLI arguments).")
    parser.add_argument("-y", "--yes", action="store_true", help="Remove skylights without confirmation (automated mode).")
    args = parser.parse_args()

    if openstudio is None:
        msg = "OpenStudio Python bindings not found! Please install OpenStudio and set up environment variables."
        print(msg)
        logging.error(msg)
        sys.exit(1)

    # DEFAULT TO GUI IF NO INPUT AND NOT EXPLICITLY CLI
    if not any([args.input, args.output, args.gui]):
        print("No arguments provided. Launching GUI by default.")
        args.gui = True

    remover = OpenStudioSkylightRemover(
        input_path=args.input,
        output_path=args.output,
        use_gui=args.gui,
        assume_yes=args.yes
    )
    try:
        if args.gui:
            success = remover.run_gui()
        else:
            success = remover.run_cli()
        if success:
            print("Process completed successfully.")
            sys.exit(0)
        else:
            print("Process terminated with errors.")
            sys.exit(2)
    except Exception as exc:
        logging.critical("Fatal error in main execution.", exc_info=True)
        print(f"Fatal error: {exc}\nSee details in {LOG_FILENAME}")
        sys.exit(10)

if __name__ == "__main__":
    main()
