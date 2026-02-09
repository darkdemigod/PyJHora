
#!/usr/bin/env python3
"""
JHora 4.5.0 - Vedic Astrology Application
Main entry point for the application
"""

import sys
import os

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from jhora.ui.horo_chart_tabs import HoroChartTabs
from jhora.ui.panchangam import Panchanga
from jhora.ui.vedic_calendar import VedicCalendar
from jhora.ui.match_ui import MatchUI
from jhora import utils
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

def except_hook(cls, exception, traceback):
    """Exception handler for PyQt"""
    print('Exception called:', exception)
    sys.__excepthook__(cls, exception, traceback)

class JHoraMainWindow(QMainWindow):
    """Main window for JHora application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JHora 4.5.0 - Vedic Astrology")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Initialize tabs
        self.init_tabs()
        
    def init_tabs(self):
        """Initialize all application tabs"""
        try:
            # Main horoscope charts tab
            self.horo_chart = HoroChartTabs()
            self.tab_widget.addTab(self.horo_chart, "Horoscope Charts")
            
            # Panchanga tab
            self.panchanga = Panchanga()
            self.tab_widget.addTab(self.panchanga, "Panchanga")
            
            # Vedic Calendar tab
            self.calendar = VedicCalendar()
            self.tab_widget.addTab(self.calendar, "Vedic Calendar")
            
            # Marriage compatibility tab
            self.match_ui = MatchUI()
            self.tab_widget.addTab(self.match_ui, "Marriage Compatibility")
            
        except Exception as e:
            print(f"Error initializing tabs: {e}")
            # Create a simple fallback tab
            from PyQt6.QtWidgets import QLabel
            fallback = QLabel(f"Error loading full UI: {e}\nPlease check dependencies.")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tab_widget.addTab(fallback, "Error")

def main():
    """Main entry point"""
    # Set exception hook
    sys.excepthook = except_hook
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("JHora")
    app.setApplicationVersion("4.5.0")
    
    try:
        # Create and show main window
        window = JHoraMainWindow()
        window.show()
        
        # Start event loop
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Falling back to basic horoscope functionality...")
        
        # Fallback to basic panchanga if full UI not available
        try:
            chart = Panchanga()
            chart.show()
            sys.exit(app.exec())
        except Exception as fallback_error:
            print(f"Fallback failed: {fallback_error}")
            print("Please install missing dependencies: pip install pyswisseph pyqt6")
            sys.exit(1)
    
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
