"""
Main Entry Point - Khởi tạo ứng dụng CCDLaser
"""
import sys
import signal
from PySide6.QtWidgets import QApplication

# Import services
from services.logService import getLogger
from services.settingService import getSettingService
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
        settingService = getSettingService()
        settings = settingService.getSetting()
        
        # 3. Create Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("CCDLaser")
        app.setOrganizationName("CCDLaser")
        
        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        # 4. Create View
        view = MainView()
        
        # 5. Create Presenter (MVP pattern)
        presenter = MainPresenter(view, settings)
        
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
