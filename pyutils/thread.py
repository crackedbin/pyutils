
import multiprocessing

from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, wait, Future, as_completed

__all__ = ['ThreadPool']

class ThreadPool:
    
    def __init__(self, limit:Optional[int]=None):
        self.__set_limit(limit)

    def __set_limit(self, limit:Optional[int]=None):
        limit = int(limit) if limit else 0
        max_limit = multiprocessing.cpu_count()
        if limit <= 0:
            self.limit = max_limit
        else:
            self.limit = limit
        self.__init_pool(self.limit)

    def __init_pool(self, limit:int):
        self.__executor = ThreadPoolExecutor(max_workers=limit)
        self.__futures = []

    def __clean_up(self, future:Future):
        self.__futures.remove(future)

    def join(self, timeout:Optional[float]=None):
        '''
            等待所有未完成的任务结束, 在所有任务结束后返回.
        '''
        wait(self.__futures, timeout=timeout)
    
    def complete(self, timeout:Optional[float]=None):
        '''
            返回future迭代器, 有任意future结束时迭代器会生成新对象.
        '''
        return as_completed(self.__futures, timeout=timeout)

    def submit(self, fn:Callable, *args, **kwargs):
        '''
            提交一个任务到线程池, 返回一个future对象.
        '''
        future = self.__executor.submit(fn, *args, **kwargs)
        self.__futures.append(future)
        future.add_done_callback(self.__clean_up)
        return future

    def shutdown(self, wait:bool=True, cancel_futures:bool=False):
        '''
            释放当前线程池的资源, 当这个方法调用之后, 当前线程池不能再接收
            新的任务.
        '''
        self.__executor.shutdown(wait=wait, cancel_futures=cancel_futures)
