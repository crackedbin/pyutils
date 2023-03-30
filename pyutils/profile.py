
import time

from functools import wraps

__all__ = [
    "measure"
]

def measure(func):
    @wraps(func)
    def _time_it(*args, **kwargs):
        start = time.time() * 1000
        try:
            return func(*args, **kwargs)
        finally:
            end_ = time.time() * 1000 - start
            print(f"{func.__name__} execution time: {end_ if end_ > 0 else 0} ms")
    return _time_it
