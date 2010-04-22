__all__ = ["ToolPathList", "ToolPath", "Generator"]

import random

class ToolPathList(list):

    def add_toolpath(self, toolpath, name, tool_settings, *args):
        self.append(ToolPath(toolpath, name, tool_settings, *args))

class ToolPath:

    def __init__(self, toolpath, name, tool_settings, tool_id, speed,
            feedrate, material_allowance, safety_height, unit, start_x,
            start_y, start_z, bounding_box):
        self.toolpath = toolpath
        self.name = name
        self.visible = True
        self.tool_id = tool_id
        self.tool_settings = tool_settings
        self.speed = speed
        self.feedrate = feedrate
        self.material_allowance = material_allowance
        self.safety_height = safety_height
        self.unit = unit
        self.start_x = start_x
        self.start_y = start_y
        self.start_z = start_z
        self.bounding_box = bounding_box
        self.color = None
        # generate random color
        self.set_color()

    def get_path(self):
        return self.toolpath

    def set_color(self, color=None):
        if color is None:
            self.color = (random.random(), random.random(), random.random())
        else:
            self.color = color


