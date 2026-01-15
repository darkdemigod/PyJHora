
from installer.installer import OneClickInstaller

class AndroidInstaller(OneClickInstaller):
    def install(self, target_path="/sdcard/ASTRO_OS"):
        print("Android installation started...")
        return super().install(target_path)
