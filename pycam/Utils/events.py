import pycam.Utils.log


log = pycam.Utils.log.get_logger()


UI_FUNC_INDEX, UI_WIDGET_INDEX = range(2)
WIDGET_NAME_INDEX, WIDGET_OBJ_INDEX, WIDGET_WEIGHT_INDEX, WIDGET_ARGS_INDEX = range(4)
HANDLER_FUNC_INDEX, HANDLER_ARG_INDEX = range(2)
EVENT_HANDLER_INDEX, EVENT_BLOCKER_INDEX = range(2)
CHAIN_FUNC_INDEX, CHAIN_WEIGHT_INDEX = range(2)


class EventCore(pycam.Gui.Settings.Settings):

    def __init__(self):
        super(EventCore, self).__init__()
        self.event_handlers = {}
        self.ui_sections = {}
        self.chains = {}
        self.state_dumps = []
        self.namespace = {}

    def register_event(self, event, func, *args):
        if event not in self.event_handlers:
            assert EVENT_HANDLER_INDEX == 0
            assert EVENT_BLOCKER_INDEX == 1
            self.event_handlers[event] = [[], 0]
        assert HANDLER_FUNC_INDEX == 0
        assert HANDLER_ARG_INDEX == 1
        self.event_handlers[event][EVENT_HANDLER_INDEX].append((func, args))

    def unregister_event(self, event, func):
        if event in self.event_handlers:
            removal_list = []
            handlers = self.event_handlers[event]
            for index, item in enumerate(handlers[EVENT_HANDLER_INDEX]):
                if func == item[HANDLER_FUNC_INDEX]:
                    removal_list.append(index)
            removal_list.reverse()
            for index in removal_list:
                handlers[EVENT_HANDLER_INDEX].pop(index)
        else:
            log.debug("Trying to unregister an unknown event: %s", event)

    def emit_event(self, event, *args, **kwargs):
        log.debug2("Event emitted: %s", str(event))
        if event in self.event_handlers:
            if self.event_handlers[event][EVENT_BLOCKER_INDEX] != 0:
                return
            # prevent infinite recursion
            self.block_event(event)
            for handler in self.event_handlers[event][EVENT_HANDLER_INDEX]:
                func = handler[HANDLER_FUNC_INDEX]
                data = handler[HANDLER_ARG_INDEX]
                func(*(data + args), **kwargs)
            self.unblock_event(event)
        else:
            log.debug("No events registered for event '%s'", str(event))

    def block_event(self, event):
        if event in self.event_handlers:
            self.event_handlers[event][EVENT_BLOCKER_INDEX] += 1
        else:
            log.debug("Trying to block an unknown event: %s", str(event))

    def unblock_event(self, event):
        if event in self.event_handlers:
            if self.event_handlers[event][EVENT_BLOCKER_INDEX] > 0:
                self.event_handlers[event][EVENT_BLOCKER_INDEX] -= 1
            else:
                log.debug("Trying to unblock non-blocked event '%s'", str(event))
        else:
            log.debug("Trying to unblock an unknown event: %s", str(event))

    def register_ui_section(self, section, add_action, clear_action):
        if section not in self.ui_sections:
            self.ui_sections[section] = [None, None]
            self.ui_sections[section][UI_WIDGET_INDEX] = []
        self.ui_sections[section][UI_FUNC_INDEX] = (add_action, clear_action)
        self._rebuild_ui_section(section)

    def unregister_ui_section(self, section):
        if section in self.ui_sections:
            ui_section = self.ui_sections[section]
            while ui_section[UI_WIDGET_INDEX]:
                ui_section[UI_WIDGET_INDEX].pop()
            del self.ui_sections[section]
        else:
            log.debug("Trying to unregister a non-existent ui section: %s", str(section))

    def _rebuild_ui_section(self, section):
        if section in self.ui_sections:
            ui_section = self.ui_sections[section]
            if ui_section[UI_FUNC_INDEX]:
                add_func, clear_func = ui_section[UI_FUNC_INDEX]
                ui_section[UI_WIDGET_INDEX].sort(key=lambda x: x[WIDGET_WEIGHT_INDEX])
                clear_func()
                for item in ui_section[UI_WIDGET_INDEX]:
                    if item[WIDGET_ARGS_INDEX]:
                        args = item[WIDGET_ARGS_INDEX]
                    else:
                        args = {}
                    add_func(item[WIDGET_OBJ_INDEX], item[WIDGET_NAME_INDEX], **args)
        else:
            log.debug("Failed to rebuild unknown ui section: %s", str(section))

    def register_ui(self, section, name, widget, weight=0, args_dict=None):
        if section not in self.ui_sections:
            self.ui_sections[section] = [None, None]
            self.ui_sections[section][UI_WIDGET_INDEX] = []
        assert WIDGET_NAME_INDEX == 0
        assert WIDGET_OBJ_INDEX == 1
        assert WIDGET_WEIGHT_INDEX == 2
        assert WIDGET_ARGS_INDEX == 3
        current_widgets = [item[1] for item in self.ui_sections[section][UI_WIDGET_INDEX]]
        if (widget is not None) and (widget in current_widgets):
            log.debug("Tried to register widget twice: %s -> %s", section, name)
            return
        self.ui_sections[section][UI_WIDGET_INDEX].append((name, widget, weight, args_dict))
        self._rebuild_ui_section(section)

    def unregister_ui(self, section, widget):
        if (section in self.ui_sections) or (None in self.ui_sections):
            if section not in self.ui_sections:
                section = None
            ui_section = self.ui_sections[section]
            removal_list = []
            for index, item in enumerate(ui_section[UI_WIDGET_INDEX]):
                if item[WIDGET_OBJ_INDEX] == widget:
                    removal_list.append(index)
            removal_list.reverse()
            for index in removal_list:
                ui_section[UI_WIDGET_INDEX].pop(index)
            self._rebuild_ui_section(section)
        else:
            log.debug("Trying to unregister unknown ui section: %s", section)

    def register_chain(self, name, func, weight=100):
        if name not in self.chains:
            self.chains[name] = []
        self.chains[name].append((func, weight))
        self.chains[name].sort(key=lambda item: item[CHAIN_WEIGHT_INDEX])

    def unregister_chain(self, name, func):
        if name in self.chains:
            for index, data in enumerate(self.chains[name]):
                if data[CHAIN_FUNC_INDEX] == func:
                    self.chains[name].pop(index)
                    break
            else:
                log.debug("Trying to unregister unknown function from %s: %s", name, func)
        else:
            log.debug("Trying to unregister from unknown chain: %s", name)

    def call_chain(self, name, *args, **kwargs):
        if name in self.chains:
            for data in self.chains[name]:
                data[CHAIN_FUNC_INDEX](*args, **kwargs)
        else:
            log.debug("Called an unknown chain: %s", name)

    def reset_state(self):
        pass

    def register_namespace(self, name, value):
        if name in self.namespace:
            log.info("Trying to register the same key in namespace twice: %s", str(name))
        self.namespace[name] = value

    def unregister_namespace(self, name):
        if name not in self.namespace:
            log.info("Tried to unregister an unknown name from namespace: %s", str(name))

    def get_namespace(self):
        return self.namespace


