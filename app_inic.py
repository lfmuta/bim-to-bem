import contextlib
import importlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import types
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import openstudio
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)


class _HeadlessWidget:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _HeadlessWidget()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _HeadlessWidget()


def _headless_attribute(name):
    if name.startswith("__"):
        raise AttributeError(name)
    return _HeadlessWidget


def _install_headless_tkinter():
    """The isolated scripts import tkinter for their dialogs. Servers without a display have no tkinter."""
    try:
        importlib.import_module("tkinter")
    except ImportError:
        module = types.ModuleType("tkinter")
        module.__getattr__ = _headless_attribute
        sys.modules["tkinter"] = module


_install_headless_tkinter()
energyplus_runner = importlib.import_module("energyplus_runner")

step00 = importlib.import_module("00_absorptance_fixer")
step01 = importlib.import_module("01_gbxml_converter")
step02 = importlib.import_module("02_schedules_cleaner")
step03 = importlib.import_module("03_loads_enricher")
step04 = importlib.import_module("04_schedules_enricher")
step05 = importlib.import_module("05_airflow_assigner")
step06 = importlib.import_module("06_ideal_loads_assigner")
step07 = importlib.import_module("07_plenum_disabler")
step08 = importlib.import_module("08_construction_renamer")
step09 = importlib.import_module("09_surface_modifier")
step10 = importlib.import_module("10_air_boundary_assigner")
step12 = importlib.import_module("12_run_simulation")
redcep = importlib.import_module("14_a_redcep")
coefficients = importlib.import_module("14_b_crcepd-a")
wall_modifier = importlib.import_module("wall_modifier")
roof_modifier = importlib.import_module("roof_modifier")
floor_modifier = importlib.import_module("floor_modifier")
glazing_modifier = importlib.import_module("glazing_modifier")
skylight_remover = importlib.import_module("skylight_remover")
shade_remover = importlib.import_module("shade_remover")
lighting_modifier = importlib.import_module("lighting_modifier")
spacetype_utils = importlib.import_module("spacetype_utils")

REFERENCE_DPI = 15.5
CEER_REFERENCE = 3.24
OUTPUT_VARIABLES = [
    "Zone Ideal Loads Supply Air Total Heating Energy",
    "Zone Ideal Loads Supply Air Total Cooling Energy",
    "Zone Lights Electricity Energy",
    "Zone Electric Equipment Electricity Energy",
    "Zone People Occupant Count",
]
WORK_ROOT = Path(tempfile.gettempdir()) / "inic_gbxml"
WORK_DIR_MAX_AGE_HOURS = 12
SIMULATION_LEFTOVERS = ("eplusout.sql", "eplusout.eso", "eplusout.mtr", "data_point.zip", "pre-preprocess.idf", "in.osm")
EDUCATION_LEVELS = {
    "Ensino fundamental e médio (1,5 m²/pessoa)": 1.5,
    "Ensino superior (1,5 m²/pessoa)": 1.5,
    "Educação infantil (2,5 m²/pessoa)": 2.5,
}
TRANSLATIONS = {
    "00 Absortância ExtIR para ExtSolar": "00 Absorptance ExtIR to ExtSolar",
    "01 Conversão gbXML para OSM": "01 gbXML to OSM conversion",
    "02 Limpeza de schedules": "02 Schedule cleanup",
    "03 Cargas internas": "03 Internal loads",
    "04 Rotinas de uso e calor metabólico": "04 Use schedules and metabolic heat",
    "07 Plenum fora da área total": "07 Plenum excluded from total area",
    "08 Renomeação de elementos": "08 Element renaming",
    "09 Condições de contorno": "09 Boundary conditions",
    "10 Fronteiras de ar e integração de zonas": "10 Air boundaries and zone merging",
    "05 Ar externo e infiltração por frestas": "05 Outdoor air and crack infiltration",
    "06 Sistema ideal e termostato": "06 Ideal loads system and thermostat",
    "Referência: paredes (Tabela A.9)": "Reference: walls (Table A.9)",
    "Referência: cobertura (Tabela A.9)": "Reference: roof (Table A.9)",
    "Referência: piso (Tabela A.9)": "Reference: floor (Table A.9)",
    "Referência: PAF 40% e vidro (Tabela A.2)": "Reference: WWR 40% and glass (Table A.2)",
    "Referência: PAZ 0%": "Reference: skylight ratio 0%",
    "Referência: sombreamento de fachada": "Reference: facade shading",
    "Referência: DPI 15,5 W/m²": "Reference: LPD 15.5 W/m²",
    "Referência: infiltração por frestas": "Reference: crack infiltration",
    "Tipologia educacional. Portaria Inmetro 309/2022, Anexo C.I.":
        "Educational building typology. Inmetro Ordinance 309/2022, Annex C.I.",
    "1. Arquivos de entrada": "1. Input files",
    "Arquivo gbXML exportado do Revit": "gbXML file exported from Revit",
    "Arquivo climático (.epw)": "Weather file (.epw)",
    "2. Iluminação": "2. Lighting",
    "3. Processamento": "3. Processing",
    "Gerar os modelos, simular e classificar": "Build the models, simulate and rate",
    "4. Geometria do modelo real": "4. Real model geometry",
    "Arraste para girar, role para aproximar e passe o mouse para ver o elemento. Clique em um item da legenda para esconder ou mostrar esse elemento. No modelo de referência, os sombreamentos de fachada (brises, beirais, marquises) são retirados automaticamente e o entorno é mantido (item C.I.4).":
        "Drag to rotate, scroll to zoom and hover to see the element. Click a legend item to hide or show that element. In the reference model, facade shading devices (louvers, overhangs, canopies) are removed automatically and the surroundings are kept (item C.I.4).",
    "5. Classificação": "5. Rating",
    "CEER real {ceer:.2f}, CEER referência {ceer_ref}. Iluminação e equipamentos ajustados para {days} dias (simulados: {simulated}). Fator de energia primária fcE = {fce}. O RedCEP desconta o consumo de equipamentos dos dois modelos (Eq. 8.1).":
        "Real CEER {ceer:.2f}, reference CEER {ceer_ref}. Lighting and equipment adjusted to {days} days (simulated: {simulated}). Primary energy factor fcE = {fce}. RedCEP excludes the equipment consumption of both models (Eq. 8.1).",
    "6. Arquivos": "6. Files",
    "Mostrar arquivos": "Show files",
    "Etiqueta de eficiência energética": "Energy efficiency label",
    "Edificações comerciais, de serviços e públicas": "Commercial, service and public buildings",
    "Método de simulação da INI-C. Portaria Inmetro 309/2022, Anexo C.I.": "INI-C simulation method. Inmetro Ordinance 309/2022, Annex C.I.",
    "Intensidade de uso de energia primária do modelo real": "Primary energy use intensity of the real model",
    "Refrigeração": "Cooling",
    "Aquecimento": "Heating",
    "Equipamentos": "Equipment",
    "Total": "Total",
    "Uso final ({unit})": "End use ({unit})",
    "Diferença": "Difference",
    "Eq. 8.1, sem equipamentos na base": "Eq. 8.1, equipment excluded from the base",
    "kWh/m².ano": "kWh/m².year",
    "kWh/ano": "kWh/year",
    "Valores em energia primária (fcE = {fce}) por área total construída ({area} m²). A diferença do total inclui os equipamentos; o RedCEP os desconta da base (Eq. 8.1).":
        "Values in primary energy (fcE = {fce}) per total floor area ({area} m²). The total difference includes equipment; RedCEP excludes it from the base (Eq. 8.1).",
    "Modelo real (kWh/ano)": "Real model (kWh/year)",
    "Modelo real (kWh/m².ano)": "Real model (kWh/m².year)",
    "Modelo de referência (kWh/ano)": "Reference model (kWh/year)",
    "Modelo de referência (kWh/m².ano)": "Reference model (kWh/m².year)",
    "Indicador": "Indicator",
    "Valor": "Value",
    "Modelo real (.osm)": "Real model (.osm)",
    "Modelo de referência (.osm)": "Reference model (.osm)",
    "Resultados (.csv)": "Results (.csv)",
    "Tudo (.zip)": "Everything (.zip)",
    "Falha na etapa: {label}": "Step failed: {label}",
    "Classificação INI-C pelo método de simulação": "INI-C rating by the simulation method",
    "Parâmetros": "Parameters",
    "Zona bioclimática (ABNT NBR 15220-3)": "Bioclimatic zone (ABNT NBR 15220-3)",
    "Nível de ensino (Tabela A.2)": "Education level (Table A.2)",
    "CEER do sistema de condicionamento de ar do projeto (W/W)": "CEER of the design air conditioning system (W/W)",
    "O projeto possui sistema de aquecimento": "The design has a heating system",
    "Motor de simulação": "Simulation engine",
    "Envie o arquivo gbXML para começar.": "Upload the gbXML file to start.",
    "Espaços do gbXML ({count})": "gbXML spaces ({count})",
    "{count} espaço(s) com spaceType fora do dicionário APP/APT (spacetype_utils.py). Eles recebem pessoas e equipamentos como APP, mas não recebem sistema de condicionamento. Revise no Revit.":
        "{count} space(s) with a spaceType outside the APP/APT dictionary (spacetype_utils.py). They receive people and equipment as APP, but no air conditioning system. Review them in Revit.",
    "DPI de projeto encontrada no gbXML. Sistema de iluminação avaliado: modelo real com a DPI do gbXML, referência com {dpi} W/m² nos ambientes com iluminação (item C.I.4).":
        "Design LPD found in the gbXML. Lighting system evaluated: real model with the gbXML LPD, reference with {dpi} W/m² in the spaces with lighting (item C.I.4).",
    "O gbXML não tem densidade de potência de iluminação (LightPowerPerArea). Escolha como seguir:":
        "The gbXML has no lighting power density (LightPowerPerArea). Choose how to proceed:",
    "Iluminação": "Lighting",
    "Informe o CEER do sistema de projeto na barra lateral.": "Enter the CEER of the design system in the sidebar.",
    "Registro das etapas": "Processing log",
    "Envie o arquivo climático (.epw) para simular.": "Upload the weather file (.epw) to simulate.",
    "Informe o caminho do openstudio.exe na barra lateral.": "Enter the openstudio.exe path in the sidebar.",
    "real": "real",
    "de referência": "reference",
    "Classificação geral": "Overall rating",
    "Envoltória": "Envelope",
    "Modelo real": "Real model",
    "Modelo de referência": "Reference model",
    "Simulação real": "Real model simulation",
    "Simulação de referência": "Reference model simulation",
    "Item C.I.6: a carga de aquecimento (setpoint 21 °C) só é calculada quando há aquecimento em projeto.":
        "Item C.I.6: the heating load (setpoint 21 °C) is only calculated when the design includes heating.",
    "CEEA do sistema de aquecimento do projeto (W/W)": "CEEA of the design heating system (W/W)",
    "Opções avançadas": "Advanced options",
    "Fp, vazão por pessoa (L/s.pessoa)": "Fp, airflow per person (L/s.person)",
    "Fa, vazão por área (L/s.m²)": "Fa, airflow per area (L/s.m²)",
    "Caminho do openstudio.exe": "openstudio.exe path",
    "DPI de projeto (W/m²)": "Design LPD (W/m²)",
    "Processando etapas 00 a 10...": "Processing steps 00 to 10...",
    "Gerando o modelo de referência...": "Building the reference model...",
    "Simulando os dois modelos no EnergyPlus (pode levar vários minutos)...":
        "Simulating both models in EnergyPlus (this may take several minutes)...",
    "Zona bioclimática": "Bioclimatic zone",
    "Classificação da envoltória": "Envelope rating",
    "Erro: {error}": "Error: {error}",
    "Equação C.I.8: para split e janela, 1,72 + 0,5 x CEER, ou dado do fabricante.":
        "Equation C.I.8: for split and window units, 1.72 + 0.5 x CEER, or manufacturer data.",
    "EnergyPlus {version} pronto.": "EnergyPlus {version} ready.",
    "EnergyPlus {version} será baixado na primeira simulação (cerca de 190 MB, uma única vez).":
        "EnergyPlus {version} will be downloaded on the first simulation (about 190 MB, only once).",
    "Espaço": "Space",
    "Classificação": "Classification",
    "DPI gbXML (W/m²)": "gbXML LPD (W/m²)",
    "Baixando o EnergyPlus (só na primeira vez)...": "Downloading EnergyPlus (first time only)...",
    "A simulação do modelo {name} falhou.": "The {name} model simulation failed.",
    "Não foi possível executar o OpenStudio nesse caminho.": "OpenStudio could not be run from this path.",
    "Falha ao preparar a simulação: {error}": "Failed to prepare the simulation: {error}",
    "Versões diferentes: CLI {cli}, Python {python}. Use a mesma versão nos dois.":
        "Different versions: CLI {cli}, Python {python}. Use the same version for both.",
    "Sem classificação": "Unclassified",
    "Não foi possível baixar o EnergyPlus: {error}": "EnergyPlus could not be downloaded: {error}",
    "Ensino fundamental e médio (1,5 m²/pessoa)": "Primary and secondary school (1.5 m²/person)",
    "Ensino superior (1,5 m²/pessoa)": "Higher education (1.5 m²/person)",
    "Educação infantil (2,5 m²/pessoa)": "Early childhood education (2.5 m²/person)",
    "Parede externa": "Exterior wall",
    "Parede interna": "Interior wall",
    "Piso em contato com o solo": "Ground floor slab",
    "Piso entre pavimentos ou exposto": "Intermediate or exposed floor",
    "Cobertura": "Roof",
    "Forro ou laje interna": "Interior ceiling or slab",
    "Janela ou porta de vidro": "Window or glass door",
    "Porta": "Door",
    "Claraboia": "Skylight",
    "Sombreamento de fachada (sai na referência)": "Facade shading (removed in the reference)",
    "Sombreamento de entorno (fica nos dois modelos)": "Surrounding shading (kept in both models)",
    "Carga térmica de refrigeração CgTR": "Cooling thermal load CgTR",
    "Carga térmica de aquecimento CgTA": "Heating thermal load CgTA",
    "Consumo de refrigeração CR": "Cooling consumption CR",
    "Consumo de aquecimento CAE": "Heating consumption CAE",
    "Consumo de iluminação CIL": "Lighting consumption CIL",
    "Consumo de equipamentos CEQ": "Equipment consumption CEQ",
    "Consumo de energia elétrica CEE": "Electricity consumption CEE",
    "Consumo de energia primária CEP": "Primary energy consumption CEP",
    "Informar a DPI de projeto (sistema de iluminação avaliado)": "Enter the design LPD (lighting system evaluated)",
    "Não avaliar o sistema de iluminação (DPI de referência {dpi} W/m² só nas APPs, nos dois modelos)":
        "Do not evaluate the lighting system (reference LPD {dpi} W/m² in APP spaces only, in both models)",
    "piso": "floor",
    "cobertura ou forro": "roof or ceiling",
    "O modelo não está fechado. Estes espaços estão sem piso e/ou sem cobertura:":
        "The model is not closed. These spaces have no floor and/or no roof:",
    "No gbXML, essas faces vieram como superfícies do ambiente com ele mesmo (InteriorFloor ou Air), que o OpenStudio descarta. No Revit, desenhe o piso e a laje de cobertura ou o telhado com a opção Delimitação de ambiente marcada, faça o limite superior dos ambientes chegar até eles e exporte o gbXML de novo. Se o telhado aparece no modelo 3D como sombreamento, é sinal de que ele não está delimitando os ambientes.":
        "In the gbXML these faces came as surfaces between the room and itself (InteriorFloor or Air), which OpenStudio discards. In Revit, model the floor and the roof slab or roof with Room Bounding checked, extend the rooms' upper limit up to them and export the gbXML again. If the roof shows up in the 3D model as shading, it is not bounding the rooms.",
    "Classificação da iluminação": "Lighting rating",
    "Classificação do condicionamento de ar": "Air conditioning rating",
    "Condicionamento de ar": "Air conditioning",
    "Não avaliado": "Not evaluated",
    "Classificações parciais dos sistemas": "Partial ratings of the systems",
    "A > {a} %, B > {b} %, C > {c} %, D de 0 a {c} %, E < 0 %":
        "A > {a} %, B > {b} %, C > {c} %, D from 0 to {c} %, E < 0 %",
    "Eq. 8.1, Tabela 8.2. CRCEPD-A = {crc:.2f}, i = {i:.2f} %. Limites: {limits}.":
        "Eq. 8.1, Table 8.2. CRCEPD-A = {crc:.2f}, i = {i:.2f} %. Limits: {limits}.",
    "Eq. C.I.10, Tabela 8.4. CRCgTTD-A = {crc:.2f}, i = {i:.2f} %.":
        "Eq. C.I.10, Table 8.4. CRCgTTD-A = {crc:.2f}, i = {i:.2f} %.",
    "Eq. B.II.1, Tabela 8.6. CRCRD-A = {crc:.2f}, i = {i:.2f} %.":
        "Eq. B.II.1, Table 8.6. CRCRD-A = {crc:.2f}, i = {i:.2f} %.",
    "Eq. B.III.1, Tabela 8.8. DPIL A = 7,5 e D = 15,5 W/m² (Tabela B.III.2), i = {i:.2f} %.":
        "Eq. B.III.1, Table 8.8. LPD limit A = 7.5 and D = 15.5 W/m² (Table B.III.2), i = {i:.2f} %.",
    "O gbXML não tem DPI de projeto e o sistema de iluminação não foi avaliado.":
        "The gbXML has no design LPD and the lighting system was not evaluated.",
    "Este campo vale apenas para sistemas unitários. Sistemas centrais (por exemplo, com resfriadores de líquido) têm o CEER calculado pelo SPLV ou pelo fator K (item B.II.4.2), que não é tratado por esta ferramenta.":
        "This field applies to unitary systems only. Central systems (for example, with chillers) have their CEER calculated from the SPLV or the K factor (item B.II.4.2), which this tool does not handle.",
    "Somente sistemas unitários (janela, split). CEER ponderado pela capacidade de refrigeração, Equação B.II.5: equipamentos inverter usam o IDRS da etiqueta Inmetro (corrigido pela Tabela B.II.1 nas zonas 2R, 4A, 4B, 5B e 6B) e equipamentos de rotação fixa usam 1,062 x CEE.":
        "Unitary systems only (window, split). CEER weighted by cooling capacity, Equation B.II.5: inverter units use the IDRS from the Inmetro label (corrected by Table B.II.1 in zones 2R, 4A, 4B, 5B and 6B) and fixed speed units use 1.062 x CEE.",
    "Renovação de ar nas APPs, aplicada igualmente aos modelos real e de referência. Os valores iniciais são os da ABNT NBR 16401-3, Tabela 1, sala de aula, nível 1.":
        "Outdoor air in long-stay spaces (APP), applied equally to the real and reference models. The initial values are those of ABNT NBR 16401-3, Table 1, classroom, level 1.",
}
CLASS_COLORS = {"A": "#00A651", "B": "#8CC63F", "C": "#FFF200", "D": "#FF9E1B", "E": "#ED1C24"}


def t(text, **values):
    """Returns the text in the language chosen on the page, filling the placeholders."""
    if st.session_state.get("lang") == "en":
        text = TRANSLATIONS.get(text, text)
    return text.format(**values) if values else text


def run_step(label, function, *args, **kwargs):
    """Runs one processing step capturing its console output. Stops the app when the step fails."""
    label = t(label)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        try:
            result = function(*args, **kwargs)
        except Exception as error:
            result = False
            print(t("Erro: {error}", error=error))
    output = buffer.getvalue().strip()
    st.session_state.setdefault("log", []).append(f"[{label}]\n{output}" if output else f"[{label}]")
    if result is False or result is None:
        st.error(t("Falha na etapa: {label}", label=label))
        if output:
            st.code(output)
        st.stop()
    return result


def find_openstudio_cli():
    found = shutil.which("openstudio")
    if found:
        return found
    for candidate in sorted(Path("C:/").glob("openstudio-3*/bin/openstudio.exe"), reverse=True):
        return str(candidate)
    return ""


def cli_version(cli_path):
    try:
        result = subprocess.run([cli_path, "--version"], capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except Exception:
        return ""


def inspect_gbxml(gbxml_path):
    """Reads space types and lighting power densities from the gbXML file."""
    namespace = {"gbXML": "http://www.gbxml.org/schema"}
    root = ET.parse(gbxml_path).getroot()
    rows = []
    for space in root.findall(".//gbXML:Space", namespace):
        space_type = space.get("spaceType", "")
        name = space.findtext("gbXML:Name", default=space.get("id", ""), namespaces=namespace)
        lpd = float(space.findtext("gbXML:LightPowerPerArea", default="0", namespaces=namespace) or 0)
        label = spacetype_utils.get_space_type_label_by_name(space_type)
        rows.append({"name": name, "space_type": space_type, "label": label, "lpd": lpd})
    return pd.DataFrame(rows, columns=["name", "space_type", "label", "lpd"])


def build_real_model(gbxml_path, work_dir, area_per_person, lighting_mode, dpi_value, oa_person, oa_area, heating):
    base = work_dir / "real"
    base.mkdir(parents=True, exist_ok=True)
    corrected = base / "gbxml_corrigido.xml"
    paths = [base / f"real_step{i:02d}.osm" for i in range(1, 11)]
    run_step("00 Absortância ExtIR para ExtSolar", step00.AbsorptanceTypeFixer().run_automated, str(gbxml_path), str(corrected))
    run_step("01 Conversão gbXML para OSM", step01.GBXMLConverter().run_automated, str(corrected), str(paths[0]))
    run_step("02 Limpeza de schedules", step02.OSMCleaner().run_automated, str(paths[0]), str(paths[1]))
    run_step("03 Cargas internas", step03.OSMEnricher(area_per_person, lighting_mode, dpi_value).run_automated, str(corrected), str(paths[1]), str(paths[2]))
    run_step("04 Rotinas de uso e calor metabólico", step04.ScheduleEnricher().run_automated, str(paths[2]), str(paths[3]))
    run_step("07 Plenum fora da área total", step07.PlenumFloorAreaDisabler().run_automated, str(paths[3]), str(paths[4]))
    run_step("08 Renomeação de elementos", step08.ModelRenamer().run_automated, str(paths[4]), str(paths[5]))
    run_step("09 Condições de contorno", step09.OSMSurfacePropertySetter().run_automated, str(paths[5]), str(paths[6]))
    run_step("10 Fronteiras de ar e integração de zonas", step10.OSMAirBoundarySetter().run_automated, str(paths[6]), str(paths[7]))
    run_step("05 Ar externo e infiltração por frestas", step05.AirflowAssigner(oa_person, oa_area).run_automated, str(paths[7]), str(paths[8]))
    run_step("06 Sistema ideal e termostato", step06.IdealLoadsAssigner(heating).run_automated, str(paths[8]), str(paths[9]))
    final = base / "modelo_real.osm"
    shutil.copy(paths[9], final)
    return final


GEOMETRY_CATEGORIES = [
    ("exterior_wall", "Parede externa", "#D7C4A3", 0.35),
    ("interior_wall", "Parede interna", "#E6E6E6", 0.15),
    ("ground_floor", "Piso em contato com o solo", "#8D6E63", 0.6),
    ("floor", "Piso entre pavimentos ou exposto", "#BCAAA4", 0.3),
    ("roof", "Cobertura", "#C0504D", 0.45),
    ("ceiling", "Forro ou laje interna", "#CFCFCF", 0.15),
    ("window", "Janela ou porta de vidro", "#29B6F6", 0.85),
    ("door", "Porta", "#5D4037", 0.95),
    ("skylight", "Claraboia", "#81D4FA", 0.85),
    ("shading_facade", "Sombreamento de fachada (sai na referência)", "#7E57C2", 0.9),
    ("shading_context", "Sombreamento de entorno (fica nos dois modelos)", "#43A047", 0.6),
]
SUB_SURFACE_OFFSET = 0.02


def spaces_missing_enclosure(osm_path):
    """Lists the spaces without a floor or without a roof/ceiling surface, which EnergyPlus cannot simulate correctly."""
    model = openstudio.model.Model.load(openstudio.path(str(osm_path))).get()
    missing = []
    for space in model.getSpaces():
        surface_types = {surface.surfaceType() for surface in space.surfaces()}
        lacks = [part for part, surface_type in (("floor", "Floor"), ("roof", "RoofCeiling")) if surface_type not in surface_types]
        if lacks:
            missing.append((space.nameString(), lacks))
    return missing


def _site_triangles(planar_surface, transformation, offset=None):
    triangles = []
    for triangle in planar_surface.triangulation():
        points = []
        for point in triangle:
            if offset is not None:
                point = openstudio.Point3d(point.x() + offset[0], point.y() + offset[1], point.z() + offset[2])
            site_point = transformation * point
            points.append((site_point.x(), site_point.y(), site_point.z()))
        triangles.append(points)
    return triangles


def _site_outline(planar_surface, transformation, offset=None):
    points = []
    for point in planar_surface.vertices():
        if offset is not None:
            point = openstudio.Point3d(point.x() + offset[0], point.y() + offset[1], point.z() + offset[2])
        site_point = transformation * point
        points.append((site_point.x(), site_point.y(), site_point.z()))
    return points


def _surface_category(surface):
    surface_type = surface.surfaceType()
    boundary = surface.outsideBoundaryCondition()
    if surface_type == "Wall":
        return "exterior_wall" if boundary == "Outdoors" else "interior_wall"
    if surface_type == "Floor":
        return "ground_floor" if boundary.startswith("Ground") or boundary == "Foundation" else "floor"
    return "roof" if boundary == "Outdoors" else "ceiling"


def _sub_surface_category(sub_surface):
    sub_type = sub_surface.subSurfaceType()
    if sub_type in ("Door", "OverheadDoor"):
        return "door"
    if sub_type in ("Skylight", "TubularDaylightDome", "TubularDaylightDiffuser"):
        return "skylight"
    return "window"


def model_geometry(osm_path):
    """Returns the triangulated geometry of the model in site coordinates, grouped by construction element."""
    model = openstudio.model.Model.load(openstudio.path(str(osm_path))).get()
    geometry = {key: {"triangles": [], "outlines": []} for key, _, _, _ in GEOMETRY_CATEGORIES}
    for surface in model.getSurfaces():
        space_opt = surface.space()
        if not space_opt.is_initialized():
            continue
        transformation = space_opt.get().siteTransformation()
        category = geometry[_surface_category(surface)]
        category["triangles"].extend(_site_triangles(surface, transformation))
        category["outlines"].append(_site_outline(surface, transformation))
    for sub_surface in model.getSubSurfaces():
        space_opt = sub_surface.space()
        if not space_opt.is_initialized():
            continue
        transformation = space_opt.get().siteTransformation()
        normal = sub_surface.outwardNormal()
        offset = (normal.x() * SUB_SURFACE_OFFSET, normal.y() * SUB_SURFACE_OFFSET, normal.z() * SUB_SURFACE_OFFSET)
        category = geometry[_sub_surface_category(sub_surface)]
        category["triangles"].extend(_site_triangles(sub_surface, transformation, offset))
        category["outlines"].append(_site_outline(sub_surface, transformation, offset))
    remover = shade_remover.ShadingSurfaceRemover(log_path=str(Path(tempfile.gettempdir()) / "shading_inspection.log"))
    remover.model = model
    for shading in model.getShadingSurfaces():
        group_opt = shading.shadingSurfaceGroup()
        transformation = group_opt.get().siteTransformation() if group_opt.is_initialized() else openstudio.Transformation()
        category = geometry["shading_facade" if remover.is_facade_device(shading) else "shading_context"]
        category["triangles"].extend(_site_triangles(shading, transformation))
        category["outlines"].append(_site_outline(shading, transformation))
    return geometry


def _mesh(triangles, color, opacity, name):
    xs, ys, zs, i, j, k = [], [], [], [], [], []
    for triangle in triangles:
        base = len(xs)
        for x, y, z in triangle:
            xs.append(x)
            ys.append(y)
            zs.append(z)
        i.append(base)
        j.append(base + 1)
        k.append(base + 2)
    return go.Mesh3d(x=xs, y=ys, z=zs, i=i, j=j, k=k, color=color, opacity=opacity, name=name, flatshading=True,
                     hovertemplate=f"{name}<extra></extra>", showlegend=True, legendgroup=name)


def _edges(polygons, name):
    xs, ys, zs = [], [], []
    for polygon in polygons:
        for x, y, z in list(polygon) + [polygon[0]]:
            xs.append(x)
            ys.append(y)
            zs.append(z)
        xs.append(None)
        ys.append(None)
        zs.append(None)
    return go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color="#505050", width=1), hoverinfo="skip",
                        showlegend=False, legendgroup=name)


def geometry_figure(geometry):
    """3D view of the model colored by construction element. Clicking a legend item hides or shows that element."""
    figure = go.Figure()
    for key, label, color, opacity in GEOMETRY_CATEGORIES:
        data = geometry[key]
        if not data["triangles"]:
            continue
        name = t(label)
        figure.add_trace(_mesh(data["triangles"], color, opacity, name))
        figure.add_trace(_edges(data["outlines"], name))
    figure.update_layout(
        scene=dict(aspectmode="data", xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
                   domain=dict(x=[0.28, 1.0], y=[0.0, 1.0])),
        margin=dict(l=0, r=0, t=0, b=0), height=600,
        legend=dict(x=0.0, y=1.0, xanchor="left", yanchor="top"),
    )
    return figure


def build_reference_model(real_osm, work_dir, lighting_app_only):
    base = work_dir / "referencia"
    base.mkdir(parents=True, exist_ok=True)
    paths = [base / f"ref_step{i:02d}.osm" for i in range(1, 9)]
    model = openstudio.model.Model.load(openstudio.path(str(real_osm))).get()
    stories = {story.nameString(): {"typology": "Educational"} for story in model.getBuildingStorys()}
    glazing_config = json.dumps({"main_orientation": "N", "stories": stories})
    run_step("Referência: paredes (Tabela A.9)", wall_modifier.WallConstructionModifier().run_automated, str(real_osm), str(paths[0]))
    run_step("Referência: cobertura (Tabela A.9)", roof_modifier.RoofConstructionModifier().run_automated, str(paths[0]), str(paths[1]))
    run_step("Referência: piso (Tabela A.9)", floor_modifier.INICFloorModifier().run_automated, str(paths[1]), str(paths[2]))
    run_step("Referência: PAF 40% e vidro (Tabela A.2)", glazing_modifier.WWRModifier().run_automated, str(paths[2]), str(paths[3]), glazing_config)
    run_step("Referência: PAZ 0%", skylight_remover.OpenStudioSkylightRemover(str(paths[3]), str(paths[4]), assume_yes=True).run_cli)
    remover = shade_remover.ShadingSurfaceRemover(log_path=str(base / "shading_removal.log"))
    run_step("Referência: sombreamento de fachada", remover.run_pipeline, paths[4], paths[5])
    run_step("Referência: DPI 15,5 W/m²", lighting_modifier.LightingPowerDensityModifier().run_automated, str(paths[5]), str(paths[6]), lighting_app_only)
    run_step("Referência: infiltração por frestas", step05.AirflowAssigner().run_automated, str(paths[6]), str(paths[7]), True)
    final = base / "modelo_referencia.osm"
    shutil.copy(paths[7], final)
    return final


def prepare_simulation(osm_path, epw_path, sim_dir, engine):
    model = step12.load_osm_model_integrated(osm_path)
    step12.apply_inic_simulation_settings(model)
    for variable in model.getOutputVariables():
        variable.remove()
    step12.add_output_variables(model, OUTPUT_VARIABLES)
    sim_dir.mkdir(parents=True, exist_ok=True)
    model_path = sim_dir / osm_path.name
    step12.save_model_as_integrated(model, model_path)
    if engine == "cli":
        return step12.prepare_workflow_osw_integrated(model_path=model_path, epw_path=epw_path)
    return energyplus_runner.translate_to_idf(model_path, epw_path, sim_dir / "run")


def start_simulation(engine, executable, job, epw_path):
    """Starts one simulation, with the OpenStudio CLI (job is an OSW file) or directly in EnergyPlus (job is an IDF file)."""
    if engine == "cli":
        return subprocess.Popen([executable, "run", "-w", str(job)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return energyplus_runner.start_simulation(executable, job, epw_path, Path(job).parent)


def wait_simulations(processes):
    results = {}
    for name, process in processes.items():
        stdout, stderr = process.communicate()
        results[name] = (process.returncode, stdout, stderr)
    return results


def run_reference_and_simulation(work_dir, epw_file, engine, executable, lighting_app_only, lighting_mode,
                                 ceer_real, ceea_real, bioclimatic_zone):
    """Builds the reference model from the real one, simulates both models and stores the rating results."""
    epw_path = work_dir / "clima.epw"
    epw_path.write_bytes(epw_file.getvalue())
    if engine == "energyplus" and not executable:
        with st.spinner(t("Baixando o EnergyPlus (só na primeira vez)...")):
            try:
                executable = energyplus_runner.install_energyplus()
            except Exception as error:
                st.error(t("Não foi possível baixar o EnergyPlus: {error}", error=error))
                st.stop()
    # The real model simulation starts first and runs while the reference model is built.
    processes = {}
    try:
        job = prepare_simulation(st.session_state["real_osm"], epw_path, work_dir / "simulacao_real", engine)
    except Exception as error:
        st.error(t("Falha ao preparar a simulação: {error}", error=error))
        st.stop()
    processes["real"] = start_simulation(engine, executable, job, epw_path)
    with st.spinner(t("Gerando o modelo de referência...")):
        try:
            ref_osm = build_reference_model(st.session_state["real_osm"], work_dir, lighting_app_only)
            job = prepare_simulation(ref_osm, epw_path, work_dir / "simulacao_referencia", engine)
        except BaseException as error:
            # run_step stops the script with a non-Exception signal; the running simulation must not be left behind.
            processes["real"].kill()
            if not isinstance(error, Exception):
                raise
            st.error(t("Falha ao preparar a simulação: {error}", error=error))
            st.stop()
    processes["referencia"] = start_simulation(engine, executable, job, epw_path)
    with st.spinner(t("Simulando os dois modelos no EnergyPlus (pode levar vários minutos)...")):
        outcome = wait_simulations(processes)
    model_names = {"real": t("real"), "referencia": t("de referência")}
    for name, (code, stdout, stderr) in outcome.items():
        if code != 0:
            st.error(t("A simulação do modelo {name} falhou.", name=model_names[name]))
            err_file = work_dir / f"simulacao_{name}" / "run" / "eplusout.err"
            st.code((stdout + "\n" + stderr)[-3000:])
            if err_file.exists():
                severe = [line for line in err_file.read_text(errors="ignore").splitlines() if "Severe" in line or "Fatal" in line]
                st.code("\n".join(severe[:30]))
            st.stop()

    real_run = work_dir / "simulacao_real" / "run"
    ref_run = work_dir / "simulacao_referencia" / "run"
    ceea = ceea_real if ceea_real else 1.72 + 0.5 * ceer_real
    with contextlib.redirect_stdout(io.StringIO()):
        real = redcep.calculate_consumption(real_run / "eplusout.csv", ceer_real, ceea)
        ref = redcep.calculate_consumption(ref_run / "eplusout.csv", CEER_REFERENCE, CEER_REFERENCE)
        real_areas = redcep.extract_building_areas(real_run / "eplustbl.htm")
        ref_areas = redcep.extract_building_areas(ref_run / "eplustbl.htm")
    results = redcep.calculate_cep_and_redcep(real, ref, real_areas, ref_areas)
    results["coefficients"] = coefficients.calculate_coefficients(bioclimatic_zone)
    results["lighting_evaluated"] = lighting_mode != "reference"
    st.session_state["results"] = results
    st.session_state["ref_osm"] = ref_osm
    remove_large_leftovers(work_dir)


def _difference_html(reference, real, decimals=2):
    difference = reference - real
    percent = 100 * difference / reference if reference else 0.0
    if abs(difference) < 0.005:
        return f"<span style='color:#7f8c8d'>= 0.00 ({0:+.1f} %)</span>"
    arrow, color = ("&#8595;", "#27ae60") if difference > 0 else ("&#8593;", "#c0392b")
    return f"<span style='color:{color};font-weight:600'>{arrow} {abs(difference):.{decimals}f} ({-percent:+.1f} %)</span>"


def energy_label(results, general_class):
    """Shows the rating in the layout of the INI-C energy label: class scale, overall class, energy use intensity
    of the real model and the comparison of each end use between the reference and real models."""
    fce = redcep.PRIMARY_ENERGY_FACTOR_BRAZIL
    real, ref = results["real_model"], results["reference_model"]
    real_area = real.get("total_area") or 0
    ref_area = ref.get("total_area") or real_area
    if not real_area or not ref_area:
        return False
    unit = t("kWh/m².ano")
    annual_unit = t("kWh/ano")
    components = [("Refrigeração", "cr", "#4FC3F7"), ("Aquecimento", "cae", "#EF5350"),
                  ("Iluminação", "cil", "#FFD54F"), ("Equipamentos", "ceq", "#FF8A65")]
    rows = []
    for label, key, color in components:
        real_eui = real[key] * fce / real_area
        ref_eui = ref[key] * fce / ref_area
        if key == "cae" and real_eui == 0 and ref_eui == 0:
            continue
        rows.append((t(label), ref_eui, real_eui, color, ref[key] * fce, real[key] * fce))
    ref_total = sum(row[1] for row in rows)
    real_total = sum(row[2] for row in rows)
    ref_annual = sum(row[4] for row in rows)
    real_annual = sum(row[5] for row in rows)

    def kwh(value):
        return f"{value:,.0f}".replace(",", " ")

    def both_units(per_area, annual):
        return (f"{per_area:.2f}<div style='font-size:0.75rem;color:#7f8c8d;font-weight:400'>"
                f"{kwh(annual)} {annual_unit}</div>")

    scale = ""
    for index, letter in enumerate(CLASS_COLORS):
        selected = letter == general_class
        text_color = "#000000" if letter in ("B", "C", "D") else "#FFFFFF"
        scale += (f"<div style='display:flex;align-items:center;margin:7px 0;opacity:{1 if selected else 0.35}'>"
                  f"<div style='background:{CLASS_COLORS[letter]};color:{text_color};font-weight:700;font-size:1.5rem;"
                  f"height:42px;line-height:42px;width:{95 + 28 * index}px;padding-left:14px;box-sizing:border-box;"
                  f"clip-path:polygon(0 0,calc(100% - 21px) 0,100% 50%,calc(100% - 21px) 100%,0 100%)'>{letter}</div>"
                  + ("<div style='margin-left:10px;font-size:1.4rem;color:#2c3e50'>&#9664;</div>" if selected else "")
                  + "</div>")

    bars = ""
    for label, _, real_eui, color, _, _ in rows:
        share = 100 * real_eui / real_total if real_total else 0
        bars += (f"<div style='margin:10px 0 4px;display:flex;justify-content:space-between;font-size:0.8rem'>"
                 f"<span style='font-weight:700;text-transform:uppercase'>{label} &middot; {share:.1f} %</span>"
                 f"<span style='color:#7f8c8d'>{real_eui:.2f} {unit}</span></div>"
                 f"<div style='background:#e9ecef;height:16px'><div style='background:{color};height:16px;width:{share:.1f}%'></div></div>")

    general_color = CLASS_COLORS.get(general_class, "#BDBDBD")
    general_text = "#000000" if general_class in ("B", "C", "D") else "#FFFFFF"
    header_cell = "padding:10px 12px;background:#34495e;color:#ffffff;text-align:center;font-weight:600"
    cell = "padding:9px 12px;text-align:center;border-bottom:1px solid #e0e0e0"
    table_rows = ""
    for position, (label, ref_eui, real_eui, _, ref_kwh, real_kwh) in enumerate(rows):
        background = "#f4f6f8" if position % 2 else "#ffffff"
        table_rows += (f"<tr style='background:{background}'><td style='{cell}'>{label}</td><td style='{cell}'>{both_units(ref_eui, ref_kwh)}</td>"
                       f"<td style='{cell}'>{both_units(real_eui, real_kwh)}</td><td style='{cell}'>{_difference_html(ref_eui, real_eui)}</td></tr>")
    table_rows += (f"<tr style='background:#e8f5e9;font-weight:700'><td style='{cell}'>{t('Total')}</td>"
                   f"<td style='{cell}'>{both_units(ref_total, ref_annual)}</td><td style='{cell}'>{both_units(real_total, real_annual)}</td>"
                   f"<td style='{cell}'>{_difference_html(ref_total, real_total)}</td></tr>")
    table_rows += (f"<tr style='background:#fff8e1;font-weight:700'><td style='{cell}'>RedCEP</td><td style='{cell}'>-</td>"
                   f"<td style='{cell}'>{results['redcep']:.2f} %</td>"
                   f"<td style='{cell};font-weight:400'>{t('Eq. 8.1, sem equipamentos na base')}</td></tr>")

    st.markdown(
        f"<div style='background:#ffffff;color:#2c3e50;border:1px solid #d0d7de;max-width:980px;margin:0 auto 1rem'>"
        f"<div style='background:#2c3e50;color:#ffffff;text-align:center;padding:18px 12px'>"
        f"<div style='font-size:1.35rem;font-weight:700;letter-spacing:0.04em;text-transform:uppercase'>{t('Etiqueta de eficiência energética')}</div>"
        f"<div style='font-size:0.9rem;margin-top:6px'>{t('Edificações comerciais, de serviços e públicas')}</div>"
        f"<div style='font-size:0.75rem;margin-top:6px;opacity:0.75'>{t('Método de simulação da INI-C. Portaria Inmetro 309/2022, Anexo C.I.')}</div></div>"
        f"<div style='display:flex;flex-wrap:wrap;gap:24px;padding:22px'>"
        f"<div style='flex:1 1 260px;display:flex;flex-direction:column;justify-content:center'>{scale}</div>"
        f"<div style='flex:1 1 300px'>"
        f"<div style='background:#f4f6f8;padding:16px;text-align:center'>"
        f"<div style='font-size:0.8rem;font-weight:700;text-transform:uppercase;color:#5d6d7e'>{t('Classificação geral')}</div>"
        f"<div style='display:inline-block;background:{general_color};color:{general_text};font-size:4rem;font-weight:700;"
        f"width:6rem;height:6rem;line-height:6rem;margin:10px 0'>{general_class}</div>"
        f"<div style='background:#e8f5e9;padding:8px;margin:0 auto;max-width:200px'><div style='font-size:0.7rem;color:#5d6d7e'>RedCEP</div>"
        f"<div style='font-size:1.5rem;font-weight:700'>{results['redcep']:.2f} %</div></div></div>"
        f"<div style='background:#f4f6f8;padding:12px 16px;margin-top:14px'>"
        f"<div style='text-align:center;font-size:0.8rem;font-weight:700;text-transform:uppercase;color:#5d6d7e'>"
        f"{t('Intensidade de uso de energia primária do modelo real')}</div>{bars}</div>"
        f"<div style='background:#2e64b5;color:#ffffff;text-align:center;padding:12px;margin-top:14px;font-weight:700'>"
        f"{t('Total')}: {real_total:.2f} {unit}<div style='font-size:0.8rem;font-weight:400;margin-top:2px'>"
        f"{kwh(real_annual)} {annual_unit}</div></div></div></div>"
        f"<div style='padding:0 22px 22px;overflow-x:auto'><table style='width:100%;border-collapse:collapse;font-size:0.9rem'>"
        f"<tr><th style='{header_cell}'>{t('Uso final ({unit})', unit=unit)}</th><th style='{header_cell}'>{t('Modelo de referência')}</th>"
        f"<th style='{header_cell}'>{t('Modelo real')}</th><th style='{header_cell}'>{t('Diferença')}</th></tr>{table_rows}</table></div></div>",
        unsafe_allow_html=True,
    )
    return True


def class_badge(label, value, size="large"):
    color = CLASS_COLORS.get(value, "#BDBDBD")
    text_color = "#000000" if value in ("C", "D", "B") else "#FFFFFF"
    box, font, label_size = ("7rem", "4.5rem", "1.1rem") if size == "large" else ("3.2rem", "1.9rem", "0.85rem")
    st.markdown(
        f"<div style='text-align:center'><div style='font-size:{label_size};font-weight:600;margin-bottom:0.3rem'>{label}</div>"
        f"<div style='display:inline-block;background:{color};color:{text_color};font-size:{font};font-weight:700;"
        f"width:{box};height:{box};line-height:{box};border-radius:0.5rem'>{value}</div></div>",
        unsafe_allow_html=True,
    )


def new_work_dir(previous=None):
    """Creates the folder of a new upload, removing the previous folder of this session and folders left by old sessions."""
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    if previous:
        shutil.rmtree(previous, ignore_errors=True)
    limit = datetime.now() - timedelta(hours=WORK_DIR_MAX_AGE_HOURS)
    for folder in WORK_ROOT.iterdir():
        try:
            created = datetime.strptime(folder.name[:15], "%Y%m%d_%H%M%S")
        except ValueError:
            continue
        if created < limit:
            shutil.rmtree(folder, ignore_errors=True)
    # Unique name, so two uploads in the same second do not share a folder.
    return Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y%m%d_%H%M%S_"), dir=WORK_ROOT))


def clear_outputs(work_dir):
    for name in ("real", "referencia", "simulacao_real", "simulacao_referencia"):
        shutil.rmtree(work_dir / name, ignore_errors=True)


def remove_large_leftovers(work_dir):
    """Deletes the intermediate models and the simulation files that the results and downloads do not use."""
    for pattern in ("real/real_step*.osm", "referencia/ref_step*.osm"):
        for file in work_dir.glob(pattern):
            file.unlink(missing_ok=True)
    for folder in ("simulacao_real", "simulacao_referencia"):
        shutil.rmtree(work_dir / folder / "reports", ignore_errors=True)
        for name in SIMULATION_LEFTOVERS:
            (work_dir / folder / "run" / name).unlink(missing_ok=True)


def zip_folder(folder):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in folder.rglob("*"):
            if file.is_file() and file.suffix.lower() in (".osm", ".idf", ".csv", ".htm", ".err", ".xml", ".log", ".osw"):
                archive.write(file, file.relative_to(folder))
    return buffer.getvalue()


def language_switch():
    st.session_state.setdefault("lang", "pt")
    label = "English" if st.session_state["lang"] == "pt" else "Português"
    if st.button(label, key="language_button", help="Traduzir a página / Translate the page"):
        st.session_state["lang"] = "en" if st.session_state["lang"] == "pt" else "pt"
        st.rerun()


def main():
    st.set_page_config(page_title="INI-C gbXML", layout="wide")
    st.session_state.setdefault("lang", "pt")
    col_title, col_lang = st.columns([6, 1])
    with col_lang:
        language_switch()
    with col_title:
        st.title(t("Classificação INI-C pelo método de simulação"))
    st.caption(t("Tipologia educacional. Portaria Inmetro 309/2022, Anexo C.I."))

    with st.sidebar:
        st.header(t("Parâmetros"))
        bioclimatic_zone = st.selectbox(t("Zona bioclimática (ABNT NBR 15220-3)"), coefficients.BIOCLIMATIC_ZONES, index=2, key="zone")
        education_options = list(EDUCATION_LEVELS.keys())
        education_level = st.selectbox(t("Nível de ensino (Tabela A.2)"), education_options, format_func=t,
                                       index=education_options.index(st.session_state.get("education", education_options[0])),
                                       key=f"education_{st.session_state['lang']}")
        st.session_state["education"] = education_level
        area_per_person = EDUCATION_LEVELS[education_level]
        ceer_real = st.number_input(t("CEER do sistema de condicionamento de ar do projeto (W/W)"), min_value=0.5, max_value=15.0,
                                    value=None, step=0.01, key="ceer",
                                    help=t("Somente sistemas unitários (janela, split). CEER ponderado pela capacidade de refrigeração, "
                                           "Equação B.II.5: equipamentos inverter usam o IDRS da etiqueta Inmetro (corrigido pela "
                                           "Tabela B.II.1 nas zonas 2R, 4A, 4B, 5B e 6B) e equipamentos de rotação fixa usam 1,062 x CEE."))
        st.caption(t("Este campo vale apenas para sistemas unitários. Sistemas centrais (por exemplo, com resfriadores de líquido) "
                     "têm o CEER calculado pelo SPLV ou pelo fator K (item B.II.4.2), que não é tratado por esta ferramenta."))
        heating = st.checkbox(t("O projeto possui sistema de aquecimento"), value=False, key="heating",
                              help=t("Item C.I.6: a carga de aquecimento (setpoint 21 °C) só é calculada quando há aquecimento em projeto."))
        ceea_real = None
        if heating and ceer_real:
            ceea_real = st.number_input(t("CEEA do sistema de aquecimento do projeto (W/W)"), min_value=0.5, max_value=15.0,
                                        value=round(1.72 + 0.5 * ceer_real, 2), step=0.01, key=f"ceea_{ceer_real}",
                                        help=t("Equação C.I.8: para split e janela, 1,72 + 0,5 x CEER, ou dado do fabricante."))
        with st.expander(t("Opções avançadas")):
            st.caption(t("Renovação de ar nas APPs, aplicada igualmente aos modelos real e de referência. Os valores iniciais são "
                         "os da ABNT NBR 16401-3, Tabela 1, sala de aula, nível 1."))
            oa_person = st.number_input(t("Fp, vazão por pessoa (L/s.pessoa)"), min_value=0.0, value=5.0, step=0.1, key="oa_person")
            oa_area = st.number_input(t("Fa, vazão por área (L/s.m²)"), min_value=0.0, value=0.6, step=0.1, key="oa_area")
        st.subheader(t("Motor de simulação"))
        cli_default = find_openstudio_cli()
        if cli_default or platform.system() != "Linux":
            engine = "cli"
            executable = st.text_input(t("Caminho do openstudio.exe"), value=cli_default, key="cli_path")
            if executable:
                version = cli_version(executable)
                python_version = openstudio.openStudioVersion()
                if not version:
                    st.error(t("Não foi possível executar o OpenStudio nesse caminho."))
                elif not version.startswith(python_version):
                    st.warning(t("Versões diferentes: CLI {cli}, Python {python}. Use a mesma versão nos dois.",
                                 cli=version, python=python_version))
                else:
                    st.success(f"OpenStudio {version}")
        else:
            engine = "energyplus"
            executable = energyplus_runner.find_energyplus()
            if executable:
                st.success(t("EnergyPlus {version} pronto.", version=energyplus_runner.ENERGYPLUS_VERSION))
            else:
                st.info(t("EnergyPlus {version} será baixado na primeira simulação (cerca de 190 MB, uma única vez).",
                          version=energyplus_runner.ENERGYPLUS_VERSION))

    st.header(t("1. Arquivos de entrada"))
    col_gbxml, col_epw = st.columns(2)
    gbxml_file = col_gbxml.file_uploader(t("Arquivo gbXML exportado do Revit"), type=["xml", "gbxml"], key="gbxml_file")
    epw_file = col_epw.file_uploader(t("Arquivo climático (.epw)"), type=["epw"], key="epw_file")

    if gbxml_file is None:
        st.info(t("Envie o arquivo gbXML para começar."))
        st.stop()

    if st.session_state.get("gbxml_name") != gbxml_file.name or "work_dir" not in st.session_state:
        work_dir = new_work_dir(st.session_state.get("work_dir"))
        gbxml_path = work_dir / "entrada.xml"
        gbxml_path.write_bytes(gbxml_file.getvalue())
        for key in ("real_osm", "ref_osm", "geometry", "results", "log", "missing_enclosure"):
            st.session_state.pop(key, None)
        st.session_state.update({"gbxml_name": gbxml_file.name, "work_dir": work_dir, "gbxml_path": gbxml_path})

    work_dir = st.session_state["work_dir"]
    gbxml_path = st.session_state["gbxml_path"]
    spaces = inspect_gbxml(gbxml_path)

    with st.expander(t("Espaços do gbXML ({count})", count=len(spaces)), expanded=False):
        st.dataframe(pd.DataFrame({
            t("Espaço"): spaces["name"],
            "spaceType": spaces["space_type"],
            t("Classificação"): [label if label else t("Sem classificação") for label in spaces["label"]],
            t("DPI gbXML (W/m²)"): spaces["lpd"],
        }), width="stretch", hide_index=True)
    unclassified = spaces[spaces["label"].isna() | (spaces["label"] == "")]
    if not unclassified.empty:
        st.warning(t("{count} espaço(s) com spaceType fora do dicionário APP/APT (spacetype_utils.py). "
                     "Eles recebem pessoas e equipamentos como APP, mas não recebem sistema de condicionamento. Revise no Revit.",
                     count=len(unclassified)))

    st.header(t("2. Iluminação"))
    has_lighting = (spaces["lpd"] > 0).any()
    if has_lighting:
        lighting_mode, dpi_value, lighting_app_only = "gbxml", None, False
        st.success(t("DPI de projeto encontrada no gbXML. Sistema de iluminação avaliado: modelo real com a DPI do gbXML, "
                     "referência com {dpi} W/m² nos ambientes com iluminação (item C.I.4).", dpi=REFERENCE_DPI))
    else:
        st.warning(t("O gbXML não tem densidade de potência de iluminação (LightPowerPerArea). Escolha como seguir:"))
        lighting_options = {
            "project": "Informar a DPI de projeto (sistema de iluminação avaliado)",
            "reference": "Não avaliar o sistema de iluminação (DPI de referência {dpi} W/m² só nas APPs, nos dois modelos)",
        }
        lighting_keys = list(lighting_options.keys())
        stored_choice = st.session_state.get("lighting_choice")
        choice = st.radio(t("Iluminação"), lighting_keys, key=f"lighting_choice_{st.session_state['lang']}",
                          index=lighting_keys.index(stored_choice) if stored_choice in lighting_keys else None,
                          format_func=lambda key: t(lighting_options[key], dpi=REFERENCE_DPI))
        st.session_state["lighting_choice"] = choice
        if choice is None:
            st.stop()
        if choice == "project":
            dpi_value = st.number_input(t("DPI de projeto (W/m²)"), min_value=0.1, value=None, step=0.1, key="dpi_value")
            if dpi_value is None:
                st.stop()
            lighting_mode, lighting_app_only = "project", False
        else:
            lighting_mode, dpi_value, lighting_app_only = "reference", None, True

    st.header(t("3. Processamento"))
    if ceer_real is None:
        st.info(t("Informe o CEER do sistema de projeto na barra lateral."))
        st.stop()
    if epw_file is None:
        st.info(t("Envie o arquivo climático (.epw) para simular."))
        st.stop()
    if engine == "cli" and not executable:
        st.error(t("Informe o caminho do openstudio.exe na barra lateral."))
        st.stop()

    if st.button(t("Gerar os modelos, simular e classificar"), type="primary", key="run_all"):
        for key in ("real_osm", "ref_osm", "geometry", "results", "missing_enclosure"):
            st.session_state.pop(key, None)
        clear_outputs(work_dir)
        st.session_state["log"] = []
        with st.spinner(t("Processando etapas 00 a 10...")):
            real_osm = build_real_model(gbxml_path, work_dir, area_per_person, lighting_mode, dpi_value,
                                        oa_person / 1000.0, oa_area / 1000.0, heating)
        st.session_state["real_osm"] = real_osm
        st.session_state["geometry"] = model_geometry(real_osm)
        st.session_state["missing_enclosure"] = spaces_missing_enclosure(real_osm)
        if not st.session_state["missing_enclosure"]:
            run_reference_and_simulation(work_dir, epw_file, engine, executable, lighting_app_only, lighting_mode,
                                         ceer_real, ceea_real, bioclimatic_zone)

    if "real_osm" not in st.session_state:
        st.stop()

    with st.expander(t("Registro das etapas")):
        st.code("\n\n".join(st.session_state.get("log", [])))

    st.header(t("4. Geometria do modelo real"))
    st.plotly_chart(geometry_figure(st.session_state["geometry"]), width="stretch")
    st.caption(t("Arraste para girar, role para aproximar e passe o mouse para ver o elemento. Clique em um item da legenda "
                 "para esconder ou mostrar esse elemento. No modelo de referência, os sombreamentos de fachada (brises, "
                 "beirais, marquises) são retirados automaticamente e o entorno é mantido (item C.I.4)."))

    missing_enclosure = st.session_state.get("missing_enclosure", [])
    if missing_enclosure:
        part_names = {"floor": t("piso"), "roof": t("cobertura ou forro")}
        listing = "\n".join(f"- {name}: {', '.join(part_names[part] for part in parts)}" for name, parts in missing_enclosure)
        st.error(t("O modelo não está fechado. Estes espaços estão sem piso e/ou sem cobertura:") + "\n\n" + listing + "\n\n" +
                 t("No gbXML, essas faces vieram como superfícies do ambiente com ele mesmo (InteriorFloor ou Air), que o "
                   "OpenStudio descarta. No Revit, desenhe o piso e a laje de cobertura ou o telhado com a opção Delimitação "
                   "de ambiente marcada, faça o limite superior dos ambientes chegar até eles e exporte o gbXML de novo. Se o "
                   "telhado aparece no modelo 3D como sombreamento, é sinal de que ele não está delimitando os ambientes."))
        st.stop()

    if "results" not in st.session_state:
        st.stop()

    st.header(t("5. Classificação"))
    results = st.session_state["results"]
    coef = results["coefficients"]
    general_class = coefficients.calculate_class(results["redcep"], coef["factor_i"])
    envelope_class = coefficients.calculate_class(results["redcgtt"], coef["factor_i_envelope"])
    air_conditioning_class = coefficients.calculate_class(results["redcr"], coef["factor_i_air_conditioning"])
    lighting_evaluated = results.get("lighting_evaluated", True)
    lighting_class = coefficients.calculate_class(results["redcil"], coef["factor_i_lighting"]) if lighting_evaluated else "-"

    def limits_text(i):
        return t("A > {a} %, B > {b} %, C > {c} %, D de 0 a {c} %, E < 0 %", a=f"{3 * i:.1f}", b=f"{2 * i:.1f}", c=f"{i:.1f}")

    if not energy_label(results, general_class):
        class_badge(t("Classificação geral"), general_class, "large")
        st.markdown(f"<div style='text-align:center;font-size:1.6rem;font-weight:600;margin-top:0.4rem'>RedCEP {results['redcep']:.1f} %</div>",
                    unsafe_allow_html=True)
    st.caption(t("Eq. 8.1, Tabela 8.2. CRCEPD-A = {crc:.2f}, i = {i:.2f} %. Limites: {limits}.",
                 crc=coef["crcepd_a"], i=coef["factor_i"], limits=limits_text(coef["factor_i"])) + " " +
               t("Valores em energia primária (fcE = {fce}) por área total construída ({area} m²). A diferença do total inclui os "
                 "equipamentos; o RedCEP os desconta da base (Eq. 8.1).", fce=redcep.PRIMARY_ENERGY_FACTOR_BRAZIL,
                 area=f"{results['real_model'].get('total_area') or 0:.0f}"))
    with st.container():
        st.markdown(f"**{t('Classificações parciais dos sistemas')}**")
        partial = [
            (t("Envoltória"), envelope_class, f"RedCgTT {results['redcgtt']:.1f} %",
             t("Eq. C.I.10, Tabela 8.4. CRCgTTD-A = {crc:.2f}, i = {i:.2f} %.", crc=coef["crcgtt_d_a"], i=coef["factor_i_envelope"])),
            (t("Condicionamento de ar"), air_conditioning_class, f"RedCR {results['redcr']:.1f} %",
             t("Eq. B.II.1, Tabela 8.6. CRCRD-A = {crc:.2f}, i = {i:.2f} %.", crc=coef["crcr_d_a"], i=coef["factor_i_air_conditioning"])),
            (t("Iluminação"), lighting_class, f"RedCIL {results['redcil']:.1f} %" if lighting_evaluated else t("Não avaliado"),
             t("Eq. B.III.1, Tabela 8.8. DPIL A = 7,5 e D = 15,5 W/m² (Tabela B.III.2), i = {i:.2f} %.", i=coef["factor_i_lighting"])
             if lighting_evaluated else t("O gbXML não tem DPI de projeto e o sistema de iluminação não foi avaliado.")),
        ]
        for column, (label, value, reduction, note) in zip(st.columns(3), partial):
            with column:
                class_badge(label, value, "small")
                st.markdown(f"<div style='text-align:center;font-size:1rem;margin-top:0.3rem'>{reduction}</div>", unsafe_allow_html=True)
                st.caption(note)

    rows = [
        ("Carga térmica de refrigeração CgTR", "cgtr"),
        ("Carga térmica de aquecimento CgTA", "cgta"),
        ("Consumo de refrigeração CR", "cr"),
        ("Consumo de aquecimento CAE", "cae"),
        ("Consumo de iluminação CIL", "cil"),
        ("Consumo de equipamentos CEQ", "ceq"),
        ("Consumo de energia elétrica CEE", "cee"),
        ("Consumo de energia primária CEP", "cep"),
    ]
    indicator_column = t("Indicador")
    real_area = results["real_model"].get("total_area") or 0
    ref_area = results["reference_model"].get("total_area") or real_area
    table = pd.DataFrame({
        indicator_column: [t(label) for label, _ in rows],
        t("Modelo real (kWh/ano)"): [round(results["real_model"][key], 1) for _, key in rows],
        t("Modelo real (kWh/m².ano)"): [round(results["real_model"][key] / real_area, 2) if real_area else None for _, key in rows],
        t("Modelo de referência (kWh/ano)"): [round(results["reference_model"][key], 1) for _, key in rows],
        t("Modelo de referência (kWh/m².ano)"): [round(results["reference_model"][key] / ref_area, 2) if ref_area else None for _, key in rows],
    })
    st.dataframe(table, width="stretch", hide_index=True)
    st.caption(t("CEER real {ceer:.2f}, CEER referência {ceer_ref}. Iluminação e equipamentos ajustados para {days} dias "
                 "(simulados: {simulated}). Fator de energia primária fcE = {fce}. "
                 "O RedCEP desconta o consumo de equipamentos dos dois modelos (Eq. 8.1).",
                 ceer=results["real_model"]["ceer"], ceer_ref=CEER_REFERENCE, days=redcep.OCCUPATION_DAYS_LIGHTING_EQUIPMENT,
                 simulated=results["real_model"]["simulated_days"], fce=redcep.PRIMARY_ENERGY_FACTOR_BRAZIL))

    st.header(t("6. Arquivos"))
    files_section = st.expander(t("Mostrar arquivos"), expanded=False)
    indicator, value = t("Indicador"), t("Valor")
    summary = pd.DataFrame([
        {indicator: t("Zona bioclimática"), value: coef["bioclimatic_zone"]},
        {indicator: "RedCEP (%)", value: round(results["redcep"], 2)},
        {indicator: t("Classificação geral"), value: general_class},
        {indicator: "RedCgTT (%)", value: round(results["redcgtt"], 2)},
        {indicator: t("Classificação da envoltória"), value: envelope_class},
        {indicator: "RedCR (%)", value: round(results["redcr"], 2)},
        {indicator: t("Classificação do condicionamento de ar"), value: air_conditioning_class},
        {indicator: "RedCIL (%)", value: round(results["redcil"], 2) if lighting_evaluated else "-"},
        {indicator: t("Classificação da iluminação"), value: lighting_class},
    ])
    with files_section:
        d1, d2, d3, d4 = st.columns(4)
        d1.download_button(t("Modelo real (.osm)"), Path(st.session_state["real_osm"]).read_bytes(), file_name="modelo_real.osm")
        d2.download_button(t("Modelo de referência (.osm)"), Path(st.session_state["ref_osm"]).read_bytes(), file_name="modelo_referencia.osm")
        d3.download_button(t("Resultados (.csv)"),
                           pd.concat([summary, table.rename(columns={indicator_column: indicator})]).to_csv(index=False).encode("utf-8-sig"),
                           file_name="resultados_inic.csv")
        d4.download_button(t("Tudo (.zip)"), zip_folder(work_dir), file_name="inic_gbxml_completo.zip")

        e1, e2 = st.columns(2)
        for column, name, folder in ((e1, t("Simulação real"), "simulacao_real"), (e2, t("Simulação de referência"), "simulacao_referencia")):
            run_dir = work_dir / folder / "run"
            with column:
                st.subheader(name)
                for file_name in ("in.idf", "eplusout.csv", "eplustbl.htm", "eplusout.err"):
                    file_path = run_dir / file_name
                    if file_path.exists():
                        st.download_button(file_name, file_path.read_bytes(), file_name=f"{folder}_{file_name}", key=f"{folder}_{file_name}")


if __name__ == "__main__":
    main()
