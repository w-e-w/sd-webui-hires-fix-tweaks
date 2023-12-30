from functools import partial
from modules import scripts

from scripts.hires_fix_tweaks.hr_modules import hr_prompt_mode
from scripts.hires_fix_tweaks.hr_modules import hr_batch_seed
from scripts.hires_fix_tweaks.hr_modules import hr_cfg_scale
from scripts.hires_fix_tweaks import xyz
from scripts.hires_fix_tweaks import ui


class Script(scripts.Script):
    def __init__(self):
        super().__init__()
        self.infotext_fields = []

        ui.init(self)
        hr_cfg_scale.init(self)
        hr_batch_seed.init(self)

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
        ui.fallback_create_ui(self, is_img2img)
        return ui.ui_args(self)

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
