# -*- coding: utf-8 -*-

#from telegram.ext import Updater, CommandHandler, RegexHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext, ConversationHandler
#from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ParseMode, ChatAction, InlineKeyboardButton, InlineKeyboardMarkup

from io import BytesIO, BufferedWriter, BufferedReader
import traceback

from telegram.ext import ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram import Update, InlineKeyboardMarkup, ParseMode, ChatAction

from .auth import authorized
from .utils import build_inline_keyboard
from .text_formating import format_printjob_status


class SettingsMenu:
    MENU_SETTINGS_HEADER = "Printer Settings"
    MENU_BACK_SETTINGS = "Back To Settings 🔙"
    MENU_YES = "Yes"
    MENU_NO = "No"

    MENU_SETTINGS_LEDS = "LEDs 💡"
    MENU_SETTINGS_LEDS_HEADER = "LEDs Settings 💡"

    MENU_SET_LED_HIGH = "LEDs High"
    MENU_SET_LED_MEDIUM = "LEDs Medium"
    MENU_SET_LED_LOW = "LEDs Low"
    MENU_GET_LED_LEVEL = "Check LEDs Brightness"

    MENU_SETTINGS_PRINTJOB = "Print Job 🔲"
    MENU_SETTINGS_PRINTJOB_HEADER = "Print Job Settings 🔲"
    MENU_GET_PRINTJOB_STATE = "Check Print Job State"
    MENU_GET_PRINTJOB_THUMBNAIL = "Get Print Job Thumbnail"
    MENU_PAUSE_PRINTJOB_STATE = "Pause Printing ⏸"
    MENU_UNPAUSE_PRINTJOB_STATE = "Resume Printing ▶"
    MENU_PRINT_MODEL = "Print Model"


    SETTINGS, LEDS, PRINTJOB = ('SETTINGS_STATE', 'LEDS_STATE', 'PRINTJOB_STATE')
    PRINTJOB_PAUSING, PRINTJOB_UNPAUSING, PRINT_MODEL = ('PRINTJOB_PAUSING_STATE', 'PRINTJOB_UNPAUSING_STATE', 'PRINT_MODEL_STATE')

    def __init__(self, printer_bot, main_menu):
        self.printer_bot = printer_bot
        self.main_menu = main_menu
        self.prepare_keyboard_menus()

    def prepare_keyboard_menus(self):
        self.MENU_INLINELAYOUT_SETTINGS = [
            [ self.MENU_SETTINGS_LEDS ],
            [ self.MENU_SETTINGS_PRINTJOB ]
        ]

        self.MENU_INLINELAYOUT_SETTINGS_LED = [
            [ self.MENU_GET_LED_LEVEL ],
            [ self.MENU_SET_LED_HIGH, self.MENU_SET_LED_MEDIUM, self.MENU_SET_LED_LOW ],
            [ self.MENU_BACK_SETTINGS]
        ]

        self.MENU_INLINELAYOUT_SETTINGS_PRINTJOB = [
            [ self.MENU_GET_PRINTJOB_STATE ],
            [ self.MENU_GET_PRINTJOB_THUMBNAIL ],
            [ self.MENU_PRINT_MODEL ],
            [ self.MENU_UNPAUSE_PRINTJOB_STATE, self.MENU_PAUSE_PRINTJOB_STATE ],
            [ self.MENU_BACK_SETTINGS ]
        ]

        self.MENU_INLINELAYOUT_YES_NO = [
            [ self.MENU_YES, self.MENU_NO ]
        ]

        self.MENU_INLINELAYOUT_YES_NO_BACK = [
            [ self.MENU_YES, self.MENU_NO ],
            [ self.MENU_BACK_SETTINGS ]
        ]

    def add_handlers(self, dp):
        dp.add_handler(self.settings_handler())

    def settings_handler(self):
        settings_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(Filters.regex('^{}$'.format(self.main_menu.MENU_PRINTER_SETTINGS)), self.printer_settings_cmd)],

            states={
                self.SETTINGS: [CallbackQueryHandler(self.printer_settings_leds_cb, pattern='^{}$'.format(self.MENU_SETTINGS_LEDS)),
                                CallbackQueryHandler(self.printer_settings_printjob_cb, pattern='^{}$'.format(self.MENU_SETTINGS_PRINTJOB))],

                self.LEDS: [CallbackQueryHandler(self.printer_leds_high_cb, pattern='^{}$'.format(self.MENU_SET_LED_HIGH)),
                                CallbackQueryHandler(self.printer_leds_medium_cb, pattern='^{}$'.format(self.MENU_SET_LED_MEDIUM)),
                                CallbackQueryHandler(self.printer_leds_low_cb, pattern='^{}$'.format(self.MENU_SET_LED_LOW)),
                                CallbackQueryHandler(self.printer_leds_level_cb, pattern='^{}$'.format(self.MENU_GET_LED_LEVEL))],

                self.PRINTJOB : [CallbackQueryHandler(self.printjob_state_cb, pattern='^{}$'.format(self.MENU_GET_PRINTJOB_STATE)),
                                CallbackQueryHandler(self.printjob_thumbnail_cb, pattern='^{}$'.format(self.MENU_GET_PRINTJOB_THUMBNAIL)),
                                CallbackQueryHandler(self.printjob_print_model_cb, pattern='^{}$'.format(self.MENU_PRINT_MODEL)),
                                CallbackQueryHandler(self.printjob_pause_cb, pattern='^{}$'.format(self.MENU_PAUSE_PRINTJOB_STATE)),
                                CallbackQueryHandler(self.printjob_unpause_cb, pattern='^{}$'.format(self.MENU_UNPAUSE_PRINTJOB_STATE))],

                self.PRINTJOB_PAUSING: [CallbackQueryHandler(self.printjob_pause_no_cb, pattern='^{}$'.format(self.MENU_NO)),
                                        CallbackQueryHandler(self.printjob_pause_yes_cb, pattern='^{}$'.format(self.MENU_YES))],

                self.PRINTJOB_UNPAUSING: [CallbackQueryHandler(self.printjob_unpause_no_cb, pattern='^{}$'.format(self.MENU_NO)),
                                        CallbackQueryHandler(self.printjob_unpause_yes_cb, pattern='^{}$'.format(self.MENU_YES))],

                self.PRINT_MODEL: [MessageHandler(Filters.document, self.download_model_file_cb)]
            },

            fallbacks=[MessageHandler(Filters.regex('^{}$'.format(self.main_menu.MENU_PRINTER_SETTINGS)), self.printer_settings_cmd),
                        MessageHandler(Filters.text, self.done), 
                        CallbackQueryHandler(self.printer_back_settings_cb, pattern='^{}$'.format(self.MENU_BACK_SETTINGS))],
            #per_user=True
        )

        return settings_conv_handler

    @authorized('control')
    def printer_settings_cmd(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS)
        reply_markup = InlineKeyboardMarkup(button_list)

        context.bot.send_message(chat_id=chat_id, text=self.MENU_SETTINGS_HEADER, reply_markup=reply_markup)

        return self.SETTINGS

    @authorized('control')
    def printer_back_settings_cb(self, update: Update, context: CallbackContext):
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS)
        reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, self.MENU_SETTINGS_HEADER, reply_markup)

        return self.SETTINGS

    @authorized('control')
    def printer_settings_leds_cb(self, update: Update, context: CallbackContext):
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS_LED)
        reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, self.MENU_SETTINGS_LEDS_HEADER, reply_markup)

        return self.LEDS

    @authorized('control')
    def printer_settings_printjob_cb(self, update: Update, context: CallbackContext):
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS_PRINTJOB)
        reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, self.MENU_SETTINGS_PRINTJOB_HEADER, reply_markup)

        return self.PRINTJOB

    @authorized('control')
    def printer_leds_high_cb(self, update: Update, context: CallbackContext):
        res = self.printer_bot.ultimaker.set_led_brightness(100)
        if res['status_code'] == 200:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  Setting LEDs to High'
            self.edit_message_text(update, context, text=text)
        else:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  Could not set LEDs...'
            self.edit_message_text(update, context, text=text)

        #return ConversationHandler.END

    @authorized('control')
    def printer_leds_low_cb(self, update: Update, context: CallbackContext):
        res = self.printer_bot.ultimaker.set_led_brightness(0)

        if res['status_code'] == 200:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  Setting LEDs to Low'
            self.edit_message_text(update, context, text=text)
        else:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  Could not set LEDs...'
            self.edit_message_text(update, context, text=text)

        #return ConversationHandler.END

    @authorized('control')
    def printer_leds_medium_cb(self, update: Update, context: CallbackContext):
        res = self.printer_bot.ultimaker.set_led_brightness(50)

        if res['status_code'] == 200:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  Setting LEDs to Medium'
            self.edit_message_text(update, context, text=text)
        else:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  Could not set LEDs...'
            self.edit_message_text(update, context, text=text)

        #return ConversationHandler.END

    @authorized('control')
    def printer_leds_level_cb(self, update: Update, context: CallbackContext):
        res = self.printer_bot.ultimaker.get_led_brightness()

        if res['status_code'] == 200:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  LEDs are set to {}'.format(res['level'])
            self.edit_message_text(update, context, text=text)
        else:
            text = self.MENU_SETTINGS_LEDS_HEADER + '\n  Could not set LEDs...'
            self.edit_message_text(update, context, text=text)

    @authorized('control')
    def printjob_state_cb(self, update: Update, context: CallbackContext):
        res = self.printer_bot.ultimaker.get_printjob_state()

        text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  <b>State</b>: ' + format_printjob_status(res['printjob_state'])
        self.edit_message_text(update, context, text=text, parse_mode=ParseMode.HTML)

    @authorized('control')
    def printjob_thumbnail_cb(self, update: Update, context: CallbackContext):
        chat_id = update.callback_query.message.chat.id

        res = self.printer_bot.ultimaker.get_printjob_thumbnail()

        if res['status_code'] == 200:
            if res['has_thumbnail']:
                context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
                context.bot.send_photo(chat_id=chat_id, photo=res['thumbnail'])
            else:
                msg = 'Could not get print job thumbnail'
                context.bot.send_message(chat_id=chat_id, text=msg)
        else:
            msg = 'No printer job running or no file found!'
            context.bot.send_message(chat_id=chat_id, text=msg)
        pass

    @authorized('control')
    def printjob_pause_cb(self, update: Update, context: CallbackContext):
        res = self.printer_bot.ultimaker.get_printjob_state()
        if res['printjob_state'] == 'paused':
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Print Job has already been stoped!'
        elif res['printjob_state'] == 'no_printjob':
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  No Print Job'
        elif res['printjob_state'] == 'printing':
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Are you sure you want to pause Print Job?'

            button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_YES_NO_BACK)
            reply_markup = InlineKeyboardMarkup(button_list)

            self.edit_message_text(update, context, text=text, reply_markup=reply_markup)
            return self.PRINTJOB_PAUSING
        else:
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + \
                    '\n  Print Job mstate must be printing to be puased\n' + \
                    '  <b>State</b>: ' + format_printjob_status(res['printjob_state'])
        
        self.edit_message_text(update, context, text=text, parse_mode=ParseMode.HTML)

    @authorized('control')
    def printjob_pause_no_cb(self, update: Update, context: CallbackContext):
        text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Canceled Print Job pause command 🚫'
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS_PRINTJOB)
        reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, text=text, reply_markup=reply_markup)
        return self.PRINTJOB

    @authorized('control')
    def printjob_pause_yes_cb(self, update: Update, context: CallbackContext):
        #text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  THIS COMMAND IS NOT SUPPORTED YET 🛑'
        text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Pausing print'
        self.printer_bot.ultimaker.pause_printjob()
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS_PRINTJOB)
        reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, text=text, reply_markup=reply_markup)
        return self.PRINTJOB

    @authorized('control')
    def printjob_unpause_cb(self, update: Update, context: CallbackContext):
        res = self.printer_bot.ultimaker.get_printjob_state()
        if res['printjob_state'] == 'printing':
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Print Job is already printing!'
        elif res['printjob_state'] == 'no_printjob':
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  No Print Job'
        elif res['printjob_state'] == 'paused':
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Are you sure you want to continue Print Job?'

            button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_YES_NO_BACK)
            reply_markup = InlineKeyboardMarkup(button_list)

            self.edit_message_text(update, context, text=text, reply_markup=reply_markup)
            return self.PRINTJOB_UNPAUSING
        else:
            text = self.MENU_SETTINGS_PRINTJOB_HEADER + \
                    '\n  Print Job mstate must be puased to continue printing\n' + \
                    '  <b>State</b>: ' + format_printjob_status(res['printjob_state'])
        
        self.edit_message_text(update, context, text=text, parse_mode=ParseMode.HTML)

    @authorized('control')
    def printjob_unpause_no_cb(self, update: Update, context: CallbackContext):
        text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Canceled Print Job resume printing command 🚫'
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS_PRINTJOB)
        reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, text=text, reply_markup=reply_markup)
        return self.PRINTJOB

    @authorized('control')
    def printjob_unpause_yes_cb(self, update: Update, context: CallbackContext):
        #text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  THIS COMMAND IS NOT SUPPORTED YET 🛑'
        text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Resuming print'
        self.printer_bot.ultimaker.unpause_printjob()
        button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS_PRINTJOB)
        reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, text=text, reply_markup=reply_markup)
        return self.PRINTJOB

    @authorized('control')
    def printjob_print_model_cb(self, update: Update, context: CallbackContext):
        print ('print model')
        text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  Pleas send model file to be printed'
        #self.printer_bot.ultimaker.unpause_printjob()
        #button_list = build_inline_keyboard(self.MENU_INLINELAYOUT_SETTINGS_PRINTJOB)
        #reply_markup = InlineKeyboardMarkup(button_list)

        self.edit_message_text(update, context, text=text)
        return self.PRINT_MODEL

    @authorized('control')
    def download_model_file_cb(self, update: Update, context: CallbackContext):
        try:
            document_id = update.message.document.file_id
            ducoment_name = update.message.document.file_name
            print (ducoment_name)
            model_file = context.bot.get_file(document_id)
            bytes_io = BytesIO()
            model_file.download(out=bytes_io)

            #bytes_io.seek(0)
            #print(self.printer_bot.ultimaker.print_model(ducoment_name, bytes_io.read()).json())

            bytes_io.seek(0)
            with open(ducoment_name,'wb') as out: 
                out.write(bytes_io.read())

            # with open(ducoment_name,'rb') as out: 
            #     print(type(out))
            print(self.printer_bot.ultimaker.print_model(ducoment_name, ducoment_name).json())

            # buffer = BufferedReader(bytes_io, buffer_size=20*1024*1024)
            # buffer.seek(0)
            # print(self.printer_bot.ultimaker.print_model(ducoment_name, buffer).json())

            text = self.MENU_SETTINGS_PRINTJOB_HEADER + '\n  File has been sent'

            chat_id = update.effective_chat.id
            context.bot.send_message(chat_id=chat_id, text=text)
        except Exception:
            traceback.print_exc()

        return self.PRINTJOB

        

    def edit_message_text(self, update: Update, context: CallbackContext, text, reply_markup=None, parse_mode=None):
        chat_id = update.callback_query.message.chat.id
        message_id = update.callback_query.message.message_id

        if reply_markup is None:
            reply_markup = update.callback_query.message.reply_markup

        if update.callback_query.message.text != text:
            context.bot.editMessageText(
                chat_id=chat_id, 
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    
    def done(self, update, context):
        # user_data = context.user_data
        # if 'choice' in user_data:
        #     del user_data['choice']

        # update.message.reply_text("I learned these facts about you:"
        #                         "{}"
        #                         "Until next time!".format(facts_to_str(user_data)))

        # user_data.clear()
        print ('END')
        return ConversationHandler.END