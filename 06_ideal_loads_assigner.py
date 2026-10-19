import openstudio
import os
import sys
import shutil
import tempfile
import logging
from tkinter import Tk, filedialog

from spacetype_utils import get_space_type_label

class IdealLoadsAssigner:
    def __init__(self, heating_enabled=False):
        logging.basicConfig(
            filename="set_ideal_loads.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )

        # Fixed setpoint values for APP zones
        self.heating_setpoint = 21.0  # °C
        self.cooling_setpoint = 24.0  # °C
        self.heating_enabled = heating_enabled

    def get_on_off_schedule_type_limits(self, model):
        """Get or create On/Off schedule type limits."""
        for stl in model.getScheduleTypeLimitss():
            if stl.nameString() == "On/Off":
                return stl

        stl = openstudio.model.ScheduleTypeLimits(model)
        stl.setName("On/Off")
        stl.setLowerLimitValue(0.0)
        stl.setUpperLimitValue(1.0)
        stl.setNumericType("Discrete")
        return stl

    def get_temperature_schedule_type_limits(self, model):
        """Get or create Temperature schedule type limits."""
        for stl in model.getScheduleTypeLimitss():
            if stl.nameString() == "Temperature":
                return stl

        stl = openstudio.model.ScheduleTypeLimits(model)
        stl.setName("Temperature")
        stl.setLowerLimitValue(0.0)
        stl.setUpperLimitValue(50.0)
        stl.setNumericType("Continuous")
        stl.setUnitType("Temperature")
        return stl

    def create_operating_schedule(self, model):
        """Create operating schedule: 09:00-17:00 weekdays (On), weekends (Off)."""
        schedule_name = "INI-C HVAC Operating Schedule"

        # Check if schedule already exists
        for sched in model.getScheduleRulesets():
            if sched.nameString() == schedule_name:
                return sched

        # Create new schedule
        schedule = openstudio.model.ScheduleRuleset(model)
        schedule.setName(schedule_name)
        schedule.setScheduleTypeLimits(self.get_on_off_schedule_type_limits(model))

        # Default day: ON from 09:00 to 17:00
        default_day = schedule.defaultDaySchedule()
        default_day.setName("Weekday Operating")
        default_day.addValue(openstudio.Time(0, 9, 0, 0), 0.0)   # 00:00-09:00 OFF
        default_day.addValue(openstudio.Time(0, 17, 0, 0), 1.0)  # 09:00-17:00 ON
        default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)  # 17:00-24:00 OFF

        # Weekend rule: always OFF
        weekend_rule = openstudio.model.ScheduleRule(schedule)
        weekend_rule.setApplySaturday(True)
        weekend_rule.setApplySunday(True)
        weekend_day = weekend_rule.daySchedule()
        weekend_day.setName("Weekend Off")
        weekend_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)  # Always OFF

        logging.info("Created INI-C HVAC operating schedule (09:00-17:00 weekdays)")
        return schedule

    def create_constant_temperature_schedule(self, model, temperature, name):
        """Create a constant temperature schedule."""
        schedule = openstudio.model.ScheduleConstant(model)
        schedule.setName(name)
        schedule.setValue(temperature)
        schedule.setScheduleTypeLimits(self.get_temperature_schedule_type_limits(model))

        logging.info(f"Created constant temperature schedule '{name}' with value {temperature}°C")
        return schedule

    def setup_ideal_loads_and_thermostats(self, model):
        """Add Ideal Loads Air Systems and thermostats to APP zones only."""
        operating_schedule = self.create_operating_schedule(model)
        heating_schedule = self.create_constant_temperature_schedule(
            model, self.heating_setpoint, f"Heating Setpoint {self.heating_setpoint}C"
        )
        cooling_schedule = self.create_constant_temperature_schedule(
            model, self.cooling_setpoint, f"Cooling Setpoint {self.cooling_setpoint}C"
        )

        zones_processed = 0
        zones_skipped = 0

        for zone in model.getThermalZones():
            # Check if any associated space is labeled as APP
            is_app_zone = False
            for space in zone.spaces():
                label = get_space_type_label(space)
                if label == "APP":
                    is_app_zone = True
                    break

            if not is_app_zone:
                logging.info(f"Skipped zone '{zone.nameString()}' (not APP)")
                zones_skipped += 1
                continue  # Do not configure non-APP zones

            zone_name = zone.nameString()

            # Remove existing Ideal Loads Air System equipment
            for equip in zone.equipment():
                if isinstance(equip, openstudio.model.ZoneHVACIdealLoadsAirSystem):
                    equip.remove()

            # Add new Ideal Loads Air System
            ideal_loads = openstudio.model.ZoneHVACIdealLoadsAirSystem(model)
            ideal_loads.addToThermalZone(zone)
            ideal_loads.setAvailabilitySchedule(operating_schedule)
            if not self.heating_enabled:
                ideal_loads.setHeatingAvailabilitySchedule(model.alwaysOffDiscreteSchedule())
            for space in zone.spaces():
                if space.designSpecificationOutdoorAir().is_initialized():
                    ideal_loads.setDesignSpecificationOutdoorAirObject(space.designSpecificationOutdoorAir().get())
                    ideal_loads.setDemandControlledVentilationType("OccupancySchedule")
                    break

            # Remove existing thermostat
            if zone.thermostatSetpointDualSetpoint().is_initialized():
                zone.thermostatSetpointDualSetpoint().get().remove()

            # Add new thermostat
            thermostat = openstudio.model.ThermostatSetpointDualSetpoint(model)
            thermostat.setHeatingSetpointTemperatureSchedule(heating_schedule)
            thermostat.setCoolingSetpointTemperatureSchedule(cooling_schedule)
            zone.setThermostatSetpointDualSetpoint(thermostat)

            zones_processed += 1
            logging.info(f"Configured APP zone '{zone_name}' with Ideal Loads Air System and thermostat")

        logging.info(f"Configured Ideal Loads and thermostats for {zones_processed} APP zones, {zones_skipped} zones skipped")
        print(f"Applied Ideal Loads Air Systems to {zones_processed} APP thermal zones.")
        print(f"Skipped {zones_skipped} zones (non-APP).")
        print(f"  - Heating setpoint: {self.heating_setpoint}°C ({'enabled' if self.heating_enabled else 'disabled, no heating system in project'})")
        print(f"  - Cooling setpoint: {self.cooling_setpoint}°C")
        print("  - Operating schedule: 09:00-17:00 weekdays, OFF weekends")

    def process_osm_file(self, osm_path, output_path):
        """Process OSM file to update (APP) zones with Ideal Loads and thermostats."""
        temp_osm = tempfile.NamedTemporaryFile(delete=False, suffix='.osm')

        try:
            shutil.copy(osm_path, temp_osm.name)

            # Load OSM model
            translator = openstudio.osversion.VersionTranslator()
            osm_model_handle = translator.loadModel(openstudio.path(temp_osm.name))

            if not osm_model_handle.is_initialized():
                raise ValueError(f"Failed to load OSM file: {osm_path}")

            model = osm_model_handle.get()

            # Setup Ideal Loads and thermostats (APP only)
            self.setup_ideal_loads_and_thermostats(model)

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
        """Interactive mode with file dialogs."""
        root = Tk()
        root.withdraw()

        print("Ideal Loads Air System Assigner")
        print("Only APP-type spaces/zones receive Ideal Loads Air System and thermostats.\n"
              "APT zones remain unchanged.")
        print(f" - Heating setpoint: {self.heating_setpoint}°C")
        print(f" - Cooling setpoint: {self.cooling_setpoint}°C")
        print(" - System active: 09:00-17:00 weekdays, OFF weekends\n")

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

    def run_automated(self, osm_path, output_path):
        """Automated (batch/script) mode."""
        return self.process_osm_file(osm_path, output_path)

def main():
    args = sys.argv[1:]
    heating_enabled = len(args) == 3 and args[2].lower() in ("heating", "1", "true", "yes")
    assigner = IdealLoadsAssigner(heating_enabled=heating_enabled)

    if len(args) in (2, 3):
        # Automated mode: osm input, osm output
        success = assigner.run_automated(args[0], args[1])
        if success:
            print(args[1])  # Output path for script chaining
        sys.exit(0 if success else 1)

    elif len(args) == 0:
        # Stand-alone mode: interactive file selection
        success = assigner.run_standalone()
        sys.exit(0 if success else 1)

    else:
        print("Usage: python script.py [osm_input osm_output [heating]] or run without arguments for GUI")
        print()
        print("Only APP-type spaces/zones receive Ideal Loads Air System and thermostats.")
        print("Heating is only enabled when the project has a heating system (third argument 'heating').")
        print("- APP: Ideal Loads, thermostat, and setpoints applied")
        print("- APT: unchanged")
        sys.exit(1)

if __name__ == "__main__":
    main()
