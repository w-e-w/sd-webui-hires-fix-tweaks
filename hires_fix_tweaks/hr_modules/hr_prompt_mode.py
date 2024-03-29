from modules import extra_networks
from modules import shared
import gradio as gr
import re


def setup_regex():
    global marker_char, search_replace_instructions_pattern
    if len(shared.opts.hires_fix_tweaks_marker_char) != 1 or re.match(r'[\s\w]', shared.opts.hires_fix_tweaks_marker_char):
        shared.opts.hires_fix_tweaks_marker_char = '@'
        invalid_marker_character_message = r'''ERROR: invalid marker character
        marker character must be a single uncommon character
        defaulting to "@"'''
        print(invalid_marker_character_message)
        gr.Warning(invalid_marker_character_message)
    marker_char = shared.opts.hires_fix_tweaks_marker_char
    marker_char_escape = re.escape(shared.opts.hires_fix_tweaks_marker_char)
    # search for all line starts with "@marker@", @@ for escaped @
    search_replace_instructions_pattern = re.compile(
        # r'^@((?:[^@]|@@)+)@'
        f'^{marker_char_escape}((?:[^{marker_char_escape}]|{marker_char_escape * 2})+){marker_char_escape}',
        flags=re.MULTILINE,
    )


def remove_extra_networks(prompt):
    """return prompt with extra networks removed"""
    return extra_networks.parse_prompts([prompt])[0][0]


def hires_prompt_mode_default(prompt, hr_prompt, remove_fp_extra_networks=False):
    """
    if hr_prompt == '' and remove_fp_extra_networks:
        remove extra networks from prompt and hr_prompt
    else:
        no change
    """
    return prompt, hr_prompt or (remove_extra_networks(prompt) if remove_fp_extra_networks else prompt)


def hires_prompt_mode_append(prompt, hr_prompt, remove_fp_extra_networks=False):
    if remove_fp_extra_networks or hr_prompt.strip():
        separator = shared.opts.hires_fix_tweaks_append_separator.format(newline='\n')
        hr_prompt = f'{remove_extra_networks(prompt) if remove_fp_extra_networks else prompt}{separator}{hr_prompt}'
    return prompt, hr_prompt


def hires_prompt_mode_prepend(prompt, hr_prompt, remove_fp_extra_networks=False):
    if remove_fp_extra_networks or hr_prompt.strip():
        separator = shared.opts.hires_fix_tweaks_prepend_separator.format(newline='\n')
        hr_prompt = f'{hr_prompt}{separator}{remove_extra_networks(prompt) if remove_fp_extra_networks else prompt}'
    return prompt, hr_prompt


# search leading and trailing newlines
one_leading_and_trailing_newline_pattern = re.compile(r'^\r?\n?([\W\w]*)\r?\n?$')
search_replace_instructions_pattern: re.Pattern
marker_char: str


def hires_prompt_mode_search_replace(prompt, hr_prompt, remove_fp_extra_networks=False):
    """
    parse hr_prompt as instructions for search and replace in prompt

    instructions syntax: @search@ replace
    each pare starts with a search value which is denoted by a newline starting with "@key@"
    anything after the search value is the replacement until the next search value
    both search and replace values are can be multi-line
    if search or replace value requires a literal "@" in the prompt, escape it with "@@"

    the instructions are parsed form hr_prompt then hr_prompt is replaced with the contents of prompt
    then based on the instructions hr_prompt is modified
    if "@search@" value is found in prompt, then it performs an "insert"
        in hr_prompt search for "@search@" and replace with "replace" value
        in prompt remove "@search@"
    otherwise if performs a "replace"
        in hr_prompt search for "search" (not "@search@") and replace with "replace" value
        prompt is not modified
    """
    # parse hr_prompt as instructions for search and replace
    # even indexes are search value, odd indexes are replacing value
    search_replace_instructions_list = search_replace_instructions_pattern.split(hr_prompt)[1:]

    hr_prompt = remove_extra_networks(prompt) if remove_fp_extra_networks else prompt
    for i in range(0, len(search_replace_instructions_list), 2):
        # restore escaped @
        key = search_replace_instructions_list[i].replace(marker_char * 2, marker_char)
        insert_key = f'{marker_char}{key}{marker_char}'

        # restore escaped @ and removes 1 leading and trailing newline
        replace = search_replace_instructions_list[i + 1].replace(marker_char * 2, marker_char)
        replace = one_leading_and_trailing_newline_pattern.search(replace).group(1)

        if insert_key in prompt:
            # insert mode: remove @key@ from prompt and replace @key@ in hr_prompt with replacement
            prompt = prompt.replace(insert_key, '')
            hr_prompt = hr_prompt.replace(insert_key, replace)
        else:
            # replace mode: replace insert_marker in hr_prompt with replacement
            hr_prompt = hr_prompt.replace(key, replace)

    return prompt, hr_prompt


hires_prompt_mode_functions = {
    'Default': hires_prompt_mode_default,
    'Append': hires_prompt_mode_append,
    'Prepend': hires_prompt_mode_prepend,
    'Prompt S/R': hires_prompt_mode_search_replace,
}


def get_prompt(prompt_obj, index):
    return prompt_obj[index] if isinstance(prompt_obj, list) else prompt_obj


def setup(p, *args):
    remove_fp_extra_networks, hires_prompt_mode, hires_negative_prompt_mode = args[1:4]

    if remove_fp_extra_networks or hires_prompt_mode != 'Default':
        hires_prompt_mode_function = hires_prompt_mode_functions.get(hires_prompt_mode, hires_prompt_mode_default)
        if any(isinstance(var, list) for var in [p.prompt, p.hr_prompt]):
            prompt_list, hr_prompt_list = [], []
            for i in range(len(p.prompt if isinstance(p.prompt, list) else p.hr_prompt)):
                prompt, hr_prompt = hires_prompt_mode_function(get_prompt(p.prompt, i), get_prompt(p.hr_prompt, i), args[1])
                prompt_list.append(prompt)
                hr_prompt_list.append(hr_prompt)
            p.prompt, p.hr_prompt = prompt_list, hr_prompt_list
        else:
            p.prompt, p.hr_prompt = hires_prompt_mode_function(p.prompt, p.hr_prompt, args[1])

    if hires_negative_prompt_mode != 'Default':
        hires_prompt_mode_function = hires_prompt_mode_functions.get(hires_negative_prompt_mode, hires_prompt_mode_default)
        if any(isinstance(var, list) for var in [p.negative_prompt, p.hr_negative_prompt]):
            negative_prompt_list, hr_negative_prompt_list = [], []
            for i in range(len(p.negative_prompt if isinstance(p.negative_prompt, list) else p.hr_negative_prompt)):
                negative_prompt, hr_negative_prompt = hires_prompt_mode_function(get_prompt(p.negative_prompt, i), get_prompt(p.hr_negative_prompt, i))
                negative_prompt_list.append(negative_prompt)
                hr_negative_prompt_list.append(hr_negative_prompt)
            p.negative_prompt, p.hr_negative_prompt = negative_prompt_list, hr_negative_prompt_list
        else:
            p.negative_prompt, p.hr_negative_prompt = hires_prompt_mode_function(p.negative_prompt, p.hr_negative_prompt)
