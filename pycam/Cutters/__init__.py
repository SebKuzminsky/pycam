list = [ "SphericalCutter", "CylindricalCutter", "ToroidalCutter" ]
__all__ = [ "BaseCutter" ] + list

from BaseCutter import BaseCutter
from SphericalCutter import SphericalCutter
from CylindricalCutter import CylindricalCutter
from ToroidalCutter import ToroidalCutter


def get_tool_from_settings(tool_settings, height=None):
    """ get the tool specified by the relevant settings

    The settings must include:
      - "shape": one of "SphericalCutter", "CylindricalCutter" and
        "ToroidalCutter"
      - "radius": the tool radius
    The following settings are optional or shape specific:
      - "torus_radius": necessary for ToroidalCutter

    @type tool_settings: dict
    @value tool_settings: contains the attributes of the tool
    @type height: float
    @value height: the height of the tool
    @rtype: BaseCutter | basestring
    @return: a tool object or an error string
    """
    cuttername = tool_settings["shape"]
    radius = tool_settings["radius"]
    if cuttername == "SphericalCutter":
        return SphericalCutter(radius, height=height)
    elif cuttername == "CylindricalCutter":
        return CylindricalCutter(radius, height=height)
    elif cuttername == "ToroidalCutter":
        toroid = tool_settings["torus_radius"]
        return ToroidalCutter(radius, toroid, height=height)
    else:
        return "Invalid cutter shape: '%s' is not one of %s" % (cuttername, TOOL_SHAPES)

