import sys
import os
import importlib
import sublime
from unittesting import TestCase
from unittest.mock import MagicMock


#-----------------------------------------------------------------------------------
class TestNotr(TestCase):

    # Code under test.
    mod_notr = sys.modules["Notr.notr"]

    def setUp(self):
        self.view = sublime.active_window().new_file()

    def tearDown(self):
        # if self.view:
        self.view.set_scratch(True)
        self.view.window().focus_view(self.view)
        self.view.window().run_command("close_file")

    def setText(self, string):
        self.view.run_command("insert", {"characters": string})

    def getRow(self, row):
        return self.view.substr(self.view.line(self.view.text_point(row, 0)))

    def test_hello_world(self):
        self.setText("new ")
        self.view.run_command("hello_world")
        first_row = self.getRow(0)
        self.assertEqual(first_row, "new hello world")

    def test_parsing(self):
        ''' Test the .ntr file parsing. TODO test messes with real Notr.store file? '''
        # Project file for testing.
        project_fn = os.path.join(sublime.packages_path(), "Notr", "tests", "test.nproj")

        self.mod_notr._open_project(project_fn)
        self.mod_notr._process_all_files(self.view.window())

        self.assertEqual(len(self.mod_notr._targets), 4)
        self.assertEqual(len(self.mod_notr._refs), 0)
        self.assertEqual(len(self.mod_notr._get_all_tags()), 4)
        self.assertEqual(len(self.mod_notr._user_errors), 0)
        self.assertEqual(len(self.mod_notr._store), 3)

        self.assertEqual(len(self.mod_notr._current_project['notr_paths']), 1)
        self.assertEqual(len(self.mod_notr._current_project['fixed_hl']), 3)
        self.assertEqual(len(self.mod_notr._current_project['sticky']), 2)
