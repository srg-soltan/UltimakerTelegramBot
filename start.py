import sys
from src.printer_bot import PrinterBot, BotError
from src.ultimaker import UltimakerError
from src.settings import load_settings, SettingsError

if __name__ == '__main__':
    print (sys.argv)
    
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
    else:
        env_file = 'start'
    
    config = load_settings('./config', env_file)

    print (config.__dict__)

    try:
        #PrinterBot(config_path='config/config.json', users_path='config/authorized_users.json', ultimker_auth_file='config/ultimker_auth_file.json')
        PrinterBot(config=config, users_path='config/authorized_users.json')
    except UltimakerError as uer:
        print (uer.message)
    except BotError as ber:
        print (ber.message)
    except SettingsError as ser:
        print (ser.message)
