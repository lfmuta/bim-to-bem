import openstudio
import os
import sys
import shutil
import tempfile
import logging
from tkinter import Tk, filedialog

class ScheduleEnricher:
    def __init__(self):
        logging.basicConfig(
            filename="assign_schedules.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        self.metabolic_rate = 180.0
    
    def create_ini_c_schedule(self, model, schedule_name="INI-C Standard Schedule"):
        """Create INI-C compliant schedule: 100% from 9:00-17:00 weekdays, 0% weekends."""
        # Create schedule ruleset
        schedule_ruleset = openstudio.model.ScheduleRuleset(model)
        schedule_ruleset.setName(schedule_name)
        
        # Default day schedule (weekdays)
        default_day = schedule_ruleset.defaultDaySchedule()
        default_day.setName(f"{schedule_name} - Weekday")
        
        # Hours 0-8: 0% (00:00-08:59)
        default_day.addValue(openstudio.Time(0, 9, 0, 0), 0.0)
        # Hours 9-16: 100% (09:00-16:59) 
        default_day.addValue(openstudio.Time(0, 17, 0, 0), 1.0)
        # Hours 17-23: 0% (17:00-23:59)
        default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)
        
        # Weekend rule (Saturday and Sunday = 0%)
        weekend_rule = openstudio.model.ScheduleRule(schedule_ruleset)
        weekend_rule.setName(f"{schedule_name} - Weekend")
        
        # Explicitly set which days this rule applies to
        weekend_rule.setApplyMonday(False)
        weekend_rule.setApplyTuesday(False)
        weekend_rule.setApplyWednesday(False)
        weekend_rule.setApplyThursday(False)
        weekend_rule.setApplyFriday(False)
        weekend_rule.setApplySaturday(True)
        weekend_rule.setApplySunday(True)
        
        weekend_day = weekend_rule.daySchedule()
        weekend_day.setName(f"{schedule_name} - Weekend Day")
        weekend_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)
        
        # Design day schedules
        summer_design = openstudio.model.ScheduleDay(model)
        summer_design.setName(f"{schedule_name} - Summer Design Day")
        summer_design.addValue(openstudio.Time(0, 9, 0, 0), 0.0)
        summer_design.addValue(openstudio.Time(0, 17, 0, 0), 1.0)
        summer_design.addValue(openstudio.Time(0, 24, 0, 0), 0.0)
        schedule_ruleset.setSummerDesignDaySchedule(summer_design)
        
        winter_design = openstudio.model.ScheduleDay(model)
        winter_design.setName(f"{schedule_name} - Winter Design Day")
        winter_design.addValue(openstudio.Time(0, 9, 0, 0), 0.0)
        winter_design.addValue(openstudio.Time(0, 17, 0, 0), 1.0)
        winter_design.addValue(openstudio.Time(0, 24, 0, 0), 0.0)
        schedule_ruleset.setWinterDesignDaySchedule(winter_design)
        
        logging.info(f"Created INI-C compliant schedule: {schedule_name}")
        return schedule_ruleset
    
    def create_activity_schedule(self, model, schedule_name="INI-C Activity Schedule"):
        """Create activity schedule with fixed metabolic rate per INI-C Table C.3 (educational: 180 W/person)."""
        activity_schedule = openstudio.model.ScheduleRuleset(model)
        activity_schedule.setName(schedule_name)
        
        default_day = activity_schedule.defaultDaySchedule()
        default_day.setName(f"{schedule_name} - Default")
        default_day.addValue(openstudio.Time(0, 24, 0, 0), self.metabolic_rate)
        
        # Design day schedules
        summer_design = openstudio.model.ScheduleDay(model)
        summer_design.setName(f"{schedule_name} - Summer Design Day")
        summer_design.addValue(openstudio.Time(0, 24, 0, 0), self.metabolic_rate)
        activity_schedule.setSummerDesignDaySchedule(summer_design)
        
        winter_design = openstudio.model.ScheduleDay(model)
        winter_design.setName(f"{schedule_name} - Winter Design Day")
        winter_design.addValue(openstudio.Time(0, 24, 0, 0), self.metabolic_rate)
        activity_schedule.setWinterDesignDaySchedule(winter_design)
        
        logging.info(f"Created INI-C activity schedule: {schedule_name}")
        return activity_schedule
    
    def assign_ini_c_schedules(self, model):
        """Assign INI-C compliant schedules to all loads in the model."""
        try:
            # Create standard schedules
            standard_schedule = self.create_ini_c_schedule(model, "INI-C Standard Schedule")
            activity_schedule = self.create_activity_schedule(model, "INI-C Activity Schedule")
            
            all_spaces = model.getSpaces()
            if len(all_spaces) == 0:
                logging.warning("No spaces found in model")
                return
            
            spaces_processed = 0
            lights_assigned = 0
            equipment_assigned = 0
            people_assigned = 0
            
            for space in all_spaces:
                space_name = space.nameString()
                space_processed = False
                
                # Assign lighting schedule
                lights = space.lights()
                if len(lights) > 0:
                    for light in lights:
                        light.setSchedule(standard_schedule)
                        lights_assigned += 1
                    logging.info(f"Assigned lighting schedule to {len(lights)} lights in space: {space_name}")
                    space_processed = True
                
                # Assign equipment schedule
                equipment = space.electricEquipment()
                if len(equipment) > 0:
                    for equip in equipment:
                        equip.setSchedule(standard_schedule)
                        equipment_assigned += 1
                    logging.info(f"Assigned equipment schedule to {len(equipment)} equipment in space: {space_name}")
                    space_processed = True
                
                # Assign people schedule and activity schedule
                people = space.people()
                if len(people) > 0:
                    for person in people:
                        person.setNumberofPeopleSchedule(standard_schedule)
                        person.setActivityLevelSchedule(activity_schedule)
                        people_assigned += 1
                    logging.info(f"Assigned people and activity schedules to {len(people)} people loads in space: {space_name}")
                    space_processed = True
                
                if space_processed:
                    spaces_processed += 1
            
            # Log summary
            logging.info("INI-C Schedule Assignment Summary:")
            logging.info(f"  Spaces processed: {spaces_processed}")
            logging.info(f"  Lights assigned: {lights_assigned}")
            logging.info(f"  Equipment assigned: {equipment_assigned}")
            logging.info(f"  People assigned: {people_assigned}")
            
            print("Successfully applied INI-C schedules:")
            print(f"  - {spaces_processed} spaces processed")
            print(f"  - {lights_assigned} lighting loads")
            print(f"  - {equipment_assigned} equipment loads")
            print(f"  - {people_assigned} people loads")
            print("Schedule pattern: 100% from 09:00-17:00 weekdays, 0% weekends")
            print(f"Activity level: {self.metabolic_rate:.0f} W/person (constant)")
            
        except Exception as e:
            logging.error(f"Error assigning INI-C schedules: {e}")
            raise
    
    def process_osm_file(self, osm_path, output_path):
        """Process OSM file to apply INI-C compliant schedules."""
        temp_osm = tempfile.NamedTemporaryFile(delete=False, suffix='.osm')
        
        try:
            shutil.copy(osm_path, temp_osm.name)
            
            # Load OSM model
            translator = openstudio.osversion.VersionTranslator()
            osm_model_handle = translator.loadModel(openstudio.path(temp_osm.name))
            
            if not osm_model_handle.is_initialized():
                raise ValueError(f"Failed to load OSM file: {osm_path}")
            
            model = osm_model_handle.get()
            
            # Apply INI-C schedules
            self.assign_ini_c_schedules(model)
            
            # Save enriched model
            if not model.save(openstudio.path(output_path), True):
                raise RuntimeError("Failed to save enriched OSM model")
            
            logging.info(f"INI-C enriched model saved: {output_path}")
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
        
        print("INI-C Schedule Enricher")
        print("Applies standardized schedules as per INI-C requirements:")
        print("- Occupancy/Equipment/Lighting: 100% from 09:00-17:00 weekdays, 0% weekends")
        print(f"- Activity level: {self.metabolic_rate:.0f} W/person (constant)")
        print()
        
        # Select OSM file
        osm_path = filedialog.askopenfilename(
            title="Select OSM file to enrich with INI-C schedules",
            filetypes=[("OSM files", "*.osm")]
        )
        if not osm_path:
            root.destroy()
            return False
        
        # Select output location (without default filename)
        output_path = filedialog.asksaveasfilename(
            title="Save INI-C enriched OSM file as",
            filetypes=[("OSM files", "*.osm")],
            defaultextension=".osm"
        )
        if not output_path:
            root.destroy()
            return False
        
        root.destroy()
        return self.process_osm_file(osm_path, output_path)
    
    def run_automated(self, osm_path, output_path):
        """Automated mode for script chaining."""
        return self.process_osm_file(osm_path, output_path)

def main():
    enricher = ScheduleEnricher()
    args = sys.argv[1:]
    
    if len(args) == 2:
        # Automated mode: osm input, osm output
        success = enricher.run_automated(args[0], args[1])
        if success:
            print(args[1])  # Output path for script chaining
        sys.exit(0 if success else 1)
    
    elif len(args) == 0:
        # Stand-alone mode: interactive file selection
        success = enricher.run_standalone()
        sys.exit(0 if success else 1)
    
    else:
        print("Usage: python script.py [osm_input osm_output] or run without arguments for GUI")
        print()
        print("This script applies INI-C compliant schedules:")
        print("- Occupancy/Equipment/Lighting: 100% from 09:00-17:00 weekdays, 0% weekends")
        print("- Activity level: 180 W/person (constant)")
        sys.exit(1)

if __name__ == "__main__":
    main()
