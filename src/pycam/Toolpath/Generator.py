# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

from pycam.PathGenerators import DropCutter, PushCutter, EngraveCutter, \
        ContourFollow
from pycam.Geometry.utils import number
from pycam.PathProcessors import PathAccumulator, SimpleCutter, ZigZagCutter, \
        PolygonCutter, ContourCutter
from pycam.Cutters.CylindricalCutter import CylindricalCutter
import pycam.Cutters
import pycam.Toolpath.SupportGrid
import pycam.Toolpath.MotionGrid
import pycam.Toolpath
import pycam.Geometry.Model
from pycam.Utils import ProgressCounter
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


DIRECTIONS = frozenset(("x", "y", "xy"))
PATH_GENERATORS = frozenset(("DropCutter", "PushCutter", "EngraveCutter",
        "ContourFollow"))
PATH_POSTPROCESSORS = frozenset(("ContourCutter", "PathAccumulator",
        "PolygonCutter", "SimpleCutter", "ZigZagCutter"))
CALCULATION_BACKENDS = frozenset((None, "ODE"))


def generate_toolpath_from_settings(model, tp_settings, callback=None):
    process = tp_settings.get_process_settings()
    support_model = tp_settings.get_support_model()
    backend = tp_settings.get_calculation_backend()
    return generate_toolpath(model, tp_settings.get_tool_settings(),
            tp_settings.get_bounds(), process["path_direction"],
            process["generator"], process["postprocessor"],
            process["material_allowance"], process["overlap_percent"],
            process["step_down"], process["engrave_offset"],
            process["milling_style"], process["pocketing_type"],
            support_model, backend, callback)

def generate_toolpath(model, tool_settings=None,
        bounds=None, direction="x",
        path_generator="DropCutter", path_postprocessor="ZigZagCutter",
        material_allowance=0, overlap_percent=0, step_down=0, engrave_offset=0,
        milling_style="ignore", pocketing_type="none",
        support_model=None, calculation_backend=None, callback=None):
    """ abstract interface for generating a toolpath

    @type model: pycam.Geometry.Model.Model
    @value model: a model contains surface triangles or a contour
    @type tool_settings: dict
    @value tool_settings: contains at least the following keys (depending on
        the tool type):
        "shape": any of possible cutter shape (see "pycam.Cutters")
        "tool_radius": main radius of the tools
        "torus_radius": (only for ToroidalCutter) second toroidal radius
    @type bounds_low: tuple(float) | list(float)
    @value bounds_low: the lower processing boundary (used for the center of
        the tool) (order: minx, miny, minz)
    @type bounds_high: tuple(float) | list(float)
    @value bounds_high: the lower processing boundary (used for the center of
        the tool) (order: maxx, maxy, maxz)
    @type direction: str
    @value direction: any member of the DIRECTIONS set (e.g. "x", "y" or "xy")
    @type path_generator: str
    @value path_generator: any member of the PATH_GENERATORS set
    @type path_postprocessor: str
    @value path_postprocessor: any member of the PATH_POSTPROCESSORS set
    @type material_allowance: float
    @value material_allowance: the minimum distance between the tool and the model
    @type overlap_percent: int
    @value overlap_percent: the overlap between two adjacent tool paths (0..100) given in percent
    @type step_down: float
    @value step_down: maximum height of each layer (for PushCutter)
    @type engrave_offset: float
    @value engrave_offset: toolpath distance to the contour model
    @type calculation_backend: str | None
    @value calculation_backend: any member of the CALCULATION_BACKENDS set
        The default is the triangular collision detection.
    @rtype: pycam.Toolpath.Toolpath | str
    @return: the resulting toolpath object or an error string in case of invalid
        arguments
    """
    log.debug("Starting toolpath generation")
    step_down = number(step_down)
    engrave_offset = number(engrave_offset)
    if bounds is None:
        # no bounds were given - we use the boundaries of the model
        bounds = pycam.Toolpath.Bounds(pycam.Toolpath.Bounds.TYPE_CUSTOM,
                (model.minx, model.miny, model.minz),
                (model.maxx, model.maxy, model.maxz))
    bounds_low, bounds_high = bounds.get_absolute_limits()
    minx, miny, minz = [number(value) for value in bounds_low]
    maxx, maxy, maxz = [number(value) for value in bounds_high]
    # trimesh model or contour model?
    if isinstance(model, pycam.Geometry.Model.ContourModel):
        # contour model
        trimesh_models = []
        contour_model = model
    else:
        # trimesh model
        trimesh_models = [model]
        contour_model = None
    # Due to some weirdness the height of the drill must be bigger than the
    # object's size. Otherwise some collisions are not detected.
    cutter_height = 4 * abs(maxz - minz)
    cutter = pycam.Cutters.get_tool_from_settings(tool_settings, cutter_height)
    if isinstance(cutter, basestring):
        return cutter
    if not path_generator in ("EngraveCutter", "ContourFollow"):
        # material allowance is not available for these two strategies
        cutter.set_required_distance(material_allowance)
    # create the grid model if requested
    if support_model:
        trimesh_models.append(support_model)
    # Adapt the contour_model to the engraving offset. This offset is
    # considered to be part of the material_allowance.
    if contour_model and (engrave_offset != 0):
        if not callback is None:
            callback(text="Preparing contour model with offset ...")
        contour_model = contour_model.get_offset_model(engrave_offset,
                callback=callback)
        if contour_model:
            return "Failed to calculate offset polygons"
        if not callback is None:
            # reset percentage counter after the contour model calculation
            callback(percent=0)
            if callback(text="Checking contour model with offset for " \
                    + "collisions ..."):
                # quit requested
                return None
            progress_callback = ProgressCounter(
                    len(contour_model.get_polygons()), callback).increment
        else:
            progress_callback = None
        result = contour_model.check_for_collisions(callback=progress_callback)
        if result is None:
            return None
        elif result:
            warning = "The contour model contains colliding line groups. " + \
                    "This can cause problems with an engraving offset.\n" + \
                    "A collision was detected at (%.2f, %.2f, %.2f)." % \
                    (result.x, result.y, result.z)
            log.warning(warning)
        else:
            # no collisions and no user interruption
            pass
    # check the pocketing type
    if contour_model and (pocketing_type != "none"):
        if not callback is None:
            callback(text="Generating pocketing polygons ...")
        pocketing_offset = cutter.radius * 1.8
        # TODO: this is an arbitrary limit to avoid infinite loops
        pocketing_limit = 1000
        base_polygons = []
        other_polygons = []
        if pocketing_type == "holes":
            # fill polygons with negative area
            for poly in contour_model.get_polygons():
                if poly.is_closed and not poly.is_outer():
                    base_polygons.append(poly)
                else:
                    other_polygons.append(poly)
        elif pocketing_type == "enclosed":
            # fill polygons with positive area
            pocketing_offset *= -1
            for poly in contour_model.get_polygons():
                if poly.is_closed and poly.is_outer():
                    base_polygons.append(poly)
                else:
                    other_polygons.append(poly)
        else:
            return "Unknown pocketing type given (not one of 'none', " + \
                    "'holes', 'enclosed'): %s" % str(pocketing_type)
        # For now we use only the polygons that do not surround eny other
        # polygons. Sorry - the pocketing is currently very simple ...
        base_filtered_polygons = []
        for candidate in base_polygons:
            if callback and callback():
                return "Interrupted"
            for other in other_polygons:
                if candidate.is_polygon_inside(other):
                    break
            else:
                base_filtered_polygons.append(candidate)
        # start the pocketing for all remaining polygons
        pocket_polygons = []
        for base_polygon in base_filtered_polygons:
            current_queue = [base_polygon]
            next_queue = []
            pocket_depth = 0
            while current_queue and (pocket_depth < pocketing_limit):
                if callback and callback():
                    return "Interrupted"
                for poly in current_queue:
                    result = poly.get_offset_polygons(pocketing_offset)
                    pocket_polygons.extend(result)
                    next_queue.extend(result)
                    pocket_depth += 1
                current_queue = next_queue
                next_queue = []
        # use a copy instead of the original
        contour_model = contour_model.get_copy()
        for pocket in pocket_polygons:
            contour_model.append(pocket)
    # limit the contour model to the bounding box
    if contour_model:
        # use minz/maxz of the contour model (in other words: ignore z)
        contour_model = contour_model.get_cropped_model(minx, maxx, miny, maxy,
                contour_model.minz, contour_model.maxz)
        if contour_model:
            return "No part of the contour model is within the bounding box."
    physics = _get_physics(trimesh_models, cutter, calculation_backend)
    if isinstance(physics, basestring):
        return physics
    generator = _get_pathgenerator_instance(trimesh_models, contour_model,
            cutter, path_generator, path_postprocessor, physics,
            milling_style)
    if isinstance(generator, basestring):
        return generator
    overlap = overlap_percent / 100.0
    if (overlap < 0) or (overlap >= 1):
        return "Invalid overlap value (%f): should be greater or equal 0 " \
                + "and lower than 1"
    # factor "2" since we are based on radius instead of diameter
    line_stepping = 2 * number(tool_settings["tool_radius"]) * (1 - overlap)
    if path_generator == "PushCutter":
        step_width = None
    else:
        # the step_width is only used for the DropCutter
        step_width = tool_settings["tool_radius"] / 4
    if path_generator == "DropCutter":
        layer_distance = None
    else:
        layer_distance = step_down
    direction_dict = {"x": pycam.Toolpath.MotionGrid.GRID_DIRECTION_X,
            "y": pycam.Toolpath.MotionGrid.GRID_DIRECTION_Y,
            "xy": pycam.Toolpath.MotionGrid.GRID_DIRECTION_XY}
    milling_style_grid = {
            "ignore": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
            "conventional": pycam.Toolpath.MotionGrid.MILLING_STYLE_CONVENTIONAL,
            "climb": pycam.Toolpath.MotionGrid.MILLING_STYLE_CLIMB}
    if path_generator in ("DropCutter", "PushCutter"):
        motion_grid = pycam.Toolpath.MotionGrid.get_fixed_grid(
                (bounds_low, bounds_high), layer_distance, line_stepping,
                step_width=step_width, grid_direction=direction_dict[direction],
                milling_style=milling_style_grid[milling_style])
        if path_generator == "DropCutter":
            toolpath = generator.GenerateToolPath(motion_grid, minz, maxz,
                    callback)
        else:
            toolpath = generator.GenerateToolPath(motion_grid, callback)
    elif path_generator == "EngraveCutter":
        if step_down > 0:
            dz = step_down
        else:
            dz = maxz - minz
        toolpath = generator.GenerateToolPath(minz, maxz, step_width, dz,
                callback)
    elif path_generator == "ContourFollow":
        if step_down > 0:
            dz = step_down
        else:
            dz = maxz - minz
            if dz <= 0:
                dz = 1
        toolpath = generator.GenerateToolPath(minx, maxx, miny, maxy, minz,
                maxz, dz, callback)
    else:
        return "Invalid path generator (%s): not one of %s" \
                % (path_generator, PATH_GENERATORS)
    return toolpath
    
def _get_pathgenerator_instance(trimesh_models, contour_model, cutter,
        pathgenerator, pathprocessor, physics, milling_style):
    if pathgenerator != "EngraveCutter" and contour_model:
        return ("The only available toolpath strategy for 2D contour models " \
                + "is 'Engraving'.")
    if pathgenerator == "DropCutter":
        if pathprocessor == "ZigZagCutter":
            processor = PathAccumulator.PathAccumulator(zigzag=True)
        elif pathprocessor == "PathAccumulator":
            processor = PathAccumulator.PathAccumulator()
        else:
            return ("Invalid postprocessor (%s) for 'DropCutter': only " \
                    + "'ZigZagCutter' or 'PathAccumulator' are allowed") \
                    % str(pathprocessor)
        return DropCutter.DropCutter(cutter, trimesh_models, processor,
                physics=physics)
    elif pathgenerator == "PushCutter":
        if pathprocessor == "PathAccumulator":
            processor = PathAccumulator.PathAccumulator()
        elif pathprocessor == "SimpleCutter":
            processor = SimpleCutter.SimpleCutter()
        elif pathprocessor == "ZigZagCutter":
            processor = ZigZagCutter.ZigZagCutter()
        elif pathprocessor == "PolygonCutter":
            processor = PolygonCutter.PolygonCutter()
        elif pathprocessor == "ContourCutter":
            processor = ContourCutter.ContourCutter()
        else:
            return ("Invalid postprocessor (%s) for 'PushCutter' - it " + \
                    "should be one of these: %s") % \
                    (pathprocessor, PATH_POSTPROCESSORS)
        return PushCutter.PushCutter(cutter, trimesh_models, processor,
                physics=physics)
    elif pathgenerator == "EngraveCutter":
        clockwise = (milling_style == "climb")
        if pathprocessor == "SimpleCutter":
            processor = SimpleCutter.SimpleCutter()
        else:
            return ("Invalid postprocessor (%s) for 'EngraveCutter' - it " \
                    + "should be: SimpleCutter") % str(pathprocessor)
        if not contour_model:
            return "The 'Engraving' toolpath strategy requires a 2D contour " \
                    + "model (e.g. from a DXF or SVG file)."
        return EngraveCutter.EngraveCutter(cutter, trimesh_models,
                contour_model, processor, clockwise=clockwise, physics=physics)
    elif pathgenerator == "ContourFollow":
        reverse = (milling_style == "conventional")
        if pathprocessor == "SimpleCutter":
            processor = SimpleCutter.SimpleCutter(reverse=reverse)
        else:
            return ("Invalid postprocessor (%s) for 'ContourFollow' - it " \
                    + "should be: SimpleCutter") % str(pathprocessor)
        if not isinstance(cutter, CylindricalCutter):
            log.warn("The ContourFollow strategy only works reliably with " + \
                    "the cylindrical cutter shape. Maybe you should use " + \
                    "the alternative ContourPolygon strategy instead.")
        return ContourFollow.ContourFollow(cutter, trimesh_models, processor,
                physics=physics)
    else:
        return "Invalid path generator (%s): not one of %s" \
                % (pathgenerator, PATH_GENERATORS)

def _get_physics(models, cutter, calculation_backend):
    if calculation_backend is None:
        # triangular collision detection does not need any physical model
        return None
    elif calculation_backend == "ODE":
        import pycam.Physics.ode_physics as ode_physics
        try:
            return ode_physics.generate_physics(models, cutter)
        except MemoryError:
            return "The ODE library returned an unexpected error " + \
                    "condition. You need to to disable ODE for this " + \
                    "calculation. Sorry!"
    else:
        return "Invalid calculation backend (%s): not one of %s" \
                % (calculation_backend, CALCULATION_BACKENDS)

