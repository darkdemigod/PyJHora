
from installer.installer import OneClickInstaller

class DesktopInstaller(OneClickInstaller):
    def install(self, target_path="~/ASTRO_OS"):
        print("Desktop installation started...")
        return super().install(target_path)
