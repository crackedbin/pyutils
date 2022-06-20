
__all__ = [
    "PyUtilsException"
]

class PyUtilsException(Exception):
    '''PyUtilException'''

class FileException(PyUtilsException):
	'''FileException'''

class LoggerException(PyUtilsException):
    '''LoggerException'''

class MiscException(PyUtilsException):
    '''MiscException'''

class NoItem(MiscException):
    '''NoItem'''