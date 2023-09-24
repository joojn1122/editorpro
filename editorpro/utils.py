from typing import Type, Tuple, Iterable
from functools import wraps
from moviepy.editor import AudioClip

def rgb_to_bgr(rgb):
    return (rgb[2], rgb[1], rgb[0])

def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def concat(*args: Iterable):
    for arg in args:
        for item in arg:
            yield item

def create_silence(duration):
    return AudioClip(lambda t: (0, 0), duration=duration)

def checktypes(*expected_types: Tuple[Type] | Type | None, allow_none: bool = False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for arg, expected_type in zip(args, expected_types):
                
                if (
                    expected_type is not None and
                    not (allow_none and arg is None) and 
                    not isinstance(arg, expected_type)
                ):
                    raise TypeError(f"Expected {expected_type}, but got {type(arg).__name__} for argument {arg}.")
            
            return func(*args, **kwargs)
    
        return wrapper
    
    return decorator