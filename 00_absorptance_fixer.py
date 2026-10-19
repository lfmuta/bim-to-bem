import os
import shutil
import tempfile
import logging
import sys
from tkinter import Tk, filedialog
import xml.etree.ElementTree as ET

class AbsorptanceTypeFixer:
    def __init__(self):
        logging.basicConfig(
            filename="xml_extir_to_extsolar.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )

    def _remove_namespace(self, xml_string):
        """Remove prefixes like ns0: inserted by ElementTree."""
        return xml_string.replace("ns0:", "").replace(":ns0", "")

    def process(self, input_path, output_path):
        """
        Replace Absorptance type 'ExtIR' with 'ExtSolar' in the given XML file.
        Operates in temp files to avoid direct editing.
        Returns (True, modific_count), or (False, exception).
        """
        temp_input = None
        temp_output = None
        try:
            # Temp copy for safe parsing
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(input_path)[1], delete=False) as tf:
                temp_input = tf.name
            shutil.copy(input_path, temp_input)
            # Parse & process
            tree = ET.parse(temp_input)
            root = tree.getroot()
            modified_count = 0
            for elem in root.findall(".//{*}Absorptance"):
                if elem.get("type") == "ExtIR":
                    elem.set("type", "ExtSolar")
                    modified_count += 1
            # Write to temp output
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(output_path)[1], delete=False, mode="w", encoding="utf-8") as tf_out:
                temp_output = tf_out.name
            tree.write(temp_output, encoding="UTF-8", xml_declaration=True)
            # Cleanup namespace prefixes for readability/compat (ElementTree quirk)
            with open(temp_output, "r", encoding="utf-8") as rf:
                cleaned = self._remove_namespace(rf.read())
            # Output to final file
            shutil.copy(temp_output, output_path)
            with open(output_path, "w", encoding="utf-8") as wf:
                wf.write(cleaned)
            logging.info(f"Substitution complete: {modified_count} occurrences in '{output_path}'")
            return True, modified_count
        except Exception as e:
            logging.error(f"Error processing '{input_path}': {e}")
            return False, e
        finally:
            for path in (temp_input, temp_output):
                if path and os.path.exists(path):
                    os.remove(path)

    def run_standalone(self):
        """
        GUI mode with Tk dialogs.
        """
        root = Tk()
        root.withdraw()
        input_path = filedialog.askopenfilename(
            filetypes=[("XML / GBXML", "*.xml *.gbxml")],
            title="Select your XML/GBXML file"
        )
        if not input_path:
            root.destroy()
            return False
        output_path = filedialog.asksaveasfilename(
            filetypes=[("XML / GBXML", "*.xml *.gbxml")],
            title="Save modified XML/GBXML as",
            defaultextension=".xml"
        )
        if not output_path:
            root.destroy()
            return False
        root.destroy()
        # Backup if overwriting
        if input_path == output_path:
            shutil.copy(input_path, input_path + ".bak")
            logging.info(f"Original file backed up at '{input_path}.bak'")
        result, info = self.process(input_path, output_path)
        if result:
            print(f"Completed! Modified {info} occurrences.\nFile saved as: {output_path}")
        else:
            print(f"ERROR: {info}")
        return result

    def run_automated(self, input_path, output_path):
        if not input_path.lower().endswith(('.xml', '.gbxml')):
            print("Invalid input extension.")
            return False
        result, info = self.process(input_path, output_path)
        if result:
            print(output_path) # For script chaining
            return True
        else:
            print(f"ERROR: {info}")
            return False

def main():
    fixer = AbsorptanceTypeFixer()
    args = sys.argv[1:]
    if len(args) == 2:
        success = fixer.run_automated(args[0], args[1])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        success = fixer.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python script.py [input.xml output.xml] or run without arguments for GUI")
        sys.exit(1)

if __name__ == "__main__":
    main()
