import launch

if not launch.is_installed('yaml'):
    launch.run_pip('install pyyaml', 'installing pyyaml for Hires fix tweaks')
