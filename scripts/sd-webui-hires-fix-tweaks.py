from modules import scripts
import gradio as gr


class Script(scripts.Script):


    hr_cfg = None
    first_pass_cfg_scale = 0

    def title(self):
        return "Hires. fix tweaks"

    def show(self, is_img2img):
        if not is_img2img:
            # self.on_before_component_elem_id = [
            #     ('txt2img_hires_fix_row4', self.before_hires_fix_extended_ui),
            # ]
            self.on_after_component_elem_id = [
                ('txt2img_hires_fix_row4', self.after_hires_fix_extended_ui),
            ]
            return scripts.AlwaysVisible

    def ui(self, is_img2img):
        if not self.hr_cfg:
            with gr.Accordion(label='more hr opts'):
                self.hr_cfg = gr.Slider(minimum=1.0, maximum=30.0, step=0.5, label='Hires CFG Scale', value=7.0, elem_id="hires_fix_tweaks_txt2img_hires_cfg_scale")
        return [self.hr_cfg]

    def before_hr(self, p, *args):
        print(args[0])
        self.first_pass_cfg_scale = p.cfg_scale
        p.cfg_scale = args[0]
        pass


    # def before_hires_fix_extended_ui(self, *args, **kwargs):
    #     with gr.Accordion(label='Before'):
    #         self.before_cb = gr.Checkbox(label='Before Checkbox')

    def after_hires_fix_extended_ui(self, *args, **kwargs):
        with gr.Accordion(label='more hr opts'):
            self.hr_cfg = gr.Slider(minimum=1.0, maximum=30.0, step=0.5, label='CFG Scale', value=7.0, elem_id="hires_fix_tweaks_txt2img_cfg_scale")
            # self.after_cb = gr.Checkbox(label='After Checkbox')
