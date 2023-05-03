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

''' Tool:
- cut/copy/paste/move section/heading
- folding by section
- heading nav pane

- insert link to a heading 9n this or other doc
- phun with phantoms?
- paste file/url from clipboard

- change list item state

- table manipulations similar to csvplugin. Autofit.




'''

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
