import os
import math
import textwrap
import pathlib
import webbrowser
import html
import sublime
import sublime_plugin
# from .sbot_common import *

NOTR_SETTINGS_FILE = "Notr.sublime-settings"


#-----------------------------------------------------------------------------------
class NotrToHtmlCommand(sublime_plugin.TextCommand):
    ''' Make a pretty. '''
    # Steal from / combine with render.


    _rows = 0
    _row_num = 0
    _line_numbers = False

    def run(self, edit, line_numbers):
        self._line_numbers = line_numbers
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
