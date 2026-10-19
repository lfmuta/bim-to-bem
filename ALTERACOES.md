# Alterações nos scripts da ferramenta BIM-BEM via gbXML

Referência: INI-C, Anexo I da Portaria Inmetro 309/2022 (versão consolidada), tipologia educacional.

Para cada script: o motivo da alteração e, em seguida, cada trecho alterado com a linha antes (arquivo original) e depois (arquivo atualizado).

## Scripts sem alteração

00_absorptance_fixer.py, 01_gbxml_converter.py, 02_schedules_cleaner.py, 06_ideal_loads_assigner_24-7.py (não é INI-C), 07_plenum_disabler.py, 14_c_class_calculator.py, gbxml_count.py, spacetype_utils.py, surface_mapping_utils.py, clean_schedules.py, purge_objects.py.

paf_modifier.py e glazing_modifier_test.py não foram atualizados: são versões anteriores do glazing_modifier.py, que reúne as correções.

## Arquivos novos

- reference_construction_utils.py: Novo módulo auxiliar usado por wall_modifier, roof_modifier e floor_modifier: monta as construções da Tabela A.9 mantendo a absortância interna do modelo real e espelha a construção nos pares de superfícies entre zonas.
- app_inic.py: Novo: aplicativo Streamlit (upload do gbXML e do EPW, geração dos modelos real e de referência, simulação, classificação e downloads).

## 03_loads_enricher.py

Motivo:

- DPI: usa o valor do gbXML; se o gbXML não tiver DPI, permite informar a DPI de projeto ou usar a DPI de referência (15,5 W/m²) só nas APPs, nos dois modelos (item C.I.4).
- Densidade de ocupação passa a ser parâmetro (1,5 m²/pessoa no ensino fundamental, médio e superior; 2,5 na educação infantil, Tabela A.2).

Antes (linha 13)

```python
    def __init__(self):
```

Depois (linha 13)

```python
    def __init__(self, area_per_person=1.5, lighting_mode="gbxml", dpi_value=None):
```

---

Antes (linha 21)

```python
        self.AREA_PER_PERSON = 1.5  # m²/person
```

Depois (linha 21)

```python
        self.AREA_PER_PERSON = area_per_person  # m²/person
```

---

Antes: nada (inserido após a linha 22)

Depois (linhas 23 a 25)

```python
        self.REFERENCE_DPI = 15.5  # W/m²
        self.lighting_mode = lighting_mode
        self.dpi_value = dpi_value
```

---

Antes: nada (inserido após a linha 43)

Depois (linhas 47 a 69)

```python
        return spaces_data

    def gbxml_has_lighting(self, spaces_data):
        """Returns True if at least one space has LightPowerPerArea greater than zero."""
        return any(d['lights'] > 0 for d in spaces_data.values())

    def resolve_lighting(self, spaces_data):
        """Defines the lighting power density of each space according to the lighting mode."""
        mode = self.lighting_mode
        if mode == "gbxml" and not self.gbxml_has_lighting(spaces_data):
            logging.warning("gbXML has no LightPowerPerArea. Using reference DPI only in APP spaces (lighting system not evaluated).")
            print("WARNING: gbXML has no lighting power density. Reference DPI applied only to APP spaces.")
            mode = "reference"
        for data in spaces_data.values():
            if mode == "project":
                data['lights'] = float(self.dpi_value)
                data['lights_app_only'] = False
            elif mode == "reference":
                data['lights'] = self.REFERENCE_DPI
                data['lights_app_only'] = True
            else:
                data['lights_app_only'] = False
        self.lighting_mode = mode
```

---

Antes: nada (inserido após a linha 95)

Depois (linhas 122 a 123)

```python
            if data.get('lights_app_only') and space_type_label != "APP":
                continue
```

---

Antes: nada (inserido após a linha 143)

Depois (linha 172)

```python
            spaces_data = self.resolve_lighting(spaces_data)
```

---

Antes: nada (inserido após a linha 156)

Depois (linha 186)

```python
            logging.info(f"Lighting mode: {self.lighting_mode}")
```

---

Antes (linha 205)

```python
    enricher = OSMEnricher()
```

Depois: removido

---

Antes: nada (inserido após a linha 206)

Depois (linhas 236 a 238)

```python
    lighting_mode = args[3] if len(args) >= 4 else "gbxml"
    dpi_value = float(args[4]) if len(args) >= 5 else None
    enricher = OSMEnricher(lighting_mode=lighting_mode, dpi_value=dpi_value)
```

---

Antes (linha 208)

```python
    if len(args) == 3:
```

Depois (linha 240)

```python
    if len(args) in (3, 4, 5):
```

---

Antes (linha 219)

```python
        print("Usage: python script.py [gbxml.xml input.osm output.osm] or run without arguments for GUI")
```

Depois (linha 251)

```python
        print("Usage: python script.py [gbxml.xml input.osm output.osm [gbxml|project|reference] [dpi]] or run without arguments for GUI")
```

---

## 04_schedules_enricher.py

Motivo:

- Calor metabólico de 120 para 180 W/pessoa (Tabela C.3, educacionais).

Antes: nada (inserido após a linha 16)

Depois (linha 17)

```python
        self.metabolic_rate = 180.0
```

---

Antes (linha 71)

```python
        """Create activity schedule with fixed 120 W/person as per INI-C."""
```

Depois (linha 72)

```python
        """Create activity schedule with fixed metabolic rate per INI-C Table C.3 (educational: 180 W/person)."""
```

---

Antes (linha 77)

```python
        default_day.addValue(openstudio.Time(0, 24, 0, 0), 120.0)  # 120 W/person
```

Depois (linha 78)

```python
        default_day.addValue(openstudio.Time(0, 24, 0, 0), self.metabolic_rate)
```

---

Antes (linha 82)

```python
        summer_design.addValue(openstudio.Time(0, 24, 0, 0), 120.0)
```

Depois (linha 83)

```python
        summer_design.addValue(openstudio.Time(0, 24, 0, 0), self.metabolic_rate)
```

---

Antes (linha 87)

```python
        winter_design.addValue(openstudio.Time(0, 24, 0, 0), 120.0)
```

Depois (linha 88)

```python
        winter_design.addValue(openstudio.Time(0, 24, 0, 0), self.metabolic_rate)
```

---

Antes (linha 158)

```python
            print("Activity level: 120 W/person (constant)")
```

Depois (linha 159)

```python
            print(f"Activity level: {self.metabolic_rate:.0f} W/person (constant)")
```

---

Antes (linha 208)

```python
        print("- Activity level: 120 W/person (constant)")
```

Depois (linha 209)

```python
        print(f"- Activity level: {self.metabolic_rate:.0f} W/person (constant)")
```

---

Antes (linha 258)

```python
        print("- Activity level: 120 W/person (constant)")
```

Depois (linha 259)

```python
        print("- Activity level: 180 W/person (constant)")
```

---

## 05_airflow_assigner.py

Motivo:

- Infiltração constante de 0,5 ren/h substituída por infiltração por frestas com janelas e portas fechadas, pelo AirflowNetwork (item C.I.6 e Tabela C.4).
- Janelas: C = 0,00063 kg/(s.m), n = 0,63. Portas: C = 0,0024 kg/(s.m), n = 0,59. Cd = 0,60. O expoente das portas aparece como 0,0024 na Tabela C.4, valor fora do intervalo aceito pelo EnergyPlus (0,5 a 1,0); foi usado 0,59 (conferir).
- Ar externo por pessoa e por área passam a ser parâmetros (NBR 16401 e NBR 17037). O ar externo é aplicado por zona térmica: a APT integrada a uma zona de APP (script 10) faz parte dessa zona (item C.I.3.2). Isso também evita que o OpenStudio gere o IDF de forma diferente a cada execução quando os espaços de uma zona têm configurações diferentes.
- Opção afn_only para reaplicar as frestas depois das alterações do modelo de referência.

Antes (linha 12)

```python
    def __init__(self):
```

Depois (linha 12)

```python
    def __init__(self, outdoor_air_per_person=0.0075, outdoor_air_per_area=0.0):
```

---

Antes (linhas 19 a 21)

```python
        # Fixed values for all spaces
        self.infiltration_ach = 0.5  # ACH
        self.outdoor_air_per_person = 0.0075  # m³/s per person
```

Depois (linhas 19 a 201)

```python
        # Outdoor air for APP spaces (NBR 16401 / NBR 17037)
        self.outdoor_air_per_person = outdoor_air_per_person  # m³/s per person
        self.outdoor_air_per_area = outdoor_air_per_area  # m³/s per m²
        # Crack infiltration for closed openings (INI-C Table C.4)
        self.window_crack_coefficient = 0.00063  # kg/(s.m)
        self.window_crack_exponent = 0.63
        self.door_crack_coefficient = 0.0024  # kg/(s.m)
        self.door_crack_exponent = 0.59
        self.discharge_coefficient = 0.60
        self.minimum_density_difference = 0.0001  # kg/m³
        self.window_types = ["FixedWindow", "OperableWindow", "Skylight", "TubularDaylightDome", "TubularDaylightDiffuser"]
        self.door_types = ["Door", "GlassDoor", "OverheadDoor"]

    def remove_infiltration_objects(self, model):
        """Removes design flow rate and leakage area infiltration objects from all spaces."""
        removed = 0
        for obj in model.getSpaceInfiltrationDesignFlowRates():
            obj.remove()
            removed += 1
        for obj in model.getSpaceInfiltrationEffectiveLeakageAreas():
            obj.remove()
            removed += 1
        logging.info(f"Removed {removed} infiltration objects (replaced by crack infiltration)")
        return removed

    def update_outdoor_air(self, model):
        """Applies outdoor air to thermal zones with APP spaces and removes it from zones with only APT spaces.
        All spaces of a zone share the same object, so APT spaces integrated into an APP zone (INI-C item C.I.3.2)
        are treated as part of the APP zone."""
        spaces_processed = {"APP": 0, "APT": 0, "UNCLASSIFIED": 0}
        for space in model.getSpaces():
            if space.designSpecificationOutdoorAir().is_initialized():
                space.designSpecificationOutdoorAir().get().remove()
        for zone in sorted(model.getThermalZones(), key=lambda z: z.nameString()):
            spaces = sorted(zone.spaces(), key=lambda sp: sp.nameString())
            labels = [get_space_type_label(space) for space in spaces]
            if "APP" in labels:
                oa_object = openstudio.model.DesignSpecificationOutdoorAir(model)
                oa_object.setName(f"Outdoor Air {zone.nameString()}")
                oa_object.setOutdoorAirMethod("Sum")
                oa_object.setOutdoorAirFlowperPerson(self.outdoor_air_per_person)
                oa_object.setOutdoorAirFlowperFloorArea(self.outdoor_air_per_area)
                for space in spaces:
                    space.setDesignSpecificationOutdoorAir(oa_object)
                    spaces_processed["APP"] += 1
                logging.info(f"APP | Outdoor air assigned for zone: {zone.nameString()} ({len(spaces)} spaces)")
            else:
                for space, label in zip(spaces, labels):
                    key = "APT" if label == "APT" else "UNCLASSIFIED"
                    spaces_processed[key] += 1
                    if key == "UNCLASSIFIED":
                        msg = f"UNCLASSIFIED | No outdoor air updates performed for space: {space.nameString()}. "
                        if space.spaceType().is_initialized():
                            msg += f"SpaceType: {space.spaceType().get().nameString()}"
                        else:
                            msg += "SpaceType: None"
                        logging.warning(msg)
                logging.info(f"APT | No outdoor air for zone: {zone.nameString()}")
        return spaces_processed

    def _building_geometry(self, model):
        """Returns number of stories, aspect ratio and long axis azimuth for wind pressure calculation."""
        xs, ys, zs = [], [], []
        for surface in model.getSurfaces():
            space_opt = surface.space()
            if not space_opt.is_initialized():
                continue
            transformation = space_opt.get().buildingTransformation()
            for vertex in surface.vertices():
                p = transformation * vertex
                xs.append(p.x())
                ys.append(p.y())
                zs.append(p.z())
        if not xs:
            return 1, 1.0, 0.0
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        long_axis = max(dx, dy)
        short_axis = max(min(dx, dy), 0.01)
        aspect_ratio = max(min(short_axis / long_axis, 1.0), 0.01) if long_axis > 0 else 1.0
        north_axis = model.getBuilding().northAxis()
        azimuth = (north_axis + (90.0 if dx >= dy else 0.0)) % 180.0
        stories = len(model.getBuildingStorys())
        return stories, aspect_ratio, azimuth

    def _remove_airflow_network_objects(self, model):
        for obj in model.getAirflowNetworkSurfaces():
            obj.remove()
        for obj in model.getAirflowNetworkSimpleOpenings():
            obj.remove()
        for obj in model.getAirflowNetworkZones():
            obj.remove()

    def _zone_of(self, planar_surface):
        space_opt = planar_surface.space()
        if not space_opt.is_initialized():
            return None
        zone_opt = space_opt.get().thermalZone()
        if not zone_opt.is_initialized():
            return None
        return zone_opt.get()

    def apply_airflow_network(self, model):
        """Models all windows and doors closed with crack infiltration (INI-C C.I.6 and Table C.4)."""
        self._remove_airflow_network_objects(model)

        stories, aspect_ratio, azimuth = self._building_geometry(model)
        control = model.getAirflowNetworkSimulationControl()
        control.setName("AirflowNetwork INI-C")
        control.setAirflowNetworkControl("MultizoneWithoutDistribution")
        control.setWindPressureCoefficientType("SurfaceAverageCalculation")
        control.setBuildingType("HighRise" if stories > 3 else "LowRise")
        control.setBuildingAspectRatio(aspect_ratio)
        control.setAzimuthAngleofLongAxisofBuilding(azimuth)

        window_component = openstudio.model.AirflowNetworkSimpleOpening(
            model, self.window_crack_coefficient, self.window_crack_exponent,
            self.minimum_density_difference, self.discharge_coefficient)
        window_component.setName("INI-C Window Crack")
        door_component = openstudio.model.AirflowNetworkSimpleOpening(
            model, self.door_crack_coefficient, self.door_crack_exponent,
            self.minimum_density_difference, self.discharge_coefficient)
        door_component.setName("INI-C Door Crack")

        linked_zones = {}
        processed = set()
        counts = {"windows": 0, "doors": 0, "skipped": 0}
        for sub_surface in model.getSubSurfaces():
            handle = str(sub_surface.handle())
            if handle in processed:
                continue
            sub_type = sub_surface.subSurfaceType()
            if sub_type in self.window_types:
                component = window_component
                key = "windows"
            elif sub_type in self.door_types:
                component = door_component
                key = "doors"
            else:
                continue
            surface_opt = sub_surface.surface()
            if not surface_opt.is_initialized():
                continue
            surface = surface_opt.get()
            boundary = surface.outsideBoundaryCondition()
            zone = self._zone_of(sub_surface)
            if zone is None:
                counts["skipped"] += 1
                continue
            if boundary == "Outdoors":
                pass
            elif boundary == "Surface":
                adjacent_opt = sub_surface.adjacentSubSurface()
                if not adjacent_opt.is_initialized():
                    counts["skipped"] += 1
                    logging.warning(f"Interior opening '{sub_surface.nameString()}' has no adjacent sub surface. Skipped.")
                    continue
                adjacent = adjacent_opt.get()
                adjacent_zone = self._zone_of(adjacent)
                processed.add(str(adjacent.handle()))
                if adjacent_zone is None or str(adjacent_zone.handle()) == str(zone.handle()):
                    counts["skipped"] += 1
                    continue
                linked_zones[str(adjacent_zone.handle())] = adjacent_zone
            else:
                counts["skipped"] += 1
                continue
            sub_surface.getAirflowNetworkSurface(component)
            linked_zones[str(zone.handle())] = zone
            processed.add(handle)
            counts[key] += 1

        for zone in linked_zones.values():
            afn_zone = zone.getAirflowNetworkZone()
            afn_zone.setVentilationControlMode("NoVent")

        logging.info(f"AirflowNetwork: {counts['windows']} windows and {counts['doors']} doors with crack infiltration, "
                     f"{len(linked_zones)} zones linked, {counts['skipped']} openings skipped")
        print("AirflowNetwork crack infiltration (INI-C Table C.4):")
        print(f" - Windows: {counts['windows']} (C = {self.window_crack_coefficient} kg/(s.m), n = {self.window_crack_exponent})")
        print(f" - Doors: {counts['doors']} (C = {self.door_crack_coefficient} kg/(s.m), n = {self.door_crack_exponent})")
        print(f" - Zones linked: {len(linked_zones)}")
        return counts
```

---

Antes (linhas 24 a 69)

```python
        """Update airflow objects with values depending on APP/APT classification (via spacetype_utils)."""
        spaces_processed = {"APP": 0, "APT": 0, "UNCLASSIFIED": 0}
        for space in model.getSpaces():
            space_name = space.nameString()
            occupancy_type = get_space_type_label(space)
            if occupancy_type == "APP":
                # --- Remove existing Outdoor Air ---
                if space.designSpecificationOutdoorAir().is_initialized():
                    space.designSpecificationOutdoorAir().get().remove()
                # Add new Outdoor Air object
                oa_object = openstudio.model.DesignSpecificationOutdoorAir(model)
                oa_object.setOutdoorAirFlowperPerson(self.outdoor_air_per_person)
                oa_object.setOutdoorAirFlowperFloorArea(0.0)
                space.setDesignSpecificationOutdoorAir(oa_object)
                # --- Infiltration (remove old, add new) ---
                for obj in space.spaceInfiltrationDesignFlowRates():
                    obj.remove()
                infiltration_object = openstudio.model.SpaceInfiltrationDesignFlowRate(model)
                infiltration_object.setSpace(space)
                infiltration_object.setAirChangesperHour(self.infiltration_ach)
                infiltration_object.setSchedule(model.alwaysOnDiscreteSchedule())
                spaces_processed["APP"] += 1
                logging.info(f"APP | Updated airflow (Infiltration + OutdoorAir) for space: {space_name}")
            elif occupancy_type == "APT":
                # Remove Outdoor Air if present
                if space.designSpecificationOutdoorAir().is_initialized():
                    space.designSpecificationOutdoorAir().get().remove()
                # Do not insert new Outdoor Air object in APT
                # --- Infiltration (remove old, add new) ---
                for obj in space.spaceInfiltrationDesignFlowRates():
                    obj.remove()
                infiltration_object = openstudio.model.SpaceInfiltrationDesignFlowRate(model)
                infiltration_object.setSpace(space)
                infiltration_object.setAirChangesperHour(self.infiltration_ach)
                infiltration_object.setSchedule(model.alwaysOnDiscreteSchedule())
                spaces_processed["APT"] += 1
                logging.info(f"APT | Updated airflow (Infiltration only) for space: {space_name}")
            else:
                spaces_processed["UNCLASSIFIED"] += 1
                msg = f"UNCLASSIFIED | No airflow updates performed for space: {space_name}. "
                if space.spaceType().is_initialized():
                    msg += f"SpaceType: {space.spaceType().get().nameString()}"
                else:
                    msg += "SpaceType: None"
                logging.warning(msg)
        logging.info(f"Airflow objects updated: {spaces_processed['APP']} APPs, {spaces_processed['APT']} APTs, {spaces_processed['UNCLASSIFIED']} unclassified")
```

Depois (linhas 204 a 208)

```python
        """Applies outdoor air (APP) and crack infiltration through AirflowNetwork (all zones)."""
        self.remove_infiltration_objects(model)
        spaces_processed = self.update_outdoor_air(model)
        self.apply_airflow_network(model)
        logging.info(f"Outdoor air updated: {spaces_processed['APP']} APPs, {spaces_processed['APT']} APTs, {spaces_processed['UNCLASSIFIED']} unclassified")
```

---

Antes (linhas 71 a 73)

```python
        print(f" - APP: {spaces_processed['APP']} (infiltration + outdoor air)")
        print(f" - APT: {spaces_processed['APT']} (infiltration only)")
        print(f" - Unclassified: {spaces_processed['UNCLASSIFIED']} (no modifications)")
```

Depois (linhas 210 a 212)

```python
        print(f" - APP: {spaces_processed['APP']} (outdoor air {self.outdoor_air_per_person} m³/s per person)")
        print(f" - APT: {spaces_processed['APT']} (no outdoor air)")
        print(f" - Unclassified: {spaces_processed['UNCLASSIFIED']} (no outdoor air changes)")
```

---

Antes (linha 75)

```python
    def process_osm_file(self, osm_path, output_path):
```

Depois (linha 214)

```python
    def process_osm_file(self, osm_path, output_path, afn_only=False):
```

---

Antes (linha 87)

```python
            self.update_airflow_objects(model)
```

Depois (linhas 226 a 229)

```python
            if afn_only:
                self.apply_airflow_network(model)
            else:
                self.update_airflow_objects(model)
```

---

Antes (linhas 107 a 110)

```python
        print("Applies standardized airflow values to all spaces in OSM model:\n"
              "- APP: infiltration + outdoor air\n"
              "- APT: infiltration only\n")
        print(f"- Infiltration: {self.infiltration_ach} ACH")
```

Depois (linhas 249 a 251)

```python
        print("Applies airflow settings to all spaces in OSM model:\n"
              "- APP: outdoor air\n"
              "- All zones: closed windows and doors with crack infiltration (AirflowNetwork)\n")
```

---

Antes (linha 132)

```python
    def run_automated(self, osm_path, output_path):
```

Depois (linha 273)

```python
    def run_automated(self, osm_path, output_path, afn_only=False):
```

---

Antes (linha 134)

```python
        return self.process_osm_file(osm_path, output_path)
```

Depois (linha 275)

```python
        return self.process_osm_file(osm_path, output_path, afn_only)
```

---

Antes (linhas 139 a 141)

```python
    if len(args) == 2:
        # Automated mode: osm input, osm output
        success = assigner.run_automated(args[0], args[1])
```

Depois (linhas 280 a 283)

```python
    if len(args) in (2, 3):
        # Automated mode: osm input, osm output, optional afn_only (reapply crack infiltration after reference changes)
        afn_only = len(args) == 3 and args[2].lower() == "afn_only"
        success = assigner.run_automated(args[0], args[1], afn_only)
```

---

Antes (linha 150)

```python
        print("Usage: python script.py [osm_input osm_output] or run without arguments for GUI")
```

Depois (linha 292)

```python
        print("Usage: python script.py [osm_input osm_output [afn_only]] or run without arguments for GUI")
```

---

Antes (linhas 152 a 154)

```python
        print("This script applies standardized airflow values to all spaces according to occupancy type.")
        print("- APP: infiltration + outdoor air")
        print("- APT: infiltration only")
```

Depois (linha 294)

```python
        print("This script applies outdoor air to APP spaces and crack infiltration (AirflowNetwork, INI-C Table C.4) to all zones.")
```

---

## 06_ideal_loads_assigner.py

Motivo:

- Aquecimento (setpoint 21 °C) só fica ativo se o projeto tiver sistema de aquecimento (item C.I.6).
- O sistema ideal passa a usar o ar externo definido no script 05 (antes o objeto existia, mas não estava ligado ao Ideal Loads).

Antes (linha 12)

```python
    def __init__(self):
```

Depois (linha 12)

```python
    def __init__(self, heating_enabled=False):
```

---

Antes: nada (inserido após a linha 22)

Depois (linha 23)

```python
        self.heating_enabled = heating_enabled
```

---

Antes: nada (inserido após a linha 130)

Depois (linhas 132 a 138)

```python
            if not self.heating_enabled:
                ideal_loads.setHeatingAvailabilitySchedule(model.alwaysOffDiscreteSchedule())
            for space in zone.spaces():
                if space.designSpecificationOutdoorAir().is_initialized():
                    ideal_loads.setDesignSpecificationOutdoorAirObject(space.designSpecificationOutdoorAir().get())
                    ideal_loads.setDemandControlledVentilationType("OccupancySchedule")
                    break
```

---

Antes (linha 148)

```python
        print(f"  - Heating setpoint: {self.heating_setpoint}°C")
```

Depois (linha 156)

```python
        print(f"  - Heating setpoint: {self.heating_setpoint}°C ({'enabled' if self.heating_enabled else 'disabled, no heating system in project'})")
```

---

Antes (linha 227)

```python
    assigner = IdealLoadsAssigner()
```

Depois: removido

---

Antes: nada (inserido após a linha 228)

Depois (linhas 236 a 237)

```python
    heating_enabled = len(args) == 3 and args[2].lower() in ("heating", "1", "true", "yes")
    assigner = IdealLoadsAssigner(heating_enabled=heating_enabled)
```

---

Antes (linha 230)

```python
    if len(args) == 2:
```

Depois (linha 239)

```python
    if len(args) in (2, 3):
```

---

Antes (linha 243)

```python
        print("Usage: python script.py [osm_input osm_output] or run without arguments for GUI")
```

Depois (linha 252)

```python
        print("Usage: python script.py [osm_input osm_output [heating]] or run without arguments for GUI")
```

---

Antes: nada (inserido após a linha 245)

Depois (linha 255)

```python
        print("Heating is only enabled when the project has a heating system (third argument 'heating').")
```

---

## 08_construction_renamer.py

Motivo:

- Correção de bug: a expressão regular travava (backtracking exponencial) com nomes longos sem dois-pontos. O resultado é o mesmo para os nomes que já funcionavam.

Antes (linha 44)

```python
                cleaned_name = re.sub(r'^((\w+\s*)+):\s*', '', new_name)
```

Depois (linha 44)

```python
                cleaned_name = re.sub(r'^[\w\s]+:\s*', '', new_name)
```

---

## 09_surface_modifier.py

Motivo:

- As palavras-chave são testadas da mais longa para a mais curta, para que 'UndergroundCeiling' não seja confundido com 'Ceiling' (condição de contorno igual ao projeto, item C.I.3.2).

Antes (linha 62)

```python
            for type_key in self.surface_type_mapping.keys():
```

Depois (linha 62)

```python
            for type_key in sorted(self.surface_type_mapping.keys(), key=len, reverse=True):
```

---

## 10_air_boundary_assigner.py

Motivo:

- Espaços ligados por fronteira de ar passam a formar uma única zona térmica (item C.I.3.2: APT ligada a APP sem porta deve ser englobada na zona da APP). Antes, as zonas ficavam separadas com troca de ar de 1 ren/h.
- Reconhece também a ConstructionAirBoundary criada pelo próprio OpenStudio a partir de superfícies 'Air' do gbXML (antes só nomes com 'air').
- Correção de bug: a busca da construção existente nunca funcionava (to_ConstructionAirBoundary chamado em Construction).
- Remove construções vazias sem uso, que faziam o EnergyPlus parar com erro.

Antes: nada (inserido após a linha 8)

Depois (linhas 9 a 10)

```python
from spacetype_utils import get_space_type_label

```

---

Antes (linhas 11 a 13)

```python
    A class to automate the replacement of specific surface constructions with a
    "Default Air Boundary" construction in an OpenStudio model.
    Constructions whose names contain "Air" will be replaced.
```

Depois (linhas 13 a 15)

```python
    Identifies air boundary surfaces (ConstructionAirBoundary or constructions whose names contain "Air")
    and integrates the spaces connected by them into a single thermal zone, as required by INI-C item C.I.3.2
    (APT connected to APP without doors must be part of the APP thermal zone).
```

---

Antes (linha 25)

```python
            force=True # Adicionado force=True para garantir que este log seja usado
```

Depois (linha 27)

```python
            force=True
```

---

Antes (linhas 31 a 37)

```python
        Creates or retrieves a 'Default Air Boundary' construction with SimpleMixing.
        If an existing one is found but not configured for SimpleMixing with non-zero ACH,
        it will be reconfigured.
        Args:
            model (openstudio.model.Model): The OpenStudio model object.
        Returns:
            openstudio.model.ConstructionAirBoundary: The default air boundary construction.
```

Depois (linhas 33 a 34)

```python
        Creates or retrieves a 'Default Air Boundary' construction. Air exchange method is set to None
        because the connected spaces are integrated into the same thermal zone.
```

---

Antes (linhas 40 a 74)

```python
        default_ach_value = 1.0 # Default Air Changes per Hour for SimpleMixing. Adjust as needed.
        
        # Try to find an existing one by iterating through all constructions and casting
        for construction in model.getConstructions():
            # CORREÇÃO AQUI: Usar to_ConstructionAirBoundary()
            construction_ab_opt = construction.to_ConstructionAirBoundary() 
            if construction_ab_opt.is_initialized():
                construction_ab = construction_ab_opt.get()
                if construction_ab.nameString() == default_air_boundary_name:
                    self.logger.info(f"Found existing '{default_air_boundary_name}' construction.")
                    
                    # Check if it's configured correctly, or reconfigure if needed
                    needs_reconfiguration = False
                    if construction_ab.airExchangeMethod() != "SimpleMixing":
                        needs_reconfiguration = True
                    
                    # Check ACH value only if SimpleMixing is set
                    if construction_ab.airExchangeMethod() == "SimpleMixing":
                        if not construction_ab.simpleMixingAirChangesPerHour().is_initialized() or \
                           construction_ab.simpleMixingAirChangesPerHour().get_value_as_double() == 0.0:
                            needs_reconfiguration = True
                    else: # If not SimpleMixing, then the ACH value is irrelevant, but we want SimpleMixing
                        needs_reconfiguration = True

                    if needs_reconfiguration:
                        self.logger.warning(
                            f"Existing '{default_air_boundary_name}' found but not configured for "
                            f"SimpleMixing with non-zero ACH. Reconfiguring to {default_ach_value} ACH."
                        )
                        construction_ab.setAirExchangeMethod("SimpleMixing")
                        construction_ab.setSimpleMixingAirChangesPerHour(default_ach_value) 
                    
                    return construction_ab

        # If not found, create a new one
```

Depois (linhas 37 a 40)

```python
        for construction_ab in model.getConstructionAirBoundarys():
            if construction_ab.nameString() == default_air_boundary_name:
                self.logger.info(f"Found existing '{default_air_boundary_name}' construction.")
                return construction_ab
```

---

Antes (linhas 78 a 83)

```python
        air_boundary_construction.setAirExchangeMethod("SimpleMixing")
        air_boundary_construction.setSimpleMixingAirChangesPerHour(default_ach_value) 
        
        self.logger.info(
            f"'{default_air_boundary_name}' created and configured with SimpleMixing ({default_ach_value} ACH)."
        )
```

Depois (linha 44)

```python
        air_boundary_construction.setAirExchangeMethod("None")
```

---

Antes: nada (inserido após a linha 92)

Depois (linhas 54 a 66)

```python
    def _is_air_boundary(self, surface):
        construction_opt = surface.construction()
        if not construction_opt.is_initialized():
            return False
        construction = construction_opt.get()
        if construction.to_ConstructionAirBoundary().is_initialized():
            return True
        return "air" in construction.nameString().lower()

    def _zone_label(self, zone):
        labels = [get_space_type_label(space) for space in zone.spaces()]
        return "APP" if "APP" in labels else "APT"

```

---

Antes (linhas 95 a 100)

```python
        Iterates through surfaces and replaces constructions containing "Air" in their name
        with the 'Default Air Boundary' construction.
        Args:
            model (openstudio.model.Model): The OpenStudio model object to be modified.
        Returns:
            int: The number of surfaces whose constructions were modified.
```

Depois (linhas 69 a 70)

```python
        Assigns the air boundary construction to air surfaces and merges the thermal zones connected by them.
        Returns the number of surfaces converted to air boundary.
```

---

Antes: nada (inserido após a linha 103)

Depois (linhas 74 a 76)

```python
        default_air_boundary_construction = self._create_or_get_default_air_boundary_construction(model)

        air_surfaces = [s for s in surfaces if self._is_air_boundary(s)]
```

---

Antes (linhas 105 a 123)

```python

        default_air_boundary_construction = self._create_or_get_default_air_boundary_construction(model)
        
        for surface in surfaces:
            surface_name = surface.nameString()
            construction_opt = surface.construction()
            
            if not construction_opt.is_initialized():
                self.logger.warning(f"Surface '{surface_name}' has no construction assigned. Skipping.")
                continue

            current_construction = construction_opt.get()
            current_construction_name = current_construction.nameString()

            # Check if the construction name contains "Air" (case-insensitive)
            # and if it's not already the default air boundary construction
            if "air" in current_construction_name.lower() and \
               current_construction.handle() != default_air_boundary_construction.handle():
                
```

Depois (linhas 78 a 80)

```python
        for surface in air_surfaces:
            construction = surface.construction().get()
            if not construction.to_ConstructionAirBoundary().is_initialized():
```

---

Antes (linha 125)

```python
                    f"Surface '{surface_name}' has construction '{current_construction_name}' "
```

Depois (linha 82)

```python
                    f"Surface '{surface.nameString()}' has construction '{construction.nameString()}' "
```

---

Antes (linhas 130 a 136)

```python
            else:
                self.logger.debug(
                    f"Surface '{surface_name}' (Construction: '{current_construction_name}') "
                    f"does not require modification or is already the default air boundary."
                )
        
        self.logger.info(f"Finished: Constructions modified for {surfaces_modified_count} out of {len(surfaces)} surfaces.")
```

Depois (linhas 87 a 146)

```python
        for construction_ab in model.getConstructionAirBoundarys():
            construction_ab.setAirExchangeMethod("None")

        parent = {}

        def find(handle):
            while parent[handle] != handle:
                parent[handle] = parent[parent[handle]]
                handle = parent[handle]
            return handle

        zones = {str(z.handle()): z for z in model.getThermalZones()}
        for handle in zones:
            parent[handle] = handle
        for surface in air_surfaces:
            adjacent_opt = surface.adjacentSurface()
            space_opt = surface.space()
            if not adjacent_opt.is_initialized() or not space_opt.is_initialized():
                continue
            adjacent_space_opt = adjacent_opt.get().space()
            if not adjacent_space_opt.is_initialized():
                continue
            zone_a = space_opt.get().thermalZone()
            zone_b = adjacent_space_opt.get().thermalZone()
            if not zone_a.is_initialized() or not zone_b.is_initialized():
                continue
            root_a = find(str(zone_a.get().handle()))
            root_b = find(str(zone_b.get().handle()))
            if root_a != root_b:
                parent[root_b] = root_a

        groups = {}
        for handle in zones:
            groups.setdefault(find(handle), []).append(zones[handle])

        merged_zones = 0
        for group in groups.values():
            if len(group) < 2:
                continue
            group.sort(key=lambda z: (self._zone_label(z) == "APP", sum(sp.floorArea() for sp in z.spaces())), reverse=True)
            target = group[0]
            for zone in group[1:]:
                for space in zone.spaces():
                    space.setThermalZone(target)
                    self.logger.info(f"Space '{space.nameString()}' integrated into thermal zone '{target.nameString()}'.")
                zone.remove()
                merged_zones += 1

        used = set()
        for planar in list(model.getSurfaces()) + list(model.getSubSurfaces()) + list(model.getShadingSurfaces()):
            if planar.construction().is_initialized():
                used.add(str(planar.construction().get().handle()))
        for construction in model.getConstructions():
            if len(construction.layers()) == 0 and str(construction.handle()) not in used:
                self.logger.info(f"Removing empty unused construction '{construction.nameString()}'.")
                construction.remove()

        self.logger.info(f"Finished: {surfaces_modified_count} surfaces converted to air boundary, {merged_zones} thermal zones merged.")
        print(f"Air boundary surfaces: {len(air_surfaces)}")
        print(f"Thermal zones merged (INI-C C.I.3.2): {merged_zones}")
```

---

## 11_orchestrator.py

Motivo:

- Nova ordem: 00, 01, 02, 03, 04, 07, 08, 09, 10, 05, 06. O script 10 junta zonas e precisa rodar antes do ar externo, das frestas (05) e do sistema ideal (06). Os arquivos continuam numerados de step01 a step10.

Antes: nada (inserido após a linha 154)

Depois (linhas 155 a 174)

```python
            # Script 07: 07_plenum_disabler
            # Input: step04_osm_path, Output: step05_osm_path
            self._run_script("07_plenum_disabler.py", [step04_osm_path, step05_osm_path])
            logging.info(f"Script 07 completed. Output: {step05_osm_path}")

            # Script 08: 08_construction_renamer
            # Input: step05_osm_path, Output: step06_osm_path
            self._run_script("08_construction_renamer.py", [step05_osm_path, step06_osm_path])
            logging.info(f"Script 08 completed. Output: {step06_osm_path}")

            # Script 09: 09_surface_modifier
            # Input: step06_osm_path, Output: step07_osm_path
            self._run_script("09_surface_modifier.py", [step06_osm_path, step07_osm_path])
            logging.info(f"Script 09 completed. Output: {step07_osm_path}")

            # Script 10: 10_air_boundary_assigner (merges thermal zones, must run before 05 and 06)
            # Input: step07_osm_path, Output: step08_osm_path
            self._run_script("10_air_boundary_assigner.py", [step07_osm_path, step08_osm_path])
            logging.info(f"Script 10 completed. Output: {step08_osm_path}")

```

---

Antes (linhas 156 a 158)

```python
            # Input: step04_osm_path, Output: step05_osm_path
            self._run_script("05_airflow_assigner.py", [step04_osm_path, step05_osm_path])
            logging.info(f"Script 05 completed. Output: {step05_osm_path}")
```

Depois (linhas 176 a 178)

```python
            # Input: step08_osm_path, Output: step09_osm_path
            self._run_script("05_airflow_assigner.py", [step08_osm_path, step09_osm_path])
            logging.info(f"Script 05 completed. Output: {step09_osm_path}")
```

---

Antes (linhas 161 a 180)

```python
            # Input: step05_osm_path, Output: step06_osm_path
            self._run_script("06_ideal_loads_assigner.py", [step05_osm_path, step06_osm_path])
            logging.info(f"Script 06 completed. Output: {step06_osm_path}")

            # Script 07: 07_plenum_disabler
            # Input: step06_osm_path, Output: step07_osm_path
            self._run_script("07_plenum_disabler.py", [step06_osm_path, step07_osm_path])
            logging.info(f"Script 07 completed. Output: {step07_osm_path}")

            # Script 08: 08_construction_renamer
            # Input: step07_osm_path, Output: step08_osm_path
            self._run_script("08_construction_renamer.py", [step07_osm_path, step08_osm_path])
            logging.info(f"Script 08 completed. Output: {step08_osm_path}")

            # Script 09: 09_surface_modifier
            # Input: step08_osm_path, Output: step09_osm_path
            self._run_script("09_surface_modifier.py", [step08_osm_path, step09_osm_path])
            logging.info(f"Script 09 completed. Output: {step09_osm_path}")

            # Script 10: 10_air_boundary_assigner
```

Depois: removido

---

Antes (linhas 182 a 183)

```python
            self._run_script("10_air_boundary_assigner.py", [step09_osm_path, step10_osm_path])
            logging.info(f"Script 10 completed. Output: {step10_osm_path}")
```

Depois (linhas 182 a 183)

```python
            self._run_script("06_ideal_loads_assigner.py", [step09_osm_path, step10_osm_path])
            logging.info(f"Script 06 completed. Output: {step10_osm_path}")
```

---

## 12_run_simulation.py

Motivo:

- Chuva e neve do arquivo climático desconsideradas (item C.I.3.2).
- Saídas horárias (item C.I.7) e saída de ocupação das zonas (Zone People Occupant Count).
- Comando do OpenStudio passado como lista: funciona com espaços no caminho (problema que travava a simulação).
- A measure openstudio_results passa a ser opcional: sem a pasta measures, a simulação roda sem o relatório extra.

Antes: nada (inserido após a linha 10)

Depois (linha 11)

```python
REPORTING_FREQUENCY = "Hourly"
```

---

Antes: nada (inserido após a linha 38)

Depois (linhas 40 a 45)

```python
    measures_dir = Path('./measures').absolute()
    steps = []
    if (measures_dir / "openstudio_results").is_dir():
        steps.append({"measure_dir_name": "openstudio_results", "arguments": {}})
    else:
        print("Measure 'openstudio_results' not found in ./measures. Running without the report measure.")
```

---

Antes (linhas 43 a 49)

```python
        "measure_paths": [str(Path('./measures').absolute())], # Assumes 'measures' folder exists
        "steps": [
            {
                "measure_dir_name": "openstudio_results", # This measure must be available
                "arguments": {}
            }
        ]
```

Depois (linhas 50 a 51)

```python
        "measure_paths": [str(measures_dir)],
        "steps": steps
```

---

Antes (linhas 65 a 66)

```python
    cmd = f"openstudio run -w {osw_path}"
    print(f"Executing command: {cmd}")
```

Depois (linhas 67 a 68)

```python
    cmd = ["openstudio", "run", "-w", str(osw_path)]
    print(f"Executing command: {' '.join(cmd)}")
```

---

Antes (linha 109)

```python
        output_var.setReportingFrequency("Timestep")
```

Depois (linhas 111 a 118)

```python
        output_var.setReportingFrequency(REPORTING_FREQUENCY)

# Simulation settings required by INI-C (items C.I.3.2 and C.I.7)
def apply_inic_simulation_settings(model):
    run_period = model.getRunPeriod()
    run_period.setUseWeatherFileRainInd(False)
    run_period.setUseWeatherFileSnowInd(False)
    model.getTimestep().setNumberOfTimestepsPerHour(SIMULATION_TIMESTEPS_PER_HOUR)
```

---

Antes (linha 135)

```python
        "Zone Electric Equipment Electricity Energy"
```

Depois (linhas 144 a 145)

```python
        "Zone Electric Equipment Electricity Energy",
        "Zone People Occupant Count"
```

---

Antes (linha 144)

```python
        model.getTimestep().setNumberOfTimestepsPerHour(SIMULATION_TIMESTEPS_PER_HOUR)
```

Depois (linha 154)

```python
        apply_inic_simulation_settings(model)
```

---

## 13_eui_calculator.py

Motivo:

- Busca das variáveis independente da frequência (horária ou timestep).
- Aquecimento dividido pelo CEEA (1,72 + 0,5 x CEER, Equação C.I.8) e não pelo CEER.

Antes (linha 9)

```python
HVAC_REFERENCE_COP = 5.5 # Reference COP for HVAC (used to convert thermal load to electrical consumption)
```

Depois (linhas 9 a 10)

```python
HVAC_REFERENCE_COP = 5.5 # CEER of the real project system (used to convert cooling load to electrical consumption)
HVAC_HEATING_CEEA = 1.72 + 0.5 * HVAC_REFERENCE_COP # CEEA for split and window systems (INI-C Equation C.I.8)
```

---

Antes (linhas 106 a 109)

```python
        "Zone Lights Electricity Energy [J](TimeStep)": "Lighting Electricity",
        "Zone Electric Equipment Electricity Energy [J](TimeStep)": "Electric Equipment Electricity",
        "Zone Ideal Loads Supply Air Total Cooling Energy [J](TimeStep)": "Ideal Cooling (Electrical Input)",
        "Zone Ideal Loads Supply Air Total Heating Energy [J](TimeStep)": "Ideal Heating (Electrical Input)"
```

Depois (linhas 107 a 110)

```python
        "Zone Lights Electricity Energy [J]": "Lighting Electricity",
        "Zone Electric Equipment Electricity Energy [J]": "Electric Equipment Electricity",
        "Zone Ideal Loads Supply Air Total Cooling Energy [J]": "Ideal Cooling (Electrical Input)",
        "Zone Ideal Loads Supply Air Total Heating Energy [J]": "Ideal Heating (Electrical Input)"
```

---

Antes (linhas 143 a 144)

```python
                total_sum_kwh_electrical = total_sum_kwh_thermal / HVAC_REFERENCE_COP
                print(f"  - Applying COP of {HVAC_REFERENCE_COP:.2f} for '{search_string}'. Thermal energy: {total_sum_kwh_thermal:.2f} kWh -> Electrical energy: {total_sum_kwh_electrical:.2f} kWh")
```

Depois (linhas 144 a 146)

```python
                efficiency = HVAC_HEATING_CEEA if "Heating" in search_string else HVAC_REFERENCE_COP
                total_sum_kwh_electrical = total_sum_kwh_thermal / efficiency
                print(f"  - Applying efficiency of {efficiency:.2f} for '{search_string}'. Thermal energy: {total_sum_kwh_thermal:.2f} kWh -> Electrical energy: {total_sum_kwh_electrical:.2f} kWh")
```

---

## 14_a_redcep.py

Motivo:

- CEER de referência de 3,54 para 3,24 (Tabela A.2, Equações C.I.3 e C.I.4).
- RedCEP pela Equação 8.1: o consumo de equipamentos é descontado dos dois modelos.
- Aquecimento entra no CEP quando existir (CAE = CgTA / CEEA, Equações C.I.4 e C.I.8).
- Iluminação e equipamentos ajustados para 200 dias de ocupação (Tabela A.2 e Nota 1 do C.I.5); pessoas e climatização ficam com 260.
- Cálculo do RedCgTT (envoltória, Equação C.I.10).
- Busca das variáveis independente da frequência de saída.

Antes (linhas 13 a 14)

```python
COP_REAL_MODEL = 5.5  # COP for real model
COP_REFERENCE_MODEL = 3.54  # COP for reference model
```

Depois (linhas 13 a 24)

```python
COP_REAL_MODEL = 5.5  # CEER of the air conditioning system of the real project (Annex B.II)
COP_REFERENCE_MODEL = 3.24  # CEER and CEEA of the reference condition (Table A.2, Equations C.I.3 and C.I.4)
CEEA_REAL_MODEL = 1.72 + 0.5 * COP_REAL_MODEL  # Heating efficiency for split and window systems (Equation C.I.8)

# Days of occupation for lighting and equipment consumption (educational typology, Table A.2)
OCCUPATION_DAYS_LIGHTING_EQUIPMENT = 200

# Output variables (any reporting frequency)
VAR_COOLING = "Zone Ideal Loads Supply Air Total Cooling Energy [J]"
VAR_HEATING = "Zone Ideal Loads Supply Air Total Heating Energy [J]"
VAR_LIGHTING = "Zone Lights Electricity Energy [J]"
VAR_EQUIPMENT = "Zone Electric Equipment Electricity Energy [J]"
```

---

Antes (linha 86)

```python
def calculate_eui(csv_path: Path, areas: dict, hvac_cop: float, primary_energy_factor: float) -> dict:
```

Depois (linhas 96 a 113)

```python
def _sum_columns(df, search_string):
    columns = [col for col in df.columns if search_string in col]
    if not columns:
        return 0.0, 0
    return float(df[columns].sum().sum()), len(columns)

def _simulated_occupied_days(df):
    """Counts the days with lighting or equipment consumption in the simulation output."""
    if "Date/Time" not in df.columns:
        return 0
    columns = [col for col in df.columns if VAR_LIGHTING in col or VAR_EQUIPMENT in col]
    if not columns:
        return 0
    daily = df[columns].sum(axis=1)
    dates = df["Date/Time"].astype(str).str.strip().str.split().str[0]
    return int(dates[daily > 0].nunique())

def calculate_consumption(csv_path: Path, ceer: float, ceea: float) -> dict:
```

---

Antes (linha 88)

```python
    Calculates EUI for a single model with specified COP.
```

Depois (linhas 115 a 117)

```python
    Calculates annual thermal loads and electricity consumption of one model (kWh/year), as described in Annex C.I.7.
    Cooling and heating consumption are the ideal thermal loads divided by CEER and CEEA.
    Lighting and equipment consumption are scaled to the days of occupation of the typology.
```

---

Antes (linhas 96 a 121)

```python
    
    net_conditioned_area = areas.get('conditioned')
    total_building_area = areas.get('total')
    
    # Validate areas
    if (net_conditioned_area is None or net_conditioned_area <= 0) and \
       (total_building_area is None or total_building_area <= 0):
        print("Error: No valid building area found.")
        return None
    
    # Define areas with fallbacks
    area_for_ideal_loads = net_conditioned_area if net_conditioned_area and net_conditioned_area > 0 else total_building_area
    area_for_lighting_equipment = total_building_area if total_building_area and total_building_area > 0 else net_conditioned_area
    
    if not area_for_ideal_loads or area_for_ideal_loads <= 0:
        print("Error: No valid area for HVAC calculations.")
        return None
    if not area_for_lighting_equipment or area_for_lighting_equipment <= 0:
        print("Error: No valid area for Lighting/Equipment calculations.")
        return None
    
    # Define output variables to search for
    output_variable_map = {
        "Zone Lights Electricity Energy [J](TimeStep)": "Lighting Electricity",
        "Zone Electric Equipment Electricity Energy [J](TimeStep)": "Electric Equipment Electricity",
        "Zone Ideal Loads Supply Air Total Cooling Energy [J](TimeStep)": "Ideal Cooling (Electrical Input)"
```

Depois (linhas 125 a 149)

```python

    cooling_j, n_cool = _sum_columns(df, VAR_COOLING)
    heating_j, _ = _sum_columns(df, VAR_HEATING)
    lighting_j, _ = _sum_columns(df, VAR_LIGHTING)
    equipment_j, _ = _sum_columns(df, VAR_EQUIPMENT)
    if n_cool == 0:
        print("Warning: no ideal loads cooling columns found in the CSV file.")

    simulated_days = _simulated_occupied_days(df)
    days_factor = OCCUPATION_DAYS_LIGHTING_EQUIPMENT / simulated_days if simulated_days > 0 else 1.0

    cgtr = cooling_j / JOULES_TO_KWH
    cgta = heating_j / JOULES_TO_KWH
    results = {
        "cgtr": cgtr,
        "cgta": cgta,
        "cgtt": cgtr + cgta,
        "cr": cgtr / ceer,
        "cae": cgta / ceea if cgta > 0 else 0.0,
        "cil": lighting_j / JOULES_TO_KWH * days_factor,
        "ceq": equipment_j / JOULES_TO_KWH * days_factor,
        "simulated_days": simulated_days,
        "days_factor": days_factor,
        "ceer": ceer,
        "ceea": ceea,
```

---

Antes (linhas 123 a 160)

```python
    
    eui_results = {}
    
    # Process each output variable
    for search_string, display_name_base in output_variable_map.items():
        matching_columns = [col for col in df.columns if search_string in col]
        
        # Determine which area to use
        if "Ideal Loads" in search_string:
            current_area_m2 = area_for_ideal_loads
        else:
            current_area_m2 = area_for_lighting_equipment
        
        if matching_columns:
            total_sum_joules = df[matching_columns].sum().sum()
            
            # Convert based on variable type
            if "Electricity Energy" in search_string:
                # Direct electrical energy
                total_sum_kwh_electrical = total_sum_joules / JOULES_TO_KWH
            elif "Ideal Loads" in search_string:
                # Thermal energy - apply COP
                total_sum_kwh_thermal = total_sum_joules / JOULES_TO_KWH
                total_sum_kwh_electrical = total_sum_kwh_thermal / hvac_cop
            else:
                total_sum_kwh_electrical = 0
            
            site_eui = total_sum_kwh_electrical / current_area_m2
            primary_eui = site_eui * primary_energy_factor
            
            eui_results[f"{display_name_base} Site EUI"] = site_eui
            eui_results[f"{display_name_base} Primary EUI"] = primary_eui
            
        else:
            eui_results[f"{display_name_base} Site EUI"] = 0.0
            eui_results[f"{display_name_base} Primary EUI"] = 0.0
    
    return eui_results
```

Depois (linhas 151 a 153)

```python
    results["cee"] = results["cr"] + results["cae"] + results["cil"] + results["ceq"]
    results["cep"] = results["cee"] * PRIMARY_ENERGY_FACTOR_BRAZIL
    return results
```

---

Antes (linha 162)

```python
def calculate_cep_and_redcep(real_eui: dict, ref_eui: dict, real_areas: dict, ref_areas: dict) -> dict:
```

Depois (linha 155)

```python
def calculate_cep_and_redcep(real: dict, ref: dict, real_areas: dict = None, ref_areas: dict = None) -> dict:
```

---

Antes (linha 164)

```python
    Calculates CEP (Primary Energy Consumption) and RedCEP for INI-C classification.
```

Depois (linhas 157 a 158)

```python
    Calculates CEP (Equations 8.2 and 8.3), RedCEP (Equation 8.1) and RedCgTT (Equation C.I.10).
    Equipment consumption is removed from both models in RedCEP, as required by Equation 8.1.
```

---

Antes (linhas 166 a 212)

```python
    results = {}
    
    # Get areas (use conditioned for HVAC, total for lighting/equipment)
    real_hvac_area = real_areas.get('conditioned') or real_areas.get('total')
    real_total_area = real_areas.get('total') or real_areas.get('conditioned')
    ref_hvac_area = ref_areas.get('conditioned') or ref_areas.get('total')
    ref_total_area = ref_areas.get('total') or ref_areas.get('conditioned')
    
    # Calculate CEP components for real model (kWh/year)
    real_cooling_cep = real_eui.get("Ideal Cooling (Electrical Input) Primary EUI", 0) * real_hvac_area
    real_lighting_cep = real_eui.get("Lighting Electricity Primary EUI", 0) * real_total_area
    real_equipment_cep = real_eui.get("Electric Equipment Electricity Primary EUI", 0) * real_total_area
    real_total_cep = real_cooling_cep + real_lighting_cep + real_equipment_cep
    
    # Calculate CEP components for reference model (kWh/year)
    ref_cooling_cep = ref_eui.get("Ideal Cooling (Electrical Input) Primary EUI", 0) * ref_hvac_area
    ref_lighting_cep = ref_eui.get("Lighting Electricity Primary EUI", 0) * ref_total_area
    ref_equipment_cep = ref_eui.get("Electric Equipment Electricity Primary EUI", 0) * ref_total_area
    ref_total_cep = ref_cooling_cep + ref_lighting_cep + ref_equipment_cep
    
    # Calculate RedCEP
    if ref_total_cep > 0:
        redcep = ((ref_total_cep - real_total_cep) / ref_total_cep) * 100
    else:
        redcep = 0
    
    # Store results
    results = {
        'real_model': {
            'cooling_cep': real_cooling_cep,
            'lighting_cep': real_lighting_cep,
            'equipment_cep': real_equipment_cep,
            'total_cep': real_total_cep,
            'hvac_area': real_hvac_area,
            'total_area': real_total_area
        },
        'reference_model': {
            'cooling_cep': ref_cooling_cep,
            'lighting_cep': ref_lighting_cep,
            'equipment_cep': ref_equipment_cep,
            'total_cep': ref_total_cep,
            'hvac_area': ref_hvac_area,
            'total_area': ref_total_area
        },
        'redcep': redcep
    }
    
```

Depois (linhas 160 a 175)

```python
    fce = PRIMARY_ENERGY_FACTOR_BRAZIL
    ref_without_eq = ref["cep"] - ref["ceq"] * fce
    real_without_eq = real["cep"] - real["ceq"] * fce
    redcep = ((ref_without_eq - real_without_eq) / ref_without_eq) * 100 if ref_without_eq > 0 else 0.0
    redcgtt = ((ref["cgtt"] - real["cgtt"]) / ref["cgtt"]) * 100 if ref["cgtt"] > 0 else 0.0

    results = {"real_model": dict(real), "reference_model": dict(ref), "redcep": redcep, "redcgtt": redcgtt}
    for key, model_results, areas in (("real_model", real, real_areas), ("reference_model", ref, ref_areas)):
        total_area = (areas or {}).get("total") or (areas or {}).get("conditioned")
        results[key]["total_area"] = total_area
        results[key]["conditioned_area"] = (areas or {}).get("conditioned")
        if total_area:
            results[key]["cooling_eui"] = (model_results["cr"] + model_results["cae"]) * fce / total_area
            results[key]["lighting_eui"] = model_results["cil"] * fce / total_area
            results[key]["equipment_eui"] = model_results["ceq"] * fce / total_area
            results[key]["total_eui"] = model_results["cep"] / total_area
```

---

Antes (linhas 242 a 243)

```python
        print(f"Real Model Areas - Conditioned: {real_areas['conditioned']:.2f} m², Total: {real_areas['total']:.2f} m²")
        print(f"Reference Model Areas - Conditioned: {ref_areas['conditioned']:.2f} m², Total: {ref_areas['total']:.2f} m²")
```

Depois (linhas 205 a 207)

```python
        # Calculate consumption for both models
        print(f"\nCalculating consumption for Real Model (CEER = {COP_REAL_MODEL}, CEEA = {CEEA_REAL_MODEL:.2f})...")
        real = calculate_consumption(real_csv, COP_REAL_MODEL, CEEA_REAL_MODEL)
```

---

Antes (linhas 245 a 247)

```python
        # Calculate EUI for both models
        print(f"\nCalculating EUI for Real Model (COP = {COP_REAL_MODEL})...")
        real_eui = calculate_eui(real_csv, real_areas, COP_REAL_MODEL, PRIMARY_ENERGY_FACTOR_BRAZIL)
```

Depois (linhas 209 a 210)

```python
        print(f"\nCalculating consumption for Reference Model (CEER = CEEA = {COP_REFERENCE_MODEL})...")
        ref = calculate_consumption(ref_csv, COP_REFERENCE_MODEL, COP_REFERENCE_MODEL)
```

---

Antes (linhas 249 a 253)

```python
        print(f"\nCalculating EUI for Reference Model (COP = {COP_REFERENCE_MODEL})...")
        ref_eui = calculate_eui(ref_csv, ref_areas, COP_REFERENCE_MODEL, PRIMARY_ENERGY_FACTOR_BRAZIL)
        
        if not real_eui or not ref_eui:
            print("Error: Could not calculate EUI for one or both models.")
```

Depois (linhas 212 a 213)

```python
        if not real or not ref:
            print("Error: Could not calculate consumption for one or both models.")
```

---

Antes (linha 258)

```python
        cep_results = calculate_cep_and_redcep(real_eui, ref_eui, real_areas, ref_areas)
```

Depois (linha 218)

```python
        cep_results = calculate_cep_and_redcep(real, ref, real_areas, ref_areas)
```

---

Antes (linhas 265 a 279)

```python
        print(f"\nREAL MODEL:")
        print(f"  COP Used: {COP_REAL_MODEL}")
        print(f"  Areas Used - HVAC: {cep_results['real_model']['hvac_area']:.2f} m², Others: {cep_results['real_model']['total_area']:.2f} m²")
        print(f"  Cooling CEP:    {cep_results['real_model']['cooling_cep']:,.0f} kWh/year")
        print(f"  Lighting CEP:   {cep_results['real_model']['lighting_cep']:,.0f} kWh/year")
        print(f"  Equipment CEP:  {cep_results['real_model']['equipment_cep']:,.0f} kWh/year")
        print(f"  TOTAL CEP:      {cep_results['real_model']['total_cep']:,.0f} kWh/year")
        
        print(f"\nREFERENCE MODEL:")
        print(f"  COP Used: {COP_REFERENCE_MODEL}")
        print(f"  Areas Used - HVAC: {cep_results['reference_model']['hvac_area']:.2f} m², Others: {cep_results['reference_model']['total_area']:.2f} m²")
        print(f"  Cooling CEP:    {cep_results['reference_model']['cooling_cep']:,.0f} kWh/year")
        print(f"  Lighting CEP:   {cep_results['reference_model']['lighting_cep']:,.0f} kWh/year")
        print(f"  Equipment CEP:  {cep_results['reference_model']['equipment_cep']:,.0f} kWh/year")
        print(f"  TOTAL CEP:      {cep_results['reference_model']['total_cep']:,.0f} kWh/year")
```

Depois (linhas 225 a 236)

```python
        for label, key in (("REAL MODEL", "real_model"), ("REFERENCE MODEL", "reference_model")):
            r = cep_results[key]
            print(f"\n{label}:")
            print(f"  CEER: {r['ceer']:.2f}  CEEA: {r['ceea']:.2f}")
            print(f"  Cooling load (CgTR):   {r['cgtr']:,.0f} kWh/year")
            print(f"  Heating load (CgTA):   {r['cgta']:,.0f} kWh/year")
            print(f"  Cooling (CR):          {r['cr']:,.0f} kWh/year")
            print(f"  Heating (CAE):         {r['cae']:,.0f} kWh/year")
            print(f"  Lighting (CIL):        {r['cil']:,.0f} kWh/year")
            print(f"  Equipment (CEQ):       {r['ceq']:,.0f} kWh/year")
            print(f"  TOTAL CEP:             {r['cep']:,.0f} kWh/year (primary energy)")
            print(f"  Lighting and equipment days: {OCCUPATION_DAYS_LIGHTING_EQUIPMENT} (simulated: {r['simulated_days']})")
```

---

Antes (linha 282)

```python
        print(f"  RedCEP = {cep_results['redcep']:.1f}%")
```

Depois (linhas 239 a 240)

```python
        print(f"  RedCEP = {cep_results['redcep']:.1f}%  (Equation 8.1, equipment consumption excluded)")
        print(f"  RedCgTT = {cep_results['redcgtt']:.1f}%  (envelope, Equation C.I.10)")
```

---

## 14_a_prpec.py

Motivo:

- Mesmas correções do 14_a_redcep (usa o mesmo cálculo, importado do 14_a_redcep).
- Remoção de comentários explicativos genéricos e dos símbolos de status.

Antes: nada (inserido após a linha 6)

Depois (linha 7)

```python
import sys
```

---

Antes: nada (inserido após a linha 7)

Depois (linhas 9 a 11)

```python
import importlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

---

Antes (linhas 14 a 15)

```python
COP_REAL_MODEL = 5.5  # COP for real model
COP_REFERENCE_MODEL = 3.54  # COP for reference model
```

Depois (linhas 18 a 23)

```python
COP_REAL_MODEL = 5.5  # CEER of the air conditioning system of the real project (Annex B.II)
COP_REFERENCE_MODEL = 3.24  # CEER and CEEA of the reference condition (Table A.2, Equations C.I.3 and C.I.4)
CEEA_REAL_MODEL = 1.72 + 0.5 * COP_REAL_MODEL  # Heating efficiency for split and window systems (Equation C.I.8)

# Shared INI-C calculation (Equations 8.1 to 8.3 and C.I.3 to C.I.12)
_redcep = importlib.import_module("14_a_redcep")
```

---

Antes (linha 88)

```python
def calculate_eui(csv_path: Path, areas: dict, hvac_cop: float, primary_energy_factor: float) -> dict:
```

Depois (linha 96)

```python
def calculate_pec_and_prpec(real: dict, ref: dict, real_areas: dict, ref_areas: dict) -> dict:
```

---

Antes (linha 90)

```python
    Calculates EUI for a single model with specified COP.
```

Depois (linha 98)

```python
    Calculates CEP and PRPEC (RedCEP, Equation 8.1) for INI-C classification and formats the results for the GUI.
```

---

Antes (linhas 92 a 235)

```python
    print(f"Reading file: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")
        return None
    
    net_conditioned_area = areas.get('conditioned')
    total_building_area = areas.get('total')
    
    # Validate areas
    if (net_conditioned_area is None or net_conditioned_area <= 0) and \
       (total_building_area is None or total_building_area <= 0):
        print("Error: No valid building area found.")
        return None
    
    # Define areas with fallbacks
    area_for_ideal_loads = net_conditioned_area if net_conditioned_area and net_conditioned_area > 0 else total_building_area
    area_for_lighting_equipment = total_building_area if total_building_area and total_building_area > 0 else net_conditioned_area
    
    if not area_for_ideal_loads or area_for_ideal_loads <= 0:
        print("Error: No valid area for HVAC calculations.")
        return None
    
    if not area_for_lighting_equipment or area_for_lighting_equipment <= 0:
        print("Error: No valid area for Lighting/Equipment calculations.")
        return None
    
    # Define output variables to search for
    output_variable_map = {
        "Zone Lights Electricity Energy [J](TimeStep)": "Lighting Electricity",
        "Zone Electric Equipment Electricity Energy [J](TimeStep)": "Electric Equipment Electricity",
        "Zone Ideal Loads Supply Air Total Cooling Energy [J](TimeStep)": "Ideal Cooling (Electrical Input)"
    }
    
    eui_results = {}
    
    # Process each output variable
    for search_string, display_name_base in output_variable_map.items():
        matching_columns = [col for col in df.columns if search_string in col]
        
        # Determine which area to use
        if "Ideal Loads" in search_string:
            current_area_m2 = area_for_ideal_loads
        else:
            current_area_m2 = area_for_lighting_equipment
        
        if matching_columns:
            total_sum_joules = df[matching_columns].sum().sum()
            
            # Convert based on variable type
            if "Electricity Energy" in search_string:
                # Direct electrical energy
                total_sum_kwh_electrical = total_sum_joules / JOULES_TO_KWH
            elif "Ideal Loads" in search_string:
                # Thermal energy - apply COP
                total_sum_kwh_thermal = total_sum_joules / JOULES_TO_KWH
                total_sum_kwh_electrical = total_sum_kwh_thermal / hvac_cop
            else:
                total_sum_kwh_electrical = 0
            
            site_eui = total_sum_kwh_electrical / current_area_m2
            primary_eui = site_eui * primary_energy_factor
            
            eui_results[f"{display_name_base} Site EUI"] = site_eui
            eui_results[f"{display_name_base} Primary EUI"] = primary_eui
        else:
            eui_results[f"{display_name_base} Site EUI"] = 0.0
            eui_results[f"{display_name_base} Primary EUI"] = 0.0
    
    return eui_results

def calculate_pec_and_prpec(real_eui: dict, ref_eui: dict, real_areas: dict, ref_areas: dict) -> dict:
    """
    Calculates PEC (Primary Energy Consumption) and PRPEC for INI-C classification.
    """
    results = {}
    
    # Get areas (use conditioned for HVAC, total for lighting/equipment)
    real_hvac_area = real_areas.get('conditioned') or real_areas.get('total')
    real_total_area = real_areas.get('total') or real_areas.get('conditioned')
    ref_hvac_area = ref_areas.get('conditioned') or ref_areas.get('total')
    ref_total_area = ref_areas.get('total') or ref_areas.get('conditioned')
    
    # Calculate PEC EUI components for real model (kWh/m²/year)
    real_cooling_eui = real_eui.get("Ideal Cooling (Electrical Input) Primary EUI", 0)
    real_lighting_eui = real_eui.get("Lighting Electricity Primary EUI", 0)
    real_equipment_eui = real_eui.get("Electric Equipment Electricity Primary EUI", 0)
    
    # Calculate PEC EUI components for reference model (kWh/m²/year)
    ref_cooling_eui = ref_eui.get("Ideal Cooling (Electrical Input) Primary EUI", 0)
    ref_lighting_eui = ref_eui.get("Lighting Electricity Primary EUI", 0)
    ref_equipment_eui = ref_eui.get("Electric Equipment Electricity Primary EUI", 0)
    
    # Calculate total PEC (kWh/year) for PRPEC calculation
    real_cooling_pec = real_cooling_eui * real_hvac_area
    real_lighting_pec = real_lighting_eui * real_total_area
    real_equipment_pec = real_equipment_eui * real_total_area
    real_total_pec = real_cooling_pec + real_lighting_pec + real_equipment_pec
    
    ref_cooling_pec = ref_cooling_eui * ref_hvac_area
    ref_lighting_pec = ref_lighting_eui * ref_total_area
    ref_equipment_pec = ref_equipment_eui * ref_total_area
    ref_total_pec = ref_cooling_pec + ref_lighting_pec + ref_equipment_pec
    
    # Calculate total EUI based on total building area
    real_total_eui = real_total_pec / real_total_area if real_total_area > 0 else 0
    ref_total_eui = ref_total_pec / ref_total_area if ref_total_area > 0 else 0
    
    # Calculate PRPEC (Primary Reduction of Primary Energy Consumption)
    if ref_total_pec > 0:
        prpec = ((ref_total_pec - real_total_pec) / ref_total_pec) * 100
    else:
        prpec = 0
    
    # Store results
    results = {
        'real_model': {
            'cooling_eui': real_cooling_eui,
            'lighting_eui': real_lighting_eui,
            'equipment_eui': real_equipment_eui,
            'total_eui': real_total_eui,
            'cooling_pec': real_cooling_pec,
            'lighting_pec': real_lighting_pec,
            'equipment_pec': real_equipment_pec,
            'total_pec': real_total_pec,
            'hvac_area': real_hvac_area,
            'total_area': real_total_area
        },
        'reference_model': {
            'cooling_eui': ref_cooling_eui,
            'lighting_eui': ref_lighting_eui,
            'equipment_eui': ref_equipment_eui,
            'total_eui': ref_total_eui,
            'cooling_pec': ref_cooling_pec,
            'lighting_pec': ref_lighting_pec,
            'equipment_pec': ref_equipment_pec,
            'total_pec': ref_total_pec,
            'hvac_area': ref_hvac_area,
            'total_area': ref_total_area
        },
        'prpec': prpec
    }
    
```

Depois (linhas 100 a 117)

```python
    shared = _redcep.calculate_cep_and_redcep(real, ref, real_areas, ref_areas)
    results = {'prpec': shared['redcep'], 'redcgtt': shared['redcgtt']}
    for key in ('real_model', 'reference_model'):
        r = shared[key]
        total_area = r.get('total_area') or 0
        fce = PRIMARY_ENERGY_FACTOR_BRAZIL
        results[key] = {
            'cooling_eui': r.get('cooling_eui', 0.0),
            'lighting_eui': r.get('lighting_eui', 0.0),
            'equipment_eui': r.get('equipment_eui', 0.0),
            'total_eui': r.get('total_eui', 0.0),
            'cooling_pec': (r['cr'] + r['cae']) * fce,
            'lighting_pec': r['cil'] * fce,
            'equipment_pec': r['ceq'] * fce,
            'total_pec': r['cep'],
            'hvac_area': total_area,
            'total_area': total_area
        }
```

---

Antes (linha 274)

```python
        status_icon = "✓"
```

Depois (linha 156)

```python
        status_icon = "+"
```

---

Antes (linha 278)

```python
        status_icon = "✗"
```

Depois (linha 160)

```python
        status_icon = "-"
```

---

Antes (linhas 705 a 706)

```python
    • Cooling EUI uses conditioned area, Lighting & Equipment use total building area
    • TOTAL EUI uses total building area for standardized comparison
```

Depois (linhas 587 a 588)

```python
    • PRPEC follows INI-C Equation 8.1: equipment consumption is excluded from both models
    • All EUI values use total building area
```

---

Antes (linhas 726 a 731)

```python
    # NEW: Configure the logging system to save to a file.
    # - level=logging.INFO: Captures informational, warning, and error messages.
    # - format: Defines the format for each log entry (timestamp - level - message).
    # - filename: The name of the log file.
    # - filemode='a': 'append' mode. Each new run adds to the end of the file.
    #                 Use 'w' (write) if you want the file to be overwritten each time.
```

Depois: removido

---

Antes (linha 750)

```python
        logging.info(f"Real Model folder selected: {real_folder}") # NEW: Log the selected folder
```

Depois (linha 626)

```python
        logging.info(f"Real Model folder selected: {real_folder}")
```

---

Antes (linha 754)

```python
        logging.info(f"Reference Model folder selected: {ref_folder}") # NEW: Log the selected folder
```

Depois (linha 630)

```python
        logging.info(f"Reference Model folder selected: {ref_folder}")
```

---

Antes (linha 758)

```python
        logging.info("Processing files...") # NEW: Log this step
```

Depois (linha 634)

```python
        logging.info("Processing files...")
```

---

Antes (linha 763)

```python
        logging.info(f"Real Model Files Found: {real_csv.name}, {real_html.name}") # NEW: Log the found files
```

Depois (linha 639)

```python
        logging.info(f"Real Model Files Found: {real_csv.name}, {real_html.name}")
```

---

Antes (linha 766)

```python
        logging.info(f"Reference Model Files Found: {ref_csv.name}, {ref_html.name}") # NEW: Log the found files
```

Depois (linha 642)

```python
        logging.info(f"Reference Model Files Found: {ref_csv.name}, {ref_html.name}")
```

---

Antes (linha 770)

```python
        logging.info("Extracting building areas...") # NEW: Log this step
```

Depois (linha 646)

```python
        logging.info("Extracting building areas...")
```

---

Antes (linhas 773 a 774)

```python
        logging.info(f"Real Model Areas: {real_areas}") # NEW: Log the extracted areas
        logging.info(f"Reference Model Areas: {ref_areas}") # NEW: Log the extracted areas
```

Depois (linhas 649 a 650)

```python
        logging.info(f"Real Model Areas: {real_areas}")
        logging.info(f"Reference Model Areas: {ref_areas}")
```

---

Antes (linhas 777 a 779)

```python
        print(f"\nCalculating EUI for Real Model (COP = {COP_REAL_MODEL})...")
        logging.info(f"Calculating EUI for Real Model (COP = {COP_REAL_MODEL})...") # NEW: Log this step
        real_eui = calculate_eui(real_csv, real_areas, COP_REAL_MODEL, PRIMARY_ENERGY_FACTOR_BRAZIL)
```

Depois (linhas 653 a 655)

```python
        print(f"\nCalculating consumption for Real Model (CEER = {COP_REAL_MODEL})...")
        logging.info(f"Calculating consumption for Real Model (CEER = {COP_REAL_MODEL})...")
        real_eui = _redcep.calculate_consumption(real_csv, COP_REAL_MODEL, CEEA_REAL_MODEL)
```

---

Antes (linhas 781 a 783)

```python
        print(f"\nCalculating EUI for Reference Model (COP = {COP_REFERENCE_MODEL})...")
        logging.info(f"Calculating EUI for Reference Model (COP = {COP_REFERENCE_MODEL})...") # NEW: Log this step
        ref_eui = calculate_eui(ref_csv, ref_areas, COP_REFERENCE_MODEL, PRIMARY_ENERGY_FACTOR_BRAZIL)
```

Depois (linhas 657 a 659)

```python
        print(f"\nCalculating consumption for Reference Model (CEER = {COP_REFERENCE_MODEL})...")
        logging.info(f"Calculating consumption for Reference Model (CEER = {COP_REFERENCE_MODEL})...")
        ref_eui = _redcep.calculate_consumption(ref_csv, COP_REFERENCE_MODEL, COP_REFERENCE_MODEL)
```

---

Antes (linha 788)

```python
            logging.error(message) # NEW: Log the error
```

Depois (linha 664)

```python
            logging.error(message)
```

---

Antes (linha 793)

```python
        logging.info("Calculating PEC and PRPEC...") # NEW: Log this step
```

Depois (linha 669)

```python
        logging.info("Calculating PEC and PRPEC...")
```

---

Antes (linha 795)

```python
        logging.info(f"Final PRPEC result: {pec_results.get('prpec', 'N/A'):.2f}%") # NEW: Log the main result
```

Depois (linha 671)

```python
        logging.info(f"Final PRPEC result: {pec_results.get('prpec', 'N/A'):.2f}%")
```

---

Antes (linha 799)

```python
        logging.info("Opening results GUI window...") # NEW: Log this step
```

Depois (linha 675)

```python
        logging.info("Opening results GUI window...")
```

---

Antes (linhas 803 a 804)

```python
        logging.info("Script completed successfully!") # NEW: Log the successful completion
        logging.info("-" * 50 + "\n") # NEW: Add a separator for the next run
```

Depois (linhas 679 a 680)

```python
        logging.info("Script completed successfully!")
        logging.info("-" * 50 + "\n")
```

---

Antes (linha 808)

```python
        logging.error(f"File Not Found Error: {e}") # NEW: Log the specific error
```

Depois (linha 684)

```python
        logging.error(f"File Not Found Error: {e}")
```

---

Antes (linha 816)

```python
        # NEW: Log the unexpected error with the full traceback for easier debugging
```

Depois: removido

---

## 14_b_crcepd-a.py

Motivo:

- Arquivo reescrito. A versão da INI-C (Portaria 309/2022 consolidada) não usa mais fator de forma: o CRCEPD-A vem da Tabela 8.3 por tipologia e zona bioclimática da ABNT NBR 15220-3 (1R e 1M até 6A e 6B).
- Educacionais: 0,56 / 0,48 / 0,51 / 0,43 / 0,33 / 0,32. Inclui também o CRCgTTD-A da envoltória (Tabela 8.5): 0,25 / 0,18 / 0,15 / 0,09 / 0,07 / 0,07.
- Não precisa mais do eplustbl.htm (Aenv e Vtot não são usados).

Antes: nada (inserido após a linha 0)

Depois (linhas 1 a 3)

```python
import sys
import logging
from pathlib import Path
```

---

Antes (linhas 2 a 7)

```python
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from bs4 import BeautifulSoup
import re
import logging
```

Depois: removido

---

Antes (linha 10)

```python
BIOCLIMATIC_ZONE = 3 # USER: Change this value to your bioclimatic zone (1-8)
```

Depois (linhas 7 a 8)

```python
BIOCLIMATIC_ZONE = "3A e 3B" # USER: Change this value to your bioclimatic zone (ABNT NBR 15220-3): "1R e 1M", "2R e 2M", "3A e 3B", "4A e 4B", "5A e 5B" or "6A e 6B"
TYPOLOGY = "Educacionais"
```

---

Antes (linha 13)

```python
AENV_CONSTRUCTION_TERMS = ['EXTERIORWALL', 'ROOF', 'RAISEDFLOOR'] # Valid construction terms for envelope area
```

Depois (linha 11)

```python
BIOCLIMATIC_ZONES = ["1R e 1M", "2R e 2M", "3A e 3B", "4A e 4B", "5A e 5B", "6A e 6B"]
```

---

Antes (linha 15)

```python
# CRCEPD-A Table (Zona Bioclimática vs Form Factor)
```

Depois (linha 13)

```python
# CRCEPD-A Table 8.3 (Tipologia vs Zona Bioclimática)
```

---

Antes (linhas 17 a 24)

```python
    1: {0.20: 0.33, 0.30: 0.34, 0.40: 0.31, 0.50: 0.30},
    2: {0.20: 0.32, 0.30: 0.33, 0.40: 0.30, 0.50: 0.28},
    3: {0.20: 0.31, 0.30: 0.32, 0.40: 0.30, 0.50: 0.28},
    4: {0.20: 0.30, 0.30: 0.31, 0.40: 0.29, 0.50: 0.27},
    5: {0.20: 0.31, 0.30: 0.33, 0.40: 0.31, 0.50: 0.29},
    6: {0.20: 0.31, 0.30: 0.32, 0.40: 0.30, 0.50: 0.28},
    7: {0.20: 0.28, 0.30: 0.30, 0.40: 0.28, 0.50: 0.26},
    8: {0.20: 0.28, 0.30: 0.30, 0.40: 0.28, 0.50: 0.27}
```

Depois (linhas 15 a 20)

```python
    "Educacionais": {"1R e 1M": 0.56, "2R e 2M": 0.48, "3A e 3B": 0.51, "4A e 4B": 0.43, "5A e 5B": 0.33, "6A e 6B": 0.32}
}

# CRCgTTD-A Table 8.5 (Tipologia vs Zona Bioclimática)
CRCGTT_D_A_TABLE = {
    "Educacionais": {"1R e 1M": 0.25, "2R e 2M": 0.18, "3A e 3B": 0.15, "4A e 4B": 0.09, "5A e 5B": 0.07, "6A e 6B": 0.07}
```

---

Antes (linha 28)

```python
def setup_logging(html_path: Path):
```

Depois (linha 24)

```python
def setup_logging(output_dir: Path):
```

---

Antes (linha 32)

```python
    log_file = html_path.parent / "aenv_calculation.log"
```

Depois (linha 28)

```python
    log_file = output_dir / "crcepd_a_calculation.log"
```

---

Antes (linha 42)

```python
def select_html_file() -> Path:
```

Depois (linha 38)

```python
def calculate_crcepd_a(bioclimatic_zone: str, typology: str = TYPOLOGY, logger=None) -> float:
```

---

Antes (linha 44)

```python
    Opens a dialog for the user to select the EnergyPlus HTML report file.
```

Depois (linha 40)

```python
    Returns CRCEPD-A from Table 8.3 according to typology and bioclimatic zone.
```

---

Antes (linhas 46 a 81)

```python
    root = tk.Tk()
    root.withdraw() # Hide the main Tkinter window
    file_path = filedialog.askopenfilename(
        title="Select the EnergyPlus HTML report file",
        filetypes=[("HTML files", "*.htm *.html"), ("All files", "*.*")]
    )
    root.destroy() # Properly destroy the window
    if not file_path:
        raise FileNotFoundError("No HTML file was selected.")
    return Path(file_path)

def calculate_crcepd_a(ff: float, bioclimatic_zone: int, logger) -> float:
    """
    Calculates CRCEPD-A based on Form Factor and Bioclimatic Zone using direct table lookup (no interpolation).
    """
    logger.info(f"Calculating CRCEPD-A for FF={ff:.4f} and Bioclimatic Zone={bioclimatic_zone}")
    
    if bioclimatic_zone not in CRCEPD_A_TABLE:
        logger.error(f"Invalid bioclimatic zone: {bioclimatic_zone}")
        raise ValueError(f"Invalid bioclimatic zone: {bioclimatic_zone}")
    
    zone_data = CRCEPD_A_TABLE[bioclimatic_zone]
    
    # Determina a faixa baseado no FF (sem interpolação)
    if ff <= 0.20:
        selected_ff = 0.20
    elif ff <= 0.30:
        selected_ff = 0.30
    elif ff <= 0.40:
        selected_ff = 0.40
    else:
        selected_ff = 0.50
    
    crcepd_a = zone_data[selected_ff]
    logger.info(f"FF={ff:.4f} -> Selected FF threshold: {selected_ff} -> CRCEPD-A = {crcepd_a}")
    
```

Depois (linhas 42 a 48)

```python
    if typology not in CRCEPD_A_TABLE:
        raise ValueError(f"Invalid typology: {typology}")
    if bioclimatic_zone not in CRCEPD_A_TABLE[typology]:
        raise ValueError(f"Invalid bioclimatic zone: {bioclimatic_zone}. Valid zones: {', '.join(BIOCLIMATIC_ZONES)}")
    crcepd_a = CRCEPD_A_TABLE[typology][bioclimatic_zone]
    if logger:
        logger.info(f"Typology={typology}, Bioclimatic Zone={bioclimatic_zone} -> CRCEPD-A = {crcepd_a}")
```

---

Antes (linha 84)

```python
def calculate_factor_i(crcepd_a: float, logger) -> float:
```

Depois (linha 51)

```python
def calculate_crcgtt_d_a(bioclimatic_zone: str, typology: str = TYPOLOGY, logger=None) -> float:
```

---

Antes (linhas 86 a 87)

```python
    Calculates factor i based on CRCEPD-A.
    Formula: i = (CRCEPD-A * 100) / 3
```

Depois (linha 53)

```python
    Returns CRCgTTD-A from Table 8.5 according to typology and bioclimatic zone.
```

---

Antes (linhas 89 a 90)

```python
    factor_i = (crcepd_a * 100) / 3
    logger.info(f"Calculating factor i: ({crcepd_a:.4f} * 100) / 3 = {factor_i:.4f}")
```

Depois (linhas 55 a 69)

```python
    if bioclimatic_zone not in CRCGTT_D_A_TABLE[typology]:
        raise ValueError(f"Invalid bioclimatic zone: {bioclimatic_zone}. Valid zones: {', '.join(BIOCLIMATIC_ZONES)}")
    crcgtt = CRCGTT_D_A_TABLE[typology][bioclimatic_zone]
    if logger:
        logger.info(f"Typology={typology}, Bioclimatic Zone={bioclimatic_zone} -> CRCgTTD-A = {crcgtt}")
    return crcgtt

def calculate_factor_i(coefficient: float, logger=None) -> float:
    """
    Calculates factor i (Equations 8.8 and 8.9).
    Formula: i = (coefficient * 100) / 3
    """
    factor_i = (coefficient * 100) / 3
    if logger:
        logger.info(f"Calculating factor i: ({coefficient:.4f} * 100) / 3 = {factor_i:.4f}")
```

---

Antes (linha 93)

```python
def find_opaque_exterior_table(soup, logger) -> object:
```

Depois (linha 72)

```python
def calculate_class(reduction: float, factor_i: float) -> str:
```

---

Antes (linhas 95 a 96)

```python
    Finds the 'Opaque Exterior' table in the EnergyPlus HTML report.
    Returns the table element or raises ValueError if not found.
```

Depois (linha 74)

```python
    Returns the efficiency class (Tables 8.2 and 8.4).
```

---

Antes (linhas 98 a 116)

```python
    logger.info("Searching for 'Opaque Exterior' table in HTML report")
    # Look for the "Opaque Exterior" text followed by a table
    opaque_exterior_elements = soup.find_all(string=re.compile(r'Opaque Exterior'))
    logger.info(f"Found {len(opaque_exterior_elements)} 'Opaque Exterior' elements")
    for element in opaque_exterior_elements:
        # Find the next table after this text
        current = element.parent if element.parent else element
        while current:
            current = current.find_next_sibling()
            if current and current.name == 'table':
                # Verify this table has the expected structure
                headers = current.find('tr')
                if headers:
                    header_text = headers.get_text()
                    if 'Construction' in header_text and 'Gross Area' in header_text:
                        logger.info("Found valid 'Opaque Exterior' table")
                        return current
    logger.error("'Opaque Exterior' table not found in HTML report")
    raise ValueError("'Opaque Exterior' table not found in HTML report")
```

Depois (linhas 76 a 84)

```python
    if reduction < 0:
        return "E"
    if reduction <= factor_i:
        return "D"
    if reduction <= 2 * factor_i:
        return "C"
    if reduction <= 3 * factor_i:
        return "B"
    return "A"
```

---

Antes (linha 118)

```python
def find_zone_summary_table(soup, logger) -> object:
```

Depois (linha 86)

```python
def calculate_coefficients(bioclimatic_zone: str, typology: str = TYPOLOGY, logger=None) -> dict:
```

---

Antes (linhas 120 a 121)

```python
    Finds the 'Zone Summary' table in the EnergyPlus HTML report.
    Returns the table element or raises ValueError if not found.
```

Depois (linha 88)

```python
    Calculates CRCEPD-A, CRCgTTD-A and the corresponding factors i.
```

---

Antes (linhas 123 a 342)

```python
    logger.info("Searching for 'Zone Summary' table in HTML report")
    # Look for "Zone Summary" text followed by a table
    zone_summary_elements = soup.find_all(string=re.compile(r'Zone Summary'))
    logger.info(f"Found {len(zone_summary_elements)} 'Zone Summary' elements")
    for element in zone_summary_elements:
        # Find the next table after this text
        current = element.parent if element.parent else element
        while current:
            current = current.find_next_sibling()
            if current and current.name == 'table':
                # Verify this table has the expected structure
                headers = current.find('tr')
                if headers:
                    header_text = headers.get_text()
                    if 'Volume' in header_text:
                        logger.info("Found valid 'Zone Summary' table")
                        return current
    logger.error("'Zone Summary' table not found in HTML report")
    raise ValueError("'Zone Summary' table not found in HTML report")

def extract_construction_data(table, logger) -> list:
    """
    Extracts construction data from the opaque exterior table.
    Returns list of dictionaries with construction name, type, and gross area.
    """
    logger.info("Extracting construction data from opaque exterior table")
    rows = table.find_all('tr')
    if len(rows) < 2:
        logger.warning("Opaque exterior table has insufficient rows")
        return []
    
    # First row contains headers
    header_row = rows[0]
    headers = [cell.get_text(strip=True) for cell in header_row.find_all('td')]
    logger.info(f"Table headers: {headers}")
    
    # Find column indices
    construction_idx = None
    gross_area_idx = None
    for i, header in enumerate(headers):
        if 'Construction' in header:
            construction_idx = i
        elif 'Gross Area' in header:
            gross_area_idx = i
    
    if construction_idx is None or gross_area_idx is None:
        logger.error("Required columns 'Construction' or 'Gross Area' not found")
        raise ValueError("Required columns 'Construction' or 'Gross Area' not found")
    
    # Process data rows (skip header row)
    surface_data = []
    for row_idx, row in enumerate(rows[1:], 1):
        cells = row.find_all('td')
        if len(cells) > max(construction_idx, gross_area_idx):
            construction = cells[construction_idx].get_text(strip=True)
            gross_area_text = cells[gross_area_idx].get_text(strip=True)
            
            # Check if construction contains any valid terms
            construction_type = None
            construction_upper = construction.upper()
            for term in AENV_CONSTRUCTION_TERMS:
                if term in construction_upper:
                    construction_type = term
                    break
            
            if construction_type:
                try:
                    # Extract numeric value from area text
                    area_value = float(gross_area_text.strip())
                    surface_data.append({
                        'Surface_Name': cells[0].get_text(strip=True), # First column is surface name
                        'Construction': construction,
                        'Zone': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                        'Type': construction_type,
                        'Gross_Area_m2': area_value
                    })
                    logger.info(f"Row {row_idx}: Added surface {cells[0].get_text(strip=True)} - {area_value:.2f} m² ({construction_type})")
                except ValueError:
                    logger.warning(f"Row {row_idx}: Could not parse area value '{gross_area_text}'")
                    continue
            else:
                logger.debug(f"Row {row_idx}: Construction '{construction}' does not match criteria")
    
    logger.info(f"Extracted {len(surface_data)} valid surfaces from opaque exterior table")
    return surface_data

def extract_total_volume(table, logger) -> float:
    """
    Extracts total volume from the zone summary table.
    Returns the total volume in m³.
    """
    logger.info("Extracting total volume from zone summary table")
    rows = table.find_all('tr')
    if len(rows) < 2:
        logger.error("Zone Summary table has insufficient data")
        raise ValueError("Zone Summary table has insufficient data")
    
    # First row contains headers
    header_row = rows[0]
    headers = [cell.get_text(strip=True) for cell in header_row.find_all('td')]
    logger.info(f"Zone summary headers: {headers}")
    
    # Find volume column index
    volume_idx = None
    for i, header in enumerate(headers):
        if 'Volume' in header and 'm3' in header:
            volume_idx = i
            break
    
    if volume_idx is None:
        logger.error("Volume column not found in Zone Summary table")
        raise ValueError("Volume column not found in Zone Summary table")
    
    # Look for the "Total" row
    for row_idx, row in enumerate(rows[1:], 1):
        cells = row.find_all('td')
        if len(cells) > volume_idx:
            first_cell = cells[0].get_text(strip=True)
            if first_cell.upper() == 'TOTAL':
                volume_text = cells[volume_idx].get_text(strip=True)
                try:
                    # Remove any commas and convert to float
                    volume_value = float(volume_text.replace(',', ''))
                    logger.info(f"Found total volume: {volume_value:.2f} m³")
                    return volume_value
                except ValueError:
                    logger.warning(f"Could not parse volume value '{volume_text}' in total row")
                    continue
    
    logger.error("Total volume not found in Zone Summary table")
    raise ValueError("Total volume not found in Zone Summary table")

def calculate_aenv_and_ff(html_path: Path, bioclimatic_zone: int) -> dict:
    """
    Calculates envelope area (Aenv), total volume (Vtot), form factor (FF), CRCEPD-A, and factor i
    from EnergyPlus HTML report.
    """
    logger = setup_logging(html_path)
    logger.info(f"Starting calculation for file: {html_path}")
    logger.info(f"Bioclimatic Zone: {bioclimatic_zone}")
    
    try:
        with open(html_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
        logger.info("Successfully loaded HTML file")
    except Exception as e:
        logger.error(f"Error opening HTML file {html_path}: {e}")
        return None
    
    try:
        # Find opaque exterior table
        opaque_table = find_opaque_exterior_table(soup, logger)
        # Find zone summary table
        zone_table = find_zone_summary_table(soup, logger)
        
        # Extract construction data
        surface_data = extract_construction_data(opaque_table, logger)
        # Extract total volume
        vtot = extract_total_volume(zone_table, logger)
        
        if not surface_data:
            logger.warning("No valid surfaces found for envelope area calculation")
            return {
                'aenv_total_m2': 0.0,
                'vtot_m3': vtot,
                'ff_m_minus1': 0.0,
                'crcepd_a': 0.0,
                'factor_i': 0.0,
                'bioclimatic_zone': bioclimatic_zone,
                'breakdown_by_type': {},
                'surfaces_included': 0,
                'surface_details': []
            }
        
        # Create DataFrame for analysis
        df = pd.DataFrame(surface_data)
        logger.info(f"Created DataFrame with {len(df)} surfaces")
        
        # Calculate totals by type
        breakdown = df.groupby('Type')['Gross_Area_m2'].sum().to_dict()
        logger.info(f"Area breakdown by type: {breakdown}")
        
        # Calculate total envelope area
        aenv_total = df['Gross_Area_m2'].sum()
        logger.info(f"Total envelope area (Aenv): {aenv_total:.2f} m²")
        
        # Calculate form factor (FF = Aenv / Vtot)
        ff = aenv_total / vtot if vtot > 0 else 0.0
        logger.info(f"Form factor (FF): {ff:.4f} m⁻¹")
        
        # Calculate CRCEPD-A
        crcepd_a = calculate_crcepd_a(ff, bioclimatic_zone, logger)
        logger.info(f"CRCEPD-A: {crcepd_a:.4f}")
        
        # Calculate factor i
        factor_i = calculate_factor_i(crcepd_a, logger)
        logger.info(f"Factor i: {factor_i:.4f}")
        
        # Log detailed surface information
        logger.info("Detailed surface information:")
        for surface in surface_data:
            logger.info(f" {surface['Surface_Name']}: {surface['Construction']} - {surface['Gross_Area_m2']:.2f} m² ({surface['Type']})")
        
        logger.info("Calculation completed successfully")
        
        return {
            'aenv_total_m2': aenv_total,
            'vtot_m3': vtot,
            'ff_m_minus1': ff,
            'crcepd_a': crcepd_a,
            'factor_i': factor_i,
            'bioclimatic_zone': bioclimatic_zone,
            'breakdown_by_type': breakdown,
            'surfaces_included': len(df),
            'surface_details': surface_data
        }
    
    except Exception as e:
        logger.error(f"Error processing HTML data: {e}")
        return None
```

Depois (linhas 90 a 99)

```python
    crcepd_a = calculate_crcepd_a(bioclimatic_zone, typology, logger)
    crcgtt = calculate_crcgtt_d_a(bioclimatic_zone, typology, logger)
    return {
        'bioclimatic_zone': bioclimatic_zone,
        'typology': typology,
        'crcepd_a': crcepd_a,
        'factor_i': calculate_factor_i(crcepd_a, logger),
        'crcgtt_d_a': crcgtt,
        'factor_i_envelope': calculate_factor_i(crcgtt, logger)
    }
```

---

Antes (linha 346)

```python
    Main function to execute the Aenv, FF, CRCEPD-A, and factor i calculation script.
```

Depois (linha 103)

```python
    Main function to execute the CRCEPD-A, CRCgTTD-A and factor i calculation script.
```

---

Antes (linhas 349 a 366)

```python
        print("=== INI-C Envelope Area (Aenv), Form Factor (FF), CRCEPD-A, and Factor i Calculator ===\n")
        print(f"Configured Bioclimatic Zone: {BIOCLIMATIC_ZONE}")
        print("(To change the bioclimatic zone, edit the BIOCLIMATIC_ZONE variable at the beginning of the script)\n")
        
        # Select HTML file
        print("Select the EnergyPlus HTML report file (eplustbl.htm):")
        html_file = select_html_file()
        print(f"Selected file: {html_file.name}")
        
        # Calculate Aenv, Vtot, FF, CRCEPD-A, and factor i
        print(f"\nCalculating envelope area (Aenv), total volume (Vtot), form factor (FF), CRCEPD-A, and factor i...")
        results = calculate_aenv_and_ff(html_file, BIOCLIMATIC_ZONE)
        
        if not results:
            print("Error: Could not calculate envelope area, form factor, CRCEPD-A, and factor i.")
            return
        
        # Display only key results in kernel
```

Depois (linhas 106 a 115)

```python
        zone = sys.argv[1] if len(sys.argv) > 1 else BIOCLIMATIC_ZONE
        output_dir = Path.cwd()
        logger = setup_logging(output_dir)
        print("=== INI-C CRCEPD-A, CRCgTTD-A and Factor i Calculator ===\n")
        print(f"Typology: {TYPOLOGY}")
        print(f"Bioclimatic Zone: {zone}")
        print("(To change the bioclimatic zone, edit BIOCLIMATIC_ZONE or pass it as argument, e.g. python 14_b_crcepd-a.py \"3A e 3B\")\n")

        results = calculate_coefficients(zone, TYPOLOGY, logger)

```

---

Antes (linhas 370 a 375)

```python
        print(f" Envelope Area (Aenv) = {results['aenv_total_m2']:,.2f} m²")
        print(f" Total Volume (Vtot) = {results['vtot_m3']:,.2f} m³")
        print(f" Form Factor (FF) = {results['ff_m_minus1']:.4f} m⁻¹")
        print(f" CRCEPD-A = {results['crcepd_a']:.4f}")
        print(f" Factor i = {results['factor_i']:.4f}")
        print(f" Bioclimatic Zone = {results['bioclimatic_zone']}")
```

Depois (linhas 119 a 122)

```python
        print(f" CRCEPD-A (Table 8.3) = {results['crcepd_a']:.2f}")
        print(f" Factor i (general classification) = {results['factor_i']:.4f}")
        print(f" CRCgTTD-A (Table 8.5) = {results['crcgtt_d_a']:.2f}")
        print(f" Factor i (envelope) = {results['factor_i_envelope']:.4f}")
```

---

Antes (linhas 377 a 399)

```python
        
        # Optional: Save detailed results to CSV
        if results['surface_details']:
            # Save surface details
            df_results = pd.DataFrame(results['surface_details'])
            output_file = html_file.parent / "aenv_calculation_results.csv"
            df_results.to_csv(output_file, index=False)
            
            # Save summary results
            summary_data = {
                'Metric': ['Envelope Area (Aenv)', 'Total Volume (Vtot)', 'Form Factor (FF)', 'CRCEPD-A', 'Factor i', 'Bioclimatic Zone'],
                'Value': [results['aenv_total_m2'], results['vtot_m3'], results['ff_m_minus1'], results['crcepd_a'], results['factor_i'], results['bioclimatic_zone']],
                'Unit': ['m²', 'm³', 'm⁻¹', '-', '-', '-']
            }
            df_summary = pd.DataFrame(summary_data)
            summary_file = html_file.parent / "ff_calculation_summary.csv"
            df_summary.to_csv(summary_file, index=False)
            
            print(f"\nDetailed results saved to: {output_file}")
            print(f"Summary results saved to: {summary_file}")
            print(f"Execution log saved to: {html_file.parent / 'aenv_calculation.log'}")
    
    except FileNotFoundError as e:
```

Depois (linhas 124 a 133)

```python

        summary_data = {
            'Metric': ['Typology', 'Bioclimatic Zone', 'CRCEPD-A', 'Factor i', 'CRCgTTD-A', 'Factor i envelope'],
            'Value': [results['typology'], results['bioclimatic_zone'], results['crcepd_a'], results['factor_i'], results['crcgtt_d_a'], results['factor_i_envelope']]
        }
        summary_file = output_dir / "crcepd_a_summary.csv"
        pd.DataFrame(summary_data).to_csv(summary_file, index=False)
        print(f"\nSummary results saved to: {summary_file}")

    except ValueError as e:
```

---

## wall_modifier.py

Motivo:

- Faces internas mantêm a absortância do modelo real (item C.I.4.1). A face externa usa 0,5.
- Pares de superfícies entre zonas recebem a construção espelhada.

Antes: nada (inserido após a linha 5)

Depois (linhas 6 a 7)

```python

from reference_construction_utils import ReferenceConstructionBuilder, get_face_absorptances, apply_to_surfaces
```

---

Antes: nada (inserido após a linha 20)

Depois (linha 23)

```python
        self.reference_outside_face = {"solar": 0.5, "thermal": 0.9, "visible": 0.7}
```

---

Antes (linhas 43 a 72)

```python
        """Creates INI-C wall materials."""
        mat1 = openstudio.model.StandardOpaqueMaterial(model)
        mat1.setName("Reference_Layer_1_External")
        mat1.setThickness(0.025)
        mat1.setConductivity(1.15)
        mat1.setDensity(2000.0)
        mat1.setSpecificHeat(1000.0)
        mat1.setSolarAbsorptance(0.5)

        mat2 = openstudio.model.StandardOpaqueMaterial(model)
        mat2.setName("Reference_Layer_2_Middle")
        mat2.setThickness(0.0134)
        mat2.setConductivity(0.90)
        mat2.setDensity(1600.0)
        mat2.setSpecificHeat(920.0)

        airgap = openstudio.model.AirGap(model)
        airgap.setName("Reference_Air_Gap")
        airgap.setThermalResistance(0.175)

        mat3 = openstudio.model.StandardOpaqueMaterial(model)
        mat3.setName("Reference_Layer_3_Internal")
        mat3.setThickness(0.025)
        mat3.setConductivity(1.15)
        mat3.setDensity(2000.0)
        mat3.setSpecificHeat(1000.0)
        mat3.setSolarAbsorptance(0.5)

        logging.info("INI-C materials created in model.")
        return {'mat1': mat1, 'mat2': mat2, 'airgap': airgap, 'mat3': mat3}
```

Depois (linhas 46 a 55)

```python
        """Creates the INI-C wall layer specification (Table A.9)."""
        layer_specs = [
            {"name": "Reference_Layer_1_External", "thickness": 0.025, "conductivity": 1.15, "density": 2000.0, "specific_heat": 1000.0},
            {"name": "Reference_Layer_2_Middle", "thickness": 0.0134, "conductivity": 0.90, "density": 1600.0, "specific_heat": 920.0},
            {"name": "Reference_Air_Gap", "air_gap_resistance": 0.175},
            {"name": "Reference_Layer_2_Middle", "thickness": 0.0134, "conductivity": 0.90, "density": 1600.0, "specific_heat": 920.0},
            {"name": "Reference_Layer_3_Internal", "thickness": 0.025, "conductivity": 1.15, "density": 2000.0, "specific_heat": 1000.0},
        ]
        logging.info("INI-C wall layers defined.")
        return layer_specs
```

---

Antes (linhas 75 a 81)

```python
        """Creates the INI-C wall construction."""
        layers = openstudio.model.MaterialVector()
        layers.append(materials['mat1'])
        layers.append(materials['mat2'])
        layers.append(materials['airgap'])
        layers.append(materials['mat2'])
        layers.append(materials['mat3'])
```

Depois (linhas 58 a 61)

```python
        """Creates the INI-C wall construction builder (one construction per face absorptance combination)."""
        builder = ReferenceConstructionBuilder(model, "Reference_Wall", materials)
        logging.info("Construction builder 'Reference_Wall' created.")
        return builder
```

---

Antes (linhas 83 a 87)

```python
        construction = openstudio.model.Construction(model)
        construction.setName("Reference_Wall")
        construction.setLayers(layers)
        logging.info("Construction 'Reference_Wall' created and assigned correct layers.")
        return construction
```

Depois (linhas 63 a 69)

```python
    def construction_for_surface(self, surface, builder):
        """Exterior face uses the reference absorptance; internal faces keep the absorptance of the real model."""
        original = surface.construction().get() if surface.construction().is_initialized() else None
        outside_face, inside_face = get_face_absorptances(original)
        if surface.outsideBoundaryCondition() == "Outdoors":
            outside_face = dict(self.reference_outside_face)
        return builder.get(outside_face, inside_face)
```

---

Antes (linhas 113 a 129)

```python
        """Applies the new construction to identified surfaces."""
        count = 0
        
        for surface in target_surfaces:
            try:
                old_construction_name = "Unknown"
                old_construction_opt = surface.construction()
                if old_construction_opt.is_initialized():
                    old_construction_name = old_construction_opt.get().nameString()
                
                surface.setConstruction(construction)
                count += 1
                logging.info(f"Modified surface '{surface.nameString()}': '{old_construction_name}' -> 'Reference_Wall'")
                
            except Exception as e:
                logging.warning(f"Error applying construction to surface '{surface.nameString()}': {e}")
        
```

Depois (linhas 95 a 96)

```python
        """Applies the reference construction to identified surfaces and keeps interzone pairs consistent."""
        count = apply_to_surfaces(target_surfaces, lambda surface: self.construction_for_surface(surface, construction))
```

---

## roof_modifier.py

Motivo:

- Face interna mantém a absortância do modelo real (item C.I.4.1). A face externa usa 0,8.
- Pares de superfícies entre zonas recebem a construção espelhada.

Antes: nada (inserido após a linha 5)

Depois (linhas 6 a 7)

```python

from reference_construction_utils import ReferenceConstructionBuilder, get_face_absorptances, apply_to_surfaces
```

---

Antes: nada (inserido após a linha 18)

Depois (linha 21)

```python
        self.reference_outside_face = {"solar": 0.8, "thermal": 0.9, "visible": 0.7}
```

---

Antes (linhas 44 a 46)

```python
        """Creates materials for roof according to INI-C specification."""
        materials = {}
        try:
```

Depois (linhas 47 a 48)

```python
        """Creates the INI-C roof layer specification (Table A.9)."""
        materials = [
```

---

Antes (linhas 48 a 56)

```python
            comp5 = openstudio.model.StandardOpaqueMaterial(model)
            comp5.setName("Reference_Component_5_External_Roof")
            comp5.setThickness(0.008) # 0.800 cm = 0.008 m
            comp5.setConductivity(0.950) # W/(m·K)
            comp5.setDensity(1900.0) # kg/m³
            comp5.setSpecificHeat(840.0) # J/(kg·K)
            comp5.setSolarAbsorptance(0.8)
            materials['comp5'] = comp5

```

Depois (linha 50)

```python
            {"name": "Reference_Component_5_External_Roof", "thickness": 0.008, "conductivity": 0.950, "density": 1900.0, "specific_heat": 840.0},
```

---

Antes (linhas 58 a 62)

```python
            air_gap = openstudio.model.AirGap(model)
            air_gap.setName("Reference_Roof_Air_Gap")
            air_gap.setThermalResistance(0.2100) # Rt = 0.2100 m²·K/W
            materials['air'] = air_gap

```

Depois (linha 52)

```python
            {"name": "Reference_Roof_Air_Gap", "air_gap_resistance": 0.2100},
```

---

Antes (linhas 64 a 76)

```python
            comp6 = openstudio.model.StandardOpaqueMaterial(model)
            comp6.setName("Reference_Component_6_Internal_Roof")
            comp6.setThickness(0.10) # 10.0 cm = 0.10 m
            comp6.setConductivity(1.75) # W/(m·K)
            comp6.setDensity(2200.0) # kg/m³
            comp6.setSpecificHeat(1000.0) # J/(kg·K)
            materials['comp6'] = comp6

            self.log("INI-C roof materials created successfully.")
            return materials
        except Exception as e:
            logging.error(f"Error creating roof materials: {e}")
            raise
```

Depois (linhas 54 a 57)

```python
            {"name": "Reference_Component_6_Internal_Roof", "thickness": 0.10, "conductivity": 1.75, "density": 2200.0, "specific_heat": 1000.0},
        ]
        self.log("INI-C roof layers defined successfully.")
        return materials
```

---

Antes (linhas 79 a 83)

```python
        """Creates the INI-C roof construction."""
        layers = openstudio.model.MaterialVector()
        layers.append(materials['comp5']) # External
        layers.append(materials['air']) # Air gap
        layers.append(materials['comp6']) # Internal
```

Depois (linhas 60 a 63)

```python
        """Creates the INI-C roof construction builder (one construction per face absorptance combination)."""
        builder = ReferenceConstructionBuilder(model, "Reference_Roof", materials)
        self.log("Construction builder 'Reference_Roof' created.")
        return builder
```

---

Antes (linhas 85 a 89)

```python
        construction = openstudio.model.Construction(model)
        construction.setName("Reference_Roof")
        construction.setLayers(layers)
        self.log("Construction 'Reference_Roof' created and assigned.")
        return construction
```

Depois (linhas 65 a 71)

```python
    def construction_for_surface(self, surface, builder):
        """Exterior face uses the reference absorptance (0.8); the internal face keeps the absorptance of the real model."""
        original = surface.construction().get() if surface.construction().is_initialized() else None
        outside_face, inside_face = get_face_absorptances(original)
        if surface.outsideBoundaryCondition() == "Outdoors":
            outside_face = dict(self.reference_outside_face)
        return builder.get(outside_face, inside_face)
```

---

Antes (linha 115)

```python
        """Assigns the new construction to surfaces with target construction names."""
```

Depois (linha 97)

```python
        """Assigns the reference construction to surfaces with target construction names."""
```

---

Antes (linhas 117 a 132)

```python
        count = 0
        
        for surface in target_surfaces:
            try:
                old_construction_name = "Unknown"
                old_construction_opt = surface.construction()
                if old_construction_opt.is_initialized():
                    old_construction_name = old_construction_opt.get().nameString()
                
                surface.setConstruction(construction)
                count += 1
                self.log(f"Modified surface '{surface.nameString()}': '{old_construction_name}' -> 'Reference_Roof'")
                
            except Exception as e:
                logging.warning(f"Error applying construction to surface '{surface.nameString()}': {e}")
        
```

Depois (linha 99)

```python
        count = apply_to_surfaces(target_surfaces, lambda surface: self.construction_for_surface(surface, construction))
```

---

## floor_modifier.py

Motivo:

- As duas faces mantêm a absortância do modelo real (item C.I.4.1). A camada de 10 cm foi dividida em duas de 5 cm do mesmo material para permitir isso; o comportamento térmico é o mesmo.
- O forro do pavimento de baixo passa a receber a construção espelhada do piso (antes o par ficava com construções diferentes).

Antes: nada (inserido após a linha 5)

Depois (linhas 6 a 7)

```python

from reference_construction_utils import ReferenceConstructionBuilder, get_face_absorptances, apply_to_surfaces
```

---

Antes (linhas 45 a 53)

```python
        """Creates the standard INI-C floor material."""
        mat = openstudio.model.StandardOpaqueMaterial(model)
        mat.setName("Reference_Component_4_Floor")
        mat.setThickness(0.10) # 10.0 cm
        mat.setConductivity(1.75) # W/(m·K)
        mat.setDensity(2200.0) # kg/m³
        mat.setSpecificHeat(1000.0) # J/(kg·K) => 1.00 kJ/(kg·K)
        logging.info("INI-C floor material created: 10cm, 1.75, 2200, 1.00")
        return mat
```

Depois (linhas 47 a 54)

```python
        """Creates the standard INI-C floor layer specification (Table A.9, component 4: 10cm, 1.75, 2200, 1.00).
        The 10 cm layer is split in two 5 cm layers of the same material, so each face keeps the absorptance of the real model."""
        layer_specs = [
            {"name": "Reference_Component_4_Floor", "thickness": 0.05, "conductivity": 1.75, "density": 2200.0, "specific_heat": 1000.0},
            {"name": "Reference_Component_4_Floor", "thickness": 0.05, "conductivity": 1.75, "density": 2200.0, "specific_heat": 1000.0},
        ]
        logging.info("INI-C floor layers defined: 10cm, 1.75, 2200, 1.00")
        return layer_specs
```

---

Antes (linhas 56 a 65)

```python
        """Creates INI-C floor construction (single layer)."""
        construction = openstudio.model.Construction(model)
        construction.setName("Reference_Floor")
        layers = openstudio.model.MaterialVector()
        layers.append(material)
        success = construction.setLayers(layers)
        if not success:
            raise RuntimeError("Failed to set layers for INIC_Floor construction")
        logging.info("INI-C construction created for floors.")
        return construction
```

Depois (linhas 57 a 66)

```python
        """Creates INI-C floor construction builder."""
        builder = ReferenceConstructionBuilder(model, "Reference_Floor", material)
        logging.info("INI-C construction builder created for floors.")
        return builder

    def construction_for_surface(self, surface, builder):
        """Both faces keep the absorptance of the real model."""
        original = surface.construction().get() if surface.construction().is_initialized() else None
        outside_face, inside_face = get_face_absorptances(original)
        return builder.get(outside_face, inside_face)
```

---

Antes (linhas 91 a 107)

```python
        """Applies the new construction to identified surfaces."""
        mod_count = 0

        for surf in target_surfaces:
            try:
                old_construction_name = "Unknown"
                old_construction_opt = surf.construction()
                if old_construction_opt.is_initialized():
                    old_construction_name = old_construction_opt.get().nameString()

                surf.setConstruction(construction)
                mod_count += 1
                logging.info(f"Modified surface '{surf.nameString()}': '{old_construction_name}' -> 'INIC_Floor'")

            except Exception as e:
                logging.warning(f"Error applying construction to surface '{surf.nameString()}': {e}")

```

Depois (linhas 92 a 93)

```python
        """Applies the reference construction to identified surfaces and keeps interzone pairs (floor and ceiling) consistent."""
        mod_count = apply_to_surfaces(target_surfaces, lambda surface: self.construction_for_surface(surface, construction))
```

---

## glazing_modifier.py

Motivo:

- Portas opacas não são mais apagadas (item C.I.4).
- Zonas compostas só por APT mantêm as janelas e o vidro do modelo real (item C.I.4).
- As janelas existentes são redimensionadas em torno do próprio centro, mantendo a posição (item C.I.4). Quando não cabem, a janela é recriada por parede, sem apagar portas.
- PAF calculado por fachada de cada zona térmica (Nota 1 da Tabela A.2). Portas de vidro entram como abertura.
- Tipologia padrão: Educational (40%).
- Correção de bugs na limpeza de recursos (getInternalMasses e getDefaultSubSurfaceConstructions não existiam), que impediam a limpeza de rodar.

Antes: nada (inserido após a linha 9)

Depois (linhas 10 a 11)

```python

from spacetype_utils import get_space_type_label
```

---

Antes: nada (inserido após a linha 34)

Depois (linhas 37 a 39)

```python
        self.default_typology = "Educational"
        self.transparent_types = ["FixedWindow", "OperableWindow", "GlassDoor"]
        self.edge_margin = 0.05
```

---

Antes (linha 84)

```python
            typology_var = StringVar(value="Office")
```

Depois (linha 89)

```python
            typology_var = StringVar(value=self.default_typology)
```

---

Antes (linha 117)

```python
                has_windows = any(sub.subSurfaceType() in ["FixedWindow", "OperableWindow"] for sub in surface.subSurfaces())
```

Depois (linha 122)

```python
                has_windows = any(sub.subSurfaceType() in self.transparent_types for sub in surface.subSurfaces())
```

---

Antes: nada (inserido após a linha 120)

Depois (linhas 126 a 285)

```python

    def get_surface_zone(self, surface):
        space_optional = surface.space()
        if space_optional.is_initialized():
            zone_optional = space_optional.get().thermalZone()
            if zone_optional.is_initialized():
                return zone_optional.get()
        return None

    def is_apt_only_zone(self, zone):
        """Zones composed only of APT keep the real transparent elements (INI-C item C.I.4)."""
        if zone is None:
            return False
        return all(get_space_type_label(space) != "APP" for space in zone.spaces())

    def facade_key(self, surface, model):
        zone = self.get_surface_zone(surface)
        zone_handle = str(zone.handle()) if zone is not None else "no_zone"
        true_azimuth = (math.degrees(surface.azimuth()) + model.getBuilding().northAxis()) % 360.0
        return (zone_handle, int(round(true_azimuth)) % 360)

    def _local_points(self, transformation, vertices):
        inverse = transformation.inverse()
        return [inverse * v for v in vertices]

    def _point_in_polygon(self, x, y, polygon, tolerance=1e-6):
        inside = False
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if x_cross > x + tolerance:
                    inside = not inside
        return inside

    def _bbox(self, points):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)

    def _boxes_overlap(self, a, b, tolerance=0.01):
        return not (a[2] <= b[0] + tolerance or b[2] <= a[0] + tolerance or a[3] <= b[1] + tolerance or b[3] <= a[1] + tolerance)

    def _shrunk_polygon_contains(self, polygon, points):
        cx = sum(p[0] for p in polygon) / len(polygon)
        cy = sum(p[1] for p in polygon) / len(polygon)
        for x, y in points:
            if not self._point_in_polygon(x, y, polygon):
                return False
            dx, dy = x - cx, y - cy
            norm = math.hypot(dx, dy)
            if norm > 0:
                if not self._point_in_polygon(x + dx / norm * self.edge_margin * 0.5, y + dy / norm * self.edge_margin * 0.5, polygon):
                    return False
        return True

    def scale_windows_in_place(self, walls, target_area):
        """
        Resizes the existing transparent elements around their own centroids, keeping their positions (INI-C item C.I.4).
        Returns True when all resized elements fit in their walls without overlapping other sub surfaces.
        """
        transparent = []
        for wall in walls:
            for sub in wall.subSurfaces():
                if sub.subSurfaceType() in self.transparent_types:
                    transparent.append((wall, sub))
        current_area = sum(sub.grossArea() for _, sub in transparent)
        if current_area <= 0:
            return False
        factor = math.sqrt(target_area / current_area)

        plan = []
        for wall in walls:
            transformation = openstudio.Transformation.alignFace(wall.vertices())
            wall_polygon = [(p.x(), p.y()) for p in self._local_points(transformation, wall.vertices())]
            new_boxes = []
            opaque_boxes = []
            for sub in wall.subSurfaces():
                local = [(p.x(), p.y()) for p in self._local_points(transformation, sub.vertices())]
                if sub.subSurfaceType() in self.transparent_types:
                    cx = sum(p[0] for p in local) / len(local)
                    cy = sum(p[1] for p in local) / len(local)
                    scaled = [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in local]
                    if not self._shrunk_polygon_contains(wall_polygon, scaled):
                        return False
                    new_boxes.append(self._bbox(scaled))
                    z_values = [p.z() for p in self._local_points(transformation, sub.vertices())]
                    z_mean = sum(z_values) / len(z_values)
                    plan.append((sub, transformation, scaled, z_mean))
                else:
                    opaque_boxes.append(self._bbox(local))
            boxes = new_boxes + opaque_boxes
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    if self._boxes_overlap(boxes[i], boxes[j]):
                        return False

        for sub, transformation, scaled, z_mean in plan:
            new_vertices = openstudio.Point3dVector()
            for x, y in scaled:
                new_vertices.append(transformation * openstudio.Point3d(x, y, z_mean))
            sub.setVertices(new_vertices)
        return True

    def create_window_avoiding_doors(self, surface, window_area, model):
        """
        Creates one window on a wall that keeps its opaque doors. The window is placed above the highest door
        when there is enough space; otherwise it is centered on the wall.
        """
        transformation = openstudio.Transformation.alignFace(surface.vertices())
        wall_local = self._local_points(transformation, surface.vertices())
        x_min, y_min, x_max, y_max = self._bbox([(p.x(), p.y()) for p in wall_local])
        z_mean = sum(p.z() for p in wall_local) / len(wall_local)
        margin = self.edge_margin
        width = (x_max - x_min) - 2 * margin
        if width <= 0:
            return False
        door_top = y_min
        for sub in surface.subSurfaces():
            if sub.subSurfaceType() not in self.transparent_types:
                local = self._local_points(transformation, sub.vertices())
                door_top = max(door_top, max(p.y() for p in local))
        bottom = door_top + margin if door_top > y_min else y_min + margin
        available_height = (y_max - margin) - bottom
        height = window_area / width
        if height > available_height:
            bottom = y_min + margin
            available_height = (y_max - margin) - bottom
            if height > available_height:
                height = available_height
            self.logger.warning("Window on surface %s could not avoid all doors; centered placement used.", surface.nameString())
        x_center = (x_min + x_max) / 2
        y0 = bottom
        y1 = bottom + height
        x0 = x_center - width / 2
        x1 = x_center + width / 2
        points = [(x0, y1), (x0, y0), (x1, y0), (x1, y1)]
        new_vertices = openstudio.Point3dVector()
        for x, y in points:
            new_vertices.append(transformation * openstudio.Point3d(x, y, z_mean))
        subsurface = openstudio.model.SubSurface(new_vertices, model)
        subsurface.setSubSurfaceType("OperableWindow")
        return subsurface.setSurface(surface)

    def apply_wwr_per_wall(self, walls, target_wwr, model):
        """Fallback: each wall of the facade receives the target WWR. Doors are kept."""
        successes = 0
        for wall in walls:
            self.remove_existing_windows(wall)
            has_doors = any(sub.subSurfaceType() not in self.transparent_types for sub in wall.subSurfaces())
            if not has_doors and self.apply_wwr_using_native_method(wall, target_wwr):
                successes += 1
                continue
            if self.create_window_avoiding_doors(wall, wall.grossArea() * target_wwr, model):
                successes += 1
            else:
                self.failed_surfaces.append((wall, target_wwr))
        return successes
```

---

Antes (linha 141)

```python
        window_types = ["FixedWindow", "OperableWindow", "Window", "GlassDoor", "Skylight", "TubularDaylightDome", "TubularDaylightDiffuser"]
```

Depois (linha 306)

```python
        window_types = ["FixedWindow", "OperableWindow", "Window", "GlassDoor"]
```

---

Antes (linhas 145 a 159)

```python

    def remove_doors_from_surface(self, surface):
        doors_to_remove = [sub for sub in surface.subSurfaces() if sub.subSurfaceType() == "Door"]
        doors_removed = 0
        for door in doors_to_remove:
            door.remove()
            doors_removed += 1
        return doors_removed

    def check_and_remove_doors(self, surface):
        has_doors = any(sub.subSurfaceType() == "Door" for sub in surface.subSurfaces())
        if has_doors:
            self.remove_doors_from_surface(surface)
            return True
        return False
```

Depois: removido

---

Antes: nada (inserido após a linha 252)

Depois (linhas 403 a 404)

```python
                if self.is_apt_only_zone(self.get_surface_zone(surface)):
                    continue
```

---

Antes (linha 254)

```python
                    if subsurface.subSurfaceType() in ["FixedWindow", "OperableWindow"]:
```

Depois (linha 406)

```python
                    if subsurface.subSurfaceType() in self.transparent_types:
```

---

Antes (linhas 289 a 291)

```python
            for im in model.getInternalMasses():
                if im.construction().is_initialized():
                    active_constructions.add(str(im.construction().get().handle()))
```

Depois (linhas 441 a 443)

```python
            for im_def in model.getInternalMassDefinitions():
                if im_def.construction().is_initialized():
                    active_constructions.add(str(im_def.construction().get().handle()))
```

---

Antes (linha 293)

```python
            for dssc in model.getDefaultSubSurfaceConstructions():
```

Depois (linha 445)

```python
            for dssc in model.getDefaultSubSurfaceConstructionss():
```

---

Antes (linha 341)

```python
            
```

Depois (linha 493)

```python

```

---

Antes (linhas 343 a 347)

```python
            native_successes = 0
            
            for surface in surfaces_with_windows:
                story_name = self.get_surface_story_name(surface)
                
```

Depois (linhas 495 a 512)

```python
            groups = {}
            apt_skipped = 0
            for surface in model.getSurfaces():
                if surface.surfaceType() != "Wall" or surface.outsideBoundaryCondition() != "Outdoors":
                    continue
                zone = self.get_surface_zone(surface)
                if self.is_apt_only_zone(zone):
                    if any(sub.subSurfaceType() in self.transparent_types for sub in surface.subSurfaces()):
                        apt_skipped += 1
                    continue
                groups.setdefault(self.facade_key(surface, model), []).append(surface)

            in_place = 0
            per_wall = 0
            for key, walls in groups.items():
                if not any(any(sub.subSurfaceType() in self.transparent_types for sub in w.subSurfaces()) for w in walls):
                    continue
                story_name = self.get_surface_story_name(walls[0])
```

---

Antes (linha 350)

```python
                    
```

Depois: removido

---

Antes (linhas 353 a 358)

```python
                
                if config["wwr_main"] != config["wwr_other"]:
                    if self.is_facade_match(surface, model, main_orientation):
                        target_wwr = config["wwr_main"]
                    else:
                        target_wwr = config["wwr_other"]
```

Depois (linhas 517 a 518)

```python
                if config["wwr_main"] != config["wwr_other"] and not self.is_facade_match(walls[0], model, main_orientation):
                    target_wwr = config["wwr_other"]
```

---

Antes (linhas 361 a 367)

```python
                
                self.remove_existing_windows(surface)
                self.check_and_remove_doors(surface)
                
                if self.apply_wwr_using_native_method(surface, target_wwr):
                    native_successes += 1
            
```

Depois (linhas 521 a 528)

```python

                target_area = target_wwr * sum(w.grossArea() for w in walls)
                if self.scale_windows_in_place(walls, target_area):
                    in_place += 1
                else:
                    per_wall += self.apply_wwr_per_wall(walls, target_wwr, model)
                    self.logger.info("Facade %s: windows recreated per wall (resizing in place was not possible).", key)

```

---

Antes (linhas 371 a 376)

```python
            
            total_successes = native_successes + fallback_successes
            self.logger.info("Final surface processing %d total successes (Native %d, Fallback %d)", 
                           total_successes, native_successes, fallback_successes)
            
            if total_successes == 0:
```

Depois (linhas 532 a 539)

```python

            self.logger.info("Facades resized in place: %d. Walls recreated: %d. Fallback: %d. APT only walls kept: %d",
                             in_place, per_wall, fallback_successes, apt_skipped)
            print(f"Facades resized in place (window positions kept): {in_place}")
            print(f"Walls with windows recreated: {per_wall}")
            print(f"Walls of APT only zones kept as real model: {apt_skipped}")

            if in_place + per_wall + fallback_successes == 0:
```

---

Antes (linha 379)

```python
            
```

Depois (linha 542)

```python

```

---

Antes (linha 381)

```python
            
```

Depois (linha 544)

```python

```

---

Antes (linha 384)

```python
            
```

Depois (linha 547)

```python

```

---

Antes (linha 387)

```python
            
```

Depois (linha 550)

```python

```

---

## lighting_modifier.py

Motivo:

- Opção app_only: quando o sistema de iluminação não é avaliado, a DPI de referência fica só nas APPs (item C.I.4).

Antes: nada (inserido após a linha 5)

Depois (linhas 6 a 7)

```python

from spacetype_utils import get_space_type_label
```

---

Antes (linha 36)

```python
    def set_lighting_density_all_spaces(self, model, target_density):
```

Depois (linha 38)

```python
    def set_lighting_density_all_spaces(self, model, target_density, app_only=False):
```

---

Antes: nada (inserido após a linha 54)

Depois (linhas 57 a 60)

```python
            if app_only and get_space_type_label(space) != "APP":
                for lights_obj in lights_list:
                    lights_obj.remove()
                continue
```

---

Antes (linha 88)

```python
    def process_files(self, input_path, output_path, target_density=15.5):
```

Depois (linha 94)

```python
    def process_files(self, input_path, output_path, target_density=15.5, app_only=False):
```

---

Antes (linhas 96 a 97)

```python
            logging.info(f"Setting lighting density to {target_density} W/m² for all spaces.")
            modified = self.set_lighting_density_all_spaces(model, target_density)
```

Depois (linhas 102 a 104)

```python
            scope = "APP spaces only (lighting system not evaluated)" if app_only else "all spaces with lighting (lighting system evaluated)"
            logging.info(f"Setting lighting density to {target_density} W/m² for {scope}.")
            modified = self.set_lighting_density_all_spaces(model, target_density, app_only)
```

---

Antes (linhas 124 a 125)

```python
    def run_automated(self, input_path, output_path):
        return self.process_files(input_path, output_path)
```

Depois (linhas 131 a 132)

```python
    def run_automated(self, input_path, output_path, app_only=False):
        return self.process_files(input_path, output_path, app_only=app_only)
```

---

Antes (linhas 131 a 132)

```python
    if len(args) == 2:
        success = modifier.run_automated(args[0], args[1])
```

Depois (linhas 138 a 140)

```python
    if len(args) in (2, 3):
        app_only = len(args) == 3 and args[2].lower() == "app_only"
        success = modifier.run_automated(args[0], args[1], app_only)
```

---

Antes (linha 140)

```python
        print("Usage: python ini_c_lighting_modifier.py [input.osm output.osm]")
```

Depois (linhas 148 a 149)

```python
        print("Usage: python ini_c_lighting_modifier.py [input.osm output.osm [app_only]]")
        print("Use app_only when the lighting system is not evaluated (reference DPI only in APP spaces).")
```

---

## skylight_remover.py

Motivo:

- Zonas compostas só por APT mantêm as aberturas zenitais do modelo real (item C.I.4).
- Opção -y para rodar sem confirmação; quando não há claraboias, o modelo é salvo e o script termina com sucesso.
- Remoção de travessão e símbolo nas mensagens.

Antes: nada (inserido após a linha 12)

Depois (linhas 13 a 14)

```python

from spacetype_utils import get_space_type_label
```

---

Antes (linha 33)

```python
    def __init__(self, input_path=None, output_path=None, use_gui=False):
```

Depois (linha 35)

```python
    def __init__(self, input_path=None, output_path=None, use_gui=False, assume_yes=False):
```

---

Antes: nada (inserido após a linha 36)

Depois (linha 39)

```python
        self.assume_yes = assume_yes
```

---

Antes: nada (inserido após a linha 37)

Depois (linhas 41 a 49)

```python

    def is_apt_only_surface(self, surface):
        """Transparent elements of zones composed only of APT keep the real model characteristics (INI-C item C.I.4)."""
        space_opt = surface.space()
        if not space_opt.is_initialized():
            return False
        zone_opt = space_opt.get().thermalZone()
        spaces = zone_opt.get().spaces() if zone_opt.is_initialized() else [space_opt.get()]
        return all(get_space_type_label(space) != "APP" for space in spaces)
```

---

Antes: nada (inserido após a linha 103)

Depois (linhas 116 a 117)

```python
            if self.is_apt_only_surface(roof):
                continue
```

---

Antes: nada (inserido após a linha 125)

Depois (linhas 140 a 141)

```python
                if self.is_apt_only_surface(surface):
                    continue
```

---

Antes (linha 168)

```python
            return False
```

Depois (linha 184)

```python
            return True
```

---

Antes (linha 189)

```python
                print(f" • {sky['name']} (Area: {sky['area']:.2f} m²), on Surface: {sky['parent_surface']}")
```

Depois (linha 205)

```python
                print(f" - {sky['name']} (Area: {sky['area']:.2f} m²), on Surface: {sky['parent_surface']}")
```

---

Antes (linhas 249 a 250)

```python
                print("No skylights found — no action needed.")
                print(str(self.input_path))
```

Depois (linhas 265 a 267)

```python
                print("No skylights found, no action needed.")
                self.save_model(self.output_path)
                print(str(self.output_path))
```

---

Antes (linhas 254 a 257)

```python
            user_input = input("Remove all skylights? (y/n): ").lower()
            if user_input not in ("y", "yes"):
                print("Operation aborted by user.")
                return False
```

Depois (linhas 271 a 275)

```python
            if not self.assume_yes:
                user_input = input("Remove all skylights? (y/n): ").lower()
                if user_input not in ("y", "yes"):
                    print("Operation aborted by user.")
                    return False
```

---

Antes: nada (inserido após a linha 286)

Depois (linha 305)

```python
    parser.add_argument("-y", "--yes", action="store_true", help="Remove skylights without confirmation (automated mode).")
```

---

Antes (linha 303)

```python
        use_gui=args.gui
```

Depois (linhas 322 a 323)

```python
        use_gui=args.gui,
        assume_yes=args.yes
```

---

## shade_remover.py

Motivo:

- Remove só os elementos fixos de fachada (brises, venezianas, beirais, sacadas). Entorno, circulações externas e elementos na cobertura ficam nos dois modelos (item C.I.4).
- Critério padrão: grupos de sombreamento do tipo Space, nomes com palavras-chave de dispositivos de fachada e superfícies encostadas em paredes externas. Opção -n para indicar os nomes manualmente.
- Remoção de símbolos nas mensagens.

Antes (linha 13)

```python
    Removes all shading surfaces from an OpenStudio model (.osm).
```

Depois (linhas 13 a 17)

```python
    Removes fixed facade shading devices (brises, louvers, overhangs, balconies) from an OpenStudio model (.osm),
    as required for the INI-C reference condition (item C.I.4). Shading surfaces from the surroundings (Site),
    rooftop elements and other building elements are kept in both models.
    Space shading groups are removed. Building and Site shading surfaces are removed only when their names
    contain one of the facade device keywords, or when they are explicitly selected.
```

---

Antes (linha 16)

```python
    def __init__(self, log_path=None):
```

Depois (linhas 20 a 23)

```python
    FACADE_DEVICE_KEYWORDS = ["brise", "veneziana", "beiral", "marquise", "sacada", "varanda",
                              "louver", "overhang", "balcony", "shading device"]

    def __init__(self, log_path=None, names_to_remove=None):
```

---

Antes: nada (inserido após a linha 19)

Depois (linhas 27 a 28)

```python
        self.names_to_remove = set(names_to_remove) if names_to_remove is not None else None
        self._walls = None
```

---

Antes: nada (inserido após a linha 115)

Depois (linhas 125 a 172)

```python
    def _exterior_walls(self):
        if self._walls is None:
            self._walls = []
            for surface in self.model.getSurfaces():
                if surface.surfaceType() != "Wall" or surface.outsideBoundaryCondition() != "Outdoors":
                    continue
                space_opt = surface.space()
                if not space_opt.is_initialized():
                    continue
                to_building = space_opt.get().buildingTransformation()
                vertices = [to_building * v for v in surface.vertices()]
                points = openstudio.Point3dVector(vertices)
                align = openstudio.Transformation.alignFace(points)
                local = [align.inverse() * v for v in vertices]
                xs = [p.x() for p in local]
                ys = [p.y() for p in local]
                self._walls.append((align.inverse(), min(xs), max(xs), min(ys), max(ys)))
        return self._walls

    def is_attached_to_facade(self, surface, tolerance=0.15):
        """Returns True when the shading surface touches an exterior wall (brises, overhangs, fins, balconies)."""
        group_opt = surface.shadingSurfaceGroup()
        to_building = group_opt.get().buildingTransformation() if group_opt.is_initialized() else openstudio.Transformation()
        vertices = [to_building * v for v in surface.vertices()]
        for to_local, x_min, x_max, y_min, y_max in self._exterior_walls():
            for v in vertices:
                p = to_local * v
                if abs(p.z()) <= tolerance and x_min - tolerance <= p.x() <= x_max + tolerance and y_min - tolerance <= p.y() <= y_max + tolerance:
                    return True
        return False

    def is_facade_device(self, surface):
        """Returns True when the shading surface is a fixed facade device to be removed in the reference model."""
        if self.names_to_remove is not None:
            return surface.nameString() in self.names_to_remove
        group_opt = surface.shadingSurfaceGroup()
        group_type = group_opt.get().shadingSurfaceType() if group_opt.is_initialized() else ""
        if group_type == "Space":
            return True
        if group_type == "Site":
            return False
        names = surface.nameString().lower()
        if group_opt.is_initialized():
            names += " " + group_opt.get().nameString().lower()
        if any(keyword in names for keyword in self.FACADE_DEVICE_KEYWORDS):
            return True
        return self.is_attached_to_facade(surface)

```

---

Antes (linha 118)

```python
        Removes all shading surfaces and empty shading surface groups from the model.
```

Depois (linha 175)

```python
        Removes fixed facade shading devices and empty shading surface groups from the model.
```

---

Antes: nada (inserido após a linha 124)

Depois (linha 182)

```python
            "surfaces_kept": [],
```

---

Antes (linhas 130 a 131)

```python
            shading_surfaces = self.model.getShadingSurfaces()
            logging.info(f"Removing {len(shading_surfaces)} shading surfaces.")
```

Depois (linhas 188 a 190)

```python
            shading_surfaces = [s for s in self.model.getShadingSurfaces() if self.is_facade_device(s)]
            report["surfaces_kept"] = [s.nameString() for s in self.model.getShadingSurfaces() if not self.is_facade_device(s)]
            logging.info(f"Removing {len(shading_surfaces)} facade shading surfaces. Keeping {len(report['surfaces_kept'])}.")
```

---

Antes (linha 180)

```python
        """Checks if any shading surfaces remain after removal."""
```

Depois (linha 239)

```python
        """Checks if any facade shading surfaces remain after removal."""
```

---

Antes (linha 183)

```python
        final_surfaces = self.model.getShadingSurfaces()
```

Depois (linha 242)

```python
        final_surfaces = [s for s in self.model.getShadingSurfaces() if self.is_facade_device(s)]
```

---

Antes (linha 207)

```python
                print("✗ Failed to load model.")
```

Depois (linha 266)

```python
                print("ERROR: Failed to load model.")
```

---

Antes (linha 213)

```python
                print(f"✗ Error during removal: {report}")
```

Depois (linha 272)

```python
                print(f"ERROR: Error during removal: {report}")
```

---

Antes (linha 217)

```python
                print(f"✗ Error saving model: {save_msg}")
```

Depois (linha 276)

```python
                print(f"ERROR: Error saving model: {save_msg}")
```

---

Antes: nada (inserido após a linha 224)

Depois (linha 284)

```python
            print(f"Surfaces kept (surroundings and building elements): {len(report['surfaces_kept'])}")
```

---

Antes (linha 227)

```python
                print("✓ SUCCESS: All shading surfaces removed.")
```

Depois (linha 287)

```python
                print("SUCCESS: All facade shading surfaces removed.")
```

---

Antes (linha 229)

```python
                print("⚠ WARNING: Some shading surfaces remain:")
```

Depois (linha 289)

```python
                print("WARNING: Some facade shading surfaces remain:")
```

---

Antes (linha 236)

```python
            print(f"✗ Unexpected error: {e}")
```

Depois (linha 296)

```python
            print(f"ERROR: Unexpected error: {e}")
```

---

Antes (linha 252)

```python
                print("✗ No file selected. Operation cancelled.")
```

Depois (linha 312)

```python
                print("ERROR: No file selected. Operation cancelled.")
```

---

Antes (linha 255)

```python
                print("✗ Failed to load model. Exiting.")
```

Depois (linha 315)

```python
                print("ERROR: Failed to load model. Exiting.")
```

---

Antes (linha 262)

```python
                print("✗ Output location not selected. Operation cancelled.")
```

Depois (linha 322)

```python
                print("ERROR: Output location not selected. Operation cancelled.")
```

---

Antes (linha 266)

```python
                print(f"✗ Error during removal: {report}")
```

Depois (linha 326)

```python
                print(f"ERROR: Error during removal: {report}")
```

---

Antes (linha 270)

```python
                print(f"✗ Error saving model: {save_msg}")
```

Depois (linha 330)

```python
                print(f"ERROR: Error saving model: {save_msg}")
```

---

Antes: nada (inserido após a linha 277)

Depois (linha 338)

```python
            print(f"Surfaces kept (surroundings and building elements): {len(report['surfaces_kept'])}")
```

---

Antes (linha 280)

```python
                print("✓ SUCCESS: All shading surfaces were removed!")
```

Depois (linha 341)

```python
                print("SUCCESS: All facade shading surfaces were removed.")
```

---

Antes (linha 282)

```python
                print("⚠ WARNING: Some shading surfaces remain:")
```

Depois (linha 343)

```python
                print("WARNING: Some facade shading surfaces remain:")
```

---

Antes (linha 288)

```python
            print(f"✗ Unexpected error: {e}")
```

Depois (linha 349)

```python
            print(f"ERROR: Unexpected error: {e}")
```

---

Antes (linha 296)

```python
    parser = argparse.ArgumentParser(description="Remove all shading surfaces from an OpenStudio model (.osm).")
```

Depois (linha 357)

```python
    parser = argparse.ArgumentParser(description="Remove fixed facade shading devices from an OpenStudio model (.osm) for the INI-C reference condition.")
```

---

Antes: nada (inserido após a linha 299)

Depois (linha 361)

```python
    parser.add_argument("-n", "--names", nargs="*", help="Optional: exact names of the shading surfaces to remove. When omitted, Space shading groups, surfaces with facade device keywords and surfaces attached to exterior walls are removed.")
```

---

Antes (linha 305)

```python
        print("✗ ERROR: OpenStudio Python bindings not found or not working.")
```

Depois (linha 367)

```python
        print("ERROR: OpenStudio Python bindings not found or not working.")
```

---

Antes (linha 309)

```python
    remover = ShadingSurfaceRemover(log_path=args.logfile)
```

Depois (linha 371)

```python
    remover = ShadingSurfaceRemover(log_path=args.logfile, names_to_remove=args.names)
```

---

Antes (linha 319)

```python
        print("✓ Shading surface removal completed successfully.")
```

Depois (linha 381)

```python
        print("Shading surface removal completed successfully.")
```

---

Antes (linha 322)

```python
        print("✗ Shading surface removal finished with errors.")
```

Depois (linha 384)

```python
        print("ERROR: Shading surface removal finished with errors.")
```

---
