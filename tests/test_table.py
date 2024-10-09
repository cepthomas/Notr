import sys
import os
import unittest
from unittest.mock import MagicMock


# Set up the sublime emulation environment.
import emu_sublime_api as emu

# Import the code under test.
import table
import sbot_common as sc


#-----------------------------------------------------------------------------------
class TestTable(unittest.TestCase):

    # Test text from file.
    test_text = None
    # String version.
    test_text_str = None

    print('=== TestTable')

    #------------------------------------------------------------
    # Mock scope interrogation by row. Corresponds to table in table1.ntr.
    def mock_scope_name(self, *args, **kwargs):
        rc = self.view.rowcol(args[0])
        if rc[0] == 5:
            return 'text.notr meta.table.header'
        elif rc[0] >= 6 and rc[0] <= 11:
            return 'text.notr meta.table'
        else:
            return 'text.notr'

    #------------------------------------------------------------
    def setUp(self):
        # Get test text.
        my_dir = os.path.dirname(__file__)
        fn = os.path.join(my_dir, 'table1.ntr')
        with open(fn, 'r') as f:
            self.test_text = f.readlines()
        # String version.
        self.test_text_str = ''.join(self.test_text)

        # Create top level entities.
        self.view = emu.View(10)
        self.view.set_window(emu.Window(20))
        self.view.set_syntax(emu.Syntax('', 'Notr', False, ''))

    #------------------------------------------------------------
    def tearDown(self):
        pass

    #------------------------------------------------------------
    def test_table_internal(self):
        ''' Some basic tests. '''

        self.view.insert(None, 0, self.test_text_str)

        # Test rowcol() and text_point().
        self.assertEqual(self.view.rowcol(24), (1, 5))
        self.assertEqual(self.view.rowcol(148), (7, 27))
        self.assertEqual(self.view.rowcol(257), (11, 27))
        self.assertEqual(self.view.rowcol(263), (13, 0))
        self.assertEqual(self.view.text_point(1, 5), 24)
        self.assertEqual(self.view.text_point(7, 27), 148)
        self.assertEqual(self.view.text_point(11, 27), 257)
        self.assertEqual(self.view.text_point(13, 0), 263)

    #------------------------------------------------------------
    def test_TableFit(self):
        ''' TableFitCommand. Fitting column widths. '''

        self.view.insert(None, 0, self.test_text_str)

        # Mock scope interrogation.
        self.view.scope_name = MagicMock(side_effect=self.mock_scope_name)

        # Mock view selection.
        sel = emu.Selection(self.view.id())
        sel.add(emu.Region(130, 140)) # somewhere in table
        self.view.set_selection(sel)

        # Run the command.
        cmd = table.TableFitCommand(self.view)
        cmd.run(None)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '| ME    | 11   | Red                   |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| CO    | 15   |                       |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '|       | 2    | Green                 |       |',
            '| WY    | 45   | White                 |       |',
            ''])

        reg = cmd.get_table_region()

        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

    #------------------------------------------------------------
    def test_TableSortByColAlpha(self):
        ''' TableSortByColCommand for text. '''

        self.view.insert(None, 0, self.test_text_str)

        # Mock scope interrogation.
        self.view.scope_name = MagicMock(side_effect=self.mock_scope_name)

        # Mock view selection for column 0.
        sel = emu.Selection(self.view.id())
        sel.add(emu.Region(175, 175))
        self.view.set_selection(sel)

        # Run the command.
        cmd = table.TableSortColCommand(self.view)
        cmd.run(None, asc=True)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '|       | 2    | Green                 |       |',
            '| CO    | 15   |                       |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| ME    | 11   | Red                   |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '| WY    | 45   | White                 |       |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

        # Run command again to sort opposite order. Tweak caret to match fitted table.
        sel.clear()
        sel.add(emu.Region(266, 266))
        cmd.run(None, asc=False)

        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '| WY    | 45   | White                 |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '| ME    | 11   | Red                   |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| CO    | 15   |                       |       |',
            '|       | 2    | Green                 |       |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

    #------------------------------------------------------------
    def test_TableSortByColNumeric(self):
        ''' TableSortByColCommand for numbers. '''

        self.view.insert(None, 0, self.test_text_str)

        # Mock scope interrogation.
        self.view.scope_name = MagicMock(side_effect=self.mock_scope_name)

        # Mock view selection for column 1.
        sel = emu.Selection(self.view.id())
        sel.add(emu.Region(216, 216))
        self.view.set_selection(sel)

        # Run the command.
        cmd = table.TableSortColCommand(self.view)
        cmd.run(None, asc=True)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '|       | 2    | Green                 |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '| ME    | 11   | Red                   |       |',
            '| CO    | 15   |                       |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| WY    | 45   | White                 |       |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

        # Run command again to sort opposite order. Tweak caret to match fitted table.
        sel.clear()
        sel.add(emu.Region(324, 324))
        cmd.run(None, asc=False)

        exptext = '\n'.join([
            '| State | Size | Color                 |       |',
            '| WY    | 45   | White                 |       |',
            '| IA    | 31   | Blue                  | extra |',
            '| CO    | 15   |                       |       |',
            '| ME    | 11   | Red                   |       |',
            '| NY    | 4    | Yellow  space after-> |       |',
            '|       | 2    | Green                 |       |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

    #------------------------------------------------------------
    def test_TableInsertColBeginning(self):
        ''' TableInsertColCommand at beginning of line. '''

        self.view.insert(None, 0, self.test_text_str)

        # Mock scope interrogation.
        self.view.scope_name = MagicMock(side_effect=self.mock_scope_name)

        # Mock view selection before first column.
        sel = emu.Selection(self.view.id())
        sel.add(emu.Region(121, 121))
        self.view.set_selection(sel)

        # Run the command.
        cmd = table.TableInsertColCommand(self.view)
        cmd.run(None)

        # Should look like this now.
        exptext = '\n'.join([
            '|  | State | Size | Color                 |       |',
            '|  | ME    | 11   | Red                   |       |',
            '|  | IA    | 31   | Blue                  | extra |',
            '|  | CO    | 15   |                       |       |',
            '|  | NY    | 4    | Yellow  space after-> |       |',
            '|  |       | 2    | Green                 |       |',
            '|  | WY    | 45   | White                 |       |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

    #------------------------------------------------------------
    def test_TableInsertColMiddle(self):
        ''' TableInsertColCommand in middle of line. '''

        self.view.insert(None, 0, self.test_text_str)

        # Mock scope interrogation.
        self.view.scope_name = MagicMock(side_effect=self.mock_scope_name)

        # Mock view selection for column 1.
        sel = emu.Selection(self.view.id())
        sel.add(emu.Region(105, 105))
        self.view.set_selection(sel)

        # Run the command.
        cmd = table.TableInsertColCommand(self.view)
        cmd.run(None)

        # Should look like this now.
        exptext = '\n'.join([
            '| State |  | Size | Color                 |       |',
            '| ME    |  | 11   | Red                   |       |',
            '| IA    |  | 31   | Blue                  | extra |',
            '| CO    |  | 15   |                       |       |',
            '| NY    |  | 4    | Yellow  space after-> |       |',
            '|       |  | 2    | Green                 |       |',
            '| WY    |  | 45   | White                 |       |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

    #------------------------------------------------------------
    @unittest.skip('TODO2 Doesn\'t work perfectly for ragged - user should fit first.')
    def test_TableInsertColEnd(self):
        ''' TableInsertColCommand at end of line. '''

        self.view.insert(None, 0, self.test_text_str)

        # Mock scope interrogation.
        self.view.scope_name = MagicMock(side_effect=self.mock_scope_name)

        # Mock view selection at end.
        sel = emu.Selection(self.view.id())
        #sel.add(emu.Region(154, 154)) # row 7
        sel.add(emu.Region(210, 210)) # row 9
        self.view.set_selection(sel)

        # Run the command.
        cmd = table.TableInsertColCommand(self.view)
        cmd.run(None)

        # Should look like this now.
        exptext = '\n'.join([
            '| State | Size | Color                 |       |  |',
            '| ME    | 11   | Red                   |       |  |',
            '| IA    | 31   | Blue                  | extra |  |',
            '| CO    | 15   |                       |       |  |',
            '| NY    | 4    | Yellow  space after-> |       |  |',
            '|       | 2    | Green                 |       |  |',
            '| WY    | 45   | White                 |       |  |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)

    #------------------------------------------------------------
    def test_TableDeleteCol(self):
        ''' TableDeleteColCommand. '''

        self.view.insert(None, 0, self.test_text_str)

        # Mock scope interrogation.
        self.view.scope_name = MagicMock(side_effect=self.mock_scope_name)

        # Mock view selection at column 0.
        sel = emu.Selection(self.view.id())
        sel.add(emu.Region(125, 125))
        self.view.set_selection(sel)

        # Run the command.
        cmd = table.TableDeleteColCommand(self.view)

        cmd.run(None)

        # Should look like this now.
        exptext = '\n'.join([
            '| Size | Color                 |       |',
            '| 11   | Red                   |       |',
            '| 31   | Blue                  | extra |',
            '| 15   |                       |       |',
            '| 4    | Yellow  space after-> |       |',
            '| 2    | Green                 |       |',
            '| 45   | White                 |       |',
            ''])

        reg = cmd.get_table_region()
        gentext = self.view.substr(reg)
        self.assertEqual(gentext, exptext)


#-----------------------------------------------------------------------------------
if __name__ == '__main__':
    # https://docs.python.org/3/library/unittest.html#unittest.main
    tp = unittest.main()  # verbosity=2, exit=False)
    print(tp.result)
