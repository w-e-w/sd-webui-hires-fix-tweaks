from hires_fix_tweaks.hr_modules import hr_prompt_mode
from hires_fix_tweaks.hr_modules import hr_batch_seed
from modules import generation_parameters_copypaste  # noqa: generation_parameters_copypaste is the ailes to infotext_utils
from modules import shared, ui_components, ui
from contextlib import nullcontext
import gradio as gr
import json

try:
    from modules.ui_components import InputAccordion
except ImportError:
    InputAccordion = None


def connect_reuse_seed(seed, reuse_seed: gr.Button, generation_info: gr.Textbox, is_subseed):
    def copy_seed(gen_info_string: str, index):
        infotext_skip_pasting = shared.opts.infotext_skip_pasting
        try:
            gen_info = json.loads(gen_info_string)
            infotext = gen_info['infotexts'][index]
            shared.opts.infotext_skip_pasting = []
            gen_parameters = generation_parameters_copypaste.parse_generation_parameters(infotext)
            hr_batch_seed.pares_infotext(None, gen_parameters)
            res = int(gen_parameters['Hires seed']['Subseed' if is_subseed else 'Seed'])
        except Exception:
            res = 0
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
        self.remove_fp_extra_networks_e = None

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
            self.remove_fp_extra_networks_e,
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
            self.hr_seed_resize_from_h_e,
        ]

    def fallback_create_ui(self):
        global InputAccordion
        if None in [self.create_ui_cfg_done, self.create_hr_seed_ui_done]:
            # pre 1.7.0 compatibility
            InputAccordion = None
            with gr.Accordion(label=self.script.title(), open=False):
                self.create_ui_batch_cfg()
                self.create_ui_hr_prompt_mode()

    def create_ui_hr_prompt_mode(self, *args, **kwargs):
        if self.create_ui_hr_prompt_mode_done:
            return
        gr_ui_element = getattr(gr, shared.opts.hires_fix_tweaks_hires_prompt_mode_ui_type, gr.Radio)
        with gr.Row() if (shared.opts.hires_fix_tweaks_show_hr_prompt_mode or shared.opts.hires_fix_tweaks_show_hr_remove_fp_extra_networks) else nullcontext():
            self.remove_fp_extra_networks_e = gr.Checkbox(label='Remove First Pass Extra Networks', value=False, elem_id=self.script.elem_id('remove_fp_extra_networks'), elem_classes=['hr-tweaks-center-checkbox'], tooltip='Remove extra networks from first-pass prompt before constructing hires-prompt', visible=shared.opts.hires_fix_tweaks_show_hr_remove_fp_extra_networks)
            self.hr_prompt_mode_e = gr_ui_element(choices=list(hr_prompt_mode.hires_prompt_mode_functions), label='Hires prompt mode', value='Default', elem_id=self.script.elem_id('hr_prompt_extend_mode'), elem_classes=['hr-prompt-extend-mode'] if shared.opts.hires_fix_tweaks_show_hr_remove_fp_extra_networks else [], visible=shared.opts.hires_fix_tweaks_show_hr_prompt_mode)
            self.hr_negative_prompt_mode_e = gr_ui_element(choices=list(hr_prompt_mode.hires_prompt_mode_functions), label='Hires negative prompt mode', value='Default', elem_id=self.script.elem_id('hr_negative_prompt_extend_mode'), elem_classes=['hr-prompt-extend-mode'] if shared.opts.hires_fix_tweaks_show_hr_remove_fp_extra_networks else [], visible=shared.opts.hires_fix_tweaks_show_hr_prompt_mode)
        if shared.opts.hires_fix_tweaks_show_hr_prompt_mode and not shared.opts.hires_fix_show_prompts:
            with gr.Row():
                gr.Markdown('''`Hires prompt mode` is only useful if `Settings` > `UI alternatives` > `Hires fix: show hires prompt and negative prompt` is enabled
if you do not need this feature you can disable it in `Settings` > `Hires. fix tweaks` > `Show hires Hires prompt mode`''')
            self.script.infotext_fields.extend([
                (self.remove_fp_extra_networks_e, False),
                (self.hr_prompt_mode_e, lambda d: 'Default'),
                (self.hr_negative_prompt_mode_e, lambda d: 'Default'),
            ])
        self.create_hr_seed_ui()
        self.create_ui_hr_prompt_mode_done = True

    def create_ui_batch_cfg(self, *args, **kwargs):
        if self.create_ui_cfg_done:
            return
        with gr.Row(elem_id=self.script.elem_id("batch_cfg_row")) if shared.opts.hires_fix_tweaks_show_hr_cfg or shared.opts.hires_fix_tweaks_show_hr_batch_seed else nullcontext():
            with gr.Column(scale=8) if shared.opts.hires_fix_tweaks_show_hr_cfg else nullcontext():
                self.hr_cfg_e = gr.Slider(value=0, minimum=0, maximum=30.0, step=0.5, label='Hires CFG Scale', elem_id=self.script.elem_id('hr_cfg_scale'), tooltip='0: same as first pass', visible=shared.opts.hires_fix_tweaks_show_hr_cfg)
            with gr.Column(min_width=200) if shared.opts.hires_fix_tweaks_show_hr_batch_seed else nullcontext():
                self.hr_batch_count_e = gr.Slider(label='Hires batch count', value=1, minimum=1, maximum=16, step=1, elem_id=self.script.elem_id('batch_count'), visible=shared.opts.hires_fix_tweaks_show_hr_batch_seed)
            self.script.infotext_fields.append((self.hr_cfg_e, lambda d: d.get('Hires CFG scale', 0)))
        self.create_ui_cfg_done = True

    def create_hr_seed_ui(self, *args, **kwargs):
        if self.create_hr_seed_ui_done:
            return
        with (
            ui_components.InputAccordion(False, label="Hires Seed", elem_id=self.script.elem_id('custom_seed'), visible=shared.opts.hires_fix_tweaks_show_hr_batch_seed) if InputAccordion
            else gr.Accordion('Hires Seed', open=False, elem_id=self.script.elem_id('custom_seed'))
            as self.enable_hr_seed_e
        ):
            with gr.Row(elem_id=self.script.elem_id("seed_row")):
                if not InputAccordion:
                    # pre 1.7.0 compatibility
                    self.enable_hr_seed_e = gr.Checkbox(label='Enable', elem_id=self.script.elem_id("enable_hr_seed_subseed_show"), value=False)
                    # the elem_id suffix is used _subseed_show to apply the [id$=_subseed_show] css rule
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
                    (self.enable_hr_seed_e, lambda d: 'Hires seed' in d),
                    (self.hr_seed_e, lambda d: d.get('Hires seed', {}).get('Seed', 0)),
                    (self.hr_seed_checkbox_e, lambda d: any(map(d.get('Hires seed', {}).__contains__, ['Strength', 'Resize']))),
                    (self.hr_subseed_e, lambda d: d.get('Hires seed', {}).get('Subseed', 0)),
                    (self.hr_subseed_strength_e, lambda d: d.get('Hires seed', {}).get('Strength', 0)),
                    (self.hr_seed_resize_from_w_e, lambda d: d.get('Hires seed', {}).get('Resize', [0, None])[0]),
                    (self.hr_seed_resize_from_h_e, lambda d: d.get('Hires seed', {}).get('Resize', [None, 0])[1]),
                ]
            )

            self.script.on_after_component(lambda x: connect_reuse_seed(self.hr_seed_e, reuse_seed, x.component, False), elem_id=f'generation_info_{self.script.tabname}')
            self.script.on_after_component(lambda x: connect_reuse_seed(self.hr_subseed_e, reuse_subseed, x.component, True), elem_id=f'generation_info_{self.script.tabname}')

        self.create_hr_seed_ui_done = True
