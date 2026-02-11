
import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtNetwork import QTcpSocket, QHostAddress

logger = logging.getLogger(__name__)


class RemoteTcpClient(QObject):
    """TCP Client - kết nối đến server và gửi tín hiệu OK sau khi CCD capture hoàn tất"""
    connected = Signal()
    disconnected = Signal()
    messageReceived = Signal(str)  # message line (stripped)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._socket = QTcpSocket(self)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.readyRead.connect(self._on_ready_read)
        self._socket.errorOccurred.connect(self._on_error)
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._try_reconnect)
        self._reconnect_interval = 5000  # 5 seconds
        self._is_connected = False
        self._target_host = ""
        self._target_port = 0

    def connect_to_server(self, host: str, port: int) -> bool:
        """Kết nối đến TCP server"""
        try:
            self._target_host = host
            self._target_port = int(port)
            
            if not host or not port:
                logger.error("Invalid host or port for TCP client")
                return False
            
            addr = QHostAddress(host)
            logger.info(f"Connecting to TCP server at {host}:{port}...")
            self._socket.connectToHost(addr, self._target_port)
            return True
        except Exception as e:
            logger.error(f"RemoteTcpClient connect failed: {e}", exc_info=True)
            return False

    def disconnect_from_server(self):
        """Ngắt kết nối từ server"""
        try:
            self._reconnect_timer.stop()
            if self._socket.state() == QTcpSocket.SocketState.ConnectedState:
                self._socket.disconnectFromHost()
            self._is_connected = False
            logger.info("RemoteTcpClient disconnected")
        except Exception as e:
            logger.error(f"RemoteTcpClient disconnect failed: {e}", exc_info=True)

    def send_line(self, line: str):
        """Gửi một dòng text đến server"""
        if not self._is_connected or self._socket.state() != QTcpSocket.SocketState.ConnectedState:
            logger.warning("Cannot send line: not connected to server")
            return
        
        if not line.endswith("\n"):
            line = line + "\n"
        try:
            self._socket.write(line.encode("utf-8"))
            self._socket.flush()
            logger.debug(f"Sent to server: {line.strip()}")
        except Exception as e:
            logger.warning(f"Failed to send line to server: {e}")

    def send_ok(self, serial_number: str = ""):
        """Gửi tín hiệu OK đến server (sau khi CCD capture hoàn tất)
        
        Args:
            serial_number: Mã serial number (SN) để gửi kèm, ví dụ: "OK,PT526111603305RQ"
        """
        if serial_number:
            self.send_line(f"OK,{serial_number}")
        else:
            self.send_line("OK")
    
    def send_fail(self, serial_number: str = ""):
        """gửi fail"""
        if serial_number:
            self.send_line(f"FAIL,{serial_number}")
        else:
            self.send_line("FAIL")

    @Slot()
    def _on_connected(self):
        """Khi kết nố """
        self._is_connected = True
        self._reconnect_timer.stop()
        logger.info(f"Connected to TCP server at {self._target_host}:{self._target_port}")
        self.connected.emit()

    @Slot()
    def _on_disconnected(self):
        """Khi mất kết nối"""
        was_connected = self._is_connected
        self._is_connected = False
        logger.warning(f"Disconnected from TCP server")
        self.disconnected.emit()
        
        # Tự động reconnect nếu đã từng kết nối thành công
        if was_connected:
            logger.info(f"Will attempt to reconnect in {self._reconnect_interval/1000} seconds...")
            self._reconnect_timer.start(self._reconnect_interval)

    @Slot()
    def _on_ready_read(self):
        """Khi nhận được dữ liệu từ server"""
        try:
            data = bytes(self._socket.readAll()).decode("utf-8", errors="ignore")
            # Normalize to \n-delimited
            data = data.replace("\r\n", "\n").replace("\r", "\n")
            for line in data.split("\n"):
                msg = line.strip()
                if msg:
                    logger.debug(f"Received from server: {msg}")
                    self.messageReceived.emit(msg)
        except Exception as e:
            logger.warning(f"Error reading from server: {e}", exc_info=True)

    @Slot()
    def _on_error(self, error):
        """Xử lý lỗi kết nối"""
        logger.error(f"TCP socket error: {error} - {self._socket.errorString()}")

    @Slot()
    def _try_reconnect(self):
        """Thử kết nối lại"""
        if not self._is_connected:
            logger.info(f"Attempting to reconnect to {self._target_host}:{self._target_port}...")
            self.connect_to_server(self._target_host, self._target_port)

    def is_connected(self) -> bool:
        """Kiểm tra xem có đang kết nối không"""
        return self._is_connected and self._socket.state() == QTcpSocket.SocketState.ConnectedState

