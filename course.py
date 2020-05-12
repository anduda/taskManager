#!/usr/bin/env python3
"Course work"
import os
import curses
import locale
import subprocess
from enum import Enum

HK_PROCESSES = "m"
HK_PAUSE = "p"
HK_HELPER = "?"
HK_SEARCH = "/"
HK_LEFT = "h"
HK_DOWN = "j"
HK_UP = "k"
HK_RIGHT = "l"
HK_END = "J"
HK_HOME = "K"
HK_SORT = "s"
HK_INVSORT = "b"
HK_KILL = "x"
HK_QUIT = "q"

KILLER = 'kill -s {} {}'
COMMAND = 'ps axc -o cmd,user,pid,ppid,pri,ni,stat,rss,%cpu,%mem --sort={}'
ARGS = {
    "command": "cmd",
    "user": "user",
    "pid": "pid",
    "ppid": "ppid",
    "priority": "pri",
    "niceness": "ni",
    "status": "stat",
    "ram": "rss",
    "ram%": "%mem",
    "cpu": "%cpu",
    "time": "time"
}
SORTER = ARGS["pid"]

PANEL_WINDOW_WIDTH = 0.3

SORT_HELPER = ("Sort arguments:\n" + "\n".join(
    [f"{str(i+1)}. {arg}" for i, arg in enumerate(ARGS.keys())]))

KILLER_HELP = """System signals:
Cancel   0
SIGHUP   1
SIGINT   2
SIGQUIT  3
SIGILL   4
SIGABRT  6
SIGFPE   8
SIGKILL  9
SIGSEGV 11
SIGPIPE 13
SIGALRM 14
SIGTERM 15
"""
SIGNALS = [1, 2, 3, 4, 6, 8, 9, 11, 13, 14, 15]

HELP_MESSAGE = """>>> Process manager <<<
<p> - pause/start update
<m> - show/update info
<?> - about
<k> - up
<j> - down
<h> - left
<l> - right
<K> - home
<J> - end
<s> - sort
<b> - inverse sort
<x> - send signal
<q> - quit

""" + SORT_HELPER + "\n\n" + KILLER_HELP

HELPER_PAGE = r""" ____
Course work by Stashkevich Andrei
BSUIR student, group 753504
"""


class Mode(Enum):
    processes = HK_PROCESSES
    helper = HK_HELPER


class CustomWin:
    def __init__(self, height, width, highlight_color, header_color):
        self.height = height
        self.width = width

        self.highlight_color = highlight_color
        self.header_color = header_color

        self.header = ""
        self.lines = []

        self.x_shift = 0
        self.y_shift = 0
        self.choosen_line = 0

        self.window = curses.newwin(height, width)

    def reset_content(self, header, lines):
        self.header = header
        self.lines = lines

    def resize(self, height, width):
        self.height = height
        self.width = width
        self.window.resize(height, width)

    def draw(self):
        if len(self.lines) and (self.choosen_line >= len(self.lines)):
            self.shift_end()

        self.window.border(0)
        self.window.addstr(
            1, 1, self.header[self.x_shift:self.x_shift+self.width-2],
            self.header_color)

        cutout = [line[self.x_shift:self.x_shift+self.width-2] for line in
                  self.lines[self.y_shift:self.y_shift+self.height-3]]
        for i, line in enumerate(cutout):
            if i == self.choosen_line-self.y_shift:
                self.window.addstr(i+2, 1, line, self.highlight_color)
            else:
                self.window.addstr(i+2, 1, line)

    def clear(self):
        self.window.clear()

    def refresh(self):
        self.window.refresh()

    def shift_x(self, direction=True):
        if not direction and self.x_shift > 0:
            self.x_shift -= 1
        elif direction and self.x_shift+self.width-2 < len(self.lines[0]):
            self.x_shift += 1

    def shift_y(self, direction=True):
        if not direction and self.choosen_line > 0:
            self.choosen_line -= 1
        elif direction and self.choosen_line < len(self.lines)-1:
            self.choosen_line += 1

        if self.choosen_line < self.y_shift:
            self.y_shift -= 1
        elif self.choosen_line == self.y_shift+self.height-3:
            self.y_shift += 1

    def shift_home(self):
        self.y_shift = 0
        self.choosen_line = 0

    def shift_end(self):
        self.choosen_line = len(self.lines)-1
        self.y_shift = self.choosen_line-self.height+4

    def get_size(self):
        return self.window.getmaxyx()

    def change_choosen_line(self, i):
        self.choosen_line = i
        self.y_shift = i


def get_processes():
    return subprocess.run(
        COMMAND.format(SORTER).split(' '), stdout=subprocess.PIPE
    ).stdout.decode(
            locale.getpreferredencoding())[:-1]


def initialize_boxes(stdscr, highlight, header):
    height, width = stdscr.getmaxyx()
    panel_width = int(width*PANEL_WINDOW_WIDTH)
    processes_width = width - panel_width
    procwin = CustomWin(height, processes_width, highlight, header)
    panelbox = curses.newwin(height, panel_width, 0, processes_width)
    return procwin, panelbox


def clean_boxes(stdscr, procwin, panelbox):
    stdscr.clear()
    panelbox.clear()
    procwin.clear()


def resize_boxes(stdscr, procwin):
    height, width = stdscr.getmaxyx()
    panel_width = int(width*PANEL_WINDOW_WIDTH)
    processes_width = width - panel_width
    procwin.resize(height, processes_width)
    panelbox = curses.newwin(height, panel_width, 0, processes_width)
    clean_boxes(stdscr, procwin, panelbox)
    return panelbox


def change_sort(panelbox):
    global SORTER

    curses.echo()
    message = "Input\n> "
    incorrect = "Incorrect input. Try again\n> "
    while True:
        panelbox.addstr(0, 0, message)
        panelbox.addstr(2, 0, SORT_HELPER + "\nLeave empty to return\n")
        arg = panelbox.getstr(1, 2, 10).decode(locale.getpreferredencoding())
        if arg in ARGS.keys():
            SORTER = ARGS[arg]
            break
        elif arg != "":
            message = incorrect
        else:
            break
    curses.noecho()

def inverse_sort():
    global SORTER

    if SORTER[0] == "-":
        SORTER = SORTER[1:]
    else:
        SORTER = "-" + SORTER


def killer_signal(panelbox, pid):
    curses.echo()
    message = "Input\n> "
    incorrect = "Incorrect input. Try again\n> "
    while True:
        panelbox.addstr(0, 0, message)
        panelbox.addstr(2, 0, KILLER_HELP)
        arg = int(panelbox.getstr(
            1, 2, 2).decode(locale.getpreferredencoding()))
        if arg in SIGNALS:
            os.system(KILLER.format(arg, pid))
            break
        elif arg != 0:
            message = incorrect
        else:
            break
    curses.noecho()


def search_process(panelbox, names):
    curses.echo()
    message = "Input\n> "
    panelbox.addstr(0, 0, message)
    term = panelbox.getstr(1, 2, 10).decode(locale.getpreferredencoding())
    for i, line in enumerate(names):
        if term in line:
            curses.noecho()
            return i

    curses.noecho()
    return -1


def update_processes(procwin):
    header, *processes = get_processes().split('\n')
    procwin.reset_content(header, processes)


def main(stdscr):
    mode = Mode.processes
    is_updating = True
    key = ord(HK_PROCESSES)

    procwin, panelbox = initialize_boxes(
        stdscr, curses.color_pair(1), curses.color_pair(2))

    while True:
        clean_boxes(stdscr, procwin, panelbox)
        if is_updating:
            update_processes(procwin)

        if key == ord(HK_QUIT) or key == 27:
            break
        elif key == curses.KEY_RESIZE:
            panelbox = resize_boxes(stdscr, procwin)
        elif key == ord(HK_PROCESSES):
            mode = Mode.processes
            if not is_updating:
                update_processes(procwin)
        elif key == ord(HK_HELPER):
            mode = Mode.helper
        elif key == ord(HK_LEFT) or key == curses.KEY_LEFT:
            procwin.shift_x(False)
        elif key == ord(HK_RIGHT) or key == curses.KEY_RIGHT:
            procwin.shift_x()
        elif key == ord(HK_UP) or key == curses.KEY_UP:
            procwin.shift_y(False)
        elif key == ord(HK_DOWN) or key == curses.KEY_DOWN:
            procwin.shift_y()
        elif key == ord(HK_END) or key == curses.KEY_END:
            procwin.shift_end()
        elif key == ord(HK_HOME) or key == curses.KEY_HOME:
            procwin.shift_home()
        elif key == ord(HK_SORT):
            change_sort(panelbox)
            update_processes(procwin)
        elif key == ord(HK_INVSORT):
            inverse_sort()
            update_processes(procwin)
        elif key == ord(HK_KILL):
            splits = procwin.lines[procwin.choosen_line].split(' ')
            splits = list(filter(None, splits))
            pid = splits[2]
            killer_signal(panelbox, pid)
        elif key == ord(HK_SEARCH):
            names = [line.split(' ')[0] for line in procwin.lines]
            line = search_process(panelbox, names)
            if line != -1:
                procwin.change_choosen_line(line)
        elif key == ord(HK_PAUSE):
            is_updating = not is_updating

        if mode == Mode.processes:
            procwin.draw()
            #  panelbox.addstr(0, 0, HELP_MESSAGE)
            height, _ = panelbox.getmaxyx()
            for i, line in enumerate(HELP_MESSAGE.split("\n")):
                if i < height:
                    panelbox.addstr(i, 0, line)
                else:
                    break
            stdscr.refresh()
            panelbox.refresh()
            procwin.refresh()
        elif mode == Mode.helper:
            stdscr.clear()
            stdscr.border(0)
            height, _ = stdscr.getmaxyx()
            for i, line in enumerate(HELPER_PAGE.split("\n")):
                if i < height-2:
                    stdscr.addstr(i+1, 1, line)
                else:
                    break
            stdscr.refresh()
        key = stdscr.getch()


if __name__ == '__main__':
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        curses.curs_set(0)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)

        main(stdscr)
    finally:
        curses.curs_set(1)
        stdscr.keypad(False)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        exit()
