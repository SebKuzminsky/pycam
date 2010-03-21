import Tkinter
# "ode" is imported later, if required
#import ode_objects
import random


MODEL_TRANSFORMATIONS = {
    "normal": ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)),
    "x": ((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0)),
    "y": ((0, 0, -1, 0), (0, 1, 0, 0), (1, 0, 0, 0)),
    "z": ((0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 1, 0)),
    "xy": ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0)),
    "xz": ((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0)),
    "yz": ((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)),
    "x_swap_y": ((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0)),
    "x_swap_z": ((0, 0, 1, 0), (0, 1, 0, 0), (1, 0, 0, 0)),
    "y_swap_z": ((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0)),
}


def transform_model(model, direction="normal"):
    model.transform(MODEL_TRANSFORMATIONS[direction])

def shift_model(model, shift_x, shift_y, shift_z):
    matrix = ((1, 0, 0, shift_x), (0, 1, 0, shift_y), (0, 0, 1, shift_z))
    model.transform(matrix)
    
def scale_model(model, scale):
    matrix = ((scale, 0, 0, 0), (0, scale, 0, 0), (0, 0, scale, 0))
    model.transform(matrix)


class EmergencyDialog(Tkinter.Frame):
    """ This graphical message window requires no external dependencies.
    The Tk interface package is part of the main python distribution.
    Use this class for displaying dependency errors (especially on Windows).
    """

    def __init__(self, title, message):
        try:
            root = Tkinter.Tk()
        except Tkinter.TclError, err_msg:
            print >>sys.stderr, "Warning: Failed to create error dialog window (%s). Probably you are running PyCAM from a terminal." % str(err_msg)
            print >>sys.stderr, "%s: %s" % (title, message)
            return
        root.title(title)
        root.bind("<Return>", self.finish)
        root.bind("<Escape>", self.finish)
        root.minsize(300, 100)
        Tkinter.Frame.__init__(self, root, width=400)
        self.pack()
        # add text output as label
        message = Tkinter.Message(self, text=message, width=200)
        message["width"] = 200
        message.pack()
        # add the "close" button
        close = Tkinter.Button(root, text="Close")
        close["command"] = self.finish
        close.pack(side=Tkinter.BOTTOM)
        self.mainloop()

    def finish(self, *args):
        self.quit()


class ToolPathList(list):

    def add_toolpath(self, toolpath, name, cutter, *args):
        drill_id = self._get_drill_id(cutter)
        self.append(ToolPathInfo(toolpath, name, drill_id, cutter, *args))

    def _get_drill_id(self, cutter):
        used_ids = []
        # check if a drill with the same dimensions was used before
        for tp in self:
            if tp.drill == cutter:
                return tp.drill_id
            else:
                used_ids.append(tp.drill_id)
        # find the smallest unused drill id
        index = 1
        while index in used_ids:
            index += 1
        return index


class ToolPathInfo:

    def __init__(self, toolpath, name, drill_id, cutter, speed, feedrate,
            material_allowance, safety_height, unit, start_x, start_y, start_z):
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

