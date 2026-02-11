"""
Test script for MVS Camera connection
Test kết nối với MVS camera theo tutorial
"""
import sys
import os
import logging
import yaml

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_camera_config():
    """Load camera config from YAML"""
    config_path = os.path.join(project_root, 'setting', 'camera.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return config_data.get('camera', {})
    except Exception as e:
        logger.error(f"Failed to load camera config: {e}")
        return {}


def test_mvs_camera():
    """Test MVS camera connection"""
    logger.info("=" * 80)
    logger.info("MVS CAMERA CONNECTION TEST")
    logger.info("=" * 80)
    
    try:
        # Import camera service
        from app.model.camera import CameraConnectionService
        
        # Load config
        config = load_camera_config()
        camera_id = config.get('ip', 'auto')
        
        # Force MVS camera type
        config['camera_type'] = 'mvs'
        
        logger.info(f"Camera config loaded:")
        logger.info(f"  - camera_type: {config.get('camera_type')}")
        logger.info(f"  - camera_id: {camera_id}")
        logger.info(f"  - exposure_time: {config.get('exposure_time')} μs")
        logger.info(f"  - gain: {config.get('gain')}")
        logger.info(f"  - trigger_mode: {config.get('trigger_mode')}")
        
        # Create camera service
        logger.info("\n[Step 1] Creating camera service...")
        camera_service = CameraConnectionService()
        
        # Create camera instance
        logger.info("\n[Step 2] Creating MVS camera instance...")
        if not camera_service.create_camera(camera_id, config):
            logger.error("Failed to create camera instance")
            return False
        
        # Connect to camera
        logger.info("\n[Step 3] Connecting to camera...")
        if not camera_service.connect():
            logger.error("Failed to connect to camera")
            return False
        
        logger.info("\n✓✓✓ Camera connected successfully!")
        
        # Get camera info
        logger.info("\n[Step 4] Getting camera info...")
        info = camera_service.get_camera_info()
        logger.info(f"Camera info:")
        for key, value in info.items():
            logger.info(f"  - {key}: {value}")
        
        # Start grabbing
        logger.info("\n[Step 5] Starting grabbing...")
        if not camera_service.start_streaming():
            logger.error("Failed to start grabbing")
            camera_service.cleanup()
            return False
        
        logger.info("✓ Grabbing started")
        
        # Capture a few frames
        logger.info("\n[Step 6] Capturing test frames...")
        for i in range(5):
            frame = camera_service.get_frame(timeout_ms=2000)
            if frame is not None:
                logger.info(f"  Frame {i+1}: shape={frame.shape}, dtype={frame.dtype}")
            else:
                logger.warning(f"  Frame {i+1}: Failed to capture")
        
        # Stop grabbing
        logger.info("\n[Step 7] Stopping grabbing...")
        camera_service.stop_streaming()
        
        # Disconnect
        logger.info("\n[Step 8] Disconnecting...")
        camera_service.disconnect()
        
        # Cleanup
        logger.info("\n[Step 9] Cleanup...")
        camera_service.cleanup()
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("Starting MVS camera test...")
    
    success = test_mvs_camera()
    
    if success:
        logger.info("\n✓✓✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n✗✗✗ Test failed!")
        sys.exit(1)
