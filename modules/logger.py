import logging

def setup_logging(LOG_PATH,LOG_LEVEL):
    """Creates a shared logging object for the application"""

    # create logging object
    logger = logging.getLogger('attack_range')
    logger.setLevel(LOG_LEVEL)
    # create a file and console handler
    fh = logging.FileHandler(LOG_PATH)
    fh.setLevel(LOG_LEVEL)
    ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVEL)
    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

def get():
    logger = logging.getLogger('attack_range')
    return logger
