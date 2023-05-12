# Notr TODO doc

Sublime Text markup syntax for coloring plain text files. Somewhat similar to markdown but not intended to be rendered
into a pretty final form.

Built for ST4 on Windows and Linux.

Persistence file is in `%data_dir%\Packages\User\.SbotStore`. ????

## Features

- Describe list.
- See `notr-spec.ntr`. Make a pic of this.

## Limitations

- ST is line-oriented regex only.
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables...
- view.add_regions() apparently only supports colors, annotations, and icon. It does not support font style and region flags.

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

ST uses [Oniguruma Regular Expressions Version 6.8.0    2018/07/26](https://raw.githubusercontent.com/kkos/oniguruma/v6.9.1/doc/RE)
syntax: ONIG_SYNTAX_ONIGURUMA (default)

## Links

Note that this uses the OS association so py files could open as exes. Maybe a new flavor of open_context_url.py.


## Commands

| Command                    | Implementation | Description                   | Args                           |
| :--------                  | :-------       | :-------                      | :--------                      |
| notr_xxx                   | Context        | something here                |                                |


## Settings

| Setting              | Description                              | Options                                    |
| :--------            | :-------                                 | :------                                    |
| notr_xxx             | something here                           |                                            |


## Future
Things to add later, maybe.

- Support attributes in blocks, tables, lists, etc?
- Auto-indent with bullets? Probably not possible as ST controls this.
- unicode menu/picker to insert, show at caret.
- Ligatures?
    I don't think ligatures are helpful but maybe some variation on them?
    https://www.sublimetext.com/docs/ligatures.html.
    Things like:
       `<- <-- <--- <---- <-< <--< <---< <----<`
    Supported fonts: Cascadia Code, Cascadia Code SemiBold, Consolas, Courier New, 
      Lucida Console, DejaVu Sans Mono, Source Code Pro Medium, Source Code Pro Semibold, Noto Mono
- Expose notes to web for access from phone. render html?
- for image use phantom or hover.
- toggle syntax coloring - just set to Plain Text?
- image phantoms? hover/thumbnail? https://www.sublimetext.com/docs/minihtml.html

