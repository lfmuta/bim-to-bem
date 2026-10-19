import os
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

import openstudio

ENERGYPLUS_VERSION = "24.2.0"
ENERGYPLUS_URL = ("https://github.com/NREL/EnergyPlus/releases/download/v24.2.0a/"
                  "EnergyPlus-24.2.0-94a887817b-Linux-Ubuntu22.04-x86_64.tar.gz")
REQUIRED_FILES = {
    "energyplus",
    "energyplus-24.2.0",
    "libenergyplusapi.so",
    "libenergyplusapi.so.24.2.0",
    "libpython3.12.so.1.0",
    "Energy+.idd",
    "Energy+.schema.epJSON",
}
DEFAULT_CACHE_DIR = Path.home() / ".cache" / f"energyplus-{ENERGYPLUS_VERSION}"


def find_energyplus(cache_dir=DEFAULT_CACHE_DIR):
    """Returns the path of an EnergyPlus executable already available on this machine, or an empty string."""
    candidates = [os.environ.get("ENERGYPLUS_EXE", ""), str(Path(cache_dir) / "energyplus"), shutil.which("energyplus") or ""]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return ""


def install_energyplus(cache_dir=DEFAULT_CACHE_DIR):
    """Downloads the Linux build of EnergyPlus and extracts only the files needed to run simulations."""
    cache_dir = Path(cache_dir)
    executable = cache_dir / "energyplus"
    if executable.is_file():
        return str(executable)
    partial_dir = cache_dir.with_name(cache_dir.name + "_partial")
    shutil.rmtree(partial_dir, ignore_errors=True)
    partial_dir.mkdir(parents=True)
    with urllib.request.urlopen(ENERGYPLUS_URL, timeout=600) as response:
        with tarfile.open(fileobj=response, mode="r|gz") as archive:
            for member in archive:
                name = Path(member.name).name
                if name not in REQUIRED_FILES or member.name.count("/") != 1:
                    continue
                if member.issym():
                    (partial_dir / name).symlink_to(member.linkname)
                elif member.isfile():
                    source = archive.extractfile(member)
                    target = partial_dir / name
                    with open(target, "wb") as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(member.mode | 0o644)
    missing = [name for name in REQUIRED_FILES if not (partial_dir / name).exists()]
    if missing:
        raise RuntimeError(f"EnergyPlus download incomplete, missing: {', '.join(sorted(missing))}")
    shutil.rmtree(cache_dir, ignore_errors=True)
    partial_dir.rename(cache_dir)
    return str(executable)


def energyplus_version(executable):
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except Exception:
        return ""


def translate_to_idf(osm_path, epw_path, run_dir):
    """Translates an OSM model to IDF with the weather file assigned, as the OpenStudio CLI does."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    model_opt = openstudio.model.Model.load(openstudio.path(str(osm_path)))
    if not model_opt.is_initialized():
        raise RuntimeError(f"Could not load model: {osm_path}")
    model = model_opt.get()
    openstudio.model.WeatherFile.setWeatherFile(model, openstudio.EpwFile(openstudio.path(str(epw_path))))
    translator = openstudio.energyplus.ForwardTranslator()
    workspace = translator.translateModel(model)
    errors = [str(message.logMessage()) for message in translator.errors()]
    if errors:
        raise RuntimeError("Translation errors:\n" + "\n".join(errors))
    idf_path = run_dir / "in.idf"
    workspace.save(openstudio.path(str(idf_path)), True)
    return idf_path


def start_simulation(executable, idf_path, epw_path, run_dir):
    """Starts EnergyPlus in the background and returns the process."""
    return subprocess.Popen([executable, "-w", str(epw_path), "-d", str(run_dir), str(idf_path)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
