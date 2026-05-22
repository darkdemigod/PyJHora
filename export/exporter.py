
import json

class Exporter:
    def to_json(self, data, path):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
