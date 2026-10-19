import openstudio
import os
import sys
import shutil
import tempfile
import logging
from tkinter import Tk, filedialog

class PlenumFloorAreaDisabler:
    def __init__(self):
        logging.basicConfig(
            filename="disable_plenum_floor_area.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
    
    def disable_plenum_floor_area(self, model):
        """Disable 'Part of Total Floor Area' for spaces with 'Plenum' space type."""
        modified_count = 0
        
        for space in model.getSpaces():
            space_name = space.nameString() if space.name().is_initialized() else "Unnamed Space"
            
            if not space.spaceType().is_initialized():
                continue
                
            space_type = space.spaceType().get()
            if not space_type.name().is_initialized():
                continue
                
            space_type_name = space_type.name().get()
            
            # Check if space type contains 'Plenum'
            if "Plenum" in space_type_name:
                if space.partofTotalFloorArea():
                    space.setPartofTotalFloorArea(False)
                    logging.info(f"Disabled floor area for Plenum: {space_name}")
                    modified_count += 1
        
        logging.info(f"Modified {modified_count} Plenum spaces")
        return modified_count
    
    def process_osm_file(self, osm_path, output_path):
        """Process OSM file to disable plenum floor area contribution."""
        temp_osm = tempfile.NamedTemporaryFile(delete=False, suffix='.osm')
        
        try:
            shutil.copy(osm_path, temp_osm.name)
            
            # Load OSM model
            translator = openstudio.osversion.VersionTranslator()
            osm_model_handle = translator.loadModel(openstudio.path(temp_osm.name))
            
            if not osm_model_handle.is_initialized():
                raise ValueError(f"Failed to load OSM file: {osm_path}")
            
            model = osm_model_handle.get()
            
            # Disable plenum floor area
            modified_count = self.disable_plenum_floor_area(model)
            
            # Save updated model
            if not model.save(openstudio.path(output_path), True):
                raise RuntimeError("Failed to save updated OSM model")
            
            logging.info(f"Updated OSM model saved: {output_path}")
            
            if modified_count > 0:
                print(f"Disabled floor area contribution for {modified_count} Plenum spaces")
            else:
                print("No Plenum spaces found to modify")
            
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
        
        print("Plenum Floor Area Disabler")
        print("Excludes Plenum spaces from total floor area calculation")
        print()
        
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
        """Automated mode for script chaining."""
        return self.process_osm_file(osm_path, output_path)

def main():
    disabler = PlenumFloorAreaDisabler()
    args = sys.argv[1:]
    
    if len(args) == 2:
        # Automated mode: osm input, osm output
        success = disabler.run_automated(args[0], args[1])
        if success:
            print(args[1])  # Output path for script chaining
        sys.exit(0 if success else 1)
    
    elif len(args) == 0:
        # Stand-alone mode: interactive file selection
        success = disabler.run_standalone()
        sys.exit(0 if success else 1)
    
    else:
        print("Usage: python script.py [osm_input osm_output] or run without arguments for GUI")
        print()
        print("This script disables 'Part of Total Floor Area' for spaces with 'Plenum' space type.")
        print("This ensures Plenum spaces are excluded from floor area calculations.")
        sys.exit(1)

if __name__ == "__main__":
    main()
