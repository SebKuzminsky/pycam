GET_INDEX = 0
SET_INDEX = 1
VALUE_INDEX = 2

class Settings:
    
    def __init__(self):
        self.items = {}
        self.values = {}

    def add_item(self, key, get_func=None, set_func=None):
        self.items[key] = [None, None, None]
        self.define_get_func(key, get_func)
        self.define_set_func(key, set_func)
        self.items[key][VALUE_INDEX] = None

    def define_get_func(self, key, get_func=None):
        if not self.items.has_key(key):
            return
        if get_func is None:
            get_func = lambda: self.items[key][VALUE_INDEX]
        self.items[key][GET_INDEX] = get_func

    def define_set_func(self, key, set_func=None):
        if not self.items.has_key(key):
            return
        def default_set_func(value):
            self.items[key][VALUE_INDEX] = value
        if set_func is None:
            set_func = default_set_func
        self.items[key][SET_INDEX] = set_func

    def get(self, key, default=None):
        if self.items.has_key(key):
            return self.items[key][GET_INDEX]()
        else:
            return default

    def set(self, key, value):
        if not self.items.has_key(key):
            self.add_item(key)
        self.items[key][SET_INDEX](value)
        self.items[key][VALUE_INDEX] = value

    def __str__(self):
        result = {}
        for key in self.items.keys():
            result[key] = self.get(key)
        return str(result)

