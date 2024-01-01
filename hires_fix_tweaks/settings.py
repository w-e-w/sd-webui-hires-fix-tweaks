from hires_fix_tweaks.hr_modules import hr_prompt_mode
from modules import shared
import gradio as gr


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
                    'Show hires CFG Scale slider',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_show_hr_prompt_mode':
                shared.OptionInfo(
                    True,
                    'Show hires prompt mode',
                )
                .info('only useful if "Hires fix: show hires prompt and negative prompt" is also enabled')
                .needs_reload_ui(),
            'hires_fix_tweaks_show_hr_batch_seed':
                shared.OptionInfo(
                    True,
                    'Show hires batch count and seed',
                )
                .needs_reload_ui(),
            'hires_fix_tweaks_marker_char':
                shared.OptionInfo(
                    '@',
                    'Hires fix search/replace syntax '
                    'marker character',
                    onchange=hr_prompt_mode.setup_regex,
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

hr_prompt_mode.setup_regex()
