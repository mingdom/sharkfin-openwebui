import logging
import os

APP_NAME = 'sharkfin'

DEFAULT_LOG_LEVEL = os.environ.get('SHARKFIN_LOG_LEVEL') or logging.INFO


class Log:
    def __init__(self, app_name=APP_NAME, console_level=DEFAULT_LOG_LEVEL, file_level=logging.DEBUG):
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)

        # Console Handler
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(console_level)

        # File Handler
        log_dir = "logs"  # Create a 'logs' directory if needed
        os.makedirs(log_dir, exist_ok=True)
        self.file_handler = logging.FileHandler(
            os.path.join(log_dir, f"{app_name}.log"))
        self.file_handler.setLevel(file_level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(module)s - %(message)s')
        self.console_handler.setFormatter(formatter)
        self.file_handler.setFormatter(formatter)

        self.logger.addHandler(self.console_handler)
        self.logger.addHandler(self.file_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger
