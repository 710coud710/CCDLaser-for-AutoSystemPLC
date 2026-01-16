"""
Camera Settings Service
Lưu và load camera settings vào AppData
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from .appPathService import getAppDirectory

logger = logging.getLogger(__name__)


class CameraSettingsService:
    """Service quản lý camera settings, lưu vào AppData"""
    
    def __init__(self):
        # Get AppData path
        self.settings_dir = self._get_settings_directory()
        
        # Create directory if not exists
        os.makedirs(self.settings_dir, exist_ok=True)
        
        # Settings file path
        self.settings_file = os.path.join(self.settings_dir, 'camera_settings.json')
        
        logger.info(f"CameraSettingsService initialized, settings dir: {self.settings_dir}")
    
    def _get_settings_directory(self) -> str:
        """Get settings directory in AppData"""
        if os.name == 'nt':  # Windows
            appdata = os.getenv('APPDATA')
            if appdata:
                settings_dir = os.path.join(appdata, 'CCDLaser', 'settings')
            else:
                # Fallback
                settings_dir = os.path.join(os.path.expanduser('~'), 'CCDLaser', 'settings')
        else:  # Linux/Mac
            settings_dir = os.path.join(os.path.expanduser('~'), '.ccdlaser', 'settings')
        
        return settings_dir
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save camera settings to AppData
        
        Args:
            settings: Dictionary chứa camera settings
        
        Returns:
            True nếu thành công
        """
        try:
            # Load existing settings if any
            existing_settings = self.load_settings() or {}
            
            # Merge with new settings
            existing_settings.update(settings)
            
            # Save to JSON
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Camera settings saved: {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save camera settings: {e}", exc_info=True)
            return False
    
    def load_settings(self) -> Optional[Dict[str, Any]]:
        """
        Load camera settings from AppData
        
        Returns:
            Dictionary chứa settings hoặc None nếu không có
        """
        try:
            if not os.path.exists(self.settings_file):
                logger.debug("No saved camera settings found")
                return None
            
            # Load from JSON
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            logger.info(f"Camera settings loaded: {self.settings_file}")
            return settings
            
        except Exception as e:
            logger.error(f"Failed to load camera settings: {e}", exc_info=True)
            return None
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default camera settings"""
        return {
            'exposure_time': 10000,  # microseconds
            'gain': 0,  # dB
            'brightness': 50,  # Gamma 1-100
            'contrast': 0,  # -100 to 100
            'saturation': 50,  # 0-100
            'zoom_width': 0,  # 0 = disabled
            'zoom_height': 0  # 0 = disabled
        }

