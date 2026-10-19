import openstudio
import logging
import sys
from tkinter import Tk, filedialog

class OSMCleaner:
    def __init__(self):
        logging.basicConfig(
            filename="clean_schedules.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
    
    def clean_schedules(self, model):
        """Remove schedules and related objects from model."""
        try:
            # Remove all year schedules
            for year_schedule in model.getScheduleYears():
                logging.info(f"Removing Year Schedule: {year_schedule.nameString()}")
                year_schedule.remove()
            
            logging.info("All schedules cleaned from model")
            
        except Exception as e:
            logging.error(f"Error cleaning schedules: {e}")
            raise
    
    def process_model(self, input_path, output_path):
        """Load OSM, clean schedules, and save cleaned model."""
        try:
            # Load model
            translator = openstudio.osversion.VersionTranslator()
            osm_model_handle = translator.loadModel(openstudio.path(input_path))
            
            if not osm_model_handle.is_initialized():
                raise ValueError(f"Failed to load OSM file: {input_path}")
            
            model = osm_model_handle.get()
            
            # Clean schedules
            self.clean_schedules(model)
            
            # Save cleaned model
            if not model.save(openstudio.path(output_path), True):
                raise RuntimeError("Failed to save cleaned OSM model")
            
            logging.info(f"Cleaned model saved: {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Processing failed: {e}")
            return False
    
    def run_standalone(self):
        """Stand-alone mode with file selection dialogs."""
        root = Tk()
        root.withdraw()
        
        # Select input OSM file
        input_path = filedialog.askopenfilename(
            title="Select OSM file to clean",
            filetypes=[("OSM files", "*.osm")]
        )
        if not input_path:
            root.destroy()
            return False
        
        # Select output location
        output_path = filedialog.asksaveasfilename(
            title="Save cleaned OSM file as",
            filetypes=[("OSM files", "*.osm")],
            defaultextension=".osm"
        )
        if not output_path:
            root.destroy()
            return False
        
        root.destroy()
        return self.process_model(input_path, output_path)
    
    def run_automated(self, input_path, output_path):
        """Automated mode for script chaining."""
        return self.process_model(input_path, output_path)

def main():
    cleaner = OSMCleaner()
    args = sys.argv[1:]
    
    if len(args) == 2:
        # Automated mode: input, output
        success = cleaner.run_automated(args[0], args[1])
        if success:
            print(args[1])  # Output path for script chaining
        sys.exit(0 if success else 1)
    
    elif len(args) == 0:
        # Stand-alone mode: interactive file selection
        success = cleaner.run_standalone()
        sys.exit(0 if success else 1)
    
    else:
        print("Usage: python script.py [input.osm output.osm] or run without arguments for GUI")
        sys.exit(1)

if __name__ == "__main__":
    main()
