# -*- coding: utf-8 -*-

def format_printjob_status(text):
    if text == 'printing':
        text = 'Printing ▶'
    elif text == 'pre_print':
        text = 'Pre Print ⚪'
    elif text == 'post_print':
        text = 'Post Print 🔘'
    elif text == 'paused':
        text = 'Paused ‼'
    elif text == 'wait_cleanup':
        text = 'Wait Cleanup ✅'
    elif text == 'resuming':
        text = 'Resuming ⏯'
    elif text == 'pausing':
        text = 'Pausing ⏮'
    elif text == 'no_printjob':
        text = 'No Print Job ⚪'
    elif text == 'none':
        text = 'None'
    return text

def format_printer_status(text):
    if text == 'idle':
        text = 'Idle ⚪'
    elif text == 'printing':
        text = 'Printing ▶'
    elif text == 'error':
        text = 'Error ‼'
    elif text == 'maintenance':
        text = 'Maintenance 🛠'
    elif text == 'booting':
        text = 'Booting 🖥'
    return text

