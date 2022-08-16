from __future__ import annotations

import uuid
import random
import hashlib

from typing import Union
from pathlib import Path
from collections import MutableMapping

from .exception import NoItem

__all__ = [
    "safe_uuid", "percent", "ProbCalculator",
    "md5_file", "md5_dir", "RandomDict"
]

def safe_uuid():
    return str(uuid.uuid1(random.randint(0, 0xffffffffffff)))

def percent(mole):
    '''
        0 <= mole < 100
        根据mole大小,随机返回True或False,mole越大True的几率越大
    '''
    return random.randrange(0, 100) <= mole

class ProbCalculator:

    '''
        用于根据给定的概率来随机选择item.

        例:
            calc = ProbCalculator()

            calc.add(50, func1)

            calc.add(30, func2)

            calc.add(20, func3)

            func = calc.get()
        
        func的概率分布:
            50%: func1
            30%: func2
            20%: func3
    '''

    def __init__(self, precision:int=100):
        self.__precision = precision
        self.__items = []
        self.__items_with_range = []
        self.__total_rate = 0
        self.__stable = False
    
    def add(self, rate:int, item):
        assert rate > 0
        self.__items.append((rate, item))
        self.__total_rate += rate
        self.__stable = False
    
    def remove(self, item):
        for pair in self.__items[:]:
            if pair[1] == item:
                self.__items.remove(pair)
                self.__total_rate -= pair[0]
                self.__stable = False
                return

    def __do_calculate(self):
        if self.__stable: return
        last_rate = 0
        self.__items_with_range.clear()
        for rate, item in self.__items:
            rate = int((rate / self.__total_rate)*self.__precision) + last_rate
            rate_range = range(last_rate, rate)
            self.__items_with_range.append((rate_range, item))
            last_rate = rate
        self.__stable = True
        
    def get(self):
        if not self.__items:
            raise NoItem("no item in ProbCalculator")
        self.__do_calculate()
        random_num = random.randrange(0, self.__precision)
        item = None
        for item_range, item in self.__items_with_range:
            if random_num in item_range: return item
        if not item: item = random.choice(self.__items)
        assert item
        return item 
    
    def pop(self):
        item = self.get()
        self.remove(item)
        return item
    
    def empty(self):
        return not bool(self.__items)

def md5_update_from_file(filename: Union[str, Path], hash:hashlib._Hash) -> hashlib._Hash:
    assert Path(filename).is_file()
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash

def md5_file(filename: Union[str, Path]) -> str:
    return str(md5_update_from_file(filename, hashlib.md5()).hexdigest())

def md5_update_from_dir(directory: Union[str, Path], hash: hashlib._Hash) -> hashlib._Hash:
    assert Path(directory).is_dir()
    for path in sorted(Path(directory).iterdir(), key=lambda p: str(p).lower()):
        hash.update(path.name.encode())
        if path.is_file():
            hash = md5_update_from_file(path, hash)
        elif path.is_dir():
            hash = md5_update_from_dir(path, hash)
    return hash

def md5_dir(directory: Union[str, Path]) -> str:
    return str(md5_update_from_dir(directory, hashlib.md5()).hexdigest())

class RandomDict(MutableMapping):
    def __init__(self, *args, **kwargs):
        """ Create RandomDict object with contents specified by arguments.
        Any argument
        :param *args:       dictionaries whose contents get added to this dict
        :param **kwargs:    key, value pairs will be added to this dict
        """
        # mapping of keys to array positions
        self.__keys = {}
        self.__values = []
        self.__last_index = -1

        self.update(*args, **kwargs)

    def __setitem__(self, key, val):
        if key in self.__keys:
            i = self.__keys[key]
        else:
            self.__last_index += 1
            i = self.__last_index

        self.__values.append((key, val))
        self.__keys[key] = i
    
    def __delitem__(self, key):
        if not key in self.__keys:
            raise KeyError

        # index of item to delete is i
        i = self.__keys[key]
        # last item in values array is
        move_key, move_val = self.__values.pop()

        if i != self.__last_index:
            # we move the last item into its location
            self.__values[i] = (move_key, move_val)
            self.__keys[move_key] = i
        # else it was the last item and we just throw
        # it away

        # shorten array of values
        self.__last_index -= 1
        # remove deleted key
        del self.__keys[key]
    
    def __getitem__(self, key):
        if not key in self.__keys:
            raise KeyError

        i = self.__keys[key]
        return self.__values[i][1]

    def __iter__(self):
        return iter(self.__keys)

    def __len__(self):
        return self.__last_index + 1

    def __str__(self):
        return str(self.__values)

    def random_key(self):
        """ Return a random key from this dictionary in O(1) time """
        if len(self) == 0:
            raise KeyError("RandomDict is empty")
        
        i = random.randint(0, self.__last_index)
        return self.__values[i][0]

    def random_value(self):
        """ Return a random value from this dictionary in O(1) time """
        return self[self.random_key()]

    def random_item(self):
        """ Return a random key-value pair from this dictionary in O(1) time """
        k = self.random_key()
        return k, self[k]