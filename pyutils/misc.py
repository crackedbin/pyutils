from __future__ import annotations

import re
import uuid
import random
import hashlib

from typing import Union
from pathlib import Path
from collections.abc import MutableMapping

from .exception import NoItem

__all__ = [
    "safe_uuid", "percent", "ProbCalculator","md5_file", "md5_dir", 
    "RandomDict", 'NumberRangeEnd', 'NumberRange', 'Singleton'
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

class NumberRangeEnd:

    LEFT    = 1
    RIGHT   = 2

    def __init__(
        self, value:Union[int, float], closed:bool, 
        position:Union[NumberRangeEnd.LEFT, NumberRangeEnd.RIGHT]
    ):
        self.__value = value
        self.__closed = closed
        self.__position = position
        assert self.__position in [NumberRangeEnd.LEFT, NumberRangeEnd.RIGHT]

    def __repr__(self):
        if self.closed:
            return f"[{self.value}]"
        else:
            return f"({self.value})"

    def __eq__(self, item:NumberRangeEnd):
        assert self.__position == item.__position
        return self.value == item.value and self.closed == item.closed
    
    def __lt__(self, item:NumberRangeEnd):
        assert self.__position == item.__position
        if self.value < item.value:
            return True
        

        if self.value == item.value :
            if not self.closed and item.closed:
                if self.__position == NumberRangeEnd.RIGHT:
                    return True
            elif self.closed and not item.closed:
                if self.__position == NumberRangeEnd.LEFT:
                    return True
        
        return False

    def __gt__(self, item:NumberRangeEnd):
        assert self.__position == item.__position
        if self.value > item.value:
            return True
        
        if self.value == item.value:
            if self.closed and not item.closed:
                if self.__position == NumberRangeEnd.RIGHT:
                    return True
            elif not self.closed and item.closed:
                if self.__position == NumberRangeEnd.LEFT:
                    return True
        
        return False
    
    def __le__(self, item:NumberRangeEnd):
        assert self.__position == item.__position
        return self == item or self < item
    
    def __ge__(self, item:NumberRangeEnd):
        assert self.__position == item.__position
        return self == item or self > item

    def __ne__(self, item:NumberRangeEnd):
        assert self.__position == item.__position
        return not (self == item)
    
    @property
    def value(self):
        return self.__value
    
    @property
    def closed(self):
        return self.__closed

    def is_left(self):
        return self.__position == NumberRangeEnd.LEFT
    
    def is_right(self):
        return self.__position == NumberRangeEnd.RIGHT
    
    @staticmethod
    def left(value:Union[int, float], closed:bool):
        return NumberRangeEnd(value, closed, NumberRangeEnd.LEFT)

    @staticmethod
    def right(value:Union[int, float], closed:bool):
        return NumberRangeEnd(value, closed, NumberRangeEnd.RIGHT)

class NumberRange:

    STATUS_OK               = 1
    STATUS_LEFT_NONE        = 2
    STATUS_RIGHT_NONE       = 3
    STATUS_BOTH_NONE        = 4
    STATUS_INVALID_VALUE    = 5
    
    def __init__(self, left:NumberRangeEnd, right:NumberRangeEnd):
        self.__left = left
        self.__right = right
        assert self.status != NumberRange.STATUS_INVALID_VALUE
    
    def __repr__(self) -> str:
        pre = '[' if self.left.closed else '('
        suf = ']' if self.right.closed else ')'
        return f"{pre}{self.left.value}, {self.right.value}{suf}"

    __str__ : __repr__

    def __contains__(self, item:Union[NumberRange, int]):
        assert self.valid
        if type(item) is int:
            left = NumberRangeEnd(item, True, NumberRangeEnd.LEFT)
            right = NumberRangeEnd(item, True, NumberRangeEnd.RIGHT)
            return NumberRange(left, right) in self
        return self.left <= item.left and self.right >= item.right

    @property
    def left(self):
        return self.__left
    
    @property
    def right(self):
        return self.__right

    @property
    def valid(self):
        return self.status == NumberRange.STATUS_OK

    @property
    def status(self):
        if self.left.value is None and self.right.value is None:
            return NumberRange.STATUS_BOTH_NONE

        if self.left.value is None:
            return NumberRange.STATUS_LEFT_NONE
        
        if self.right.value is None:
            return NumberRange.STATUS_RIGHT_NONE

        if self.left.value > self.right.value:
            return NumberRange.STATUS_INVALID_VALUE
        
        return NumberRange.STATUS_OK

    def random_choice(self, is_float:bool=False):
        '''
            随机生成区间内的一个数字
        '''
        if not is_float:
            return self.random_choice_int()
        else:
            return self.random_choice_float()

    def random_choice_int(self):
        assert self.valid
        left = self.left.value if self.left.closed else self.left.value + 1
        right = self.right.value if self.right.closed else self.right.value - 1
        return random.randint(left, right)

    def random_choice_float(self):
        assert self.valid
        return random.uniform(self.left.value, self.right.value)

    @staticmethod
    def from_string(string_value:str, is_float:bool=False):
        pattern_number = r'-?\d+\.?\d*'
        match = re.match(rf"([\(\[])\s*({pattern_number})?\s*,?\s*({pattern_number})?\s*([\)\]])", string_value)
        if not match:
            return None

        left_close = match.groups()[0] == '[' # 左闭区间
        right_close = match.groups()[3] == ']' # 右闭区间
        num_min = match.groups()[1]
        num_max = match.groups()[2]
        caster = float if is_float else int
        left = NumberRangeEnd(caster(num_min) if num_min else None, left_close, NumberRangeEnd.LEFT)
        right = NumberRangeEnd(caster(num_max) if num_max else None, right_close, NumberRangeEnd.RIGHT)
        return NumberRange(left, right)

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
