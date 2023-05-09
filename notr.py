import os
import math
import textwrap
import pathlib
import webbrowser
import html
import sublime
import sublime_plugin
from .sbot_common import *

NOTR_SETTINGS_FILE = "Notr.sublime-settings"

''' Tool:
- cut/copy/paste/move section/heading
- folding by section
- heading nav pane goto anything?
- search by heading tags

- insert link to a heading in this or other doc
- phun with phantoms?
- paste file/url from clipboard

- change list item state
- auto-indent on return

- table manipulations similar to csvplugin. Autofit.

- insert line (type) [setting for length]

- unicode menu/picker to insert, show at caret, ... maybe a new module. see unicode.py.

- render?

'''

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

'''
#-----------------------------------------------------------------------------------
class NotrToHtmlCommand(sublime_plugin.TextCommand):
    ''' Make a pretty. '''
    # Steal from / combine with render.


    _rows = 0
    _row_num = 0
    _line_numbers = False

    def run(self, edit, line_numbers):
        self._line_numbers = line_numbers
        settings = sublime.load_settings(NOTR_SETTINGS_FILE)
