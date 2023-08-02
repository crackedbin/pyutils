
import weakref
import threading

from typing import Iterable, Any, Optional

__all__ = [
    'Observable', 'ObserverList', 'ObserverDict', 'ObserverSet'
]

class Observer:

    def __hash__(self):
        return hash(id(self))

    def observable_deleted(self, observable:"Observable", **kwargs):
        pass

class Observable:

    def __init__(self):
        self.__observer_refs:set[weakref.ReferenceType[Observer]] = set()
        self.__dict_key = None
        self.__lock = threading.Lock()

    def __hash__(self):
        return hash(id(self))

    def add_observer(self, observer:Observer, **kwargs):
        with self.__lock:
            self.__observer_refs.add(weakref.ref(observer))
            key = kwargs.get('key', None)
            if self.__dict_key and key and self.__dict_key != key:
                raise Exception(f"can not use multiple keys({key}, {self.__dict_key}) for an observable object.")
            self.__dict_key = key

    def observable_deleted(self):
        with self.__lock:
            for ref in list(self.__observer_refs):
                observer = ref()
                if not observer: continue
                observer.observable_deleted(self, key=self.__dict_key)
            self.__observer_refs.clear()

class ObserverList(Observer, list):

    def __init__(self, __iterable: Optional[Iterable]=None):
        list.__init__(self)
        if __iterable: self.extend(__iterable)

    def observable_deleted(self, observable:Observable, **kwargs):
        while observable in self:
            self.remove(observable)

    def insert(self, index:int, observable:Observable):
        list.insert(self, index, observable)
        if not isinstance(observable, Observable): return
        observable.add_observer(self)

    def append(self, observable:Observable):
        list.append(self, observable)
        if not isinstance(observable, Observable): return
        observable.add_observer(self)

    def copy(self) -> "ObserverList":
        __new = ObserverList()
        __new.extend(self)
        return __new

    def extend(self, __iterable: Iterable):
        for i in __iterable:
            self.append(i)

class ObserverDict(Observer, dict):

    def __init__(self, **kwargs):
        dict.__init__(self)
        self.update(kwargs)

    def observable_deleted(self, observable: Observable, **kwargs):
        key = kwargs.get('key', None)
        if key is None: return
        if key not in self: return
        self.pop(key)

    def __setitem__(self, __key, __value):
        dict.__setitem__(self, __key, __value)
        if not isinstance(__value, Observable): return
        __value.add_observer(self, key=__key)

    def setdefault(self, __key, __default=None):
        if __key not in self:
            self.__setitem__(__key, __default)
            return __default
        return self.__getitem__(__key)

    def update(self, __m:dict):
        for k, v in __m.items():
            self.__setitem__(k, v)

    @classmethod
    def fromkeys(cls, __iterable: Iterable, __value=None) -> "ObserverDict":
        new_dict = cls()
        for key in __iterable:
            new_dict.__setitem__(key, __value)
        return new_dict

    def copy(self) -> "ObserverDict":
        new_dict = ObserverDict()
        for key, value in self.items():
            new_dict.__setitem__(key, value)
        return new_dict
    
    def __or__(self, other: dict) -> "ObserverDict":
        assert isinstance(other, dict)
        new_dict = self.copy()
        for key, value in other.items():
            new_dict.__setitem__(key, value)
        return new_dict

    def __ror__(self, other: dict) -> "ObserverDict":
        assert isinstance(other, dict)
        new_dict = ObserverDict(other)
        for key, value in self.items():
            new_dict.__setitem__(key, value)
        return new_dict
    
    def __ior__(self, other: dict) -> "ObserverDict":
        assert isinstance(other, dict)
        for key, value in other.items():
            self.__setitem__(key, value)
        return self

class ObserverSet(Observer, set):

    def __init__(self, __iterable: Optional[Iterable]):
        if not __iterable:
            set.__init__(self)
        else:
            set.__init__(self, __iterable)
            for item in __iterable:
                if not isinstance(item, Observable):
                    continue
                item.add_observer(self)

    def add(self, __element: Any) -> None:
        set.add(self, __element)
        if not isinstance(__element, Observable): return
        __element.add_observer(self)

    def observable_deleted(self, observable:Observable, **kwargs):
        self.discard(observable)

    def copy(self) -> "ObserverSet":
        return ObserverSet(self)

    def difference(self, *s: Iterable) -> "ObserverSet":
        return ObserverSet(set.difference(self, *s))

    def difference_update(self, *s: Iterable) -> None:
        for iterable in s:
            for observable in iterable:
                self.remove(observable)

    def intersection(self, *s: Iterable) -> "ObserverSet":
        return ObserverSet(set.intersection(self, *s))

    def intersection_update(self, *s: Iterable) -> None:
        to_remove = set.difference(self, *s)
        for observable in to_remove:
            self.remove(observable)

    def symmetric_difference(self, s: Iterable) -> "ObserverSet":
        return ObserverSet(set.symmetric_difference(self, s))

    def symmetric_difference_update(self, s: Iterable) -> None:
        to_remove = set.intersection(self, s)
        to_add = set.difference(s, self)
        for observable in to_remove:
            self.remove(observable)
        for observable in to_add:
            self.add(observable)

    def union(self, *s: Iterable) -> "ObserverSet":
        return ObserverSet(set.union(self, *s))

    def update(self, *s: Iterable) -> None:
        for iterable in s:
            for observable in iterable:
                self.add(observable)

    def __ior__(self, __value: set) -> "ObserverSet":
        self.update(__value)
        return self

    def __isub__(self, __value: set) -> "ObserverSet":
        for item in __value:
            self.remove(item)
        return self
