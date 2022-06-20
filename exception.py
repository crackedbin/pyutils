
__all__ = [
    "PyUtilsException"
]

class PyUtilsException(Exception):
    '''PyUtilException'''

class MiscException(PyUtilsException):
    '''MiscException'''

class NoItem(MiscException):
    '''NoItem'''