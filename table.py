# The guts of this are blatantly stolen from https://github.com/wadetb/Sublime-Text-Advanced-CSV.
# Basically the raw csv manipulation without formatting, expressions, quoting, optional header, compact, ...
# Source license is MIT so all is good. I invite others to blatantly steal this.
# 
# Originally written by Eric Martel (emartel@gmail.com / www.ericmartel.com)
# Improved by Wade Brainerd (wadetb@gmail.com / www.wadeb.com)

import sublime
import sublime_plugin


#-----------------------------------------------------------------------------------
class TableValue:
    def __init__(self, text, first_char_index=0, last_char_index=0):
        self.text = text
        self.first_char_index = first_char_index
        self.last_char_index = last_char_index

    def as_float(self):
        try:
            return True, float(self.text)
        except ValueError:
            return False, None

    def compare(self, other):
        a_is_float, a_float = self.as_float()
        b_is_float, b_float = other.as_float()

        if a_is_float and b_is_float:
            return a_float - b_float

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
    def __init__(self, view):
        self.rows = []
        self.num_columns = 0
        self.valid = False
        self.view = view
        self.delimiter = '|'

    @staticmethod
    def from_view(view):
        ''' Factory function - from a view. '''
        matrix = TableMatrix(view)
        text = view.substr(sublime.Region(0, view.size()))

        for line in text.split("\n"):
            row = matrix.parse_row(line)
            matrix.rows.append(row)
        # matrix.finalize()
        if len(self.rows) > 0:
            self.num_columns = 0
            for row in self.rows:
                if len(row) > self.num_columns:
                    self.num_columns = len(row)
            self.valid = True

        return matrix

    def sort_by_column(self, column_index, asc):

        class Compare:
            def __init__(self, row):
                self.value = row[column_index] if len(self.rows) > 0 else TableValue('') 

            def __lt__(self, other):
                return self.value < other.value

            def __eq__(self, other):
                return self.value == other.value

        # Assume header.
        self.rows[1:] = sorted(self.rows[1:], key=lambda row: Compare(row), reverse=not asc)

    def insert_column(self, column_index):
        for row in self.rows:
            if column_index <= len(row):
                row.insert(column_index, TableValue(''))

    def delete_column(self, column_index):
        for row in self.rows:
            if column_index < len(row):
                row.pop(column_index)

    def select_column(self, column_index, view):
        view.sel().clear()

        for row_index, row in enumerate(self.rows):
            if column_index < len(row):
                value = row[column_index]
                a = view.text_point(row_index, value.first_char_index)
                b = view.text_point(row_index, value.last_char_index)
                region = sublime.Region(a, b)
                view.sel().add(region)

    def save_selection(self, view):
        saved_selection = []

        for region in view.sel():
            a_row, a_col = view.rowcol(region.a)
            b_row, b_col = view.rowcol(region.b)
            rowcol_region = (a_row, a_col, b_row, b_col)
            saved_selection.append(rowcol_region)

        return saved_selection

    def restore_selection(self, view, saved_selection):
        view.sel().clear()

        for rowcol_region in saved_selection:
            a = view.text_point(rowcol_region[0], rowcol_region[1])
            b = view.text_point(rowcol_region[2], rowcol_region[3])
            region = sublime.Region(a, b)
            view.sel().add(region)

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

        for row_index, row in enumerate(self.rows):
            row_text = ''

            for column_index, value in enumerate(row):
                row_text += value.text
                if column_index < len(row) - 1:
                    row_text += self.delimiter
            output += row_text

            if row_index < len(self.rows) - 1:
                output += '\n'

        return output

    def format_expanded(self):
        self.measure_columns()

        output = ''

        for row_index, row in enumerate(self.rows):
            row_text = ''

            for column_index, value in enumerate(row):
                column_width = self.column_widths[column_index]
                text = value.text.ljust(column_width)
                row_text += text
                if column_index < len(row) - 1:
                    row_text += self.delimiter
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
            if char == self.delimiter:
                columns.append(TableValue(currentword, first_char_index, char_index))
                currentword = ''
                first_char_index = char_index + 1
            else:
                currentword += char
            char_index += 1

        columns.append(TableValue(currentword, first_char_index, char_index))
        return columns

    def get_column_index_from_cursor(self, view):
        selection = view.sel()[0]
        row_index, col_index = view.rowcol(selection.begin())

        if row_index < len(self.rows):
            row = self.rows[row_index]
            for column_index, value in enumerate(row):
                if value.first_char_index > col_index:
                    return column_index - 1
            return len(row) - 1
        else:
            return 0


#-----------------------------------------------------------------------------------
class TableSortByColCommand(sublime_plugin.TextCommand):

    def run(self, edit, asc):
        matrix = TableMatrix.from_view(self.view)
        saved_selection = matrix.save_selection(self.view)

        column_index = matrix.get_column_index_from_cursor(self.view)
        matrix.sort_by_column(column_index, asc)
        output = matrix.format()

        self.view.replace(edit, sublime.Region(0, self.view.size()), output)
        TableMatrix.restore_selection(self.view, saved_selection)

    def is_visible(self):
        scope = self.view.scope_name(self.view.sel()[-1].b).rstrip()
        scopes = scope.split()

        hdr = "meta.table.header" in scopes
        table = "meta.table" in scopes
        return table
        

#-----------------------------------------------------------------------------------
class TableInsertColCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        matrix = TableMatrix.from_view(self.view)
        saved_selection = matrix.save_selection(self.view)
        column_index = matrix.get_column_index_from_cursor(self.view)
        matrix.insert_column(column_index)
        output = matrix.format()
        self.view.replace(edit, sublime.Region(0, self.view.size()), output)
        matrix.restore_selection(self.view, saved_selection)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class TableDeleteColCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        matrix = TableMatrix.from_view(self.view)
        saved_selection = matrix.save_selection(self.view)
        column_index = matrix.get_column_index_from_cursor(self.view)
        matrix.delete_column(column_index)
        output = matrix.format()
        self.view.replace(edit, sublime.Region(0, self.view.size()), output)
        matrix.restore_selection(self.view, saved_selection)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class TableSelectColCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        matrix = TableMatrix.from_view(self.view)
        column_index = matrix.get_column_index_from_cursor(self.view)
        matrix.select_column(column_index, self.view)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class TableFitCommand(sublime_plugin.TextCommand):
    
    def run(self, edit):
        matrix = TableMatrix.from_view(self.view)
        saved_selection = matrix.save_selection(self.view)
        output = matrix.format_expanded()
        self.view.replace(edit, sublime.Region(0, self.view.size()), output)
        matrix.restore_selection(self.view, saved_selection)

    def is_visible(self):
        return True
