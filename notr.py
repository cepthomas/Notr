import os
import platform
import re
import glob
import collections
import random
import subprocess
import sublime
import sublime_plugin
from . import sbot_common as sc


NOTR_SETTINGS_FILE = "Notr.sublime-settings"

# Known file types.
IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']

# TODO Put MRU targets at top of selector.
# TODO Add non-ntr files to index.


#--------------------------- Types -------------------------------------------------

# One target of section or file/uri.
# type: section, uri, image, path
# name: section title
# resource: what type points to
# level: for section only
# tags[] tags for targets
# srcfile: ntr file path
# line: ntr file line
Target = collections.namedtuple('Target', 'type, name, resource, level, tags, srcfile, line')

# A reference to a Target.
# name: target name
# srcfile: ntr file path
# line: ntr file line
Ref = collections.namedtuple('Ref', 'name, srcfile, line')

#---------------------------- Globals -----------------------------------------------

# All Targets found in all ntr files.
_targets = []

# All Refs found in all ntr files.
_refs = []

# All tags found in all ntr files. Key is tag text, value is count.
_tags = {}

# All processed ntr files, fully qualified paths.
_ntr_files = []

# Parse errors to report to user.
_parse_errors = []


#-----------------------------------------------------------------------------------
def plugin_loaded():
    pass


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    pass


#-----------------------------------------------------------------------------------
class NotrEvent(sublime_plugin.EventListener):
    ''' Process view events. '''

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Initialize everything. '''

        # Open and process notr files.
        _process_notr_files(views[0].window())

        # Views are all valid now so init them.
        for view in views:
            self._init_fixed_hl(view)

    def on_load(self, view):
        ''' Load a new file. View is valid so init it. '''
        self._init_fixed_hl(view)

    def on_post_save(self, view):
        ''' Called after a ntr view has been saved so reload all ntr files. Seems a bit brute force, how else? '''
        if view.syntax().name == 'Notr':
            _process_notr_files(view.window())

    def _init_fixed_hl(self, view):
        ''' Add any highlights. '''
        if view.is_scratch() is False and view.file_name() is not None and view.syntax().name == 'Notr':
            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            fixed_hl = settings.get('fixed_hl')
            whole_word = settings.get('fixed_hl_whole_word')

            if fixed_hl is not None:
                hl_info = sc.get_highlight_info('fixed')
                for hl_index in range(len(fixed_hl)):
                    hl = hl_info[hl_index]
                    # Clean first.
                    view.erase_regions(hl.region_name)

                    # New ones.
                    hl_regions = []

                    # Colorize one token.
                    for token in fixed_hl[hl_index]:
                        escaped = re.escape(token)
                        if whole_word:  # and escaped[0].isalnum():
                            escaped = r'\b%s\b' % escaped
                        regs = view.find_all(escaped) if whole_word else view.find_all(token, sublime.LITERAL)
                        hl_regions.extend(regs)

                    if len(hl_regions) > 0:
                        view.add_regions(key=hl.region_name, regions=hl_regions, scope=hl.scope_name,
                                         flags=sublime.RegionFlags.DRAW_STIPPLED_UNDERLINE)


#-----------------------------------------------------------------------------------
class NotrGotoTargetCommand(sublime_plugin.TextCommand):
    ''' List all the tag(s) and/or target(s) for user selection then open corresponding file. '''

    # Prepared lists for quick panel.
    _sorted_tags = []
    _sorted_targets = []

    def run(self, edit, filter_by_tag):
        self._sorted_tags.clear()
        self._sorted_targets.clear()

        if filter_by_tag:
            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            sort_tags_alpha = settings.get('sort_tags_alpha')
            panel_items = []

            if sort_tags_alpha:
                self._sorted_tags = sorted(_tags)
            else:  # Sort by frequency.
                self._sorted_tags = [x[0] for x in sorted(_tags.items(), key=lambda x:x[1], reverse=True)]
            for tag in self._sorted_tags:
                panel_items.append(sublime.QuickPanelItem(trigger=tag, annotation=f"qty:{_tags[tag]}", kind=sublime.KIND_AMBIGUOUS))
            self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_tag)
        else:
            self.show_targets(_targets)

    def on_sel_tag(self, *args, **kwargs):
        sel = args[0]

        if sel >= 0:
            # Make a selector with sorted target names, current file's first.
            sel_tag = self._sorted_tags[sel]

            # Hide current quick panel.
            self.view.window().run_command("hide_overlay")

            # Filter per tag selection.
            filtered_targets = []
            for target in _targets:
                if sel_tag in target.tags:
                    filtered_targets.append(target)

            if len(filtered_targets) > 0:
                self.show_targets(filtered_targets)
            else:
                sublime.status_message('No targets with that tag')

    def show_targets(self, targets):
        ''' Present target options to user. '''

        main_targets = []
        other_targets = []
        panel_items = []
        current_file = self.view.file_name()

        for target in targets:
            if current_file is not None and os.path.samefile(target.srcfile, current_file):
                main_targets.append(target)
            else:
                other_targets.append(target)

        # Sort them all.
        # main_targets = sorted(main_targets)
        # other_targets = sorted(other_targets)
        main_targets.extend(other_targets)

        for target in main_targets:
            panel_items.append(sublime.QuickPanelItem(trigger=f'{target.name}', kind=sublime.KIND_AMBIGUOUS))
        # Combine the two.
        self._sorted_targets = main_targets
        self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_target)

    def on_sel_target(self, *args, **kwargs):
        sel = args[0]

        if sel >= 0:
            # Locate the target record.
            target = self._sorted_targets[sel]
            if target.type == "section":
                # Open the notr file and position it.
                sc.wait_load_file(self.view.window(), target.srcfile, target.line)
                valid = True
            else:
                valid = sc.open_file(target.resource)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrFollowRefCommand(sublime_plugin.TextCommand):
    ''' Open target from selected ref. '''

    refs = []

    def run(self, edit):
        valid = True  # default
        # Determine if user has selected a specific ref to follow, otherwise show the list of all.

        tref = _get_selection_for_scope(self.view, 'markup.link.refname.notr')

        if tref is not None:  # explicit ref to selected element. do immediate.
            # Get the corresponding target spec. Could be a dict?
            for target in _targets:
                valid = False
                if target.name == tref:
                    if target.type == "section":
                        # Open the notr file and position it.
                        sc.wait_load_file(self.view.window(), target.srcfile, target.line)
                        valid = True
                    else:
                        valid = sc.open_file(target.resource)
                    break

            if not valid:
                sc.slog(sc.CAT_ERR, f'Invalid reference: {self.view.file_name()} :{tref}')

        else:
            # Show a quickpanel of all target names.
            self.refs = _get_valid_refs(True)  # sorted
            panel_items = []
            for sec_name in self.refs:
                panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
            self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_ref)

    def on_sel_ref(self, *args, **kwargs):
        sel = args[0]
        if sel >= 0:
            tref = self.refs[sel]            
            for target in _targets:
                valid = False
                if target.name == tref:
                    if target.type == "section":
                        # Open the notr file and position it.
                        sc.wait_load_file(self.view.window(), target.srcfile, target.line)
                        valid = True
                    else:
                        valid = sc.open_file(target.resource)
                    break

    # def is_visible(self):
    #     return _get_selection_for_scope(self.view, 'markup.link.refname.notr') is not None


#-----------------------------------------------------------------------------------
class NotrInsertRefCommand(sublime_plugin.TextCommand):
    ''' Insert ref from list of known refs. '''
    refs = []

    def run(self, edit):
        self.refs = _get_valid_refs(True)  # sorted
        panel_items = []
        for sec_name in self.refs:
            panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
        self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_ref)

    def on_sel_ref(self, *args, **kwargs):
        sel = args[0]
        if sel >= 0:
            s = f'[*{self.refs[sel]}]'
            self.view.run_command("insert", {"characters": f'{s}'})  # Insert in created view
        else:
            # Stick them in the clipboard.
            sublime.set_clipboard('\n'.join(self.refs))

    def is_visible(self):
        return self.view.syntax() is not None and self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrInsertHruleCommand(sublime_plugin.TextCommand):
    ''' Insert visuals. '''

    def run(self, edit, fill_str, reps):
        v = self.view

        # Start of current line.
        caret = sc.get_single_caret(v)
        lst = v.line(caret)

        s = fill_str * reps + '\n'
        v.insert(edit, lst.a, s)

    def is_visible(self):
        v = self.view
        return v.syntax() is not None and v.syntax().name == 'Notr' and sc.get_single_caret(v) is not None


#-----------------------------------------------------------------------------------
class NotrInsertTargetFromClipCommand(sublime_plugin.TextCommand):
    ''' Insert target from clipboard. Assumes user clipped appropriate string. '''

    def run(self, edit):
        random.seed()
        s = f'[EDITME{random.randrange(10000)}]({sublime.get_clipboard()})'
        caret = sc.get_single_caret(self.view)
        self.view.insert(edit, caret, s)

    def is_visible(self):
        v = self.view
        return v.syntax() is not None and \
            v.syntax().name == 'Notr' and \
            sc.get_single_caret(v) is not None and \
            sublime.get_clipboard() != ''


#-----------------------------------------------------------------------------------
class NotrPublishCommand(sublime_plugin.WindowCommand):
    ''' Publish notes somewhere... '''

    def run(self):
        # Render notr files for android target.
        # self.window.active_view().run_command('sbot_render_to_html', {'font_face':'monospace', 'font_size':'1.2em' } )  
        pass

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrReloadCommand(sublime_plugin.WindowCommand):
    ''' Reload after editing. '''

    def run(self):
        # Open and process notr files.
        _process_notr_files(self.window)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrDumpCommand(sublime_plugin.WindowCommand):
    ''' Diagnostic. '''

    def run(self):
        text = []

        def do_one(name, coll):
            text.append(f'\n========== {name} ==========')
            text.extend([str(x) for x in coll])

        do_one('targets', _targets)
        do_one('refs', _refs)
        do_one('tags', _tags)  # text.append(f'{x}:{_tags[x]}')
        do_one('ntr_files', _ntr_files)
        if len(_parse_errors) > 0:
            do_one('parse_errors', _parse_errors)

        sc.create_new_view(self.window, '\n'.join(text))

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
def _user_error(path, line, msg):
    ''' Error in user edited file. '''
    _parse_errors.append(f'{path}({line}): {msg}')


#-----------------------------------------------------------------------------------
def _process_notr_files(window):
    ''' Get all ntr files and grab their goodies. '''

    _ntr_files.clear()
    _targets.clear()
    _refs.clear()
    _tags.clear()
    _parse_errors.clear()

    # Open and process all notr files.
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)

    # Index first.
    notr_index = settings.get('notr_index')
    if notr_index is not None:
        index_path = sc.expand_vars(notr_index)
        if index_path is not None and os.path.exists(index_path):
            _ntr_files.append(index_path)
        else:
            _user_error(NOTR_SETTINGS_FILE, -1, f'Invalid path in settings {notr_index}')

    # Paths.
    notr_paths = settings.get('notr_paths')
    for npath in notr_paths:
        expath = sc.expand_vars(npath)
        if expath is not None and os.path.exists(expath):
            for nfile in glob.glob(os.path.join(expath, '*.ntr')):
                if index_path is None or not os.path.samefile(nfile, index_path):  # don't do index twice
                    _ntr_files.append(nfile)
        else:
            _user_error(NOTR_SETTINGS_FILE, -1, f'Invalid path in settings {npath}')

    # Process the files. Targets are ordered by sections then files/uris.
    s = []
    l = []
    for nfile in _ntr_files:
        fparts = _process_notr_file(nfile)
        if fparts is not None:
            s.extend(fparts[0])
            l.extend(fparts[1])
            _refs.extend(fparts[2])
    _targets.extend(s)
    _targets.extend(l)

    # Check all user refs are valid.
    valid_refs = _get_valid_refs(False)  # unsorted
    for ref in _refs:
        if ref.name not in valid_refs:
            _user_error(ref.srcfile, ref.line, f'Invalid ref name:{ref.name}')

    if len(_parse_errors) > 0:
        _parse_errors.insert(0, "Errors in your configuration:")
        sc.create_new_view(window, '\n'.join(_parse_errors))


#-----------------------------------------------------------------------------------
def _process_notr_file(ntr_fn):
    ''' Regex and process sections and links. This collects the text and checks syntax.
    Validity will be checked when all files processed.
    Returns (sections, links,refs)
    '''

    sections = []
    links = []
    refs = []
    no_index = False

    try:
        with open(ntr_fn, 'r', encoding='utf-8') as file:
            lines = file.read().splitlines()
            line_num = 1

            # Get the things of interest defined in the file. Grep escape these .^$*+?()[{\|  syntax uses X?!*
            re_directives = re.compile(r'^:(.*)')
            # re_directives = re.compile(r'^\$(.*)')
            re_links = re.compile(r'\[(.*)\]\((.*)\) *(?:\[(.*)\])?')
            # re_links = re.compile(r'\[([^:]*): *([^\]]*)\]')
            re_refs = re.compile(r'\[\* *([^\]]*)\]')
            re_sections = re.compile(r'^(#+ +[^\[]+) *(?:\[(.*)\])?')
            # re_sections = re.compile(r'^(#+) +([^\[]+) *(?:\[(.*)\])?')

            for line in lines:

                ### Directives, aliases.
                # :NOTES_PATH=some/where/notes
                # :NO_INDEX
                matches = re_directives.findall(line)
                for m in matches:
                    handled = False
                    parts = m.strip().split('=')
                    if len(parts) == 1:
                        directive = parts[0].strip()
                        if directive == 'NO_INDEX':
                            no_index = True
                            handled = True
                    elif len(parts) == 2:
                        alias = parts[0].strip()
                        value = parts[1].strip()
                        os.environ[alias] = value
                        handled = True  # so far

                    if not handled:
                        _user_error(ntr_fn, line_num, 'Invalid directive')

                ### Links - also checks validity.
                # [yer news](https://nytimes.com)
                # [some felix]($NOTES_PATH/felix9.jpg)
                matches = re_links.findall(line)
                for m in matches:
                    if len(m) >= 2:
                        name = m[0].strip()
                        res = sc.expand_vars(m[1].strip())
                        if res is None:
                            # Bad env var.
                            _user_error(ntr_fn, line_num, f'Bad env var: {m[1]}')
                        else:
                            ttype = None
                            _, ext = os.path.splitext(res)

                            if ext in IMAGE_TYPES:
                                ttype = "image"
                            elif res.startswith('http'):
                                ttype = "uri"
                            elif os.path.exists(res):
                                ttype = "path"
                            else:
                                _user_error(ntr_fn, line_num, f'Invalid target resource: {res}')

                            if ttype is not None:
                                # Tags?
                                tags = []
                                if len(m) >= 2:
                                    tags = m[2].strip().split()
                                links.append(Target(ttype, name, res, 0, tags, ntr_fn, line_num))
                                # Update global tags.
                                for tag in tags:
                                    _tags[tag] = _tags[tag] + 1 if tag in _tags else 1
                    else:
                        _user_error(ntr_fn, line_num, 'Invalid syntax')

                ### Refs - will be validated at end.
                # [*some felix]
                # [*yer news]
                # [*ST executable dir]
                # [* #section no tags].
                # [*page2#P2 section 2]
                matches = re_refs.findall(line)
                for m in matches:
                    name = m.strip()
                    # If it's local section insert the froot.
                    if name.startswith('#'):
                        froot = _get_froot(ntr_fn)
                        name = froot + name
                    refs.append(Ref(name, ntr_fn, line_num))

                ### Sections
                # # Some name[tag1 tag2]
                matches = re_sections.findall(line)
                for m in matches:
                    valid = True
                    if len(m) == 2:
                        content = m[0].strip().split(None, 1)
                        if len(content) == 2:
                            hashes = content[0].strip()
                            name = f'{_get_froot(ntr_fn)}#{content[1].strip()}'
                        else:
                            valid = False

                        if valid:
                            tags = m[1].strip().split()
                    else:
                        valid = False

                    if valid:
                        sections.append(Target("section", name, "", len(hashes), tags, ntr_fn, line_num))
                        # Update global tags.
                        for tag in tags:
                            _tags[tag] = _tags[tag] + 1 if tag in _tags else 1
                    else:
                        _user_error(ntr_fn, line_num, 'Invalid syntax')

                line_num += 1

    except Exception as e:
        sc.slog(sc.CAT_ERR, f'Error processing {ntr_fn}: {e}')
        raise

    return None if no_index else (sections, links,refs)


#-----------------------------------------------------------------------------------
def _get_valid_refs(sort):
    ''' Get all valid target for generating refs. '''

    # All valid ref targets.
    ref_targets = {}

    for target in _targets:
        tname = target.name
        if tname not in ref_targets:
            ref_targets[tname] = tname  # f'{target.srcfile}({target.line})'
        else:
            _user_error(target.srcfile, target.line, f'Duplicate target name:{target.name} see:{ref_targets[tname]}')

    return sorted(ref_targets) if sort else ref_targets


#-----------------------------------------------------------------------------------
def _get_selection_for_scope(view, scope):
    ''' If the current region includes the scope return it otherwise None. '''

    sel_text = None
    caret = sc.get_single_caret(view)
    if caret is not None:
        scopes = view.scope_name(caret).rstrip().split()
        if scope in scopes:
            reg = view.expand_to_scope(caret, scope)
            if reg is not None:
                sel_text = view.substr(reg).strip()

    return sel_text


#-----------------------------------------------------------------------------------
def _get_froot(fn):
    return os.path.basename(os.path.splitext(fn)[0])
