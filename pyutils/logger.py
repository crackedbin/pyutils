
from __future__ import annotations

import os
import re
import sys
import logging

from logging import LogRecord, handlers, Formatter, Logger
from typing import Callable, Iterable, ByteString, TextIO, Union, Optional
from pathlib import Path

from pyutils.misc import TerminalCursor
from pyutils.exception import LoggerException

__all__ = [
    'SimpleLogger'
]

class LogLevel:

    DEBUG       = logging.DEBUG
    INFO        = logging.INFO
    SUC         = logging.INFO + 1
    WARNING     = logging.WARNING
    ERROR       = logging.ERROR
    CRITICAL    = logging.CRITICAL

    level2name = {
        CRITICAL: 'CRITICAL',
        ERROR: 'ERROR',
        WARNING: 'WARNING',
        INFO: 'INFO',
        DEBUG: 'DEBUG',
        SUC: 'SUC'
    }
    name2level = {
        'CRITICAL': CRITICAL,
        'ERROR': ERROR,
        'WARNING': WARNING,
        'INFO': INFO,
        'DEBUG': DEBUG,
        'SUC': SUC
    }

    @classmethod
    def get_level(cls, level:Union[str, int]):
        result = cls.level2name.get(level)
        if result is not None:
            return result
        result = cls.name2level.get(level)
        if result is not None:
            return result
        return "Level %s" % level

logging.addLevelName(LogLevel.SUC, 'SUC')

color_endc = '\x1b[0m'
def colorful(color:str, content:str):
    return f"{color}{content}{color_endc}"

class SimpleStreamFormatter(logging.Formatter):

    STREAM_FORMAT = r'[%(name)s]%(channel)s %(levelname)s: %(message)s'

    COLOR = {
        'INFO'      : '\x1b[94m',
        'WARNING'   : '\x1b[93m',
        'ERROR'     : '\x1b[91m',
        'CRITICAL'  : '\x1b[41m',
        'DEBUG'     : '\x1b[95m',
        'SUC'       : '\x1b[32m',
        'ENDC'      : '\x1b[0m'
    }

    FORMATTERS = {'default': Formatter(STREAM_FORMAT)}
    for name, level in LogLevel.name2level.items():
        FORMATTERS[level] = Formatter(colorful(COLOR[name], STREAM_FORMAT))

    def enable_date(self):
        _format = f"%(asctime)s - {self.STREAM_FORMAT}"
        self.FORMATTERS = {'default': Formatter(_format)}
        for name, level in LogLevel.name2level.items():
            self.FORMATTERS[level] = Formatter(colorful(self.COLOR[name], _format))

    def format(self, record:LogRecord) -> str:  
        if record.levelno in self.FORMATTERS:
            formatter = self.FORMATTERS[record.levelno]
        else:
            formatter = self.FORMATTERS['default']

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

    DEFAULT_NAME_PADDING = '.'

    def __init__(self, host:SimpleLogger, channel_name:str):
        self.name = channel_name
        self.__host = host
        self.__enable = True
        self.__callbacks = {}
        self.should_display_name:bool = True
        _length = self.__host.channel_name_length
        if isinstance(_length, int):
            if len(self.name) > _length:
                self.__name_to_show = f"({self.name[:_length]})"
            else:
                self.__name_to_show = f"({self.name.rjust(_length, self.DEFAULT_NAME_PADDING)})"
        else:
            self.__name_to_show = f"({self.name})"

    def enable(self):
        self.__enable = True

    def disable(self):
        self.__enable = False

    def __do_log(self, msg, level):
        if not self.__enable: return
        should_display_name = self.__host.should_display_channel_name and self.should_display_name
        name_to_show = self.__name_to_show if should_display_name else ''
        self.__host.raw_logger.log(level, msg, extra={'channel': name_to_show})
        if level not in self.__callbacks: return
        self.__callbacks[level](msg, self.__host)

    def log(self, msg, level=LogLevel.INFO):
        self.__do_log(msg, level)

    def debug(self, msg):
        self.log(msg, LogLevel.DEBUG)

    def info(self, msg):
        self.log(msg, LogLevel.INFO)

    def suc(self, msg):
        self.log(msg, LogLevel.SUC)

    def warning(self, msg):
        self.log(msg, LogLevel.WARNING)

    def error(self, msg):
        self.log(msg, LogLevel.ERROR)

    def critical(self, msg):
        self.log(msg, LogLevel.CRITICAL)

    def log_col(self, msgs:Iterable, width:int, spliter:str='|', level=LogLevel.INFO):
        msgs = [ f"{str(m).ljust(width)}" for m in msgs]
        spliter = f"{spliter} "
        msg = f"{spliter}{spliter.join(msgs)}"
        self.log(msg, level)

    def debug_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.DEBUG)

    def info_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.INFO)

    def suc_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.SUC)

    def warning_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.WARNING)

    def error_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.ERROR)

    def critical_col(self, msgs:Iterable, width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.CRITICAL)

    def set_callback(
        self, level:Union[str, int], callback:Callable[[ByteString, SimpleLogger], None]
    ):
        if isinstance(level, str): level = LogLevel.get_level(level)
        self.__callbacks[level] = callback

    def clear_callback(self, level:Union[str, int]):
        if isinstance(level, str): level = LogLevel.get_level(level)
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

    # https://docs.python.org/zh-cn/3/library/logging.handlers.html#timedrotatingfilehandler
    FILE_ROATING_WHEN       = 'H'
    FILE_ROATING_INTERVAL   = 6
    FILE_ROATING_BACKCOUNT  = 12

    FILE_FORMAT = r'%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
    DEFAULT_LOGGING_LEVEL = LogLevel.INFO

    # 日志存放目录
    DEFAULT_DIR = None

    DEFAULT_CHANNEL_NAME = 'default'

    def __init__(
        self, logger_name:str='', extend_name:str='', enable_file:bool=False, 
        enable_stream:bool=True, log_dirname:str='', log_filename:str='',
        channel_name_length:int=None, share_global:bool=False
    ):
        logger_name = logger_name if logger_name else self.__class__.__name__
        self.dirname    = log_dirname if log_dirname else logger_name
        self.filename   = log_filename if log_filename else f"{logger_name}.log"

        # extend_name的作用是防止多进程日志重复问题,当一个类多线程运行时,如果logger name相同
        # 则会造成logger相互影响
        self.name = logger_name
        if extend_name:
            self.name = f"{logger_name}-{extend_name}"
        else:
            self.name = logger_name

        if not share_global:
            self.raw_logger = Logger(self.name)
        else:
            self.raw_logger = logging.getLogger(self.name)

        self.file_handler = None
        self.stream_handler = None
        self.stream_formatter = SimpleStreamFormatter()

        self.channels:dict[str, LoggerChannel] = {}
        self.channel_name_length:Optional[int] = channel_name_length
        self.should_display_channel_name = True

        self.raw_logger.handlers.clear()
        self.raw_logger.propagate = False # 如果该属性为True,日志消息会传递到更高级的记录器中(比如根记录器)导致日志被多次打印输出。
        self.enable_stream(enable_stream)
        self.enable_file(enable_file)
        self.set_level(SimpleLogger.DEFAULT_LOGGING_LEVEL)

        # not to display default channel name
        self.channel().should_display_name = False

    def __create_channel(self, name:str):
        if name in self.channels:
            raise LoggerException(f"duplicate logger channel name: {name}")
        self.channels[name] = LoggerChannel(self, name)

    def channel(self, name:str=''):
        name = name if name else SimpleLogger.DEFAULT_CHANNEL_NAME
        if name not in self.channels: self.__create_channel(name)
        return self.channels[name]

    @classmethod
    def set_default_dir(cls, dirpath:os.PathLike):
        cls.DEFAULT_DIR = Path(dirpath)

    def set_dir(self, log_dir:os.PathLike):
        self.DEFAULT_DIR = Path(log_dir)

    def enable_stream(self, enable=True):
        if enable:
            self.stream_handler = logging.StreamHandler()
            self.stream_handler.setFormatter(self.stream_formatter)
            self.raw_logger.addHandler(self.stream_handler)
        elif self.stream_handler:
            self.raw_logger.removeHandler(self.stream_handler)
            self.stream_handler = None

    def enable_merger(self):
        if not self.stream_handler: return
        self.stream_handler.setStream(LogMerger())

    def disable_merger(self):
        if not self.stream_handler: return
        self.stream_handler.setStream(sys.stdout)

    def enable_file(self, enable=True):
        if enable and (not self.DEFAULT_DIR or not self.DEFAULT_DIR.exists()):
            self.warning("Not set log_dir or it not exist, can not enable file logging.")
            return

        if enable:
            file_log_dir = self.DEFAULT_DIR.joinpath(self.dirname)
            file_log_path = file_log_dir.joinpath(self.filename)
            file_log_dir.mkdir(parents=True, exist_ok=True)
            self.file_handler = handlers.TimedRotatingFileHandler(
                filename    = file_log_path, 
                when        = SimpleLogger.FILE_ROATING_WHEN, 
                interval    = SimpleLogger.FILE_ROATING_INTERVAL, 
                backupCount = SimpleLogger.FILE_ROATING_BACKCOUNT, 
                encoding    = 'utf-8'
            )
            self.file_handler.setFormatter(logging.Formatter(
                SimpleLogger.FILE_FORMAT
            ))
            self.file_handler.setLevel(LogLevel.INFO)
            self.raw_logger.addHandler(self.file_handler)
        elif self.file_handler:
            self.raw_logger.removeHandler(self.file_handler)
            self.file_handler = None

    def set_level(self, level:Union[str, int]):
        if isinstance(level, str): level = LogLevel.get_level(level)
        self.raw_logger.setLevel(level)
        if self.stream_handler:
            self.stream_handler.setLevel(level)
        # 不在日志文件中记录调试信息
        if self.file_handler and level > LogLevel.DEBUG:
            self.file_handler.setLevel(level)

    def set_callback(
        self, level:Union[str, int], callback:Callable[[ByteString, SimpleLogger], None]
    ):
        for channel in self.channels.values():
            channel.set_callback(level, callback)

    def clear_callback(self, level:Union[str, int]):
        for channel in self.channels.values():
            channel.clear_callback(level)

    def log(self, msg, level=LogLevel.INFO, channel_name:str=''):
        self.channel(channel_name).log(msg, level)

    def debug(self, msg, channel_name:str=''):
        self.channel(channel_name).log(msg, LogLevel.DEBUG)

    def info(self, msg, channel_name:str=''):
        self.channel(channel_name).log(msg, LogLevel.INFO)

    def suc(self, msg, channel_name:str=''):
        self.channel(channel_name).log(msg, LogLevel.SUC)

    def warning(self, msg, channel_name:str=''):
        self.channel(channel_name).log(msg, LogLevel.WARNING)

    def error(self, msg, channel_name:str=''):
        self.channel(channel_name).log(msg, LogLevel.ERROR)

    def critical(self, msg, channel_name:str=''):
        self.channel(channel_name).log(msg, LogLevel.CRITICAL)

    def log_col(self, msgs:Iterable, width:int, spliter:str='|', level=LogLevel.INFO, channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, level)

    def debug_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, LogLevel.DEBUG)

    def info_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, LogLevel.INFO)

    def suc_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, LogLevel.SUC)

    def warning_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, LogLevel.WARNING)

    def error_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, LogLevel.ERROR)

    def critical_col(self, msgs:Iterable, width:int, spliter:str='|', channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, LogLevel.CRITICAL)

    @staticmethod
    def for_current_file():
        return SimpleLogger(os.path.basename(__file__))

'''
TODO: 实现一个LazySimpleLogger，用于在需要的时候才初始化SimpleLogger，
      而不需要每次继承SimpleLogger时都显示地调用__init__方法。
候选方案：
    1. 首先在实现一个SimpleLogger.__getattr__
        ```
        def __getattr__(self, attr:str, *args, **kwargs):
            return self.__getattribute__(attr)
        ```
    2. 然后在实现一个LazySimpleLogger，它的__getattr__方法中调用SimpleLogger.__getattr__
        ```
        class LazySimpleLogger(SimpleLogger):

        _lazy_logger_initialized = False

        def __getattr__(self, attr:str, *args, **kwargs):
            if not SimpleLogger.__getattr__(self, '_lazy_logger_initialized'):
                SimpleLogger.__setattr__(self, '_lazy_logger_initialized', True)
                SimpleLogger.__init__(self)
            return SimpleLogger.__getattr__(self, attr, *args, **kwargs)
        ```
该方案会对SimpleLogger的性能造成一定影响，因为增加了__getattr__这个方法，
导致SimpleLogger的性能下降约20%。
'''

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
                TerminalCursor.up(line_breaks)
            TerminalCursor.up()
            sys.stdout.write(f"{msg}(~{self.__cache_hits+1})")
        else:
            self.__cache_hits = 0
            sys.stdout.write(msg)
        sys.stdout.write('\n')
        self.__cached_line = msg

