from dogepartylib.lib import config
import json
import requests
import threading
import sys
import time
import logging
logger = logging.getLogger(__name__)


VERSIONS = None


def fetch_versions():
    pass


def get_versions():
    return VERSIONS


def get_version_file():
    global VERSIONS
    try:
        host = config.VERSION_FILE
        response = requests.get(host,
                                headers={'cache-control': 'no-cache'})
        VERSIONS = json.loads(response.text)
    except:
        VERSIONS = None
        logger.warning('Unable to check version! '
                        + str(sys.exc_info()[1]))


def start():
    get_version_file()
    server = BackendServer()
    server.daemon = True
    server.start()


class BackendServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            get_version_file()
            time.sleep(60)

    def stop(self):
        self.stop_event.set()
