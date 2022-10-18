import os
import shutil

from typing import Callable

__all__ = [
    "read_file",
    "write_file",
    "mkdir",
    "mvdir",
    "find_all_files_by_suffix",
    "delete_dir",
    "delete_file",
    "find_files"
]


def _open(filepath:os.PathLike, mode:str, encoding:str='utf-8'):
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

def delete_dir(dirpath):
    shutil.rmtree(dirpath, ignore_errors=True)

def delete_file(filepath):
    if not os.path.exists(filepath):
        return
    os.remove(filepath)

def mvdir(src, dst):
    shutil.move(src, dst)

def mkdir(path, parent=True):
    if os.path.exists(path):
        return
    if parent:
        os.makedirs(path)
    else:
        os.mkdir(path)

def find_files(
    __dir: str, prefix: str = "", suffix: str = "", filter_func: Callable = None
) -> list[str]:
    """功能简单的文件查找方法

    :param `__dir`       : 目录路径
    :param `prefix`      : 文件名前缀
    :param `suffix`      : 文件名后缀
    :param `filter_func` : 过滤函数, 原型: `(dirpath:str, filename:str) -> bool`

    :return: 返回文件路径列表, 如果找不到某些文件可能是缺少目录权限.
    """
    result = []
    for dirpath, _, files in os.walk(__dir):
        for file in files:
            if prefix and not file.startswith(prefix):
                continue
            if suffix and not file.endswith(suffix):
                continue
            if filter_func and not filter_func(dirpath, file):
                continue
            result.append(os.path.join(dirpath, file))
    return result

def find_all_files_by_suffix(target_dir: str, suffix: str):
    '''deprecated, use `find_files` insted'''
    return find_files(target_dir, suffix=suffix)
