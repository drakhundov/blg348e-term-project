import logging
import os

DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DEFAULT_DATEFMT = "%H:%M:%S"

logger_initialized = False


class Logger:
    def __init__(self):
        self.__logger = None

    def init_logger(self, logfile: str, format: str, datefmt: str):
        logging.basicConfig(
            filename=f"log/{logfile}.log",
            filemode="w",
            format=format,
            datefmt=datefmt,
            level=logging.DEBUG,
        )
        self.__logger = logging.getLogger()

    def get_logger(self):
        if self.__logger is not None:
            return self.__logger
        else:
            raise Exception("Logger hasn't been initialized.")

    def info(self, msg: str):
        self.__logger.info(str)

    def debug(self, msg: str):
        self.__logger.debug(msg)

    def error(self, msg: str):
        self.__logger.error(msg)


# ! Supposed to be initialized.
__loggerObj = Logger()


def init_log(logfile):
    global __loggerObj, logger_initialized
    if logger_initialized:
        raise Exception("Logger has already been initialized.")
    if not os.path.exists("log"):
        os.makedirs("log")
    __loggerObj.init_logger(
        logfile=logfile, format=DEFAULT_FORMAT, datefmt=DEFAULT_DATEFMT
    )
    logger_initialized = True


def get_logger():
    global __loggerObj
    return __loggerObj
