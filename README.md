# Notr

Sublime Text markup syntax for coloring plain text files. The intention is to provide visual clues for things
like sections, links, tables, lists, etc. The syntax is somewhat similar to markdown but this is not intended
to be rendered into a pretty final form.

Built for ST4 on Windows and Linux.

## Features

- Sections with tags
- Various text decorations
- Links and references
- Lists
- Tables
- Auto highlight TODO1 these are shared with SbotHighlight differentiate?

- See [The spec](files/notr-spec.ntr) for an example of the features. Looks like this (sorry about the colors...):

![Some](files/ex1.jpg)

![Other](files/ex2.jpg)


## Limitations

- ST regex is a line-oriented version of [Oniguruma Regular Expressions Version 6.8.0](https://github.com/kkos/oniguruma).
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables...
- view.add_regions() apparently only supports colors, annotations, and icon. It does not support font style and region flags.
    Also they are not available via extract_scope().
- Auto-indent with bullets? Probably not possible as ST controls this.

## Scopes

ST defaults:
  - From [Minimal Scope Coverage](https://www.sublimetext.com/docs/scope_naming.html#minimal-scope-coverage).
  - [Markup languages](https://www.sublimetext.com/docs/scope_naming.html#markup).
  - ditdit

Notr uses these existing scopes.

- meta.table
- meta.table.header
- markup.bold - capture
- markup.italic - capture
- markup.strikethrough - capture

New scopes added for this application. Notr is a markup language but some of the default markup.* scopes didn't feel right.

- text.notr
- markup.underline.link.notr
- markup.heading.notr
- markup.heading.content.notr
- markup.heading.marker.notr
- markup.heading.tags.notr
- markup.hrule.notr
- markup.link.alias.notr
- markup.link.name.notr
- markup.link.refname.notr
- markup.list.content.notr
- markup.list.indent.notr
- markup.list.marker.notr
- markup.quote.notr
- markup.raw.block.notr
- markup.raw.inline.notr

New scopes added for general use.

- markup.underline
- markup.user_hl1
- markup.user_hl2
- markup.user_hl3
- markup.user_hl4
- markup.user_hl5
- markup.user_hl6

## Configuration

- Commands: see Context.sublime-menu
- Settings: see Notr.sublime-settings


## Now

- TODO1 Add execute-python-script menu item (utils.context and sidebar)
- TODO1 Consolidate ? :
utils Context.sublime-menu
[ 
    // My custom menu.
    { "caption": "-" },
    { "caption": "Split View 2 Pane", "command": "sbot_split_view" },
    { "caption": "Open Terminal", "command": "sbot_terminal"},
    { "caption": "Execute", "command": "sbot_exec"},
    // { "caption": "CSV Justify columns", "command": "csv_format_expand" },
    // { "caption": "CSV Compact columns", "command": "csv_format_compact" },
    { "caption": "Toggle Hex View", "command": "hex_viewer" },
    { "caption": "Reopen as UTF-8", "command": "reopen", "args": { "encoding": "utf-8" } },
]
Side Bar.sublime-menu
[
    { "caption": "-", "id": "sbot_sidebar_addons" },
    { "caption": "Copy Name", "command": "sbot_sidebar_copy_name", "args": { "paths": [] }},
    { "caption": "Copy Path", "command": "sbot_sidebar_copy_path", "args": { "paths": [] }},
    { "caption": "Copy File", "command": "sbot_sidebar_copy_file", "args": { "paths": [] }},
    { "caption": "Execute", "command": "sbot_sidebar_exec", "args": { "paths": [] }},
    { "caption": "Open Terminal", "command": "sbot_sidebar_terminal", "args": { "paths": [] }},
    { "caption": "Tree", "command": "sbot_sidebar_tree", "args": { "paths": [] }},
]

- TODO1 C:\Users\cepth\OneDrive\OneDrive Documents\do_st_repos.py zip User

- TODO1 folding by section

- TODO1 Use icons, style, annotations, phantoms? see:
    - Show image as phantom or hover. Thumbnail. See SbotDev.
    - Annotations? See anns.append()
    - see linter code to see what they do: outline
    - see Sublime Markdown Popups (mdpopups) is a library for Sublime Text plugins. for generating tooltip popups.
        It also provides API methods for generating and styling the new phantom elements
        utilizes Python Markdown with a couple of special extensions to convert Markdown to
        HTML that can be used to create the popups and/or phantoms.
        API commands to aid in creating great tooltips and phantoms.
        will use your color scheme


## Future
Things to add later, maybe.

- Support text/link attributes in blocks, tables, lists, etc.
- Unicode menu/picker to insert, show at caret.
- Toggle syntax coloring (distraction free). Could just set to Plain Text.
- Block comment/uncomment useful? What would that mean - "hide" text? shade? Insert string (# or // or ...) from settings.
- Fancy file.section navigator (like word-ish and/or goto anything). Drag/drop section.
- Expose notes to web for access from phone. Render html with anchors/links?
- Tables: insert table(w, h)  autofit/justify  add/delete row(s)/col(s)
