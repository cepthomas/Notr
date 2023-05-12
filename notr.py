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
- TODO folding by section - Default.fold.py? folding.py?
- TODO nav pane (like word-ish and/or goto anything):
    - with files/sections
    - drag/move section
    - search by section tags
    - context click to open/goto linked uri/file/notr section
- TODO context insert link/reference in this or other doc, paste file/url from clipboard
- TODO Block "comment/uncomment" useful? What would that mean? Insert string from settings? Like # or // or...
- TODO insert visual-line (type) - needs setting for length
- TODO table manipulations similar to csvplugin: Autofit/justify.
'''


#-----------------------------------------------------------------------------------
def plugin_loaded():
    slog(CAT_DBG, 'plugin_loaded()')


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    slog(CAT_DBG, 'plugin_unloaded()')


#-----------------------------------------------------------------------------------
class NotrEvent(sublime_plugin.EventListener):

    # Need to track what's been initialized.
    # _views_inited = set()
    # User higlight word selection mode. From settings?
    _whole_word = True

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Views are all valid so init them. '''
        slog(CAT_DBG, f'on_init() {views}')
        # settings = sublime.load_settings(NOTR_SETTINGS_FILE)
        # user_hl = settings.get('user_hl')
        for view in views:
            self._init_user_hl(view)

    # def on_load_project(self, window):
    #     ''' This gets called for new windows but not for the first one. No views yet. '''
    #     slog(CAT_DBG, f'on_load_project() {window.views()}')
    #     for view in window.views():
    #         self._init_user_hl(view)

    def on_load(self, view):
        ''' Load a new file. View is valid so init it. '''
        slog(CAT_DBG, f'on_load() {view}')
        self._init_user_hl(view)

    def _init_user_hl(self, view):
        ''' Add any user highlights. '''
        if view.is_scratch() is False and view.file_name() is not None and view.syntax().name == 'Notr':
            settings = sublime.load_settings(NOTR_SETTINGS_FILE)
            user_hl = settings.get('user_hl')

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
                        if self._whole_word:  # and escaped[0].isalnum():
                            escaped = r'\b%s\b' % escaped
                        regs = view.find_all(escaped) if self._whole_word else view.find_all(token, sublime.LITERAL)
                        hl_regions.extend(regs)

                    if len(hl_regions) > 0:
                        anns = []
                        for reg in hl_regions:
                            anns.append(f'ann=={reg.to_tuple()}')
                            # anns.append(f'<body><style> p background-color:pink </style><p>{reg}</p></body>')

                        view.add_regions(key=region_name, regions=hl_regions, scope=f'markup.user_hl{i+1}.notr',
                            icon='dot', flags=sublime.RegionFlags.DRAW_STIPPLED_UNDERLINE, annotations=anns, annotation_color='lightgreen')
                            # TODO something fun with icon and annotations?




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
