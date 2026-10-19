import openstudio
import os
import tempfile
import shutil
import xml.etree.ElementTree as ET
import logging
import sys
from tkinter import Tk, filedialog

from spacetype_utils import get_space_type_label

class OSMEnricher:
    def __init__(self, area_per_person=1.5, lighting_mode="gbxml", dpi_value=None):
        logging.basicConfig(
            filename="assign_loads.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        # Fixed values
        self.AREA_PER_PERSON = area_per_person  # m²/person
        self.EQUIPMENT_POWER = 15.0  # W/m²
        self.REFERENCE_DPI = 15.5  # W/m²
        self.lighting_mode = lighting_mode
        self.dpi_value = dpi_value

    def create_temp_copy(self, file_path):
        """Create temporary copy of file."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_path)[1])
        shutil.copy(file_path, temp_file.name)
        return temp_file.name

    def extract_gbxml_data(self, gbxml_path):
        """Extract only lighting data from gbXML file."""
        tree = ET.parse(gbxml_path)
        root = tree.getroot()
        namespace = {'gbXML': 'http://www.gbxml.org/schema'}

        spaces_data = {}
        for space in root.findall('.//gbXML:Space', namespace):
            space_id = space.get('id', 'Unknown')
            spaces_data[space_id] = {
                'lights': float(space.findtext('gbXML:LightPowerPerArea', default='0', namespaces=namespace))
            }

        logging.info("Lighting data extracted from gbXML")
        return spaces_data

    def gbxml_has_lighting(self, spaces_data):
        """Returns True if at least one space has LightPowerPerArea greater than zero."""
        return any(d['lights'] > 0 for d in spaces_data.values())

    def resolve_lighting(self, spaces_data):
        """Defines the lighting power density of each space according to the lighting mode."""
        mode = self.lighting_mode
        if mode == "gbxml" and not self.gbxml_has_lighting(spaces_data):
            logging.warning("gbXML has no LightPowerPerArea. Using reference DPI only in APP spaces (lighting system not evaluated).")
            print("WARNING: gbXML has no lighting power density. Reference DPI applied only to APP spaces.")
            mode = "reference"
        for data in spaces_data.values():
            if mode == "project":
                data['lights'] = float(self.dpi_value)
                data['lights_app_only'] = False
            elif mode == "reference":
                data['lights'] = self.REFERENCE_DPI
                data['lights_app_only'] = True
            else:
                data['lights_app_only'] = False
        self.lighting_mode = mode
        return spaces_data

    def add_loads_to_model(self, model, spaces_data):
        """Add internal loads to OSM model with fixed occupancy and equipment values,
        differentiating based on APP/APT classification."""
        people_defs, lights_defs, equip_defs = {}, {}, {}

        for space_id, data in spaces_data.items():
            # Find space in model
            space = next((s for s in model.getSpaces()
                          if s.name().is_initialized() and s.name().get() == space_id), None)
            if not space:
                logging.warning(f"Space '{space_id}' not found in OSM")
                continue

            # Get space floor area
            floor_area = space.floorArea()  # m²

            # Determine if space is a Plenum (special handling for loads even if zero)
            is_plenum = (space.spaceType().is_initialized() and
                         space.spaceType().get().name().is_initialized() and
                         space.spaceType().get().name().get() == "Plenum")

            # Use spacetype_utils to determine APP/APT
            space_type_label = get_space_type_label(space)
            space_type_name = (space.spaceType().get().name().get()
                               if space.spaceType().is_initialized() and
                                  space.spaceType().get().name().is_initialized()
                               else "N/A")

            # Default to APP if not found or not initialized
            if space_type_label is None:
                space_type_label = "APP"
                logging.warning(f"Space '{space_id}' with SpaceType '{space_type_name}' not found in dictionary or not initialized. Defaulting to APP behavior.")

            # Calculate number of people based on area (used for APP)
            num_people = floor_area / self.AREA_PER_PERSON if floor_area > 0 else 0

            # Add loads based on APP/APT classification
            if space_type_label == "APP":
                self._add_people_load(model, space, num_people, people_defs, is_plenum)
                self._add_equipment_load(model, space, self.EQUIPMENT_POWER, equip_defs, is_plenum)
                logging.info(
                    f"Space '{space_id}' (APP): {floor_area:.1f}m², {num_people:.1f} people, "
                    f"{data['lights']:.1f}W/m² lights, {self.EQUIPMENT_POWER}W/m² equipment"
                )
            elif space_type_label == "APT":
                logging.info(
                    f"Space '{space_id}' (APT): {floor_area:.1f}m², only {data['lights']:.1f}W/m² lights added (people and equipment loads skipped per INI-C)."
                )

            # Lights are always added if light_power > 0 (or if it's a plenum)
            if data.get('lights_app_only') and space_type_label != "APP":
                continue
            self._add_lights_load(model, space, data['lights'], lights_defs, is_plenum)

    def _add_people_load(self, model, space, num_people, people_defs, is_plenum):
        """Add people load to space."""
        if num_people > 0 or is_plenum:
            people_key = round(num_people, 2)

            if people_key not in people_defs:
                people_def = openstudio.model.PeopleDefinition(model)
                people_def.setNumberofPeople(people_key)
                people_defs[people_key] = people_def

            people = openstudio.model.People(people_defs[people_key])
            people.setSpace(space)
            people.setName(f"People_{space.name().get()}")

    def _add_lights_load(self, model, space, light_power, lights_defs, is_plenum):
        """Add lighting load to space."""
        if light_power > 0 or is_plenum:
            if light_power not in lights_defs:
                lights_def = openstudio.model.LightsDefinition(model)
                lights_def.setWattsperSpaceFloorArea(light_power)
                lights_defs[light_power] = lights_def

            lights = openstudio.model.Lights(lights_defs[light_power])
            lights.setSpace(space)
            lights.setName(f"Lights_{space.name().get()}")

    def _add_equipment_load(self, model, space, equip_power, equip_defs, is_plenum):
        """Add equipment load to space."""
        if equip_power > 0 or is_plenum:
            if equip_power not in equip_defs:
                equip_def = openstudio.model.ElectricEquipmentDefinition(model)
                equip_def.setWattsperSpaceFloorArea(equip_power)
                equip_defs[equip_power] = equip_def

            equipment = openstudio.model.ElectricEquipment(equip_defs[equip_power])
            equipment.setSpace(space)
            equipment.setName(f"ElectricEquipment_{space.name().get()}")

    def enrich_model(self, gbxml_path, osm_path, output_path):
        """Enrich OSM model with gbXML lighting data and fixed occupancy/equipment values."""
        temp_gbxml = temp_osm = None
        try:
            temp_gbxml = self.create_temp_copy(gbxml_path)
            temp_osm = self.create_temp_copy(osm_path)

            spaces_data = self.extract_gbxml_data(temp_gbxml)
            spaces_data = self.resolve_lighting(spaces_data)

            osm_model_handle = openstudio.model.Model.load(openstudio.toPath(temp_osm))
            if not osm_model_handle.is_initialized():
                raise FileNotFoundError(f"Failed to load OSM file: {osm_path}")

            model = osm_model_handle.get()
            self.add_loads_to_model(model, spaces_data)

            if not model.save(openstudio.toPath(output_path), True):
                raise IOError("Failed to save enriched OSM model")

            logging.info(f"Model enriched with fixed loads: {output_path}")
            logging.info(f"Applied: {self.AREA_PER_PERSON}m²/person, {self.EQUIPMENT_POWER}W/m² equipment (conditionally for APP/APT)")
            logging.info(f"Lighting mode: {self.lighting_mode}")
            return True

        except Exception as e:
            logging.error(f"Enrichment failed: {e}")
            return False
        finally:
            for temp_file in [temp_gbxml, temp_osm]:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)

    def run_standalone(self):
        """Stand-alone mode with file selection dialogs."""
        root = Tk()
        root.withdraw()

        gbxml_path = filedialog.askopenfilename(
            title="Select gbXML file",
            filetypes=[("gbXML files", "*.xml *.gbxml")]
        )
        if not gbxml_path:
            root.destroy()
            return False

        osm_path = filedialog.askopenfilename(
            title="Select OSM file",
            filetypes=[("OSM files", "*.osm")]
        )
        if not osm_path:
            root.destroy()
            return False

        output_path = filedialog.asksaveasfilename(
            title="Save enriched OSM file as",
            filetypes=[("OSM files", "*.osm")],
            defaultextension=".osm"
        )
        if not output_path:
            root.destroy()
            return False

        root.destroy()
        return self.enrich_model(gbxml_path, osm_path, output_path)

    def run_automated(self, gbxml_path, osm_path, output_path):
        """Automated mode for script chaining."""
        return self.enrich_model(gbxml_path, osm_path, output_path)

def main():
    args = sys.argv[1:]
    lighting_mode = args[3] if len(args) >= 4 else "gbxml"
    dpi_value = float(args[4]) if len(args) >= 5 else None
    enricher = OSMEnricher(lighting_mode=lighting_mode, dpi_value=dpi_value)

    if len(args) in (3, 4, 5):
        success = enricher.run_automated(args[0], args[1], args[2])
        if success:
            print(args[2])  # Output path for script chaining
        sys.exit(0 if success else 1)

    elif len(args) == 0:
        success = enricher.run_standalone()
        sys.exit(0 if success else 1)

    else:
        print("Usage: python script.py [gbxml.xml input.osm output.osm [gbxml|project|reference] [dpi]] or run without arguments for GUI")
        sys.exit(1)

if __name__ == "__main__":
    main()
