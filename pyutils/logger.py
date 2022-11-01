
from __future__ import annotations

import os
import re
import sys
import logging

import pyutils

from logging import LogRecord, handlers
from typing import Callable, Iterable, ByteString, TextIO, Union
from pathlib import Path

__all__ = [
    'SimpleLogger'
]

class LoggerLevel:

    DEBUG       = logging.DEBUG
    INFO        = logging.INFO
    WARNING     = logging.WARNING
    ERROR       = logging.ERROR
    CRITICAL    = logging.CRITICAL

    @staticmethod
    def get_level(level:Union[str, int]):
        if isinstance(level, str):
            level = level.upper()
        return logging.getLevelName(level)

class SimpleStreamFormatter(logging.Formatter):

    STREAM_FORMAT = r'[%(name)s]%(channel)s %(levelname)s: %(message)s'

    COLOR = {
        'INFO'      : '\x1b[94m',
        'WARNING'   : '\x1b[93m',
        'ERROR'     : '\x1b[91m',
        'CRITICAL'  : '\x1b[41m',
        'DEBUG'     : '\x1b[95m',
        'ENDC'      : '\x1b[0m'
    }

    FORMATTERS = {
        LoggerLevel.DEBUG   : logging.Formatter(
            f"{COLOR['DEBUG']}{STREAM_FORMAT}{COLOR['ENDC']}"),
        LoggerLevel.INFO    : logging.Formatter(
            f"{COLOR['INFO']}{STREAM_FORMAT}{COLOR['ENDC']}"),
        LoggerLevel.WARNING : logging.Formatter(
            f"{COLOR['WARNING']}{STREAM_FORMAT}{COLOR['ENDC']}"),
        LoggerLevel.ERROR   : logging.Formatter(
            f"{COLOR['ERROR']}{STREAM_FORMAT}{COLOR['ENDC']}"),
        LoggerLevel.CRITICAL: logging.Formatter(
            f"{COLOR['CRITICAL']}{STREAM_FORMAT}{COLOR['ENDC']}"),
        'default': logging.Formatter(STREAM_FORMAT)
    }

    def format(self, record:LogRecord) -> str:  
        if record.levelno in SimpleStreamFormatter.FORMATTERS:
            formatter = SimpleStreamFormatter.FORMATTERS[record.levelno]
        else:
            formatter = SimpleStreamFormatter.FORMATTERS['default']
        
        if hasattr(record, 'channel'):
            channel = getattr(record, 'channel')
            if channel == 'default':
                setattr(record, 'channel', '')
            else:
                setattr(record, 'channel', f"{channel}")

        return formatter.format(record)

class LoggerChannel:
    '''
        一个LoggerBase及其子类可以拥有多个LoggerChannel
    '''

    def __init__(self, host:SimpleLogger, channel_name:str):
        self.__host = host
        self.__name = channel_name
        self.__enable = True
        self.__callbacks = {}
        if isinstance(self.__host.channel_name_length, int):
            if len(self.__name) > self.__host.channel_name_length:
                self.__name_to_show = f"({self.__name[:10]})"
            else:
                self.__name_to_show = f"({self.__name})".ljust(self.__host.channel_name_length + 2, ' ')
        else:
            self.__name_to_show = f"({self.__name})"

    @property
    def name(self):
        return self.__name

    def enable(self):
        self.__enable = True

    def disable(self):
        self.__enable = False

    def __do_log(self, msg, level):
        if not self.__enable: return
        self.__host.logger.log(level, msg, extra={'channel': self.__name_to_show})
        if level not in self.__callbacks: return
        self.__callbacks[level](msg)

    def log(self, msg, level=LoggerLevel.INFO):
        self.__do_log(msg, level)

    def debug(self, msg):
        self.log(msg, SimpleLogger.DEBUG)

    def info(self, msg):
        self.log(msg, SimpleLogger.INFO)

    def warning(self, msg):
        self.log(msg, SimpleLogger.WARNING)

    def error(self, msg):
        self.log(msg, SimpleLogger.ERROR)

    def critical(self, msg):
        self.log(msg, SimpleLogger.CRITICAL)
    
    def log_col(self, msgs:Iterable, width:int, spliter:str='|', level=LoggerLevel.INFO):
        msgs = [ f"{str(m).ljust(width)}" for m in msgs]
        msg = spliter.join(msgs)
        self.log(msg, level)
    
    def debug_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, SimpleLogger.DEBUG)
    
    def info_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, SimpleLogger.INFO)
    
    def warning_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, SimpleLogger.WARNING)
    
    def error_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, SimpleLogger.ERROR)
    
    def critical_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, SimpleLogger.CRITICAL)
    
    def set_callback(self, level:Union[str, int], callback:Callable[[ByteString], None]):
        if isinstance(level, str): level = LoggerLevel.get_level(level)
        self.__callbacks[level] = callback

    def clear_callback(self, level:Union[str, int]):
        if isinstance(level, str): level = LoggerLevel.get_level(level)
        if level not in self.__callbacks: return
        self.__callbacks.pop(level)

class SimpleLogger(object):
    '''
        SimpleLogger推荐当作基类使用，也可以单独使用。
        子类要使用该接口的功能,需要在`__init__`中调用`SimpleLogger.__init__(self)`。
        没有提供`logger_name`参数时会自动使用子类的类名作为`logger_name`。
        
        如果子类有多个实例同时运行且需要对这些实例进行区分,可以调用
        `SimpleLogger.__init__(self, extend_name=<unique name>)`
    '''

    DEBUG       = LoggerLevel.DEBUG
    INFO        = LoggerLevel.INFO
    WARNING     = LoggerLevel.WARNING
    ERROR       = LoggerLevel.ERROR
    CRITICAL    = LoggerLevel.CRITICAL

    # https://docs.python.org/zh-cn/3/library/logging.handlers.html#timedrotatingfilehandler
    FILE_ROATING_WHEN       = 'H'
    FILE_ROATING_INTERVAL   = 6
    FILE_ROATING_BACKCOUNT  = 12

    FILE_FORMAT = r'%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
    STREAM_FORMAT = r'[%(name)s] %(levelname)s: %(message)s'
    DEFAULT_LOGGING_LEVEL = INFO

    # 日志存放目录
    __log_root_dir = None

    DEFAULT_CHANNEL_NAME = 'default'

    def __init__(
        self, logger_name:str='', extend_name:str='', enable_file:bool=False, 
        enable_stream:bool=True, log_dirname:str='', log_filename:str='',
        channel_name_length:int=None
    ):
        logger_name = logger_name if logger_name else self.__class__.__name__
        self.__log_dirname:str    = log_dirname if log_dirname else logger_name
        self.__log_filename:str   = log_filename if log_filename else f"{logger_name}.log"

        # extend_name的作用是防止多进程日志重复问题,当一个类多线程运行时,如果logger name相同
        # 则会造成logger相互影响
        self.__logger_name = logger_name
        if extend_name:
            self.__logger_name = f"{logger_name}-{extend_name}"
        else:
            self.__logger_name = logger_name

        self.__logger:logging.Logger = logging.getLogger(self.__logger_name)
        
        self.__file_handler = None
        self.__stream_handler = None
        
        self.__channels:dict[str, LoggerChannel] = {}
        self.__channel_name_length:Union[int, None] = channel_name_length

        self.__logger.handlers.clear()
        self.__logger.propagate = False # 如果该属性为True,日志消息会传递到更高级的记录器中(比如根记录器)导致日志被多次打印输出。
        self.enable_stream(enable_stream)
        self.enable_file(enable_file)
        self.set_level(SimpleLogger.DEFAULT_LOGGING_LEVEL)

    @property
    def channel_name_length(self):
        return self.__channel_name_length

    @property
    def logger(self):
        return self.__logger

    def __create_channel(self, name:str):
        if name in self.__channels:
            raise pyutils.LoggerException(f"duplicate logger channel name: {name}")
        self.__channels[name] = LoggerChannel(self, name)

    def channel(self, name:str=''):
        name = name if name else SimpleLogger.DEFAULT_CHANNEL_NAME
        if name not in self.__channels: self.__create_channel(name)
        return self.__channels[name]
    
    def channel_names(self) -> list[str]:
        return list(self.__channels.keys())

    @classmethod
    def set_default_log_dir(cls, dirpath:os.PathLike):
        cls.__log_root_dir = Path(dirpath)
    
    def set_log_dir(self, log_dir:os.PathLike):
        self.__log_root_dir = Path(log_dir)

    def enable_stream(self, enable=True):
        if enable:
            self.__stream_handler = logging.StreamHandler()
            self.__stream_handler.setFormatter(SimpleStreamFormatter())
            self.__logger.addHandler(self.__stream_handler)
        elif self.__stream_handler:
            self.__logger.removeHandler(self.__stream_handler)
            self.__stream_handler = None

    def enable_merger(self):
        if not self.__stream_handler: return
        self.__stream_handler.setStream(LogMerger())

    def disable_merger(self):
        if not self.__stream_handler: return
        self.__stream_handler.setStream(sys.stdout)

    def enable_file(self, enable=True):
        if enable and (not self.__log_root_dir or not os.path.exists(self.__log_root_dir)):
            self.warning("Not set log_dir or it not exist, can not enable file logging.")
            return
        
        if enable:
            file_log_dir = self.__log_root_dir.joinpath(self.__log_dirname)
            file_log_path = file_log_dir.joinpath(self.__log_filename)
            file_log_dir.mkdir(parents=True, exist_ok=True)
            self.__file_handler = handlers.TimedRotatingFileHandler(
                filename    = file_log_path, 
                when        = SimpleLogger.FILE_ROATING_WHEN, 
                interval    = SimpleLogger.FILE_ROATING_INTERVAL, 
                backupCount = SimpleLogger.FILE_ROATING_BACKCOUNT, 
                encoding    = 'utf-8'
            )
            self.__file_handler.setFormatter(logging.Formatter(
                SimpleLogger.FILE_FORMAT
            ))
            self.__file_handler.setLevel(LoggerLevel.INFO)
            self.__logger.addHandler(self.__file_handler)
        elif self.__file_handler:
            self.__logger.removeHandler(self.__file_handler)
            self.__file_handler = None
    
    def setLevel(self, level:Union[str, int]):
        '''
            deprecated, please use `set_level` instead.
        '''
        self.set_level(level)
    
    def set_level(self, level:Union[str, int]):
        if isinstance(level, str): level = LoggerLevel.get_level(level)
        self.__logger.setLevel(level)
        if self.__stream_handler:
            self.__stream_handler.setLevel(level)
        # 不在日志文件中记录调试信息
        if self.__file_handler and level > LoggerLevel.DEBUG:
            self.__file_handler.setLevel(level)
    
    def set_callback(self, level:Union[str, int], callback:Callable[[ByteString], None], channel:str=''):
        self.channel(channel).set_callback(level, callback)
    
    def clear_callback(self, level:Union[str, int], channel:str=''):
        self.channel(channel).clear_callback(level)

    def log(self, msg, level=LoggerLevel.INFO, channel_name:str=''):
        self.channel(channel_name).log(msg, level)

    def debug(self, msg, channel_name:str=''):
        self.log(msg, SimpleLogger.DEBUG, channel_name)

    def info(self, msg, channel_name:str=''):
        self.log(msg, SimpleLogger.INFO, channel_name)

    def warning(self, msg, channel_name:str=''):
        self.log(msg, SimpleLogger.WARNING, channel_name)

    def error(self, msg, channel_name:str=''):
        self.log(msg, SimpleLogger.ERROR, channel_name)

    def critical(self, msg, channel_name:str=''):
        self.log(msg, SimpleLogger.CRITICAL, channel_name)
    
    def log_col(self, msgs:Iterable, width:int, spliter:str='|', level=LoggerLevel.INFO, channel_name:str=''):
        msgs = [ f"{str(m).ljust(width)}" for m in msgs]
        msg = spliter.join(msgs)
        self.log(msg, level, channel_name)
    
    def debug_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.log_col(msgs, width, spliter, SimpleLogger.DEBUG, channel_name)
    
    def info_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.log_col(msgs, width, spliter, SimpleLogger.INFO, channel_name)
    
    def warning_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.log_col(msgs, width, spliter, SimpleLogger.WARNING, channel_name)
    
    def error_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.log_col(msgs, width, spliter, SimpleLogger.ERROR, channel_name)
    
    def critical_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.log_col(msgs, width, spliter, SimpleLogger.CRITICAL, channel_name)
    
    @staticmethod
    def for_current_file():
        return SimpleLogger(os.path.basename(__file__))

class LogMerger(TextIO):

    def __init__(self):
        self.__cached_line = None
        self.__cache_hits = 0

    def write(self, msg:Union[bytes, str]):
        if msg.endswith('\n'): msg = msg[:-1]
        if msg == self.__cached_line:
            self.__cache_hits += 1
            if isinstance(msg, str):
                line_breaks = len(list(re.finditer(r'(\r\n|\r|\n)', msg)))
                Cursor.up(line_breaks)
            Cursor.up()
            sys.stdout.write(f"{msg}(repeat: {self.__cache_hits+1})")
        else:
            self.__cache_hits = 0
            sys.stdout.write(msg)
        sys.stdout.write('\n')
        self.__cached_line = msg

class Cursor:

    @staticmethod
    def up(row=1):
        if row < 1: return
        sys.stdout.write('\033[{}F'.format(row))
