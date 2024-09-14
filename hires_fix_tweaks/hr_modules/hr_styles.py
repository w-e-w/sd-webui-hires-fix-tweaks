from modules import patches, processing, shared, script_callbacks
from functools import wraps

try:
    from modules.infotext_versions import v180_hr_styles
    enable_hr_styles_module = True
except ImportError:
    enable_hr_styles_module = False


def parse_infotext(infotext, params):
    if not params.get('Hr styles', False) or not shared.opts.infotext_styles != "Ignore":
        return

    prompt, negative_prompt = params.get('Prompt', ''), params.get('Negative prompt', '')

    found_styles, prompt_no_styles, negative_prompt_no_styles = shared.prompt_styles.extract_styles_from_prompt(prompt, negative_prompt)
    params['Prompt'], params['Negative prompt'] = prompt_no_styles, negative_prompt_no_styles
    if (shared.opts.infotext_styles == "Apply if any" and found_styles) or shared.opts.infotext_styles == "Apply":
        params['Styles array'] = found_styles

    if "Hires prompt" in params or "Hires negative prompt" in params:
        hr_prompt, hr_negative_prompt = params.get("Hires prompt", prompt), params.get("Hires negative prompt", negative_prompt)
        hr_found_styles, hr_prompt_no_styles, hr_negative_prompt_no_styles = shared.prompt_styles.extract_styles_from_prompt(hr_prompt, hr_negative_prompt)
        params["Hires prompt"] = '' if hr_prompt_no_styles == prompt_no_styles else hr_prompt_no_styles
        params['Hires negative prompt'] = '' if hr_negative_prompt_no_styles == negative_prompt_no_styles else hr_negative_prompt_no_styles
        if (shared.opts.infotext_styles == "Apply if any" and hr_found_styles) or shared.opts.infotext_styles == "Apply":
            params['Hires styles array'] = hr_found_styles


def setup(p, *args):
    enable, hr_styles = args[12:14]
    if enable_hr_styles_module and getattr(p, 'enable_hr', False) and enable and p.styles != hr_styles:
        p.hr_tweaks_hr_styles = hr_styles


def wrap_setup_prompts(func):
    @wraps(func)
    def setup_prompts(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        if (hr_tweaks_hr_styles := getattr(self, 'hr_tweaks_hr_styles', None)) is not None:
            self.hr_tweaks_fp_styles = self.styles
            self.styles = hr_tweaks_hr_styles
            self.extra_generation_params['Hr styles'] = True
        return res
    return setup_prompts


def wrap_txt2img_setup_prompts(func):
    @wraps(func)
    def setup_prompts(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        if (hr_tweaks_fp_styles := getattr(self, 'hr_tweaks_fp_styles', None)) is not None:
            self.styles = hr_tweaks_fp_styles
        return res
    return setup_prompts


def patch_setup_prompts():
    try:
        patches.patch(__name__, processing.StableDiffusionProcessing, 'setup_prompts', wrap_setup_prompts(processing.StableDiffusionProcessing.setup_prompts))
        patches.patch(__name__, processing.StableDiffusionProcessingTxt2Img, 'setup_prompts', wrap_txt2img_setup_prompts(processing.StableDiffusionProcessingTxt2Img.setup_prompts))

        def undo_patch():
            patches.undo(__name__, processing.StableDiffusionProcessingTxt2Img, 'setup_prompts')
            patches.undo(__name__, processing.StableDiffusionProcessing, 'setup_prompts')

        script_callbacks.on_script_unloaded(undo_patch)

    except RuntimeError:
        pass
