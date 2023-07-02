import os
import re
import glob
import collections
import sublime
import sublime_plugin
from . import sbot_common as sc


NOTR_SETTINGS_FILE = "Notr.sublime-settings"
# NOTR_SETTINGS_FILE = "Notr_demo.sublime-settings"


#--------------------------- Types -------------------------------------------------

# One section: srcfile=ntr file path, line=ntr file line, froot=ntr file name root, level=1-N, name=section title, tags[]
Section = collections.namedtuple('Section', 'srcfile, line, froot, level, name, tags')

# One link: srcfile=ntr file path, line=ntr file line, name=unique desc text, target=clickable uri or file
Link = collections.namedtuple('Link', 'srcfile, line, name, target')

# One reference: srcfile=ntr file path, line=ntr file line, target=section or link
Ref = collections.namedtuple('Ref', 'srcfile, line, target')


#---------------------------- Globals -----------------------------------------------
# Some could be multidict?

# All Sections found in all ntr files - in order to support hierarchy.
_sections = []

# All Links found in all ntr files.
_links = []

# All Refs found in all ntr files.
_refs = []

# All valid ref targets in _sections and _links.
_valid_ref_targets = {}

# All tags found in all ntr files. Value is count.
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
        _process_notr_files()

        if len(_parse_errors) > 0:
            sc.create_new_view(views[0].window(), '\n'.join(_parse_errors))

        # Views are all valid now so init them.
        for view in views:
            self._init_fixed_hl(view)

    def on_load(self, view):
        ''' Load a new file. View is valid so init it. '''
        self._init_fixed_hl(view)

    def on_post_save(self, view):
        ''' Called after a ntr view has been saved so reload all ntr files. Seems a bit brute force, how else? '''
        if view.syntax().name == 'Notr':
            _process_notr_files()

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
                    anns = []

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
class NotrGotoSectionCommand(sublime_plugin.WindowCommand):
    ''' List all the tag(s) and/or sections(s) for user selection then open corresponding file. '''

    # Prepared lists for quick panel.
    _sorted_tags = []
    _sorted_sec_names = []

    def run(self, filter_by_tag):
        self._sorted_tags.clear()
        self._sorted_sec_names.clear()
        panel_items = []

        if filter_by_tag:
            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            sort_tags_alpha = settings.get('sort_tags_alpha')
            if sort_tags_alpha:
                self._sorted_tags = sorted(_tags)
            else:  # Sort by frequency.
                self._sorted_tags = [x[0] for x in sorted(_tags.items(), key=lambda x:x[1], reverse=True)]

            for tag in self._sorted_tags:
                panel_items.append(sublime.QuickPanelItem(trigger=tag, annotation=f"qty:{_tags[tag]}", kind=sublime.KIND_AMBIGUOUS))
            self.window.show_quick_panel(panel_items, on_select=self.on_sel_tag)
        else:  # all sections
            n = []
            for section in _sections:
                n.append(f'{section.froot}#{section.name}')
            self._sorted_sec_names = sorted(n)
            for sec_name in self._sorted_sec_names:
                panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
            self.window.show_quick_panel(panel_items, on_select=self.on_sel_section)

    def on_sel_tag(self, *args, **kwargs):
        sel = args[0]

        if sel >= 0:
            # Make a selector with sorted section names.
            sel_tag = self._sorted_tags[sel]

            n = []
            for section in _sections:
                if sel_tag in section.tags:
                    n.append(f'{section.froot}#{section.name}')
            if len(n) > 0:
                self._sorted_sec_names = sorted(n)
                # Hide current quick panel.
                self.window.run_command("hide_overlay")
                panel_items = []
                for sec_name in self._sorted_sec_names:
                    panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
                self.window.show_quick_panel(panel_items, on_select=self.on_sel_section)
            else:
                sublime.status_message('No sections with that tag')
        else:
            # Stick them in the clipboard.
            sublime.set_clipboard('\n'.join(self._sorted_tags))

    def on_sel_section(self, *args, **kwargs):
        sel = args[0]

        if sel >= 0:
            # Locate the section record.
            sel_secname = self._sorted_sec_names[sel]
            for section in _sections:
                if f'{section.froot}#{section.name}' == sel_secname:
                    # Open the section in a new view.
                    vnew = sc.wait_load_file(self.window, section.srcfile, section.line)
                    break
        else:
            # Stick them in the clipboard.
            sublime.set_clipboard('\n'.join(self._sorted_sec_names))

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrGotoRefCommand(sublime_plugin.TextCommand):
    ''' Open link or section from selected ref. '''

    def run(self, edit):
        valid = True # default
        ref_text = _get_selection_for_scope(self.view, 'markup.link.refname.notr')

        if ref_text is not None and '#' in ref_text:  # Section ref like  [*#Links and Refs]  [* file_root#section_name]
            froot = None
            ref_name = None
            ref_parts = ref_text.split('#')

            if len(ref_parts) == 2:
                froot = ref_parts[0].strip()
                ref_name = ref_parts[1].strip()

                if len(froot) == 0:
                    # It's this file.
                    froot = _get_froot(self.view.file_name())
            else:
                valid = False

            # Get the Section spec.
            if valid:
                valid = False
                for section in _sections:
                    if section.froot == froot and section.name == ref_name:
                        # Open the file and position it.
                        sc.wait_load_file(self.view.window(), section.srcfile, section.line)
                        valid = True
                        break

            if not valid:
                sc.slog(sc.CAT_ERR, f'Invalid reference: {self.view.file_name()} :{ref_name}')

        else:  # Link ref
            # Get the Link spec.
            for link in _links:
                if link.name == ref_text:
                    if os.path.exists(link.target) or link.target.startswith('http'):
                        sc.start_file(link.target)
                    break

    def is_visible(self):
        return _get_selection_for_scope(self.view, 'markup.link.refname.notr') is not None


#-----------------------------------------------------------------------------------
class NotrInsertHruleCommand(sublime_plugin.TextCommand):
    ''' Insert visuals. '''

    def run(self, edit, fill_char):
        v = self.view
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
        visual_line_length = settings.get('visual_line_length')

        # Start of current line.
        caret = sc.get_single_caret(v)
        lst = v.line(caret)

        s = fill_char * visual_line_length + '\n'
        v.insert(edit, lst.a, s)

    def is_visible(self):
        return self.view.syntax() is not None and self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrInsertLinkCommand(sublime_plugin.TextCommand):
    ''' Insert link from clipboard. Assumes user clipped appropriate string. '''

    def run(self, edit):
        s = f'[name?: {sublime.get_clipboard()}]'
        caret = sc.get_single_caret(self.view)
        self.view.insert(edit, caret, s)

    def is_visible(self):
        return self.view.syntax() is not None and self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrInsertRefCommand(sublime_plugin.TextCommand):
    ''' Insert ref from list of known refs. '''
    _sorted_refs = []

    def run(self, edit):
        self._sorted_refs = sorted(_valid_ref_targets)
        panel_items = []
        for sec_name in self._sorted_refs:
            panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
        self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_ref)

    def on_sel_ref(self, *args, **kwargs):
        sel = args[0]
        if sel >= 0:
            s = f'[*{self._sorted_refs[sel]}]'
            self.view.run_command("insert", {"characters": f'{s}'})  # Insert in created view
        else:
            # Stick them in the clipboard.
            sublime.set_clipboard('\n'.join(self._sorted_refs))

    def is_visible(self):
        return self.view.syntax() is not None and self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrReloadCommand(sublime_plugin.WindowCommand):
    ''' Reload after editing. '''

    def run(self):
        # Open and process notr files.
        _process_notr_files()

        if len(_parse_errors) > 0:
            sc.create_new_view(self.window, '\n'.join(_parse_errors))

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrDumpCommand(sublime_plugin.WindowCommand):
    ''' Diagnostic. '''

    def run(self):
        text = []
        text.append('=== _sections ===')
        for x in _sections:
            text.append(str(x))

        text.append('')
        text.append('=== _links ===')
        for x in _links:
            text.append(str(x))

        text.append('')
        text.append('=== _refs ===')
        for x in _refs:
            text.append(str(x))

        text.append('')
        text.append('=== _valid_ref_targets ===')
        for x in _valid_ref_targets:
            text.append(f'{x}')

        text.append('')
        text.append('=== _tags ===')
        for x in _tags:
            text.append(f'{x}:{_tags[x]}')

        text.append('')
        text.append('=== _ntr_files ===')
        for x in _ntr_files:
            text.append(f'{x}')

        text.append('')
        text.append('=== _parse_errors ===')
        for x in _parse_errors:
            text.append(f'{x}')

        sc.create_new_view(self.window, '\n'.join(text))

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
def _user_error(path, line, msg):
    ''' Error in user edited file. '''
    _parse_errors.append(f'{path}({line}): {msg}')

#-----------------------------------------------------------------------------------
def _process_notr_files():
    ''' Get all ntr files and grab their goodies. '''

    # sc.slog(sc.CAT_DBG, 'Processing notr files')

    _ntr_files.clear()
    _tags.clear()
    _refs.clear()
    _sections.clear()
    _links.clear()
    _valid_ref_targets.clear()
    _parse_errors.clear()

    ### Open and process all notr files.
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
                if nfile != index_path:
                    _ntr_files.append(nfile)
        else:
            _user_error(NOTR_SETTINGS_FILE, -1, f'Invalid path in settings {npath}')

    # Process the files.
    for nfile in _ntr_files:
        _process_notr_file(nfile)

    ### Check sanity of collected material.

    # Get valid ref targets.
    for section in _sections:
        target = f'{section.froot}#{section.name}'
        if target not in _valid_ref_targets:
            _valid_ref_targets[target] = 0
        else:
            _user_error(section.srcfile, section.line, f'Duplicate section name:{section.name}')

    # Check all links are valid 'http(s)://' or file, no dupe names.
    for link in _links:
        if link.name in _valid_ref_targets:
            _user_error(link.srcfile, link.line, f'Duplicate link name:{link.name}')
        else:
            if link.target.startswith('http') or os.path.exists(link.target):
                # Assume a valid uri or path
                _valid_ref_targets[link.name] = 0
            else:
                _user_error(link.srcfile, link.line, f'Invalid link target:{link.target}')

    # Check all user refs are valid -> (froot)#section or link.name, no dupes.
    for ref in _refs:
        if ref.target not in _valid_ref_targets:
            _user_error(ref.srcfile, ref.line, f'Invalid ref target:{ref.target}')


#-----------------------------------------------------------------------------------
def _process_notr_file(fn):
    ''' Regex and process sections and links. This collects the text and checks syntax. Validity will be checked when all files processed. '''

    sections = []
    links = []
    refs = []
    no_index = False

    try:
        with open(fn, 'r', encoding='utf-8') as file:
            lines = file.read().splitlines()
            line_num = 1

            # Get the things of interest defined in the file.
            re_directives = re.compile(r'^\$(.*)')
            re_links = re.compile(r'\[([^:]*): *([^\]]*)\]')
            re_refs = re.compile(r'\[\* *([^\]]*)\]')
            re_sections = re.compile(r'^(#+ +[^\[]+) *(?:\[(.*)\])?')
            # re_sections = re.compile(r'^(#+) +([^\[]+) *(?:\[(.*)\])?')

            for line in lines:
                # First: directives, aliases.
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
                        handled = True
                        # sc.slog(sc.CAT_DBG, f'>>> alias {alias}={value}')

                    if not handled:
                        _user_error(fn, line_num, f'Invalid directive')

                # Links
                matches = re_links.findall(line)
                for m in matches:
                    if len(m) == 2:
                        name = m[0].strip()
                        target = sc.expand_vars(m[1].strip())
                        if target == None:
                            # Bad env var.
                            _user_error(fn, line_num, f'Bad env var')
                        else:
                            links.append(Link(fn, line_num, name, target))
                    else:
                        _user_error(fn, line_num, f'Invalid syntax')

                # Refs
                matches = re_refs.findall(line)
                for m in matches:
                    target = m.strip()
                    # If it's local insert the froot.
                    if target.startswith('#'):
                        froot = _get_froot(fn)
                        target = froot + target
                    refs.append(Ref(fn, line_num, target))

                # Sections
                matches = re_sections.findall(line)
                for m in matches:
                    valid = True
                    if len(m) == 2:
                        # ## bla bla
                        content = m[0].strip().split(None, 1)
                        if len(content) == 2:
                            hashes = content[0].strip()
                            name = content[1].strip()
                        else:
                            valid = False

                        if valid:
                            tags = m[1].strip().split()
                    else:
                        valid = False

                    if valid:
                        froot = _get_froot(fn)
                        sections.append(Section(fn, line_num, froot, len(hashes), name, tags))
                        for tag in tags:
                            _tags[tag] = _tags[tag] + 1 if tag in _tags else 1
                    else:
                        _user_error(fn, line_num, f'Invalid syntax')


                line_num += 1

    except Exception as e:
        sc.slog(sc.CAT_ERR, f'Error processing {fn}: {e}')
        raise

    if not no_index:
        _sections.extend(sections)
        _links.extend(links)
        _refs.extend(refs)

#-----------------------------------------------------------------------------------
def _get_selection_for_scope(view, scope):
    ''' If the current region includes the scope return it otherwise None. '''

    sel_text = None
    caret = sc.get_single_caret(view)
    scopes = view.scope_name(caret).rstrip().split()
    if scope in scopes:
        reg = view.expand_to_scope(caret, scope)
        if reg is not None:
            sel_text = view.substr(reg).strip()

    return sel_text

#-----------------------------------------------------------------------------------
def _get_froot(fn):
    return os.path.basename(os.path.splitext(fn)[0])
