import logging

# Configure the logger for this utility module
# The check `if not logging.getLogger(__name__).handlers:` prevents reconfiguring handlers
# if the module is reloaded or if logging has already been configured elsewhere.
if not logging.getLogger(__name__).handlers:
    logging.basicConfig(
        filename="assign_surface_properties.log",
        filemode="a",
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
logger = logging.getLogger(__name__)

# The mapping dictionary is now EMBEDDED directly within the module
# It is defined as a global constant for easy access.
SURFACE_TYPE_MAPPING = {
    "InteriorWall": {
        "outsideBoundaryCondition": "Surface",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "ExteriorWall": {
        "outsideBoundaryCondition": "Outdoors",
        "sunExposure": "SunExposed",
        "windExposure": "WindExposed"
    },
    "Roof": {
        "outsideBoundaryCondition": "Outdoors",
        "sunExposure": "SunExposed",
        "windExposure": "WindExposed"
    },
    "InteriorFloor": {
        "outsideBoundaryCondition": "Surface",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "ExposedFloor": {
        "outsideBoundaryCondition": "Outdoors",
        "sunExposure": "NoSun", # Generally no direct sun exposure for exposed floors below
        "windExposure": "WindExposed"
    },
    "Shade": { # Shading elements are not thermal surfaces, but can be mapped
        "outsideBoundaryCondition": "Outdoors",
        "sunExposure": "SunExposed",
        "windExposure": "WindExposed"
    },
    "UndergroundWall": {
        "outsideBoundaryCondition": "Ground",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "UndergroundSlab": { # Similar to UndergroundWall, but for slabs
        "outsideBoundaryCondition": "Ground",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "Ceiling": { # Ceiling adjacent to another conditioned or unconditioned space
        "outsideBoundaryCondition": "Surface",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "Air": { # Surfaces representing a boundary with an air cavity
        "outsideBoundaryCondition": "Surface",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "UndergroundCeiling": { # Ceiling above an underground space or ground
        "outsideBoundaryCondition": "Ground",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "RaisedFloor": { # Raised floor with a ventilated crawl space or exterior
        "outsideBoundaryCondition": "Outdoors",
        "sunExposure": "NoSun", # Generally no direct sun exposure
        "windExposure": "WindExposed"
    },
    "SlabOnGrade": { # Slab on grade
        "outsideBoundaryCondition": "Ground",
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "FreestandingColumn": { # Internal or external columns without direct contact with exterior or ground
        "outsideBoundaryCondition": "Adiabatic", # Assuming no significant heat exchange through a single face
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    },
    "EmbeddedColumn": { # Columns embedded in walls, floors, etc.
        "outsideBoundaryCondition": "Adiabatic", # Assuming heat exchange is handled by the main surface
        "sunExposure": "NoSun",
        "windExposure": "NoWind"
    }
}

def get_surface_mapping():
    """
    Returns the embedded surface mapping dictionary.
    This function acts as a wrapper to access the dictionary,
    allowing for future logic (like validation or copying) if needed,
    while maintaining a consistent interface.
    """
    logger.info("Surface mapping dictionary returned from the utility module.")
    return SURFACE_TYPE_MAPPING
