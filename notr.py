import os
import re
import glob
import collections
import sublime
import sublime_plugin
from . import sbot_common as sc


NOTR_SETTINGS_FILE = "Notr.sublime-settings"

''' 
- TODO2 icons, style, annotations, phantoms:
    - Show image as phantom or hover. Thumbnail. See SbotDev.
    - Annotations? See anns.append()
    - see linter code to see what they do: outline
    - see Sublime Markdown Popups (mdpopups) is a library for Sublime Text plugins. for generating tooltip popups.
      It also provides API methods for generating and styling the new phantom elements
        utilizes Python Markdown with a couple of special extensions to convert Markdown to
        HTML that can be used to create the popups and/or phantoms.
        API commands to aid in creating great tooltips and phantoms.
        will use your color scheme

- TODO1 folding by section - Default.fold.py? folding.py?

- TODO2 tables:
    - insert table = notr_insert_table(w, h)
    - table autofit/justify - notr_justify_table
    - table add/delete row(s)/col(s) ?

- TODO2 Block comment/uncomment useful? What would that mean - "hide" text? Insert string (# or // or ...) from settings.

- TODO1 Expose notes to web for access from phone. R/O render html?

- TODO2 Toggle syntax coloring (distraction free). Could just set to Plain Text.

- TODO2 Fancy file.section navigator (like word-ish and/or goto anything). Drag/drop section.

'''


#-----------------------------------------------------------------------------------

# All processed ntr files, fully qualified paths.
_ntr_files = []

# LinkType = Enum('LinkType', ['WEB', 'NTR', 'IMAGE', 'FILE', 'OTHER'])

# One section: srcfile=ntr file path, line=ntr file line, froot=ntr file name root, level=1-N, name=section text, tags[]
Section = collections.namedtuple('Section', 'srcfile, line, froot, level, name, tags')

# One link: srcfile=ntr file path, name=desc text, target=uri/file/clickable
Link = collections.namedtuple('Link', 'srcfile, name, target')

# Ref = collections.namedtuple('Ref', 'srcfile, name')

# All Sections found in all ntr files. Could be multidict?
_sections = []

# All Links found in all ntr files. Could be multidict?
_links = []

# All refs found in all ntr files.
_refs = []

# All tags found in all ntr files. Value is count.
_tags = {}


#-----------------------------------------------------------------------------------
def plugin_loaded():
    # sc.slog(sc.CAT_DBG, 'plugin_loaded()')
    pass


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    # sc.slog(sc.CAT_DBG, 'plugin_unloaded()')
    pass


#-----------------------------------------------------------------------------------
class NotrEvent(sublime_plugin.EventListener):
    ''' Process view events. '''

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Initialize everything. '''
        # sc.slog(sc.CAT_DBG, f'on_init() {views}')

        _ntr_files.clear()
        _tags.clear()
        _refs.clear()
        _sections.clear()
        _links.clear()

        # Open and process notr files. TODO1 need to redo if one of the ntr files is changed.
        _process_notr_files()

        # Views are all valid now so init them.
        for view in views:
            self._init_user_hl(view)

    def on_load(self, view):
        ''' Load a new file. View is valid so init it. '''
        # sc.slog(sc.CAT_DBG, f'on_load() {view}')
        self._init_user_hl(view)

    def _init_user_hl(self, view):
        ''' Add any user highlights. TODO1 differentiate these from SbotHighlight flavor - outline or inverse or italic or something. '''

        if view.is_scratch() is False and view.file_name() is not None and view.syntax().name == 'Notr':
            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            user_hl = settings.get('user_hl')
            whole_word = settings.get('user_hl_whole_word')

            if user_hl is not None:
                for i in range(max(len(user_hl), 3)):
                    # Clean first.
                    region_name = f'userhl_{i+1}_region'
                    view.erase_regions(region_name)

                    # New ones.
                    hl_regions = []
                    anns = []

                    # Colorize one token.
                    for token in user_hl[i]:
                        escaped = re.escape(token)
                        if whole_word:  # and escaped[0].isalnum():
                            escaped = r'\b%s\b' % escaped
                        regs = view.find_all(escaped) if whole_word else view.find_all(token, sublime.LITERAL)
                        hl_regions.extend(regs)

                    if len(hl_regions) > 0:
                        anns = []
                        for reg in hl_regions:
                            anns.append(f'Region: {reg.a}->{len(reg)}')

                        view.add_regions(key=region_name, regions=hl_regions, scope=f'markup.user_hl{i+1}.notr',
                                         icon='dot', flags=sublime.RegionFlags.DRAW_STIPPLED_UNDERLINE, annotations=anns, annotation_color='lightgreen')


#-----------------------------------------------------------------------------------
class NotrGotoSectionCommand(sublime_plugin.TextCommand):
    ''' List all the tag(s) or sections(s) for user selection then open corresponding file. '''
    _sorted_tags = []
    _sorted_sec_names = []

    def run(self, edit, filter_by_tag):
        # sc.slog(sc.CAT_DBG, f'NotrGotoSectionCommand.run()')
        self._sorted_tags.clear()
        self._sorted_sec_names.clear()
        panel_items = []

        if filter_by_tag:
            # Sort by frequency.
            self._sorted_tags = [x[0] for x in sorted(_tags.items(), key=lambda x:x[1], reverse=True)]
            # Sort alphabetically.
            self._sorted_tags = sorted(_tags)

            for tag in self._sorted_tags:
                panel_items.append(sublime.QuickPanelItem(trigger=tag, annotation=f"qty:{_tags[tag]}", kind=sublime.KIND_AMBIGUOUS))
            self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_tag)
        else:  # all sections
            n = []
            for section in _sections:
                n.append(f'{section.froot}#{section.name}')
            self._sorted_sec_names = sorted(n)
            for sec_name in self._sorted_sec_names:
                panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
            self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_section)

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
                self.view.window().run_command("hide_overlay")
                panel_items = []
                for sec_name in self._sorted_sec_names:
                    panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
                self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_section)
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
                    vnew = sc.wait_load_file(self.view.window(), section.srcfile, section.line)
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
        ref_text = _get_selection_for_scope(self.view, 'markup.link.refname.notr')
        valid = True

        if '#' in ref_text:  # Section ref like  [*#Links and Refs]  [* file_root#section_name]
            froot = None
            ref_name = None
            ref_parts = ref_text.split('#')

            if len(ref_parts) == 2:
                froot = ref_parts[0].strip()
                ref_name = ref_parts[1].strip()

                if len(froot) == 0:
                    # It's this file.
                    froot = os.path.basename(os.path.splitext(self.view.file_name())[0])
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
                sc.slog(sc.CAT_ERR, f'Invalid reference in {self.view.file_name()} name:{ref_name}')

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

    def run(self, edit, style):  # 1-4
        v = self.view
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
        visual_line_length = settings.get('visual_line_length')

        lchar = 'X'  # default
        if style == 1:
            lchar = '-'
        elif style == 1:
            lchar = '='
        elif style == 1:
            lchar = '+'

        # Start of current line.
        lst = v.line(v.sel()[0].a)

        s = lchar * visual_line_length + '\n'
        v.insert(edit, lst.a, s)

    def is_visible(self):
        return self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrInsertLinkCommand(sublime_plugin.TextCommand):
    ''' Insert link from clipboard. Assumes user clipped appropriate string. '''

    def run(self, edit):
        v = self.view
        s = f'[name?: {sublime.get_clipboard()}]'
        v.insert(edit, v.sel()[0].a, s)

    def is_visible(self):
        return self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrInsertRefCommand(sublime_plugin.TextCommand):
    ''' Insert ref from list of known refs. '''
    _sorted_refs = []

    def run(self, edit):
        # sc.slog('!!!', f'NotrInsertRefCommand()')
        self._sorted_refs.clear()
        panel_items = []

        # Collect all possible refs.
        n = []
        for section in _sections:
            n.append(f'{section.froot}#{section.name}')
        for link in _links:
            n.append(f'{link.name}')

        self._sorted_refs = sorted(n)

        for sec_name in self._sorted_refs:
            panel_items.append(sublime.QuickPanelItem(trigger=sec_name, kind=sublime.KIND_AMBIGUOUS))
        self.view.window().show_quick_panel(panel_items, on_select=self.on_sel_ref)

    def on_sel_ref(self, *args, **kwargs):
        sel = args[0]
        if sel >= 0:
            v = self.view
            # s = f'[*{self._sorted_refs[sel]}]'
            s = f'[*{self._sorted_refs[sel]}]'
            v.run_command("insert", {"characters": f'{s}'})  # Insert in created view
            # v.insert(edit, v.sel()[0].a, s)
        else:
            # Stick them in the clipboard.
            sublime.set_clipboard('\n'.join(self._sorted_refs))

    def is_visible(self):
        return self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrToHtmlCommand(sublime_plugin.TextCommand):
    ''' Make an html file. TODO2 useful? Sbot render doesn't pick up user_hl, underline, annotations. '''

    def run(self, edit, line_numbers):
        pass

    def is_visible(self):
        return self.view.syntax().name == 'Notr'


#-----------------------------------------------------------------------------------
class NotrDumpCommand(sublime_plugin.TextCommand):
    ''' Diagnostic. '''

    def run(self, edit):
        text = []
        text.append('=== _sections ===')
        for x in _sections:
            text.append(str(x))

        text.append('=== _links ===')
        for x in _links:
            text.append(str(x))

        text.append('=== _tags ===')
        for x in _tags:
            text.append(f'{x}:{_tags[x]}')

        text.append('=== _refs ===')
        for x in _refs:
            text.append(str(x))

        sc.create_new_view(self.view.window(), '\n'.join(text))


#-----------------------------------------------------------------------------------
def _get_selection_for_scope(view, scope):
    ''' If the current region includes the scope return it otherwise None. '''

    sel_text = None
    scopes = view.scope_name(view.sel()[-1].b).rstrip().split()
    if scope in scopes:
        reg = view.expand_to_scope(view.sel()[-1].b, scope)
        if reg is not None:
            sel_text = view.substr(reg).strip()

    return sel_text


#-----------------------------------------------------------------------------------
def _process_notr_files():
    ''' Get all ntr files and grab their goodies. '''

    _ntr_files.clear()
    _tags.clear()
    _refs.clear()
    _sections.clear()
    _links.clear()

    # Open and process notr files.
    settings = sublime.load_settings(NOTR_SETTINGS_FILE)
    notr_paths = settings.get('notr_paths')
    for npath in notr_paths:
        if os.path.exists(npath):
            for nfile in glob.glob(os.path.join(npath, '*.ntr')):
                _ntr_files.append(nfile)
                _process_notr_file(nfile)

    # TODO1 check that all collected links and refs are valid. Check for duplicate refs.


#-----------------------------------------------------------------------------------
def _process_notr_file(fn):
    ''' Regex and process sections and links. '''
    try:
        with open(fn, 'r') as file:
            lines = file.read().splitlines()
            line_num = 1

            # Get the things of interest defined in the file.
            re_links = re.compile(r'\[([^:]*): *([^\]]*)\]')
            re_refs = re.compile(r'\[\* *([^\]]*)\]')
            re_sections = re.compile(r'^(#+) +([^\[]+) *(?:\[(.*)\])?')

            for line in lines:
                # Links
                matches = re_links.findall(line)
                for m in matches:
                    if len(m) == 2:
                        name = m[0].strip()
                        target = m[1].strip()
                        # sc.slog('LNK', m)
                        _links.append(Link(fn, name, target))
                    else:
                        sc.slog(sc.CAT_ERR, f'Invalid syntax in {fn} line {line_num}')

                # Refs
                matches = re_refs.findall(line)
                for m in matches:
                    # sc.slog('REF', m)
                    # name = m[0].strip()
                    _refs.append(m)

                # Sections
                matches = re_sections.findall(line)
                for m in matches:
                    if len(m) == 3:
                        # sc.slog('SEC', m)
                        hashes = m[0].strip()
                        name = m[1].strip()
                        tags = m[2].strip().split()
                        froot = os.path.basename(os.path.splitext(fn)[0])
                        _sections.append(Section(fn, line_num, froot, len(hashes), name, tags))
                        for tag in tags:
                            _tags[tag] = _tags[tag] + 1 if tag in _tags else 1
                    else:
                        sc.slog(sc.CAT_ERR, f'Invalid syntax in {fn} line {line_num}')

                line_num += 1                    

    except Exception as e:
        sc.slog(sc.CAT_ERR, f'{e}')
        raise
