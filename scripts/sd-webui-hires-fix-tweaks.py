from modules import scripts, shared
import gradio as gr
import re
# import yaml

# settings
shared.options_templates.update(
    shared.options_section(
        ('hires_fix_tweaks', 'Hires. fix tweaks'),
        {
            "hires_fix_tweaks_append_separator":
                shared.OptionInfo(
                    '{newline}',
                    'Append mode insert separator'
                )
                .info('default: "{newline}"'),
            "hires_fix_tweaks_prepend_separator":
                shared.OptionInfo(
                    '{newline}',
                    'Prepend mode insert separator'
                )
                .info('default: "{newline}"'),
            "hires_fix_tweaks_show_hr_cfg":
                shared.OptionInfo(
                    True,
                    'Show hires Hires CFG Scale slider'
                )
                .needs_reload_ui(),
            "hires_fix_tweaks_show_hr_prompt_mode":
                shared.OptionInfo(
                    True,
                    'Show hires Hires prompt mode'
                )
                .info('only shows if "Hires fix: show hires prompt and negative prompt" is also enabled')
                .needs_reload_ui(),
        }
    )
)


def hires_prompt_mode_default(prompt, hr_prompt):
    return prompt, hr_prompt


def hires_prompt_mode_append(prompt, hr_prompt):
    if hr_prompt.strip():
        separator = shared.opts.hires_fix_tweaks_append_separator.format(newline='\n')
        hr_prompt = f'{prompt}{separator}{hr_prompt}'
    return prompt, hr_prompt


def hires_prompt_mode_prepend(prompt, hr_prompt):
    if hr_prompt.strip():
        separator = shared.opts.hires_fix_tweaks_prepend_separator.format(newline='\n')
        hr_prompt = f'{hr_prompt}{separator}{prompt}'
    return prompt, hr_prompt


# search for all line starts with "@marker@", @@ for escaped @
search_replace_instructions_pattern = re.compile(r'^@((?:[^@]|@@)*)@', flags=re.MULTILINE)
# search leading and trailing newlines
remove_1_leading_space_pattern = re.compile(r'^\r?\n?([\W\w]+)\r?\n?$')
# search for escaped @
restore_escaped_at_replace_pattern = re.compile(r'^@@', flags=re.MULTILINE)


def hires_prompt_mode_search_replace(prompt, hr_prompt):
    """
    parse hr_prompt as instructions for search and replace in prompt

    instructions syntax: @search@ replace
    each pare starts with a search value which is denoted by a newline starting with "@key@"
    anything after the search value is the replacement until the next search value
    both search and replace values are can be multi-line
    if search value requires a literal "@" in the prompt, escape it with "@@"
    if replacement value requires a literal @ at the beginning of a new line, escape it with @@

    if "@search@" value is found in prompt, then it performs an "insert"
    whitespace is removed "@search@" from prompt and replace "@search@" in hr_prompt with replace value
    otherwise if @search@ value is not found in prompt, then it performs a "replace"
    replace search in hr_prompt with replace value, the prompt is not modified
    """

    search_replace_list = search_replace_instructions_pattern.split(hr_prompt)[1:]

    hr_prompt = prompt
    for i in range(0, len(search_replace_list), 2):
        # restore escaped }
        key = search_replace_list[i].replace('@@', '@')
        insert_key = f'@{key}@'

        replace = restore_escaped_at_replace_pattern.sub('@', search_replace_list[i + 1])
        replace = remove_1_leading_space_pattern.search(replace).group(1)

        if insert_key in prompt:
            # insert mode: remove @key@ from prompt and replace @key@ in hr_prompt with replacement
            prompt = prompt.replace(insert_key, '')
            hr_prompt = hr_prompt.replace(insert_key, replace)
        else:
            # replace mode: replace insert_marker in hr_prompt with replacement
            hr_prompt = hr_prompt.replace(key, replace)

    # todo remove debug
    print(prompt)
    print('-' * 80)
    print(hr_prompt)
    print('=' * 80)
    return prompt, hr_prompt


hires_prompt_mode_functions = {
    'Default': hires_prompt_mode_default,
    'Append': hires_prompt_mode_append,
    'Prepend': hires_prompt_mode_prepend,
    'Prompt S/R': hires_prompt_mode_search_replace,
}


class Script(scripts.Script):
    def __init__(self):
        self.infotext_fields = []
        self.hr_cfg = None
        self.hr_prompt_mode = None
        self.hr_negative_prompt_mode = None

        self.first_pass_cfg_scale = None

    def title(self):
        return "Hires. fix tweaks"

    def show(self, is_img2img):
        if not is_img2img:
            self.on_after_component_elem_id = [
                ('txt2img_hires_fix_row2', self.create_ui_cfg),
                ('txt2img_hires_fix_row4', self.create_ui_hr_prompt_mode),
            ]
            return scripts.AlwaysVisible

    def create_ui_cfg(self, *args, **kwargs):
        self.hr_cfg = gr.Slider(
            value=0,
            minimum=0,
            maximum=30.0,
            step=0.5,
            label='Hires CFG Scale',
            elem_id="hires_fix_tweaks_txt2img_cfg_scale",
            tooltip="0: same as first pass",
            visible=shared.opts.hires_fix_tweaks_show_hr_cfg
        )
        self.infotext_fields.append((self.hr_cfg, lambda d: d.get('Hires CFG scale', 0)))

    def create_ui_hr_prompt_mode(self, *args, **kwargs):
        with gr.Row():
            self.hr_prompt_mode = gr.Radio(
                choices=list(hires_prompt_mode_functions),
                label='Hires prompt mode', value='Default',
                elem_id="hires_prompt_extend_mode",
                visible=shared.opts.hires_fix_show_prompts and shared.opts.hires_fix_tweaks_show_hr_prompt_mode
            )
            self.hr_negative_prompt_mode = gr.Radio(
                choices=list(hires_prompt_mode_functions),
                label='Hires negative prompt mode', value='Default',
                elem_id="hires_negative_prompt_extend_mode",
                visible=shared.opts.hires_fix_show_prompts and shared.opts.hires_fix_tweaks_show_hr_prompt_mode
            )
            self.infotext_fields.append((self.hr_prompt_mode, lambda d: 'Default'))
            self.infotext_fields.append((self.hr_negative_prompt_mode, lambda d: 'Default'))

    def ui(self, is_img2img):
        if None in [self.hr_cfg, self.hr_prompt_mode]:
            # pre 1.7.0 compatibility
            with gr.Accordion(label=self.title(), open=False):
                if self.hr_cfg is None:
                    self.create_ui_cfg()
                if self.hr_prompt_mode is None or self.hr_negative_prompt_mode is None:
                    self.create_ui_hr_prompt_mode()
        return [self.hr_cfg, self.hr_prompt_mode, self.hr_negative_prompt_mode]

    def setup(self, p, *args):
        p.prompt, p.hr_prompt = hires_prompt_mode_functions.get(args[1], hires_prompt_mode_default)(p.prompt, p.hr_prompt)
        p.negative_prompt, p.hr_negative_prompt = hires_prompt_mode_functions.get(args[2], hires_prompt_mode_default)(p.negative_prompt, p.hr_negative_prompt)

    def before_hr(self, p, *args):
        self.first_pass_cfg_scale = p.cfg_scale
        if args[0] != 0:
            p.cfg_scale = args[0]
            p.extra_generation_params['Hires CFG scale'] = p.cfg_scale

    def postprocess_batch(self, p, *args, **kwargs):
        p.cfg_scale = self.first_pass_cfg_scale
