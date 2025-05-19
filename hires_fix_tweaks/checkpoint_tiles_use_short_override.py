from modules import shared, sd_models, patches, script_callbacks
from functools import wraps
import inspect
from pathlib import Path

modules_ui = Path('modules/ui.py')


def is_called_by_modules_ui_create_ui():
    stack = inspect.stack()
    return len(stack) > 2 and stack[2].function in ('create_ui', '<lambda>') and stack[2].frame.f_globals['__name__'] == 'modules.ui'


def wrap_checkpoint_tiles(func):
    checkpoint_tiles_signature = inspect.signature(func)

    @wraps(func)
    def checkpoint_tiles(*args, **kwargs):
        match shared.opts.hires_fix_tweaks_checkpoint_tiles_short_override:
            case 'With paths (Hires fix)' if is_called_by_modules_ui_create_ui():
                override_use_short = False
            case 'Without paths (Hires fix)' if is_called_by_modules_ui_create_ui():
                override_use_short = True
            case 'With paths (Global)':
                override_use_short = False
            case 'Without paths (Global)':
                override_use_short = True
            case _:
                return func(*args, **kwargs)

        bind_args = checkpoint_tiles_signature.bind(*args, **kwargs)
        bind_args.apply_defaults()
        bind_args.arguments['use_short'] = override_use_short
        return func(*bind_args.args, **bind_args.kwargs)

    return checkpoint_tiles


def patch_checkpoint_tiles():
    try:
        patches.patch(__name__, sd_models, "checkpoint_tiles", wrap_checkpoint_tiles(sd_models.checkpoint_tiles))

        def undo():
            try:
                patches.undo(__name__, sd_models, "checkpoint_tiles")
            except RuntimeError:
                pass

        script_callbacks.on_script_unloaded(undo)
    except RuntimeError:
        pass
