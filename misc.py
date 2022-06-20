from __future__ import annotations

import uuid
import random
import hashlib

from typing import Union
from pathlib import Path

from .exception import NoItem

__all__ = [
    "safe_uuid", "percent", "ProbCalculator",
    "md5_file", "md5_dir"
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
