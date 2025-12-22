"""
Main Entry Point - Khởi tạo ứng dụng CCDLaser
"""
import sys
import signal
from PySide6.QtWidgets import QApplication

# Import services
from services.LogService import getLogger
from services.ConfigService import get_config_service
# Import MVP components
from app.view import MainView
from app.presenter import MainPresenter


def main():
    """Main entry point"""
    
    # 1. Setup logging
    logger = getLogger()
    logger.info("=" * 80)
    logger.info("CCDLaser - Camera Control System Started")
    logger.info("=" * 80)
    
    try:
        # 2. Load configuration
        config_service = get_config_service()
        if not config_service.load_all_configs():
            logger.warning("Failed to load some config files, using defaults")
        else:
            logger.info("Configuration loaded successfully")
        
        # Get all config
        config = config_service.get_all()
        
        # 3. Create Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("CCDLaser")
        app.setOrganizationName("CCDLaser")
        
        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        # 4. Create View
        view = MainView()
        
        # 5. Create Presenter (MVP pattern)
        presenter = MainPresenter(view, config)
        
        # 6. Connect View and Presenter
        view.set_presenter(presenter)
        
        # 7. Show window
        view.show()
        
        logger.info("Application UI initialized")
        
        # 8. Run event loop
        exit_code = app.exec()
        
        logger.info("Application exited normally")
        return exit_code
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
