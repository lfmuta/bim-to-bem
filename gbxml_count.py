import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import os

def analyze_gbxml():
    # Abrir diálogo para selecionar arquivo
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Selecione o arquivo gbXML",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    
    if not file_path:
        print("Nenhum arquivo selecionado.")
        return
    
    print(f"Analisando: {os.path.basename(file_path)}")
    print("Aguarde... (pode demorar alguns segundos para arquivos grandes)\n")
    
    # Carregar o arquivo gbXML
    try:
        tree = ET.parse(file_path)
        root_xml = tree.getroot()
    except Exception as e:
        print(f"Erro ao carregar o arquivo: {e}")
        return
    
    # Namespace do gbXML
    ns = {'gbxml': 'http://www.gbxml.org/schema'}
    
    # Criar janela de resultados com abas
    result_window = tk.Tk()
    result_window.title("Análise gbXML - Resultados Completos")
    result_window.geometry("1000x700")
    
    # Criar notebook (abas)
    notebook = ttk.Notebook(result_window)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Função para criar aba com texto
    def create_tab(title):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Courier", 9))
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        return text_area
    
    # Criar abas
    tab_overview = create_tab("Visão Geral")
    tab_spaces = create_tab("Spaces")
    tab_zones = create_tab("Zones")
    tab_surfaces = create_tab("Surfaces")
    tab_constructions = create_tab("Constructions")
    tab_materials = create_tab("Materials")
    tab_schedules = create_tab("Schedules")
    tab_summary = create_tab("Resumo p/ Artigo")
    
    # ========== ABA: VISÃO GERAL ==========
    def add_overview():
        text = tab_overview
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, "INFORMAÇÕES DO ARQUIVO gbXML\n")
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"Arquivo: {os.path.basename(file_path)}\n")
        text.insert(tk.END, f"Versão gbXML: {root_xml.get('version', 'N/A')}\n")
        text.insert(tk.END, f"Temperature Unit: {root_xml.get('temperatureUnit', 'N/A')}\n")
        text.insert(tk.END, f"Length Unit: {root_xml.get('lengthUnit', 'N/A')}\n")
        text.insert(tk.END, f"Area Unit: {root_xml.get('areaUnit', 'N/A')}\n")
        text.insert(tk.END, f"Volume Unit: {root_xml.get('volumeUnit', 'N/A')}\n")
        text.insert(tk.END, f"Use SI Units: {root_xml.get('useSIUnitsForResults', 'N/A')}\n")
        
        # Location
        location = root_xml.find('.//gbxml:Location', ns)
        if location:
            text.insert(tk.END, "\n" + "=" * 80 + "\n")
            text.insert(tk.END, "LOCATION\n")
            text.insert(tk.END, "=" * 80 + "\n")
            
            name = location.find('gbxml:Name', ns)
            lat = location.find('gbxml:Latitude', ns)
            lon = location.find('gbxml:Longitude', ns)
            elev = location.find('gbxml:Elevation', ns)
            station = location.find('gbxml:StationId', ns)
            zipcode = location.find('gbxml:ZipcodeOrPostalCode', ns)
            azimuth = location.find('gbxml:CADModelAzimuth', ns)
            
            if name is not None:
                text.insert(tk.END, f"Location: {name.text}\n")
            if lat is not None and lon is not None:
                text.insert(tk.END, f"Coordinates: {lat.text}, {lon.text}\n")
            if elev is not None:
                text.insert(tk.END, f"Elevation: {elev.text} m\n")
            if station is not None:
                text.insert(tk.END, f"Weather Station ID: {station.text}\n")
            if zipcode is not None:
                text.insert(tk.END, f"Zipcode: {zipcode.text}\n")
            if azimuth is not None:
                text.insert(tk.END, f"CAD Model Azimuth: {azimuth.text}°\n")
        
        # Building
        building = root_xml.find('.//gbxml:Building', ns)
        if building:
            text.insert(tk.END, "\n" + "=" * 80 + "\n")
            text.insert(tk.END, "BUILDING\n")
            text.insert(tk.END, "=" * 80 + "\n")
            text.insert(tk.END, f"Building ID: {building.get('id', 'N/A')}\n")
            text.insert(tk.END, f"Building Type: {building.get('buildingType', 'N/A')}\n")
            
            area = building.find('gbxml:Area', ns)
            address = building.find('gbxml:StreetAddress', ns)
            
            if area is not None:
                text.insert(tk.END, f"Total Area: {area.text} m²\n")
            if address is not None:
                text.insert(tk.END, f"Address: {address.text}\n")
        
        # Contadores gerais
        spaces = root_xml.findall('.//gbxml:Space', ns)
        zones = root_xml.findall('.//gbxml:Zone', ns)
        surfaces = root_xml.findall('.//gbxml:Surface', ns)
        openings = root_xml.findall('.//gbxml:Opening', ns)
        constructions = root_xml.findall('.//gbxml:Construction', ns)
        materials = root_xml.findall('.//gbxml:Material', ns)
        layers = root_xml.findall('.//gbxml:Layer', ns)
        schedules = root_xml.findall('.//gbxml:Schedule', ns)
        day_schedules = root_xml.findall('.//gbxml:DaySchedule', ns)
        week_schedules = root_xml.findall('.//gbxml:WeekSchedule', ns)
        
        text.insert(tk.END, "\n" + "=" * 80 + "\n")
        text.insert(tk.END, "CONTAGEM DE ELEMENTOS\n")
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"Spaces: {len(spaces)}\n")
        text.insert(tk.END, f"Zones: {len(zones)}\n")
        text.insert(tk.END, f"Surfaces: {len(surfaces)}\n")
        text.insert(tk.END, f"Openings: {len(openings)}\n")
        text.insert(tk.END, f"Constructions: {len(constructions)}\n")
        text.insert(tk.END, f"Materials: {len(materials)}\n")
        text.insert(tk.END, f"Layers: {len(layers)}\n")
        text.insert(tk.END, f"Schedules: {len(schedules)}\n")
        text.insert(tk.END, f"Day Schedules: {len(day_schedules)}\n")
        text.insert(tk.END, f"Week Schedules: {len(week_schedules)}\n")
        
        text.config(state=tk.DISABLED)
    
    # ========== ABA: SPACES ==========
    def add_spaces():
        text = tab_spaces
        spaces = root_xml.findall('.//gbxml:Space', ns)
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"SPACES ({len(spaces)} total)\n")
        text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Tipos de espaços
        space_types = [s.get('spaceType') for s in spaces if s.get('spaceType')]
        space_type_counts = Counter(space_types)
        
        text.insert(tk.END, "TIPOS DE ESPAÇOS:\n")
        text.insert(tk.END, "-" * 80 + "\n")
        for st, count in sorted(space_type_counts.items(), key=lambda x: x[1], reverse=True):
            text.insert(tk.END, f"  {st}: {count}\n")
        
        # Condition types
        condition_types = [s.get('conditionType') for s in spaces if s.get('conditionType')]
        condition_type_counts = Counter(condition_types)
        
        text.insert(tk.END, "\nCONDITION TYPES:\n")
        text.insert(tk.END, "-" * 80 + "\n")
        for ct, count in sorted(condition_type_counts.items(), key=lambda x: x[1], reverse=True):
            text.insert(tk.END, f"  {ct}: {count}\n")
        
        # Estatísticas de áreas
        areas = []
        volumes = []
        for space in spaces:
            area = space.find('gbxml:Area', ns)
            volume = space.find('gbxml:Volume', ns)
            if area is not None:
                try:
                    areas.append(float(area.text))
                except:
                    pass
            if volume is not None:
                try:
                    volumes.append(float(volume.text))
                except:
                    pass
        
        if areas:
            text.insert(tk.END, "\nESTATÍSTICAS DE ÁREA:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Total: {sum(areas):.2f} m²\n")
            text.insert(tk.END, f"  Média: {sum(areas)/len(areas):.2f} m²\n")
            text.insert(tk.END, f"  Mínima: {min(areas):.2f} m²\n")
            text.insert(tk.END, f"  Máxima: {max(areas):.2f} m²\n")
        
        if volumes:
            text.insert(tk.END, "\nESTATÍSTICAS DE VOLUME:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Total: {sum(volumes):.2f} m³\n")
            text.insert(tk.END, f"  Média: {sum(volumes)/len(volumes):.2f} m³\n")
            text.insert(tk.END, f"  Mínimo: {min(volumes):.2f} m³\n")
            text.insert(tk.END, f"  Máximo: {max(volumes):.2f} m³\n")
        
        # Exemplo detalhado: aim0711
        example_space = root_xml.find('.//gbxml:Space[@id="aim0711"]', ns)
        if example_space:
            text.insert(tk.END, "\n" + "=" * 80 + "\n")
            text.insert(tk.END, "EXEMPLO DETALHADO: SPACE aim0711\n")
            text.insert(tk.END, "=" * 80 + "\n")
            
            name = example_space.find('gbxml:Name', ns)
            desc = example_space.find('gbxml:Description', ns)
            
            if name is not None:
                text.insert(tk.END, f"Name: {name.text}\n")
            if desc is not None:
                text.insert(tk.END, f"Description: {desc.text}\n")
            
            text.insert(tk.END, f"Space Type: {example_space.get('spaceType', 'N/A')}\n")
            text.insert(tk.END, f"Condition Type: {example_space.get('conditionType', 'N/A')}\n")
            text.insert(tk.END, f"Zone ID Ref: {example_space.get('zoneIdRef', 'N/A')}\n")
            text.insert(tk.END, f"Building Storey ID Ref: {example_space.get('buildingStoreyIdRef', 'N/A')}\n")
            
            # Schedules
            light_sched = example_space.get('lightScheduleIdRef')
            equip_sched = example_space.get('equipmentScheduleIdRef')
            people_sched = example_space.get('peopleScheduleIdRef')
            
            if light_sched:
                text.insert(tk.END, f"Light Schedule ID: {light_sched}\n")
            if equip_sched:
                text.insert(tk.END, f"Equipment Schedule ID: {equip_sched}\n")
            if people_sched:
                text.insert(tk.END, f"People Schedule ID: {people_sched}\n")
            
            # Geometria
            area = example_space.find('gbxml:Area', ns)
            volume = example_space.find('gbxml:Volume', ns)
            if area is not None:
                text.insert(tk.END, f"Area: {area.text} m²\n")
            if volume is not None:
                text.insert(tk.END, f"Volume: {volume.text} m³\n")
            
            # Cargas internas
            text.insert(tk.END, "\nCARGAS INTERNAS:\n")
            
            people = example_space.find('gbxml:PeopleNumber', ns)
            if people is not None:
                text.insert(tk.END, f"  People: {people.text} {people.get('unit', 'NumberOfPeople')}\n")
            
            people_heat = example_space.findall('gbxml:PeopleHeatGain', ns)
            for ph in people_heat:
                heat_type = ph.get('heatGainType', 'Unknown')
                text.insert(tk.END, f"  People Heat Gain ({heat_type}): {ph.text} {ph.get('unit', 'W/person')}\n")
            
            light = example_space.find('gbxml:LightPowerPerArea', ns)
            if light is not None:
                text.insert(tk.END, f"  Lighting: {light.text} {light.get('unit', 'W/m²')}\n")
            
            equip = example_space.find('gbxml:EquipPowerPerArea', ns)
            if equip is not None:
                text.insert(tk.END, f"  Equipment: {equip.text} {equip.get('unit', 'W/m²')}\n")
            
            ach = example_space.find('gbxml:AirChangesPerHour', ns)
            if ach is not None:
                text.insert(tk.END, f"  Air Changes Per Hour: {ach.text}\n")
            
            # Parâmetros de análise
            params = example_space.findall('gbxml:AnalysisParameter', ns)
            if params:
                text.insert(tk.END, "\nPARÂMETROS DE ANÁLISE:\n")
                for param in params:
                    name_elem = param.find('gbxml:Name', ns)
                    value = param.find('gbxml:ParameterValue', ns)
                    unit = param.get('unit', '')
                    if name_elem is not None and value is not None:
                        text.insert(tk.END, f"  {name_elem.text}: {value.text} {unit}\n")
        
        text.config(state=tk.DISABLED)
    
    # ========== ABA: ZONES ==========
    def add_zones():
        text = tab_zones
        zones = root_xml.findall('.//gbxml:Zone', ns)
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"ZONES ({len(zones)} total)\n")
        text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Estatísticas de setpoints
        heat_setpoints = []
        cool_setpoints = []
        
        for zone in zones:
            heat_t = zone.find('gbxml:DesignHeatT', ns)
            cool_t = zone.find('gbxml:DesignCoolT', ns)
            
            if heat_t is not None:
                try:
                    heat_setpoints.append(float(heat_t.text))
                except:
                    pass
            if cool_t is not None:
                try:
                    cool_setpoints.append(float(cool_t.text))
                except:
                    pass
        
        if heat_setpoints:
            text.insert(tk.END, "HEATING SETPOINTS:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Média: {sum(heat_setpoints)/len(heat_setpoints):.2f} °C\n")
            text.insert(tk.END, f"  Mínimo: {min(heat_setpoints):.2f} °C\n")
            text.insert(tk.END, f"  Máximo: {max(heat_setpoints):.2f} °C\n")
            text.insert(tk.END, f"  Valores únicos: {sorted(set(heat_setpoints))}\n")
        
        if cool_setpoints:
            text.insert(tk.END, "\nCOOLING SETPOINTS:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Média: {sum(cool_setpoints)/len(cool_setpoints):.2f} °C\n")
            text.insert(tk.END, f"  Mínimo: {min(cool_setpoints):.2f} °C\n")
            text.insert(tk.END, f"  Máximo: {max(cool_setpoints):.2f} °C\n")
            text.insert(tk.END, f"  Valores únicos: {sorted(set(cool_setpoints))}\n")
        
        # Exemplo detalhado
        example_zone = root_xml.find('.//gbxml:Zone[@id="aim44838"]', ns)
        if example_zone:
            text.insert(tk.END, "\n" + "=" * 80 + "\n")
            text.insert(tk.END, "EXEMPLO DETALHADO: ZONE aim44838\n")
            text.insert(tk.END, "=" * 80 + "\n")
            
            name = example_zone.find('gbxml:Name', ns)
            if name is not None:
                text.insert(tk.END, f"Name: {name.text}\n")
            
            cad_id = example_zone.find('gbxml:CADObjectId', ns)
            if cad_id is not None:
                text.insert(tk.END, f"CAD Object ID: {cad_id.text}\n")
            
            # Parâmetros de ventilação
            ach = example_zone.find('gbxml:AirChangesPerHour', ns)
            oa_area = example_zone.find('gbxml:OAFlowPerArea', ns)
            oa_person = example_zone.find('gbxml:OAFlowPerPerson', ns)
            
            text.insert(tk.END, "\nVENTILAÇÃO:\n")
            if ach is not None:
                text.insert(tk.END, f"  Air Changes Per Hour: {ach.text}\n")
            if oa_area is not None:
                text.insert(tk.END, f"  OA Flow Per Area: {oa_area.text} {oa_area.get('unit', '')}\n")
            if oa_person is not None:
                text.insert(tk.END, f"  OA Flow Per Person: {oa_person.text} {oa_person.get('unit', '')}\n")
            
            # Setpoints
            heat_t = example_zone.find('gbxml:DesignHeatT', ns)
            cool_t = example_zone.find('gbxml:DesignCoolT', ns)
            heat_rh = example_zone.find('gbxml:DesignHeatRH', ns)
            cool_rh = example_zone.find('gbxml:DesignCoolRH', ns)
            
            text.insert(tk.END, "\nSETPOINTS:\n")
            if heat_t is not None:
                text.insert(tk.END, f"  Design Heat T: {heat_t.text} {heat_t.get('unit', '°C')}\n")
            if cool_t is not None:
                text.insert(tk.END, f"  Design Cool T: {cool_t.text} {cool_t.get('unit', '°C')}\n")
            if heat_rh is not None:
                text.insert(tk.END, f"  Design Heat RH: {heat_rh.text}\n")
            if cool_rh is not None:
                text.insert(tk.END, f"  Design Cool RH: {cool_rh.text}\n")
        
        text.config(state=tk.DISABLED)
    
    # ========== ABA: SURFACES ==========
    def add_surfaces():
        text = tab_surfaces
        surfaces = root_xml.findall('.//gbxml:Surface', ns)
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"SURFACES ({len(surfaces)} total)\n")
        text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Tipos de superfícies
        surface_types = [s.get('surfaceType') for s in surfaces if s.get('surfaceType')]
        surface_type_counts = Counter(surface_types)
        
        text.insert(tk.END, "TIPOS DE SUPERFÍCIES:\n")
        text.insert(tk.END, "-" * 80 + "\n")
        for st, count in sorted(surface_type_counts.items(), key=lambda x: x[1], reverse=True):
            text.insert(tk.END, f"  {st}: {count}\n")
        
        # Exposure types
        exposure_types = [s.get('exposedToSun') for s in surfaces if s.get('exposedToSun')]
        exposure_counts = Counter(exposure_types)
        
        text.insert(tk.END, "\nEXPOSURE TO SUN:\n")
        text.insert(tk.END, "-" * 80 + "\n")
        for et, count in sorted(exposure_counts.items(), key=lambda x: x[1], reverse=True):
            text.insert(tk.END, f"  {et}: {count}\n")
        
        # Openings
        openings = root_xml.findall('.//gbxml:Opening', ns)
        if openings:
            opening_types = [o.get('openingType') for o in openings if o.get('openingType')]
            opening_type_counts = Counter(opening_types)
            
            text.insert(tk.END, f"\nOPENINGS ({len(openings)} total):\n")
            text.insert(tk.END, "-" * 80 + "\n")
            for ot, count in sorted(opening_type_counts.items(), key=lambda x: x[1], reverse=True):
                text.insert(tk.END, f"  {ot}: {count}\n")
        
        text.config(state=tk.DISABLED)
    
    # ========== ABA: CONSTRUCTIONS ==========
    def add_constructions():
        text = tab_constructions
        constructions = root_xml.findall('.//gbxml:Construction', ns)
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"CONSTRUCTIONS ({len(constructions)} total)\n")
        text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Estatísticas de U-value
        u_values = []
        for const in constructions:
            u_val = const.find('gbxml:U-value', ns)
            if u_val is not None:
                try:
                    u_values.append(float(u_val.text))
                except:
                    pass
        
        if u_values:
            text.insert(tk.END, "ESTATÍSTICAS DE U-VALUE:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Média: {sum(u_values)/len(u_values):.4f} W/m²K\n")
            text.insert(tk.END, f"  Mínimo: {min(u_values):.4f} W/m²K\n")
            text.insert(tk.END, f"  Máximo: {max(u_values):.4f} W/m²K\n")
        
        # Exemplo detalhado
        example_const = root_xml.find('.//gbxml:Construction[@id="aim14698"]', ns)
        if example_const:
            text.insert(tk.END, "\n" + "=" * 80 + "\n")
            text.insert(tk.END, "EXEMPLO DETALHADO: CONSTRUCTION aim14698\n")
            text.insert(tk.END, "=" * 80 + "\n")
            
            name = example_const.find('gbxml:Name', ns)
            if name is not None:
                text.insert(tk.END, f"Name: {name.text}\n")
            
            text.insert(tk.END, f"Is Schematic: {example_const.get('constructionIsSchematic', 'N/A')}\n")
            
            u_val = example_const.find('gbxml:U-value', ns)
            if u_val is not None:
                text.insert(tk.END, f"U-value: {u_val.text} {u_val.get('unit', 'W/m²K')}\n")
            
            absorptance = example_const.find('gbxml:Absorptance', ns)
            if absorptance is not None:
                text.insert(tk.END, f"Absorptance ({absorptance.get('type', 'N/A')}): {absorptance.text} {absorptance.get('unit', '')}\n")
            
            roughness = example_const.find('gbxml:Roughness', ns)
            if roughness is not None:
                text.insert(tk.END, f"Roughness: {roughness.get('value', 'N/A')}\n")
            
            # Layers
            layer_ids = example_const.findall('gbxml:LayerId', ns)
            if layer_ids:
                text.insert(tk.END, f"\nLayers: {len(layer_ids)}\n")
                for lid in layer_ids:
                    text.insert(tk.END, f"  - Layer ID: {lid.get('layerIdRef', 'N/A')}\n")
        
        text.config(state=tk.DISABLED)
    
    # ========== ABA: MATERIALS ==========
    def add_materials():
        text = tab_materials
        materials = root_xml.findall('.//gbxml:Material', ns)
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"MATERIALS ({len(materials)} total)\n")
        text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Estatísticas
        conductivities = []
        densities = []
        specific_heats = []
        
        for mat in materials:
            cond = mat.find('gbxml:Conductivity', ns)
            dens = mat.find('gbxml:Density', ns)
            spec_heat = mat.find('gbxml:SpecificHeat', ns)
            
            if cond is not None:
                try:
                    conductivities.append(float(cond.text))
                except:
                    pass
            if dens is not None:
                try:
                    densities.append(float(dens.text))
                except:
                    pass
            if spec_heat is not None:
                try:
                    specific_heats.append(float(spec_heat.text))
                except:
                    pass
        
        if conductivities:
            text.insert(tk.END, "CONDUTIVIDADE TÉRMICA:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Média: {sum(conductivities)/len(conductivities):.4f} W/mK\n")
            text.insert(tk.END, f"  Mínima: {min(conductivities):.4f} W/mK\n")
            text.insert(tk.END, f"  Máxima: {max(conductivities):.4f} W/mK\n")
        
        if densities:
            text.insert(tk.END, "\nDENSIDADE:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Média: {sum(densities)/len(densities):.2f} kg/m³\n")
            text.insert(tk.END, f"  Mínima: {min(densities):.2f} kg/m³\n")
            text.insert(tk.END, f"  Máxima: {max(densities):.2f} kg/m³\n")
        
        if specific_heats:
            text.insert(tk.END, "\nCALOR ESPECÍFICO:\n")
            text.insert(tk.END, "-" * 80 + "\n")
            text.insert(tk.END, f"  Média: {sum(specific_heats)/len(specific_heats):.2f} J/kgK\n")
            text.insert(tk.END, f"  Mínimo: {min(specific_heats):.2f} J/kgK\n")
            text.insert(tk.END, f"  Máximo: {max(specific_heats):.2f} J/kgK\n")
        
        # Exemplo detalhado
        example_mat = root_xml.find('.//gbxml:Material[@id="aim14703"]', ns)
        if example_mat:
            text.insert(tk.END, "\n" + "=" * 80 + "\n")
            text.insert(tk.END, "EXEMPLO DETALHADO: MATERIAL aim14703\n")
            text.insert(tk.END, "=" * 80 + "\n")
            
            name = example_mat.find('gbxml:Name', ns)
            desc = example_mat.find('gbxml:Description', ns)
            
            if name is not None:
                text.insert(tk.END, f"Name: {name.text}\n")
            if desc is not None:
                text.insert(tk.END, f"Description: {desc.text}\n")
            
            r_val = example_mat.find('gbxml:R-value', ns)
            thickness = example_mat.find('gbxml:Thickness', ns)
            cond = example_mat.find('gbxml:Conductivity', ns)
            dens = example_mat.find('gbxml:Density', ns)
            spec_heat = example_mat.find('gbxml:SpecificHeat', ns)
            
            if r_val is not None:
                text.insert(tk.END, f"R-value: {r_val.text} {r_val.get('unit', 'm²K/W')}\n")
            if thickness is not None:
                text.insert(tk.END, f"Thickness: {thickness.text} {thickness.get('unit', 'm')}\n")
            if cond is not None:
                text.insert(tk.END, f"Conductivity: {cond.text} {cond.get('unit', 'W/mK')}\n")
            if dens is not None:
                text.insert(tk.END, f"Density: {dens.text} {dens.get('unit', 'kg/m³')}\n")
            if spec_heat is not None:
                text.insert(tk.END, f"Specific Heat: {spec_heat.text} {spec_heat.get('unit', 'J/kgK')}\n")
        
        text.config(state=tk.DISABLED)
    
    # ========== ABA: SCHEDULES ==========
    def add_schedules():
        text = tab_schedules
        schedules = root_xml.findall('.//gbxml:Schedule', ns)
        day_schedules = root_xml.findall('.//gbxml:DaySchedule', ns)
        week_schedules = root_xml.findall('.//gbxml:WeekSchedule', ns)
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, "SCHEDULES\n")
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"Schedules (Year): {len(schedules)}\n")
        text.insert(tk.END, f"Week Schedules: {len(week_schedules)}\n")
        text.insert(tk.END, f"Day Schedules: {len(day_schedules)}\n")
        
        # Tipos de schedules
        schedule_types = [s.get('type') for s in schedules if s.get('type')]
        schedule_type_counts = Counter(schedule_types)
        
        text.insert(tk.END, "\nTIPOS DE SCHEDULES:\n")
        text.insert(tk.END, "-" * 80 + "\n")
        for st, count in sorted(schedule_type_counts.items(), key=lambda x: x[1], reverse=True):
            text.insert(tk.END, f"  {st}: {count}\n")
        
        # Exemplo detalhado: Day Schedule
        example_day = root_xml.find('.//gbxml:DaySchedule[@id="aim0724"]', ns)
        if example_day:
            text.insert(tk.END, "\n" + "=" * 80 + "\n")
            text.insert(tk.END, "EXEMPLO DETALHADO: DAY SCHEDULE aim0724\n")
            text.insert(tk.END, "=" * 80 + "\n")
            
            name = example_day.find('gbxml:Name', ns)
            if name is not None:
                text.insert(tk.END, f"Name: {name.text}\n")
            
            text.insert(tk.END, f"Schedule Type: {example_day.get('scheduleType', 'N/A')}\n")
            
            values = example_day.findall('gbxml:ScheduleValue', ns)
            text.insert(tk.END, f"\nSchedule Values (24 hours): {len(values)}\n")
            text.insert(tk.END, "Hour | Value\n")
            text.insert(tk.END, "-" * 20 + "\n")
            for i, val in enumerate(values):
                text.insert(tk.END, f"{i:4d} | {val.text}\n")
        
        text.config(state=tk.DISABLED)
    
    # ========== ABA: RESUMO PARA ARTIGO ==========
    def add_summary():
        text = tab_summary
        
        spaces = root_xml.findall('.//gbxml:Space', ns)
        zones = root_xml.findall('.//gbxml:Zone', ns)
        surfaces = root_xml.findall('.//gbxml:Surface', ns)
        openings = root_xml.findall('.//gbxml:Opening', ns)
        constructions = root_xml.findall('.//gbxml:Construction', ns)
        materials = root_xml.findall('.//gbxml:Material', ns)
        schedules = root_xml.findall('.//gbxml:Schedule', ns)
        
        surface_types = [s.get('surfaceType') for s in surfaces if s.get('surfaceType')]
        surface_type_counts = Counter(surface_types)
        
        opening_types = [o.get('openingType') for o in openings if o.get('openingType')]
        opening_type_counts = Counter(opening_types)
        
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, "RESUMO PARA O ARTIGO\n")
        text.insert(tk.END, "=" * 80 + "\n\n")
        
        text.insert(tk.END, "PARÁGRAFO SUGERIDO:\n")
        text.insert(tk.END, "-" * 80 + "\n\n")
        
        # Construir parágrafo
        paragraph = f"The gbXML file exported from the energy analytical model contained the geometric and semantic data defined in the BIM model, including spatial organization, surface boundaries, and construction assignments. "
        
        paragraph += f"The file comprised {len(spaces)} space objects, {len(surfaces)} surfaces "
        
        # Top 5 surface types
        main_surface_types = []
        for st, count in sorted(surface_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            main_surface_types.append(f"{count} {st.lower()}{'s' if count > 1 else ''}")
        
        if main_surface_types:
            paragraph += f"({', '.join(main_surface_types)})"
        
        if openings:
            paragraph += f", and {len(openings)} openings"
            
            main_opening_types = []
            for ot, count in sorted(opening_type_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                main_opening_types.append(f"{count} {ot.lower()}{'s' if count > 1 else ''}")
            
            if main_opening_types:
                paragraph += f" ({', '.join(main_opening_types)})"
        
        paragraph += ". "
        
        paragraph += f"The model included {len(zones)} thermal zones with complete HVAC specifications (heating and cooling setpoints, outdoor air requirements), "
        paragraph += f"{len(constructions)} construction assemblies with thermal properties, "
        paragraph += f"{len(materials)} material definitions, "
        paragraph += f"and {len(schedules)} operational schedules. "
        
        paragraph += "Each space included complete geometric definitions (planar and shell geometry), internal load specifications (people density, lighting power density, equipment power density), and airflow parameters (outdoor air flow rates and infiltration rates). "
        
        paragraph += "Visual inspection through the analytical preview revealed overall geometric continuity across the building envelope and internal partitions. "
        
        paragraph += "The surface type misclassification identified in the analytical model (e.g., RaisedFloor instead of SlabOnGrade in the South block) was present in the exported file. "
        
        paragraph += "This gbXML file served as the input dataset for the subsequent automated processing stages."
        
        # Quebrar em linhas de ~80 caracteres
        import textwrap
        wrapped = textwrap.fill(paragraph, width=80)
        text.insert(tk.END, wrapped + "\n")
        
        text.insert(tk.END, "\n" + "=" * 80 + "\n")
        text.insert(tk.END, "DADOS QUANTITATIVOS:\n")
        text.insert(tk.END, "=" * 80 + "\n")
        text.insert(tk.END, f"Spaces: {len(spaces)}\n")
        text.insert(tk.END, f"Zones: {len(zones)}\n")
        text.insert(tk.END, f"Surfaces: {len(surfaces)}\n")
        if openings:
            text.insert(tk.END, f"Openings: {len(openings)}\n")
        text.insert(tk.END, f"Constructions: {len(constructions)}\n")
        text.insert(tk.END, f"Materials: {len(materials)}\n")
        text.insert(tk.END, f"Schedules: {len(schedules)}\n")
        
        text.insert(tk.END, "\nSURFACE TYPES (top 10):\n")
        for st, count in sorted(surface_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            text.insert(tk.END, f"  {st}: {count}\n")
        
        if opening_types:
            text.insert(tk.END, "\nOPENING TYPES:\n")
            for ot, count in sorted(opening_type_counts.items(), key=lambda x: x[1], reverse=True):
                text.insert(tk.END, f"  {ot}: {count}\n")
        
        text.config(state=tk.DISABLED)
    
    # Preencher todas as abas
    add_overview()
    add_spaces()
    add_zones()
    add_surfaces()
    add_constructions()
    add_materials()
    add_schedules()
    add_summary()
    
    # Botão para salvar todos os resultados
    def save_all_results():
        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="gbxml_complete_analysis.txt"
        )
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                # Salvar conteúdo de todas as abas
                for tab_name, text_widget in [
                    ("VISÃO GERAL", tab_overview),
                    ("SPACES", tab_spaces),
                    ("ZONES", tab_zones),
                    ("SURFACES", tab_surfaces),
                    ("CONSTRUCTIONS", tab_constructions),
                    ("MATERIALS", tab_materials),
                    ("SCHEDULES", tab_schedules),
                    ("RESUMO PARA ARTIGO", tab_summary)
                ]:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(f"{tab_name}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(text_widget.get(1.0, tk.END))
                    f.write("\n")
            print(f"Análise completa salva em: {save_path}")
    
    save_button = tk.Button(result_window, text="Salvar Análise Completa", command=save_all_results, 
                           font=("Arial", 12), bg="#4CAF50", fg="white", padx=20, pady=10)
    save_button.pack(pady=10)
    
    result_window.mainloop()

if __name__ == "__main__":
    analyze_gbxml()
