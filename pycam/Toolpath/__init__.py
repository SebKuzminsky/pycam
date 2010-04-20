import random

class ToolPathList(list):

    def add_toolpath(self, toolpath, name, cutter, *args):
        self.append(ToolPath(toolpath, name, cutter, *args))

class ToolPath:

    def __init__(self, toolpath, name, cutter, drill_id, speed, feedrate,
            material_allowance, safety_height, unit, start_x, start_y, start_z, bounding_box):
        self.toolpath = toolpath
        self.name = name
        self.visible = True
        self.drill_id = drill_id
        self.drill = cutter
        self.drill_size = cutter.radius
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


