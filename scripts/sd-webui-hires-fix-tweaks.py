from functools import partial
from modules import scripts
import gradio as gr

from scripts.hires_fix_tweaks.hr_modules import hr_prompt_mode
from scripts.hires_fix_tweaks.hr_modules import hr_batch_seed
from scripts.hires_fix_tweaks.hr_modules import hr_cfg_scale
from scripts.hires_fix_tweaks import xyz
from scripts.hires_fix_tweaks import ui


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
