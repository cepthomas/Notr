# Notr

Sublime Text markup syntax for coloring plain text files. Somewhat similar to markdown but not intended to be rendered
into a pretty final form.

Built for ST4 on Windows and Linux.

Persistence file is in `%data_dir%\Packages\User\.SbotStore`.

## Features

- Describe list.
- See `notr-spec.ntr`. Make a pic of this.

## Scopes

- See my C:\Users\cepth\AppData\Roaming\Sublime Text\Packages\User\CT.sublime-color-scheme.

TODOdoc Notr uses these scopes:
- ST defaults:
  - From [Minimal Scope Coverage](https://www.sublimetext.com/docs/scope_naming.html#minimal-scope-coverage).
  - [Markup languages](https://www.sublimetext.com/docs/scope_naming.html#markup).
  - ditdit

- New scopes added for this application. Notr is a markup language but some of the default markup.* scopes
  didn't feel right.
  - From C:\Users\cepth\AppData\Roaming\Sublime Text\Packages\User\CT.sublime-color-scheme).
  - ditdit

meta. Meta scopes are used to scope larger sections of code or markup, generally containing multiple, more specific scopes. These are not intended to be styled by a color scheme, but used by preferences and plugins.


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
- Block "comment/uncomment" useful? What would that mean?
- Auto-indent with bullets? Probably not possible as ST controls this.
- Ligatures?
    I don't think ligatures are helpful but maybe some variation on them?
    https://www.sublimetext.com/docs/ligatures.html.
    Things like:
       `<- <-- <--- <---- <-< <--< <---< <----<`
    Supported fonts: Cascadia Code, Cascadia Code SemiBold, Consolas, Courier New, 
      Lucida Console, DejaVu Sans Mono, Source Code Pro Medium, Source Code Pro Semibold, Noto Mono
