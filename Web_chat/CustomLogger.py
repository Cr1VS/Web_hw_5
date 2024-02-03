import logging


class CustomLogger:
    """
    Custom logger class for handling both console and file logging.

    :param log_file: Path to the log file.
    :param console_level: Logging level for console output (default INFO).
    :param file_level: Logging level for file output (default ERROR).
    """

    def __init__(
        self,
        log_file: str,
        console_level: int = logging.INFO,
        file_level: int = logging.ERROR,
    ):
        self.logger = logging.getLogger("custom_logger")
        self.logger.setLevel(logging.INFO)

        # Log for console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Log for file
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(file_level)
        file_formatter = logging.Formatter(
            "%(levelname)s, %(asctime)s %(module)s %(funcName)s %(lineno)d - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def log(self, message: str, level: int = logging.INFO):
        """
        Method for recording messages in the log.

        :param message: Message for writing to the log.
        :param level: Logging level (default Info).
        """
        self.logger.log(level, message)
