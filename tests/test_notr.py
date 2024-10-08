import sys
import os
import unittest
from unittest.mock import MagicMock


# Set up the sublime emulation environment.
import emu_sublime_api as emu

# Import the code under test.
import notr
import sbot_common as sc


#-----------------------------------------------------------------------------------
class TestNotr(unittest.TestCase):  # TODOT fix for multiple projects.

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parsing(self):
        ''' Tests the .ntr file parsing. '''
        self.window = emu.Window(900)
        self.view = emu.View(901)

        mock_settings = {
            "projects": [],
            "sort_tags_alpha": True,
            "mru_size": 5,
            "fixed_hl_whole_word": True,
            "section_marker_size": 1,
        }
        # emu.set_settings(mock_settings)


        # Mock settings.
        emu.settings = MagicMock(return_value=mock_settings)
        emu.load_settings = MagicMock(return_value=mock_settings)

        notr._process_notr_files(self.window)
        for e in notr._parse_errors:
            print(f'parse error:{e}')

        evt = notr.NotrEvent()
        evt.on_init([self.view])

        # self.assertEqual(len(notr._get_all_tags()), 7)
        # self.assertEqual(len(notr._links), 6)
        # self.assertEqual(len(notr._refs), 6)
        # self.assertEqual(len(notr._sections), 13)
        self.assertEqual(len(notr._parse_errors), 0)

    # @unittest.skip('')
    # def test_InsertRef(self):
    #     cmd = notr.NotrInsertRefCommand(self.view)
    #     edit = emu.Edit
    #     cmd.run(edit)

    @unittest.skip('')
    def test_GotoRef(self):
        cmd = notr.NotrGotoTargetCommand(self.view)
        cmd.run(None, False)
