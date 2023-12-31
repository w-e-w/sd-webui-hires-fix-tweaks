from modules import scripts


def xyz_grid_axis():
    for data in scripts.scripts_data:
        if data.script_class.__module__ == 'xyz_grid.py' and hasattr(data, 'module'):
            xyz_grid = data.module
            xyz_grid.axis_options.extend(
                [
                    xyz_grid.AxisOptionTxt2Img('Hires CFG Scale', float, xyz_grid.apply_field('hr_cfg_scale')),
                ]
            )
            break
