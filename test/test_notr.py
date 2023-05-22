import unittest
from unittest.mock import MagicMock
import sublime
import sublime_plugin
from sbot_common import *
import Notr.notr as snotr


#-----------------------------------------------------------------------------------
class TestNotr(unittest.TestCase):

    view = None

    def setUp(self):
        # Mock settings.
        mock_settings = {
            "notr_paths": ["C:\\Users\\cepth\\AppData\\Roaming\\Sublime Text\\Packages\\Notr\\test\\files"],
            "visual_line_length": 100,
            "user_hl": [["2DO", "things"], ["user"], ["dynamic"], ["and_a"], ["and_b"], ["and_c"]],
            "user_hl_whole_word": True,
        }
        sublime.load_settings = MagicMock(return_value = mock_settings)

        # Mock settings with side effect.
        #settings = sublime.load_settings('NOTR_SETTINGS_FILE')
        #notr_paths = settings.get('notr_paths')
        #def settings_get_side_effect(*args, **kwargs):
        #    if args[0] == 'notr_paths':
        #        return ["C:\\Users\\cepth\\AppData\\Roaming\\Sublime Text\\Packages\\Notr",
        #                "C:\\Users\\cepth\\OneDrive\\OneDrive Documents\\_notes" ]
        #    else:
        #        raise Exception('haha')
        #settings.get = MagicMock(side_effect = settings_get_side_effect)


        # Old stuff
        self.view = sublime.View(600)
        sel = sublime.Selection(self.view.id())
        sel.add(sublime.Region(10, 20, 101))
        self.view.sel = MagicMock(return_value = sel)

        # Mock syntax.
        syntax = sublime.Syntax()
        syntax.name = MagicMock(return_value = 'Notr')
        self.view.syntax = MagicMock(return_value = syntax)

    def tearDown(self):
        pass

    def test_init(self):
        evt = snotr.NotrEvent()
        evt.on_init([self.view])

        self.assertEqual(len(snotr._tags), 7)
        self.assertEqual(len(snotr._links), 6)
        #self.assertEqual(len(snotr._refs), 99)
        self.assertEqual(len(snotr._sections), 13)

    def test_GotoRef(self):
        edit = sublime.Edit('token')
        cmd = snotr.NotrGotoRefCommand(self.view)
        cmd.run(edit)

    def test_GotoSection(self):
        edit = sublime.Edit('token')
        cmd = snotr.NotrGotoSectionCommand(self.view)
        #cmd.run(edit)

    def test_InsertRef(self):
        edit = sublime.Edit('token')
        cmd = snotr.NotrInsertRefCommand(self.view)
        #cmd.run(edit)


#-----------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
