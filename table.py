# The guts of this is based on https://github.com/wadetb/Sublime-Text-Advanced-CSV.
# Basically the raw matrix manipulation without formatting, expressions, quoting, optional header, compact, ...
# Source license is MIT so all is good. I invite others to steal this also.
# 
# Originally written by Eric Martel (emartel@gmail.com / www.ericmartel.com)
# Improved by Wade Brainerd (wadetb@gmail.com / www.wadeb.com)

import sublime
import sublime_plugin
from . import sbot_common as sc


#-----------------------------------------------------------------------------------
class TableValue:
    ''' One value in a TableMatrix row/col cell. '''

    def __init__(self, text):#, first_char_index=0, last_char_index=0):
        self.text = text
        # self.first_char_index = first_char_index
        # self.last_char_index = last_char_index

    def as_float(self):
        try:
            return True, float(self.text)
        except ValueError:
            return False, None

    def compare(self, other):
        ret = 0

        a_is_float, a_float = self.as_float()
        b_is_float, b_float = other.as_float()

        if a_is_float and b_is_float:
            ret = a_float - b_float
        if self.text > other.text:
            ret = 1
        if self.text < other.text:
            ret = -1

        return ret

    def __lt__(self, other):
        return self.compare(other) < 0

    def __eq__(self, other):
        return self.compare(other) == 0


#-----------------------------------------------------------------------------------
class TableMatrix:
    ''' Container for the TableValues in the cells. '''

    _delimiter = '|'

    def __init__(self, text):
        # self.view = view
        self.rows = []  # List of lists of row columns
        self.num_columns = 0
        self.valid = False

        for line in text.split('\n'):
            cols = []
            for val in line.split(self._delimiter):
                cols.append(TableValue(val.strip()))
            self.rows.append(cols)
            # Calc col count.
            if len(cols) > self.num_columns:
                self.num_columns = len(cols)
            self.valid = True

    def __repr__(self):
        return f'rows:{self.rows}'

    def sort_by_column(self, column_index, asc):
        ''' General row sorter. '''

        class Compare:
            def __init__(self, row):
                self.value = row[column_index] if len(self.rows) > 0 else TableValue('') 

            def __lt__(self, other):
                return self.value < other.value

            def __eq__(self, other):
                return self.value == other.value

        # Assume header always.
        self.rows[1:] = sorted(self.rows[1:], key=lambda row: Compare(row), reverse=not asc)

    def insert_column(self, column_index):
        for row in self.rows:
            if column_index <= len(row):
                row.insert(column_index, TableValue(''))

    def delete_column(self, column_index):
        for row in self.rows:
            if column_index < len(row):
                row.pop(column_index)

    def measure_columns(self):
        self.column_widths = [0] * self.num_columns

        for row in self.rows:
            for column_index, value in enumerate(row):
                text = value.text
                # text = self.QuoteText(value.text)
                width = len(text)
                if width > self.column_widths[column_index]:
                    self.column_widths[column_index] = width

    def format(self):
        ''' Format the output for display. '''
        output = ''

        self.measure_columns()

        for row_index, row in enumerate(self.rows):
            row_text = ''

            for column_index, value in enumerate(row):
                column_width = self.column_widths[column_index]
                text = value.text.ljust(column_width)
                row_text += text
                row_text += self._delimiter
            output += row_text

            if row_index < len(self.rows) - 1:
                output += '\n'

        return output

    def parse_row(self, row):
        columns = []

        currentword = ''
        first_char_index = 0
        char_index = 0

        while char_index < len(row):
            char = row[char_index]
            if char == self._delimiter:
                columns.append(TableValue(currentword, first_char_index, char_index))
                currentword = ''
                first_char_index = char_index + 1
            else:
                currentword += char
            char_index += 1

        columns.append(TableValue(currentword, first_char_index, char_index))
        return columns


#-----------------------------------------------------------------------------------
class TableCommand(sublime_plugin.TextCommand):
    ''' Common table command stuff. '''

    def __init__(self, view):
        self.view = view
        self.region = self.get_table_region()
        self.column_index = -1

        if self.region is not None:
            text = self.view.substr(self.region)
            self.matrix = TableMatrix(text)  # create matrix from table text

    def start(self):
         sc.slog(sc.CAT_DBG, f'{self}')

    def finish(self, edit):
        if self.region is not None:
            output = self.matrix.format()  # render justified
            self.view.replace(edit, self.region, output)

    def is_visible(self):
        return is_table(self.view, self.view.sel()[-1].b)

    def get_table_region(self):
        ''' Get the region for the current selected table. None if it's not a table. '''

        region = None
        v = self.view

        sel_row = v.rowcol(v.sel()[0].a)[0]
        start_row = sel_row
        end_row = -1
        current_row = start_row

        # Find the first row.
        done = False
        while not done:
            point = v.text_point(current_row, 0)
            if is_table(v, point):
                start_row = current_row
                current_row -= 1
            else:
                done = True

        # Find the last row.
        current_row = sel_row
        done = False
        while not done:
            point = v.text_point(current_row, 0)
            if is_table(v, point):
                end_row = current_row
                current_row += 1
            else:
                done = True

        if start_row != -1 and end_row != -1:
            start_point = v.text_point(start_row, 0)
            end_point = v.full_line(v.text_point(end_row, 0)).b
            region = sublime.Region(start_point, end_point)

        return region

    def select_column(self, column_index):
        ''' View select specific column. '''
        v = self.view
        v.sel().clear()

        for row_index, row in enumerate(self.rows):
            if column_index < len(row):
                value = row[column_index]
                a = v.text_point(row_index, value.first_char_index)
                b = v.text_point(row_index, value.last_char_index)
                region = sublime.Region(a, b)
                v.sel().add(region)


#-----------------------------------------------------------------------------------
class TableFitCommand(TableCommand):
    
    def __init__(self, view):
        super().__init__(view)

    def run(self, edit):
        super().start()
        # no work
        super().finish(edit)


#-----------------------------------------------------------------------------------
class TableSortByColCommand(TableCommand):

    def __init__(self, view):
        super().__init__(view)

    def run(self, edit, asc):
        super().start()
        # do work
        self.matrix.sort_by_column(self.column_index, asc)
        super().finish(edit)
        

#-----------------------------------------------------------------------------------
class TableInsertColCommand(TableCommand):

    def __init__(self, view):
        super().__init__(view)

    def run(self, edit):
        super().start()
        # do work
        self.matrix.insert_column(self.column_index)
        super().finish(edit)


#-----------------------------------------------------------------------------------
class TableDeleteColCommand(TableCommand):

    def __init__(self, view):
        super().__init__(view)

    def run(self, edit):
        super().start()
        # do work
        self.matrix.delete_column(self.column_index)
        super().finish(edit)


#-----------------------------------------------------------------------------------
class TableSelectColCommand(TableCommand):

    def __init__(self, view):
        super().__init__(view)

    def run(self, edit):
        super().start()
        # do work
        selection = self.view.sel()[0]
        row, col = self.view.rowcol(selection.begin())
        column_index = self.matrix.get_column_index_from_pos(row, col)  # get current column
        self.select_column(column_index)
        super().finish(edit)


#-----------------------------------------------------------------------------------
def is_table(view, point):
    ''' True if the point is in a table. '''
    scope = view.scope_name(point).rstrip()
    scopes = scope.split()
    is_hdr = "meta.table.header" in scopes
    is_table = "meta.table" in scopes
    return is_table or is_hdr
