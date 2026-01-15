
from plugins.plugin_loader import PluginLoader

class PluginHook:
    def __init__(self):
        self.loader = PluginLoader()

    def load(self, system):
        return self.loader.load_all(system)
