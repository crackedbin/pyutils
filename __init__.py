
import sys

from .file import *
from .exception import *
from .logger import *

# 检查版本

if sys.version_info.major != 3:
    raise PyUtilsException("PyUtils only support python3!")