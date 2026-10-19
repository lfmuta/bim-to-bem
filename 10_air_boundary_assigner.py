import openstudio
import os
import tempfile
import shutil
import logging
import sys
from tkinter import Tk, filedialog

from spacetype_utils import get_space_type_label

class OSMAirBoundarySetter:
    """
    Identifies air boundary surfaces (ConstructionAirBoundary or constructions whose names contain "Air")
    and integrates the spaces connected by them into a single thermal zone, as required by INI-C item C.I.3.2
    (APT connected to APP without doors must be part of the APP thermal zone).
    Supports standalone execution with a GUI and automated execution via command line.
    """
    def __init__(self):
        """
        Initializes the air boundary setter and configures logging.
        """
        logging.basicConfig(
            filename="assign_air_boundary.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO,
            force=True
        )
        self.logger = logging.getLogger(__name__)

    def _create_or_get_default_air_boundary_construction(self, model):
        """
        Creates or retrieves a 'Default Air Boundary' construction. Air exchange method is set to None
        because the connected spaces are integrated into the same thermal zone.
        """
        default_air_boundary_name = "Default Air Boundary"
        for construction_ab in model.getConstructionAirBoundarys():
            if construction_ab.nameString() == default_air_boundary_name:
                self.logger.info(f"Found existing '{default_air_boundary_name}' construction.")
                return construction_ab
        self.logger.info(f"Creating new '{default_air_boundary_name}' construction.")
        air_boundary_construction = openstudio.model.ConstructionAirBoundary(model)
        air_boundary_construction.setName(default_air_boundary_name)
        air_boundary_construction.setAirExchangeMethod("None")
        return air_boundary_construction

    def create_temp_copy(self, file_path):
        """Creates a temporary copy of the file to avoid direct modifications to the original."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_path)[1])
        shutil.copy(file_path, temp_file.name)
        self.logger.debug(f"Temporary copy created: {temp_file.name}")
        return temp_file.name

    def _is_air_boundary(self, surface):
        construction_opt = surface.construction()
        if not construction_opt.is_initialized():
            return False
        construction = construction_opt.get()
        if construction.to_ConstructionAirBoundary().is_initialized():
            return True
        return "air" in construction.nameString().lower()

    def _zone_label(self, zone):
        labels = [get_space_type_label(space) for space in zone.spaces()]
        return "APP" if "APP" in labels else "APT"

    def set_air_boundary_to_model(self, model):
        """
        Assigns the air boundary construction to air surfaces and merges the thermal zones connected by them.
        Returns the number of surfaces converted to air boundary.
        """
        surfaces = model.getSurfaces()
        self.logger.info(f"Starting with {len(surfaces)} surfaces in the model.")
        default_air_boundary_construction = self._create_or_get_default_air_boundary_construction(model)

        air_surfaces = [s for s in surfaces if self._is_air_boundary(s)]
        surfaces_modified_count = 0
        for surface in air_surfaces:
            construction = surface.construction().get()
            if not construction.to_ConstructionAirBoundary().is_initialized():
                self.logger.info(
                    f"Surface '{surface.nameString()}' has construction '{construction.nameString()}' "
                    f"containing 'Air'. Replacing with '{default_air_boundary_construction.nameString()}'."
                )
                surface.setConstruction(default_air_boundary_construction)
                surfaces_modified_count += 1
        for construction_ab in model.getConstructionAirBoundarys():
            construction_ab.setAirExchangeMethod("None")

        parent = {}

        def find(handle):
            while parent[handle] != handle:
                parent[handle] = parent[parent[handle]]
                handle = parent[handle]
            return handle

        zones = {str(z.handle()): z for z in model.getThermalZones()}
        for handle in zones:
            parent[handle] = handle
        for surface in air_surfaces:
            adjacent_opt = surface.adjacentSurface()
            space_opt = surface.space()
            if not adjacent_opt.is_initialized() or not space_opt.is_initialized():
                continue
            adjacent_space_opt = adjacent_opt.get().space()
            if not adjacent_space_opt.is_initialized():
                continue
            zone_a = space_opt.get().thermalZone()
            zone_b = adjacent_space_opt.get().thermalZone()
            if not zone_a.is_initialized() or not zone_b.is_initialized():
                continue
            root_a = find(str(zone_a.get().handle()))
            root_b = find(str(zone_b.get().handle()))
            if root_a != root_b:
                parent[root_b] = root_a

        groups = {}
        for handle in zones:
            groups.setdefault(find(handle), []).append(zones[handle])

        merged_zones = 0
        for group in groups.values():
            if len(group) < 2:
                continue
            group.sort(key=lambda z: (self._zone_label(z) == "APP", sum(sp.floorArea() for sp in z.spaces())), reverse=True)
            target = group[0]
            for zone in group[1:]:
                for space in zone.spaces():
                    space.setThermalZone(target)
                    self.logger.info(f"Space '{space.nameString()}' integrated into thermal zone '{target.nameString()}'.")
                zone.remove()
                merged_zones += 1

        used = set()
        for planar in list(model.getSurfaces()) + list(model.getSubSurfaces()) + list(model.getShadingSurfaces()):
            if planar.construction().is_initialized():
                used.add(str(planar.construction().get().handle()))
        for construction in model.getConstructions():
            if len(construction.layers()) == 0 and str(construction.handle()) not in used:
                self.logger.info(f"Removing empty unused construction '{construction.nameString()}'.")
                construction.remove()

        self.logger.info(f"Finished: {surfaces_modified_count} surfaces converted to air boundary, {merged_zones} thermal zones merged.")
        print(f"Air boundary surfaces: {len(air_surfaces)}")
        print(f"Thermal zones merged (INI-C C.I.3.2): {merged_zones}")
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
            modified_count = self.set_air_boundary_to_model(model) # Call the new method

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
    setter = OSMAirBoundarySetter()
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
        print("Usage: python assign_air_boundary.py [input.osm output.osm]")
        print("Or run without arguments for GUI mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()
