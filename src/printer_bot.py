# -*- coding: utf-8 -*-

import sys
import os
import datetime
import json
import re
from telegram.ext import Updater, CallbackContext, MessageHandler, Filters
from telegram import Update, ParseMode

from .settings import load_settings
from .auth import auth_load_users, auth_get_notify_group, authorized
from .ultimaker import Ultimaker, UltimakerError
from .main_menu import MainMenu
from .text_formating import format_printjob_status, format_printer_status


class BotError(Exception):
    """Base error for telegram bot class.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class PrinterBot:
    printer_status = None
    printjob_state = None

    def __init__(self, config, app_name='TelegramBot', users_path='authorized_users.json'):
        print ('Loading Configs...')
        self.config = config
        
        self.bot_token = self.config.TLEGRAM_TOKEN
        self.status_update_interval = self.config.STATUS_UPDATE_INTERVAL

        self.load_users(users_path)

        print ('Loading Ultimaker...')
        self.ultimaker = Ultimaker(app_name, self.config)
        print ('Ultimaker loaded.')

        self.main_menu = MainMenu(self)

        print ('Starting bot...')
        updater = Updater(self.bot_token, use_context=True)
        dp = updater.dispatcher
        jq = updater.job_queue
        
        self.main_menu.add_handlers(dp)
        self.add_handlers(dp)

        self.add_job_queue(jq)

        updater.start_polling()
        print ('Bot has been successfully started.')
        updater.idle()

    def load_users(self, users_path):
        try:
            f = open(users_path, "rt")
            users_config = json.load(f)    
            f.close()

            auth_load_users(users_config)
        except IOError:
            print ("Telegran Bot: Could not load users config file: {}".format(users_path))
            raise BotError("Telegran Bot: Could not load users config file: {}".format(users_path))
        
        self.access_levels = users_config['access_levels']
        self.users = users_config['users']

        self.authorized_uses = {}
        for level in self.access_levels:
            self.authorized_uses[level] = set()

        self.notify_group = set()
        
        for user in self.users:
            # higher access levels get acces to lower
            for level in range(0, user['access_level'] + 1):
                self.authorized_uses[self.access_levels[level]].add(user['id'])
            
            if user['notify']:
                self.notify_group.add(user['id'])

    def add_handlers(self, dp):
        dp.add_handler(MessageHandler(Filters.regex(re.compile('^{}$'.format('well done'), re.IGNORECASE)), self.send_ok))
        dp.add_error_handler(self.error)

    def add_job_queue(self, job_queue):
        job_queue.run_repeating(self.status_notification_callback, interval=self.status_update_interval, first=0)

    def is_authorized(self, user_id, level):
        return user_id in self.authorized_uses[level]

    def error(self, update, context):
        """Log Errors caused by Updates."""
        print('[{}] Update caused error: {}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), context.error))

    def simulate_printer(self):
        res = json.load(open('sim.json', "rt"))  
        return res

    def send_ok(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        context.bot.send_message(chat_id=chat_id, text="OK! 😀")

    def status_notification_callback(self, context: CallbackContext):
        response = self.ultimaker.get_printer_state()
        changed = False

        if self.printer_status == None:
            self.printer_status = response['printer_status']
        else:
            if self.printer_status != response['printer_status']:
                # printer_status changed
                self.printer_status = response['printer_status']
                changed = True
        if self.printjob_state == None:
            self.printjob_state = response['printjob_state']
        else:
            if self.printjob_state != response['printjob_state']:
                # printer_status changed
                self.printjob_state = response['printjob_state']
                changed = True

        if changed:
            # notify users
            for user_id in auth_get_notify_group():
                msg = "Status Changed❗\n"
                msg += "   <b>Printer Status:</b> {}\n".format(format_printer_status(self.printer_status))
                msg += "   <b>Print Job Status:</b> {}".format(format_printjob_status(self.printjob_state))
                if response['printjob_state'] == 'paused':
                    msg += "<b>   Pause Source:</b> {0}\n".format(response['pause_source'])
                context.bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.HTML)
