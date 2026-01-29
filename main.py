import sys
import signal
from PySide6.QtWidgets import QApplication

from services.logService import getLogger
from services.settingService import getSettingService
from app.view import MainView
from app.presenter import MainPresenter


def main():

    logger = getLogger()
    try:
        logger.info("CCDLaser - Camera Control System Started")
        try:
            settingService = getSettingService()
            settings = settingService.getSetting()
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}", exc_info=True)
            raise
        app = QApplication(sys.argv)
        app.setApplicationName("CCDLaser")
        app.setOrganizationName("CCDLaser")
        
        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        logger.info("Signal handlers registered")
        
        # 4. Create View
        logger.info("Creating MainView...")
        try:
            view = MainView()
            logger.info("MainView created successfully")
        except Exception as e:
            logger.error(f"Failed to create MainView: {e}", exc_info=True)
            raise
        
        # 5. Create Presenter (MVP pattern)
        logger.info("Creating MainPresenter...")
        try:
            presenter = MainPresenter(view, settings)
            logger.info("MainPresenter created successfully")
        except Exception as e:
            logger.error(f"Failed to create MainPresenter: {e}", exc_info=True)
            raise
        
        # 6. Connect View and Presenter
        logger.info("Connecting View and Presenter...")
        view.set_presenter(presenter)
        
        # 7. Show window
        logger.info("Showing main window...")
        view.show()
        logger.info("Application ready - Main window displayed")

        # 8. Run event loop
        exit_code = app.exec()
        
        logger.info("Application exited normally")
        return exit_code
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
