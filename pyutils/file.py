import os
import shutil
import importlib
import importlib.util

from pathlib import Path
from typing import Callable

__all__ = [
    "read_file", "write_file", "mkdir", "mvdir",
    "find_all_files_by_suffix", "delete_dir",
    "delete_file", "find_files", 'import_from'
]


def _open(filepath:os.PathLike, mode:str, encoding:str='utf-8'):
    if 'b' in mode:
        return open(filepath, mode)
    else:
        return open(filepath, mode, encoding=encoding)

def read_file(filepath:os.PathLike, mode:str="r", lines: bool = False, encoding='utf-8'):
    with _open(filepath, mode, encoding=encoding) as fd:
        if not lines:
            content = fd.read()
        else:
            content = fd.readlines()
    return content

def write_file(filepath:os.PathLike, content, mode="w", lines: bool = False):
    with _open(filepath, mode) as f:
        if not lines:
            f.write(content)
        else:
            f.writelines(content)

def delete_dir(dirpath:os.PathLike):
    shutil.rmtree(dirpath, ignore_errors=True)

def delete_file(filepath:os.PathLike):
    if not os.path.exists(filepath):
        return
    os.remove(filepath)

def mvdir(src:os.PathLike, dst:os.PathLike):
    shutil.move(src, dst)

def mkdir(path:os.PathLike, parent:bool=True):
    if os.path.exists(path):
        return
    if parent:
        os.makedirs(path)
    else:
        os.mkdir(path)

def find_files(
    _dir: os.PathLike, prefix: str = "", suffix: str = "", 
    filter_func: Callable[[os.PathLike, str], bool] = None
) -> list[Path]:
    """功能简单的文件查找方法

    :param `__dir`       : 目录路径
    :param `prefix`      : 文件名前缀
    :param `suffix`      : 文件名后缀
    :param `filter_func` : 过滤函数, 原型: `(dirpath:os.PathLike, filename:str) -> bool`

    :return: 返回文件路径列表, 如果找不到某些文件可能是缺少目录权限.
    """
    result = []
    for dirpath, _, files in os.walk(_dir):
        for file in files:
            if prefix and not file.startswith(prefix):
                continue
            if suffix and not file.endswith(suffix):
                continue
            if filter_func and not filter_func(dirpath, file):
                continue
            result.append(Path(os.path.join(dirpath, file)))
    return result

def find_all_files_by_suffix(target_dir: os.PathLike, suffix: str):
    '''deprecated, use `find_files` insted'''
    return find_files(target_dir, suffix=suffix)

def import_from(module_dir:os.PathLike) -> dict[str, object]:
    '''
        从指定目录导入所有.py文件`__all__`列表中指定的对象, 以字典形式返回, 
        如果出现相同的导出符号会抛出异常.
    '''
    module_dir = Path(module_dir).absolute()
    py_files = find_files(
        module_dir, suffix='.py', filter_func=lambda _, f: f != '__init__.py'
    )
    _all = {}
    for file in py_files:
        module_name = file.parts[-1].split('.')[0]
        module_spec = importlib.util.spec_from_file_location(module_name, file)
        module = importlib.util.module_from_spec(module_spec)
        try:
            module_spec.loader.exec_module(module)
        except SystemExit:
            continue

        if not hasattr(module, '__all__'): continue
        for k in module.__all__:
            if k in _all:
                raise ImportError(f"Conflict name {k}")
            _all[k] = module.__dict__[k]
    return _all
