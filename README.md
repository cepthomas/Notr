# Notr

Sublime Text markup syntax for colorizing plain text files. The intention is to provide visual clues for things
like sections, links, tables, lists, etc. The syntax is somewhat similar to markdown but this is not intended
to be rendered into a pretty final form.

Built for ST4 on Windows and Linux.

## Features

- Sections with tags
- Various text decorations
- Links and references
- Lists
- Tables
- Auto highlight

- See [The spec](files/notr-spec.ntr) for an example of the features with plugin installed. Looks like this (excuse the colors...):

![Some](files/ex1.jpg)

![More](files/ex2.jpg)


## Limitations

- ST regex is a line-oriented version of [Oniguruma Regular Expressions Version 6.8.0](https://github.com/kkos/oniguruma).
  Some things pertaining to line endings don't quite work as expected.
- Note that coloring *should* stop at the right edge of a table. This is also how ST renders MD tables...
- TODO Coloring for the markup.user_hls only supports fore and back colors, but not font_style - RegionFlags doesn't work in add_regions().
- view.add_regions() apparently only supports colors, annotations, and icon. It does not support font style and region flags.
  Also they are not available via extract_scope().

## Scopes

Notr uses these existing scopes.
```
meta.table
meta.table.header
markup.bold
markup.italic
markup.strikethrough
```

New notr-specific scopes added for this application.
```
text.notr
markup.underline.link.notr
markup.heading.notr
markup.heading.content.notr
markup.heading.marker.notr
markup.heading.tags.notr
markup.hrule.notr
markup.link.alias.notr
markup.link.name.notr
markup.link.refname.notr
markup.list.content.notr
markup.list.indent.notr
markup.list.marker.notr
markup.quote.notr
markup.raw.block.notr
markup.raw.inline.notr
```

New general scopes added (used by other sbot plugins)
```
markup.underline
markup.user_hl1
markup.user_hl2
markup.user_hl3
markup.user_hl4
markup.user_hl5
markup.user_hl6
markup.fixed_hl1
markup.fixed_hl2
markup.fixed_hl3
```

`files\NotrEx.sublime-color-scheme` can be used as an example for colorizing. These are used for all members of the sbot family.


## Commands

| Command              | Type     | Description                             | Args                              |
| :--------            | :------- | :-------                                | :--------                         |
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
| sort_tags_alpha     | Sort tags alphabetically or by frequency   |                                            |
| visual_line_length  | For horizontal rule                        |                                            |
| fill_char           | For horizontal rule                        |                                            |
| fixed_hl            | 3 sets of user keywords                    |                                            |
| fixed_hl_whole_word | User highlights option                     |                                            |
| debug               | debug                                      |                                            |


## Future
Things to consider.

- Simple git tools: diff, commit, push? https://github.com/kemayo/sublime-text-git.
- Support text attributes, links, refs in blocks, tables, lists, etc.
- Unicode menu/picker to insert and view at caret.
- Toggle syntax coloring (distraction free). Maybe just set to Plain Text.
- Block "comment/uncomment" useful? What would that mean - "hide" text? shade?
- File/section navigator, drag/drop/cut/copy/paste section.
- Publish notes to web for access from phone. Render html would need links.
- Tables: insert table(w, h), autofit/justify, add/delete row(s)/col(s).
- Use icons, style, annotations, phantoms? See mdpopups for generating tooltip popups.
- Show image file as phantom or hover, maybe thumbnail. See SbotDev.
- Auto/manual Indent/dedent lists with bullets. Probably not possible as ST controls this.
- Make into package when it's cooked. https://packagecontrol.io/docs/submitting_a_package.
