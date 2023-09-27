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

# TODO highlight links in lists like [nyt](https://nytimes.com). See \sublime\md\Markdown.sublime-syntax  link-inline
# TODO Make into package when it's cooked. Maybe others. https://packagecontrol.io/docs/submitting_a_package.
# TODO Parse md files too?


#--------------------------- Types -------------------------------------------------

# One section:
# srcfile=ntr file path
# line=ntr file line
# froot=ntr file name root
# level=1-N (not used now)
# name=section title
# tags[]
# Section = collections.namedtuple('Section', 'srcfile, line, froot, level, name, tags')

# One link:
# srcfile=ntr file path
# line=ntr file line
# name=desc text
# target=clickable uri or file
# Link = collections.namedtuple('Link', 'srcfile, line, name, target')

# One reference:
# name=section or link name
# srcfile=ntr file path
# line=ntr file line
Ref = collections.namedtuple('Ref', 'name, srcfile, line')

########### new ##############
# Target = collections.namedtuple('Target', 'type, name, froot, level, tags, srcfile, line')
Target = collections.namedtuple('Target', 'type, name, resource, level, tags, srcfile, line')
# type: section, uri, image?, other/file
# srcfile=ntr file path
# line=ntr file line
# froot=ntr file name root
# level: section only
# name=section title
# tags[]  tags for links?


# name = froot#section_title | #section_title | user_assigned
# resource = fn | uri | ???



# All Targets found in all ntr files.
_targets = []


#---------------------------- Globals -----------------------------------------------
# Some could be multidict?

# All Sections found in all ntr files - in order to support hierarchy.
# _sections = []

# All Links found in all ntr files.
# _links = []

# All Refs found in all ntr files.
_refs = []

# All valid ref targets in _sections and _links.
# _valid_ref_targets = {}

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
class NotrGotoTargetCommand(sublime_plugin.WindowCommand):
    ''' List all the tag(s) and/or target(s) for user selection then open corresponding file. '''

    # Prepared lists for quick panel.
    _sorted_tags = []
    _sorted_targets = []

    def run(self, filter_by_tag):
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
            self.window.show_quick_panel(panel_items, on_select=self.on_sel_tag)
        else:
            self.show_targets(_targets)

    def on_sel_tag(self, *args, **kwargs):
        sel = args[0]

        if sel >= 0:
            # Make a selector with sorted target names, current file's first.
            sel_tag = self._sorted_tags[sel]

            # Hide current quick panel.
            self.window.run_command("hide_overlay")

            # Filter per tag selection.
            filtered_targets = []
            for target in _targets:
                if sel_tag in target.tags:
                    filtered_targets.append(target)

            if len(filtered_targets) > 0:
                self.show_targets(filtered_targets)
            else:
                sublime.status_message('No targets with that tag')

    def on_sel_target(self, *args, **kwargs):
        sel = args[0]

        if sel >= 0:
            # Locate the target record.
            target = self._sorted_targets[sel]
            # Open the target in a new view.
            sc.wait_load_file(self.window, target.srcfile, target.line)

    def show_targets(self, targets):
        ''' Present target options to user. '''

        current_file_targets = []
        other_targets = []
        panel_items = []
        current_file = self.window.active_view().file_name()

        for target in targets:
            if current_file is not None and os.path.samefile(target.srcfile, current_file):
                current_file_targets.append(target)
            else:
                other_targets.append(target)

        # Sort them all.
        current_file_targets = sorted(current_file_targets)
        other_targets = sorted(other_targets)

        # Make readable names.
        for target in current_file_targets:
            panel_items.append(sublime.QuickPanelItem(trigger=f'#{target.name}', kind=sublime.KIND_AMBIGUOUS))
        for target in other_targets:
            panel_items.append(sublime.QuickPanelItem(trigger=f'{target.froot}#{target.name}', kind=sublime.KIND_AMBIGUOUS))
        # Combine the two.
        self._sorted_targets = current_file_targets + other_targets

        self.window.show_quick_panel(panel_items, on_select=self.on_sel_target)

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

        if tref is not None:  # explicit ref.
            # Get the corresponding target spec. TODO should be a dict?
            for target in _targets:
                valid = False
                if target.name == tref:
                    try:
                        tname = None
                        if target.type == "section":
                            # Open the notr file and position it.
                            sc.wait_load_file(self.view.window(), target.srcfile, target.line)
                            valid = True
                        elif target.type == "image":
                            tname = target.name
                        elif target.type == "uri":
                            tname = target.name
                        elif target.type == "other":
                            tname = target.name

                        if tname is not None:
                            if platform.system() == 'Darwin':
                                ret = subprocess.call(('open', target.resource))
                            elif platform.system() == 'Windows':
                                os.startfile(target.resource)
                            else:  # linux variants
                                ret = subprocess.call(('xdg-open', target.resource))
                            valid = True
                    except Exception as e:
                        if e is None:
                            sc.slog(sc.CAT_ERR, "???")
                        else:
                            sc.slog(sc.CAT_ERR, e)
                    break

            if not valid:
                sc.slog(sc.CAT_ERR, f'Invalid reference: {self.view.file_name()} :{ref_name}')

        else:

            # TODO only if scope is _ref else show _valid_ref_targets like notr_insert_ref. Or combine with notr_goto_target.

            self.refs = _get_valid_refs(True)
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
                if target.name == tref: #TODO dupe code - refactor, maybe common
                    try:
                        tname = None
                        if target.type == "section":
                            # Open the notr file and position it.
                            sc.wait_load_file(self.view.window(), target.srcfile, target.line)
                            valid = True
                        elif target.type == "image":
                            tname = target.name
                        elif target.type == "uri":
                            tname = target.name
                        elif target.type == "other":
                            tname = target.name

                        if tname is not None:
                            if platform.system() == 'Darwin':
                                ret = subprocess.call(('open', target.resource))
                            elif platform.system() == 'Windows':
                                os.startfile(target.resource)
                            else:  # linux variants
                                ret = subprocess.call(('xdg-open', target.resource))
                            valid = True
                    except Exception as e:
                        if e is None:
                            sc.slog(sc.CAT_ERR, "???")
                        else:
                            sc.slog(sc.CAT_ERR, e)
                    break


        # if ref_text is not None and '#' in ref_text:  # TODO Section ref like  [*#Links and Refs]  [* file_root#section_name]
        #     froot = None
        #     ref_name = None
        #     ref_parts = ref_text.split('#')

        #     if len(ref_parts) == 2:
        #         froot = ref_parts[0].strip()
        #         ref_name = ref_parts[1].strip()

        #         if len(froot) == 0:
        #             # It's this file.
        #             froot = _get_froot(self.view.file_name())
        #     else:
        #         valid = False

        #     # Get the Section spec.
        #     if valid:
        #         valid = False
        #         for target in _targets:
        #             if target.froot == froot and target.name == ref_name:
        #                 # Open the file and position it.
        #                 sc.wait_load_file(self.view.window(), target.srcfile, target.line)
        #                 valid = True
        #                 break

        #     if not valid:
        #         sc.slog(sc.CAT_ERR, f'Invalid reference: {self.view.file_name()} :{ref_name}')

        # else:  # Link ref
        #     # Get the Link spec.
        #     for target in _targets:  # links: TODO
        #         if target.name == ref_text:
        #             try:
        #                 if platform.system() == 'Darwin':
        #                     ret = subprocess.call(('open', target.target))
        #                 elif platform.system() == 'Windows':
        #                     os.startfile(target.target)
        #                 else:  # linux variants
        #                     ret = subprocess.call(('xdg-open', target.target))
        #             except Exception as e:
        #                 if e is None:
        #                     sc.slog(sc.CAT_ERR, "???")
        #                 else:
        #                     sc.slog(sc.CAT_ERR, e)
        #             break

    # def is_visible(self):
    #     return _get_selection_for_scope(self.view, 'markup.link.refname.notr') is not None


#-----------------------------------------------------------------------------------
class NotrInsertRefCommand(sublime_plugin.TextCommand):
    ''' Insert ref from list of known refs. '''
    refs = []

    def run(self, edit):
        self.refs = _get_valid_refs(True)
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
        v = self.view
        return v.syntax() is not None and v.syntax().name == 'Notr' and sc.get_single_caret(v) is not None


#-----------------------------------------------------------------------------------
class NotrInsertLinkCommand(sublime_plugin.TextCommand):
    ''' Insert link from clipboard. Assumes user clipped appropriate string. '''

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
# class NotrPublishCommand(sublime_plugin.WindowCommand):
#     ''' TODO Publish notes somewhere for access from internet/phone - raw or rendered. refs should be Links. Nothing confidential! Android OneDrive doesn't recognize .ntr files'''

#     #### Render for android target.
#     # self.window.active_view().run_command('sbot_render_to_html', {'font_face':'monospace', 'font_size':'1.2em' } )  

#     def run(self):
#         # Render notr files.
#         # Render for android target.
#         # self.window.active_view().run_command('sbot_render_to_html', {'font_face':'monospace', 'font_size':'1.2em' } )  
#         pass

#     def is_visible(self):
#         return True


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
            text.append(f'\n===== {name} =====')
            text.extend([str(x) for x in coll])

        # do_one('sections', _sections)
        # do_one('links', _links)
        do_one('targets', _targets)
        do_one('refs', _refs)
        # do_one('valid_ref_targets', _valid_ref_targets)
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

    # _sections.clear()
    # _links.clear()
    # _valid_ref_targets.clear()
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
                if index_path is None or not os.path.samefile(nfile, index_path):  # don't do index twice
                    _ntr_files.append(nfile)
        else:
            _user_error(NOTR_SETTINGS_FILE, -1, f'Invalid path in settings {npath}')

    # Process the files.
    for nfile in _ntr_files:
        _process_notr_file(nfile)

    # Check all user refs are valid -> (froot)#target or link.name, no dupes.
    valid_refs = _get_valid_refs(False)
    for ref in _refs:
        if ref.target not in valid_refs:
            _user_error(ref.srcfile, ref.line, f'Invalid ref target:{ref.target}')

    if len(_parse_errors) > 0:
        _parse_errors.insert(0, "Errors in your configuration:")
        sc.create_new_view(window, '\n'.join(_parse_errors))

    # ### Check sanity of collected material.

    # # Add sections to list.
    # for section in _sections:
    #     target = f'{section.froot}#{section.name}'
    #     if target not in _valid_ref_targets:
    #         _valid_ref_targets[target] = f'{section.srcfile}({section.line})'
    #     else:
    #         _user_error(section.srcfile, section.line, f'Duplicate section name:{section.name} see:{_valid_ref_targets[target]}')

    # # Add links to list. Check valid 'http(s)://' or file, no dupe names.
    # for link in _links:
    #     if link.name in _valid_ref_targets:
    #         _user_error(link.srcfile, link.line, f'Duplicate link name:{link.name} see:{_valid_ref_targets[link.name]}')
    #     else:
    #         if link.target.startswith('http') or os.path.exists(link.target):
    #             # Assume a valid uri or path
    #             _valid_ref_targets[link.name] = f'{link.srcfile}({link.line})'
    #         else:
    #             _user_error(link.srcfile, link.line, f'Invalid link target:{link.target}')

    # # Check all user refs are valid -> (froot)#section or link.name, no dupes.
    # for ref in _refs:
    #     if ref.target not in _valid_ref_targets:
    #         _user_error(ref.srcfile, ref.line, f'Invalid ref target:{ref.target}')

    # if len(_parse_errors) > 0:
    #     _parse_errors.insert(0, "Errors in your configuration:")
    #     sc.create_new_view(window, '\n'.join(_parse_errors))


#-----------------------------------------------------------------------------------
def _get_valid_refs(sort):
    ''' Get all valid target for generating refs. '''

    # All valid ref targets.
    ref_targets = {}

    for target in _targets:
        tname = None

        if target.type == "section":
            tname = f'{target.froot}#{target.name}'
        elif target.type == "image":
            tname = target.name
        elif target.type == "uri":
            tname = target.name
        elif target.type == "other":
            tname = target.name
        else:
            pass # never happen

        if tname not in ref_targets:
            ref_targets[tname] = tname #f'{target.srcfile}({target.line})'
        else:
            _user_error(target.srcfile, target.line, f'Duplicate target name:{target.name} see:{ref_targets[tname]}')

    return sorted(ref_targets) if sort else ref_targets


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

            # Get the things of interest defined in the file. Grep escape these .^$*+?()[{\|  syntax uses X?!*
            re_directives = re.compile(r'^:(.*)')
            # re_directives = re.compile(r'^\$(.*)')
            re_links = re.compile(r'\[(.*)\]\((.*)\)')
            # re_links = re.compile(r'\[([^:]*): *([^\]]*)\]')
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
                        _user_error(fn, line_num, 'Invalid directive')

                # Links - also checks validity.
                matches = re_links.findall(line)
                for m in matches:
                    if len(m) == 2:
                        name = m[0].strip()
                        res = sc.expand_vars(m[1].strip())
                        if res is None:
                            # Bad env var.
                            _user_error(fn, line_num, f'Bad env var: {m[1]}')
                        else:
                            _, ext = os.path.splitext(fn)

                            ttype = None
                            if ext in IMAGE_TYPES:
                                ttype = "image"
                            elif fn.startswith('http'):
                                ttype = "uri"
                            elif os.path.exists(fn):
                                ttype = "other"
                            else:
                                _user_error(fn, line_num, f'Invalid target resource: {fn}')

                            if ttype is not None:
                                # froot = _get_froot(fn)
                                tags = []  # TODO? Support tags in links.
                                links.append(Target(ttype, name, res, 0, tags, fn, line_num))
                    else:
                        _user_error(fn, line_num, 'Invalid syntax')

                # Refs
                matches = re_refs.findall(line)
                for m in matches:
                    name = m.strip()
                    # If it's local section insert the froot.
                    if name.startswith('#'):
                        froot = _get_froot(fn)
                        name = froot + name
                    refs.append(Ref(name, fn, line_num))

                # Sections
                matches = re_sections.findall(line)
                for m in matches:
                    valid = True
                    if len(m) == 2:
                        content = m[0].strip().split(None, 1)
                        if len(content) == 2:
                            hashes = content[0].strip()
                            name = f'{_get_froot(fn)}#{content[1].strip()}'
                        else:
                            valid = False

                        if valid:
                            tags = m[1].strip().split()
                    else:
                        valid = False

                    if valid:
                        # sections.append(Section(fn, line_num, froot, len(hashes), name, tags))
                        sections.append(Target("section", name, "", len(hashes), tags, fn, line_num))
                        for tag in tags:
                            _tags[tag] = _tags[tag] + 1 if tag in _tags else 1
                    else:
                        _user_error(fn, line_num, 'Invalid syntax')

                line_num += 1

    except Exception as e:
        sc.slog(sc.CAT_ERR, f'Error processing {fn}: {e}')
        raise

    if not no_index:
        # _sections.extend(sections)
        # _links.extend(links)
        _targets.extend(sections)
        _targets.extend(links)
        _refs.extend(refs)


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
