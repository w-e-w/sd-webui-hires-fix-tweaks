from hires_fix_tweaks.hr_modules import hr_prompt_mode
from modules import shared
import gradio as gr


shared.options_templates.update(
    shared.options_section(
        ('hires_fix_tweaks', 'Hires. fix tweaks'),
        {
            'hires_fix_tweaks_save_template':
                shared.OptionInfo(
                    True,
                    'Save the hires prompt mode template to infotext',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_restore_template':
                shared.OptionInfo(
                    True,
                    'Restore hires prompt mode template from infotext',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_append_separator':
                shared.OptionInfo(
                    '{newline}',
                    'Append mode insert separator',
                    infotext='HR append',
                )
                .info('default: "{newline}"'),
            'hires_fix_tweaks_prepend_separator':
                shared.OptionInfo(
                    '{newline}',
                    'Prepend mode insert separator',
                    infotext='HR prepend',
                )
                .info('default: "{newline}"'),
            'hires_fix_tweaks_show_hr_cfg':
                shared.OptionInfo(
                    True,
                    'Show hires CFG Scale slider',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_show_hr_batch_seed':
                shared.OptionInfo(
                    True,
                    'Show hires batch count and seed',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_show_hr_remove_fp_extra_networks':
                shared.OptionInfo(
                    True,
                    'Show "Remove First Pass Extra Networks" checkbox',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_show_hr_prompt_mode':
                shared.OptionInfo(
                    True,
                    'Show hires prompt mode',
                )
                .info('only usable if "Hires fix: show hires prompt and negative prompt" is also enabled')
                .needs_reload_ui(),
            'hires_fix_tweaks_show_hr_styles':
                shared.OptionInfo(
                    True,
                    'Show hires styles',
                )
                .info('Available for Webui >= 1.9.0')
                .needs_reload_ui(),
            'hires_fix_tweaks_marker_char':
                shared.OptionInfo(
                    '@',
                    'Hires fix search/replace syntax '
                    'marker character',
                    onchange=hr_prompt_mode.setup_regex,
                    infotext='HR marker',
                )
                .info('default: "@", can be changed other characters if the default is causing issues, must be a single uncommon character'),
            'hires_fix_tweaks_hires_prompt_mode_ui_type':
                shared.OptionInfo(
                    'Radio', 'Hires Prompt mode menu style', gr.Radio,
                    {'choices': ['Radio', 'Dropdown']},
                )
                .needs_reload_ui(),
        }
    )
)

shared.options_templates.update(
    shared.options_section(
        ('saving-paths', "Paths for saving"),
        {
            "hires_fix_tweaks_outdir_hires_fix":
                shared.OptionInfo(
                    '', 'Output directory for hires. fix images',
                    component_args=shared.hide_dirs
                )
                .info('leave blank to use same directory as txt2img, and will be ignored if "Output directory for images" is not empty. (hires-fix-tweaks extension)'),
        }
    )
)

hr_prompt_mode.setup_regex()
