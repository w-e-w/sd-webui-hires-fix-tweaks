# sd-webui-hires-fix-tweaks

### This is still in development and not meant to be used by users
normally this repo would be set as private at this stage but due to some reasons I opened it up to the public

if you wish to use this
- expect things to break and change without warning

- expect me to do random things such as force push commit history change the repo name etc

### Feel free to request features

---

the goal of this extension is to add more options and features to hires fix
the types of options and features that are less likely to be built into web UI itself as they only apply to certain workflows

## Features

1. Hires pass CFG scale
   - set a different CFG scale for hires pass<br>this is particularly useful if you're working with LCM, can also a cheap interesting effects

2. Hires Batch and Seed
   - Generate multiple hires pass form first pass image
   - Specify different seed for hires pass

3. Hires prompt mode
   - `Default`: Webui default behavior:<br>if blank same as first pass else use hires prompt 
   - `Append`: Append hires prompt after first pass prompt
   - `Prepend`: Prepend hires prompt before first pass prompt
   - `Prompt S/R`: Prompt Search and Replace:<br>replace or insert first pass prompt with hires prompt

4. Hires output directory
   - Specify a different output directory for hires pass
   - `Settings > Paths for saving > Output directory for hires. fix images`


## Prompt Search and Replace syntax
When in Prompt Search and Replace mode the first pass prompt will be used as the base template to perform a search and replace on to create the hires prompt.

the first pass can be any regular prompt, or you can insert `@insert_marker@` anywhere in the prompt to indicate where the hires prompt should be inserted.
the `@insert_marker@` will be removed from the prompt before image generation.

example first pass prompt
```
this is an example prompt @insert_marker@, and replace prompt some more replace with blank prompt, 
prompt to
replace can be
multil-ine
like so
```

the hires prompt is used as instructions for the search and replace
each instruction is entry starts with a `key_word` enclosed by `@` at the start of the line, everything after this until the next `@key_word@` is the replacement or inserted prompt

example hires prompt (instructions)
```
@insert_marker@ insert something here
@replace prompt@ replace something here
@replace with blank@
@can be
multil-ine@replacement can
be multi-line
```

- `@insert_marker@` exists in the prompt it will perform insert mode `insert something here` will be inserted in its place of `@insert_marker@` the `@insert_marker@` itself will be removed from the prompt

- `@replace prompt@` dose not in the prompt it will perform replace mode, the prompt will be unchanged but the hires prompt will have `replace prompt` replaced with `replace something here`

- `@replace with blank@` similar to `@replace prompt@` but the replacement is `"empty"`, this effectively this removes the `replace with blank` from the hires prompt

- both search phrase and replacement can be multi-line

if you need a literal `@` in the instructions then you can escape it by doubling it `@@`
you can also change the character used to enclose the `key_word` by setting the `@` to some other character

This is the resulting using the above prompt and hires prompt
resulting prompt
```
this is an example prompt , and replace prompt some more replace with blank prompt,
prompt to
replace can be
multil-ine
like so
```

resulting hires prompt
```
this is an example prompt  insert something here
, and  replace something here
 some more  prompt, 
prompt to
replace replacement can
be multi-line
like so
```
