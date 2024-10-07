# Some of this is loosely based on https://github.com/wadetb/Sublime-Text-Advanced-CSV.
# Source licenses are MIT so all is good. Steal This Code.

import sys
import os
import sublime
import sublime_plugin

# Kludge to make testing work.
try:
    import sbot_common as sc
except:
    from . import sbot_common as sc

# TODO Make into a generic component?

# TODOF allow '|' in tables -> make delim configurable. maybe like '||'?
DELIM = '|'


#-----------------------------------------------------------------------------------
class TableValue:
    ''' One value in a TableMatrix row/col cell. '''

    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return f'{self.text}'

    def as_float(self):
        try:
            return True, float(self.text)
        except ValueError:
            return False, None

    def compare(self, other):
        self_is_float, self_float = self.as_float()
        other_is_float, other_float = other.as_float()

        if self_is_float and other_is_float:
            return self_float - other_float
        if self.text > other.text:
            return 1
        if self.text < other.text:
            return -1
        return 0

    def __lt__(self, other):
        return self.compare(other) < 0

    def __eq__(self, other):
        return self.compare(other) == 0


#-----------------------------------------------------------------------------------
class TableMatrix:
    ''' Container for the TableValues in the cells. '''

    def __init__(self, text):
        self.rows = []  # List of lists of row columns
        self.valid = False

        # Split each line into table rows.
        for line in text.splitlines():
            cols = []
            parts = line.split(DELIM)

            # Process the cells.
            # Rows honor empty cells except for the last one. Whitespace cells are converted to empty.
            for i in range(1, len(parts)):
                s = parts[i].strip()
                if i < len(parts) - 1 or len(s) > 0:
                    cols.append(TableValue(s))
            self.rows.append(cols)

        # Make the collection square.
        num_columns = self.count_columns()
        for r in self.rows:
            while len(r) < num_columns:
                r.append(TableValue(''))

        self.valid = True

    def __repr__(self):
        return f'rows:{self.rows}'

    def validate_col_sel(self, table_col):
        num_cols = self.count_columns()
        return table_col >= 0 and table_col < num_cols

    def sort_column(self, table_col, asc):
        ''' General row sorter. '''
        class Compare:
            def __init__(self, row):
                self.value = row[table_col] # if len(self.rows) > 0 else TableValue('') 

            def __lt__(self, other):
                return self.value < other.value

            def __eq__(self, other):
                return self.value == other.value

        if self.validate_col_sel(table_col):
            # Assume header always.
            self.rows[1:] = sorted(self.rows[1:], key=lambda row: Compare(row), reverse=not asc)

    def insert_column(self, table_col):
        if table_col >= self.count_columns():
            for row in self.rows:
                row.append(TableValue(''))
        elif table_col < 0:
            for row in self.rows:
                row.insert(0, TableValue(''))
        else:
            for row in self.rows:
                row.insert(table_col, TableValue(''))

    def delete_column(self, table_col):
        if self.validate_col_sel(table_col):
            for row in self.rows:
                row.pop(table_col)

    def count_columns(self):
        num_columns = 0
        for row in self.rows:
            num_columns = max(num_columns, len(row))
        return num_columns

    def format(self):
        ''' Format the output for display. '''
        output = []

        # Measure all columns.
        column_widths = [0] * self.count_columns()
        for row in self.rows:
            for icol, value in enumerate(row):
                text = value.text
                # text = self.QuoteText(value.text)
                width = len(text)
                if width > column_widths[icol]:
                    column_widths[icol] = width

        # Generate the output text.
        for _, row in enumerate(self.rows):
            row_text = []
            for icol, value in enumerate(row):
                column_width = column_widths[icol] + 2  # add pad
                text = (' ' + value.text).ljust(column_width)
                row_text.append(text)
            output.append(DELIM + DELIM.join(row_text) + DELIM)

        return '\n'.join(output) + '\n'


#-----------------------------------------------------------------------------------
class TableCommand(sublime_plugin.TextCommand):
    ''' Common table command stuff. '''

    def __init__(self, view):
        self.view = view
        # 0-based row where the caret is.
        self.table_row_sel = None
        # 0-based column where the caret is. -1 is before the first column and >= num columns is at end.
        self.table_col_sel = None

    def is_visible(self):
        ''' Show this? '''
        caret = sc.get_single_caret(self.view)
        vis = caret is not None and self.is_table(caret)
        return vis 

    def start(self):
        ''' Collect the table the caret is in. '''
        self.region = self.get_table_region()
        text = self.view.substr(self.region) if self.region is not None else ''
        self.matrix = TableMatrix(text)  # create matrix from table text

    def finish(self, edit):
        ''' Display the table. '''
        if self.region is not None:
            output = self.matrix.format()
            self.view.replace(edit, self.region, output)

    def is_table(self, point):
        ''' True if the point is in a table. '''
        scope = self.view.scope_name(point).rstrip()
        scopes = scope.split()
        is_hdr = "meta.table.header" in scopes
        is_table = "meta.table" in scopes
        return is_table or is_hdr

    def get_table_region(self):
        ''' Get the region for the current selected table, including the header.
            Returns None if it's not a table. Also finds row/column in the table.
        '''
        region = None
        v = self.view

        caret = sc.get_single_caret(v)
        if caret is None:
            return None

        caret_row = v.rowcol(caret)[0]
        caret_col = v.rowcol(caret)[1]

        # Find the first row.
        start_row = caret_row
        end_row = -1
        current_row = start_row
        done = False
        while not done:
            point = v.text_point(current_row, 0)
            if self.is_table(point):
                start_row = current_row
                current_row -= 1
            else:
                done = True

        # Find the last row.
        current_row = caret_row
        done = False
        while not done:
            point = v.text_point(current_row, 0)
            if point >= len(v):
                done = True
            else:
                if self.is_table(point):
                    end_row = current_row
                    current_row += 1
                else:
                    done = True

        # Get the region and table row/col selected.
        if start_row != -1 and end_row != -1:
            start_point = v.text_point(start_row, 0)
            end_point = v.full_line(v.text_point(end_row, 0)).b
            region = sublime.Region(start_point, end_point)

            # Calc the table row.
            self.table_row_sel = caret_row - start_row

            # Calc the table column by counting delimiters between start and caret.
            sel_line_text = v.substr(v.full_line(caret))
            self.table_col_sel = sel_line_text.count(DELIM, 0, caret_col) - 1 # correct count to columns
        else:
            region = None
            self.table_row_sel = None
            self.table_col_sel = None

        return region


#-----------------------------------------------------------------------------------
class TableFitCommand(TableCommand):
    
    def __init__(self, view):
        super().__init__(view)

    def run(self, edit):
        super().start()
        # do work
        # ... no work other than formatting
        # finish
        super().finish(edit)


#-----------------------------------------------------------------------------------
class TableSortColCommand(TableCommand):

    def __init__(self, view):
        super().__init__(view)

    def run(self, edit, asc):
        super().start()
        # do work
        self.matrix.sort_column(self.table_col_sel, asc)
        # finish
        super().finish(edit)
        

#-----------------------------------------------------------------------------------
class TableInsertColCommand(TableCommand):

    def __init__(self, view):
        super().__init__(view)

    def run(self, edit):
        super().start()
        # do work
        self.matrix.insert_column(self.table_col_sel)
        # finish
        super().finish(edit)


#-----------------------------------------------------------------------------------
class TableDeleteColCommand(TableCommand):

    def __init__(self, view):
        super().__init__(view)

    def run(self, edit):
        super().start()
        # do work
        self.matrix.delete_column(self.table_col_sel)
        # finish
        super().finish(edit)
