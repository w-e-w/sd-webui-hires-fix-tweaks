from functools import partial
from modules import scripts
import gradio as gr

from scripts.hires_fix_tweaks.hr_modules import hr_prompt_mode
from scripts.hires_fix_tweaks.hr_modules import hr_batch_seed
from scripts.hires_fix_tweaks.hr_modules import hr_cfg_scale
from scripts.hires_fix_tweaks import xyz
from scripts.hires_fix_tweaks import ui

# import re
# invalid_marker_character_message = r'''ERROR: invalid marker character
# marker character must be a single uncommon character
# defaulting to "@"'''
#
#
# def setup_regex():
#     global marker_char, search_replace_instructions_pattern
#     if len(shared.opts.hires_fix_tweaks_marker_char) != 1 or re.match(r'[\s\w]', shared.opts.hires_fix_tweaks_marker_char):
#         shared.opts.hires_fix_tweaks_marker_char = '@'
#         print(invalid_marker_character_message)
#         gr.Warning(invalid_marker_character_message)
#     marker_char = shared.opts.hires_fix_tweaks_marker_char
#     marker_char_escape = re.escape(shared.opts.hires_fix_tweaks_marker_char)
#     # search for all line starts with "@marker@", @@ for escaped @
#     search_replace_instructions_pattern = re.compile(
#         # r'^@((?:[^@]|@@)+)@'
#         f'^{marker_char_escape}((?:[^{marker_char_escape}]|{marker_char_escape * 2})+){marker_char_escape}',
#         flags=re.MULTILINE,
#     )
#
#
# def hires_prompt_mode_default(prompt, hr_prompt):
#     return prompt, hr_prompt
#
#
# def hires_prompt_mode_append(prompt, hr_prompt):
#     if hr_prompt.strip():
#         separator = shared.opts.hires_fix_tweaks_append_separator.format(newline='\n')
#         hr_prompt = f'{prompt}{separator}{hr_prompt}'
#     return prompt, hr_prompt
#
#
# def hires_prompt_mode_prepend(prompt, hr_prompt):
#     if hr_prompt.strip():
#         separator = shared.opts.hires_fix_tweaks_prepend_separator.format(newline='\n')
#         hr_prompt = f'{hr_prompt}{separator}{prompt}'
#     return prompt, hr_prompt
#
#
# # search leading and trailing newlines
# one_leading_and_trailing_newline_pattern = re.compile(r'^\r?\n?([\W\w]*)\r?\n?$')
# search_replace_instructions_pattern: re.Pattern
# marker_char: str
# setup_regex()
#
#
# def hires_prompt_mode_search_replace(prompt, hr_prompt):
#     """
#     parse hr_prompt as instructions for search and replace in prompt
#
#     instructions syntax: @search@ replace
#     each pare starts with a search value which is denoted by a newline starting with "@key@"
#     anything after the search value is the replacement until the next search value
#     both search and replace values are can be multi-line
#     if search or replace value requires a literal "@" in the prompt, escape it with "@@"
#
#     the instructions are parsed form hr_prompt then hr_prompt is replaced with the contents of prompt
#     then based on the instructions hr_prompt is modified
#     if "@search@" value is found in prompt, then it performs an "insert"
#         in hr_prompt search for "@search@" and replace with "replace" value
#         in prompt remove "@search@"
#     otherwise if performs a "replace"
#         in hr_prompt search for "search" (not "@search@") and replace with "replace" value
#         prompt is not modified
#     """
#     # parse hr_prompt as instructions for search and replace
#     # even indexes are search value, odd indexes are replace value
#     search_replace_instructions_list = search_replace_instructions_pattern.split(hr_prompt)[1:]
#
#     hr_prompt = prompt
#     for i in range(0, len(search_replace_instructions_list), 2):
#         # restore escaped @
#         key = search_replace_instructions_list[i].replace(marker_char * 2, marker_char)
#         insert_key = f'{marker_char}{key}{marker_char}'
#
#         # restore escaped @ and remove 1 leading and trailing newline
#         replace = search_replace_instructions_list[i + 1].replace(marker_char * 2, marker_char)
#         replace = one_leading_and_trailing_newline_pattern.search(replace).group(1)
#
#         if insert_key in prompt:
#             # insert mode: remove @key@ from prompt and replace @key@ in hr_prompt with replacement
#             prompt = prompt.replace(insert_key, '')
#             hr_prompt = hr_prompt.replace(insert_key, replace)
#         else:
#             # replace mode: replace insert_marker in hr_prompt with replacement
#             hr_prompt = hr_prompt.replace(key, replace)
#
#     return prompt, hr_prompt


# hires_prompt_mode_functions = {
#     'Default': hires_prompt_mode_default,
#     'Append': hires_prompt_mode_append,
#     'Prepend': hires_prompt_mode_prepend,
#     'Prompt S/R': hires_prompt_mode_search_replace,
# }


# Extension
class Script(scripts.Script):
    def __init__(self):
        super().__init__()
        # script attributes
        self.infotext_fields = []

        # ui create status
        self.create_ui_cfg_done = None
        self.create_ui_hr_prompt_mode_done = None
        self.create_hr_seed_ui_done = None

        # gradio elements
        self.hr_cfg_e = None
        self.hr_batch_count_e = None
        self.hr_seed_resize_from_h_e = None
        self.hr_seed_resize_from_w_e = None
        self.hr_subseed_strength_e = None
        self.hr_subseed_e = None
        self.hr_seed_checkbox_e = None
        self.hr_prompt_mode_e = None
        self.hr_negative_prompt_mode_e = None
        self.hr_seed_e = None

        self.enable_hr_seed_e = None

        # runtime values
        # self.ui_args = None

        # self.hr_batch_count = None

        self.apply_hr_cfg_scale = None

        # self.batch_size = None
        self.first_pass_cfg_scale = None

        self.first_pass_seed_resize_from_w = None
        self.first_pass_seed_resize_from_h = None

        self.hr_batch_count = None

        self.first_pass_seeds = None

        self.hr_seed_enable_extras = None
        self.first_pass_subseeds = None

        self.hr_seed = None
        self.hr_subseed = None
        self.hr_subseed_strength = None
        self.hr_seed_resize_from_w = None
        self.hr_seed_resize_from_h = None

        self.all_hr_seeds = None
        self.all_hr_subseeds = None

        self.enable_hr_seed = None

    def title(self):
        return 'Hires. fix tweaks'

    def show(self, is_img2img):
        if not is_img2img:
            self.on_after_component_elem_id = [
                ('txt2img_hires_fix_row2', partial(ui.create_ui_cfg, self)),
                ('txt2img_hires_fix_row4', partial(ui.create_ui_hr_prompt_mode, self)),
            ]
            return scripts.AlwaysVisible


    def ui(self, is_img2img):
        if None in [self.create_ui_cfg_done, self.create_hr_seed_ui_done]:
            # pre 1.7.0 compatibility
            with gr.Accordion(label=self.title(), open=False):
                if self.create_ui_cfg_done is None:
                    ui.create_ui_cfg(self)
                    # self.create_ui_cfg()
                if self.create_hr_seed_ui_done is None:
                    ui.create_ui_hr_prompt_mode(self)

        return [
            self.hr_cfg_e,

            self.hr_prompt_mode_e,
            self.hr_negative_prompt_mode_e,

            self.hr_batch_count_e,

            self.enable_hr_seed_e,
            self.hr_seed_e,
            self.hr_seed_checkbox_e,
            self.hr_subseed_e,
            self.hr_subseed_strength_e,
            self.hr_seed_resize_from_w_e,
            self.hr_seed_resize_from_h_e
        ]

    def setup(self, p, *args):
        hr_prompt_mode.setup(self, p, *args)
        hr_cfg_scale.setup(self, p, *args)

    def process(self, p, *args):
        hr_batch_seed.process(self, p, *args)

    def before_process(self, p, *args):
        pass

    def process_batch(self, p, *args, **kwargs):
        hr_cfg_scale.process_batch(self, p, *args, **kwargs)
        hr_batch_seed.process_batch(self, p, *args, **kwargs)

    def before_hr(self, p, *args):
        hr_cfg_scale.before_hr(self, p)

    def postprocess_batch_list(self, p, pp, *args, **kwargs):
        hr_batch_seed.postprocess_batch_list(self, p, pp, *args, **kwargs)

    def postprocess_batch(self, p, *args, **kwargs):
        hr_cfg_scale.postprocess_batch(self, p)
