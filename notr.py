import os
import re
import glob
import collections
import random
import json
from dataclasses import dataclass
import sublime
import sublime_plugin
from . import sbot_common as sc


NOTR_SETTINGS_FILE = "Notr.sublime-settings"
NOTR_STORAGE_FILE = "notr.store"

# Known file types.
IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']


# TODO Use different colors for each of -X?!*
# TODO Indent/dedent lists. Toggle bullets. Code chunks get '```'. Quote chunks get '> '.


# FUTURE:
# - Publish notes somewhere - raw or rendered.
# - Hierarchal section folding. Might be tricky - https://github.com/sublimehq/sublime_text/issues/5423.
# - Multiple projects. One would be the example.
# - Show image file thumbnail as phantom or hover. Something fun with annotations, see sublime-markdown-popups.
# - Make into package, maybe others. https://packagecontrol.io/docs/submitting_a_package.
# - Backup notr files.


#--------------------------- Types -------------------------------------------------

# One target of section or file/uri.
@dataclass
class Target:
    name: str  # section title
    type: str  # section, uri, image, path
    category: str  # sticky, mru, none
    level: int  # for section only
    tags: []  # tags for targets
    resource: str  # what type points to
    file: str  # .ntr file path
    line: int  # .ntr file line

# A reference to a Target.
@dataclass
class Ref:
    name: str  # target name
    file: str  # .ntr file path
    line: int  # .ntr file line


#---------------------------- Data -----------------------------------------------

# All Targets found in all ntr files.
_targets = []

# All Refs found in all ntr files.
_refs = []

# Persisted mru.
_mru = []

# Parse errors to report to user.
_parse_errors = []


#-----------------------------------------------------------------------------------
def plugin_loaded():
    pass


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    pass


#-----------------------------------------------------------------------------------
#-------------------------- Events -------------------------------------------------
#-----------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------
class NotrEvent(sublime_plugin.EventListener):
    ''' Process view events. '''

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Initialize everything. '''
        _read_store()

        # Open and process notr files.
        _process_notr_files(views[0].window())

        # Views are all valid now so init them.
        for view in views:
            self._init_fixed_hl(view)

    def on_load(self, view):
        ''' Loaded a new file. '''
        # View is valid so init it.
        self._init_fixed_hl(view)

    def on_pre_close(self, view):
        ''' Save anything. '''
        _write_store()

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
#-------------------------- WindowCommands -----------------------------------------
#-----------------------------------------------------------------------------------


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
        do_one('tags', _get_all_tags())
        do_one('ntr_files', _get_all_ntr_files())
        if len(_parse_errors) > 0:
            text.insert(0, '========== Errors in your file - see below ==========\n')
            do_one('parse_errors', _parse_errors)

        sc.create_new_view(self.window, '\n'.join(text))

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrFindInFilesCommand(sublime_plugin.WindowCommand):
    ''' Search in the .ntr files. '''

    def run(self):

        # Assemble the search locations from users paths. Index directory also?
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
        paths = ["*.ntr", "-<open files>"]
        notr_paths = settings.get('notr_paths')
        for npath in notr_paths:
            expath = sc.expand_vars(npath)
            if expath is not None and os.path.exists(expath):
                paths.append(expath)

        # Show it so the user can enter the pattern.
        # https://github.com/SublimeText/PackageDev/blob/master/plugins/command_completions/builtin_commands_meta_data.yaml
        self.window.run_command("show_panel",
            {
                "panel": "find_in_files",
                "where": ', '.join(paths),
                "case_sensitive": True,
                "pattern": "",
                "whole_word": False, 
                "preserve_case": True,
                "show_context": False,
                "use_buffer": True,
                "replace": "",
                "regex": False,
            })

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrPublishCommand(sublime_plugin.WindowCommand):
    ''' Publish notes somewhere... '''

    def run(self):
        # Render notr files for android or ? target.
        # self.window.active_view().run_command('sbot_render_to_html', {'font_face':'monospace', 'font_size':'1.2em' } )  
        pass

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
#-------------------------- TextCommands -------------------------------------------
#-----------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
class NotrGotoTargetCommand(sublime_plugin.TextCommand):
    ''' List all the tag(s) and/or target(s) for user selection then open corresponding file. '''

    # Prepared lists for quick panel.
    _tags = []
    _targets_to_select = []

    def run(self, edit, filter_by_tag):
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
        sel = args[0]

        if sel >= 0:
            # Hide current quick panel.
            self.view.window().run_command("hide_overlay")

            # Make a selector with sorted target names, current file's first.
            sel_tag = self._tags[sel]

            # Filter per tag selection.
            tag_targets = _filter_order_targets(sort=True, mru_first=True, tags=[sel_tag])
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
        sel = args[0]
        if sel >= 0:
            # Locate the target record.
            target = self._targets_to_select[sel]
            _update_mru(target.name)
            if target.type == "section":
                # Open the notr file and position it.
                sc.wait_load_file(self.view.window(), target.file, target.line)
            else:  # "image", "uri", "path"
                sc.open_file(target.resource)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrFollowCommand(sublime_plugin.TextCommand):
    ''' Open target from selected ref or link. '''
    _targets_to_select = []

    def run(self, edit):
        # Determine if user has selected a specific ref or link to follow, otherwise show the list of all.
        valid = True  # default
        tref = _get_selection_for_scope(self.view, 'markup.link.refname.notr')
        tlink = _get_selection_for_scope(self.view, 'markup.underline.link.notr')

        if tref is not None:  # explicit ref to selected element - do immediate.
            # Get the corresponding target spec.
            for target in _targets:
                valid = False
                if target.name == tref:
                    if target.type == "section":
                        # Open the notr file and position it.
                        sc.wait_load_file(self.view.window(), target.file, target.line)
                        valid = True
                    else:  # "image", "uri", "path"
                        valid = sc.open_file(target.resource)
                    break

            if not valid:
                sc.slog(sc.CAT_ERR, f'Invalid reference: {self.view.file_name()} :{tref}')

        elif tlink is not None:  # explicit link. do immediate.
            fn = sc.expand_vars(tlink)
            valid = sc.open_file(fn)
            if not valid:
                sc.slog(sc.CAT_ERR, f'Invalid link: {tlink}')

        else:  # Show a quickpanel of all target names.
            self._targets_to_select = _filter_order_targets(sort=True, mru_first=True, current_file=self.view.file_name())
            panel_items = _build_selector(self._targets_to_select)
            self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_ref)

    def on_sel_ref(self, *args, **kwargs):
        sel = args[0]
        if sel >= 0:
            tsel = self._targets_to_select[sel]            
            for target in self._targets_to_select:
                if target.name == tsel.name:
                    if target.type == "section":
                        # Open the notr file and position it.
                        sc.wait_load_file(self.view.window(), target.file, target.line)
                    else:  # "image", "uri", "path"
                        sc.open_file(target.resource)
                    break

    # def is_visible(self):
    #     return _get_selection_for_scope(self.view, 'markup.link.refname.notr') is not None


#-----------------------------------------------------------------------------------
class NotrInsertRefCommand(sublime_plugin.TextCommand):
    ''' Insert ref from list of known refs. '''
    _targets_to_select = []

    def run(self, edit):
        # Show a quickpanel of all target names.
        self._targets_to_select = _filter_order_targets(sort=True, mru_first=True, current_file=self.view.file_name())
        panel_items = _build_selector(self._targets_to_select)
        self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_ref)

    def on_sel_ref(self, *args, **kwargs):
        sel = args[0]
        if sel >= 0:
            s = f'[*{self._targets_to_select[sel].name}]'
            self.view.run_command("insert", {"characters": f'{s}'})  # Insert in created view
        else:
            # Stick them in the clipboard.
            sublime.set_clipboard('\n'.join(self._targets_to_select))

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
        s = f'[EDIT_ME{random.randrange(10000)}]({sublime.get_clipboard()})'
        caret = sc.get_single_caret(self.view)
        self.view.insert(edit, caret, s)

    def is_visible(self):
        v = self.view
        return v.syntax() is not None and \
            v.syntax().name == 'Notr' and \
            sc.get_single_caret(v) is not None and \
            sublime.get_clipboard() != ''


#-----------------------------------------------------------------------------------
#-------------------------- Private Functions --------------------------------------
#-----------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------
def _process_notr_files(window):
    ''' Get all ntr files and grab their goodies. '''
    _targets.clear()
    _refs.clear()
    _parse_errors.clear()
    ntr_files = []

    # Open and process all notr files.
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)

    # Index first.
    notr_index = settings.get('notr_index')
    if notr_index is not None:
        index_path = sc.expand_vars(notr_index)
        if index_path is not None and os.path.exists(index_path):
            ntr_files.append(index_path)
        else:
            _user_error(NOTR_SETTINGS_FILE, -1, f'Invalid path in settings {notr_index}')

    # Paths.
    notr_paths = settings.get('notr_paths')
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

            # Get the things of interest defined in the file.
            re_directives = re.compile(r'^:(.*)')
            re_links = re.compile(r'\[(.*)\]\((.*)\) *(?:\[(.*)\])?')
            re_refs = re.compile(r'\[\* *([^\]]*)\]')
            re_sections = re.compile(r'^(#+ +[^\[]+) *(?:\[(.*)\])?')

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
                                ttype = "image"
                            elif res.startswith('http'):
                                ttype = "uri"
                            elif os.path.exists(res):
                                ttype = "path"  # FUTURE useful to discriminate file and directory?
                            else:
                                _user_error(ntr_fn, line_num, f'Invalid target resource: {res}')

                            if ttype is not None:
                                # Any tags?
                                tags = []
                                if len(m) >= 2:
                                    tags = m[2].strip().split()
                                links.append(Target(name, ttype, "", 0, tags, res, ntr_fn, line_num))
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
                            name = f'{_get_froot(ntr_fn)}{hashes}{content[1].strip()}'
                        else:
                            valid = False

                        if valid:
                            tags = m[1].strip().split()
                    else:
                        valid = False

                    if valid:
                        if len(hashes) == 1:  # Minimizes selector clutter, could be setting.
                            sections.append(Target(name, "section", "", len(hashes), tags, "", ntr_fn, line_num))
                    else:
                        _user_error(ntr_fn, line_num, 'Invalid syntax')

                line_num += 1

    except Exception as e:
        sc.slog(sc.CAT_ERR, f'Error processing {ntr_fn}: {e}')
        raise

    return None if no_index else (sections, links, refs)


#-----------------------------------------------------------------------------------
def _build_selector(targets):
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)
    sticky = settings.get("sticky")

    panel_items = []
    for target in targets:
        color = sublime.KIND_ID_AMBIGUOUS  # default
        if target.category == "sticky": color = sublime.KindId.COLOR_REDISH
        elif target.category == "mru": color = sublime.KindId.COLOR_GREENISH
        panel_items.append(sublime.QuickPanelItem(trigger=f'{target.name}', kind=(color, "", "")))  # details="deets", annotation="annie"))
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
        returns a list per request
    '''
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)
    stickies = settings.get("sticky")

    sticky_targets = []
    current_file_targets = []
    other_targets = []

    # Args.
    sort = True if "sort" in kwargs and kwargs["sort"] else False
    tags = kwargs["tags"] if "tags" in kwargs else []
    mru_first = True if "mru_first" in kwargs and kwargs["mru_first"] else False
    current_file = kwargs["current_file"] if "current_file" in kwargs else None

    # Cache some targets to maintain order.
    sticky_cache = {}
    mru_cache = {}

    for target in _targets:
        target.category = "" # default
        # Sticky always wins.
        if target.name in stickies:
            target.category = "sticky"
            sticky_cache[target.name] = target
        else: # The others.
            # Check tags.
            tag_ok = len(tags) == 0
            for t in tags:
                if t in target.tags:
                    tag_ok = True

            if tag_ok:
                if mru_first and target.name in _mru:
                    target.category = "mru"
                    mru_cache[target.name] = target
                elif current_file is not None and os.path.samefile(target.file, current_file):
                    current_file_targets.append(target)
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
    for mru in _mru:  # by recent first
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
    global _mru

    settings = sublime.load_settings(NOTR_SETTINGS_FILE)
    mru_size = settings.get("mru_size")

    # Clean up the mru.
    tmp = _mru.copy()
    _mru.clear()
    _mru.append(name)  # new first

    valid_refs = set()
    for target in _targets:
        valid_refs.add(target.name)

    for tname in tmp:
        if tname in valid_refs and tname not in _mru and len(_mru) <= mru_size:
            _mru.append(tname)

    # Persist.
    _write_store()


#-----------------------------------------------------------------------------------
def _read_store():
    ''' Get everything. '''
    global _mru

    # Get persisted info.
    store_fn = sc.get_store_fn(NOTR_STORAGE_FILE)

    if os.path.isfile(store_fn):
        try:
            with open(store_fn, 'r') as fp:
                s = fp.read()
                store = json.loads(s)
                _mru = store["mru"]
        except Exception as e:
            # Assume bad file.
            sc.slog(sc.CAT_ERR, f'Error processing {store_fn}: {e}')
    else:  # Assume new file.
        _mru.clear()


#-----------------------------------------------------------------------------------
def _write_store():
    ''' Save everything. '''
    global _mru
    
    store_fn = sc.get_store_fn(NOTR_STORAGE_FILE)
    store = {"mru": _mru}
    with open(store_fn, 'w') as fp:
        json.dump(store, fp, indent=4)


#-----------------------------------------------------------------------------------
def _user_error(path, line, msg):
    ''' Error in user edited file. '''
    _parse_errors.append(f'{path}({line}): {msg}')


#-----------------------------------------------------------------------------------
def _get_froot(fn):
    return os.path.basename(os.path.splitext(fn)[0])
