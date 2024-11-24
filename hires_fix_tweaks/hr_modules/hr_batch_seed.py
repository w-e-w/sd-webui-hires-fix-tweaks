from modules import errors, patches, processing, shared, script_callbacks, images, sd_models
from hires_fix_tweaks.utils import dumps_quote_swap_json, loads_quote_swap_json
from PIL import ImageChops
import inspect
import random


def same_img_pil(img1, img2):
    return img1.size == img2.size and ImageChops.difference(img1, img2).getbbox() is None


def create_infotext_hijack(create_infotext, script_class):
    create_infotext_signature = inspect.signature(create_infotext)

    def wrapped_function(*args, **kwargs):
        try:
            bind_args = create_infotext_signature.bind(*args, **kwargs)
            bind_args.apply_defaults()
            bind_args = bind_args.arguments
            p = bind_args['p']
            index = bind_args['index']
            use_main_prompt = bind_args['use_main_prompt']

            try:
                hires_batch_seed = next((obj for obj in p.scripts.alwayson_scripts if isinstance(obj, script_class))).hires_batch_seed

                if use_main_prompt or hires_batch_seed.force_write_hr_info_flag:
                    # params.txt and grid
                    seeds = p.all_seeds
                    subseeds = p.all_subseeds
                    hr_seeds = hires_batch_seed.all_hr_seeds
                    hr_subseeds = hires_batch_seed.all_hr_subseeds
                    index = 0
                elif index is None:
                    # intermediate images
                    assert False
                else:
                    # hr batch results
                    seeds = p.seeds
                    subseeds = p.subseeds
                    hr_seeds = hires_batch_seed.hr_seeds
                    hr_subseeds = hires_batch_seed.hr_subseeds

                hires_seed_diff = [
                    seeds[index] != hr_seeds[index],
                    p.subseed_strength != hires_batch_seed.hr_subseed_strength,
                    hires_batch_seed.hr_subseed_strength > 0 and subseeds[index] != hr_subseeds[index],
                    p.seed_resize_from_w != hires_batch_seed.hr_seed_resize_from_w,
                    p.seed_resize_from_h != hires_batch_seed.hr_seed_resize_from_h,
                ]
                if any(hires_seed_diff):
                    hr_seed_info = {}
                    if hires_seed_diff[0]:
                        hr_seed_info['Seed'] = hr_seeds[index]

                    if hires_batch_seed.hr_subseed_strength > 0:
                        if p.subseed_strength <= 0 or subseeds[index] != hr_subseeds[index]:
                            hr_seed_info['Subseed'] = hr_subseeds[index]
                        hr_seed_info['Strength'] = hires_batch_seed.hr_subseed_strength

                    if hires_batch_seed.hr_seed_resize_from_w > 0 and hires_batch_seed.hr_seed_resize_from_h > 0:
                        hr_seed_info['Resize'] = [hires_batch_seed.hr_seed_resize_from_w, hires_batch_seed.hr_seed_resize_from_h]

                    # store hr_seed_info as json string with double and single quotes swapped
                    p.extra_generation_params['Hires seed'] = dumps_quote_swap_json(hr_seed_info)
                else:
                    assert False

            except Exception:
                # remove hr_seed_info
                p.extra_generation_params.pop('Hires seed', None)

        except Exception:
            errors.report(f"create infotext hijack failed {__name__}")

        finally:
            results = create_infotext(*args, **kwargs)
            return results
        return create_infotext(*args, **kwargs)

    return wrapped_function


def hijack_create_infotext(script_class):
    try:
        patches.patch(__name__, processing, 'create_infotext', create_infotext_hijack(processing.create_infotext, script_class))

        def undo_hijack():
            patches.undo(__name__, processing, 'create_infotext')

        script_callbacks.on_script_unloaded(undo_hijack)
    except RuntimeError:
        pass


def parse_infotext(infotext, params):
    try:
        params['Hires seed'] = loads_quote_swap_json(params['Hires seed'])
    except Exception:
        pass


class HiresBatchSeed:
    def __init__(self,  script):
        self.script = script

        self.enable = None

        self.first_pass_seeds = None
        self.first_pass_subseeds = None
        self.first_pass_seed_resize_from_w = None
        self.first_pass_seed_resize_from_h = None

        self.hr_batch_count = None
        self.enable_hr_seed = None
        self.hr_seed = None
        self.hr_seed_enable_extras = None
        self.hr_subseed = None
        self.hr_subseed_strength = None
        self.hr_seed_resize_from_w = None
        self.hr_seed_resize_from_h = None

        self.all_hr_seeds = None
        self.all_hr_subseeds = None
        self.hr_seeds = None
        self.hr_subseeds = None
        self.force_write_hr_info_flag = None
        self.resize_image_cache = None

        self.update_progress_bar = None
        self.patch_get_hr_prompt = None

        self.original_get_hr_prompt = None
        self.original_get_hr_negative_prompt = None

    def setup(self, p, *args):
        # cleanup
        self.force_write_hr_info_flag = None
        self.hr_seeds = None
        self.hr_subseed_strength = None
        self.hr_subseeds = None
        self.hr_seed_resize_from_w = None
        self.hr_seed_resize_from_h = None
        self.original_get_hr_prompt = None
        self.original_get_hr_negative_prompt = None

    def process(self, p, *args):
        self.hr_batch_count = args[4]  # multi hr seed
        self.enable_hr_seed = args[5]

        self.update_progress_bar = self.patch_get_hr_prompt = self.hr_batch_count > 1

        self.enable = p.enable_hr and (self.enable_hr_seed or self.update_progress_bar)
        # if hr_disabled or hr batch count <= 1 and hr seed is disabled then module is disabled
        if not self.enable:
            # module is disabled
            return

        if self.enable_hr_seed:
            self.hr_seed = args[6]
            self.hr_seed_enable_extras = args[7]
            if self.hr_seed_enable_extras:
                self.hr_subseed = args[8]
                self.hr_subseed_strength = args[9]
                self.hr_seed_resize_from_w = args[10]
                self.hr_seed_resize_from_h = args[11]
                if self.hr_seed_resize_from_w <= 0 or self.hr_seed_resize_from_h <= 0:
                    self.hr_seed_resize_from_w = -1
                    self.hr_seed_resize_from_h = -1
            else:
                self.hr_subseed = 0
                self.hr_subseed_strength = 0
                self.hr_seed_resize_from_w = -1
                self.hr_seed_resize_from_h = -1

            self.force_write_hr_info_flag = True
        else:
            # enable_hr_seed is false use first pass seed
            self.hr_seed = 0
            self.hr_subseed = 0
            self.hr_subseed_strength = p.subseed_strength
            self.hr_seed_resize_from_w = p.seed_resize_from_w
            self.hr_seed_resize_from_h = p.seed_resize_from_h

        self.init_hr_seeds(p)

        p.sample_hr_pass = self.sample_hr_pass_hijack(p, p.sample_hr_pass)
        p.sample = self.sample_hijack(p, p.sample)

    def before_process_batch(self, p, *args, **kwargs):
        if not self.enable:
            return

        if self.patch_get_hr_prompt:
            # fix for 1.9
            if self.original_get_hr_prompt:
                p.extra_generation_params['Hires prompt'] = self.original_get_hr_prompt
                self.original_get_hr_prompt = None
            if self.original_get_hr_negative_prompt:
                p.extra_generation_params['Hires negative prompt'] = self.original_get_hr_negative_prompt
                self.original_get_hr_negative_prompt = None

        if not self.update_progress_bar:
            return
        self.update_progress_bar = False
        # known issue: progress may break when using scripts like xyz grid
        additional_hr_batch_count = (self.hr_batch_count - 1) * p.n_iter
        shared.state.job_count += additional_hr_batch_count
        if shared.opts.multiple_tqdm and not shared.cmd_opts.disable_console_progressbars and shared.total_tqdm._tqdm and shared.total_tqdm._tqdm.total:
            shared.total_tqdm.updateTotal(shared.total_tqdm._tqdm.total + additional_hr_batch_count * (p.hr_second_pass_steps or p.steps))

    def process_batch(self, p, *args, **kwargs):
        if not self.enable:
            return
        self.hr_seeds = self.all_hr_seeds
        self.hr_subseeds = self.all_hr_subseeds

    def postprocess_batch_list(self, p, pp, *args, **kwargs):
        if not self.enable:
            return
        p.prompts = p.prompts * self.hr_batch_count
        p.negative_prompts = p.negative_prompts * self.hr_batch_count
        p.seeds = p.seeds * self.hr_batch_count
        p.subseeds = p.subseeds * self.hr_batch_count

    def postprocess(self, p, processed, *args):
        if not self.enable:
            return
        processed.all_seeds = [j for i in range(0, len(processed.all_seeds), processed.batch_size) for j in processed.all_seeds[i:i + processed.batch_size] * self.hr_batch_count]
        processed.all_subseeds = [j for i in range(0, len(processed.all_subseeds), processed.batch_size) for j in processed.all_subseeds[i:i + processed.batch_size] * self.hr_batch_count]

    def init_hr_seeds(self, p):
        if isinstance(self.hr_seed, str):
            try:
                self.hr_seed = int(self.hr_seed)
            except Exception:
                self.hr_seed = 0

        if self.hr_seed == 0:
            self.all_hr_seeds = p.all_seeds
        else:
            seed = int(random.randrange(4294967294)) if self.hr_seed == -1 else self.hr_seed
            self.all_hr_seeds = [int(seed) + (x if self.hr_subseed_strength == 0 else 0) for x in range(len(p.all_seeds))]

        if isinstance(self.hr_subseed, str):
            try:
                self.hr_subseed = int(self.hr_subseed)
            except Exception:
                self.hr_subseed = 0

        if self.hr_subseed == 0:
            self.all_hr_subseeds = p.all_subseeds
        else:
            subseed = int(random.randrange(4294967294)) if self.hr_seed == -1 else self.hr_subseed
            self.all_hr_subseeds = [int(subseed) + x for x in range(len(p.all_subseeds))]

    def sample_hijack(self, p, sample):
        def wrapped_function(*args, **kwargs):
            if not self.enable:
                return sample(*args, **kwargs)

            self.force_write_hr_info_flag = False
            result = sample(*args, **kwargs)
            return result

        return wrapped_function

    def sample_hr_pass_hijack(self, p, sample_hr_pass):
        def wrapped_function(*args, **kwargs):
            if not self.enable:
                return sample_hr_pass(*args, **kwargs)

            # save original shared.opts.save_images_before_highres_fix setting to be restored later
            save_images_before_highres_fix = shared.opts.save_images_before_highres_fix

            original_resize_image = images.resize_image

            self.first_pass_seeds = p.seeds
            self.first_pass_subseeds = p.subseeds
            self.first_pass_subseed_strength = p.subseed_strength
            self.first_pass_seed_resize_from_w = p.seed_resize_from_w
            self.first_pass_seed_resize_from_h = p.seed_resize_from_h

            samples = processing.DecodedSamples()
            try:
                # hijack resize_image and init resize_image_cache
                images.resize_image = self.resize_image_hijack(images.resize_image)
                self.resize_image_cache = []

                p.subseed_strength = self.hr_subseed_strength
                p.seed_resize_from_w = self.hr_seed_resize_from_w
                p.seed_resize_from_h = self.hr_seed_resize_from_h

                self.hr_seeds = []
                self.hr_subseeds = []
                hr_seeds_batch = self.all_hr_seeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]
                hr_subseeds_batch = self.all_hr_subseeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]

                for index in range(self.hr_batch_count):
                    p.seeds = [seed + index for seed in hr_seeds_batch] if self.hr_subseed_strength == 0 else hr_seeds_batch
                    self.hr_seeds.extend(p.seeds)
                    p.subseeds = [subseed + index for subseed in hr_subseeds_batch]
                    self.hr_subseeds.extend(p.subseeds)

                    result = sample_hr_pass(*args, **kwargs)
                    samples.extend(result)

                    # disable saving images before highres fix for all but the first batch
                    shared.opts.save_images_before_highres_fix = False

                    # check and restore hr_checkpoint incase model was switch by something like refine
                    if index < self.hr_batch_count - 1 and sd_models.model_data.sd_model.sd_model_checkpoint != (p.hr_checkpoint_info or sd_models.select_checkpoint()).filename:
                        sd_models.reload_model_weights(info=p.hr_checkpoint_info)
                        p.setup_conds()
                        p.calculate_hr_conds()

                if self.patch_get_hr_prompt:
                    # fix for 1.9
                    if callable(get_hr_prompt := p.extra_generation_params.get('Hires prompt')):
                        self.original_get_hr_prompt = get_hr_prompt
                        p.extra_generation_params['Hires prompt'] = self.get_hr_prompt_hijack(get_hr_prompt)
                    if callable(get_hr_negative_prompt := p.extra_generation_params.get('Hires negative prompt')):
                        self.original_get_hr_negative_prompt = get_hr_negative_prompt
                        p.extra_generation_params['Hires negative prompt'] = self.get_hr_prompt_hijack(get_hr_negative_prompt)

            finally:
                p.seeds = self.first_pass_seeds
                p.subseeds = self.first_pass_subseeds
                p.subseed_strength = self.first_pass_subseed_strength
                p.seed_resize_from_w = self.first_pass_seed_resize_from_w
                p.seed_resize_from_h = self.first_pass_seed_resize_from_h

                # restore original shared.opts.save_images_before_highres_fix setting
                shared.opts.save_images_before_highres_fix = save_images_before_highres_fix

                # restore original images.resize_image and clear resize_image_cache
                images.resize_image = original_resize_image
                self.resize_image_cache = None

                return samples

        return wrapped_function

    def resize_image_hijack(self, resize_image):
        resize_image_signature = inspect.signature(resize_image)

        def wrapped_function(*args, **kwargs):
            if not self.enable:
                return resize_image(*args, **kwargs)
            bind_args = resize_image_signature.bind(*args, **kwargs).arguments
            im = bind_args.pop('im')

            bind_args_items = bind_args.items()
            for cache_key, cache_im, cached_result in self.resize_image_cache:
                if bind_args_items == cache_key and same_img_pil(im, cache_im):
                    return cached_result

            result = resize_image(*args, **kwargs)
            self.resize_image_cache.append((bind_args_items, im, result))
            return result
        return wrapped_function

    def get_hr_prompt_hijack(self, get_hr_prompt):
        # fix for 1.9
        get_hr_prompt_signature = inspect.signature(get_hr_prompt)

        def wrapped_function(*args, **kwargs):
            if not self.enable:
                return get_hr_prompt(*args, **kwargs)
            try:
                bind_args = get_hr_prompt_signature.bind(*args, **kwargs).arguments
                bind_args['index'] = bind_args['index'] // self.hr_batch_count
                return get_hr_prompt(**bind_args)
            except Exception:
                return get_hr_prompt(*args, **kwargs)

        return wrapped_function
