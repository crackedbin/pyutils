import os
import signal
import subprocess
import multiprocessing

from queue import Empty
from typing import Callable, Union
from threading import Thread

__all__ = [
    'kill_process', 'async_execute', 'Event', 'EventTarget'
]

def kill_process(pid):
    os.kill(pid, signal.SIGTERM)

def async_execute(args:list, env:dict=None) -> subprocess.Popen:
    '''
        subprocess.Popen wrapper.

        https://docs.python.org/3.8/whatsnew/3.8.html#optimizations
    '''
    current_env = os.environ.copy()
    if env: current_env.update(env)
    process = subprocess.Popen(
        args=args, 
        stderr=subprocess.STDOUT, stdout=subprocess.PIPE, 
        env=current_env, 
        close_fds=False
    )
    return process

class Event:

    def __init__(self, name:str, **args):
        self.name = name
        self.args = args

    def get_arg(self, k):
        return self.args.get(k)

class EventTarget:
    '''
        模仿javascript的EventTarget设计，可以用来实现IPC。
    '''

    def __init__(self):
        self.__event_queue:multiprocessing.Queue[Event] = multiprocessing.Queue()
        self.__handler_lock = multiprocessing.Lock()
        self.__event_loop_running = True
        self.__event_handlers = {}

    def __event_loop(self):
        while self.__event_loop_running:
            try:
                event = self.__event_queue.get(block=True, timeout=0.01)
            except Empty:
                continue
            if not event: continue
            with self.__handler_lock:
                if event.name not in self.__event_handlers: continue
                handler = self.__event_handlers[event.name]
            handler(self, event)

    def start_event_loop(self):
        self.__event_loop_running = True
        Thread(target=self.__event_loop, daemon=True).start()
    
    def stop_event_loop(self):
        self.__event_loop_running = False
    
    def dispatch_event(self, event:Union[Event, str], **event_args):
        if isinstance(event, Event):
            self.__event_queue.put(event)
        elif isinstance(event, str):
            self.__event_queue.put(Event(event, **event_args))

    def add_event_handler(self, event_name:str, handler:Callable):
        with self.__handler_lock:
            self.__event_handlers[event_name] = handler
    
    def remove_event_handler(self, event_name:str):
        with self.__handler_lock:
            if event_name in self.__event_handlers: return
            self.__event_handlers.pop(event_name)
