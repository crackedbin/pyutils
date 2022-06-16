
import os
import shutil

from . import PyUtilsException

__all__ = [
    "read_file", "write_file", "mkdir", "mvdir", "find_all_files_by_suffix",
    "delete_dir", "delete_file", 
	"PyUtilsFileSysException"
]

class PyUtilsFileSysException(PyUtilsException):
	'''PyUtilsFileSysException'''


def _open(file, mode):
	if not 'b' in mode:
		encoding = 'utf-8'
	else:
		encoding = None
	
	return open(file, mode, encoding=encoding)

def read_file(filepath, mode='r', lines:bool=False):
	with _open(filepath, mode) as fd:
		if not lines:
			content = fd.read()
		else:
			content = fd.readlines()
	return content

def write_file(filepath, content, mode='w', lines:bool=False):
	with _open(filepath, mode) as f:
		if not lines:
			f.write(content)
		else:
			f.writelines(content)

def delete_dir(dirpath):
	shutil.rmtree(dirpath, ignore_errors=True)

def delete_file(filepath):
	try:
		os.remove(filepath)
	except FileNotFoundError:
		pass

def mvdir(src, dst):
	shutil.move(src, dst)

def mkdir(path, parent=True):
	if os.path.exists(path): return
	try:
		if parent:
			os.makedirs(path)
		else:
			os.mkdir(path)
	except:
		pass

def find_all_files_by_suffix(target_dir:str, suffix:str):
    result = []
    for path, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(suffix):
                result.append(os.path.join(path, file))
    return result