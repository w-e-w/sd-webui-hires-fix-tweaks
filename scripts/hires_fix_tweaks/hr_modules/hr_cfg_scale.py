def init(self):
    self.apply_hr_cfg_scale = None
    self.first_pass_cfg_scale = None


def setup(self, p, *args):
    p.hr_cfg_scale = args[0]


def process_batch(self, p, *args, **kwargs):
    # p.extra_generation_params
    self.first_pass_cfg_scale = p.cfg_scale
    self.apply_hr_cfg_scale = p.hr_cfg_scale != 0 and p.hr_cfg_scale != self.first_pass_cfg_scale
    if self.apply_hr_cfg_scale:
        p.extra_generation_params['Hires CFG scale'] = p.hr_cfg_scale
    else:
        p.extra_generation_params.pop('Hires CFG scale', None)


def before_hr(self, p):
    if self.apply_hr_cfg_scale:
        p.cfg_scale = p.hr_cfg_scale


def postprocess_batch(self, p):
    if self.apply_hr_cfg_scale:
        p.cfg_scale = self.first_pass_cfg_scale
