# Notr

Sublime Text plugin for managing collections of notes. Note files have the extension `.ntr` and the corresponding markup syntax
provides file and section navigation and colorizing to provide visual clues for things like sections, links, tables, lists, etc.
It is a plain text format with a lot of similarity to markdown but is not intended to be rendered into a publication - the text
itself is the whole point of this.

Built for ST4 on Windows and Linux.

## Features

- Sections with tags
- Various text decorations
- Targets and references - targets can be section, file (image or other), uri
- Lists
- Tables - fit, sort, etc (could be ported for general purpose md use)
- Auto highlight - supplements [SbotHighlight](https://github.com/cepthomas/SbotHighlight)
- Render to html with [SbotRender](https://github.com/cepthomas/SbotRender)


## Demo

[The spec](test_files/notr-spec.ntr) provides an example of the features. If the plugin is installed it will look
something like this (uses my color scheme):

![ex1](test_files/ex1.jpg)

![ex2](test_files/ex2.jpg)

To run the demo:
- Install the plugin.
- Open `Preferences->Package Settings->Notr`.
- Edit to something like this:
```
{
    "notr_paths": [
        ".../Sublime Text/Packages/Notr/test_files",
    ],
    "notr_index": ".../Sublime Text/Packages/Notr/test_files/test-index.ntr",
    "fixed_hl": [
        ["2DO", "and_a"],
        ["user", "and_b"],
        ["dynamic", "and_c"],
    ],
}
```

- Color schemes require new and edited scopes to support this tool. They are identified in `test_files/NotrOverlay.sublime-color-scheme`.
  Implement your unique version of this per [Color customization](https://www.sublimetext.com/docs/color_schemes.html#customization).
- Now open `test_files/notr-spec.ntr` and be amazed.


## Commands

| Command              | Type     | Description                                       | Args                                  |
| :--------            | :-----   | :-------                                          | :--------                             |
| notr_insert_target   | Context  | Insert a target from clipboard                    |                                       |
| notr_insert_ref      | Context  | Insert a ref from selector                        |                                       |
| notr_goto_target     | Context  | Go to a target from selector                      | filter_by_tag: true select tag first  |
| notr_follow_ref      | Context  | Go to a reference from selector                   |                                       |
| notr_insert_hrule    | Context  | Make a line                                       | fill_char: "="                        |
| table_fit            | Context  | Fit table contents to columns                     |                                       |
| table_insert_col     | Context  | Insert column at caret                            |                                       |
| table_delete_col     | Context  | Remove column at caret                            |                                       |
| table_sort_col       | Context  | Sort column at caret - direction toggles          | asc: true/false                       |
| notr_dump            | Context  | Diagnostic to show the internal info              |                                       |
| notr_reload          | Context  | Diagnostid to force reload after editing colors   |                                       |


## Settings

| Setting             | Description                                | Options                                    |
| :--------           | :-------                                   | :------                                    |
| notr_paths          | List of where notr files live              |                                            |
| notr_index          | Main notr file                             |                                            |
| sort_tags_alpha     | Sort tags alphabetically else by frequency | true/false                                 |
| visual_line_length  | For horizontal rule                        |                                            |
| fixed_hl            | Three sets of user keywords                |                                            |
| fixed_hl_whole_word | User highlights option                     | true/false                                 |


## Caveats

- ST regex is a line-oriented version of [Oniguruma Regular Expressions Version 6.8.0](https://github.com/kkos/oniguruma).
  Some things pertaining to normal line endings don't quite work as expected.
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables...
- Coloring for the markup.user_hls and markup.fixed_hls only supports fore and back colors, not font_style.
- view.add_regions() apparently only supports colors, annotations, and icon. It does not support font style and region flags.
  Also they are not available via extract_scope().
- After editing color-scheme, close and reopen affected views.

# Future Features Consideration
- Block comment/uncomment with char/string from settings.
- Nav and folding by section/hierarchy. Might be tricky: https://github.com/sublimehq/sublime_text/issues/5423.
- Unicode menu/picker to insert/view at caret.
- Toggle syntax coloring (distraction free). Or just set syntax to Plain Text.
- Show image file as phantom or hover, maybe thumbnail. Annotations, popups (mdpopups)?
- Indent/dedent lists with bullets.
- Table filters.
- Make a syntax_test_notr.ntr.
