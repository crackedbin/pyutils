import os
import signal
import subprocess

__all__ = [
    'kill_process', 'async_execute'
]

def kill_process(pid):
    os.kill(pid, signal.SIGTERM)

def async_execute(args:list, env:dict=None) -> subprocess.Popen:
    '''
        subprocess.Popen wrapper.

        https://docs.python.org/3.8/whatsnew/3.8.html#optimizations
    '''
    current_env = os.environ.copy()
    if env: current_env.update(env)
    process = subprocess.Popen(
        args=args, 
        stderr=subprocess.STDOUT, stdout=subprocess.PIPE, 
        env=current_env, 
        close_fds=False
    )
    return process
