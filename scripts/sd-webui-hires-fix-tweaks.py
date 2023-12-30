from modules import scripts, shared, script_callbacks, ui_components, ui, errors, processing, patches, generation_parameters_copypaste
from html.parser import HTMLParser
import gradio as gr
import inspect
import random
import re

invalid_marker_character_message = r'''ERROR: invalid marker character
marker character must be a single uncommon character
defaulting to "@"'''


def setup_regex():
    global marker_char, search_replace_instructions_pattern
    if len(shared.opts.hires_fix_tweaks_marker_char) != 1 or re.match(r'[\s\w]', shared.opts.hires_fix_tweaks_marker_char):
        shared.opts.hires_fix_tweaks_marker_char = '@'
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


# search leading and trailing newlines
one_leading_and_trailing_newline_pattern = re.compile(r'^\r?\n?([\W\w]*)\r?\n?$')
search_replace_instructions_pattern: re.Pattern
marker_char: str
setup_regex()


def hires_prompt_mode_search_replace(prompt, hr_prompt):
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
    # even indexes are search value, odd indexes are replace value
    search_replace_instructions_list = search_replace_instructions_pattern.split(hr_prompt)[1:]

    hr_prompt = prompt
    for i in range(0, len(search_replace_instructions_list), 2):
        # restore escaped @
        key = search_replace_instructions_list[i].replace(marker_char * 2, marker_char)
        insert_key = f'{marker_char}{key}{marker_char}'

        # restore escaped @ and remove 1 leading and trailing newline
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


class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_content = ''

    def handle_data(self, data):
        self.text_content += data


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
                ('txt2img_hires_fix_row2', self.create_ui_cfg),
                ('txt2img_hires_fix_row4', self.create_ui_hr_prompt_mode),
            ]
            return scripts.AlwaysVisible

    def create_ui_cfg(self, *args, **kwargs):
        with gr.Row(elem_id=self.elem_id("batch_cfg_row")):
            self.hr_cfg_e = gr.Slider(value=0, minimum=0, maximum=30.0, step=0.5, label='Hires CFG Scale', elem_id=self.elem_id('hr_cfg_scale'), tooltip='0: same as first pass', visible=shared.opts.hires_fix_tweaks_show_hr_cfg)
            self.hr_batch_count_e = gr.Slider(label='Hires batch count', value=1, minimum=1, maximum=64, step=1, elem_id=self.elem_id('batch_count'))
        self.infotext_fields.append((self.hr_cfg_e, lambda d: d.get('Hires CFG scale', 0)))
        self.create_ui_cfg_done = True

    def create_ui_hr_prompt_mode(self, *args, **kwargs):
        gr_ui_element = getattr(gr, shared.opts.hires_fix_tweaks_hires_prompt_mode_ui_type, gr.Radio)
        with gr.Row():
            self.hr_prompt_mode_e = gr_ui_element(
                choices=list(hires_prompt_mode_functions),
                label='Hires prompt mode', value='Default',
                elem_id=self.elem_id('hr_prompt_extend_mode'),
                visible=shared.opts.hires_fix_show_prompts and shared.opts.hires_fix_tweaks_show_hr_prompt_mode
            )
            self.hr_negative_prompt_mode_e = gr_ui_element(
                choices=list(hires_prompt_mode_functions),
                label='Hires negative prompt mode', value='Default',
                elem_id=self.elem_id('hr_negative_prompt_extend_mode'),
                visible=shared.opts.hires_fix_show_prompts and shared.opts.hires_fix_tweaks_show_hr_prompt_mode
            )
            self.infotext_fields.append((self.hr_prompt_mode_e, lambda d: 'Default'))
            self.infotext_fields.append((self.hr_negative_prompt_mode_e, lambda d: 'Default'))

        self.create_hr_seed_ui(self)
        self.create_ui_hr_prompt_mode_done = True

    def create_hr_seed_ui(self, *args, **kwargs):
        with ui_components.InputAccordion(False, label="Hr Seed", elem_id=self.elem_id('custom_seed')) as self.enable_hr_seed_e:  # todo
            # with gr.Row(elem_id=self.elem_id("batch_row")):

            with gr.Row(elem_id=self.elem_id("seed_row")):

                if shared.cmd_opts.use_textbox_seed:
                    self.hr_seed_e = gr.Textbox(label='Hires Seed', value='0', elem_id=self.elem_id("seed"))
                else:
                    self.hr_seed_e = gr.Number(label='Hires Seed', value=0, elem_id=self.elem_id("seed"), precision=0)

                same_seed = ui_components.ToolButton('🟰', elem_id=self.elem_id("same_seed"), tooltip="Set seed to 0, use same seed as the first pass")
                random_seed = ui_components.ToolButton(ui.random_symbol, elem_id=self.elem_id("random_seed"), tooltip="Set seed to -1, which will cause a new random number to be used every time")
                reuse_seed = ui_components.ToolButton(ui.reuse_symbol, elem_id=self.elem_id("reuse_seed"), tooltip="Reuse seed from last generation, mostly useful if it was randomized")

                self.hr_seed_checkbox_e = gr.Checkbox(label='Extra', elem_id=self.elem_id("subseed_show"), value=False)

            with gr.Group(visible=False, elem_id=self.elem_id("seed_extras")) as seed_extras:
                with gr.Row(elem_id=self.elem_id("subseed_row")):
                    if shared.cmd_opts.use_textbox_seed:
                        self.hr_subseed_e = gr.Textbox(label='Hires variation seed', value='0', elem_id=self.elem_id("subseed"))
                    else:
                        self.hr_subseed_e = gr.Number(label='Hires variation seed', value=0, elem_id=self.elem_id("subseed"), precision=0)
                    same_seed_subseed = ui_components.ToolButton('🟰', elem_id=self.elem_id("same_seed_subseed"), tooltip="Set seed to 0, use same seed as the first pass")
                    random_subseed = ui_components.ToolButton(ui.random_symbol, elem_id=self.elem_id("random_subseed"), tooltip="Set seed to -1, which will cause a new random number to be used every time")
                    reuse_subseed = ui_components.ToolButton(ui.reuse_symbol, elem_id=self.elem_id("reuse_subseed"), tooltip="Reuse seed from last generation, mostly useful if it was randomized")
                    self.hr_subseed_strength_e = gr.Slider(label='Hires variation strength', value=0.0, minimum=0, maximum=1, step=0.01, elem_id=self.elem_id("hr_subseed_strength"))

                with gr.Row(elem_id=self.elem_id("seed_resize_from_row")):
                    self.hr_seed_resize_from_w_e = gr.Slider(minimum=0, maximum=2048, step=8, label="Hires resize seed from width", value=0, elem_id=self.elem_id("seed_resize_from_w"))
                    self.hr_seed_resize_from_h_e = gr.Slider(minimum=0, maximum=2048, step=8, label="Hires resize seed from height", value=0, elem_id=self.elem_id("seed_resize_from_h"))

            same_seed.click(fn=None, _js="function(){setInputToValue('" + self.elem_id("seed") + "', '0')}", show_progress=False, inputs=[], outputs=[])
            same_seed_subseed.click(fn=None, _js="function(){setInputToValue('" + self.elem_id("subseed") + "', '0')}", show_progress=False, inputs=[], outputs=[])
            random_seed.click(fn=None, _js="function(){setRandomSeed('" + self.elem_id("seed") + "')}", show_progress=False, inputs=[], outputs=[])
            random_subseed.click(fn=None, _js="function(){setRandomSeed('" + self.elem_id("subseed") + "')}", show_progress=False, inputs=[], outputs=[])

            self.hr_seed_checkbox_e.change(lambda x: gr.update(visible=x), show_progress=False, inputs=[self.hr_seed_checkbox_e], outputs=[seed_extras])

            self.infotext_fields = [
                (self.hr_seed_e, "hr_seed"),
                (self.hr_seed_checkbox_e, lambda d: "hr_variation seed" in d or "hr_seed resize from-1" in d),
                (self.hr_subseed_e, "hr_variation seed"),
                (self.hr_subseed_strength_e, "hr_variation seed strength"),
                (self.hr_seed_resize_from_w_e, "hr_seed resize from-1"),
                (self.hr_seed_resize_from_h_e, "hr_seed resize from-2"),
            ]

            self.on_after_component(lambda x: self.connect_reuse_seed(self.hr_seed_e, reuse_seed, x.component, False), elem_id=f'html_info_{self.tabname}')
            self.on_after_component(lambda x: self.connect_reuse_seed(self.hr_subseed_e, reuse_subseed, x.component, True), elem_id=f'html_info_{self.tabname}')

        self.create_hr_seed_ui_done = True
        # return self.hr_seed_e, self.hr_seed_checkbox_e, self.hr_subseed_e, self.hr_subseed_strength_e, self.hr_seed_resize_from_w_e, self.hr_seed_resize_from_h_e

    def connect_reuse_seed(self, seed: gr.Number, reuse_seed: gr.Button, generation_info: gr.Textbox, is_subseed):

        def copy_seed(html_content: str, index):
            res = 0
            infotext_skip_pasting = shared.opts.infotext_skip_pasting
            try:
                parser = SimpleHTMLParser()
                parser.feed(html_content)
                shared.opts.infotext_skip_pasting = []
                parameters = generation_parameters_copypaste.parse_generation_parameters(parser.text_content)
                res = int(parameters.get('hr_subseed' if is_subseed else 'hr_seed', res))

            except Exception as e:
                errors.report(f"Error parsing generation info: {html_content}")
            finally:
                shared.opts.infotext_skip_pasting = infotext_skip_pasting
            return [res, gr.update()]

        reuse_seed.click(
            fn=copy_seed,
            _js="(x, y) => [x, selected_gallery_index()]",
            show_progress=False,
            inputs=[generation_info, seed],
            outputs=[seed, seed]
        )

    def ui(self, is_img2img):
        if None in [self.create_ui_cfg_done, self.create_hr_seed_ui_done]:
            # pre 1.7.0 compatibility
            with gr.Accordion(label=self.title(), open=False):
                if self.create_ui_cfg_done is None:
                    self.create_ui_cfg()
                if self.create_hr_seed_ui_done is None:
                    self.create_ui_hr_prompt_mode()

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
        p.prompt, p.hr_prompt = hires_prompt_mode_functions.get(args[1], hires_prompt_mode_default)(p.prompt, p.hr_prompt)
        p.negative_prompt, p.hr_negative_prompt = hires_prompt_mode_functions.get(args[2], hires_prompt_mode_default)(p.negative_prompt, p.hr_negative_prompt)
        p.hr_cfg_scale = args[0]
        # self.ui_args = args
        self.hr_batch_count = args[3]
        # self.batch_size = p.batch_size

    def before_process(self, p, *args):
        self.enable_hr_seed = args[4]
        if self.enable_hr_seed:
            self.hr_seed = args[5]
            self.hr_seed_enable_extras = args[6]
            if self.hr_seed_enable_extras:
                self.hr_subseed = args[7]
                self.hr_subseed_strength = args[8]
                self.hr_seed_resize_from_w = args[9]
                self.hr_seed_resize_from_h = args[10]
            else:
                self.hr_subseed = 0
                self.hr_subseed_strength = 0
                self.hr_seed_resize_from_w = 0
                self.hr_seed_resize_from_h = 0
            if p.enable_hr:
                # use to write hr info to params.txt
                p.force_write_hr_info_flag = True
        else:
            # enable_hr_seed is false use first pass seed
            self.hr_seed = 0
            self.hr_subseed = 0
            self.hr_subseed_strength = p.subseed_strength
            self.hr_seed_resize_from_w = p.seed_resize_from_w
            self.hr_seed_resize_from_h = p.seed_resize_from_h


        # print(p.all_prompts)
        p.sample_hr_pass = self.sample_hr_pass_hijack(p, p.sample_hr_pass)
        p.sample = self.sample_hijack(p, p.sample)
        # p.js = self.js_hijack(p.js)
        pass

    def init_hr_seeds(self, p):
        if isinstance(self.hr_seed, str):
            try:
                self.hr_seed = int(self.hr_seed)
            except Exception:
                self.hr_seed = 0

        if self.hr_seed == 0:
            self.all_hr_seeds = p.all_seeds
            self.hr_seed_resize_from_w = p.seed_resize_from_w
            self.hr_seed_resize_from_h = p.seed_resize_from_h
        else:
            seed = int(random.randrange(4294967294)) if self.hr_seed == -1 else self.hr_seed
            self.all_hr_seeds = [int(seed) + (x if self.hr_subseed_strength == 0 else 0) for x in range(len(p.all_seeds))]

        if isinstance(self.hr_subseed, str):
            try:
                self.hr_subseed = int(self.hr_subseed)
            except Exception:
                self.hr_subseed = 0

        if self.hr_subseed == 0:
            self.all_hr_subseeds = p.all_subseeds
        else:
            subseed = int(random.randrange(4294967294)) if self.hr_seed == -1 else self.hr_subseed
            self.all_hr_subseeds = [int(subseed) + x for x in range(len(p.all_subseeds))]

    def process_batch(self, p, *args, **kwargs):
        self.first_pass_cfg_scale = p.cfg_scale
        self.apply_hr_cfg_scale = p.hr_cfg_scale != 0 and p.hr_cfg_scale != self.first_pass_cfg_scale
        if self.apply_hr_cfg_scale:
            p.extra_generation_params['Hires CFG scale'] = p.hr_cfg_scale
        else:
            p.extra_generation_params.pop('Hires CFG scale', None)

        # init hr seeds


        self.init_hr_seeds(p)

        # if p.enable_hr and getattr(p, 'force_write_hr_info_flag', False):
        if p.enable_hr:
            p.hr_seeds = self.all_hr_seeds
            p.hr_subseeds = self.all_hr_subseeds
            p.hr_subseed_strength = self.hr_subseed_strength
            p.hr_seed_resize_from_w = self.hr_seed_resize_from_w
            p.hr_seed_resize_from_h = self.hr_seed_resize_from_h

    def sample_hijack(self, p, sample):
        def wrapped_function(*args, **kwargs):
            p.force_write_hr_info_flag = False
            result = sample(*args, **kwargs)
            return result
        return wrapped_function

    def sample_hr_pass_hijack(self, p, sample_hr_pass):
        def wrapped_function(*args, **kwargs):
            self.first_pass_seeds = p.seeds
            self.first_pass_subseeds = p.subseeds
            self.first_pass_subseed_strength = p.subseed_strength
            self.first_pass_seed_resize_from_w = p.seed_resize_from_w
            self.first_pass_seed_resize_from_h = p.seed_resize_from_h

            samples = processing.DecodedSamples()
            save_images_before_highres_fix = shared.opts.save_images_before_highres_fix
            #
            # self.all_hr_seeds
            # self.all_hr_subseed

            p.hr_seeds = []
            p.hr_subseeds = []
            print('p.seeds', p.seeds, len(p.seeds), 'p.batch_size', p.batch_size)


            hr_seeds_batch = self.all_hr_seeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]
            hr_subseeds_batch = self.all_hr_subseeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]
            # p.seeds = p.all_seeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]
            # p.subseeds = p.all_subseeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]

            p.subseed_strength = p.hr_subseed_strength
            p.seed_resize_from_w = self.hr_seed_resize_from_w
            p.seed_resize_from_h = self.hr_seed_resize_from_h

            try:
                for index in range(self.hr_batch_count):
                    # p.seeds = [seed + index for seed in self.first_pass_seeds]
                    p.seeds = [seed + index for seed in hr_seeds_batch]
                    p.hr_seeds.extend(p.seeds)
                    # p.hr_seeds = p.seeds
                    #
                    # p.subseeds = [subseed + index for subseed in self.first_pass_subseeds]
                    p.subseeds = [subseed + index for subseed in hr_subseeds_batch]
                    p.hr_subseeds.extend(p.subseeds)
                    # p.hr_subseeds = p.subseeds

                    result = sample_hr_pass(*args, **kwargs)
                    samples.extend(result)
                    # disable saving images before highres fix for all but the first batch
                    shared.opts.save_images_before_highres_fix = False

            finally:
                p.seeds = self.first_pass_seeds
                p.subseeds = self.first_pass_subseeds
                p.subseed_strength = self.first_pass_subseed_strength
                p.seed_resize_from_w = self.first_pass_seed_resize_from_w
                p.seed_resize_from_h = self.first_pass_seed_resize_from_h

                # restore original shared.opts.save_images_before_highres_fix setting
                shared.opts.save_images_before_highres_fix = save_images_before_highres_fix
                return samples

        return wrapped_function

    # def js_hijack(self, js):
    #     def wrapped_function(*args, **kwargs):
    #         original_json_dumps = json.dumps
    #         json.dumps = self.json_dumps_hijack(json.dumps)
    #         try:
    #             result = js(*args, **kwargs)
    #         finally:
    #             json.dumps = original_json_dumps
    #         return result
    #     return wrapped_function

    # def json_dumps_hijack(self, json_dunps):
    #     json_dunps_signature = inspect.signature(json_dunps)
    #
    #     def wrapped_function(*args, **kwargs):
    #         try:
    #             print('json_dumps_hijack---')
    #             bind_args = json_dunps_signature.bind(*args, **kwargs)
    #             bind_args.apply_defaults()
    #             bind_args = bind_args.arguments
    #             bind_args['obj']['all_hr_seeds'] = self.all_hr_seeds
    #             bind_args['obj']['all_hr_subseeds'] = self.all_hr_subseeds
    #             bind_args['obj']['hr_subseed_strength'] = self.hr_subseed_strength
    #             print('===json_dumps_hijack')
    #         finally:
    #             return json_dunps(*args, **kwargs)
    #     return wrapped_function

    def before_hr(self, p, *args):
        if self.apply_hr_cfg_scale:
            p.cfg_scale = p.hr_cfg_scale

    def postprocess_batch_list(self, p, pp, *args, **kwargs):
        p.prompts = p.prompts * self.hr_batch_count
        p.negative_prompts = p.negative_prompts * self.hr_batch_count
        p.seeds = p.seeds * self.hr_batch_count
        p.subseeds = p.subseeds * self.hr_batch_count

    def postprocess_batch(self, p, *args, **kwargs):
        if self.apply_hr_cfg_scale:
            p.cfg_scale = self.first_pass_cfg_scale


# XYZ grid support
def xyz_grid_axis():
    for data in scripts.scripts_data:
        if data.script_class.__module__ == 'xyz_grid.py' and hasattr(data, 'module'):
            xyz_grid = data.module
            xyz_grid.axis_options.extend(
                [
                    xyz_grid.AxisOptionTxt2Img('Hires CFG Scale', float, xyz_grid.apply_field('hr_cfg_scale')),
                ]
            )
            break


script_callbacks.on_before_ui(xyz_grid_axis)


# settings
shared.options_templates.update(
    shared.options_section(
        ('hires_fix_tweaks', 'Hires. fix tweaks'),
        {
            'hires_fix_tweaks_append_separator':
                shared.OptionInfo(
                    '{newline}',
                    'Append mode insert separator',
                )
                .info('default: "{newline}"'),
            'hires_fix_tweaks_prepend_separator':
                shared.OptionInfo(
                    '{newline}',
                    'Prepend mode insert separator',
                )
                .info('default: "{newline}"'),
            'hires_fix_tweaks_show_hr_cfg':
                shared.OptionInfo(
                    True,
                    'Show hires Hires CFG Scale slider',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_show_hr_prompt_mode':
                shared.OptionInfo(
                    True,
                    'Show hires Hires prompt mode',
                )
                .info('only shows if "Hires fix: show hires prompt and negative prompt" is also enabled')
                .needs_reload_ui(),
            'hires_fix_tweaks_marker_char':
                shared.OptionInfo(
                    '@',
                    'Hires fix search/replace syntax '
                    'marker character',
                    onchange=setup_regex,
                )
                .info('default: "@", can be changed other characters if the default is causing issues, must be a single uncommon character'),
            'hires_fix_tweaks_hires_prompt_mode_ui_type':
                shared.OptionInfo(
                    'Radio', 'text', gr.Radio,
                    {'choices': ['Radio', 'Dropdown']},
                )
                .needs_reload_ui()

        }
    )
)


# def add_hr_seed_info(p, index):
#     if hasattr(p, 'hr_seeds') and p.seeds[index] != p.hr_seeds[index]:
#         p.extra_generation_params['hr_seed'] = p.hr_seeds[index]
#     else:
#         p.extra_generation_params.pop('hr_seed', None)
#
#     if hasattr(p, 'hr_subseeds') and p.subseeds[index] != p.hr_subseeds[index] and p.hr_subseed_strength != 0:
#         p.extra_generation_params['hr_subseed'] = p.hr_subseeds[index]
#     else:
#         p.extra_generation_params.pop('hr_subseed', None)
#
#     if hasattr(p, 'hr_seed_resize_from_w') and hasattr(p, 'hr_seed_resize_from_h') and p.hr_seed_resize_from_w > 0 and p.hr_seed_resize_from_h > 0:
#         p.extra_generation_params['hr seed resize from'] = f"{p.hr_seed_resize_from_w}x{p.hr_seed_resize_from_h}"
#     else:
#         p.extra_generation_params.pop('hr seed resize from', None)

def create_infotext_hijack(create_infotext):
    create_infotext_signature = inspect.signature(create_infotext)

    def wrapped_function(*args, **kwargs):
        try:
            bind_args = create_infotext_signature.bind(*args, **kwargs)
            bind_args.apply_defaults()
            bind_args = bind_args.arguments

            p = bind_args['p']
            # iteration = bind_args['iteration']
            # position_in_batch = bind_args['position_in_batch']
            index = bind_args['index']
            use_main_prompt = bind_args['use_main_prompt']

            try:
                if use_main_prompt or getattr(p, 'force_write_hr_info_flag', None):
                    index = 0
                elif index is None:
                    assert False, 'index is None'
                    # index = position_in_batch + iteration * p.batch_size
                # add_hr_seed_info(p, index)
                if hasattr(p, 'hr_seeds') and p.seeds[index] != p.hr_seeds[index]:
                    p.extra_generation_params['hr_seed'] = p.hr_seeds[index]
                else:
                    p.extra_generation_params.pop('hr_seed', None)

                # todo fix subseed

                if hasattr(p, 'hr_subseeds') and p.subseeds[index] != p.hr_subseeds[index] and p.hr_subseed_strength != 0:
                    p.extra_generation_params['hr_subseed'] = p.hr_subseeds[index]
                else:
                    p.extra_generation_params.pop('hr_subseed', None)

                if hasattr(p, 'hr_seed_resize_from_w') and hasattr(p, 'p.hr_seed_resize_from_h') and p.hr_seed_resize_from_w > 0 and p.hr_seed_resize_from_h > 0:
                    p.extra_generation_params['hr seed resize from'] = f"{p.hr_seed_resize_from_w}x{p.hr_seed_resize_from_h}"
                else:
                    p.extra_generation_params.pop('hr seed resize from', None)
            except Exception as e:
                errors.report(f"not results: {e}")
                for key in ['hr_seed', 'hr_subseed', 'hr seed resize from']:
                    p.extra_generation_params.pop(key, None)
                pass

        except Exception as e:
            errors.report(f"create infotext hijack failed: {e}")
            pass

        finally:
            results = create_infotext(*args, **kwargs)
            return results

    return wrapped_function


try:
    patches.patch(key=__name__, obj=processing, field='create_infotext', replacement=create_infotext_hijack(processing.create_infotext))
except RuntimeError:
    pass
