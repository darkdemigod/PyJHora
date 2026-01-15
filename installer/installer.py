
import os
import shutil

class OneClickInstaller:
    def install(self, target_path):
        os.makedirs(target_path, exist_ok=True)
        print("Installing ASTRO_OS to", target_path)
        return True
