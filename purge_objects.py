import openstudio
import os
import sys
import logging
import traceback
from datetime import datetime
from tkinter import Tk, filedialog

class ModelResourcePurger:
    def __init__(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"resource_purger_{timestamp}.log"
        logging.basicConfig(
            filename=log_filename,
            filemode="w",
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            level=logging.INFO
        )
        self.logger = logging.getLogger("ModelResourcePurger")
        self.logger.info("Initializing ModelResourcePurger. Log file %s", log_filename)

    def select_input_file(self, parent_root):
        input_path = filedialog.askopenfilename(
            parent=parent_root,
            title="Select input file (.osm)",
            filetypes=[("OpenStudio Model", "*.osm"), ("All files", "*.*")]
        )
        if not input_path:
            self.logger.warning("Input file selection cancelled.")
        return input_path

    def select_output_file(self, parent_root):
        output_path = filedialog.asksaveasfilename(
            parent=parent_root,
            title="Select save location (.osm)",
            defaultextension=".osm",
            filetypes=[("OpenStudio Model", "*.osm"), ("All files", "*.*")]
        )
        if not output_path:
            self.logger.warning("Output file selection cancelled.")
        return output_path

    def purge_unused_resources(self, model):
        try:
            active_constructions = set()
            
            for surf in model.getSurfaces():
                if surf.construction().is_initialized():
                    active_constructions.add(str(surf.construction().get().handle()))
                    
            for sub in model.getSubSurfaces():
                if sub.construction().is_initialized():
                    active_constructions.add(str(sub.construction().get().handle()))
                    
            for shading in model.getShadingSurfaces():
                if shading.construction().is_initialized():
                    active_constructions.add(str(shading.construction().get().handle()))
                    
            for im_def in model.getInternalMassDefinitions():
                if im_def.construction().is_initialized():
                    active_constructions.add(str(im_def.construction().get().handle()))

            removed_constructions = 0
            for construction in model.getConstructions():
                if str(construction.handle()) not in active_constructions:
                    construction.remove()
                    removed_constructions += 1

            active_materials = set()
            for construction in model.getConstructions():
                for layer in construction.layers():
                    active_materials.add(str(layer.handle()))

            removed_materials = 0
            for material in model.getMaterials():
                if str(material.handle()) not in active_materials:
                    material.remove()
                    removed_materials += 1

            self.logger.info("Purge operation completed. %d constructions and %d materials removed.", 
                             removed_constructions, removed_materials)
            
            return removed_constructions, removed_materials
            
        except Exception as e:
            self.logger.error("Error during resource purge %s\n%s", str(e), traceback.format_exc())
            return -1, -1

    def process_model(self, input_path, output_path):
        try:
            self.logger.info("Loading model %s", input_path)
            model_optional = openstudio.model.Model.load(openstudio.path(input_path))
            
            if not model_optional.is_initialized():
                self.logger.error("Failed to load OSM model.")
                print("Failed to load OSM model.")
                return False
                
            model = model_optional.get()
            
            print("Executing resource purge...")
            removed_constructions, removed_materials = self.purge_unused_resources(model)
            
            if removed_constructions >= 0 and removed_materials >= 0:
                print(f"Purge complete. Removed {removed_constructions} constructions and {removed_materials} materials.")
                
                success = model.save(openstudio.path(output_path), True)
                if success:
                    self.logger.info("Model saved successfully %s", output_path)
                    print("Process completed successfully.")
                    return True
                else:
                    self.logger.error("Failed to save model %s", output_path)
                    print("Failed to save the modified model.")
                    return False
            else:
                print("An error occurred during the purge process.")
                return False
                
        except Exception as e:
            self.logger.error("Error processing model %s", str(e))
            print("Processing failed.")
            return False

    def run_standalone(self):
        self.logger.info("Running in standalone mode.")
        
        main_root = Tk()
        main_root.withdraw()
        main_root.attributes('-topmost', True)
        
        try:
            input_path = self.select_input_file(main_root)
            if not input_path:
                print("Input file selection cancelled.")
                return False
                
            output_path = self.select_output_file(main_root)
            if not output_path:
                print("Output file selection cancelled.")
                return False
                
            return self.process_model(input_path, output_path)
            
        finally:
            main_root.destroy()

    def run_automated(self, input_path, output_path):
        self.logger.info("Running in automated mode.")
        return self.process_model(input_path, output_path)

def main():
    purger = ModelResourcePurger()
    args = sys.argv[1:]
    
    if len(args) == 2:
        success = purger.run_automated(args[0], args[1])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        success = purger.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage python resource_purger.py [input.osm output.osm]")
        print("Or run without arguments for dialog mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()