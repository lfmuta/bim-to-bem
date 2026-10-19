import openstudio
import sys
import logging
import traceback
from datetime import datetime
from tkinter import Tk, filedialog

class OSMCleaner:
    def __init__(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"schedule_cleaner_{timestamp}.log"
        logging.basicConfig(
            filename=log_filename,
            filemode="w",
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            level=logging.INFO
        )
        self.logger = logging.getLogger("OSMCleaner")
        self.logger.info("Initializing OSMCleaner. Log file %s", log_filename)

    def select_input_file(self, parent_root):
        input_path = filedialog.askopenfilename(
            parent=parent_root,
            title="Select OSM file to clean",
            filetypes=[("OpenStudio Model", "*.osm"), ("All files", "*.*")]
        )
        if not input_path:
            self.logger.warning("Input file selection cancelled.")
        return input_path

    def select_output_file(self, parent_root):
        output_path = filedialog.asksaveasfilename(
            parent=parent_root,
            title="Save cleaned OSM file as",
            defaultextension=".osm",
            filetypes=[("OpenStudio Model", "*.osm"), ("All files", "*.*")]
        )
        if not output_path:
            self.logger.warning("Output file selection cancelled.")
        return output_path

    def clean_schedules(self, model):
        try:
            removed_count = 0

            for obj in model.getDefaultScheduleSets():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleRulesets():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleYears():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleWeeks():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleDays():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleConstants():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleCompacts():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleFixedIntervals():
                obj.remove()
                removed_count += 1

            for obj in model.getScheduleVariableIntervals():
                obj.remove()
                removed_count += 1

            limits_removed = 0
            # CORREÇÃO DA API: O plural correto da classe adiciona um segundo 's'
            for obj in model.getScheduleTypeLimitss():
                obj.remove()
                limits_removed += 1

            self.logger.info("Deep purge completed. %d schedules and %d type limits removed.", removed_count, limits_removed)
            return True

        except Exception as e:
            self.logger.error("Error cleaning schedules %s\n%s", str(e), traceback.format_exc())
            return False

    def process_model(self, input_path, output_path):
        try:
            self.logger.info("Loading model %s", input_path)
            translator = openstudio.osversion.VersionTranslator()
            osm_model_handle = translator.loadModel(openstudio.path(input_path))

            if not osm_model_handle.is_initialized():
                self.logger.error("Failed to load OSM file.")
                print("Failed to load OSM file.")
                return False

            model = osm_model_handle.get()

            print("Executing deep schedule purge...")
            success = self.clean_schedules(model)

            if success:
                save_status = model.save(openstudio.path(output_path), True)
                if save_status:
                    self.logger.info("Cleaned model saved successfully %s", output_path)
                    print("Process completed successfully.")
                    return True
                else:
                    self.logger.error("Failed to save the modified model.")
                    print("Failed to save the modified model.")
                    return False
            else:
                print("An error occurred during the purge process.")
                return False

        except Exception as e:
            self.logger.error("Processing failed %s", str(e))
            print("Processing failed.")
            return False

    def run_standalone(self):
        self.logger.info("Running in standalone mode.")
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        try:
            input_path = self.select_input_file(root)
            if not input_path:
                print("Input file selection cancelled.")
                return False

            output_path = self.select_output_file(root)
            if not output_path:
                print("Output file selection cancelled.")
                return False

            return self.process_model(input_path, output_path)
        finally:
            root.destroy()

    def run_automated(self, input_path, output_path):
        self.logger.info("Running in automated mode.")
        return self.process_model(input_path, output_path)

def main():
    cleaner = OSMCleaner()
    args = sys.argv[1:]

    if len(args) == 2:
        success = cleaner.run_automated(args[0], args[1])
        if success:
            print(args[1])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        success = cleaner.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage python schedule_cleaner.py [input.osm output.osm]")
        print("Or run without arguments for dialog mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()
