# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os


class SettingsError(Exception):
    """Base error for telegram bot class.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message

class Settings():
    def __init__(self):
        self.TLEGRAM_TOKEN = os.getenv("TLEGRAM_TOKEN")
        if check_not_set(self.TLEGRAM_TOKEN):
            raise SettingsError("Settings: TLEGRAM_TOKEN env variable has not been set")

        self.STATIC_IP = os.getenv("STATIC_IP")
        self.STATIC_IP = self.STATIC_IP.lower() == 'true' if self.STATIC_IP is not None else False

        self.PRINTER_IP = os.getenv("PRINTER_IP")
        self.PRINTER_MAC = os.getenv("PRINTER_MAC")
        self.PRINTER_SUBNET = os.getenv("PRINTER_SUBNET")

        if self.STATIC_IP:
            if check_not_set(self.PRINTER_IP):
                raise SettingsError("Settings: STATIC_IP is set to True, but PRINTER_IP env variable has not been set")
        else:
            if check_not_set(self.PRINTER_MAC):
                raise SettingsError("Ultimaker: STATIC_IP is set to False, but PRINTER_MAC env variable has not been set")
            if check_not_set(self.PRINTER_SUBNET):
                raise SettingsError("Ultimaker: STATIC_IP is set to False, but PRINTER_SUBNET env variable has not been set")

        self.ULTIMAKER_ID = os.getenv("ULTIMAKER_ID")
        if check_not_set(self.ULTIMAKER_ID):
            raise SettingsError("Settings: ULTIMAKER_ID env variable has not been set")

        self.ULTIMAKER_KEY = os.getenv("ULTIMAKER_KEY")
        if check_not_set(self.ULTIMAKER_KEY):
            raise SettingsError("Settings: ULTIMAKER_KEY env variable has not been set")

        self.STATUS_UPDATE_INTERVAL = os.getenv("STATUS_UPDATE_INTERVAL")
        if check_not_set(self.STATUS_UPDATE_INTERVAL):
            raise SettingsError("Settings: STATUS_UPDATE_INTERVAL env variable has not been set")

        try:
            self.STATUS_UPDATE_INTERVAL = int(self.STATUS_UPDATE_INTERVAL)
        except ValueError:
            raise SettingsError("Settings: STATUS_UPDATE_INTERVAL env variable has to be integer")


def check_not_set(var):
    return (var is None or var == '')

def load_settings(config_path, env_file):
    print (os.path.join(config_path, env_file + '.env'))
    print (__file__)
    load_dotenv(verbose=True, dotenv_path=os.path.join(config_path, env_file + '.env'))
    return Settings()
