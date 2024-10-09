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
        pass

    def tearDown(self):
        pass

    def test_parsing(self):
        ''' Tests the .ntr file parsing. '''
        self.window = emu.Window(900)
        self.view = emu.View(901)
        self.view.set_window(self.window)

        # Use the demo project for testing.

        # Mock settings.
        mock_settings = {
            "project_files": ["$APPDATA\\Sublime Text\\Packages\\Notr\\example\\notr-demo.nproj"],
            "sort_tags_alpha": True,
            "mru_size": 5,
            "fixed_hl_whole_word": True,
            "section_marker_size": 1,
        }
        emu.set_settings(mock_settings)

        # Trigger the code under test.
        evt = notr.NotrEvent()
        evt.on_init([self.view])

        self.assertEqual(len(notr._get_all_tags()), 5)
        self.assertEqual(len(notr._targets), 16)
        self.assertEqual(len(notr._refs), 6)
        self.assertEqual(len(notr._parse_errors), 2)
        # self.assertEqual(len(notr._store), 13)

        self.assertEqual(len(notr._current_project['notr_paths']), 1)
        self.assertEqual(len(notr._current_project['fixed_hl']), 3)
        self.assertEqual(len(notr._current_project['sticky']), 2)

    @unittest.skip('')
    def test_GotoRef(self):
        cmd = notr.NotrGotoTargetCommand(self.view)
        cmd.run(None, False)
