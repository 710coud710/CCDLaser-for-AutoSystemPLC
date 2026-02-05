"""
Camera Settings Service - Quản lý lưu trữ cài đặt camera
Lưu vào AppData/CCDLaser/camera_settings.json
"""
import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CameraSettingsService:
    """
    Service quản lý lưu trữ cài đặt camera
    - Lưu exposure, gain, brightness, contrast
    - Lưu vào AppData/CCDLaser/camera_settings.json
    """
    
    def __init__(self):
        # Lấy đường dẫn AppData
        self.appdata_dir = self._get_appdata_dir()
        self.settings_file = os.path.join(self.appdata_dir, "camera_settings.json")
        
        # Default settings
        self.default_settings = {
            "ccd1": {
                "exposure": 10000,  # μs
                "gain": 0,  # dB
                "brightness": 50,
                "contrast": 0
            },
            "ccd2": {
                "exposure": 10000,  # μs
                "gain": 0,  # dB
                "brightness": 50,
                "contrast": 0
            }
        }
        
        # Ensure directory exists
        os.makedirs(self.appdata_dir, exist_ok=True)
        
        logger.info(f"CameraSettingsService initialized. Settings file: {self.settings_file}")
    
    def _get_appdata_dir(self) -> str:
        """Lấy đường dẫn AppData/CCDLaser"""
        # Windows: C:\Users\<username>\AppData\Roaming\CCDLaser
        # Linux/Mac: ~/.config/CCDLaser
        
        if os.name == 'nt':  # Windows
            appdata = os.getenv('APPDATA')
            if appdata:
                return os.path.join(appdata, 'CCDLaser')
        
        # Linux/Mac fallback
        home = Path.home()
        return os.path.join(home, '.config', 'CCDLaser')
    
    def load_settings(self, camera_id: str = "ccd1") -> Dict[str, Any]:
        """
        Load settings cho camera
        
        Args:
            camera_id: "ccd1" hoặc "ccd2"
        
        Returns:
            Dict chứa settings: exposure, gain, brightness, contrast
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    all_settings = json.load(f)
                
                # Lấy settings cho camera cụ thể
                camera_settings = all_settings.get(camera_id, self.default_settings[camera_id])
                
                logger.info(f"Loaded settings for {camera_id}: {camera_settings}")
                return camera_settings
            else:
                logger.info(f"Settings file not found. Using default settings for {camera_id}")
                return self.default_settings[camera_id].copy()
        
        except Exception as e:
            logger.error(f"Failed to load settings for {camera_id}: {e}", exc_info=True)
            return self.default_settings[camera_id].copy()
    
    def save_settings(self, camera_id: str, settings: Dict[str, Any]) -> bool:
        """
        Save settings cho camera
        
        Args:
            camera_id: "ccd1" hoặc "ccd2"
            settings: Dict chứa exposure, gain, brightness, contrast
        
        Returns:
            True nếu save thành công
        """
        try:
            # Load all settings
            all_settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    all_settings = json.load(f)
            else:
                all_settings = self.default_settings.copy()
            
            # Update settings cho camera cụ thể
            all_settings[camera_id] = settings
            
            # Save to file
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(all_settings, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Saved settings for {camera_id}: {settings}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save settings for {camera_id}: {e}", exc_info=True)
            return False
    
    def update_parameter(self, camera_id: str, param_name: str, value: Any) -> bool:
        """
        Update một parameter cụ thể
        
        Args:
            camera_id: "ccd1" hoặc "ccd2"
            param_name: "exposure", "gain", "brightness", "contrast"
            value: Giá trị mới
        
        Returns:
            True nếu update thành công
        """
        try:
            # Load current settings
            settings = self.load_settings(camera_id)
            
            # Update parameter
            settings[param_name] = value
            
            # Save back
            return self.save_settings(camera_id, settings)
        
        except Exception as e:
            logger.error(f"Failed to update {param_name} for {camera_id}: {e}", exc_info=True)
            return False
    
    def get_parameter(self, camera_id: str, param_name: str) -> Optional[Any]:
        """
        Lấy giá trị của một parameter
        
        Args:
            camera_id: "ccd1" hoặc "ccd2"
            param_name: "exposure", "gain", "brightness", "contrast"
        
        Returns:
            Giá trị của parameter hoặc None
        """
        try:
            settings = self.load_settings(camera_id)
            return settings.get(param_name)
        except Exception as e:
            logger.error(f"Failed to get {param_name} for {camera_id}: {e}", exc_info=True)
            return None
    
    def reset_to_default(self, camera_id: str) -> bool:
        """
        Reset settings về default
        
        Args:
            camera_id: "ccd1" hoặc "ccd2"
        
        Returns:
            True nếu reset thành công
        """
        try:
            default = self.default_settings[camera_id].copy()
            return self.save_settings(camera_id, default)
        except Exception as e:
            logger.error(f"Failed to reset settings for {camera_id}: {e}", exc_info=True)
            return False
