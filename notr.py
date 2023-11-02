import os
import re
import glob
import collections
import random
import json
import sublime
import sublime_plugin
from . import sbot_common as sc


NOTR_SETTINGS_FILE = "Notr.sublime-settings"
NOTR_STORAGE_FILE = "notr.store"

# Known file types.
IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']

# TODO1 Indent/dedent lists. Toggle bullets. Code chunks get '```'. Quote chunks get '> '. Use different colors for each of X?!*
# TODO1 Text formatting inside lists, tables, etc. See link in list for example.
# TODO1 Simple section folding. C:\\Users\\cepth\\OneDrive\\OneDriveDocuments\\tech\\sublime\\folding-hack.py ??https://github.com/jamalsenouci/sublimetext-syntaxfold.
# TODO2 Publish notes somewhere - raw or rendered.
# TODO2 Sticky targets in list.

# FUTURE:
# - Hierarchal section folding. Might be tricky - https://github.com/sublimehq/sublime_text/issues/5423.
# - Multiple projects. One would be the demo.
# - Show image file thumbnail as phantom or hover. Something fun with annotations, see sublime-markdown-popups.
# - Make into package, maybe others. https://packagecontrol.io/docs/submitting_a_package.
# - Backup notr project files.


#--------------------------- Types -------------------------------------------------

# One target of section or file/uri.
# type: section, uri, image, path
# name: section title
# resource: what type points to
# level: for section only
# tags[] tags for targets
# file: .ntr file path
# line: .ntr file line
Target = collections.namedtuple('Target', 'type, name, resource, level, tags, file, line')

# A reference to a Target.
# name: target name
# file: ntr file path
# line: ntr file line
Ref = collections.namedtuple('Ref', 'name, file, line')

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
class NotrGotoTargetCommand(sublime_plugin.TextCommand):
    ''' List all the tag(s) and/or target(s) for user selection then open corresponding file. '''

    # Prepared lists for quick panel.
    _tags = []
    _targets_to_select = []

    def run(self, edit, filter_by_tag):
        if filter_by_tag:
            self._tags = _get_tags()
            panel_items = []

            for tag in self._tags:
                panel_items.append(sublime.QuickPanelItem(trigger=tag, kind=sublime.KIND_AMBIGUOUS))
            self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_tag)
        else:
            self.show_targets(_get_targets(mru_first=True, current_file=self.view.file_name()))

    def on_sel_tag(self, *args, **kwargs):
        sel = args[0]

        if sel >= 0:
            # Make a selector with sorted target names, current file's first.
            sel_tag = self._tags[sel]

            # Hide current quick panel.
            self.view.window().run_command("hide_overlay")

            # Filter per tag selection.
            tag_targets = []
            for target in _targets:
                if sel_tag in target.tags:
                    tag_targets.append(target)

            if len(tag_targets) > 0:
                self.show_targets(tag_targets)
            else:
                sublime.status_message('No targets with that tag')

    def show_targets(self, targets):
        ''' Present target options to user. '''
        self._targets_to_select = targets
        panel_items = []

        for target in self._targets_to_select:
            panel_items.append(sublime.QuickPanelItem(trigger=f'{target.name}', kind=sublime.KIND_AMBIGUOUS))
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
            else: # "image", "uri", "path"
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
                    else: # "image", "uri", "path"
                        valid = sc.open_file(target.resource)
                    break

            if not valid:
                sc.slog(sc.CAT_ERR, f'Invalid reference: {self.view.file_name()} :{tref}')

        elif tlink is not None:  # explicit link. do immediate.
            fn = sc.expand_vars(tlink)
            valid = sc.open_file(fn)
            if not valid:
                sc.slog(sc.CAT_ERR, f'Invalid link: {tlink}')

        else: # Show a quickpanel of all target names.
            panel_items = []
            self._targets_to_select = _get_targets(sort=True, mru_first=True, current_file=self.view.file_name())
            for target in self._targets_to_select:
                panel_items.append(sublime.QuickPanelItem(trigger=target.name, kind=sublime.KIND_AMBIGUOUS))
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
                    else: # "image", "uri", "path"
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
        panel_items = []
        self._targets_to_select = _get_targets(sort=True, mru_first=True, current_file=self.view.file_name())
        for target in self._targets_to_select:
            panel_items.append(sublime.QuickPanelItem(trigger=target.name, kind=sublime.KIND_AMBIGUOUS))
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
class NotrPublishCommand(sublime_plugin.WindowCommand):
    ''' Publish notes somewhere... '''

    def run(self):
        # Render notr files for android or ? target.
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
        do_one('tags', _get_tags())
        do_one('ntr_files', _get_ntr_files())
        if len(_parse_errors) > 0:
            text.insert(0, f'========== Errors in your file - see below ==========\n')
            do_one('parse_errors', _parse_errors)

        sc.create_new_view(self.window, '\n'.join(text))

    def is_visible(self):
        return True


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
    valid_targets = _get_targets()
    valid_refs = []
    for target in valid_targets:
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
            re_links = re.compile(r'\[(.*)\]\((.*)\) *(?:\[(.*)\])?') # TODO1 handle unnamed ok  - anonymous
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
                                ttype = "path" # TODO2 useful to discriminate file and folder?
                            else:
                                _user_error(ntr_fn, line_num, f'Invalid target resource: {res}')

                            if ttype is not None:
                                # Any tags?
                                tags = []
                                if len(m) >= 2:
                                    tags = m[2].strip().split()
                                links.append(Target(ttype, name, res, 0, tags, ntr_fn, line_num))
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
                        if len(hashes) == 1: # Minimizes slector clutter, could be setting. TODO2
                            sections.append(Target("section", name, "", len(hashes), tags, ntr_fn, line_num))
                    else:
                        _user_error(ntr_fn, line_num, 'Invalid syntax')

                line_num += 1

    except Exception as e:
        sc.slog(sc.CAT_ERR, f'Error processing {ntr_fn}: {e}')
        raise

    return None if no_index else (sections, links, refs)


#-----------------------------------------------------------------------------------
def _get_tags():
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
def _get_ntr_files():
    ''' Return a sorted list of all processed .ntr file names. '''
    fns = []
    for target in _targets:
        if target.file not in fns:
            fns.append(target.file)
    return sorted(fns)


#-----------------------------------------------------------------------------------
def _get_targets(**kwargs):

    ''' Get filtered/ordered list of targets.
        Options facilitate usage for UI presentation or internal consumption:
        sort: T/F asc only
        mru_first: Put the mru first, then the ones in the current file
        current_file: If provided put these after mru and before the rest
        filter_by_tags: filter by tags
        returns a list per request
    '''
    current_file_targets = []
    other_targets = []

    # Args.
    sort = True if "sort" in kwargs and kwargs["sort"] else False
    filter_by_tags = True if "filter_by_tags" in kwargs and kwargs["filter_by_tags"] else False
    mru_first = True if "mru_first" in kwargs and kwargs["mru_first"] else False
    current_file = kwargs["current_file"] if "current_file" in kwargs else None

    print(f"sort:{sort} filter_by_tags:{filter_by_tags} mru_first:{mru_first} current_file:{current_file}")

    # Cache the mru targets to maintain order.
    mru_cache = {}

    for target in _targets:
        if mru_first and target.name in _mru:
            mru_cache[target.name] = target
        elif current_file is not None and os.path.samefile(target.file, current_file):
            current_file_targets.append(target)
        else:
            other_targets.append(target)

    # Sort?
    if sort:
        current_file_targets = sorted(current_file_targets)
        other_targets = sorted(other_targets)

    # Collect and return.
    ret = []
    if mru_first:
        for mru in _mru:  # ordered by recent first
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
    _mru.append(name) # new first

    valid_refs = set()
    for target in _get_targets():
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
    else: # Assume new file.
        _mru.clear()


#-----------------------------------------------------------------------------------
def _write_store():
    ''' Save everything. '''
    global _mru
    
    store_fn = sc.get_store_fn(NOTR_STORAGE_FILE)
    store = { "mru":_mru }
    print(f"_write_store:{store}")
    with open(store_fn, 'w') as fp:
        json.dump(store, fp, indent=4)


#-----------------------------------------------------------------------------------
def _user_error(path, line, msg):
    ''' Error in user edited file. '''
    _parse_errors.append(f'{path}({line}): {msg}')


#-----------------------------------------------------------------------------------
def _get_froot(fn):
    return os.path.basename(os.path.splitext(fn)[0])
