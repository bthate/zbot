# ZBOT - 24/7 channel daemon
#
#

import atexit
import datetime
import os
import pwd
import readline
import sys
import termios
import time
import threading
import zbot.obj

from zbot.obj import Default, Object, cdir, fntime, last, save, update
from zbot.hdl import Cfg, Event, Kernel, get_kernel, launch, starttime

def __dir__():
    return ("Console", "execute", "elapsed", "parse", "parse_time", "parse_cli")

year_formats = [
    "%b %H:%M",
    "%b %H:%M:%S",
    "%a %H:%M %Y",
    "%a %H:%M",
    "%a %H:%M:%S",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d-%m",
    "%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m %H:%M:%S",
    "%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d-%m-%Y %H:%M",
    "%d-%m %H:%M",
    "%m-%d %H:%M",
    "%H:%M:%S",
    "%H:%M"
]

cmds = []
resume = {}

class Console(Object):

    def __init__(self):
        super().__init__()
        self.ready = threading.Event()

    def announce(self, txt):
        pass

    def input(self):
        k = get_kernel()
        while 1:
            try:
                event = self.poll()
            except EOFError:
                print("")
                continue
            event.orig = repr(self)
            k.queue.put(event)
            event.wait()

    def poll(self):
        e = Event()
        e.orig = repr(self)
        e.txt = input("> ")
        return e

    def raw(self, txt):
        print(txt.rstrip())

    def say(self, channel, txt):
        self.raw(txt)

    def start(self):
        k = get_kernel()
        setcompleter(k.cmds)
        launch(self.input)

class Token(Object):

    def __init__(self, txt):
        super().__init__()
        self.txt = txt

class Option(Default):

    def __init__(self, txt):
        super().__init__()
        if txt.startswith("--"):
            self.opt = txt[2:]
        if txt.startswith("-"):
            self.opt = txt[1:]

class Getter(Object):

    def __init__(self, txt):
        super().__init__()
        try:
            pre, post = txt.split("==")
        except ValueError:
            pre = post = ""
        if pre:
            self[pre] = post

class Setter(Object):

    def __init__(self, txt):
        super().__init__()
        try:
            pre, post = txt.split("=")
        except ValueError:
            pre = post = ""
        if pre:
            self[pre] = post


class Skip(Object):

    def __init__(self, txt):
        super().__init__()
        pre = ""
        if txt.endswith("-"):
            try:
                pre, _post = txt.split("=")
            except ValueError:
                try:
                    pre, _post = txt.split("==")
                except ValueError:
                    pre = txt
        if pre:
            self[pre] = True

class Timed(Object):

    def __init__(self, txt):
        super().__init__()
        v = 0
        vv = 0
        try:
            pre, post = txt.split("-")
            v = parse_time(pre)
            vv = parse_time(post)
        except ValueError:
            pass
        if not v or not vv:
            try:
                vv = parse_time(txt)
            except ValueError:
                vv = 0
            v = 0
        if v:
            self["from"] = time.time() - v
        if vv:
            self["to"] = time.time() - vv


def complete(text, state):
    matches = []
    if text:
        matches = [s for s in cmds if s and s.startswith(text)]
    else:
        matches = cmds[:]
    try:
        return matches[state]
    except IndexError:
        return None

def execute(main):
    termsave()
    try:
        main()
    except KeyboardInterrupt:
        print("")
    except PermissionError:
        print("you need root permissions.")
    finally:
        termreset()

def get_completer():
    return readline.get_completer()

def boot(name, wd=""):
    k = get_kernel()
    parsed = Default()
    parse(k.cfg, " ".join(sys.argv[1:]))
    zbot.obj.workdir = wd or os.path.expanduser("~/.%s" % name)
    cdir(zbot.obj.workdir)
    return k

def root():
    if os.geteuid() != 0:
        return False
    return True

def privileges(name):
    if os.getuid() != 0:
        return
    pwnam = pwd.getpwnam(name)
    os.setgroups([])
    os.setgid(pwnam.pw_gid)
    os.setuid(pwnam.pw_uid)
    old_umask = os.umask(0o22)

def setcompleter(commands):
    cmds.extend(commands)
    readline.set_completer(complete)
    readline.parse_and_bind("tab: complete")
    atexit.register(lambda: readline.set_completer(None))

def termsetup(fd):
    return termios.tcgetattr(fd)

def termreset():
    if "old" in resume:
        termios.tcsetattr(resume["fd"], termios.TCSADRAIN, resume["old"])

def termsave():
    try:
        resume["fd"] = sys.stdin.fileno()
        resume["old"] = termsetup(sys.stdin.fileno())
        atexit.register(termreset)
    except termios.error:
        pass

def touch(fname):
    try:
        fd = os.open(fname, os.O_RDWR | os.O_CREAT)
        os.close(fd)
    except (IsADirectoryError, TypeError):
        pass

def day():
    return str(datetime.datetime.today()).split()[0]

def days(path):
    return elapsed(time.time() - fntime(path))

def elapsed(seconds, short=True):
    txt = ""
    nsec = float(seconds)
    year = 365*24*60*60
    week = 7*24*60*60
    nday = 24*60*60
    hour = 60*60
    minute = 60
    years = int(nsec/year)
    nsec -= years*year
    weeks = int(nsec/week)
    nsec -= weeks*week
    nrdays = int(nsec/nday)
    nsec -= nrdays*nday
    hours = int(nsec/hour)
    nsec -= hours*hour
    minutes = int(nsec/minute)
    sec = nsec - minutes*minute
    if years:
        txt += "%sy" % years
    if weeks:
        nrdays += weeks * 7
    if nrdays:
        txt += "%sd" % nrdays
    if years and short and txt:
        return txt
    if hours:
        txt += "%sh" % hours
    if nrdays and short and txt:
        return txt
    if minutes:
        txt += "%sm" % minutes
    if hours and short and txt:
        return txt
    if sec == 0:
        txt += "0s"
    #elif sec < 1 or not short:
    #    txt += "%.3fs" % sec
    else:
        txt += "%ss" % int(sec)
    txt = txt.strip()
    return txt

def get_time(daystr):
    for f in year_formats:
        try:
            t = time.mktime(time.strptime(daystr, f))
            return t
        except ValueError:
            pass

def parse_time(daystr):
    if not any([c.isdigit() for c in daystr]):
        return 0
    valstr = ""
    val = 0
    total = 0
    for c in daystr:
        try:
            vv = int(valstr)
        except ValueError:
            vv = 0
        if c == "y":
            val = vv * 3600*24*365
        if c == "w":
            val = vv * 3600*24*7
        elif c == "d":
            val = vv * 3600*24
        elif c == "h":
            val = vv * 3600
        elif c == "m":
            val = vv * 60
        else:
            valstr += c
        total += val
    return total

def today():
    return datetime.datetime.today().timestamp()

def to_day(daystring):
    line = ""
    daystr = str(daystring)
    for word in daystr.split():
        if "-" in word:
            line += word + " "
        elif ":" in word:
            line += word
    if "-" not in line:
        line = day() + " " + line
    try:
        return get_time(line.strip())
    except ValueError:
        pass

def parse(o, txt):
    args = []
    o.origtxt = txt
    o.gets = Object()
    o.opts = Object()
    o.sets = Object()
    o.skip = Object()
    o.timed = Object()
    o.index = None
    for token in [Token(txt) for txt in txt.split()]:
        s = Skip(token.txt)
        if s:
            update(o.skip, s)
            token.txt = token.txt[:-1]
        t = Timed(token.txt)
        if t:
            update(o.timed, t)
            continue
        g = Getter(token.txt)
        if g:
            update(o.gets, g)
            continue
        s = Setter(token.txt)
        if s:
            update(o.sets, s)
            update(o, s)
            continue
        opt = Option(token.txt)
        if opt.opt:
            try:
                o.index = int(opt.opt)
                continue
            except ValueError:
                pass
            o.opts[opt.opt] = True
            continue
        args.append(token.txt)
    if not args:
        o.args = []
        o.cmd = ""
        o.rest = ""
        o.txt = ""
        return o
    o.cmd = args[0]
    o.args = args[1:]
    o.txt = " ".join(args)
    o.rest = " ".join(args[1:])
    return o
