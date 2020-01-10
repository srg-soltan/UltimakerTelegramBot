import json
from functools import wraps
from telegram import Update
from telegram.ext import Updater, CallbackContext


AUTHORIZED_USERS = {}
ACCESS_LEVELS = []
USERS = []
NOTIFY_GROUP = set()

def auth_load_users(users_config):
    ACCESS_LEVELS = users_config['access_levels']

    USERS = users_config['users']
    
    for level in ACCESS_LEVELS:
        AUTHORIZED_USERS[level] = set()

    NOTIFY_GROUP = set()
    
    for user in USERS:
        # higher access levels get acces to lower
        for level in range(0, user['access_level'] + 1):
            AUTHORIZED_USERS[ACCESS_LEVELS[level]].add(user['id'])
        
        if user['notify']:
            NOTIFY_GROUP.add(user['id'])

def authorized(level):

    def decorator(function):
        @wraps(function)
        def wrapper(self, update: Update, context: CallbackContext, *args, **kwargs):
            if update.message is not None:
                user_id = update.message.from_user.id
            else:
                user_id = update._effective_user.id
            
            if user_id in AUTHORIZED_USERS[level]:
                return function(self, update, context, *args, **kwargs)

        return wrapper

    return decorator

def auth_get_notify_group():
    return NOTIFY_GROUP

