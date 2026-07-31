import sys
import os
import unittest

# Set up the sublime emulation environment.
import emu_sublime_api as emu
# Import the code under test - set up path.
cut_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if cut_path not in sys.path: sys.path.insert(0, cut_path)

import notr as n


#-----------------------------------------------------------------------------------
class TestNotr(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    #------------------------------------------------------------
    def test_parsing(self):
        ''' Tests the .ntr file parsing. '''
        self.window = emu.Window(900)
        self.view = emu.View(901)
        self.view.set_window(self.window)

        # Mock settings.
        proj_fn = os.path.join(emu.packages_path(), "Notr", "test", "test.nproj")
        mock_settings = {
            "project_files": [proj_fn],
            "sort_tags_alpha": True,
            "mru_size": 5,
            "fixed_hl_whole_word": True,
        }
        emu.set_settings(mock_settings)

        # Trigger the code under test.
        evt = n.NotrEvent()
        evt.on_init([self.view])

        # print(n)

        self.assertEqual(len(n._targets), 15)
        self.assertEqual(len(n._refs), 6)
        self.assertEqual(len(n._get_all_tags()), 5)
        # self.assertEqual(len(n._parse_errors), 2)
        # self.assertEqual(len(n._store), 13)

        self.assertEqual(len(n._current_project['notr_paths']), 1)
        self.assertEqual(len(n._current_project['fixed_hl']), 3)
        self.assertEqual(len(n._current_project['sticky']), 2)

    #------------------------------------------------------------
    @unittest.skip('')
    def test_GotoRef(self):
        cmd = n.NotrGotoTargetCommand(self.view)
        cmd.run(None, False)
