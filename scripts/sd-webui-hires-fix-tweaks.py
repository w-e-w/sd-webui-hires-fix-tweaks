from modules import scripts, shared
import gradio as gr
import yaml

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
    separator = shared.opts.hires_fix_tweaks_append_separator.format(newline='\n')
    hr_prompt = f'{prompt}{separator}{hr_prompt}'
    return prompt, hr_prompt


def hires_prompt_mode_prepend(prompt, hr_prompt):
    separator = shared.opts.hires_fix_tweaks_prepend_separator.format(newline='\n')
    hr_prompt = f'{hr_prompt}{separator}{prompt}'
    return prompt, hr_prompt


# search for all line starts with "{marker}"
# pattern = re.compile(r'^{([^}]+)}', flags=re.MULTILINE)


def hires_prompt_mode_search_replace(prompt, hr_prompt):
    prompt_copy, hr_prompt_copy = prompt, hr_prompt
    try:
        replacement_list = yaml.safe_load(hr_prompt)
        for replacement in replacement_list:
            search_list, replace = (replacement[:-1], replacement[-1]) if len(replacement) > 1 else (replacement, None)
            if replace is None:
                replace = ''
            for search in search_list:
                if search is None:
                    continue
                search_insert = f'{{{search}}}'
                if search_insert in prompt:
                    hr_prompt = prompt.replace(search_insert, replace)
                    prompt = prompt.replace(search_insert, '')
                else:
                    hr_prompt = prompt.replace(search, replace)
        return prompt, hr_prompt
    except yaml.YAMLError as e:
        print('yaml error:', e)
    except Exception as e:
        print(e)
    return prompt_copy, hr_prompt_copy


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
