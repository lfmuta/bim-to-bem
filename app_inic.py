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
from datetime import datetime
from pathlib import Path

import openstudio
import pandas as pd
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
EDUCATION_LEVELS = {
    "Ensino fundamental e médio (1,5 m²/pessoa)": 1.5,
    "Ensino superior (1,5 m²/pessoa)": 1.5,
    "Educação infantil (2,5 m²/pessoa)": 2.5,
}
CLASS_COLORS = {"A": "#00A651", "B": "#8CC63F", "C": "#FFF200", "D": "#FF9E1B", "E": "#ED1C24"}


def run_step(label, function, *args, **kwargs):
    """Runs one processing step capturing its console output. Stops the app when the step fails."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        try:
            result = function(*args, **kwargs)
        except Exception as error:
            result = False
            print(f"Erro: {error}")
    output = buffer.getvalue().strip()
    st.session_state.setdefault("log", []).append(f"[{label}]\n{output}" if output else f"[{label}]")
    if result is False or result is None:
        st.error(f"Falha na etapa: {label}")
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
        label = spacetype_utils.get_space_type_label_by_name(space_type) or "Sem classificação"
        rows.append({"Espaço": name, "spaceType": space_type, "Classificação": label, "DPI gbXML (W/m²)": lpd})
    return pd.DataFrame(rows)


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


def shading_table(osm_path):
    model = openstudio.model.Model.load(openstudio.path(str(osm_path))).get()
    remover = shade_remover.ShadingSurfaceRemover(log_path=str(Path(tempfile.gettempdir()) / "shading_inspection.log"))
    remover.model = model
    rows = []
    for surface in model.getShadingSurfaces():
        group_opt = surface.shadingSurfaceGroup()
        rows.append({
            "Nome": surface.nameString(),
            "Grupo": group_opt.get().shadingSurfaceType() if group_opt.is_initialized() else "",
            "Área (m²)": round(surface.grossArea(), 2),
            "Remover na referência": remover.is_facade_device(surface),
        })
    return pd.DataFrame(rows)


def build_reference_model(real_osm, work_dir, shading_to_remove, lighting_app_only):
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
    remover = shade_remover.ShadingSurfaceRemover(log_path=str(base / "shading_removal.log"), names_to_remove=shading_to_remove)
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


def run_simulations(engine, executable, jobs, epw_path):
    """Runs both models in parallel, with the OpenStudio CLI (jobs are OSW files) or directly in EnergyPlus (jobs are IDF files)."""
    if engine == "cli":
        processes = {name: subprocess.Popen([executable, "run", "-w", str(job)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for name, job in jobs.items()}
    else:
        processes = {name: energyplus_runner.start_simulation(executable, job, epw_path, Path(job).parent)
                     for name, job in jobs.items()}
    results = {}
    for name, process in processes.items():
        stdout, stderr = process.communicate()
        results[name] = (process.returncode, stdout, stderr)
    return results


def class_badge(label, value):
    color = CLASS_COLORS.get(value, "#999999")
    text_color = "#000000" if value in ("C", "D", "B") else "#FFFFFF"
    st.markdown(
        f"<div style='text-align:center'><div style='font-size:0.9rem'>{label}</div>"
        f"<div style='display:inline-block;background:{color};color:{text_color};font-size:3rem;font-weight:700;"
        f"width:5rem;height:5rem;line-height:5rem;border-radius:0.5rem'>{value}</div></div>",
        unsafe_allow_html=True,
    )


def zip_folder(folder):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in folder.rglob("*"):
            if file.is_file() and file.suffix.lower() in (".osm", ".idf", ".csv", ".htm", ".err", ".xml", ".log", ".osw"):
                archive.write(file, file.relative_to(folder))
    return buffer.getvalue()


def main():
    st.set_page_config(page_title="Classificação INI-C via gbXML", layout="wide")
    st.title("Classificação INI-C pelo método de simulação")
    st.caption("Tipologia educacional. Portaria Inmetro 309/2022, Anexo C.I.")

    with st.sidebar:
        st.header("Parâmetros")
        bioclimatic_zone = st.selectbox("Zona bioclimática (ABNT NBR 15220-3)", coefficients.BIOCLIMATIC_ZONES, index=2)
        education_level = st.selectbox("Nível de ensino (Tabela A.2)", list(EDUCATION_LEVELS.keys()))
        area_per_person = EDUCATION_LEVELS[education_level]
        ceer_real = st.number_input("CEER do sistema de condicionamento de ar do projeto (W/W)", min_value=0.5, max_value=15.0, value=None,
                                    step=0.01, help="Anexo B.II. Valor do sistema real, por exemplo da etiqueta Inmetro.")
        heating = st.checkbox("O projeto possui sistema de aquecimento", value=False,
                              help="Item C.I.6: a carga de aquecimento (setpoint 21 °C) só é calculada quando há aquecimento em projeto.")
        ceea_real = None
        if heating and ceer_real:
            ceea_real = st.number_input("CEEA do sistema de aquecimento do projeto (W/W)", min_value=0.5, max_value=15.0,
                                        value=round(1.72 + 0.5 * ceer_real, 2), step=0.01,
                                        help="Equação C.I.8: para split e janela, 1,72 + 0,5 x CEER, ou dado do fabricante.")
        st.subheader("Renovação de ar (APP)")
        oa_person = st.number_input("Vazão por pessoa (L/s)", min_value=0.0, value=7.5, step=0.5,
                                    help="Conferir na ABNT NBR 16401 e NBR 17037 vigentes.")
        oa_area = st.number_input("Vazão por área (L/s.m²)", min_value=0.0, value=0.0, step=0.1)
        st.subheader("Motor de simulação")
        cli_default = find_openstudio_cli()
        if cli_default or platform.system() != "Linux":
            engine = "cli"
            executable = st.text_input("Caminho do openstudio.exe", value=cli_default)
            if executable:
                version = cli_version(executable)
                python_version = openstudio.openStudioVersion()
                if not version:
                    st.error("Não foi possível executar o OpenStudio nesse caminho.")
                elif not version.startswith(python_version):
                    st.warning(f"Versões diferentes: CLI {version}, Python {python_version}. Use a mesma versão nos dois.")
                else:
                    st.success(f"OpenStudio {version}")
        else:
            engine = "energyplus"
            executable = energyplus_runner.find_energyplus()
            if executable:
                st.success(f"EnergyPlus {energyplus_runner.ENERGYPLUS_VERSION} pronto.")
            else:
                st.info(f"EnergyPlus {energyplus_runner.ENERGYPLUS_VERSION} será baixado na primeira simulação (cerca de 190 MB, uma única vez).")

    st.header("1. Arquivos de entrada")
    col_gbxml, col_epw = st.columns(2)
    gbxml_file = col_gbxml.file_uploader("Arquivo gbXML exportado do Revit", type=["xml", "gbxml"])
    epw_file = col_epw.file_uploader("Arquivo climático (.epw)", type=["epw"])

    if gbxml_file is None:
        st.info("Envie o arquivo gbXML para começar.")
        st.stop()

    if st.session_state.get("gbxml_name") != gbxml_file.name or "work_dir" not in st.session_state:
        work_dir = Path(tempfile.gettempdir()) / "inic_gbxml" / datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir.mkdir(parents=True, exist_ok=True)
        gbxml_path = work_dir / "entrada.xml"
        gbxml_path.write_bytes(gbxml_file.getvalue())
        st.session_state.clear()
        st.session_state.update({"gbxml_name": gbxml_file.name, "work_dir": work_dir, "gbxml_path": gbxml_path})

    work_dir = st.session_state["work_dir"]
    gbxml_path = st.session_state["gbxml_path"]
    spaces = inspect_gbxml(gbxml_path)

    with st.expander(f"Espaços do gbXML ({len(spaces)})", expanded=False):
        st.dataframe(spaces, use_container_width=True, hide_index=True)
    unclassified = spaces[spaces["Classificação"] == "Sem classificação"]
    if not unclassified.empty:
        st.warning(f"{len(unclassified)} espaço(s) com spaceType fora do dicionário APP/APT (spacetype_utils.py). "
                   "Eles recebem pessoas e equipamentos como APP, mas não recebem sistema de condicionamento. Revise no Revit.")

    st.header("2. Iluminação")
    has_lighting = (spaces["DPI gbXML (W/m²)"] > 0).any()
    if has_lighting:
        lighting_mode, dpi_value, lighting_app_only = "gbxml", None, False
        st.success("DPI de projeto encontrada no gbXML. Sistema de iluminação avaliado: modelo real com a DPI do gbXML, "
                   f"referência com {REFERENCE_DPI} W/m² nos ambientes com iluminação (item C.I.4).")
    else:
        st.warning("O gbXML não tem densidade de potência de iluminação (LightPowerPerArea). Escolha como seguir:")
        choice = st.radio("Iluminação", [
            "Informar a DPI de projeto (sistema de iluminação avaliado)",
            f"Não avaliar o sistema de iluminação (DPI de referência {REFERENCE_DPI} W/m² só nas APPs, nos dois modelos)",
        ], index=None)
        if choice is None:
            st.stop()
        if choice.startswith("Informar"):
            dpi_value = st.number_input("DPI de projeto (W/m²)", min_value=0.1, value=None, step=0.1)
            if dpi_value is None:
                st.stop()
            lighting_mode, lighting_app_only = "project", False
        else:
            lighting_mode, dpi_value, lighting_app_only = "reference", None, True

    st.header("3. Modelo real")
    if ceer_real is None:
        st.info("Informe o CEER do sistema de projeto na barra lateral.")
        st.stop()

    if st.button("Processar gbXML e gerar o modelo real", type="primary"):
        st.session_state["log"] = []
        with st.spinner("Processando etapas 00 a 10..."):
            real_osm = build_real_model(gbxml_path, work_dir, area_per_person, lighting_mode, dpi_value,
                                        oa_person / 1000.0, oa_area / 1000.0, heating)
        st.session_state["real_osm"] = real_osm
        st.session_state["shading"] = shading_table(real_osm)
        st.session_state.pop("results", None)

    if "real_osm" not in st.session_state:
        st.stop()

    st.success("Modelo real gerado.")
    with st.expander("Registro das etapas"):
        st.code("\n\n".join(st.session_state.get("log", [])))

    st.header("4. Sombreamento na referência")
    shading = st.session_state["shading"]
    if shading.empty:
        st.write("O modelo não tem superfícies de sombreamento.")
        shading_to_remove = []
    else:
        st.write("Na referência, saem só os elementos fixos de fachada (brises, venezianas, beirais, sacadas). "
                 "Entorno, circulações externas e elementos na cobertura ficam nos dois modelos (item C.I.4). "
                 "A seleção abaixo é uma sugestão: revise antes de simular.")
        edited = st.data_editor(shading, use_container_width=True, hide_index=True, disabled=["Nome", "Grupo", "Área (m²)"])
        shading_to_remove = edited.loc[edited["Remover na referência"], "Nome"].tolist()

    st.header("5. Simulação e classificação")
    if epw_file is None:
        st.info("Envie o arquivo climático (.epw) para simular.")
        st.stop()
    if engine == "cli" and not executable:
        st.error("Informe o caminho do openstudio.exe na barra lateral.")
        st.stop()

    if st.button("Gerar referência, simular e classificar", type="primary"):
        epw_path = work_dir / "clima.epw"
        epw_path.write_bytes(epw_file.getvalue())
        with st.spinner("Gerando o modelo de referência..."):
            ref_osm = build_reference_model(st.session_state["real_osm"], work_dir, shading_to_remove, lighting_app_only)
        if engine == "energyplus" and not executable:
            with st.spinner("Baixando o EnergyPlus (só na primeira vez)..."):
                try:
                    executable = energyplus_runner.install_energyplus()
                except Exception as error:
                    st.error(f"Não foi possível baixar o EnergyPlus: {error}")
                    st.stop()
        with st.spinner("Simulando os dois modelos no EnergyPlus (pode levar vários minutos)..."):
            try:
                jobs = {
                    "real": prepare_simulation(st.session_state["real_osm"], epw_path, work_dir / "simulacao_real", engine),
                    "referencia": prepare_simulation(ref_osm, epw_path, work_dir / "simulacao_referencia", engine),
                }
            except Exception as error:
                st.error(f"Falha ao preparar a simulação: {error}")
                st.stop()
            outcome = run_simulations(engine, executable, jobs, epw_path)
        for name, (code, stdout, stderr) in outcome.items():
            if code != 0:
                st.error(f"A simulação do modelo {name} falhou.")
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
        st.session_state["results"] = results
        st.session_state["ref_osm"] = ref_osm

    if "results" not in st.session_state:
        st.stop()

    results = st.session_state["results"]
    coef = results["coefficients"]
    general_class = coefficients.calculate_class(results["redcep"], coef["factor_i"])
    envelope_class = coefficients.calculate_class(results["redcgtt"], coef["factor_i_envelope"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        class_badge("Classificação geral", general_class)
    with col2:
        st.metric("RedCEP (Eq. 8.1)", f"{results['redcep']:.1f} %")
        st.caption(f"CRCEPD-A = {coef['crcepd_a']:.2f}, i = {coef['factor_i']:.2f} %")
    with col3:
        class_badge("Envoltória", envelope_class)
    with col4:
        st.metric("RedCgTT (Eq. C.I.10)", f"{results['redcgtt']:.1f} %")
        st.caption(f"CRCgTTD-A = {coef['crcgtt_d_a']:.2f}, i = {coef['factor_i_envelope']:.2f} %")

    i = coef["factor_i"]
    st.write(f"Limites da Tabela 8.2: A > {3 * i:.1f} %, B > {2 * i:.1f} %, C > {i:.1f} %, D de 0 a {i:.1f} %, E < 0 %.")

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
    table = pd.DataFrame({
        "Indicador (kWh/ano)": [label for label, _ in rows],
        "Modelo real": [round(results["real_model"][key], 1) for _, key in rows],
        "Modelo de referência": [round(results["reference_model"][key], 1) for _, key in rows],
    })
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(f"CEER real {results['real_model']['ceer']:.2f}, CEER referência {CEER_REFERENCE}. "
               f"Iluminação e equipamentos ajustados para {redcep.OCCUPATION_DAYS_LIGHTING_EQUIPMENT} dias "
               f"(simulados: {results['real_model']['simulated_days']}). Fator de energia primária fcE = {redcep.PRIMARY_ENERGY_FACTOR_BRAZIL}. "
               "O RedCEP desconta o consumo de equipamentos dos dois modelos (Eq. 8.1).")

    st.header("6. Arquivos para conferência")
    summary = pd.DataFrame([
        {"Indicador": "Zona bioclimática", "Valor": coef["bioclimatic_zone"]},
        {"Indicador": "RedCEP (%)", "Valor": round(results["redcep"], 2)},
        {"Indicador": "Classificação geral", "Valor": general_class},
        {"Indicador": "RedCgTT (%)", "Valor": round(results["redcgtt"], 2)},
        {"Indicador": "Classificação da envoltória", "Valor": envelope_class},
    ])
    d1, d2, d3, d4 = st.columns(4)
    d1.download_button("Modelo real (.osm)", Path(st.session_state["real_osm"]).read_bytes(), file_name="modelo_real.osm")
    d2.download_button("Modelo de referência (.osm)", Path(st.session_state["ref_osm"]).read_bytes(), file_name="modelo_referencia.osm")
    d3.download_button("Resultados (.csv)", pd.concat([summary, table.rename(columns={"Indicador (kWh/ano)": "Indicador"})]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="resultados_inic.csv")
    d4.download_button("Tudo (.zip)", zip_folder(work_dir), file_name="inic_gbxml_completo.zip")

    e1, e2 = st.columns(2)
    for column, name, folder in ((e1, "real", "simulacao_real"), (e2, "referência", "simulacao_referencia")):
        run_dir = work_dir / folder / "run"
        with column:
            st.subheader(f"Simulação {name}")
            for file_name in ("in.idf", "eplusout.csv", "eplustbl.htm", "eplusout.err"):
                file_path = run_dir / file_name
                if file_path.exists():
                    st.download_button(file_name, file_path.read_bytes(), file_name=f"{folder}_{file_name}", key=f"{folder}_{file_name}")


if __name__ == "__main__":
    main()
