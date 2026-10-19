import openstudio
import math
import os
import sys
import logging
import traceback
import json
from datetime import datetime
from tkinter import Tk, filedialog, Toplevel, Label, Button, StringVar, OptionMenu

from spacetype_utils import get_space_type_label

class WWRModifier:
    def __init__(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"wwr_modifier_{timestamp}.log"
        logging.basicConfig(
            filename=log_filename,
            filemode="w",
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            level=logging.DEBUG
        )
        self.logger = logging.getLogger("WWRModifier")
        self.logger.info("Initializing WWRModifier. Log file %s", log_filename)
        self.failed_surfaces = [] 
        
        self.typology_data = {
            "Office": {"wwr_main": 0.50, "wwr_other": 0.50},
            "Educational": {"wwr_main": 0.40, "wwr_other": 0.40},
            "Lodging": {"wwr_main": 0.45, "wwr_other": 0.45},
            "Healthcare (Clinic)": {"wwr_main": 0.30, "wwr_other": 0.30},
            "Retail & Services": {"wwr_main": 0.60, "wwr_other": 0.05},
            "Supermarket": {"wwr_main": 0.60, "wwr_other": 0.10},
            "Food Service": {"wwr_main": 0.40, "wwr_other": 0.40},
            "Other": {"wwr_main": 0.60, "wwr_other": 0.60}
        }
        self.default_typology = "Educational"
        self.transparent_types = ["FixedWindow", "OperableWindow", "GlassDoor"]
        self.edge_margin = 0.05

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

    def get_story_configs_from_user(self, stories, parent_root):
        if not stories:
            self.logger.warning("No building stories found in the model.")
            return None, None

        gui_vars = {}
        final_configs = {}
        
        dialog = Toplevel(parent_root)
        dialog.title("Building and Story Typology Configuration")
        dialog.attributes('-topmost', True)
        
        orientations = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        typology_list = list(self.typology_data.keys())
        
        main_orient_var = StringVar(value="N")
        
        Label(dialog, text="Global Main Facade", font=('Arial', 10, 'bold')).grid(row=0, column=0, pady=10, sticky="e")
        OptionMenu(dialog, main_orient_var, *orientations).grid(row=0, column=1, pady=10, sticky="w")
        
        Label(dialog, text="Building Story", font=('Arial', 10, 'bold')).grid(row=1, column=0, padx=10, pady=5)
        Label(dialog, text="Typology", font=('Arial', 10, 'bold')).grid(row=1, column=1, padx=10, pady=5)

        for i, story_name in enumerate(stories):
            row = i + 2
            Label(dialog, text=story_name).grid(row=row, column=0, padx=10, pady=2, sticky="w")
            
            typology_var = StringVar(value=self.default_typology)
            OptionMenu(dialog, typology_var, *typology_list).grid(row=row, column=1, padx=10, pady=2, sticky="ew")
            
            gui_vars[story_name] = typology_var

        def on_apply():
            for story, typ_var in gui_vars.items():
                final_configs[story] = {
                    "typology": typ_var.get()
                }
            dialog.destroy()

        Button(dialog, text="Apply and Continue", command=on_apply, bg="#4CAF50", fg="white").grid(row=len(stories)+2, column=0, columnspan=2, pady=20)
        
        dialog.wait_window()
        
        if final_configs:
            return final_configs, main_orient_var.get()
        return None, None

    def get_surface_story_name(self, surface):
        space_optional = surface.space()
        if space_optional.is_initialized():
            space = space_optional.get()
            story_optional = space.buildingStory()
            if story_optional.is_initialized():
                return story_optional.get().nameString()
        return "Unknown_Story"

    def identify_surfaces_with_windows(self, model):
        surfaces_with_windows = []
        for surface in model.getSurfaces():
            if surface.surfaceType() == "Wall" and surface.outsideBoundaryCondition() == "Outdoors":
                has_windows = any(sub.subSurfaceType() in self.transparent_types for sub in surface.subSurfaces())
                if has_windows:
                    surfaces_with_windows.append(surface)
        return surfaces_with_windows

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

    def is_facade_match(self, surface, model, target_orientation):
        directions = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
        target_angle = directions.get(target_orientation, 0)
        
        building = model.getBuilding()
        north_axis = building.northAxis()
        
        azimuth_rad = surface.azimuth()
        azimuth_deg = math.degrees(azimuth_rad)
        
        true_azimuth = (azimuth_deg + north_axis) % 360.0
        
        abs_diff = abs(true_azimuth - target_angle)
        if abs_diff > 180.0:
            abs_diff = 360.0 - abs_diff
            
        return abs_diff < 22.5

    def remove_existing_windows(self, surface):
        window_types = ["FixedWindow", "OperableWindow", "Window", "GlassDoor"]
        subsurfaces_to_remove = [sub for sub in surface.subSurfaces() if sub.subSurfaceType() in window_types]
        for subsurface in subsurfaces_to_remove:
            subsurface.remove()

    def apply_wwr_using_native_method(self, surface, target_wwr):
        try:
            door_area = sum(sub.grossArea() for sub in surface.subSurfaces() if sub.subSurfaceType() == "Door")
            surface_area = surface.grossArea()
            net_area = surface_area - door_area
            
            if net_area <= 0:
                self.failed_surfaces.append((surface, target_wwr))
                return False
            
            success = surface.setWindowToWallRatio(target_wwr)
            if success:
                for subsurface in surface.subSurfaces():
                    if subsurface.subSurfaceType() in ["FixedWindow", "Window"]:
                        subsurface.setSubSurfaceType("OperableWindow")
                return True
            
            self.failed_surfaces.append((surface, target_wwr))
            return False
        except Exception as e:
            self.failed_surfaces.append((surface, target_wwr))
            self.logger.error("Error applying native WWR %s", str(e))
            return False

    def create_fallback_window(self, surface, window_area, model):
        try:
            vertices = surface.vertices()
            if len(vertices) < 4:
                return False
            
            surface_area = surface.grossArea()
            if surface_area <= 0:
                return False
            
            scale_factor = math.sqrt(window_area / surface_area)
            
            center_x = sum(v.x() for v in vertices) / len(vertices)
            center_y = sum(v.y() for v in vertices) / len(vertices)
            center_z = sum(v.z() for v in vertices) / len(vertices)
            
            new_vertices = openstudio.Point3dVector()
            for v in vertices:
                new_x = center_x + (v.x() - center_x) * scale_factor
                new_y = center_y + (v.y() - center_y) * scale_factor
                new_z = center_z + (v.z() - center_z) * scale_factor
                new_vertices.append(openstudio.Point3d(new_x, new_y, new_z))
            
            subsurface = openstudio.model.SubSurface(new_vertices, model)
            subsurface.setSubSurfaceType("OperableWindow")
            subsurface.setSurface(surface)
            return True
        except Exception as e:
            self.logger.error("Error creating manual window %s", str(e))
            return False

    def process_failed_surfaces(self):
        if not self.failed_surfaces:
            return 0
        
        fallback_successes = 0
        for surface, target_wwr in self.failed_surfaces:
            surface_area = surface.grossArea()
            window_area = surface_area * target_wwr
            
            if self.create_fallback_window(surface, window_area, surface.model()):
                fallback_successes += 1
        
        return fallback_successes

    def apply_global_window_construction(self, model):
        try:
            mat_name = "Reference_Glass"
            const_name = "Reference_Window"
            
            construction = model.getConstructionByName(const_name)
            if not construction.is_initialized():
                simple_glazing = openstudio.model.SimpleGlazing(model)
                simple_glazing.setName(mat_name)
                simple_glazing.setUFactor(5.7)
                simple_glazing.setSolarHeatGainCoefficient(0.82)
                
                new_construction = openstudio.model.Construction(model)
                new_construction.setName(const_name)
                layers = openstudio.model.MaterialVector()
                layers.append(simple_glazing)
                new_construction.setLayers(layers)
                construction = new_construction
            else:
                construction = construction.get()

            applied_count = 0
            for surface in model.getSurfaces():
                if self.is_apt_only_zone(self.get_surface_zone(surface)):
                    continue
                for subsurface in surface.subSurfaces():
                    if subsurface.subSurfaceType() in self.transparent_types:
                        subsurface.setConstruction(construction)
                        applied_count += 1
                        
            self.logger.info("Global construction applied to %d windows", applied_count)
            return True
        except Exception as e:
            self.logger.error("Error applying global construction %s", str(e))
            return False

    def purge_unused_resources_by_geometry(self, model):
        try:
            orphans_removed = 0
            for sub in model.getSubSurfaces():
                if not sub.surface().is_initialized():
                    sub.remove()
                    orphans_removed += 1
                    
            if orphans_removed > 0:
                self.logger.info("Destroyed %d orphaned subsurfaces.", orphans_removed)

            active_constructions = set()
            
            for surf in model.getSurfaces():
                if surf.construction().is_initialized():
                    active_constructions.add(str(surf.construction().get().handle()))
                    
            for sub in model.getSubSurfaces():
                if sub.surface().is_initialized() and sub.construction().is_initialized():
                    active_constructions.add(str(sub.construction().get().handle()))
                    
            for shading in model.getShadingSurfaces():
                if shading.construction().is_initialized():
                    active_constructions.add(str(shading.construction().get().handle()))
                    
            for im_def in model.getInternalMassDefinitions():
                if im_def.construction().is_initialized():
                    active_constructions.add(str(im_def.construction().get().handle()))

            for dssc in model.getDefaultSubSurfaceConstructionss():
                if dssc.fixedWindowConstruction().is_initialized():
                    c_handle = str(dssc.fixedWindowConstruction().get().handle())
                    if c_handle not in active_constructions:
                        dssc.resetFixedWindowConstruction()
                        
                if dssc.operableWindowConstruction().is_initialized():
                    c_handle = str(dssc.operableWindowConstruction().get().handle())
                    if c_handle not in active_constructions:
                        dssc.resetOperableWindowConstruction()
                        
                if dssc.windowConstruction().is_initialized():
                    c_handle = str(dssc.windowConstruction().get().handle())
                    if c_handle not in active_constructions:
                        dssc.resetWindowConstruction()

            model.purgeUnusedResourceObjects()

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

            self.logger.info("Purge completed %d unused constructions and %d unused materials removed.", 
                             removed_constructions, removed_materials)
            return True
        except Exception as e:
            self.logger.error("Error during resource purge %s", str(e))
            return False

    def modify_wwr_by_story(self, model, output_model_path, story_configs, main_orientation):
        try:
            surfaces_with_windows = self.identify_surfaces_with_windows(model)
            if not surfaces_with_windows:
                self.logger.warning("No surfaces with windows found.")
                return False

            self.failed_surfaces = []
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
                if story_name not in story_configs:
                    continue
                typology = story_configs[story_name]["typology"]
                config = self.typology_data.get(typology, self.typology_data["Other"])
                if config["wwr_main"] != config["wwr_other"] and not self.is_facade_match(walls[0], model, main_orientation):
                    target_wwr = config["wwr_other"]
                else:
                    target_wwr = config["wwr_main"]

                target_area = target_wwr * sum(w.grossArea() for w in walls)
                if self.scale_windows_in_place(walls, target_area):
                    in_place += 1
                else:
                    per_wall += self.apply_wwr_per_wall(walls, target_wwr, model)
                    self.logger.info("Facade %s: windows recreated per wall (resizing in place was not possible).", key)

            fallback_successes = 0
            if self.failed_surfaces:
                fallback_successes = self.process_failed_surfaces()

            self.logger.info("Facades resized in place: %d. Walls recreated: %d. Fallback: %d. APT only walls kept: %d",
                             in_place, per_wall, fallback_successes, apt_skipped)
            print(f"Facades resized in place (window positions kept): {in_place}")
            print(f"Walls with windows recreated: {per_wall}")
            print(f"Walls of APT only zones kept as real model: {apt_skipped}")

            if in_place + per_wall + fallback_successes == 0:
                self.logger.error("No successes in surface processing.")
                return False

            self.apply_global_window_construction(model)

            self.logger.info("Executing geometry-based purge of unused resources...")
            self.purge_unused_resources_by_geometry(model)

            success = model.save(openstudio.path(output_model_path), True)
            self.logger.info("Model saved successfully %s", output_model_path)

            return success
        except Exception as e:
            self.logger.error("General error modifying WWR %s\n%s", str(e), traceback.format_exc())
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
                
            model_optional = openstudio.model.Model.load(openstudio.path(input_path))
            if not model_optional.is_initialized():
                print("Failed to load OSM model.")
                return False
            model = model_optional.get()
            
            stories = sorted([story.nameString() for story in model.getBuildingStorys()])
            
            story_configs, main_orientation = self.get_story_configs_from_user(stories, main_root)
            if not story_configs or not main_orientation:
                print("Configuration cancelled or failed.")
                return False
                
            output_path = self.select_output_file(main_root)
            if not output_path:
                print("Output file selection cancelled.")
                return False
                
            success = self.modify_wwr_by_story(model, output_path, story_configs, main_orientation)
            if success:
                print("Process completed successfully.")
            else:
                print("Processing failed.")
            return success
            
        finally:
            main_root.destroy()

    def run_automated(self, input_path, output_path, config_json_string):
        self.logger.info("Running in automated mode.")
        try:
            data = json.loads(config_json_string)
            main_orientation = data.get("main_orientation", "N")
            story_configs = data.get("stories", {})
            
            model_optional = openstudio.model.Model.load(openstudio.path(input_path))
            if not model_optional.is_initialized():
                return False
            model = model_optional.get()
            return self.modify_wwr_by_story(model, output_path, story_configs, main_orientation)
        except Exception as e:
            self.logger.error("Automated mode error %s", str(e))
            return False

def main():
    modifier = WWRModifier()
    args = sys.argv[1:]
    
    if len(args) == 3:
        success = modifier.run_automated(args[0], args[1], args[2])
        sys.exit(0 if success else 1)
    elif len(args) == 0:
        success = modifier.run_standalone()
        sys.exit(0 if success else 1)
    else:
        print("Usage python wwr_modifier.py [input.osm output.osm '{\"main_orientation\" \"N\", \"stories\" {\"Story1\" {\"typology\" \"Office\"}}}']")
        print("Or run without arguments for dialog mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()