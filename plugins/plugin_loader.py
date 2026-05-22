
import os
import importlib.util

class PluginLoader:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = []

    def load_all(self, system):
        for f in os.listdir(self.plugin_dir):
            if f.endswith(".py") and f not in ["plugin_base.py", "plugin_loader.py"]:
                path = os.path.join(self.plugin_dir, f)
                name = f[:-3]
                spec = importlib.util.spec_from_file_location(name, path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for obj in mod.__dict__.values():
                    try:
                        if hasattr(obj, "register"):
                            plugin = obj()
                            plugin.register(system)
                            self.plugins.append(plugin)
                    except Exception:
                        pass
        return self.plugins
