from .appPathService import getAppDirectory
import yaml
import os
import logging

logger = logging.getLogger(__name__)


class SettingService:    
    def __init__(self):
        self.app_dir = getAppDirectory()
        self.setting_dir = os.path.join(self.app_dir, "setting")
        self.config = self.loadAllSetting()

    def loadAllSetting(self) -> dict:
        """
        Load tất cả setting files và merge lại
        - base_setting.yaml
        - camera.yaml
        - qr.yaml (future)
        """
        merged_config = {}
        
        # Load base settings
        base_path = os.path.join(self.setting_dir, "base_setting.yaml")
        if os.path.exists(base_path):
            try:
                with open(base_path, "r", encoding="utf-8") as f:
                    base_config = yaml.load(f, Loader=yaml.FullLoader)
                    if base_config:
                        merged_config.update(base_config)
                        logger.info("Loaded base_setting.yaml")
            except Exception as e:
                logger.error(f"Failed to load base_setting.yaml: {e}")
        
        # Load camera settings
        camera_path = os.path.join(self.setting_dir, "camera.yaml")
        if os.path.exists(camera_path):
            try:
                with open(camera_path, "r", encoding="utf-8") as f:
                    camera_config = yaml.load(f, Loader=yaml.FullLoader)
                    if camera_config:
                        merged_config.update(camera_config)
                        logger.info("Loaded camera.yaml")
            except Exception as e:
                logger.error(f"Failed to load camera.yaml: {e}")
        
        # Load QR settings (future)
        qr_path = os.path.join(self.setting_dir, "qr.yaml")
        if os.path.exists(qr_path):
            try:
                with open(qr_path, "r", encoding="utf-8") as f:
                    qr_config = yaml.load(f, Loader=yaml.FullLoader)
                    if qr_config:
                        merged_config.update(qr_config)
                        logger.info("Loaded qr.yaml")
            except Exception as e:
                logger.error(f"Failed to load qr.yaml: {e}")
        
        return merged_config

    def getSetting(self) -> dict:
        """Get toàn bộ config"""
        return self.config

    def getSettingValue(self, key: str, default=None):
        return self.config.get(key, default)


def getSettingService():
    """Factory function để tạo SettingService instance"""
    return SettingService()