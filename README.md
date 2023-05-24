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

- See `notr-spec.ntr` for an example of the features. Looks like this (sorry about the colors...):

![Some](files/ex1.jpg)

![Other](files/ex2.jpg)


## Limitations

- ST is line-oriented regex only.
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables...
- view.add_regions() apparently only supports colors, annotations, and icon. It does not support font style and region flags.
    Also they are not available via extract_scope().
- Auto-indent with bullets? Probably not possible as ST controls this.

## Scopes

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


## Commands

| Command                    | Implementation | Description                   | Args                           |
| :--------                  | :-------       | :-------                      | :--------                      |
| notr_xxxx                  | Context        | something here                |                                |

Gotos put tags/sections on clipboard if esc.


## Settings

| Setting              | Description                              | Options                                    |
| :--------            | :-------                                 | :------                                    |
| notr_xxxx            | something here                           |                                            |


## Future
Things to add later, maybe.

- Support text/link attributes in blocks, tables, lists, etc.
- Unicode menu/picker to insert, show at caret.
- Ligatures - some compromise? https://practicaltypography.com/ligatures-in-programming-fonts-hell-no.html
