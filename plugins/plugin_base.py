
class AstroPlugin:
    name = "BasePlugin"
    version = "1.0"

    def register(self, system):
        raise NotImplementedError("Plugin must implement register(system)")
