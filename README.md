# Notr TODO doc

Sublime Text markup syntax for coloring plain text files. The intention is to provide visual clues for things
like sections, links, tables, lists, etc. The syntax is somewhat similar to markdown but this is not intended
to be rendered into some pretty final form.

Built for ST4 on Windows and Linux.

Persistence file is in `%data_dir%\Packages\User\.SbotStore`. ????

## Features

- Describe list.
- See `notr-spec.ntr`. Make a pic of this.

## Limitations

- ST is line-oriented regex only.
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables...
- view.add_regions() apparently only supports colors, annotations, and icon. It does not support font style and region flags.
    Also they are not available via extract_scope().
- Auto-indent with bullets? Probably not possible as ST controls this.

## Structure

- Lists of:
  - managed ntr filepaths.
  - managed other filepaths.
like:
[Charlotte inline: http://pattedemouche.free.fr/]
[felix-le-chat1: C:\Dev\Notr\felix.jpg]
[felix-le-chat2: ..\..\Dev\Notr\felix.jpg]


## Scopes

- See my C:\Users\cepth\AppData\Roaming\Sublime Text\Packages\User\CT.sublime-color-scheme.

Notr uses these scopes:
- ST defaults:
  - From [Minimal Scope Coverage](https://www.sublimetext.com/docs/scope_naming.html#minimal-scope-coverage).
  - [Markup languages](https://www.sublimetext.com/docs/scope_naming.html#markup).
  - ditdit

- New scopes added for this application. Notr is a markup language but some of the default markup.* scopes
  didn't feel right.
  - From C:\Users\cepth\AppData\Roaming\Sublime Text\Packages\User\CT.sublime-color-scheme).
  - ditdit

meta. Meta scopes are used to scope larger sections of code or markup, generally containing multiple, more specific scopes. These are not intended to be styled by a color scheme, but used by preferences and plugins.

ST uses [Oniguruma Regular Expressions Version 6.8.0    2018/07/26](https://github.com/kkos/oniguruma)
Doc: https://github.com/kkos/oniguruma/blob/master/doc/RE
syntax: ONIG_SYNTAX_ONIGURUMA (default)

## Links

Note that this uses the OS association so py files could open as exes. Maybe a new flavor of open_context_url.py.


## Commands

| Command                    | Implementation | Description                   | Args                           |
| :--------                  | :-------       | :-------                      | :--------                      |
| notr_xxxx                  | Context        | something here                |                                |

// visuals
{ "caption": "Insert", "command": "notr_insert_hrule", "args" : {"style" : 1} },
// insert link from clipboard
{ "caption": "Insert Link", "command": "notr_insert_link" },
// insert ref from list of known refs
{ "caption": "Insert Ref", "command": "notr_insert_ref" },
// open link or section from ref: markup.link.refname.notr  like open_context_url
{ "caption": "Open Ref", "command": "notr_open_ref" },
// list all tags
{ "caption": "All Tags", "command": "notr_all_tags" },
// find all sections with tag(s) - input? put in find pane. also wildcard search on name.
{ "caption": "Find Sections", "command": "notr_find_sections" },
// insert link from clipboard
{ "caption": "Insert Link Sections", "command": "notr_insert_link" },
// rendering
{ "caption": "Notr HTML", "command": "notr_to_html", "args" : {"line_numbers" : false} },


## Settings

| Setting              | Description                              | Options                                    |
| :--------            | :-------                                 | :------                                    |
| notr_xxxx            | something here                           |                                            |


## Future
Things to add later, maybe.

- Support text/link attributes in blocks, tables, lists, etc.
- Unicode menu/picker to insert, show at caret.
- Ligatures - some compromise? https://practicaltypography.com/ligatures-in-programming-fonts-hell-no.html
- Expose notes to web for access from phone. R/O render html?
- Show image as phantom or hover. Thumbnail.
- Annotations? See anns.append()
- Toggle syntax coloring (distraction free). Could just set to Plain Text.
- Fancy file.section navigator (like word-ish and/or goto anything). Drag/drop section.
