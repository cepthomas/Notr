import os
import math
import textwrap
import pathlib
import webbrowser
import html
import re
import sublime
import sublime_plugin
from .sbot_common import *

NOTR_SETTINGS_FILE = "Notr.sublime-settings"

''' 
Tool:
    - TODO1 folding by section
    - TODO1 nav pane (like word-ish and/or goto anything):
        - with files/sections
        - drag/move section
        - search by section tags
    - TODO1 context:
        - click to open/goto linked uri/file/notr section
        - insert link/reference in this or other doc, paste file/url from clipboard
        ? change list item state
        - insert visual-line (type)
        - toggle syntax coloring - distraction-free
    - TODO2 image phantoms? hover/thumbnail? https://www.sublimetext.com/docs/minihtml.html
    - TODO2 table manipulations similar to csvplugin: Autofit/justify.
    - TODO2 unicode menu/picker to insert, show at caret.

settings:
    - visual-line length
    X auto-highlight keywords and colors
    ? render more like md
    ? unicode config
'''


#-----------------------------------------------------------------------------------
def plugin_loaded():
    slog(CAT_DBG, 'plugin_loaded')


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    slog(CAT_DBG, 'plugin_unloaded')



#-----------------------------------------------------------------------------------
class NotrEvent(sublime_plugin.EventListener):

    # Need to track what's been initialized.
    _views_inited = set()
    _whole_word = False # TODO2?

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Load the settings file. Views are valid. '''
        # slog(CAT_DBG, f'on_init {views[0]}')
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
        user_hl = settings.get('user_hl')
        for view in views:
            self._init_view(view)

    def on_load_project(self, window):
        ''' This gets called for new windows but not for the first one. '''
        # slog(CAT_DBG, f'on_load_project {window.views()[0]}')
        self._open_hls(window)
        for view in window.views():
            self._init_view(view)

    def on_load(self, view):
        ''' Load a file. '''
        # slog(CAT_DBG, f'on_load {view}')
        self._init_view(view)

    def _init_view(self, view):
        ''' Lazy init. '''
        fn = view.file_name()
        if view.is_scratch() is False and fn is not None:
            # Init the view if not already.
            vid = view.id()
            if vid not in self._views_inited and view.syntax().name == 'Notr':
                self._views_inited.add(vid)

                # Init the view with any user highligts.
                settings = sublime.load_settings(NOTR_SETTINGS_FILE)
                user_hl = settings.get('user_hl')

                if user_hl is not None:
                    # slog(CAT_DBG, f'{user_hl}')
                    for i in range(max(len(user_hl), 3)):
                        # slog(CAT_DBG, f'{user_hl[i]}')

                        highlight_regions = []
                        for token in user_hl[i]:
                            # slog(CAT_DBG, f'{i}:{token}')
                            # Colorize one token.
                            escaped = re.escape(token)
                            if self._whole_word:  # and escaped[0].isalnum():
                                escaped = r'\b%s\b' % escaped
                            regs = view.find_all(escaped) if self._whole_word else view.find_all(token, sublime.LITERAL)
                            highlight_regions.extend(regs)

                        if len(highlight_regions) > 0:
                            view.add_regions(f'userhl_{i+1}_region', highlight_regions, f'markup.user_hl{i+1}.notr') #TODO2 seems to be only color not style.


''' unicode
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
