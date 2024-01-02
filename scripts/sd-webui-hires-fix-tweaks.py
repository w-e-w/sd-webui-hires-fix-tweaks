from hires_fix_tweaks.hr_modules import hr_cfg_scale, hr_prompt_mode, hr_batch_seed
from hires_fix_tweaks import ui, xyz, settings  # noqa: F401
from modules import scripts, script_callbacks


class HiresFixTweaks(scripts.Script):
    def __init__(self):
        super().__init__()
        self.infotext_fields = []
        self.on_after_component_elem_id = []
        self.ui_class = ui.UI(self)
        self.hires_cfg_scale = hr_cfg_scale.HiresCFGScale(self)
        self.hires_batch_seed = hr_batch_seed.HiresBatchSeed(self)

    def title(self):
        return 'Hires. fix tweaks'

    def show(self, is_img2img):
        if not is_img2img:
            return scripts.AlwaysVisible

    def ui(self, is_img2img):
        self.ui_class.fallback_create_ui()
        return self.ui_class.ui_args()

    def setup(self, p, *args):
        hr_prompt_mode.setup(p, *args)
        self.hires_cfg_scale.setup(p, *args)
        self.hires_batch_seed.setup(p, *args)

    def process(self, p, *args):
        self.hires_batch_seed.process(p, *args)

    def process_batch(self, p, *args, **kwargs):
        self.hires_cfg_scale.process_batch(p, *args, **kwargs)
        self.hires_batch_seed.process_batch(p, *args, **kwargs)

    def before_hr(self, p, *args):
        self.hires_cfg_scale.before_hr(p)

    def postprocess_batch_list(self, p, pp, *args, **kwargs):
        self.hires_batch_seed.postprocess_batch_list(p, pp, *args, **kwargs)

    def postprocess_batch(self, p, *args, **kwargs):
        self.hires_cfg_scale.postprocess_batch(p)

    def postprocess(self, p, processed, *args):
        self.hires_batch_seed.postprocess(p, processed, *args)


hr_batch_seed.hijack_create_infotext(HiresFixTweaks)
script_callbacks.on_infotext_pasted(hr_batch_seed.pares_infotext)
script_callbacks.on_before_ui(xyz.xyz_grid_axis)
