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
class TestNotr(unittest.TestCase):

    def setUp(self):

        notr_files_path = os.path.join(emu.packages_path(), 'Notr', 'files')

        mock_settings = {
            "projects": [],
            "sort_tags_alpha": True,
            "mru_size": 5,
            "fixed_hl_whole_word": True,
            "section_marker_size": 1,
        }
        emu.load_settings = MagicMock(return_value=mock_settings)

        # Mock top level entities.
        self.view = emu.View(10)
        self.window = emu.Window(20)
        self.view.window = MagicMock(return_value=self.window)

        # Mock syntax interrogation.
        self.syntax = emu.Syntax('', 'Notr', False, '')
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
    #     edit = emu.Edit
    #     cmd.run(edit)

