import os
# import math
# import textwrap
# import pathlib
# import webbrowser
# import html
import subprocess
import re
import glob
import collections
# from enum import Enum
import sublime
import sublime_plugin
from .sbot_common import *

NOTR_SETTINGS_FILE = "Notr.sublime-settings"

''' 

- TODO? look at other plugins:
    - linter code to see what they do
    - Sublime Markdown Popups (mdpopups) is a library for Sublime Text plugins.  It utilizes the new plugin API found in ST3
        3080+ for generating tooltip popups. It also provides API methods for generating and styling the new phantom elements
        introduced in ST3 3118+.  Mdpopups utilizes Python Markdown with a couple of special extensions to convert Markdown to
        HTML that can be used to create the popups and/or phantoms.  It also provides a number of other helpful API commands to
        aid in creating great tooltips and phantoms.
        Mdpopups will use your color scheme to create popups/phantoms that fit your editors look.

- TODO folding by section - Default.fold.py? folding.py?

- TODO? tables
    - insert table = notr_insert_table(w, h)
    - table autofit/justify - notr_justify_table
    - table add/delete row(s)/col(s) ?

- TODO? odds and ends
    - Block comment/uncomment useful? What would that mean - "hide" text? Insert string (# or //) from settings.
    - LMH Priorities (for searching) or could be tag.

- TODO bug: render html from .ntr doesn't pick up user_hl. .md does. also underline.

'''



#-----------------------------------------------------------------------------------

# All ntr files, fully qualified paths.
_ntr_files = []

# LinkType = Enum('LinkType', ['WEB', 'NTR', 'IMAGE', 'FILE', 'OTHER'])

# One section: ntr file path, ntr file line, ntr file name root, level 1-N, name/id, list of tags
Section = collections.namedtuple('Section', 'srcfile, line, froot, level, name, tags')

# One link: ntr file path, name/id, uri/file
Link = collections.namedtuple('Link', 'srcfile, name, target')

# Ref = collections.namedtuple('Ref', 'srcfile, name')

# All Sections in all files. TODO multidict?
_sections = []

# All Links in all files. TODO multidict?
_links = []

# All ref strings in all files. Mainly used for ui list display or picker.
_refs = {}

# All unique tags. Value is count.
_tags = {}


#-----------------------------------------------------------------------------------
def plugin_loaded():
    # slog(CAT_DBG, 'plugin_loaded()')
    pass


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    # slog(CAT_DBG, 'plugin_unloaded()')
    pass


#-----------------------------------------------------------------------------------
class NotrEvent(sublime_plugin.EventListener):
    '''
    Process view events.
    '''

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. '''
        # slog(CAT_DBG, f'on_init() {views}')
        global _ntr_files, _tags, _refs, _sections, _links

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
                    self._process_notr_file(nfile)

        # Views are all valid so init them.
        for view in views:
            self._init_user_hl(view)

    def on_load(self, view):
        ''' Load a new file. View is valid so init it. '''
        # slog(CAT_DBG, f'on_load() {view}')
        self._init_user_hl(view)

    def _process_notr_file(self, fn):
        ''' Regex and process sections and links. '''
        # slog('!!!', f'regex fn:{fn}')
        global _ntr_files, _tags, _refs, _sections, _links

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
                            slog('LNK', m)
                            _links.append(Link(fn, name, target))
                        else:
                            sublime.error_message(f'Invalid syntax in {fn} line{line_num}')

                    # Refs
                    matches = re_refs.findall(line)
                    for m in matches:
                        slog('REF', m)
                        name = m[0].strip()
                        _refs[name] = 1

                    # Sections
                    matches = re_sections.findall(line)
                    for m in matches:
                        if len(m) == 3:
                            # slog('SEC', m)
                            hashes = m[0].strip()
                            name = m[1].strip()
                            tags = m[2].strip().split()
                            froot = os.path.basename(os.path.splitext(fn)[0])
                            # slog('!!!', froot)
                            _sections.append(Section(fn, line_num, froot, len(hashes), name, tags))
                            for tag in tags:
                                _tags[tag] = _tags[tag] + 1 if tag in _tags else 1
                        else:
                            sublime.error_message(f'Invalid syntax in {fn} line{line_num}')

                    line_num += 1                    
                # slog('!!!', _tags)

        except Exception as e:
            slog(CAT_ERR, f'{e}')
            raise

    def _init_user_hl(self, view):
        ''' Add any user highlights. '''
        #print(view.is_scratch(), view.file_name(), view.syntax().name())
        if view.is_scratch() is False and view.file_name() is not None and view.syntax().name() == 'Notr':
            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            user_hl = settings.get('user_hl')
            whole_word = settings.get('user_hl_whole_word')

            if user_hl is not None:
                for i in range(max(len(user_hl), 3)):
                    # Clean first.r
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

    def _process_notr_file_not_not_not(self, fn):
        '''
        Load file into a hidden view and process links.
        https://forum.sublimetext.com/t/is-it-possible-to-open-a-file-without-showing-it-to-the-user/35884/3
        '''
        # slog('!!!', f'fn:{fn}')

        try:
            with open(fn, 'r') as file:
                content = file.read()
                view = sublime.active_window().create_output_panel('_ntr_tmp', True )
                view.run_command('append', {'characters': content})
                view.assign_syntax('Packages/Notr/Notr.sublime-syntax')
                # Get the links defined in the file.
                doc = sublime.Region(0, view.size())
                tokens = view.extract_tokens_with_scopes(doc)

        except Exception as e:
            # slog(CAT_ERR, f'{e}')
            pass


#-----------------------------------------------------------------------------------
class NotrInsertHruleCommand(sublime_plugin.TextCommand): # TODO
    ''' Insert visuals. '''

    def run(self, edit, style): # 1-4
        slog('!!!', f'NotrInsertHruleCommand')
        global _ntr_files, _tags, _refs, _sections, _links

        v = self.view
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
        visual_line_length = settings.get('visual_line_length')

        lchar = 'X' # default
        if style == 1: lchar = '-'
        elif style == 1: lchar = '='
        elif style == 1: lchar = '+'

        # Start of current line.
        lst = v.line(v.sel())[0]

        s = lchar * visual_line_length + '\n'
        v.insert(edit, lst, s)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrInsertLinkCommand(sublime_plugin.TextCommand): # TODO
    ''' insert link from clipboard. '''

    def run(self, edit):
        slog('!!!', f'NotrInsertLinkCommand')
        global _ntr_files, _tags, _refs, _sections, _links


    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrInsertRefCommand(sublime_plugin.TextCommand): # TODO
    ''' insert ref from list of known refs. '''

    def run(self, edit):
        slog('!!!', f'NotrInsertRefCommand')
        global _ntr_files, _tags, _refs, _sections, _links


    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrOpenRefCommand(sublime_plugin.TextCommand):
    ''' open link or section from selected ref: markup.link.refname.notr. '''

    def run(self, edit):
        ref_text = _get_selection_for_scope(self.view, 'markup.link.refname.notr')
        global _ntr_files, _tags, _refs, _sections, _links


        if '#' in ref_text:
            # Section ref like  [*#Links and Refs]  [* file_root#section_name]
            froot = None
            ref_name = None
            ref_parts = ref_text.split('#')
            if len(ref_parts) > 1:
                froot = ref_parts[0]
                ref_name = ref_parts[1]
            elif len(ref_parts) > 0:
                ref_name = ref_parts[0]
                froot = os.path.basename(os.path.splitext(self.view.file_name())[0])
            else:
                fn = '???'
                line_num = -1
                sublime.error_message(f'Invalid syntax in {fn} line{line_num}')

            # Get the Section spec.
            for section in _sections:
                if section.froot == froot:
                    # Open the file and position it.
                    vnew = self.view.window().open_file(section.srcfile)
                    while vnew.is_loading():
                        pass
                    vnew.run_command("goto_line", {"line": section.line})
                    break;
        else:
            # Link ref
            # Get the Link spec.
            for link in _links:
                if link.name == ref_text:
                    cmd = [link.target]
                    cp = subprocess.run(cmd, universal_newlines=True, capture_output=True, shell=True, check=True)
                    if(len(cp.stdout) > 0):
                        create_new_view(self.window, cp.stdout)
                    break

    def is_visible(self):
        return _get_selection_for_scope(self.view, 'markup.link.refname.notr') is not None


#-----------------------------------------------------------------------------------
class NotrAllTagsCommand(sublime_plugin.TextCommand): # TODO
    ''' find all sections with tag(s) - input? put in find pane. '''

    def run(self, edit):
        slog('!!!', f'_tags:{_tags}')
        global _ntr_files, _tags, _refs, _sections, _links


    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrFindSectionsCommand(sublime_plugin.TextCommand): # TODO
    ''' find all sections with tag(s) - input? put in find pane. TODO also wildcard search on name. '''

    def run(self, edit):
        global _ntr_files, _tags, _refs, _sections, _links
        pass

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrToHtmlCommand(sublime_plugin.TextCommand): # TODO
    ''' rendering. '''

    def run(self, edit, line_numbers):
        global _ntr_files, _tags, _refs, _sections, _links
        pass

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrYayaCommand(sublime_plugin.TextCommand): # TODO
    ''' Do something. Talk about it. '''

    def run(self, edit, arg_1):
        global _ntr_files, _tags, _refs, _sections, _links
        pass

        # settings = sublime.load_settings(HIGHLIGHT_SETTINGS_FILE)
        # highlight_scopes = settings.get('highlight_scopes')

        # # Get whole word or specific span.
        # region = self.view.sel()[0]

        # whole_word = region.empty()
        # if whole_word:
        #     region = self.view.word(region)
        # token = self.view.substr(region)

        # arg_1 %= len(highlight_scopes)
        # scope = highlight_scopes[arg_1]
        # hl_vals = _get_hl_vals(self.view, True)

        # if hl_vals is not None:
        #     hl_vals[scope] = {"token": token, "whole_word": whole_word}
        # _highlight_view(self.view, token, whole_word, scope)

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
def _get_selection_for_scope(view, scope):
    ''' If the current selection includes the scope return it otherwise None. '''

    sel_text = None
    scopes = view.scope_name(view.sel()[-1].b).rstrip().split()
    # slog('!!!', f'scopes:{scopes}')
    if scope in scopes:
        reg = view.expand_to_scope(view.sel()[-1].b, scope)
        if reg is not None:
            sel_text = view.substr(reg).strip()

    return sel_text
