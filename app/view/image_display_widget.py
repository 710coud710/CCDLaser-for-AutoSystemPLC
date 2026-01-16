"""
Image Display Widget - Widget hiển thị ảnh với khả năng chọn ROI bằng chuột
"""
import logging
from typing import Optional, Callable
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QMouseEvent, QPaintEvent

logger = logging.getLogger(__name__)


class ImageDisplayWidget(QLabel):
    """
    Custom QLabel để hiển thị ảnh và cho phép chọn ROI bằng chuột
    
    Signals:
        roi_selected: Emit khi user chọn xong ROI (x, y, width, height) - tọa độ ảnh gốc
    """
    
    roi_selected = Signal(int, int, int, int)  # x, y, width, height
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ROI selection state
        self._roi_selection_active = False
        self._roi_start_point: Optional[QPoint] = None
        self._roi_end_point: Optional[QPoint] = None
        self._current_roi_rect: Optional[QRect] = None
        
        # Original pixmap (before scaling)
        self._original_pixmap: Optional[QPixmap] = None
        
        # Mouse tracking
        self.setMouseTracking(True)
        
        # Style
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 2px solid #555;
                color: #888;
            }
        """)
        self.setText("No Image")
        
        logger.info("ImageDisplayWidget initialized")
    
    def set_image(self, pixmap: QPixmap):
        """Set image to display"""
        self._original_pixmap = pixmap
        self._update_display()
    
    def start_roi_selection(self):
        """Bắt đầu chế độ chọn ROI"""
        logger.info("ROI selection started")
        self._roi_selection_active = True
        self._roi_start_point = None
        self._roi_end_point = None
        self._current_roi_rect = None
        self.setCursor(Qt.CrossCursor)
        self._update_display()
    
    def cancel_roi_selection(self):
        """Hủy chế độ chọn ROI"""
        logger.info("ROI selection cancelled")
        self._roi_selection_active = False
        self._roi_start_point = None
        self._roi_end_point = None
        self._current_roi_rect = None
        self.setCursor(Qt.ArrowCursor)
        self._update_display()
    
    def _update_display(self):
        """Cập nhật hiển thị"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            self.setText("No Image")
            return
        
        # Scale pixmap to fit label
        scaled_pixmap = self._original_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Nếu đang vẽ ROI, vẽ lên pixmap
        if self._roi_selection_active and self._roi_start_point and self._roi_end_point:
            scaled_pixmap = scaled_pixmap.copy()  # Make a copy to draw on
            painter = QPainter(scaled_pixmap)
            
            # Draw ROI rectangle
            pen = QPen(QColor(0, 255, 0), 2, Qt.SolidLine)
            painter.setPen(pen)
            
            # Convert points to rect
            x1 = min(self._roi_start_point.x(), self._roi_end_point.x())
            y1 = min(self._roi_start_point.y(), self._roi_end_point.y())
            x2 = max(self._roi_start_point.x(), self._roi_end_point.x())
            y2 = max(self._roi_start_point.y(), self._roi_end_point.y())
            
            roi_rect = QRect(x1, y1, x2 - x1, y2 - y1)
            painter.drawRect(roi_rect)
            
            # Draw size info
            painter.setPen(QColor(0, 255, 0))
            text = f"{roi_rect.width()} x {roi_rect.height()}"
            painter.drawText(x1, y1 - 5, text)
            
            painter.end()
        
        self.setPixmap(scaled_pixmap)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Mouse press - bắt đầu vẽ ROI"""
        if not self._roi_selection_active:
            return super().mousePressEvent(event)
        
        if event.button() == Qt.LeftButton:
            # Get position on pixmap (not widget)
            pixmap_pos = self._widget_pos_to_pixmap_pos(event.pos())
            if pixmap_pos:
                self._roi_start_point = pixmap_pos
                self._roi_end_point = pixmap_pos
                logger.info(f"ROI start: {pixmap_pos.x()}, {pixmap_pos.y()}")
        
        return super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Mouse move - cập nhật ROI đang vẽ"""
        if not self._roi_selection_active:
            return super().mouseMoveEvent(event)
        
        if self._roi_start_point:
            # Get position on pixmap
            pixmap_pos = self._widget_pos_to_pixmap_pos(event.pos())
            if pixmap_pos:
                self._roi_end_point = pixmap_pos
                self._update_display()
        
        return super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Mouse release - hoàn thành vẽ ROI"""
        if not self._roi_selection_active:
            return super().mouseReleaseEvent(event)
        
        if event.button() == Qt.LeftButton and self._roi_start_point:
            # Get position on pixmap
            pixmap_pos = self._widget_pos_to_pixmap_pos(event.pos())
            if pixmap_pos:
                self._roi_end_point = pixmap_pos
                
                # Calculate ROI in original image coordinates
                scale_x = self._original_pixmap.width() / self.pixmap().width()
                scale_y = self._original_pixmap.height() / self.pixmap().height()
                
                x1 = int(min(self._roi_start_point.x(), self._roi_end_point.x()) * scale_x)
                y1 = int(min(self._roi_start_point.y(), self._roi_end_point.y()) * scale_y)
                x2 = int(max(self._roi_start_point.x(), self._roi_end_point.x()) * scale_x)
                y2 = int(max(self._roi_start_point.y(), self._roi_end_point.y()) * scale_y)
                
                width = x2 - x1
                height = y2 - y1
                
                # Validate ROI size
                if width > 10 and height > 10:
                    logger.info(f"ROI selected: ({x1}, {y1}, {width}, {height})")
                    self.roi_selected.emit(x1, y1, width, height)
                    
                    # End selection mode
                    self.cancel_roi_selection()
                else:
                    logger.warning("ROI too small, ignored")
                    self._roi_start_point = None
                    self._roi_end_point = None
                    self._update_display()
        
        return super().mouseReleaseEvent(event)
    
    def _widget_pos_to_pixmap_pos(self, widget_pos: QPoint) -> Optional[QPoint]:
        """Chuyển đổi tọa độ widget sang tọa độ pixmap (scaled)"""
        if self.pixmap() is None or self.pixmap().isNull():
            return None
        
        # Get pixmap rect (centered in label)
        pixmap_rect = self.pixmap().rect()
        label_rect = self.rect()
        
        # Calculate offset (pixmap is centered)
        offset_x = (label_rect.width() - pixmap_rect.width()) // 2
        offset_y = (label_rect.height() - pixmap_rect.height()) // 2
        
        # Convert widget pos to pixmap pos
        pixmap_x = widget_pos.x() - offset_x
        pixmap_y = widget_pos.y() - offset_y
        
        # Check if within pixmap bounds
        if 0 <= pixmap_x < pixmap_rect.width() and 0 <= pixmap_y < pixmap_rect.height():
            return QPoint(pixmap_x, pixmap_y)
        
        return None
    
    def resizeEvent(self, event):
        """Handle resize - update display"""
        super().resizeEvent(event)
        self._update_display()
    
    def paintEvent(self, event: QPaintEvent):
        """Custom paint event"""
        super().paintEvent(event)
        
        # Draw instruction text if in selection mode
        if self._roi_selection_active and not self._roi_start_point:
            painter = QPainter(self)
            painter.setPen(QColor(0, 255, 0))
            painter.drawText(
                self.rect(),
                Qt.AlignTop | Qt.AlignHCenter,
                "Click and drag to select ROI"
            )
            painter.end()

