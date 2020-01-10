# -*- coding: utf-8 -*-

import datetime
import dateutil.parser
from tzlocal import get_localzone

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ChatAction, ParseMode, ReplyKeyboardMarkup

from .auth import authorized
from .utils import progress_bar,  send_typing_action, build_keyboard
from .settings_menu import SettingsMenu
from .text_formating import format_printjob_status, format_printer_status


class MainMenu:
    MENU_GET_IMAGE = "Get Image 🖼"
    MENU_TEST = "Bot Status 🤖"
    MENU_GET_PRINTER_STATUS = "Printer Status 🖨"
    MENU_GET_PRINTJOB = "Print Job 🔲" 
    MENU_GET_ID = "Get My Id"
    MENU_PRINTER_SETTINGS = "Printer Settings ⚙"

    def __init__(self, printer_bot):
        self.printer_bot = printer_bot
        self.prepare_keyboard_menus()
        self.settings_menu = SettingsMenu(printer_bot, self)

    def prepare_keyboard_menus(self):
        self.MENU_LAYOUT_UNAUTHORIZED = [self.MENU_GET_ID]

        self.MENU_LAYOUT_MONITOR = [
            [ self.MENU_GET_PRINTJOB, self.MENU_GET_PRINTER_STATUS ], 
            [ self.MENU_GET_IMAGE ], 
            [ self.MENU_TEST ]
        ]

        self.MENU_LAYOUT_CONTROL = [
            [ self.MENU_GET_PRINTJOB, self.MENU_GET_PRINTER_STATUS ], 
            [ self.MENU_GET_IMAGE ], 
            [ self.MENU_PRINTER_SETTINGS ],
            [ self.MENU_TEST ]
        ]

    def add_handlers(self, dp):
        dp.add_handler(CommandHandler('start', self.start_cmd))
        dp.add_handler(CommandHandler('image', self.get_image_cmd))
        dp.add_handler(CommandHandler('test', self.test_cmd))
        dp.add_handler(CommandHandler('printjob', self.get_printjob_cmd))
        dp.add_handler(CommandHandler('printer', self.get_printjob_cmd))
        dp.add_handler(CommandHandler('myid', self.get_id_cmd))


        dp.add_handler(MessageHandler(Filters.regex('^{}$'.format(self.MENU_TEST)), self.test_cmd))
        dp.add_handler(MessageHandler(Filters.regex('^{}$'.format(self.MENU_GET_IMAGE)), self.get_image_cmd))
        dp.add_handler(MessageHandler(Filters.regex('^{}$'.format(self.MENU_GET_PRINTJOB)), self.get_printjob_cmd))
        dp.add_handler(MessageHandler(Filters.regex('^{}$'.format(self.MENU_GET_PRINTER_STATUS)), self.get_printer_cmd))
        dp.add_handler(MessageHandler(Filters.regex('^{}$'.format(self.MENU_GET_ID)), self.get_id_cmd))

        self.settings_menu.add_handlers(dp)

    @authorized('monitor')
    def get_image_cmd(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
            
        context.bot.send_message(chat_id=chat_id, text="Retriving image...")

        context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        img = self.printer_bot.ultimaker.get_camera_snapshot()
        
        if img is not None:
            img_name = 'printer_{}.jpeg'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))

            context.bot.send_message(chat_id=chat_id, text="Sending image: {}".format(img_name))

            context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
            context.bot.send_photo(chat_id=chat_id, photo=img)
        else:
            context.bot.send_message(chat_id=chat_id, text="Could not get image :(")

    @authorized('monitor')
    @send_typing_action
    def get_printjob_cmd(self, update: Update, context: CallbackContext):
        try:
            chat_id = update.effective_chat.id

            res = self.printer_bot.ultimaker.get_printjob_status()

            if res['status_code'] == 200:
                status = format_printjob_status(res['status'])

                time_remaining_secs = res['time_total'] - res['time_elapsed']
                if time_remaining_secs < 0:
                    time_remaining_secs = 0

                time_remaining = datetime.timedelta(seconds=time_remaining_secs)

                if 'datetime_finished' in res and res['datetime_finished'] != '':
                    end_time_utc = dateutil.parser.parse(res['datetime_finished']).replace(tzinfo=datetime.timezone.utc)
                    end_time = end_time_utc.astimezone(get_localzone())
                else:
                    end_time = datetime.datetime.now() + time_remaining

                start_time_utc = dateutil.parser.parse(res['datetime_started']).replace(tzinfo=datetime.timezone.utc)
                start_time = start_time_utc.astimezone(get_localzone())

                msg = "<b>Status:</b> {0}\n".format(status)
                if res['status'] == 'paused':
                    msg += "<b>Pause Source:</b> {0}\n".format(res['pause_source'])
                msg += "<b>Model name:</b> {0}\n".format(res['print_name'])
                msg += "<b>Total time:</b> {0}\n".format(str(datetime.timedelta(seconds=res['time_total'])))
                msg += "<b>Time remaning:</b> {0}\n".format(str(time_remaining))
                msg += "<b>Progress:</b> {0:.2f}% {1}\n".format(res['progress'] * 100, progress_bar(res['progress']))
                msg += "<b>Start Time:</b> {0}\n".format(start_time.strftime("%Y-%m-%d %H:%M:%S"))
                msg += "<b>End Time:</b> {0}".format(end_time.strftime("%Y-%m-%d %H:%M:%S"))

                context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML)
            else:
                msg = "<b>Status:</b> No printer job running"
                context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML)
        except Exception as ex:
            print(ex)

    @authorized('monitor')
    @send_typing_action
    def get_printer_cmd(self, update: Update, context: CallbackContext):
        try:
            chat_id = update.effective_chat.id
            
            res = self.printer_bot.ultimaker.get_printer_status()

            if res['status_code'] == 200:
                status = format_printjob_status(res['status'])

                msg = "<b>Printer Status:</b> {0}\n".format(status)
                msg += "<b>  Bed Temperature 🌡:</b>\n"
                msg += "<b>    Current:</b> {0:.2f} C\n".format(res['bed_temp_cur'])
                msg += "<b>    Target:</b> {0} C\n".format(res['bed_temp_target'])
                msg += "<b>  Extruder [1]:</b>\n"
                msg += "<b>    Temperature 🌡:</b>\n"
                msg += "<b>      Current:</b> {0:.2f} C\n".format(res['ext_1_temp_cur'])
                msg += "<b>      Target:</b> {0} C\n".format(res['ext_1_temp_target'])
                msg += "<b>    Feeder:</b>\n"
                msg += "<b>      Max Speed:</b> {0} mm/s\n".format(res['ext_1_feeder_max_speed'])

                context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML)
            else:
                context.bot.send_message(chat_id=chat_id, text="Could not get status :(")
        except Exception as ex:
            print(ex)

    @authorized('monitor')
    def test_cmd(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        context.bot.send_message(chat_id=chat_id, text="Bot is alive 👍")

    def get_id_cmd(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id
        context.bot.send_message(chat_id=chat_id, text="Your user id is {}".format(user_id))

    def start_menu_unauth(self):
        button_list = build_keyboard(self.MENU_LAYOUT_UNAUTHORIZED)
        reply_markup = ReplyKeyboardMarkup(button_list, resize_keyboard=True)
        
        msg = "Commands:\n"
        msg += "/start - To get started\n"
        msg += "/myid - To get your user id"

        return msg, reply_markup

    def start_menu_monitor(self):
        button_list = build_keyboard(self.MENU_LAYOUT_MONITOR)
        reply_markup = ReplyKeyboardMarkup(button_list, resize_keyboard=True)

        msg = "Commands:\n"
        msg += "/start - To get started\n"
        msg += "/test - To test if the bot is alive\n"
        msg += "/image - To get image from printer\n"
        msg += "/printjob - To get current print job\n"
        msg += "/printer - To get printer status\n"
        msg += "/myid - To get your user id"

        return msg, reply_markup

    def start_menu_control(self):
        button_list = build_keyboard(self.MENU_LAYOUT_CONTROL)
        reply_markup = ReplyKeyboardMarkup(button_list, resize_keyboard=True)

        msg = "Commands:\n"
        msg += "/start - To get started\n"
        msg += "/test - To test if the bot is alive\n"
        msg += "/image - To get image from printer\n"
        msg += "/printjob - To get current print job\n"
        msg += "/printer - To get printer status\n"
        msg += "/myid - To get your user id"

        return msg, reply_markup

    def start_cmd(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id

        if self.printer_bot.is_authorized(user_id, 'control'):
            msg, reply_markup = self.start_menu_control()
        elif self.printer_bot.is_authorized(user_id, 'monitor'):
            msg, reply_markup = self.start_menu_monitor()
        else:
            msg, reply_markup = self.start_menu_unauth()

        context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=reply_markup)

