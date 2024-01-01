from modules import shared, ui_components, ui, errors, generation_parameters_copypaste
from hires_fix_tweaks.hr_modules import hr_prompt_mode
from hires_fix_tweaks.hr_modules import hr_batch_seed
# from scripts.hires_fix_tweaks.hr_modules import hr_cfg_scale
import gradio as gr


def connect_reuse_seed(seed, reuse_seed: gr.Button, generation_info: gr.Textbox, is_subseed):
    def copy_seed(html_content: str, index):
        res = 0
        infotext_skip_pasting = shared.opts.infotext_skip_pasting
        try:
            parser = hr_batch_seed.SimpleHTMLParser()
            parser.feed(html_content)
            shared.opts.infotext_skip_pasting = []
            parameters = generation_parameters_copypaste.parse_generation_parameters(parser.text_content)
            res = int(parameters.get('hr_subseed' if is_subseed else 'hr_seed', res))
        except Exception as _:
            errors.report(f"Error parsing generation info: {html_content}")
        finally:
            shared.opts.infotext_skip_pasting = infotext_skip_pasting
        return [res, gr.update()]
    reuse_seed.click(fn=copy_seed, _js="(x, y) => [x, selected_gallery_index()]", show_progress=False, inputs=[generation_info, seed], outputs=[seed, seed])


class UI:
    def __init__(self, script):
        self.script = script
        self.script.on_after_component_elem_id.append(('txt2img_hires_fix_row2', self.create_ui_batch_cfg))
        self.script.on_after_component_elem_id.append(('txt2img_hires_fix_row4', self.create_ui_hr_prompt_mode))
        # ui create status
        self.create_ui_cfg_done = None
        self.create_ui_hr_prompt_mode_done = None
        self.create_hr_seed_ui_done = None

        # gradio elements
        # hr cfg scale
        self.hr_cfg_e = None

        # hr prompt mode
        self.hr_prompt_mode_e = None
        self.hr_negative_prompt_mode_e = None

        # hr batch and seed
        self.hr_batch_count_e = None
        self.enable_hr_seed_e = None
        self.hr_seed_e = None
        self.hr_seed_checkbox_e = None
        self.hr_subseed_e = None
        self.hr_subseed_strength_e = None
        self.hr_seed_resize_from_h_e = None
        self.hr_seed_resize_from_w_e = None

    def ui_args(self):
        return [
            # hr cfg scale
            self.hr_cfg_e,

            # hr prompt mode
            self.hr_prompt_mode_e,
            self.hr_negative_prompt_mode_e,

            # hr batch and seed
            self.hr_batch_count_e,
            self.enable_hr_seed_e,
            self.hr_seed_e,
            self.hr_seed_checkbox_e,
            self.hr_subseed_e,
            self.hr_subseed_strength_e,
            self.hr_seed_resize_from_w_e,
            self.hr_seed_resize_from_h_e
        ]

    def fallback_create_ui(self):
        if None in [self.create_ui_cfg_done, self.create_hr_seed_ui_done]:
            # pre 1.7.0 compatibility
            with gr.Accordion(label=self.script.title(), open=False):
                self.create_ui_batch_cfg()
                self.create_ui_hr_prompt_mode()

    def create_ui_hr_prompt_mode(self, *args, **kwargs):
        if self.create_ui_hr_prompt_mode_done:
            return
        gr_ui_element = getattr(gr, shared.opts.hires_fix_tweaks_hires_prompt_mode_ui_type, gr.Radio)
        with gr.Row():
            self.hr_prompt_mode_e = gr_ui_element(choices=list(hr_prompt_mode.hires_prompt_mode_functions), label='Hires prompt mode', value='Default', elem_id=self.script.elem_id('hr_prompt_extend_mode'), visible=shared.opts.hires_fix_tweaks_show_hr_prompt_mode)
            self.hr_negative_prompt_mode_e = gr_ui_element(choices=list(hr_prompt_mode.hires_prompt_mode_functions), label='Hires negative prompt mode', value='Default', elem_id=self.script.elem_id('hr_negative_prompt_extend_mode'), visible=shared.opts.hires_fix_tweaks_show_hr_prompt_mode)
        if shared.opts.hires_fix_tweaks_show_hr_prompt_mode and not shared.opts.hires_fix_show_prompts:
            with gr.Row():
                gr.Markdown('''`Hires prompt mode` is only useful if `Settings` > `UI alternatives` > `Hires fix: show hires prompt and negative prompt` is enabled
if you do not need this feature you can disable it in `Settings` > `Hires. fix tweaks` > `Show hires Hires prompt mode`''')
            self.script.infotext_fields.extend([
                (self.hr_prompt_mode_e, lambda d: 'Default'),
                (self.hr_negative_prompt_mode_e, lambda d: 'Default'),
            ])
        self.create_hr_seed_ui()
        self.create_ui_hr_prompt_mode_done = True

    def create_ui_batch_cfg(self, *args, **kwargs):
        if self.create_ui_cfg_done:
            return
        with gr.Row(elem_id=self.script.elem_id("batch_cfg_row")):
            self.hr_cfg_e = gr.Slider(value=0, minimum=0, maximum=30.0, step=0.5, label='Hires CFG Scale', elem_id=self.script.elem_id('hr_cfg_scale'), tooltip='0: same as first pass', visible=shared.opts.hires_fix_tweaks_show_hr_cfg)
            self.hr_batch_count_e = gr.Slider(label='Hires batch count', value=1, minimum=1, maximum=64, step=1, elem_id=self.script.elem_id('batch_count'))
            self.script.infotext_fields.append((self.hr_cfg_e, lambda d: d.get('Hires CFG scale', 0)))
        self.create_ui_cfg_done = True

    def create_hr_seed_ui(self, *args, **kwargs):
        if self.create_hr_seed_ui_done:
            return
        with ui_components.InputAccordion(False, label="Hr Seed", elem_id=self.script.elem_id('custom_seed')) as self.enable_hr_seed_e:
            with gr.Row(elem_id=self.script.elem_id("seed_row")):
                if shared.cmd_opts.use_textbox_seed:
                    self.hr_seed_e = gr.Textbox(label='Hires Seed', value='0', elem_id=self.script.elem_id("seed"))
                else:
                    self.hr_seed_e = gr.Number(label='Hires Seed', value=0, elem_id=self.script.elem_id("seed"), precision=0)

                same_seed = ui_components.ToolButton('🟰', elem_id=self.script.elem_id("same_seed"), tooltip="Set seed to 0, use same seed as the first pass")
                random_seed = ui_components.ToolButton(ui.random_symbol, elem_id=self.script.elem_id("random_seed"), tooltip="Set seed to -1, which will cause a new random number to be used every time")
                reuse_seed = ui_components.ToolButton(ui.reuse_symbol, elem_id=self.script.elem_id("reuse_seed"), tooltip="Reuse seed from last generation, mostly useful if it was randomized")

                self.hr_seed_checkbox_e = gr.Checkbox(label='Extra', elem_id=self.script.elem_id("subseed_show"), value=False)

            with gr.Group(visible=False, elem_id=self.script.elem_id("seed_extras")) as seed_extras:
                with gr.Row(elem_id=self.script.elem_id("subseed_row")):
                    if shared.cmd_opts.use_textbox_seed:
                        self.hr_subseed_e = gr.Textbox(label='Hires variation seed', value='0', elem_id=self.script.elem_id("subseed"))
                    else:
                        self.hr_subseed_e = gr.Number(label='Hires variation seed', value=0, elem_id=self.script.elem_id("subseed"), precision=0)
                    same_seed_subseed = ui_components.ToolButton('🟰', elem_id=self.script.elem_id("same_seed_subseed"), tooltip="Set seed to 0, use same seed as the first pass")
                    random_subseed = ui_components.ToolButton(ui.random_symbol, elem_id=self.script.elem_id("random_subseed"), tooltip="Set seed to -1, which will cause a new random number to be used every time")
                    reuse_subseed = ui_components.ToolButton(ui.reuse_symbol, elem_id=self.script.elem_id("reuse_subseed"), tooltip="Reuse seed from last generation, mostly useful if it was randomized")
                    self.hr_subseed_strength_e = gr.Slider(label='Hires variation strength', value=0.0, minimum=0, maximum=1, step=0.01, elem_id=self.script.elem_id("hr_subseed_strength"))

                with gr.Row(elem_id=self.script.elem_id("seed_resize_from_row")):
                    self.hr_seed_resize_from_w_e = gr.Slider(minimum=0, maximum=2048, step=8, label="Hires resize seed from width", value=0, elem_id=self.script.elem_id("seed_resize_from_w"))
                    self.hr_seed_resize_from_h_e = gr.Slider(minimum=0, maximum=2048, step=8, label="Hires resize seed from height", value=0, elem_id=self.script.elem_id("seed_resize_from_h"))

            same_seed.click(fn=None, _js="function(){setInputToValue('" + self.script.elem_id("seed") + "', '0')}", show_progress=False, inputs=[], outputs=[])
            same_seed_subseed.click(fn=None, _js="function(){setInputToValue('" + self.script.elem_id("subseed") + "', '0')}", show_progress=False, inputs=[], outputs=[])
            random_seed.click(fn=None, _js="function(){setRandomSeed('" + self.script.elem_id("seed") + "')}", show_progress=False, inputs=[], outputs=[])
            random_subseed.click(fn=None, _js="function(){setRandomSeed('" + self.script.elem_id("subseed") + "')}", show_progress=False, inputs=[], outputs=[])

            self.hr_seed_checkbox_e.change(lambda x: gr.update(visible=x), show_progress=False, inputs=[self.hr_seed_checkbox_e], outputs=[seed_extras])

            self.script.infotext_fields.extend(
                [
                    (self.enable_hr_seed_e, lambda d: 'Hires seed info' in d),
                    (self.hr_seed_e, lambda d: d.get('Hires seed info', {}).get('Seed', 0)),
                    (self.hr_seed_checkbox_e, lambda d: any(map(d.get('Hires seed info', {}).__contains__, ['Strength', 'Resize']))),
                    (self.hr_subseed_e, lambda d: d.get('Hires seed info', {}).get('Subseed', 0)),
                    (self.hr_subseed_strength_e, lambda d: d.get('Hires seed info', {}).get('Strength', 0)),
                    (self.hr_seed_resize_from_w_e, lambda d: d.get('Hires seed info', {}).get('Resize', [0, None])[0]),
                    (self.hr_seed_resize_from_h_e, lambda d: d.get('Hires seed info', {}).get('Resize', [None, 0])[1]),
                ]
            )

            self.script.on_after_component(lambda x: connect_reuse_seed(self.hr_seed_e, reuse_seed, x.component, False), elem_id=f'html_info_{self.script.tabname}')
            self.script.on_after_component(lambda x: connect_reuse_seed(self.hr_subseed_e, reuse_subseed, x.component, True), elem_id=f'html_info_{self.script.tabname}')

        self.create_hr_seed_ui_done = True


hr_seed_extras = ['Hires variation seed', 'Hires variation seed strength', 'Hires seed resize from-1']


def get_extra_seed_value(d, hr_key, fp_key):
    if 'Hires seed' in d:
        pass

    if any(map(d.__contains__, ['Hires variation seed', 'Hires variation seed strength', 'Hires seed resize from-1'])):
        # hires seed extra check box enabled
        value = d.get(hr_key)
        if value is None:
            value = d.get(fp_key, 0)
        return value
    return 0
