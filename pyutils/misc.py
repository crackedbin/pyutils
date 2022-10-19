from __future__ import annotations

import os
import re
import uuid
import random
import hashlib
import importlib
import importlib.util

import pyutils

from types import ModuleType
from typing import Union
from pathlib import Path
from collections.abc import MutableMapping

__all__ = [
    "safe_uuid", "percent", "ProbCalculator","md5_file", "md5_dir", 
    "RandomDict", 'NumberRangeEnd', 'NumberRange', 'Singleton',
    'import_from'
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
            calc = ProbCalculator()\n
            calc.add(50, func1)\n
            calc.add(30, func2)\n
            calc.add(20, func3)\n
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
            raise pyutils.NoItem("no item in ProbCalculator")
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

class RandomDict(MutableMapping):
    '''
        对比普通的dict对象, 增加了以下方法:
            random_key: 随机返回一个key
            random_value: 随机返回一个value
            random_item: 随机返回一个item
    '''
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
    '''
        类似range对象, 增加以下功能:
            * 支持从字符串构建
            * 支持开闭区间
            * 支持随机从区间取值: random_choice
    '''

    STATUS_OK               = 1
    STATUS_LEFT_NONE        = 2
    STATUS_RIGHT_NONE       = 3
    STATUS_BOTH_NONE        = 4
    STATUS_INVALID_VALUE    = 5
    
    def __init__(self, left:NumberRangeEnd, right:NumberRangeEnd, base:int=None):
        self.__left = left
        self.__right = right
        self.__base = base
        assert isinstance(self.__base, int) or base is None
        assert self.status != NumberRange.STATUS_INVALID_VALUE

    def __repr__(self) -> str:
        pre = '[' if self.left.closed else '('
        suf = ']' if self.right.closed else ')'
        if self.__base is None:
            return f"{pre}{self.left.value}, {self.right.value}{suf}"
        else:
            return f"{pre}{self.left.value}, {self.right.value}{suf}{{{self.__base}}}"

    __str__ : __repr__

    def __contains__(self, item:Union[NumberRange, int]):
        assert self.valid
        if isinstance(item, int):
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

    @property
    def base(self):
        return self.__base

    def random_choice(self, is_float:bool=False, step:int=1, mode:float=None):
        '''
            随机生成区间内的一个数字
        '''
        if not is_float:
            if self.__base is None:
                return self.random_choice_int(step=step)
            else:
                return self.random_choice_int_with_base()
        else:
            return self.random_choice_float(mode=mode)

    def random_choice_int(self, step:int=1):
        assert self.valid
        start = self.left.value if self.left.closed else self.left.value + 1
        end = self.right.value + 1 if self.right.closed else self.right.value
        return random.randrange(start, end, step)

    def random_choice_int_with_base(self):
        assert self.valid
        assert isinstance(self.__base, int)
        assert self.__base != 0
        left_value = self.left.value if self.left.closed else self.left.value + 1
        right_value = self.right.value if self.right.closed else self.right.value - 1
        assert right_value - left_value >= self.__base
        m = left_value % self.__base
        start = left_value if m == 0 else left_value + abs(self.__base - m)
        end = right_value + 1
        return random.randrange(start, end, abs(self.__base))

    def random_choice_float(self, mode:float=None):
        assert self.valid
        return random.triangular(self.left.value, self.right.value, mode)

    @staticmethod
    def from_string(string_value:str, is_float:bool=False, base:int=None):
        '''
            string中的数字只支持十进制

            string_value示例:
                [0, 10], [0, 10.5), (0.5, 10), (0, 10]
        '''
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
        return NumberRange(left, right, base=base)

class Singleton(type):
    '''
        实现单例模式的基类, 如果有实现单例模式的需求, 直接继承该类即可.
    '''
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

def md5_update_from_file(filename:os.PathLike, hash:hashlib._Hash) -> hashlib._Hash:
    assert Path(filename).is_file()
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash

def md5_file(filename:os.PathLike) -> str:
    '''
        计算一个文件的md5
    '''
    return str(md5_update_from_file(filename, hashlib.md5()).hexdigest())

def md5_update_from_dir(directory:os.PathLike, hash: hashlib._Hash) -> hashlib._Hash:
    assert Path(directory).is_dir()
    for path in sorted(Path(directory).iterdir(), key=lambda p: str(p).lower()):
        hash.update(path.name.encode())
        if path.is_file():
            hash = md5_update_from_file(path, hash)
        elif path.is_dir():
            hash = md5_update_from_dir(path, hash)
    return hash

def md5_dir(directory:os.PathLike) -> str:
    '''
        计算一个目录的md5
    '''
    return str(md5_update_from_dir(directory, hashlib.md5()).hexdigest())

def import_from(module_dir:os.PathLike) -> dict[str, object]:
    '''
        从指定目录导入所有.py文件`__all__`列表中指定的对象, 以字典形式返回, 
        如果出现相同的导出符号会抛出异常.
    '''
    py_files = pyutils.find_files(
        module_dir, suffix='.py', filter_func=lambda _, f: f != '__init__.py')
    _all = {}
    for file in py_files:
        module_name = file.parts[-1].split('.')[0]
        module_spec = importlib.util.spec_from_file_location(module_name, file)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        for k in module.__all__:
            if k in _all:
                raise ImportError(f"Conflict name {k}")
            _all[k] = module.__dict__[k]
    return _all
