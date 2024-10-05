import sys
import os
import unittest
from unittest.mock import MagicMock

# Add path to code under test.
cut_path = os.path.join(os.path.dirname(__file__), '..')
if cut_path not in sys.path:
      sys.path.insert(0, cut_path)

# Now import the sublime emulation.
import emu_sublime
import emu_sublime_plugin
sys.modules["sublime"] = emu_sublime
sys.modules["sublime_plugin"] = emu_sublime_plugin

# Now import the code under test.
from Notr import notr, table

import sbot_common as sc


#-----------------------------------------------------------------------------------
class TestNotr(unittest.TestCase):

    def setUp(self):

        notr_files_path = os.path.join(sublime.packages_path(), 'Notr', 'files')

        mock_settings = {
            "projects": [],
            "sort_tags_alpha": True,
            "mru_size": 5,
            "fixed_hl_whole_word": True,
            "section_marker_size": 1,
        }
        sublime.load_settings = MagicMock(return_value=mock_settings)

        # Mock top level entities.
        self.view = sublime.View(10)
        self.window = sublime.Window(20)
        self.view.window = MagicMock(return_value=self.window)

        # Mock syntax interrogation.
        self.syntax = sublime.Syntax('', 'Notr', False, '')
        self.view.syntax = MagicMock(return_value=self.syntax)

    def tearDown(self):
        pass

    # @unittest.skip('')
    def test_parsing(self):
        ''' Tests the .ntr file parsing. '''

        # notr._process_notr_files()
        # for e in notr._parse_errors:
        #     print(f'parse error:{e}')

        # evt = notr.NotrEvent()
        # evt.on_init([self.view])

        # self.assertEqual(len(notr._tags), 7)
        # self.assertEqual(len(notr._links), 6)
        # self.assertEqual(len(notr._refs), 6)
        # self.assertEqual(len(notr._sections), 13)
        # self.assertEqual(len(notr._parse_errors), 0)

    @unittest.skip('')
    def test_GotoRef(self):
        cmd = notr.NotrGotoTargetCommand(self.view)
        cmd.run(None, False)

    # @unittest.skip('')
    # def test_InsertRef(self):
    #     cmd = notr.NotrInsertRefCommand(self.view)
    #     edit = sublime.Edit
    #     cmd.run(edit)

