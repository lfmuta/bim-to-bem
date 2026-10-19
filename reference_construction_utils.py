# reference_construction_utils.py

"""
Utilities for building INI-C reference constructions (Table A.9) in OpenStudio models.

- Internal faces keep the absorptance of the real model (INI-C item C.I.4.1).
- Interzone surface pairs receive mirrored constructions, so both sides of the same element are consistent.
"""

import openstudio

DEFAULT_SOLAR_ABSORPTANCE = 0.7
DEFAULT_THERMAL_ABSORPTANCE = 0.9
DEFAULT_VISIBLE_ABSORPTANCE = 0.7


def get_face_absorptances(construction_base):
    """
    Returns the absorptances of the outside and inside faces of a construction as two dictionaries.
    Values come from the first and last opaque layers. Defaults are used when they are not available.
    """
    default = {
        "solar": DEFAULT_SOLAR_ABSORPTANCE,
        "thermal": DEFAULT_THERMAL_ABSORPTANCE,
        "visible": DEFAULT_VISIBLE_ABSORPTANCE,
    }
    outside, inside = dict(default), dict(default)
    if construction_base is None:
        return outside, inside
    construction_opt = construction_base.to_LayeredConstruction()
    if not construction_opt.is_initialized():
        return outside, inside
    layers = construction_opt.get().layers()
    if len(layers) == 0:
        return outside, inside
    for face, layer in ((outside, layers[0]), (inside, layers[len(layers) - 1])):
        opaque_opt = layer.to_OpaqueMaterial()
        if opaque_opt.is_initialized():
            opaque = opaque_opt.get()
            face["solar"] = opaque.solarAbsorptance()
            face["thermal"] = opaque.thermalAbsorptance()
            face["visible"] = opaque.visibleAbsorptance()
    return outside, inside


def create_standard_material(model, name, thickness, conductivity, density, specific_heat, absorptances=None):
    """Creates a StandardOpaqueMaterial with SI units (m, W/(m.K), kg/m3, J/(kg.K))."""
    material = openstudio.model.StandardOpaqueMaterial(model)
    material.setName(name)
    material.setThickness(thickness)
    material.setConductivity(conductivity)
    material.setDensity(density)
    material.setSpecificHeat(specific_heat)
    if absorptances:
        material.setSolarAbsorptance(absorptances["solar"])
        material.setThermalAbsorptance(absorptances["thermal"])
        material.setVisibleAbsorptance(absorptances["visible"])
    return material


def _absorptance_key(face):
    return (round(face["solar"], 4), round(face["thermal"], 4), round(face["visible"], 4))


class ReferenceConstructionBuilder:
    """
    Creates reference constructions on demand, one for each combination of outside and inside face absorptances.

    layer_specs: list of dictionaries describing the layers from outside to inside.
        Opaque layer: {"name", "thickness", "conductivity", "density", "specific_heat"}
        Air gap: {"name", "air_gap_resistance"}
    The first and last layers must be opaque.
    """

    def __init__(self, model, base_name, layer_specs):
        self.model = model
        self.base_name = base_name
        self.layer_specs = layer_specs
        self.cache = {}
        self.shared_layers = {}

    def _shared_layer(self, index):
        spec = self.layer_specs[index]
        key = spec["name"]
        if key not in self.shared_layers:
            if "air_gap_resistance" in spec:
                layer = openstudio.model.AirGap(self.model)
                layer.setName(spec["name"])
                layer.setThermalResistance(spec["air_gap_resistance"])
            else:
                layer = create_standard_material(self.model, spec["name"], spec["thickness"], spec["conductivity"],
                                                 spec["density"], spec["specific_heat"])
            self.shared_layers[key] = layer
        return self.shared_layers[key]

    def _face_layer(self, index, face, suffix):
        spec = self.layer_specs[index]
        name = f"{spec['name']} {suffix} a{face['solar']:.2f}"
        return create_standard_material(self.model, name, spec["thickness"], spec["conductivity"],
                                        spec["density"], spec["specific_heat"], face)

    def get(self, outside_face, inside_face):
        key = (_absorptance_key(outside_face), _absorptance_key(inside_face))
        if key in self.cache:
            return self.cache[key]
        layers = openstudio.model.MaterialVector()
        last = len(self.layer_specs) - 1
        for index in range(len(self.layer_specs)):
            if index == 0:
                layers.append(self._face_layer(index, outside_face, "Outside"))
            elif index == last:
                layers.append(self._face_layer(index, inside_face, "Inside"))
            else:
                layers.append(self._shared_layer(index))
        construction = openstudio.model.Construction(self.model)
        suffix = "" if not self.cache else f" {len(self.cache) + 1}"
        construction.setName(f"{self.base_name}{suffix}")
        construction.setLayers(layers)
        self.cache[key] = construction
        return construction


def apply_to_surfaces(surfaces, construction_for_surface):
    """
    Applies constructions to surfaces. For interzone pairs, the adjacent surface receives the reversed
    construction of the first surface processed, so both sides represent the same element.
    Returns the number of modified surfaces.
    """
    processed = set()
    count = 0
    for surface in surfaces:
        handle = str(surface.handle())
        if handle in processed:
            continue
        construction = construction_for_surface(surface)
        surface.setConstruction(construction)
        processed.add(handle)
        count += 1
        adjacent_opt = surface.adjacentSurface()
        if adjacent_opt.is_initialized():
            adjacent = adjacent_opt.get()
            adjacent_handle = str(adjacent.handle())
            if adjacent_handle not in processed:
                adjacent.setConstruction(construction.reverseConstruction())
                processed.add(adjacent_handle)
                count += 1
    return count
