from hires_fix_tweaks.utils import dumps_quote_swap_json, loads_quote_swap_json
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


class FakeP:
    def __init__(self, prompt, negative_prompt, hr_prompt, hr_negative_prompt):
        self.prompt = '' if prompt is None else prompt.strip()
        self.negative_prompt = '' if negative_prompt is None else negative_prompt.strip()
        self.hr_prompt = '' if hr_prompt is None else hr_prompt.strip()
        self.hr_negative_prompt = '' if hr_negative_prompt is None else hr_negative_prompt.strip()

    def compare(self, other, p, np):
        positive = p and all(getattr(self, attr).strip() == getattr(other, attr).strip() for attr in ['prompt', 'hr_prompt'])
        negative = np and all(getattr(self, attr).strip() == getattr(other, attr).strip() for attr in ['negative_prompt', 'hr_negative_prompt'])
        return positive, negative


def get_mode_info(mode, hr_prompt, negative, remove_fp_extra_networks=False):
    """
    {
        'h': [mode, hr_prompt, remove_fp_extra_networks],
        'n': [mode, hr_prompt],
        'a': append_separator,
        'p': prepend_separator,
        'c': marker_char,
    }
    """
    if shared.opts.hires_fix_tweaks_save_template:
        prompt_mode = [mode, hr_prompt.strip()]
        if remove_fp_extra_networks:
            prompt_mode.append(remove_fp_extra_networks)
        info_obj = {'n' if negative else 'h': prompt_mode}
        if mode == 'Append' and shared.opts.hires_fix_tweaks_append_separator != shared.opts.get_default('hires_fix_tweaks_append_separator'):
            info_obj['a'] = shared.opts.hires_fix_tweaks_append_separator
        elif mode == 'Prepend' and shared.opts.hires_fix_tweaks_prepend_separator != shared.opts.get_default('hires_fix_tweaks_prepend_separator'):
            info_obj['p'] = shared.opts.hires_fix_tweaks_prepend_separator
        elif mode == 'Prompt S/R' and shared.opts.hires_fix_tweaks_marker_char != shared.opts.get_default('hires_fix_tweaks_marker_char'):
            info_obj['c'] = shared.opts.hires_fix_tweaks_marker_char
        return info_obj


def merge_mode_info(info_obj_1, info_obj_2):
    if info_obj_1 and info_obj_2:
        match (isinstance(info_obj_1, dict), isinstance(info_obj_2, dict)):
            case True, True:
                info_obj_1.update(info_obj_2)
                return info_obj_1
            case False, False:
                assert len(info_obj_1) == len(info_obj_2)
                info_obj = []
                for o1, o2 in zip(info_obj_1, info_obj_2):
                    o1.update(o2)
                    info_obj.append(o1)
                return info_obj
            case False, True:
                [o.update(info_obj_2) for o in info_obj_1]
                return info_obj_1
            case True, False:
                [o.update(info_obj_2) for o in info_obj_2]
                return info_obj_2
    elif info_obj_1:
        return info_obj_1
    elif info_obj_2:
        return info_obj_2


def parse_mode_info(mode_info):
    info_obj = loads_quote_swap_json(mode_info)
    h = info_obj.get('h', [None, None, None])
    mode_p, hr_prompt, remove_fp_extra_networks = h if len(h) == 3 else (h + [False])
    mode_np, hr_np_prompt = info_obj.get('n', [None, None])
    app_sep = info_obj.get('a', shared.opts.get_default('hires_fix_tweaks_append_separator'))
    pre_sep = info_obj.get('p', shared.opts.get_default('hires_fix_tweaks_prepend_separator'))
    marker = info_obj.get('c', shared.opts.get_default('hires_fix_tweaks_marker_char'))
    return mode_p, hr_prompt, mode_np, hr_np_prompt, app_sep, pre_sep, marker, remove_fp_extra_networks


def parse_and_apply_mode_info(mode_info, params):
    mode_p, hr_prompt, mode_np, hr_np_prompt, app_sep, pre_sep, marker, remove_fp_extra_networks = parse_mode_info(mode_info)

    if 'HR Append' not in params:
        params['HR append'] = app_sep
        shared.opts.set('hires_fix_tweaks_append_separator', app_sep)

    if 'HR Prepend' not in params:
        params['HR prepend'] = pre_sep
        shared.opts.set('hires_fix_tweaks_prepend_separator', pre_sep)

    if 'HR marker' not in params:
        params['HR marker'] = marker
        shared.opts.set('hires_fix_tweaks_marker_char', marker)

    return mode_p, hr_prompt, mode_np, hr_np_prompt, remove_fp_extra_networks


def process_prompt_mode(hires_prompt_mode, p, negative=False, remove_fp_extra_networks=False):
    info_obj = None
    if remove_fp_extra_networks or hires_prompt_mode != 'Default':
        p_prompt, p_hr_prompt = (p.negative_prompt, p.hr_negative_prompt) if negative else (p.prompt, p.hr_prompt)

        hires_prompt_mode_function = hires_prompt_mode_functions.get(hires_prompt_mode, hires_prompt_mode_default)

        if any(isinstance(var, list) for var in [p_prompt, p_hr_prompt]):
            prompt_list, hr_prompt_list, info_obj = [], [], []
            for i in range(len(p_prompt if isinstance(p_prompt, list) else p_hr_prompt)):
                prompt, hr_prompt = hires_prompt_mode_function(get_prompt(p_prompt, i), get_prompt(p_hr_prompt, i), remove_fp_extra_networks)
                prompt_list.append(prompt)
                hr_prompt_list.append(hr_prompt)
                info_obj.append(get_mode_info(hires_prompt_mode, get_prompt(p_hr_prompt, i), negative, remove_fp_extra_networks))

            if negative:
                p.negative_prompt, p.hr_negative_prompt = prompt_list, hr_prompt_list
            else:
                p.prompt, p.hr_prompt = prompt_list, hr_prompt_list

        else:
            info_obj = get_mode_info(hires_prompt_mode, p_hr_prompt, negative, remove_fp_extra_networks)
            if negative:
                p.negative_prompt, p.hr_negative_prompt = hires_prompt_mode_function(p_prompt, p_hr_prompt, remove_fp_extra_networks)
            else:
                p.prompt, p.hr_prompt = hires_prompt_mode_function(p_prompt, p_hr_prompt, remove_fp_extra_networks)

    return info_obj


def apply_override(p):
    for key in ['hires_fix_tweaks_append_separator', 'hires_fix_tweaks_prepend_separator', 'hires_fix_tweaks_marker_char']:
        if key in p.override_settings:
            shared.opts.set(key, p.override_settings[key])


def setup(p, *args):
    remove_fp_extra_networks, hires_prompt_mode, hires_negative_prompt_mode = args[1:4]
    with RestoreSettings():
        apply_override(p)
        info_obj_p = process_prompt_mode(hires_prompt_mode, p, remove_fp_extra_networks=remove_fp_extra_networks)
        info_obj_np = process_prompt_mode(hires_negative_prompt_mode, p, negative=True)
        if info_obj := merge_mode_info(info_obj_p, info_obj_np):
            p.extra_generation_params['Hires prompt mode'] = dumps_quote_swap_json(info_obj)


class RestoreSettings:
    def __enter__(self):
        keys = ['hires_fix_tweaks_append_separator', 'hires_fix_tweaks_prepend_separator', 'hires_fix_tweaks_marker_char']
        self.settings = {key: getattr(shared.opts, key) for key in keys}

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, value in self.settings.items():
            shared.opts.set(key, value)


def parse_infotext(infotext, params):
    use_p, use_n = False, False
    try:
        if shared.opts.hires_fix_tweaks_restore_template:
            with RestoreSettings():
                if 'Hires prompt mode' in params:
                    mode_p, hr_prompt, mode_np, hr_np_prompt, remove_fp_extra_networks = parse_and_apply_mode_info(params['Hires prompt mode'], params)

                    if mode_p or mode_np:
                        p_info = FakeP(params['Prompt'], params['Negative prompt'], params['Hires prompt'], params['Hires negative prompt'])
                        p = FakeP(params['Prompt'], params['Negative prompt'], hr_prompt, hr_np_prompt)
                        if mode_p:
                            process_prompt_mode(mode_p, p, remove_fp_extra_networks=remove_fp_extra_networks)
                        if mode_np:
                            process_prompt_mode(mode_np, p, negative=True)
                        use_p, use_n = p.compare(p_info, mode_p, mode_np)
                        if use_p:
                            params['Hires prompt mode'] = mode_p
                            params['Hires prompt'] = hr_prompt
                            params['Remove FP Networks'] = remove_fp_extra_networks
                        if use_n:
                            params['Hires negative prompt mode'] = mode_np
                            params['Hires negative prompt'] = hr_np_prompt

    except Exception as e:
        print(e)
        pass

    if not use_p:
        params['Hires prompt mode'] = 'Default'
        params['Remove FP Networks'] = False
    if not use_n:
        params['Hires negative prompt mode'] = 'Default'
