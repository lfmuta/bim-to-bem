import os
import shutil
import tempfile
import logging
import sys
from tkinter import Tk, filedialog
import openstudio

class GBXMLConverter:
    def __init__(self):
        logging.basicConfig(
            filename="gbxml_to_osm.log",
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )

    def convert(self, gbxml_path, osm_path):
        """Convert GBXML to OSM."""
        temp_path = None
        try:
            # Create temporary copy
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(gbxml_path)[1], delete=False) as temp_file:
                temp_path = temp_file.name
            shutil.copy(gbxml_path, temp_path)
            # Convert
            translator = openstudio.gbxml.GbXMLReverseTranslator()
            gbxml_model = translator.loadModel(openstudio.toPath(temp_path))
            if not gbxml_model.is_initialized():
                raise RuntimeError("Failed to initialize OpenStudio Model")
            model = gbxml_model.get()
            model.save(openstudio.toPath(osm_path), True)
            logging.info(f"Conversion successful: {osm_path}")
            return True
        except Exception as e:
            logging.error(f"Conversion failed: {e}")
            return False
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def run_standalone(self):
        """Stand-alone mode with file selection dialogs."""
        root = Tk()
        root.withdraw()
        # Select input file
        gbxml_path = filedialog.askopenfilename(
            filetypes=[("GBXML Files", "*.gbxml *.xml")],
            title="Select GBXML input file"
        )
        if not gbxml_path:
            root.destroy()
            return False
        # Select output location (nenhum nome sugerido!)
        osm_path = filedialog.asksaveasfilename(
            filetypes=[("OpenStudio Files", "*.osm")],
            title="Save OSM file as",
            defaultextension=".osm"
            # Não define initialfile
        )
        if not osm_path:
            root.destroy()
            return False
        root.destroy()
        return self.convert(gbxml_path, osm_path)

    def run_automated(self, gbxml_path, osm_path):
        """Automated mode for script chaining."""
        if not gbxml_path.lower().endswith(('.gbxml', '.xml')):
            return False
        return self.convert(gbxml_path, osm_path)

def main():
    converter = GBXMLConverter()
    args = sys.argv[1:]
    if len(args) == 2:
        # Automated mode: input and output provided
        success = converter.run_automated(args[0], args[1])
        if success:
            print(args[1]) # Output path for script chaining
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        # Stand-alone mode: interactive file selection
        success = converter.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python script.py [input.gbxml output.osm] or run without arguments for GUI")
        sys.exit(1)

if __name__ == "__main__":
    main()
