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
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            view = MainView()
        except Exception as e:
            logger.error(f"Failed to create MainView: {e}", exc_info=True)
            raise
        try:
            presenter = MainPresenter(view, settings)
        except Exception as e:
            logger.error(f"Failed to create MainPresenter: {e}", exc_info=True)
            raise
        view.set_presenter(presenter)
        view.show()
        exit_code = app.exec()
        
        logger.info("Application closed")
        return exit_code
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
