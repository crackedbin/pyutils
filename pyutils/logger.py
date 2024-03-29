
from __future__ import annotations

import os
import inspect
import logging
import typing_extensions

from enum import Enum
from dataclasses import dataclass, field
from logging import LogRecord, Formatter, Logger
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from typing import Callable, Iterable, ByteString, Union
from pathlib import Path

from pyutils.exception import LoggerException

__all__ = [
    'SimpleLogger', 'LoggerOption', 'LoggerMixin', 'FileOption',
    'ChannelOption', 'StreamOption'
]

class LogLevel(int, Enum):

    VERBOSE     = logging.DEBUG - 1
    DEBUG       = logging.DEBUG
    INFO        = logging.INFO
    SUCCESS     = logging.INFO + 1
    WARNING     = logging.WARNING
    ERROR       = logging.ERROR
    CRITICAL    = logging.CRITICAL

    @classmethod
    def level_map(cls):
        return {
            cls.VERBOSE: 'VERBOSE',
            cls.DEBUG: 'DEBUG',
            cls.INFO: 'INFO',
            cls.SUCCESS: 'SUCCESS',
            cls.WARNING: 'WARNING',
            cls.ERROR: 'ERROR',
            cls.CRITICAL: 'CRITICAL'
        }

    @classmethod
    def name_map(cls):
        return {
            'VERBOSE': cls.VERBOSE,
            'DEBUG': cls.DEBUG,
            'INFO': cls.INFO,
            'SUC': cls.SUCCESS,
            'SUCCESS': cls.SUCCESS,
            'WARN': cls.WARNING,
            'WARNING': cls.WARNING,
            'ERROR': cls.ERROR,
            'ERR': cls.ERROR,
            'CRITICAL': cls.CRITICAL
        }

    @classmethod
    def get_level(cls, level:Union[str, int]):
        result = cls.level_map().get(level)
        if result is not None:
            return result
        result = cls.name_map().get(level)
        if result is not None:
            return result
        return f"Level {level}"

    @classmethod
    def level2name(cls, level:int):
        return cls.level_map().get(level, f"Level {level}")

    @classmethod
    def name2level(cls, name:str):
        return cls.name_map().get(name, None)

    @classmethod
    def just_level(cls, may_level:Union[int, str]) -> int:
        if isinstance(may_level, int): return may_level
        may_level = may_level.upper()
        return cls.name2level(may_level)

    @classmethod
    def just_name(cls, may_name:Union[int, str]) -> str:
        if isinstance(may_name, str): return may_name.upper()
        return cls.level2name(may_name)

logging.addLevelName(LogLevel.SUCCESS, 'SUCCESS')
logging.addLevelName(LogLevel.VERBOSE, 'VERBOSE')

color_endc = '\x1b[0m'
def colorful(color:str, content:str):
    return f"{color}{content}{color_endc}"

class SimpleStreamFormatter(logging.Formatter):

    STREAM_FORMAT = r'[%(name)s]%(channel)s %(levelname)s: %(message)s'

    COLOR = {
        'VERBOSE'   : '\x1b[0;36m',
        'DEBUG'     : '\x1b[0;35m',
        'INFO'      : '\x1b[1;34m',
        'SUCCESS'   : '\x1b[1;32m',
        'WARNING'   : '\x1b[1;33m',
        'ERROR'     : '\x1b[1;31m',
        'CRITICAL'  : '\x1b[0;37;41m',
        'ENDC'      : '\x1b[0m'
    }

    FORMATTERS = {'default': Formatter(STREAM_FORMAT)}
    for level, name in LogLevel.level_map().items():
        FORMATTERS[level] = Formatter(colorful(COLOR[name], STREAM_FORMAT))

    def __init__(
        self, fmt: str | None = None, datefmt: str | None = None, style = "%", 
        validate: bool = True
    ):
        logging.Formatter.__init__(self, fmt, datefmt, style, validate)

    def enable_date(self):
        _format = f"%(asctime)s - {self.STREAM_FORMAT}"
        self.FORMATTERS = {'default': Formatter(_format)}
        for name, level in LogLevel.name_map().items():
            self.FORMATTERS[level] = Formatter(colorful(self.COLOR[name], _format))

    def format(self, record:LogRecord) -> str:  
        if record.levelno in self.FORMATTERS:
            formatter = self.FORMATTERS[record.levelno]
        else:
            formatter = self.FORMATTERS['default']

        if hasattr(record, 'channel'):
            channel = getattr(record, 'channel')
            setattr(record, 'channel', f"{channel}")

        return formatter.format(record)

@dataclass
class ChannelOption:
    name_length:int | None = None
    display_name:bool = True
    name_padding:str = '.'

@dataclass
class StreamOption:
    enable:bool = True
    format:str = r'%(asctime)s - [%(name)s]%(channel)s %(levelname)s: %(message)s'
    default_level:int = LogLevel.INFO

@dataclass
class FileOption:
    enable:bool = False
    root_dir:Path | None = None
    dirname:str | None = None
    filename:str | None = None
    format:str = r'%(asctime)s - [%(name)s%(channel)s] %(levelname)s: %(message)s'
    default_level:str = "INFO"
    encoding:str = "utf-8"
    concurrent:bool = False
    backup_count:int = 0
    # Size Rotating
    rotating:bool = False
    mode:str = "a"
    max_bytes:int = 1024 * 1024 # 默认日志文件最大为1M
    # Time Rotating
    time_rotating:bool = True
    when:str = "h"
    interval:str = 1

@dataclass
class LoggerOption:
    name:str | None = None
    extend_name:str | None = None
    share_global:bool = False
    default_channel_name:str = "default"
    channel:ChannelOption = field(default_factory=ChannelOption)
    stream:StreamOption = field(default_factory=StreamOption)
    file:FileOption = field(default_factory=FileOption)

class LoggerInterface:

    def log(self, msg:str, level:LogLevel):
        raise NotImplementedError()

    def verbose(self, msg:str):
        return self.log(msg, LogLevel.VERBOSE)

    def debug(self, msg:str):
        return self.log(msg, LogLevel.DEBUG)
    
    def info(self, msg:str):
        return self.log(msg, LogLevel.INFO)
    
    def suc(self, msg:str):
        return self.log(msg, LogLevel.SUCCESS)
    
    def warning(self, msg:str):
        return self.log(msg, LogLevel.WARNING)
    
    def error(self, msg:str):
        return self.log(msg, LogLevel.ERROR)
    
    def critical(self, msg:str):
        return self.log(msg, LogLevel.CRITICAL)

    def log_col(
        self, msgs:Iterable[str], width:int, spliter:str='|', 
        level:LogLevel=LogLevel.INFO
    ):
        raise NotImplementedError()

    def verbose_col(self, msgs:Iterable[str], width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.VERBOSE)

    def debug_col(self, msgs:Iterable[str], width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.DEBUG)

    def info_col(self, msgs:Iterable[str], width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.INFO)

    def suc_col(self, msgs:Iterable[str], width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.SUCCESS)

    def warning_col(self, msgs:Iterable[str], width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.WARNING)

    def error_col(self, msgs:Iterable[str], width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.ERROR)

    def critical_col(self, msgs:Iterable[str], width:int, spliter:str='|'):
        self.log_col(msgs, width, spliter, LogLevel.CRITICAL)

class LogChannel(LoggerInterface):

    def __init__(
        self, host:LoggerMixin, name:str, option:LoggerOption, logger:Logger, 
        global_callbacks:dict
    ):
        self.name = name
        self.option = option
        self.enable = True
        self.logger = logger
        self.host = host
        self.callbacks:dict[int, list[Callable]] = {}
        self.global_callbacks = global_callbacks
        name_length = self.option.channel.name_length
        if isinstance(name_length, int):
            if len(self.name) > name_length:
                self.name_to_show = f"({self.name[:name_length]})"
            else:
                self.name_to_show = f"({self.name.rjust(name_length, self.option.channel.name_padding)})"
        elif self.name:
            self.name_to_show = f"({self.name})"
        else:
            self.name_to_show = ""

    def log(self, msg:ByteString, level=LogLevel.INFO):
        if not self.enable: return
        name_to_show = self.name_to_show if self.option.channel.display_name else ''
        self.logger.log(level, msg, extra={'channel': name_to_show})
        for callback in self.callbacks.setdefault(level, []):
            callback(msg, self.host)
        for callback in self.global_callbacks.setdefault(level, []):
            callback(msg, self.host)

    def log_col(self, msgs:Iterable, width:int, spliter:str='|', level=LogLevel.INFO):
        if not self.enable: return
        msgs = [ f"{str(m).ljust(width)}" for m in msgs]
        spliter = f"{spliter} "
        msg = f"{spliter}{spliter.join(msgs)}"
        self.log(msg, level)

    def add_log_callback(
        self, level:Union[str, int], callback:Callable[[ByteString, SimpleLogger], None]
    ):
        sig = inspect.signature(callback)
        param_count = len(sig.parameters)
        def wrap(msg, logger):
            if param_count < 1:
                return callback()
            elif param_count == 1:
                return callback(msg)
            elif param_count >= 2:
                return callback(msg, logger)
        self.callbacks.setdefault(LogLevel.just_level(level), []).append(wrap)

    def clear_log_callbacks(self, level:Union[str, int, None]=None):
        if level is None:
            self.callbacks.clear()
            return
        level = LogLevel.just_level(level)
        self.callbacks.setdefault(level, []).clear()

class LoggerMixin(LoggerInterface):

    def __init__(self, option:LoggerOption=None):
        LoggerInterface.__init__(self)
        self.__option = option if option else LoggerOption()
        self.__channels:dict[str, LogChannel] = {}
        self.__callbacks:dict[int, list[Callable]] = {}
        self.__set_name()
        self.__init_logger()

    @property
    def log_option(self):
        return self.__option

    def __set_name(self):
        name = self.__option.name
        if not name: name = self.__class__.__name__
        if self.__option.extend_name: name = f"{name}-{self.__option.extend_name}"
        self.__name = name

    def __init_logger(self):
        if not self.__option.share_global:
            self.__logger = Logger(self.__name)
        else:
            self.__logger = logging.getLogger(self.__name)
        self.__stream_formatter = SimpleStreamFormatter()
        self.__file_handler:logging.FileHandler | None = None
        self.__stream_handler:logging.StreamHandler | None = None
        self.__logger.handlers.clear()
        self.__logger.propagate = False
        self.set_streamlog(self.__option.stream.enable)
        self.set_filelog(self.__option.file.enable)

    def __create_channel(self, name:str):
        if name in self.__channels:
            raise LoggerException(f"duplicate logger channel name: {name}")
        self.__channels[name] = LogChannel(
            self, name, self.__option, self.__logger, self.__callbacks
        )

    def channel(self, name:str=''):
        if name not in self.__channels: self.__create_channel(name)
        return self.__channels[name]

    def set_streamlog(self, enable:bool=True):
        if enable == bool(self.__stream_handler): return
        if enable:
            self.__stream_handler = logging.StreamHandler()
            self.__stream_handler.setFormatter(self.__stream_formatter)
            self.__logger.addHandler(self.__stream_handler)
        elif self.__stream_handler:
            self.__logger.removeHandler(self.__stream_handler)
            self.__stream_handler = None

    def __get_filelog_path(self):
        option = self.__option.file
        root_dir = option.root_dir
        if not root_dir: raise TypeError("Must set file root dir")
        root_dir = Path(root_dir)
        if root_dir.exists() and not root_dir.is_dir():
            raise RuntimeError(f"Path {root_dir} is not a directory")
        dirname = option.dirname if option.dirname else self.__name
        filename = option.filename if option.filename else f"{self.__name}.log"
        log_dir = root_dir / dirname
        if not log_dir.exists(): log_dir.mkdir(exist_ok=True, parents=True)
        return log_dir / filename

    def __get_filehandler(self):
        opt = self.__option.file
        filepath = self.__get_filelog_path()
        encoding = opt.encoding
        if opt.time_rotating:
            if opt.concurrent:
                try:
                    from concurrent_log_handler import ConcurrentTimedRotatingFileHandler
                except ModuleNotFoundError:
                    err_msgs = [
                        "please install concurrent-log-handler",
                        "'pip install concurrent-log-handler' or 'poetry add concurrent-log-handler'"
                    ]
                    raise ModuleNotFoundError(", ".join(err_msgs))
                HandlerClass = ConcurrentTimedRotatingFileHandler
            else:
                HandlerClass = TimedRotatingFileHandler
            handler = HandlerClass(
                filepath, encoding=encoding, when=opt.when, interval=opt.interval,
                backupCount=opt.backup_count, delay=True
            )
        elif opt.rotating:
            if opt.concurrent:
                try:
                    from concurrent_log_handler import ConcurrentRotatingFileHandler
                except ModuleNotFoundError:
                    err_msgs = [
                        "please install concurrent-log-handler",
                        "'pip install concurrent-log-handler' or 'poetry add concurrent-log-handler'"
                    ]
                    raise ModuleNotFoundError(", ".join(err_msgs))
                HandlerClass = ConcurrentRotatingFileHandler
            else:
                HandlerClass = RotatingFileHandler
            handler = HandlerClass(
                filepath, encoding=opt.encoding, mode=opt.mode, maxBytes=opt.max_bytes, 
                backupCount=opt.backup_count, delay=True
            )
        else:
            handler = logging.FileHandler(filepath, encoding=encoding, delay=True)
        handler.setLevel(LogLevel.just_level(opt.default_level))
        formatter = Formatter(opt.format)
        handler.setFormatter(formatter)
        return handler

    def set_filelog(self, enable:bool=True):
        '''
            not implement yet
        '''
        if enable == bool(self.__file_handler): return
        if enable:
            self.__file_handler = self.__get_filehandler()
            self.__logger.addHandler(self.__file_handler)
        elif self.__file_handler:
            self.__logger.removeHandler(self.__file_handler)
            self.__file_handler = None

    def set_level(self, level:Union[str, int]):
        level = LogLevel.just_level(level)
        self.__logger.setLevel(level)
        if self.__stream_handler: self.__stream_handler.setLevel(level)
        if self.__file_handler: self.__file_handler.setLevel(level)

    def add_log_callback(
        self, level:Union[str, int], callback:Callable[[ByteString, SimpleLogger], None]
    ):
        sig = inspect.signature(callback)
        param_count = len(sig.parameters)
        def wrap(msg, logger):
            if param_count < 1:
                return callback()
            elif param_count == 1:
                return callback(msg)
            elif param_count >= 2:
                return callback(msg, logger)
        self.__callbacks.setdefault(LogLevel.just_level(level), []).append(wrap)

    def clear_log_callbacks(self, level:Union[str, int, None]=None):
        if level is None:
            self.__callbacks.clear()
            return
        level = LogLevel.just_level(level)
        self.__callbacks.setdefault(level, []).clear()

    def log(self, msg, level=LogLevel.INFO):
        self.channel().log(msg, level)

    def log_col(self, msgs:Iterable, width:int, spliter:str='|', level=LogLevel.INFO, channel_name:str=''):
        self.channel(channel_name).log_col(msgs, width, spliter, level)

@typing_extensions.deprecated(
    "The SimpleLogger is deprecated, use LoggerMixin insted. And SimpleLogger will be removed in version 3.0.0"
)
class SimpleLogger(LoggerMixin):
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
        option = LoggerOption()
        option.name = logger_name
        option.extend_name = extend_name
        option.file.enable = enable_file
        option.stream.enable = enable_stream
        option.file.dirname = log_dirname
        option.file.filename = log_filename
        option.channel.name_length = channel_name_length
        option.share_global = share_global
        LoggerMixin.__init__(self, option)

    def enable_stream(self, enable=True):
        self.set_streamlog(enable)

    def enable_file(self, enable=True):
        self.set_filelog(enable)

    def callback(self, level:Union[str, int]):
        def decorator(func):
            self.set_callback(level, func)
        return decorator

    def set_callback(
        self, level:Union[str, int], callback:Callable[[ByteString, SimpleLogger], None]
    ):
        self.add_log_callback(level, callback)

    def clear_callbacks(self, level:Union[str, int]):
        self.clear_log_callbacks(level)

    @staticmethod
    def for_current_file():
        return SimpleLogger(os.path.basename(__file__))
