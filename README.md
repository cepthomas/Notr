# Notr

Notr is a Sublime Text application plugin for managing and displaying collections of text notes.
It is a plain text format with a lot of similarity to markdown without the powerful
publication capabilities - the text itself is the whole point.

The markup syntax provides file and section navigation and colorizing to provide visual clues for things like
sections, links, tables, lists, etc.

Built for ST4 on Windows and Linux.

## Features

- Notr files have the extension `.ntr`
- Sections with tags and simple (non-hierarchal) folding.
- Sections are identified like markdown `# ## ### etc`.
- Various text decorations for visual indication.
- Targets and references - targets can be section, file (image or other), uri.
- Navigation to targets via goto anything. Has MRU and sticky entries.
- Navigation to notr file errors.
- Search in all notr files.
- Lists with customizable bullets.
- Markdown-like quotes and raw text also act like comments.
- Tables with insert/delete column, fit, sort. Loosely based on https://github.com/wadetb/Sublime-Text-Advanced-CSV.
  This could be ported for general purpose use.
- Auto highlight - supplements [SbotHighlight](https://github.com/cepthomas/SbotHighlight) (recommended).
- Render to html with [SbotRender](https://github.com/cepthomas/SbotRender) (recommended).
- After editing your color-scheme, you need to close and reopen affected views.
- Multiple notr projects.

## Example

[The spec](example/notr-spec.ntr) provides an example of the features. If the plugin is installed it will look
something like this:

![ex1](example/ex1.jpg)

![ex2](example/ex2.jpg)

![ex3](example/ex3.jpg)

To run the demo:
- Install the plugin.
- Select `Preferences->Package Settings->Notr`.
- Add this project name to your settings:
``` json
"projects":
[
    "$APPDATA\\Sublime Text\\Packages\\Notr\\example\\notr-demo.nproj",
]
```
- Implement color scheme per section Color Scheme.
- Now open `example/notr-spec.ntr`. Test drive the various context menu selections.

## Commands

| Command                      | Type    | Description                                  | Args                            |
| :--------                    | :-----  | :-------                                     | :--------                       |
| notr_open_project            | Context | Open a project from settings using selector  |                                 |
| notr_edit_project            | Context | Edit the current project                     |                                 |
| notr_insert_target_from_clip | Context | Insert a target from clipboard               |                                 |
| notr_insert_ref              | Context | Insert a ref from selector                   |                                 |
| notr_goto_target             | Context | Go to a target via selector or ref or link   | filter_by_tag=select tag first  |
| notr_insert_hrule            | Context | Make a line                                  | fill_str="=", reps=20           |
| notr_find_in_files           | Context | Search within the notr_paths in settings     |                                 |
| table_fit                    | Context | Fit table contents to columns                |                                 |
| table_insert_col             | Context | Insert column at caret                       |                                 |
| table_delete_col             | Context | Remove column at caret                       |                                 |
| table_sort_col               | Context | Sort column at caret - direction toggles     | asc=true/false                  |
| notr_dump                    | Context | Diagnostic to show the internal info         |                                 |
| notr_reload                  | Context | Force reload after editing colors etc.       |                                 |

## Settings

| Setting             | Description                                   | Options                              |
| :--------           | :-------                                      | :------                              |
| sort_tags_alpha     | Sort tags alphabetically else by frequency    | true/false                           |
| mru_size            | How many mru entries in selector              | default=5                            |
| fixed_hl_whole_word | Select fixed_hl by whole word                 | true/false                           |
| section_marker_size | Include these and higher sections in selector | default=1                            |

## Project File

A notr project file contains these elements. See [demo project](example/notr-demo.nproj)

| Setting             | Description                                                     |
| :--------           | :-------                                                        |
| notr_paths          | List of where notr files live                                   |
| notr_index          | Main notr file                                                  |
| sticky              | list of section names that always appear at the top of selector |
| fixed_hl            | Three sets of user keywords                                     |

## Color Scheme

New scopes have been added to support this application. Adjust the values in

[notr scopes](example/notr-scopes.sublime-color-scheme) to taste and add them
to your `Packages\User\your.sublime-color-scheme` file. Note that `markup.fixed_hl*`
and `markup.user_hl*` are also used by other members of the sbot family.

## Caveats

- ST uses a custom line-oriented [regex engine](https://www.sublimetext.com/docs/syntax.html). Some things pertaining to normal line endings don't quite work as expected.
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables. Something to do with meta-scope.
- Coloring for `markup.user_hls` and `markup.fixed_hls` only supports fore and back colors, not font_style.
- `view.add_regions()` apparently only supports colors, annotations, and icon. It does not support font style and region flags.
  Also they are not available via `extract_scope()`.
- Doesn't handle targets with embedded parentheses (i.e. C:\Program Files (x86)\SomeApp). It exceeds my meager regex skills.

## Future

- Publish somewhere for web access. Probably render html.
- Fancy stuff like image thumbnail phantom/hover, annotations, hover/popups, etc.
- Unicode picker/inserter for symbols.
