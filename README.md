# Notr

Sublime Text plugin for managing collections of notes. Note files have the extension `.ntr` and the corresponding markup syntax
provides file and section navigation and colorizing to provide visual clues for things like sections, links, tables, lists, etc.
It is a plain text format with a lot of similarity to markdown but is not intended to be rendered into a publication - the text
itself is the whole point of this.

Built for ST4 on Windows and Linux.

## Features

- Sections with tags
- Various text decorations
- Links and references
- Lists
- Tables
- Auto highlight - supplements [SbotHighlight](https://github.com/cepthomas/SbotHighlight)
- Render to html with [SbotRender](https://github.com/cepthomas/SbotRender)


## Demo

[The spec](files/notr-spec.ntr) provides an example of the features. If the plugin is installed it will look
something  like this (excuse the colors...):

![Some](files/ex1.jpg)

![More](files/ex2.jpg)

To run the demo:
- Install the plugin.
- Open `Preferences->Package Settings->Notr`.
- Edit to something like this:
```
{
    "notr_paths": [
        "<$LOCALAPPDATA>\\Sublime Text\\Packages\\Notr\\files",
    ],
    "notr_index": "<$LOCALAPPDATA>\\Sublime Text\\Packages\\Notr\\files\\test-index.ntr",
    "fixed_hl": [
        ["2DO", "and_a"],
        ["user", "and_b"],
        ["dynamic", "and_c"],
    ],
}
```

- Create a custom color scheme file for Notr based on `file/NotrOverlay.sublime-color-scheme`.
  Implement it per [Color customization](https://www.sublimetext.com/docs/color_schemes.html#customization).
- Note that Notr uses some existing scopes and adds some new ones - these are specified in the overlay scheme.
- Now open `files/notr-spec.ntr` and be amazed.


## Commands

| Command              | Type     | Description                             | Args                              |
| :--------            | :-----   | :-------                                | :--------                         |
| notr_insert_link     | Context  | Insert a link from clipboard            |                                   |
| notr_insert_ref      | Context  | Insert a ref from selector              |                                   |
| notr_insert_hrule    | Context  | Visual horizontal rule                  |                                   |
| notr_goto_section    | Context  | Go to section from selector             | filter_by_tag = select tag first  |
| notr_goto_ref        | Context  | Go to a reference from selector         |                                   |
| notr_reload          | Context  | Reload after editing colors or settings |                                   |
| notr_dump            | Context  | xxxx                                    |                                   |


## Settings

| Setting             | Description                                | Options                                    |
| :--------           | :-------                                   | :------                                    |
| notr_paths          | List of where notr files live              |                                            |
| notr_index          | Main notr file                             |                                            |
| sort_tags_alpha     | Sort tags alphabetically or by frequency   | true/false                                 |
| visual_line_length  | For horizontal rule                        |                                            |
| fill_char           | For horizontal rule                        |                                            |
| fixed_hl            | Three sets of user keywords                |                                            |
| fixed_hl_whole_word | User highlights option                     | true/false                                 |


## Caveats

- ST regex is a line-oriented version of [Oniguruma Regular Expressions Version 6.8.0](https://github.com/kkos/oniguruma).
  Some things pertaining to normal line endings don't quite work as expected.
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables...
- Coloring for the markup.user_hls and markup.fixed_hls only supports fore and back colors, but not font_style.
  Also RegionFlags doesn't work in add_regions().
- view.add_regions() apparently only supports colors, annotations, and icon. It does not support font style and region flags.
  Also they are not available via extract_scope().


## Future
Things to consider.

- Support text attributes, links, refs in blocks, tables, lists, etc.
- Unicode menu/picker to insert and view at caret.
- Toggle syntax coloring (distraction free). Maybe just set to Plain Text.
- File/section navigator, drag/drop/cut/copy/paste section.
- Publish notes to web for access from phone. Render html would need links.
- Tables: insert table(w, h), autofit/justify, add/delete row(s)/col(s).
- Use icons, style, annotations, phantoms for something? See mdpopups for generating tooltip popups.
- Show image file as phantom or hover, maybe thumbnail.
- Auto/manual Indent/dedent lists with bullets. Probably not possible as ST controls this.
