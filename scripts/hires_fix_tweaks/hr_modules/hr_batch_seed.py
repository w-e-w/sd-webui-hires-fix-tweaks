import inspect
import random

from modules import errors, patches, processing, shared
from html.parser import HTMLParser


class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_content = ''

    def handle_data(self, data):
        self.text_content += data


def init(self):
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


def create_infotext_hijack(create_infotext):
    create_infotext_signature = inspect.signature(create_infotext)

    def wrapped_function(*args, **kwargs):
        try:
            bind_args = create_infotext_signature.bind(*args, **kwargs)
            bind_args.apply_defaults()
            bind_args = bind_args.arguments

            p = bind_args['p']
            # iteration = bind_args['iteration']
            # position_in_batch = bind_args['position_in_batch']
            index = bind_args['index']
            use_main_prompt = bind_args['use_main_prompt']

            try:
                if use_main_prompt or getattr(p, 'force_write_hr_info_flag', None):
                    index = 0
                elif index is None:
                    assert False, 'index is None'
                    # index = position_in_batch + iteration * p.batch_size
                # add_hr_seed_info(p, index)
                if hasattr(p, 'hr_seeds') and p.seeds[index] != p.hr_seeds[index]:
                    p.extra_generation_params['hr_seed'] = p.hr_seeds[index]
                else:
                    p.extra_generation_params.pop('hr_seed', None)

                # todo fix subseed
                if p.subseed_strength != p.hr_subseed_strength:



                    if hasattr(p, 'hr_subseeds') and p.subseeds[index] != p.hr_subseeds[index] and p.hr_subseed_strength != 0:
                        p.extra_generation_params['hr_subseed'] = p.hr_subseeds[index]
                    else:
                        p.extra_generation_params.pop('hr_subseed', None)

                    if hasattr(p, 'hr_seed_resize_from_w') and hasattr(p, 'p.hr_seed_resize_from_h') and p.hr_seed_resize_from_w > 0 and p.hr_seed_resize_from_h > 0:
                        p.extra_generation_params['hr seed resize from'] = f"{p.hr_seed_resize_from_w}x{p.hr_seed_resize_from_h}"
                    else:
                        p.extra_generation_params.pop('hr seed resize from', None)
            except Exception as e:
                errors.report(f"not results: {e}")
                for key in ['hr_seed', 'hr_subseed', 'hr seed resize from']:
                    p.extra_generation_params.pop(key, None)
                pass

        except Exception as e:
            errors.report(f"create infotext hijack failed: {e}")
            pass

        finally:
            results = create_infotext(*args, **kwargs)
            return results

    return wrapped_function


try:
    patches.patch(key=__name__, obj=processing, field='create_infotext', replacement=create_infotext_hijack(processing.create_infotext))
except RuntimeError:
    pass


def sample_hijack(self, p, sample):
    def wrapped_function(*args, **kwargs):
        p.force_write_hr_info_flag = False
        result = sample(*args, **kwargs)
        return result
    return wrapped_function


def sample_hr_pass_hijack(self, p, sample_hr_pass):
    def wrapped_function(*args, **kwargs):
        self.first_pass_seeds = p.seeds
        self.first_pass_subseeds = p.subseeds
        self.first_pass_subseed_strength = p.subseed_strength
        self.first_pass_seed_resize_from_w = p.seed_resize_from_w
        self.first_pass_seed_resize_from_h = p.seed_resize_from_h

        samples = processing.DecodedSamples()
        save_images_before_highres_fix = shared.opts.save_images_before_highres_fix
        #
        # self.all_hr_seeds
        # self.all_hr_subseed

        p.hr_seeds = []
        p.hr_subseeds = []
        print('p.seeds', p.seeds, len(p.seeds), 'p.batch_size', p.batch_size)


        hr_seeds_batch = self.all_hr_seeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]
        hr_subseeds_batch = self.all_hr_subseeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]
        # p.seeds = p.all_seeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]
        # p.subseeds = p.all_subseeds[p.iteration * p.batch_size:(p.iteration + 1) * p.batch_size]

        p.subseed_strength = p.hr_subseed_strength
        p.seed_resize_from_w = self.hr_seed_resize_from_w
        p.seed_resize_from_h = self.hr_seed_resize_from_h

        try:
            for index in range(self.hr_batch_count):
                # p.seeds = [seed + index for seed in self.first_pass_seeds]
                p.seeds = [seed + index for seed in hr_seeds_batch]
                p.hr_seeds.extend(p.seeds)
                # p.hr_seeds = p.seeds
                #
                # p.subseeds = [subseed + index for subseed in self.first_pass_subseeds]
                p.subseeds = [subseed + index for subseed in hr_subseeds_batch]
                p.hr_subseeds.extend(p.subseeds)
                # p.hr_subseeds = p.subseeds

                result = sample_hr_pass(*args, **kwargs)
                samples.extend(result)
                # disable saving images before highres fix for all but the first batch
                shared.opts.save_images_before_highres_fix = False

        finally:
            p.seeds = self.first_pass_seeds
            p.subseeds = self.first_pass_subseeds
            p.subseed_strength = self.first_pass_subseed_strength
            p.seed_resize_from_w = self.first_pass_seed_resize_from_w
            p.seed_resize_from_h = self.first_pass_seed_resize_from_h

            # restore original shared.opts.save_images_before_highres_fix setting
            shared.opts.save_images_before_highres_fix = save_images_before_highres_fix
            return samples

    return wrapped_function


def process(self, p, *args):
    # seed init
    self.hr_batch_count = args[3]  # multi hr seed

    self.enable_hr_seed = args[4]

    if self.enable_hr_seed:

        self.hr_seed = args[5]
        self.hr_seed_enable_extras = args[6]
        if self.hr_seed_enable_extras:
            self.hr_subseed = args[7]
            self.hr_subseed_strength = args[8]
            self.hr_seed_resize_from_w = args[9]
            self.hr_seed_resize_from_h = args[10]
        else:
            self.hr_subseed = 0
            self.hr_subseed_strength = 0
            self.hr_seed_resize_from_w = 0
            self.hr_seed_resize_from_h = 0
        if p.enable_hr:
            # use to write hr info to params.txt
            p.force_write_hr_info_flag = True
    else:
        # enable_hr_seed is false use first pass seed
        self.hr_seed = 0
        self.hr_subseed = 0
        self.hr_subseed_strength = p.subseed_strength
        self.hr_seed_resize_from_w = p.seed_resize_from_w
        self.hr_seed_resize_from_h = p.seed_resize_from_h

    # print(p.all_prompts)
    # p.sample_hr_pass = self.sample_hr_pass_hijack(p, p.sample_hr_pass)
    p.sample_hr_pass = sample_hr_pass_hijack(self, p, p.sample_hr_pass)

    # p.sample = self.sample_hijack(p, p.sample)
    p.sample = sample_hijack(self, p, p.sample)
    # p.js = self.js_hijack(p.js)

    # init hr seeds
    init_hr_seeds(self, p)


def init_hr_seeds(self, p):
    if isinstance(self.hr_seed, str):
        try:
            self.hr_seed = int(self.hr_seed)
        except Exception:
            self.hr_seed = 0

    if self.hr_seed == 0:
        self.all_hr_seeds = p.all_seeds
        self.hr_seed_resize_from_w = p.seed_resize_from_w
        self.hr_seed_resize_from_h = p.seed_resize_from_h
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


def process_batch(self, p, *args, **kwargs):
    # p.extra_generation_params

    # if p.enable_hr and getattr(p, 'force_write_hr_info_flag', False):
    if p.enable_hr:
        p.hr_seeds = self.all_hr_seeds
        p.hr_subseeds = self.all_hr_subseeds
        p.hr_subseed_strength = self.hr_subseed_strength
        p.hr_seed_resize_from_w = self.hr_seed_resize_from_w
        p.hr_seed_resize_from_h = self.hr_seed_resize_from_h


def postprocess_batch_list(self, p, pp, *args, **kwargs):
    p.prompts = p.prompts * self.hr_batch_count
    p.negative_prompts = p.negative_prompts * self.hr_batch_count
    p.seeds = p.seeds * self.hr_batch_count
    p.subseeds = p.subseeds * self.hr_batch_count

