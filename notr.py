import sys
import os
import re
import glob
import random
import json
import pathlib
import traceback
import shutil
import subprocess
import time


from dataclasses import dataclass, field
import sublime
import sublime_plugin
from . import sbot_common as sc


NOTR_SETTINGS_FILE = "Notr.sublime-settings"
NOTR_STORAGE_FILE = "notr.store"

# Known file types.
IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']


#--------------------------- Types -------------------------------------------------

# One target: section or file/uri.
@dataclass(order=True)
class Target:
    sort_index: str = field(init=False)
    name: str      # section title or description
    ttype: str     # 'section', 'uri', 'image', 'path' - maybe useful to discriminate file and dir?
    category: str  # 'sticky', 'mru', 'none'
    level: int     # for section only
    tags: []       # tags for targets
    resource: str  # what ttype points to
    file: str      # .ntr file path
    line: int      # .ntr file line

    def __post_init__(self):
        self.sort_index = self.name

# A reference to a Target.
@dataclass(order=True)
class Ref:
    sort_index: str = field(init=False)
    name: str  # "target#name"
    file: str  # .ntr file path
    line: int  # .ntr file line

    def __post_init__(self):
        self.sort_index = self.name


#---------------------------- Data -----------------------------------------------

# Current project file (*.nproj) contents.
_current_project = None

# The whole store file (notr.store) contents.
_store = None

# Persisted mru.
_current_mru = None

# All Targets found in all ntr files.
_targets = []

# All Refs found in all ntr files.
_refs = []

# Parse errors to report to user. Tuples of (path, line, msg)
_parse_errors = []


#-----------------------------------------------------------------------------------
def plugin_loaded():
    '''Called per plugin instance.'''
    sc.info(f'plugin_loaded() {__package__}')


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    '''Ditto.'''
    pass


#-----------------------------------------------------------------------------------
#-------------------------- EventListener ------------------------------------------
#-----------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
class NotrEvent(sublime_plugin.EventListener):
    ''' Process view events. '''

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Initialize everything. '''
        global _store

        settings = sublime.load_settings(NOTR_SETTINGS_FILE)

        # Check user projects.
        valid_projects = []
        for p in settings.get('projects'):
            if not os.path.isfile(sc.expand_vars(p)):
                sc.info(f'Invalid project file {p} - edit your settings')
            else:
                valid_projects.append(sc.expand_vars(p))

        # Get persisted store info.
        store_fn = sc.get_store_fn(NOTR_STORAGE_FILE)
        _store = None
        if os.path.isfile(store_fn):
            try:
                with open(store_fn, 'r') as fp:
                    s = fp.read()
                    _store = json.loads(s)
            except Exception as e:
                sc.error(f'Error processing {store_fn}: {e}', e.__traceback__)

        if _store is None:  # Assume new file with default fields.
            _store = {}
            for p in valid_projects:
                _store[sc.expand_vars(p)] = {'active': {len(_store) == 0}, 'mru': []}

        # Remove dead/invalid projects. Determine project file. Ensure one only active.
        dead = []
        project_fn = None
        for path, v in _store.items():
            if not os.path.isfile(path) or path not in valid_projects:
                dead.append(path)
            elif not project_fn and v['active'] is True:
                project_fn = path
            else:
                v['active'] = False
        for p in dead:
            del _store[p]

        if project_fn is None and len(valid_projects) > 0:
            project_fn = valid_projects[0]

        if project_fn is not None:
            _open_project(project_fn)
            _process_notr_files(views[0].window())
            # Views are all valid now so init them.
            for view in views:
                self._init_fixed_hl(view)
        else:
            sc.warn(f'No valid projects in your settings - please edit')

    def on_load(self, view):
        ''' Loaded a new file. '''
        # View is valid so init it.
        self._init_fixed_hl(view)

    def on_pre_close(self, view):
        ''' Save anything. '''
        _save_store()

    def on_post_save(self, view):
        ''' Called after a ntr view has been saved so reload all ntr files. Seems a bit brute force, how else? '''
        if view.syntax().name == 'Notr':
            _process_notr_files(view.window())

    def _init_fixed_hl(self, view):
        ''' Add any highlights. '''
        if (_current_project is not None and
            view.is_scratch() is False and
            view.file_name() is not None and
            view.syntax() is not None and
            view.syntax().name == 'Notr'):
            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            whole_word = settings.get('fixed_hl_whole_word')
            fixed_hl = _current_project['fixed_hl']
            if fixed_hl is None:
                return

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
                    # print(escaped, len(regs))
                    hl_regions.extend(regs)

                if len(hl_regions) > 0:
                    view.add_regions(key=hl.region_name, regions=hl_regions, scope=hl.scope_name,
                                     flags=sublime.RegionFlags.DRAW_STIPPLED_UNDERLINE)


#-----------------------------------------------------------------------------------
#-------------------------- WindowCommands -----------------------------------------
#-----------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
class NotrOpenProjectCommand(sublime_plugin.WindowCommand):
    ''' User selects an existing project. '''
    panel_items = []

    def run(self):
        ''' Populate selector with user projects. '''
        self.panel_items.clear()
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)

        for path, v in _store.items():
            projnm = pathlib.Path(path).stem
            self.panel_items.append(sublime.QuickPanelItem(trigger=projnm, details=path, kind=sublime.KIND_AMBIGUOUS))
        self.window.show_quick_panel(self.panel_items, on_select=self.on_sel_project)

    def on_sel_project(self, *args, **kwargs):
        if len(args) > 0 and args[0] >= 0:
            _open_project(self.panel_items[args[0]].details)
            _process_notr_files(self.window)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrEditProjectCommand(sublime_plugin.WindowCommand):
    ''' Open the file in a new view for editing. TODO nice to reload after user finished edits. '''

    def run(self):
        # Open the file in a new view.
        vnew = None
        fn = _current_project['_fn']
        try:
            vnew = self.window.open_file(fn)
            vnew.assign_syntax('Packages/JSON/JSON.sublime-syntax')
        except Exception as e:
            sc.error(f'Failed to open {fn}: {e}', e.__traceback__)
            vnew = None

    def is_visible(self):
        return _store is not None and len(_store) > 0 and _current_project is not None


#-----------------------------------------------------------------------------------
class NotrReloadCommand(sublime_plugin.WindowCommand):
    ''' Reload after editing. '''

    def run(self):
        # Open and process notr files.
        _process_notr_files(self.window)

    def is_visible(self):
        return _current_project is not None


#-----------------------------------------------------------------------------------
class NotrDumpCommand(sublime_plugin.WindowCommand):
    ''' Diagnostic. '''

    def run(self):
        text = []

        def do_one(name, coll):
            text.append(f'\n========== {name} ==========')
            text.extend([str(x) for x in coll])

        if len(_parse_errors) > 0:
            text.append('\n========== !! errors below !! ==========')

        do_one('targets', _targets)
        do_one('refs', _refs)
        do_one('tags', _get_all_tags())
        do_one('ntr_files', _get_all_ntr_files())

        if len(_parse_errors) > 0:
            text.append('\n========== errors ==========')
            text.extend([f'{p[0]}({p[1]}): {p[2]}' for p in _parse_errors])

        sc.create_new_view(self.window, '\n'.join(text))

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrFindInFilesCommand(sublime_plugin.WindowCommand):
    ''' Search in the .ntr files. '''

    def run(self):
        ''' Assemble the search locations from users paths. Index directory also? '''
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
        paths = ["*.ntr", "-<open files>"]
        notr_paths = settings.get('notr_paths')
        for npath in notr_paths:
            expath = sc.expand_vars(npath)
            if expath is not None and os.path.exists(expath):
                paths.append(expath)

        # Show it so the user can enter the pattern.
        # https://github.com/SublimeText/PackageDev/blob/master/plugins/command_completions/builtin_commands_meta_data.yaml
        self.window.run_command("show_panel", {
                                "panel": "find_in_files", "where": ', '.join(paths), "case_sensitive": True, "pattern": '',
                                "whole_word": False, "preserve_case": True, "show_context": False, "use_buffer": True,
                                "replace": '', "regex": False})

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrPublishCommand(sublime_plugin.WindowCommand):
    ''' TODO A research project to publish the .ntr files somehow/somewhere. '''

    def run(self):
        onedrive_path = os.path.expandvars('$OneDrive')
        docs_path = os.path.join(onedrive_path, 'OneDriveDocuments')
        pub_path = os.path.join(onedrive_path, '_notr')
        notes_path = os.path.join(docs_path, 'notes')
        tech_path = os.path.join(docs_path, 'tech')
        sports_path = os.path.join(docs_path, 'sports')

        notes_to_pub = [
            'activities.ntr',
            # 'books.ntr',
            'food-places.ntr',
            # 'movies.ntr',
            'shop.ntr',
            'todo.ntr',
            # 'tv.ntr',
        ]

        # Gen the pub files.
        for p in notes_to_pub:
            src = os.path.join(notes_path, p)
            dest = os.path.join(pub_path, p.replace('.ntr', '.html'))
            # need to manage files in/out. Maybe use clipboard?
            # self.window.run_command("sbot_render_to_html", {"group": 0})
            time.sleep(0.5) # let st finish this first

    def is_visible(self):
        return False


#-----------------------------------------------------------------------------------
#-------------------------- TextCommands -------------------------------------------
#-----------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
class NotrGotoTargetCommand(sublime_plugin.TextCommand):
    ''' List all the tag(s) and/or target(s) for user selection then open corresponding file. '''

    # Prepared lists for quick panel.
    _tags = []

    def run(self, edit, filter_by_tag):
        # Determine if user has selected a specific ref or link to follow, otherwise show the list of all.
        valid = True  # default
        tref = _get_selection_for_scope(self.view, 'markup.link.refname.notr')
        tlink = _get_selection_for_scope(self.view, 'markup.underline.link.notr')
        if tlink is None:
            tlink = _get_selection_for_scope(self.view, 'markup.link.target.notr')

        # Explicit ref to selected element - do immediate.
        if tref is not None:
            # Get the corresponding target spec.
            for target in _targets:
                valid = False
                if target.name == tref:
                    if target.ttype == 'section':
                        # Open the notr file and position it.
                        sc.wait_load_file(self.view.window(), target.file, target.line)
                        valid = True
                    else:  # 'image', 'uri', 'path'
                        valid = sc.open_path(target.resource)
                    break

            if not valid:
                sc.warn(f'Invalid reference: {self.view.file_name()}: {tref}')

        # Explicit link. do immediate.
        elif tlink is not None:
            fn = sc.expand_vars(tlink)
            valid = sc.open_path(fn)
            if not valid:
                sc.warn(f'Invalid link: {tlink}')

        # Show a quickpanel of all target names.
        else:
            if filter_by_tag:
                self._tags = _get_all_tags()
                panel_items = []

                for tag in self._tags:
                    panel_items.append(sublime.QuickPanelItem(trigger=tag, kind=sublime.KIND_AMBIGUOUS))
                self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_tag)
            else:
                targets = _filter_order_targets(mru_first=True, current_file=self.view.file_name())
                self.show_targets(targets)

    def on_sel_tag(self, *args, **kwargs):
        if len(args) > 0 and args[0] >= 0:
            # Hide current quick panel.
            self.view.window().run_command("hide_overlay")

            # Make a selector with target names, current file's first.
            sel_tag = self._tags[args[0]]

            # Filter per tag selection.
            tag_targets = _filter_order_targets(sort=False, mru_first=True, tags=[sel_tag])
            if len(tag_targets) > 0:
                self.show_targets(tag_targets)
            else:
                sublime.status_message('No targets with that tag')

    def show_targets(self, targets):
        ''' Present target options to user. '''
        self._targets_to_select = targets
        panel_items = _build_selector(self._targets_to_select)
        self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_target)

    def on_sel_target(self, *args, **kwargs):
        if len(args) > 0 and args[0] >= 0:
            # Locate the target record.
            target = self._targets_to_select[args[0]]
            _update_mru(target.name)
            if target.ttype == 'section':
                # Open the notr file and position it.
                sc.wait_load_file(self.view.window(), target.file, target.line)
            else:  # 'image', 'uri', 'path'
                sc.open_path(target.resource)

    def is_visible(self):
        return True


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
        s = f'[]({sublime.get_clipboard()})'
        caret = sc.get_single_caret(self.view)
        self.view.insert(edit, caret, s)

    def is_visible(self):
        v = self.view
        return v.syntax() is not None and \
            v.syntax().name == 'Notr' and \
            sc.get_single_caret(v) is not None and \
            sublime.get_clipboard() != ''


#-----------------------------------------------------------------------------------
class NotrInsertRefCommand(sublime_plugin.TextCommand):
    ''' Insert ref from list of known refs. '''
    _targets_to_select = []

    def run(self, edit):
        # Show a quickpanel of all target names.
        self._targets_to_select = _filter_order_targets(sort=False, mru_first=True, current_file=self.view.file_name())
        panel_items = _build_selector(self._targets_to_select)
        self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_ref)

    def on_sel_ref(self, *args, **kwargs):
        if len(args) > 0 and args[0] >= 0:
            s = f'[*{self._targets_to_select[args[0]].name}]'
            self.view.run_command("insert", {"characters": f'{s}'})  # Insert in view

    def is_visible(self):
        return self.view.syntax() is not None and self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
#-------------------------- Private Functions --------------------------------------
#-----------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
def _save_store():
    ''' Save everything. '''
    store_fn = sc.get_store_fn(NOTR_STORAGE_FILE)
    with open(store_fn, 'w') as fp:
        json.dump(_store, fp, indent=4)


#-----------------------------------------------------------------------------------
def _open_project(project_fn):
    global _current_project, _current_mru

    try:
        expfn = sc.expand_vars(project_fn)
        with open(expfn, 'r') as fp:
            s = fp.read()
            proj = json.loads(s)

            # Check file integrity.
            if "notr_paths" not in proj or "notr_index" not in proj:
                # Broken file.
                sc.error(f'Invalid project file {expfn} - needs to be edited')
                return

            # Non-fatal patchups.
            if "fixed_hl" not in proj:
                proj["fixed_hl"] = []
            if 'sticky' not in proj:
                proj['sticky'] = []

            _current_project = proj
            _current_project['_fn'] = expfn  # for downstream

            # Reset flags first.
            for path, v in _store.items():
                v['active'] = False

            # Get dynamic stuff. Add if not included.
            if expfn not in _store:  # new, add
                _store[expfn] = {'active': True, 'mru': []}
            else:
                _store[expfn]['active'] = True
            _current_mru = _store[expfn]['mru']

            sc.info(f'Opened project file {project_fn}')

    except Exception as e:
        # Assume bad project file.
        sc.error(f'Error opening project file {project_fn}: {e}', e.__traceback__)


#-----------------------------------------------------------------------------------
def _process_notr_files(window):
    ''' Get all ntr files and grab their goodies. '''
    _targets.clear()
    _refs.clear()
    _parse_errors.clear()
    ntr_files = []

    if _current_project is None:
        return

    # Open and process all notr files.
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)

    # Index first.
    notr_index = _current_project['notr_index']
    if notr_index is not None:
        index_path = sc.expand_vars(notr_index)
        if index_path is not None and os.path.exists(index_path):
            ntr_files.append(index_path)
        else:
            _user_error(NOTR_SETTINGS_FILE, -1, f'Invalid path in settings {notr_index}')

    # Paths.
    notr_paths = _current_project['notr_paths']
    for npath in notr_paths:
        expath = sc.expand_vars(npath)
        if expath is not None and os.path.exists(expath):
            for nfile in glob.glob(os.path.join(expath, '*.ntr')):
                if index_path is None or not os.path.samefile(nfile, index_path):  # don't do index twice
                    ntr_files.append(nfile)
        else:
            _user_error(NOTR_SETTINGS_FILE, -1, f'Invalid path in settings {npath}')

    # Process the files. Targets are ordered by sections then files/uris.
    sections = []
    uris = []
    for nfile in ntr_files:
        fparts = _process_notr_file(nfile)
        if fparts is not None:
            sections.extend(fparts[0])
            uris.extend(fparts[1])
            _refs.extend(fparts[2])
    _targets.extend(sections)
    _targets.extend(uris)

    # Check all user refs are valid.
    valid_refs = []
    for target in _targets:
        if len(target.name) > 0:
            valid_refs.append(target.name)

    for ref in _refs:
        if ref.name not in valid_refs:
            _user_error(ref.file, ref.line, f'Invalid ref name:{ref.name}')

    # Do output if errors.
    if len(_parse_errors) > 0:
        output_view = None
        working_dir = ''
        use_panel = True  # prefs.get("show_panel_on_build", True)

        # Create output to panel or view. Don't call get_output_panel until the regexes are assigned.
        if use_panel:
            output_view = window.create_output_panel("exec")
        else:
            output_view = sc.create_new_view(window, '')

        # Enable result navigation.
        settings = output_view.settings()
        settings.set('result_file_regex', r'^([^\(]+)\(([0-9]+)\)(): (.*)$')
        settings.set('result_base_dir', working_dir)

        # Create a second time after assigning the above regex and settings.
        if use_panel:
            output_view = window.create_output_panel("exec")
            window.run_command('show_panel', {'panel': 'output.exec'})
        else:
            window.focus_view(output_view)

        # Fill with info.
        output_view.run_command('append', {'characters': "Notr file errors:\n"})
        for p in _parse_errors:
            output_view.run_command('append', {'characters': f'{p[0]}({p[1]}): {p[2]}\n', 'force': True, 'scroll_to_end': True})


#-----------------------------------------------------------------------------------
def _process_notr_file(ntr_fn):
    ''' Process one notr file. Regex and process sections and links.
    This collects the text and checks syntax. Validity will be checked when all files processed.
    Returns (sections, links, refs)
    '''

    sections = []
    links = []
    refs = []
    no_index = False
    line_num = -1

    try:
        with open(ntr_fn, 'r', encoding='utf-8') as file:  # need to explicitly set encoding because default windows is ascii
            lines = file.read().splitlines()
            line_num = 1

            # Get the things of interest defined in the file.
            re_directives = re.compile(r'^:(.*)')
            re_links = re.compile(r'\[(.*)\]\(([^\)]*)\)')
            re_refs = re.compile(r'\[\* *([^\]]*)\]')
            re_sections = re.compile(r'^(#+ +[^\[]+) *(?:\[(.*)\])?')

            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            section_marker_size = settings.get('section_marker_size')

            for line in lines:

                ### Directives/aliases.
                # :MY_PATH=some/where/my
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
                                ttype = 'image'
                            elif res.startswith('http'):
                                ttype = 'uri'
                            elif os.path.exists(res):
                                ttype = 'path'
                            else:
                                _user_error(ntr_fn, line_num, f'Invalid target resource: {res}')

                            if ttype is not None:
                                links.append(Target(name, ttype, '', 0, [], res, ntr_fn, line_num))
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
                        # print(content)

                        if len(content) == 2:
                            hashes = content[0].strip()
                            name = f'{_get_froot(ntr_fn)}{hashes}{content[1].strip()}'
                        else:
                            valid = False

                        if valid:
                            tags = m[1].strip().split()
                    else:
                        valid = False

                    if valid:
                        if len(hashes) <= section_marker_size:
                            sections.append(Target(name, 'section', '', len(hashes), tags, '', ntr_fn, line_num))
                    else:
                        _user_error(ntr_fn, line_num, 'Invalid syntax')

                line_num += 1

    except Exception as e:
        _user_error(ntr_fn, line_num, f'Error processing file: {e}')
        sc.error(f'Error processing file: {ntr_fn}:{line_num} {e}', e.__traceback__)
        return None

    return None if no_index else (sections, links, refs)


#-----------------------------------------------------------------------------------
def _build_selector(targets):
    ''' Populate the selector. '''

    panel_items = []
    for target in targets:
        ann = target.ttype
        if target.ttype == 'section':
            tt = "S"
            ann = ''
        elif target.ttype == 'uri':
            tt = "R"
        elif target.ttype == 'image':
            tt = "R"
        elif target.ttype == 'path':
            tt = "R"
        else:
            tt = "?"

        # COLOR_REDISH/_ORANGISH, _GREENISH/_YELLOWISH/_CYANISH, _BLUISH, _PURPLISH, _PINKISH (_DARK, _LIGHT)
        if target.category == 'sticky':
            clr = sublime.KindId.COLOR_PURPLISH
        elif target.category == 'mru':
            clr = sublime.KindId.COLOR_REDISH
        else:
            clr = sublime.KindId.COLOR_GREENISH

        sty = (clr, tt, '')

        lbl = target.name if len(target.name) > 0 else target.resource
        panel_items.append(sublime.QuickPanelItem(trigger=f'{lbl}', annotation=ann, kind=sty))

    return panel_items


#-----------------------------------------------------------------------------------
def _get_all_tags():
    ''' Return all tags found in all ntr files. Honors sort_tags_alpha setting. '''
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)
    sort_tags_alpha = settings.get('sort_tags_alpha')
    tags = {}  # k:tag text v:count

    for target in _targets:
        for tag in target.tags:
            tags[tag] = tags[tag] + 1 if tag in tags else 1

    sorted_tags = []
    if sort_tags_alpha:
        sorted_tags = sorted(tags.keys())
    else:  # Sort by frequency.
        sorted_tags = [x[0] for x in sorted(tags.items(), key=lambda x:x[1], reverse=True)]
    return sorted_tags


#-----------------------------------------------------------------------------------
def _get_all_ntr_files():
    ''' Return a sorted list of all processed .ntr file names. '''
    fns = []
    for target in _targets:
        if target.file not in fns:
            fns.append(target.file)
    return sorted(fns)


#-----------------------------------------------------------------------------------
def _filter_order_targets(**kwargs):
    ''' Get filtered/ordered list of targets.
        Options facilitate usage for UI presentation or internal consumption:
        sort: T/F asc only
        mru_first: Put the mru first, then the ones in the current file
        current_file: If provided put these after mru and before the rest
        tags: filter by tags
        returns a list of targets
    '''
    if _current_project is None:
        return []

    settings = sublime.load_settings(NOTR_SETTINGS_FILE)
    stickies = _current_project['sticky']

    current_file_targets = []
    other_targets = []

    # Args.
    sort = True if "sort" in kwargs and kwargs["sort"] else False
    tags = kwargs["tags"] if "tags" in kwargs else []
    mru_first = True if "mru_first" in kwargs and kwargs["mru_first"] else False

    current_file = None
    if ("current_file" in kwargs and
        kwargs["current_file"] is not None and
        os.path.exists(kwargs["current_file"])):
        current_file = kwargs["current_file"]

    # Cache some targets to maintain order.
    sticky_cache = {}
    mru_cache = {}

    for target in _targets:
        target.category = ''  # default
        # Sticky always wins.
        if target.name in stickies:
            target.category = 'sticky'
            sticky_cache[target.name] = target
        else:  # The others.
            # Check tags.
            tag_ok = len(tags) == 0
            for t in tags:
                if t in target.tags:
                    tag_ok = True

            if tag_ok:
                if mru_first and target.name in _current_mru:
                    target.category = 'mru'
                    mru_cache[target.name] = target
                elif current_file is not None:
                    if target.file is not None and os.path.samefile(target.file, current_file):
                        current_file_targets.append(target)
                    else:
                        other_targets.append(target)
                else:
                    other_targets.append(target)

    # Sort the bulk?
    if sort:
        current_file_targets = sorted(current_file_targets)
        other_targets = sorted(other_targets)

    # Collect and return.
    ret = []
    # Order these.
    for st in stickies:  # by position in settings
        if st in sticky_cache:
            ret.append(sticky_cache[st])
    for mru in _current_mru:  # by recent first
        if mru in mru_cache:
            ret.append(mru_cache[mru])

    ret.extend(current_file_targets)
    ret.extend(other_targets)

    return ret


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
def _update_mru(name):
    ''' Update the mru list. Removes duplicate and invalid names. '''
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)
    mru_size = settings.get("mru_size")

    # Clean up the mru.
    tmp = _current_mru.copy()
    _current_mru.clear()
    _current_mru.append(name)  # new first

    valid_refs = set()
    for target in _targets:
        if target.category != 'sticky':
            valid_refs.add(target.name)
    for tname in tmp:
        if tname in valid_refs and tname not in _current_mru and len(_current_mru) < mru_size:
            _current_mru.append(tname)

    # Persist.
    _save_store()


#-----------------------------------------------------------------------------------
def _user_error(path, line, msg):
    ''' Error in user edited file. '''
    if '(' in msg or ')' in msg:
        msg = msg + '   <<< Targets with parens not allowed'
    _parse_errors.append((path, line, msg))


#-----------------------------------------------------------------------------------
def _get_froot(fn):
    return os.path.basename(os.path.splitext(fn)[0])
