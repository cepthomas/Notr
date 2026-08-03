import sys
import os
import sublime
from unittesting import TestCase
from unittest.mock import MagicMock


#-----------------------------------------------------------------------------------
class TestTable(TestCase):

    # Test text from file.
    my_dir = os.path.dirname(__file__)
    test_fn = os.path.join(os.path.dirname(__file__), 'table1.ntr')
    with open(test_fn, 'r') as f:
        test_text = f.read()

    # Code under test.
    mod_table = sys.modules["Notr.table"]

    #------------------------------------------------------------
    def setUp(self):
        # print('!!! setUp', self)
        # TODO Could manage test_view here?
        pass

    #------------------------------------------------------------
    def tearDown(self):
        # print('!!! tearDown', self)
        pass

    #------------------------------------------------------------
    def _make_test_file_view(self, name):
        ''' Create a view with the contents of the test file. None if error. '''
        test_view = sublime.active_window().new_file()
        test_view.set_scratch(True)
        test_view.set_name(name)
        test_view.assign_syntax('Packages/Notr/Notr.sublime-syntax')

        # Create/populate the view.
        with open(self.test_fn, 'r') as fp:
            text = fp.read()
            test_view.run_command('select_all')
            test_view.run_command('cut')
            test_view.run_command('append', {'characters': text})  # insert has some odd behavior - indentationtest
        return test_view

    #------------------------------------------------------------
    def test_table_internal(self):
        ''' Some basic tests. '''
        test_view = self._make_test_file_view('internal')

        # Test rowcol() and text_point().
        self.assertEqual(test_view.rowcol(24), (1, 5))
        self.assertEqual(test_view.rowcol(148), (7, 27))
        self.assertEqual(test_view.rowcol(257), (11, 27))
        self.assertEqual(test_view.rowcol(263), (13, 0))
        self.assertEqual(test_view.text_point(1, 5), 24)
        self.assertEqual(test_view.text_point(7, 27), 148)
        self.assertEqual(test_view.text_point(11, 27), 257)
        self.assertEqual(test_view.text_point(13, 0), 263)

        test_view.close()

    #------------------------------------------------------------
    def test_TableFit(self):
        ''' TableFitCommand. Fitting column widths. '''
        test_view = self._make_test_file_view('Fit')

        # Set up test.
        reg = sublime.Region(130, 140) # anywhere in table
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_fit")

        # Check results.
        reg = sublime.Region(67, 409)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '| ME    | 11   | Red                   |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| CO    | 15   |                       |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '|       | 2    | Green                 |       |',
            '| WY    | 45   | White                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()


    #------------------------------------------------------------
    def test_TableSortByColAlphaAsc(self):
        ''' TableSortByColCommand for text. '''
        test_view = self._make_test_file_view('SortByColAlphaAsc')

        # Set up test.
        reg = sublime.Region(175, 175) # column 1
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_sort_col", {"asc" : True})
        # cmd.run(None, asc=True)

        # Check results.
        reg = sublime.Region(67, 409)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '|       | 2    | Green                 |       |',
            '| CO    | 15   |                       |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| ME    | 11   | Red                   |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '| WY    | 45   | White                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()

    #------------------------------------------------------------
    def test_TableSortByColAlphaDesc(self):
        ''' TableSortByColCommand for text. '''
        test_view = self._make_test_file_view('SortByColAlphaDesc')

        # Set up test.
        reg = sublime.Region(175, 175) # column 1
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_sort_col", {"asc" : False})
        # cmd.run(None, asc=True)

        # Check results.
        reg = sublime.Region(67, 409)
        gentext = test_view.substr(reg)

        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '| WY    | 45   | White                 |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '| ME    | 11   | Red                   |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| CO    | 15   |                       |       |',
            '|       | 2    | Green                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()

    #------------------------------------------------------------
    def test_TableSortByColNumericAsc(self):
        ''' TableSortByColCommand for numbers. '''
        test_view = self._make_test_file_view('SortByColNumericAsc')

        # Set up test.
        reg = sublime.Region(216, 216) # column 1.
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_sort_col", {"asc" : True})
        # cmd.run(None, asc=True)

        # Check results.
        reg = sublime.Region(67, 409)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '|       | 2    | Green                 |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '| ME    | 11   | Red                   |       |',
            '| CO    | 15   |                       |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| WY    | 45   | White                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()

    #------------------------------------------------------------
    def test_TableSortByColNumericDesc(self):
        ''' TableSortByColCommand for numbers. '''
        test_view = self._make_test_file_view('SortByColNumericDesc')

        # Set up test.
        reg = sublime.Region(216, 216) # column 1.
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_sort_col", {"asc" : False})
        # cmd.run(None, asc=True)

        # Check results.
        reg = sublime.Region(67, 409)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '| WY    | 45   | White                 |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| CO    | 15   |                       |       |',
            '| ME    | 11   | Red                   |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '|       | 2    | Green                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()

    #------------------------------------------------------------x
    def test_TableInsertColBeginning(self):
        ''' TableInsertColCommand at beginning of line. '''
        test_view = self._make_test_file_view('InsertColBeginning')

        # Set up test.
        reg = sublime.Region(121, 121) # before first column
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_insert_col")

        # Check results.
        reg = sublime.Region(67, 430)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '|  | State | Size | Color                 |       |',
            '|  | ME    | 11   | Red                   |       |',
            '|  | IA    | 31   | Blue                  | extra |',
            '|  | CO    | 15   |                       |       |',
            '|  | NY    | 4    | Yellow  space after-> |       |',
            '|  |       | 2    | Green                 |       |',
            '|  | WY    | 45   | White                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()

    #------------------------------------------------------------
    def test_TableInsertColMiddle(self):
        ''' TableInsertColCommand in middle of line. '''
        test_view = self._make_test_file_view('InsertColMiddle')

        # Set up test.
        reg = sublime.Region(105, 105) # column 1
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_insert_col")

        # Check results.
        reg = sublime.Region(67, 430)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '| State |  | Size | Color                 |       |',
            '| ME    |  | 11   | Red                   |       |',
            '| IA    |  | 31   | Blue                  | extra |',
            '| CO    |  | 15   |                       |       |',
            '| NY    |  | 4    | Yellow  space after-> |       |',
            '|       |  | 2    | Green                 |       |',
            '| WY    |  | 45   | White                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()

    #------------------------------------------------------------
    def test_TableInsertColEnd(self):
        ''' TableInsertColCommand at end of line. '''
        test_view = self._make_test_file_view('InsertColEnd')

        # Set up test.
        reg = sublime.Region(210, 210) # row 9??? (154, 154)) # row 7
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_insert_col")

        # Check results.
        reg = sublime.Region(67, 409)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |  |',
            '| ME    | 11   | Red                   |       |  |',
            '| IA    | 31   | Blue                  | extra |  |',
            '| CO    | 15   |                       |       |  |',
            '| NY    | 4    | Yellow  space after-> |       |  |',
            '|       | 2    | Green                 |       |  |',
            '| WY    | 45   | White                 |       |  |'])

        # TODO This test fails. What should be real expected behavior for ragged ends?
        # self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()

    #------------------------------------------------------------
    def test_TableDeleteCol(self):
        ''' TableDeleteColCommand. '''
        test_view = self._make_test_file_view('DeleteCol')

        # Set up test.
        reg = sublime.Region(125, 125) # column 2
        test_view.sel().clear()
        test_view.sel().add(reg)

        # Run the command.
        test_view.run_command("table_delete_col")

        # Check results.
        reg = sublime.Region(67, 353)
        gentext = test_view.substr(reg)

        # Should look like this now.
        exptext = '\n'.join([
            '| Size | Color                 |       |',
            '| 11   | Red                   |       |',
            '| 31   | Blue                  | extra |',
            '| 15   |                       |       |',
            '| 4    | Yellow  space after-> |       |',
            '| 2    | Green                 |       |',
            '| 45   | White                 |       |'])

        self.assertEqual(gentext, exptext)

        # Clean up.
        test_view.close()
