
import os
import sys
import time

from pyutils.misc import TerminalCursor

__all__ = [
    'ProgressBar'
]

class ProgressBar:

    SPEED_INFO_FORMAT = "[{spend_time:.02f}<{left_time:.02f}, {speed:.02f}it/s]"
    BAR_INFO_FORMAT = "[{desc} {percent} ]"
    PROGRESS_FORMAT = "|{bar}| {count}/{limit}"
    DISPLAY_FORMAT = f"{BAR_INFO_FORMAT} {PROGRESS_FORMAT} {SPEED_INFO_FORMAT}"

    def __init__(
        self, count:int, description:str='', progress_char:str='█',
        reserved_char:str=' '
    ):
        self.__max_count = count
        self.__cur_count = 0
        self.__description = description
        self.__progress_char = progress_char
        self.__reserved_char = reserved_char
        self.__columns = int(os.get_terminal_size().columns * 0.5)
        self.__init_time = time.time()

    def __iter__(self):
        return self
    
    def __next__(self):
        count = self.update()
        if self.__cur_count > self.__max_count:
            print('')
            raise StopIteration
        return count

    def update(self):
        count = self.__cur_count
        progress_rate = self.__cur_count / self.__max_count
        percentage = int(progress_rate * 100)
        progress_count = int(self.__columns * progress_rate)
        reserved_count = self.__columns - progress_count
        progress_bar = f"{progress_count*self.__progress_char}{reserved_count*self.__reserved_char}"
        cur_time = time.time()
        spend_time = cur_time - self.__init_time
        speed = count / spend_time
        predicted_total_time = self.__max_count / speed if speed else 0
        left_time = predicted_total_time - spend_time if predicted_total_time else 0
        
        TerminalCursor.left_end()
        TerminalCursor.clear_line()

        line = ProgressBar.DISPLAY_FORMAT.format(
            # bar info
            desc=self.__description, percent=f"{percentage}%",
            # progress bar
            bar=progress_bar, count=count, limit=self.__max_count,
            # speed info
            spend_time=spend_time, left_time=left_time, speed=speed
        )
        print(line, end='')
        sys.stdout.flush()
        self.__cur_count += 1
        return count
