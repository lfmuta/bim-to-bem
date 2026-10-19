import openstudio
import os
import sys
import shutil
import tempfile
import logging
from tkinter import Tk, filedialog

from spacetype_utils import get_space_type_label

class AirflowAssigner:
    def __init__(self, outdoor_air_per_person=0.0075, outdoor_air_per_area=0.0):
        logging.basicConfig(
            filename="assign_airflow.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        # Outdoor air for APP spaces (NBR 16401 / NBR 17037)
        self.outdoor_air_per_person = outdoor_air_per_person  # m³/s per person
        self.outdoor_air_per_area = outdoor_air_per_area  # m³/s per m²
        # Crack infiltration for closed openings (INI-C Table C.4)
        self.window_crack_coefficient = 0.00063  # kg/(s.m)
        self.window_crack_exponent = 0.63
        self.door_crack_coefficient = 0.0024  # kg/(s.m)
        self.door_crack_exponent = 0.59
        self.discharge_coefficient = 0.60
        self.minimum_density_difference = 0.0001  # kg/m³
        self.window_types = ["FixedWindow", "OperableWindow", "Skylight", "TubularDaylightDome", "TubularDaylightDiffuser"]
        self.door_types = ["Door", "GlassDoor", "OverheadDoor"]

    def remove_infiltration_objects(self, model):
        """Removes design flow rate and leakage area infiltration objects from all spaces."""
        removed = 0
        for obj in model.getSpaceInfiltrationDesignFlowRates():
            obj.remove()
            removed += 1
        for obj in model.getSpaceInfiltrationEffectiveLeakageAreas():
            obj.remove()
            removed += 1
        logging.info(f"Removed {removed} infiltration objects (replaced by crack infiltration)")
        return removed

    def update_outdoor_air(self, model):
        """Applies outdoor air to thermal zones with APP spaces and removes it from zones with only APT spaces.
        All spaces of a zone share the same object, so APT spaces integrated into an APP zone (INI-C item C.I.3.2)
        are treated as part of the APP zone."""
        spaces_processed = {"APP": 0, "APT": 0, "UNCLASSIFIED": 0}
        for space in model.getSpaces():
            if space.designSpecificationOutdoorAir().is_initialized():
                space.designSpecificationOutdoorAir().get().remove()
        for zone in sorted(model.getThermalZones(), key=lambda z: z.nameString()):
            spaces = sorted(zone.spaces(), key=lambda sp: sp.nameString())
            labels = [get_space_type_label(space) for space in spaces]
            if "APP" in labels:
                oa_object = openstudio.model.DesignSpecificationOutdoorAir(model)
                oa_object.setName(f"Outdoor Air {zone.nameString()}")
                oa_object.setOutdoorAirMethod("Sum")
                oa_object.setOutdoorAirFlowperPerson(self.outdoor_air_per_person)
                oa_object.setOutdoorAirFlowperFloorArea(self.outdoor_air_per_area)
                for space in spaces:
                    space.setDesignSpecificationOutdoorAir(oa_object)
                    spaces_processed["APP"] += 1
                logging.info(f"APP | Outdoor air assigned for zone: {zone.nameString()} ({len(spaces)} spaces)")
            else:
                for space, label in zip(spaces, labels):
                    key = "APT" if label == "APT" else "UNCLASSIFIED"
                    spaces_processed[key] += 1
                    if key == "UNCLASSIFIED":
                        msg = f"UNCLASSIFIED | No outdoor air updates performed for space: {space.nameString()}. "
                        if space.spaceType().is_initialized():
                            msg += f"SpaceType: {space.spaceType().get().nameString()}"
                        else:
                            msg += "SpaceType: None"
                        logging.warning(msg)
                logging.info(f"APT | No outdoor air for zone: {zone.nameString()}")
        return spaces_processed

    def _building_geometry(self, model):
        """Returns number of stories, aspect ratio and long axis azimuth for wind pressure calculation."""
        xs, ys, zs = [], [], []
        for surface in model.getSurfaces():
            space_opt = surface.space()
            if not space_opt.is_initialized():
                continue
            transformation = space_opt.get().buildingTransformation()
            for vertex in surface.vertices():
                p = transformation * vertex
                xs.append(p.x())
                ys.append(p.y())
                zs.append(p.z())
        if not xs:
            return 1, 1.0, 0.0
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        long_axis = max(dx, dy)
        short_axis = max(min(dx, dy), 0.01)
        aspect_ratio = max(min(short_axis / long_axis, 1.0), 0.01) if long_axis > 0 else 1.0
        north_axis = model.getBuilding().northAxis()
        azimuth = (north_axis + (90.0 if dx >= dy else 0.0)) % 180.0
        stories = len(model.getBuildingStorys())
        return stories, aspect_ratio, azimuth

    def _remove_airflow_network_objects(self, model):
        for obj in model.getAirflowNetworkSurfaces():
            obj.remove()
        for obj in model.getAirflowNetworkSimpleOpenings():
            obj.remove()
        for obj in model.getAirflowNetworkZones():
            obj.remove()

    def _zone_of(self, planar_surface):
        space_opt = planar_surface.space()
        if not space_opt.is_initialized():
            return None
        zone_opt = space_opt.get().thermalZone()
        if not zone_opt.is_initialized():
            return None
        return zone_opt.get()

    def apply_airflow_network(self, model):
        """Models all windows and doors closed with crack infiltration (INI-C C.I.6 and Table C.4)."""
        self._remove_airflow_network_objects(model)

        stories, aspect_ratio, azimuth = self._building_geometry(model)
        control = model.getAirflowNetworkSimulationControl()
        control.setName("AirflowNetwork INI-C")
        control.setAirflowNetworkControl("MultizoneWithoutDistribution")
        control.setWindPressureCoefficientType("SurfaceAverageCalculation")
        control.setBuildingType("HighRise" if stories > 3 else "LowRise")
        control.setBuildingAspectRatio(aspect_ratio)
        control.setAzimuthAngleofLongAxisofBuilding(azimuth)

        window_component = openstudio.model.AirflowNetworkSimpleOpening(
            model, self.window_crack_coefficient, self.window_crack_exponent,
            self.minimum_density_difference, self.discharge_coefficient)
        window_component.setName("INI-C Window Crack")
        door_component = openstudio.model.AirflowNetworkSimpleOpening(
            model, self.door_crack_coefficient, self.door_crack_exponent,
            self.minimum_density_difference, self.discharge_coefficient)
        door_component.setName("INI-C Door Crack")

        linked_zones = {}
        processed = set()
        counts = {"windows": 0, "doors": 0, "skipped": 0}
        for sub_surface in model.getSubSurfaces():
            handle = str(sub_surface.handle())
            if handle in processed:
                continue
            sub_type = sub_surface.subSurfaceType()
            if sub_type in self.window_types:
                component = window_component
                key = "windows"
            elif sub_type in self.door_types:
                component = door_component
                key = "doors"
            else:
                continue
            surface_opt = sub_surface.surface()
            if not surface_opt.is_initialized():
                continue
            surface = surface_opt.get()
            boundary = surface.outsideBoundaryCondition()
            zone = self._zone_of(sub_surface)
            if zone is None:
                counts["skipped"] += 1
                continue
            if boundary == "Outdoors":
                pass
            elif boundary == "Surface":
                adjacent_opt = sub_surface.adjacentSubSurface()
                if not adjacent_opt.is_initialized():
                    counts["skipped"] += 1
                    logging.warning(f"Interior opening '{sub_surface.nameString()}' has no adjacent sub surface. Skipped.")
                    continue
                adjacent = adjacent_opt.get()
                adjacent_zone = self._zone_of(adjacent)
                processed.add(str(adjacent.handle()))
                if adjacent_zone is None or str(adjacent_zone.handle()) == str(zone.handle()):
                    counts["skipped"] += 1
                    continue
                linked_zones[str(adjacent_zone.handle())] = adjacent_zone
            else:
                counts["skipped"] += 1
                continue
            sub_surface.getAirflowNetworkSurface(component)
            linked_zones[str(zone.handle())] = zone
            processed.add(handle)
            counts[key] += 1

        for zone in linked_zones.values():
            afn_zone = zone.getAirflowNetworkZone()
            afn_zone.setVentilationControlMode("NoVent")

        logging.info(f"AirflowNetwork: {counts['windows']} windows and {counts['doors']} doors with crack infiltration, "
                     f"{len(linked_zones)} zones linked, {counts['skipped']} openings skipped")
        print("AirflowNetwork crack infiltration (INI-C Table C.4):")
        print(f" - Windows: {counts['windows']} (C = {self.window_crack_coefficient} kg/(s.m), n = {self.window_crack_exponent})")
        print(f" - Doors: {counts['doors']} (C = {self.door_crack_coefficient} kg/(s.m), n = {self.door_crack_exponent})")
        print(f" - Zones linked: {len(linked_zones)}")
        return counts

    def update_airflow_objects(self, model):
        """Applies outdoor air (APP) and crack infiltration through AirflowNetwork (all zones)."""
        self.remove_infiltration_objects(model)
        spaces_processed = self.update_outdoor_air(model)
        self.apply_airflow_network(model)
        logging.info(f"Outdoor air updated: {spaces_processed['APP']} APPs, {spaces_processed['APT']} APTs, {spaces_processed['UNCLASSIFIED']} unclassified")
        print("Airflow assigner processing summary:")
        print(f" - APP: {spaces_processed['APP']} (outdoor air {self.outdoor_air_per_person} m³/s per person)")
        print(f" - APT: {spaces_processed['APT']} (no outdoor air)")
        print(f" - Unclassified: {spaces_processed['UNCLASSIFIED']} (no outdoor air changes)")

    def process_osm_file(self, osm_path, output_path, afn_only=False):
        """Process OSM file to update airflow objects."""
        temp_osm = tempfile.NamedTemporaryFile(delete=False, suffix='.osm')
        try:
            shutil.copy(osm_path, temp_osm.name)
            # Load OSM model
            translator = openstudio.osversion.VersionTranslator()
            osm_model_handle = translator.loadModel(openstudio.path(temp_osm.name))
            if not osm_model_handle.is_initialized():
                raise ValueError(f"Failed to load OSM file: {osm_path}")
            model = osm_model_handle.get()
            # Update airflow objects
            if afn_only:
                self.apply_airflow_network(model)
            else:
                self.update_airflow_objects(model)
            # Save updated model
            if not model.save(openstudio.path(output_path), True):
                raise RuntimeError("Failed to save updated OSM model")
            logging.info(f"Updated OSM model saved: {output_path}")
            return True
        except Exception as e:
            logging.error(f"Processing failed: {e}")
            print(f"Error: {e}")
            return False
        finally:
            temp_osm.close()
            if os.path.exists(temp_osm.name):
                os.remove(temp_osm.name)

    def run_standalone(self):
        """Stand-alone mode with file selection dialogs."""
        root = Tk()
        root.withdraw()
        print("Airflow Assigner")
        print("Applies airflow settings to all spaces in OSM model:\n"
              "- APP: outdoor air\n"
              "- All zones: closed windows and doors with crack infiltration (AirflowNetwork)\n")
        print(f"- Outdoor Air (APP): {self.outdoor_air_per_person} m³/s per person\n")
        # Select OSM file
        osm_path = filedialog.askopenfilename(
            title="Select OSM file to update",
            filetypes=[("OSM files", "*.osm")]
        )
        if not osm_path:
            root.destroy()
            return False
        # Select output location
        output_path = filedialog.asksaveasfilename(
            title="Save updated OSM file as",
            filetypes=[("OSM files", "*.osm")],
            defaultextension=".osm"
        )
        if not output_path:
            root.destroy()
            return False
        root.destroy()
        return self.process_osm_file(osm_path, output_path)

    def run_automated(self, osm_path, output_path, afn_only=False):
        """Automated mode for script chaining."""
        return self.process_osm_file(osm_path, output_path, afn_only)

def main():
    assigner = AirflowAssigner()
    args = sys.argv[1:]
    if len(args) in (2, 3):
        # Automated mode: osm input, osm output, optional afn_only (reapply crack infiltration after reference changes)
        afn_only = len(args) == 3 and args[2].lower() == "afn_only"
        success = assigner.run_automated(args[0], args[1], afn_only)
        if success:
            print(args[1]) # Output path for script chaining
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        # Stand-alone mode: interactive file selection
        success = assigner.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python script.py [osm_input osm_output [afn_only]] or run without arguments for GUI")
        print()
        print("This script applies outdoor air to APP spaces and crack infiltration (AirflowNetwork, INI-C Table C.4) to all zones.")
        sys.exit(1)

if __name__ == "__main__":
    main()
