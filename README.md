# sd-webui-hires-fix-tweaks

## Features

1. Hires pass CFG scale<br>set a different CFG scale for hires pass

2. Hires prompt mode
- Default webui behavior:<br>if blank same as first pass else use hires prompt 
- Append:<br>append hires prompt after first pass prompt
- Prepend:<br>prepend hires prompt before first pass prompt
- Prompt Search and Replace:<br>replace or insert first pass prompt with hires prompt

### Prompt Search and Replace syntax

```
{key_word_1} prompt to
{key_word_2} some other prompt
can be multiple lines
{key_word_3}
```



exampl first pass prompt
```
this is an example prompt {insert_here} some more prompt

``` 



this will be an extension to extend the options of hires fix
this is still in development and not meant to be used by users
normally this repo would be set as private at this stage
expect me to do random things such as Force push commit history

planned features
https://github.com/AUTOMATIC1111/stable-diffusion-webui/issues/14111
https://github.com/AUTOMATIC1111/stable-diffusion-webui/issues/14055
