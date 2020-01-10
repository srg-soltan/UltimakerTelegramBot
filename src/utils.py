# -*- coding: utf-8 -*-

from telegram.ext import Updater, CallbackContext
from telegram import Update, ChatAction
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from functools import wraps
import sys


def build_inline_keyboard(layout):
    return [[InlineKeyboardButton(si, callback_data=si) for si in s] if type(s) == list 
            else [InlineKeyboardButton(s, callback_data=s)] for s in layout]

def build_keyboard(layout):
    return [[KeyboardButton(si) for si in s] if type(s) == list else [KeyboardButton(s)] for s in layout]

def progress_bar(progress, bars_count=5, bar_w='▫', bar_b='⬛', bar_cb='▪◾'):
    if progress >= 1.0:
        return bar_b * bars_count
    b = int(progress * bars_count)
    w = bars_count - 1 - b
    whites = bar_w * w
    blacks = bar_b * b

    p = b / float(bars_count)
    d = progress - p
    z = int(bars_count * len(bar_cb) * d)
    middle = bar_cb[z]

    return blacks + middle + whites

def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(function):
        @wraps(function)
        def wrapper(self, update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_chat.id, action=action)
            return function(self, update, context,  *args, **kwargs)
        return wrapper
    
    return decorator

send_typing_action = send_action(ChatAction.TYPING)
send_upload_video_action = send_action(ChatAction.UPLOAD_VIDEO)
send_upload_photo_action = send_action(ChatAction.UPLOAD_PHOTO)

