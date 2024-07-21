from modules import shared
import json

quote_swap = str.maketrans('\'"', '"\'')


def dumps_quote_swap_json(input_object):
    return json.dumps(input_object).translate(quote_swap)


def loads_quote_swap_json(input_string):
    return json.loads(input_string.translate(quote_swap))

