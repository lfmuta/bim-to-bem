import openstudio
import os
import sys
import shutil
import tempfile
import logging
from tkinter import Tk, filedialog

from spacetype_utils import get_space_type_label

class AirflowAssigner:
    def __init__(self, outdoor_air_per_person=0.005, outdoor_air_per_area=0.0006):
        logging.basicConfig(
            filename="assign_airflow.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        # Outdoor air for APP spaces (NBR 16401-3 Table 1, classroom, level 1)
        self.outdoor_air_per_person = outdoor_air_per_person  # m³/s per person
        self.outdoor_air_per_area = outdoor_air_per_area  # m³/s per m²
        # Crack infiltration for closed openings (INI-C Table C.3)
        self.window_crack_coefficient = 0.00063  # kg/(s.m)
        self.window_crack_exponent = 0.63
        self.door_crack_coefficient = 0.0024  # kg/(s.m)
        self.door_crack_exponent = 0.59
        self.air_density = 1.2  # kg/m³, converts the mass flow coefficients to volume flow
        # AIM-2 enhanced model (EnergyPlus ZoneInfiltration:FlowCoefficient, ASHRAE Fundamentals): no flue,
        # one, two and three or more stories; shelter class 3 (other buildings across the street)
        self.stack_coefficients = (0.054, 0.078, 0.098)  # (Pa/K)^n
        self.wind_coefficients = (0.156, 0.170, 0.170)  # (Pa.s²/m²)^n
        self.shelter_factor = 0.70
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

    def _remove_airflow_network_objects(self, model):
        """Removes AirflowNetwork objects left by earlier versions of this script."""
        for obj in model.getAirflowNetworkSurfaces():
            obj.remove()
        for obj in model.getAirflowNetworkSimpleOpenings():
            obj.remove()
        for obj in model.getAirflowNetworkZones():
            obj.remove()
        control = model.getOptionalAirflowNetworkSimulationControl()
        if control.is_initialized():
            control.get().remove()

    def apply_crack_infiltration(self, model):
        """Models all windows and doors closed with crack infiltration (INI-C C.I.6 and Table C.3).
        The Table C.3 coefficients of the exterior windows and doors of each space are summed into one flow
        coefficient, driven by wind and indoor-outdoor temperature difference (ZoneInfiltration:FlowCoefficient).
        Replaces the AirflowNetwork, which took about 80 % of the simulation time with close results."""
        self._remove_airflow_network_objects(model)
        for obj in model.getSpaceInfiltrationFlowCoefficients():
            obj.remove()

        stories = len(model.getBuildingStorys())
        index = min(max(stories, 1), 3) - 1
        stack_coefficient = self.stack_coefficients[index]
        wind_coefficient = self.wind_coefficients[index]

        spaces = {}
        counts = {"windows": 0, "doors": 0}
        for sub_surface in model.getSubSurfaces():
            sub_type = sub_surface.subSurfaceType()
            if sub_type in self.window_types:
                coefficient, exponent, key = self.window_crack_coefficient, self.window_crack_exponent, "windows"
            elif sub_type in self.door_types:
                coefficient, exponent, key = self.door_crack_coefficient, self.door_crack_exponent, "doors"
            else:
                continue
            surface_opt = sub_surface.surface()
            space_opt = sub_surface.space()
            if not surface_opt.is_initialized() or not space_opt.is_initialized():
                continue
            if surface_opt.get().outsideBoundaryCondition() != "Outdoors":
                continue
            # Crack length taken as the opening perimeter
            vertices = list(sub_surface.vertices())
            perimeter = sum((vertices[i] - vertices[i - 1]).length() for i in range(len(vertices)))
            mass_flow = coefficient * perimeter
            handle = str(space_opt.get().handle())
            space, total, weighted = spaces.get(handle, (space_opt.get(), 0.0, 0.0))
            spaces[handle] = (space, total + mass_flow, weighted + mass_flow * exponent)
            counts[key] += 1

        always_on = model.alwaysOnDiscreteSchedule()
        for space, total, weighted in sorted(spaces.values(), key=lambda item: item[0].nameString()):
            infiltration = openstudio.model.SpaceInfiltrationFlowCoefficient(model)
            infiltration.setName(f"{space.nameString()} Crack Infiltration")
            infiltration.setSpace(space)
            infiltration.setSchedule(always_on)
            infiltration.setFlowCoefficient(total / self.air_density)
            infiltration.setPressureExponent(weighted / total)
            infiltration.setStackCoefficient(stack_coefficient)
            infiltration.setWindCoefficient(wind_coefficient)
            infiltration.setShelterFactor(self.shelter_factor)

        logging.info(f"Crack infiltration: {counts['windows']} exterior windows and {counts['doors']} exterior doors, "
                     f"{len(spaces)} spaces, stack coefficient {stack_coefficient}, wind coefficient {wind_coefficient}, "
                     f"shelter factor {self.shelter_factor}")
        print("Crack infiltration with flow coefficients (INI-C Table C.3):")
        print(f" - Exterior windows: {counts['windows']} (C = {self.window_crack_coefficient} kg/(s.m), n = {self.window_crack_exponent})")
        print(f" - Exterior doors: {counts['doors']} (C = {self.door_crack_coefficient} kg/(s.m), n = {self.door_crack_exponent})")
        print(f" - Spaces with crack infiltration: {len(spaces)}")
        return counts

    def update_airflow_objects(self, model):
        """Applies outdoor air (APP) and crack infiltration (all spaces with exterior windows or doors)."""
        self.remove_infiltration_objects(model)
        spaces_processed = self.update_outdoor_air(model)
        self.apply_crack_infiltration(model)
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
                self.apply_crack_infiltration(model)
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
              "- All spaces: closed exterior windows and doors with crack infiltration (flow coefficients)\n")
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
        print("This script applies outdoor air to APP spaces and crack infiltration (flow coefficients, INI-C Table C.3) to all spaces.")
        sys.exit(1)

if __name__ == "__main__":
    main()
