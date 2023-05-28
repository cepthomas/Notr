import sublime
import sublime_plugin

# From C:\Dev\Notr\py\Default.fold.py

#   { "keys": ["ctrl+shift+["], "command": "fold" },
#   { "keys": ["ctrl+shift+]"], "command": "unfold" },
#   { "keys": ["ctrl+k", "ctrl+1"], "command": "fold_by_level", "args": {"level": 1} },
#   { "keys": ["ctrl+k", "ctrl+2"], "command": "fold_by_level", "args": {"level": 2} },
#   { "keys": ["ctrl+k", "ctrl+3"], "command": "fold_by_level", "args": {"level": 3} },
#   { "keys": ["ctrl+k", "ctrl+4"], "command": "fold_by_level", "args": {"level": 4} },
#   { "keys": ["ctrl+k", "ctrl+5"], "command": "fold_by_level", "args": {"level": 5} },
#   { "keys": ["ctrl+k", "ctrl+6"], "command": "fold_by_level", "args": {"level": 6} },
#   { "keys": ["ctrl+k", "ctrl+7"], "command": "fold_by_level", "args": {"level": 7} },
#   { "keys": ["ctrl+k", "ctrl+8"], "command": "fold_by_level", "args": {"level": 8} },
#   { "keys": ["ctrl+k", "ctrl+9"], "command": "fold_by_level", "args": {"level": 9} },
#   { "keys": ["ctrl+k", "ctrl+0"], "command": "unfold_all" },
#   { "keys": ["ctrl+k", "ctrl+j"], "command": "unfold_all" },
#   { "keys": ["ctrl+k", "ctrl+t"], "command": "fold_tag_attributes" },

# API View:
#   is_folded(Region) Returns Whether the provided Region is folded.
#   folded_regions() Returns The list of folded regions.
# 
#   fold(list[Region]) Returns  False if the regions were already folded.
#     Fold the provided Region (s).
# 
#   unfold(list[Region]) Returns  The unfolded regions.
#     Unfold all text in the provided Region (s).


def fold_region_from_indent(view, r):
    if view.substr(r.b - 1) != '\n':
        return sublime.Region(r.a - 1, r.b)
    else:
        return sublime.Region(r.a - 1, r.b - 1)


class FoldUnfoldCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        new_sel = []
        for s in self.view.sel():
            r = s
            empty_region = r.empty()
            if empty_region:
                r = sublime.Region(r.a - 1, r.a + 1)

            unfolded = self.view.unfold(r)
            if len(unfolded) == 0:
                self.view.fold(s)
            elif empty_region:
                for r in unfolded:
                    new_sel.append(r)

        if len(new_sel) > 0:
            self.view.sel().clear()
            for r in new_sel:
                self.view.sel().add(r)


class FoldCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        new_sel = []
        for s in self.view.sel():
            if s.empty():
                r = self.view.indented_region(s.a)
                if not r.empty():
                    r = fold_region_from_indent(self.view, r)
                    self.view.fold(r)
                    new_sel.append(r)
                else:
                    new_sel.append(s)
            else:
                if self.view.fold(s):
                    new_sel.append(s)
                else:
                    r = self.view.indented_region(s.a)
                    if not r.empty():
                        r = fold_region_from_indent(self.view, r)
                        self.view.fold(r)
                        new_sel.append(r)
                    else:
                        new_sel.append(s)

        self.view.sel().clear()
        for r in new_sel:
            self.view.sel().add(r)


class FoldAllCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        folds = []
        tp = 0
        size = self.view.size()
        while tp < size:
            s = self.view.indented_region(tp)
            if not s.empty():
                r = fold_region_from_indent(self.view, s)
                folds.append(r)
                tp = s.b
            else:
                tp = self.view.full_line(tp).b

        self.view.fold(folds)
        self.view.show(self.view.sel())

        sublime.status_message("Folded " + str(len(folds)) + " regions")


class FoldByLevelCommand(sublime_plugin.TextCommand):
    def run(self, edit, level):
        level = int(level)
        folds = []
        tp = 0
        size = self.view.size()
        while tp < size:
            if self.view.indentation_level(tp) == level:
                if len(self.view.substr(self.view.full_line(tp)).strip()) < 1:
                    tp = self.view.full_line(tp).b
                    continue
                s = self.view.indented_region(tp)
                if not s.empty():
                    r = fold_region_from_indent(self.view, s)
                    folds.append(r)
                    tp = s.b
                    continue

            tp = self.view.full_line(tp).b

        self.view.fold(folds)
        self.view.show(self.view.sel())

        sublime.status_message("Folded " + str(len(folds)) + " regions")


class UnfoldCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        new_sel = []
        for s in self.view.sel():
            unfold = s
            if s.empty():
                unfold = sublime.Region(s.a - 1, s.a + 1)

            unfolded = self.view.unfold(unfold)
            if len(unfolded) == 0 and s.empty():
                unfolded = self.view.unfold(self.view.full_line(s.b))

            if len(unfolded) == 0:
                new_sel.append(s)
            else:
                for r in unfolded:
                    new_sel.append(r)

        if len(new_sel) > 0:
            self.view.sel().clear()
            for r in new_sel:
                self.view.sel().add(r)


class UnfoldAllCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.unfold(sublime.Region(0, self.view.size()))
        self.view.show(self.view.sel())
