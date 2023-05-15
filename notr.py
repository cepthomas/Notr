import os
import math
import textwrap
import pathlib
import webbrowser
import html
import re
import glob
import collections
from enum import Enum
import sublime
import sublime_plugin
from .sbot_common import *

NOTR_SETTINGS_FILE = "Notr.sublime-settings"

''' 

- TODO folding by section - Default.fold.py? folding.py?

- TODO? context-insert
    - visual-line (type) - needs setting for length. others: table(W, H), link,...
    - insert link from clip [TODO: <clip>]
    - insert ref from clip *[<clip>]
    - insert ref from list of known refs

- TODO bug render html from .ntr doesn't pick up user_hl. .md does. also underline.

- TODO table manipulations similar to csvplugin. insert(W, H), autofit/justify, add/delete row(s)/col(s)

'''


#-----------------------------------------------------------------------------------

# Fully qualified paths.
_ntr_files = []

# LinkType = Enum('LinkType', ['WEB', 'NTR', 'IMAGE', 'FILE', 'OTHER'])
Section = collections.namedtuple('Section', 'srcfile, line, level, name, tags')
Link = collections.namedtuple('Link', 'srcfile, name, target')
# Ref = collections.namedtuple('Ref', 'srcfile, name')

# All Sections in all files.
_sections = []
# All Links in all files.
_links = []
# _refs = []
# All unique tags. Value is count.
_all_tags = {}

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

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. '''
        # slog(CAT_DBG, f'on_init() {views}')

        _ntr_files.clear()
        _tags.clear()

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

        try:
            with open(fn, 'r') as file:
                lines = file.read().splitlines()
                line_num = 1

                # Get the things of interest defined in the file.
                re_links = re.compile(r'\[([^:]*): *([^\]]*)\]')
                re_sections = re.compile(r'^(#+) +([^\[]+) *(?:\[(.*)\])?')

                for line in lines:
                    matches = re_links.findall(line)
                    for m in matches:
                        if len(m) == 2:
                            name = m[0].strip()
                            target = m[1].strip()
                            if name != '*': # link
                                # slog('LNK', m)
                                _links.append(Link(fn, name, target))
                            else: # ref
                                # refs get handled at run time
                                # slog('REF', m)
                                pass
                        else:
                            sublime.error_message(f'Invalid syntax in {fn} line{line_num}')

                    matches = re_sections.findall(line)
                    for m in matches:
                        if len(m) == 3:
                            # slog('SEC', m)
                            hashes = m[0].strip()
                            name = m[1].strip()
                            tags = m[2].strip().split()
                            _sections.append(Section(fn, line_num, len(hashes), name, tags))
                            # slog('!!!', tags)
                            for tag in tags:
                                _all_tags[tag] = _all_tags[tag] + 1 if tag in _all_tags else 1
                        else:
                            sublime.error_message(f'Invalid syntax in {fn} line{line_num}')

                    line_num += 1                    
                # slog('!!!', _all_tags)

        except Exception as e:
            raise
            slog(CAT_ERR, f'{e}')

    def _init_user_hl(self, view):
        ''' Add any user highlights. '''
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
                            anns.append(f'Region: {reg.a}->{len(reg)}') # TODO remove/relocate.

                        view.add_regions(key=region_name, regions=hl_regions, scope=f'markup.user_hl{i+1}.notr',
                            icon='dot', flags=sublime.RegionFlags.DRAW_STIPPLED_UNDERLINE, annotations=anns, annotation_color='lightgreen')

    def _process_notr_file_not(self, fn):
        ''' Load file into a hidden view and process links. '''
        # https://forum.sublimetext.com/t/is-it-possible-to-open-a-file-without-showing-it-to-the-user/35884/3
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
class NotrOpenRefCommand(sublime_plugin.TextCommand):
    ''' Do something. Talk about it. '''

    def run(self, edit):
        v = self.view
        scope = v.scope_name(v.sel()[-1].b).rstrip()
        scopes = scope.split()
        slog('!!!', f'scopes:{scopes}')
        if 'markup.link.refname.notr' in scopes:
            reg = v.expand_to_scope(v.sel()[-1].b, 'markup.link.refname.notr')
            if reg is not None:
                refname = v.substr(reg).strip()
                if '#' in refname:
                    # Section ref
                    ref_parts = refname.split('#')
                    ref = ref_parts[1] if len(ref_parts) > 1 else ref_parts[0]

                    pass
                else:
                    # Link ref
                    pass

    def is_visible(self):
        return True
        # return self.view.settings().get('syntax') == SYNTAX_XML


#-----------------------------------------------------------------------------------
class NotrAllTagsCommand(sublime_plugin.TextCommand):
    ''' Do something. Talk about it. '''

    def run(self, edit):
        slog('!!!', f'_all_tags:{_all_tags}')

    def is_visible(self):
        return True


#-----------------------------------------------------------------------------------
class NotrFindTagsCommand(sublime_plugin.TextCommand):
    ''' Do something. Talk about it. '''

    def run(self, edit):
        pass

    def is_visible(self):
        return True
        # return self.view.settings().get('syntax') == SYNTAX_XML


#-----------------------------------------------------------------------------------
class NotrYayaCommand(sublime_plugin.TextCommand):
    ''' Do something. Talk about it. '''

    def run(self, edit, arg_1):
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
        # return self.view.settings().get('syntax') == SYNTAX_XML







'''
- Matching pairs «»‹›“”‘’〖〗【】「」『』〈〉《》〔〕
- Currency  ¤ $ ¢ € ₠ £ ¥
- Common symbols © ® ™ ² ³ § ¶ † ‡ ※
- Bullets •◦ ‣ ✓ ●■◆ ○□◇ ★☆ ♠♣♥♦ ♤♧♡♢
- Music ♩♪♫♬♭♮♯
- Punctuation “” ‘’ ¿¡ ¶§ª - ‐ ‑ ‒ – — ― …
- Accents àáâãäåæç èéêë ìíîï ðñòóôõö øùúûüýþÿ ÀÁÂÃÄÅ Ç ÈÉÊË ÌÍÎÏ ÐÑ ÒÓÔÕÖ ØÙÚÛÜÝÞß 
- Math ° ⌈⌉ ⌊⌋ ∏ ∑ ∫ ×÷ ⊕ ⊖ ⊗ ⊘ ⊙ ⊚ ⊛ ∙ ∘ ′ ″ ‴ ∼ ∂ √ ≔ × ⁱ ⁰ ¹ ² ³ ₀ ₁ ₂ π ∞ ± ∎
- Logic & Set Theory ∀¬∧∨∃⊦∵∴∅∈∉⊂⊃⊆⊇⊄⋂⋃
- Relations ≠≤≥≮≯≫≪≈≡
- Sets ℕℤℚℝℂ
- Arrows ←→↑↓ ↔ ↖↗↙↘  ⇐⇒⇑⇓ ⇔⇗  ⇦⇨⇧⇩ ↞↠↟↡ ↺↻  ☞☜☝☟
- Computing ⌘ ⌥ ‸ ⇧ ⌤ ↑ ↓ → ← ⇞ ⇟ ↖ ↘ ⌫ ⌦ ⎋⏏ ↶↷ ◀▶▲▼ ◁▷△▽ ⇄ ⇤⇥ ↹ ↵↩⏎ ⌧ ⌨ ␣ ⌶ ⎗⎘⎙⎚ ⌚⌛ ✂✄ ✉✍
- Digits ➀➁➂➃➄➅➆➇➈➉
- Religious and cultural symbols ✝✚✡☥⎈☭☪☮☺☹☯☰☱☲☳☴☵☶☷
- Dingbats ❦☠☢☣☤♲♳⌬♨♿ ☉☼☾☽ ♀♂ ♔♕♖ ♗♘♙ ♚♛ ♜♝♞♟

http://xahlee.info/comp/unicode_computing_symbols.html
⌘ ✲ ⎈ ^ ⌃ ❖ ⎇ ⌥ ⇮ ◆ ◇ ✦ ✧ ⇧ ⇪ 🄰 🅰 ⇪ ⇬ 🔠 🔡 ⇭ 🔢 🔤 ↩ ↵ ⏎ ⌤ ⎆ ▤ ☰ 𝌆 ⎄ ⭾ ↹ ⇄ ⇤ ⇥ ↤ ↦ ⎋ ⌫ ⟵ ⌦ ⎀ ⎚ ⌧ ↖ ↘ ⇤ ⇥ ⤒ ⤓ ⇞ ⇟ △ ▽ ▲ ▼ ⎗ ⎘ ↑ ↓ ← → ◀ ▶ ▲ ▼ ◁ ▷ △ ▽ ⇦ ⇨ ⇧ ⇩ ⬅ ➡ ⮕ ⬆ ⬇ ⎉ ⎊ ⎙ ⍰ ❓ ❔ ℹ 🛈 ☾ ⏏ ✉ 🏠 🏡 ⌂ ✂ ✄ ⎌ ↶ ↷ ⟲ ⟳ ↺ ↻ 🔍 🔎 🔅 🔆 🔇 🔈 🔉 🔊 🕨 🕩 🕪 ◼ ⏯ ⏮ ⏭ ⏪ ⏩ ⏫ ⏬ 🌐

- github-unicode-?
You can use either decimal or hex code point or HTML entity name (if exists) of a unicode character:
`&#8364; &#x20AC; &euro; displays as â‚¬ â‚¬ â‚¬`

'''
