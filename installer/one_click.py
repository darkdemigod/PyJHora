
from installer.desktop_installer import DesktopInstaller
from installer.android_installer import AndroidInstaller

def run_all():
    DesktopInstaller().install()
    AndroidInstaller().install()
    print("One-click install complete")
