from modules import scripts


def xyz_grid_axis():
    for data in scripts.scripts_data:
        if data.script_class.__module__ in ('xyz_grid.py', 'scripts.xyz_grid') and hasattr(data, 'module'):
            xyz_grid = data.module
            xyz_grid.axis_options.extend(
                [
                    xyz_grid.AxisOptionTxt2Img('Hires CFG Scale', float, xyz_grid.apply_field('hr_cfg_scale')),
                ]
            )
            break
    else:
        raise ImportError("[Hires fix tweaks] Can't find xyz_grid: Hires CFG Scale won't work in XYZ Grid")
