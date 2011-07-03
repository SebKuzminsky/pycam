# -*- coding: utf-8 -*-
"""
$Id: __init__.py 1061 2011-04-12 13:14:12Z sumpfralle $

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

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

# imported later (on demand)
#import gtk

import pycam.Plugins


class Models(pycam.Plugins.ListPluginBase):

    UI_FILE = "models.ui"

    def setup(self):
        if self.gui:
            import gtk
            model_frame = self.gui.get_object("ModelBox")
            model_frame.unparent()
            self.core.register_ui("main", "Models", model_frame, -50)
            model_handling_obj = self.gui.get_object("ModelHandlingNotebook")
            def clear_model_handling_obj():
                for index in range(model_handling_obj.get_n_pages()):
                    model_handling_obj.remove_page(0)
            def add_model_handling_item(item, name):
                model_handling_obj.append_page(item, gtk.Label(name))
            self.core.register_ui_section("model_handling",
                    add_model_handling_item, clear_model_handling_obj)
            self._modelview = self.gui.get_object("ModelView")
            for action, obj_name in ((self.ACTION_UP, "ModelMoveUp"),
                    (self.ACTION_DOWN, "ModelMoveDown"),
                    (self.ACTION_DELETE, "ModelDelete"),
                    (self.ACTION_CLEAR, "ModelDeleteAll")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            treemodel = self.gui.get_object("ModelList")
            def update_model():
                treemodel.clear()
                for index in range(len(self)):
                    treemodel.append((self[index], ))
            # clean the model now
            self.register_model_update(update_model)
            #update_model()
        self.core.add_item("models", lambda: self)
        return True

    def get_selected(self):
        return self._get_selected(self._modelview, force_list=True)

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ModelBox"))
            self.core.unregister_ui_section("main", "model_handling")
        self.core.set("models", None)
        return True

