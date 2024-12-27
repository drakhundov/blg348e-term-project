import logging
import os

# ! Supposed to be initialized.
__logger = None


def init_log(timestamp):
    global logger
    if not os.path.exists("log"):
        os.makedirs("log")
    logging.basicConfig(
        filename=f"log/{timestamp}.log",
        filemode="w",
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )
    logger = logging.getLogger(__name__)


def get_logger():
    global __logger
    return __logger
