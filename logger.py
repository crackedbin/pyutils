
from __future__ import annotations

import os
import logging
import importlib

from logging import LogRecord, handlers

from .file import mkdir
from .exception import PyUtilsException

__all__ = [
    'PyUtilsLoggerException', 'LoggerBase'
]

class PyUtilsLoggerException(PyUtilsException):
    '''PyUtilsLoggerException'''

class BaseStreamFormatter(logging.Formatter):
    '''
        base stream formatter
        
        https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    '''
    COLOR_CONSTANTS = {
        'INFO'      : '\x1b[94m',
        'WARNING'   : '\x1b[93m',
        'ERROR'     : '\x1b[91m',
        'CRITICAL'  : '\x1b[41m',
        'DEBUG'     : '\x1b[95m',
        'ENDC'      : '\x1b[0m'
    }

    def __init__(self, fmt=None, datefmt=None, style='%', validate=True) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)
        constants = BaseStreamFormatter.COLOR_CONSTANTS
        self.FORMATS = {
            LoggerBase.DEBUG   : f"{constants['DEBUG']}{fmt}{constants['ENDC']}",
            LoggerBase.INFO    : f"{constants['INFO']}{fmt}{constants['ENDC']}",
            LoggerBase.WARNING : f"{constants['WARNING']}{fmt}{constants['ENDC']}",
            LoggerBase.ERROR   : f"{constants['ERROR']}{fmt}{constants['ENDC']}",
            LoggerBase.CRITICAL: f"{constants['CRITICAL']}{fmt}{constants['ENDC']}",
        }
    
    def format(self, record:LogRecord) -> str:
        formatter = logging.Formatter(self.FORMATS[record.levelno])
        return formatter.format(record)

class LoggerChannel:
    '''
        一个LoggerBase及其子类可以拥有多个LoggerChannel
    '''

    def __init__(self, channel_name:str, logger:logging.Logger):
        self.__logger = logger
        self.__name = channel_name
        self.__enable = True

    @property
    def name(self):
        return self.__name

    def enable(self):
        self.__enable = True

    def disable(self):
        self.__enable = False

    def log(self, msg, level=logging.INFO):
        if not self.__enable: return
        self.__logger.log(level, msg)

    def debug(self, msg):
        self.log(msg, LoggerBase.DEBUG)

    def info(self, msg):
        self.log(msg, LoggerBase.INFO)

    def warning(self, msg):
        self.log(msg, LoggerBase.WARNING)

    def error(self, msg):
        self.log(msg, LoggerBase.ERROR)

    def critical(self, msg):
        self.log(msg, LoggerBase.CRITICAL)

class LoggerBase(object):
    '''
        子类要使用该接口的功能,需要在`__init__`中调用`LoggerBase.__init__(self, type(self).__name__)`。
        
        如果子类有多个实例同时运行且需要对这些实例进行区分,可以调用
        `LoggerBase.__init__(self, type(self).__name__, extend_name=<unique name>)`
    '''

    DEBUG       = logging.DEBUG
    INFO        = logging.INFO
    WARNING     = logging.WARNING
    ERROR       = logging.ERROR
    CRITICAL    = logging.CRITICAL

    # https://docs.python.org/zh-cn/3/library/logging.handlers.html#timedrotatingfilehandler
    FILE_ROATING_WHEN       = 'H'
    FILE_ROATING_INTERVAL   = 6
    FILE_ROATING_BACKCOUNT  = 12

    FILE_FORMAT = r'%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
    STREAM_FORMAT = r'[%(name)s] %(levelname)s: %(message)s'
    DEFAULT_LOGGING_LEVEL = INFO

    # 日志存放目录
    __log_dir = None

    # 记录已经实例化的logger name
    __loggers:set[str] = set()

    DEFAULT_CHANNEL_NAME = 'default'

    def __init__(
        self, logger_name:str, extend_name:str='', enable_file:bool=False, 
        enable_stream:bool=True, log_dirname:str='', log_filename:str=''
    ):
        self.__log_dirname:str    = log_dirname if log_dirname else logger_name
        self.__log_filename:str   = log_filename if log_filename else f"{logger_name}.log"

        self.__registered = False

        # extend_name的作用是防止多进程日志重复问题,当一个类多线程运行时,如果logger name相同
        # 则会造成logger相互影响
        self.__logger_name = logger_name
        if extend_name:
            self.__logger_name = f"{logger_name}-{extend_name}"
        else:
            self.__logger_name = logger_name
        
        if self.__logger_name in LoggerBase.__loggers:
            raise PyUtilsLoggerException(f"duplicate logger name: {self.__logger_name}")

        LoggerBase.__loggers.add(self.__logger_name)
        self.__registered = True

        self.__logger:logging.Logger = logging.getLogger(self.__logger_name)
        
        self.__file_handler = None
        self.__stream_handler = None
        
        self.__channels:dict[str, LoggerChannel] = {}

        self.__logger.handlers.clear()
        self.__logger.propagate = False # 如果该属性为True,日志消息会传递到更高级的记录器中(比如根记录器)导致日志被多次打印输出。
        self.enable_stream(enable_stream)
        self.enable_file(enable_file)
        self.setLevel(LoggerBase.DEFAULT_LOGGING_LEVEL)

        self.__create_channel(LoggerBase.DEFAULT_CHANNEL_NAME)
        
    def __del__(self):
        if self.__registered:
            LoggerBase.__loggers.remove(self.__logger_name)

    def __create_channel(self, name:str):
        if name in self.__channels:
            raise PyUtilsLoggerException(f"duplicate logger channel name: {name}")
        self.__channels[name] = LoggerChannel(name, self.__logger)

    def channel(self, name:str=''):
        name = name if name else LoggerBase.DEFAULT_CHANNEL_NAME
        if name not in self.__channels: self.__create_channel(name)
        return self.__channels[name]

    @classmethod
    def set_default_log_dir(cls, dirpath:os.PathLike):
        cls.__log_dir = dirpath
    
    def set_log_dir(self, log_dir:os.PathLike):
        self.__log_dir = log_dir
        if self.__file_handler is None: return
        self.enable_file(False)
        self.enable_file(True)

    def enable_stream(self, enable=True):
        if enable:
            self.__stream_handler = logging.StreamHandler()
            self.__stream_handler.setFormatter(BaseStreamFormatter(
                LoggerBase.STREAM_FORMAT
            ))
            self.__logger.addHandler(self.__stream_handler)
        elif self.__stream_handler:
            self.__logger.removeHandler(self.__stream_handler)
            self.__stream_handler = None

    def enable_file(self, enable=True):
        if enable and (not self.__log_dir or not os.path.exists(self.__log_dir)):
            self.warning("Not set log_dir or it not exist, can not enable file logging.")
            return
        
        if enable:
            file_log_dir = os.path.join(self.__log_dir, self.__log_dirname)
            file_log_path = os.path.join(file_log_dir, self.__log_filename)
            mkdir(file_log_dir)
            self.__file_handler = handlers.TimedRotatingFileHandler(
                filename    = file_log_path, 
                when        = LoggerBase.FILE_ROATING_WHEN, 
                interval    = LoggerBase.FILE_ROATING_INTERVAL, 
                backupCount = LoggerBase.FILE_ROATING_BACKCOUNT, 
                encoding    = 'utf-8'
            )
            self.__file_handler.setFormatter(logging.Formatter(
                LoggerBase.FILE_FORMAT
            ))
            self.__file_handler.setLevel(logging.INFO)
            self.__logger.addHandler(self.__file_handler)
        elif self.__file_handler:
            self.__logger.removeHandler(self.__file_handler)
            self.__file_handler = None
    
    def setLevel(self, level):
        self.__logger.setLevel(level)
        if self.__stream_handler:
            self.__stream_handler.setLevel(level)
        # 不在日志文件中记录调试信息
        if self.__file_handler and level > logging.DEBUG:
            self.__file_handler.setLevel(level)

    def log(self, msg, level=logging.INFO, channel_name:str=''):
        self.channel(channel_name).log(msg, level)

    def debug(self, msg, channel_name:str=''):
        self.log(msg, LoggerBase.DEBUG, channel_name)

    def info(self, msg, channel_name:str=''):
        self.log(msg, LoggerBase.INFO, channel_name)

    def warning(self, msg, channel_name:str=''):
        self.log(msg, LoggerBase.WARNING, channel_name)

    def error(self, msg, channel_name:str=''):
        self.log(msg, LoggerBase.ERROR, channel_name)

    def critical(self, msg, channel_name:str=''):
        self.log(msg, LoggerBase.CRITICAL, channel_name)
    
