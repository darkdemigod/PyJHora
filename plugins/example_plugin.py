
from plugins.plugin_base import AstroPlugin

class ExamplePlugin(AstroPlugin):
    name = "ExamplePlugin"
    version = "1.0"

    def register(self, system):
        system["example_plugin"] = "Loaded"
