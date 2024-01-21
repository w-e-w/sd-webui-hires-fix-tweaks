from modules import shared


class HiresOutputDir:
    def __init__(self):
        self.enable = None
        self.original_outpath_samples = None
        self.job_original_outpath_samples = None

    def setup(self, p, *args):
        self.original_outpath_samples = None
        self.job_original_outpath_samples = None

        self.enable = (
                p.enable_hr
                and len(shared.opts.hires_fix_tweaks_outdir_hires_fix) > 0
                and not len(shared.opts.outdir_samples) > 0
        )
        if not self.enable:
            return

        # save original outdir
        self.original_outpath_samples = p.outpath_samples

    def before_process_batch(self, p, *args, **kwargs):
        if not self.enable:
            return

        if self.job_original_outpath_samples is not None:
            # ensure job outdir for current batch
            p.outpath_samples = self.job_original_outpath_samples

    def postprocess_batch(self, p, *args, **kwargs):
        if not self.enable:
            return

        # save job outdir for next batch
        self.job_original_outpath_samples = p.outpath_samples

        # set outdir to hires_fix_tweaks_outdir_hires_fix
        p.outpath_samples = shared.opts.hires_fix_tweaks_outdir_hires_fix

    def postprocess(self, p, processed, *args):
        if not self.enable:
            return

        # restore original outdir (don't think this is necessary but to be safe)
        p.outpath_samples = self.original_outpath_samples
