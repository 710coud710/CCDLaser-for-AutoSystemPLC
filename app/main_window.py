"""
Main Window - Gộp CCD1 và CCD2 vào 1 cửa sổ
Mỗi CCD chạy trong thread riêng, hoàn toàn độc lập
"""
import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main Window chứa cả CCD1 và CCD2
    Layout: CCD1 bên trái, CCD2 bên phải
    """
    
    def __init__(self, ccd1_view, ccd2_view):
        super().__init__()
        self._ccd1_view = ccd1_view
        self._ccd2_view = ccd2_view
        self._init_ui()
        logger.info("MainWindow initialized")
    
    def _init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("CCDLaser - Dual Camera System")
        self.setMinimumSize(1600, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - 2 cột
        main_layout = QHBoxLayout(central_widget)
        
        # Cột trái - CCD1
        main_layout.addWidget(self._ccd1_view, stretch=1)
        
        # Cột phải - CCD2
        main_layout.addWidget(self._ccd2_view, stretch=1)
        
        logger.info("MainWindow UI initialized")
    
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        logger.info("MainWindow closing...")
        event.accept()
