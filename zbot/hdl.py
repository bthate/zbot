# ZBOT - 24/7 channel daemon
#
#

__version__ = 59

import importlib
import importlib.util
import inspect
import os
import pkgutil
import queue
import sys
import time
import threading
import traceback
import zipfile
import _thread
import zbot.obj

from zbot.obj import Cfg, Default, Object, Ol, cdir, get, get_name, last, locked, save, update

def __dir__():
    return ("Cfg", "Event", "Kernel", "direct", "get_exception", "get_kernel", "launch", "starttime")

dispatchlock = _thread.allocate_lock()
starttime = time.time()

class Bus(Object):

    objs = []

    def __iter__(self):
        return iter(Bus.objs)

    def add(self, obj):
        Bus.objs.append(obj)

    def announce(self, txt, skip=None):
        for h in self.objs:
            if skip is not None and isinstance(h, skip):
                continue
            if "announce" in dir(h):
                h.announce(txt)

    def dispatch(self, event):
        for b in Bus.objs:
            if repr(b) == event.orig:
                b.dispatch(event)

    def by_orig(self, orig):
        for o in Bus.objs:
            if repr(o) == orig:
                return o

    def say(self, orig, channel, txt):
        for o in Bus.objs:
            if repr(o) == orig:
                o.say(channel, str(txt))

class Cfg(Cfg):

    pass

class Event(Default):

    def __init__(self):
        super().__init__()
        self.args = []
        self.cmd = ""
        self.ready = threading.Event()
        self.rest = ""
        self.result = []
        self.thrs = []
        self.txt = ""

    def parse(self):
        args = self.txt.split()
        if args:
            self.cmd = args[0]
        if len(args) >= 2:
            self.args = args[1:]
            self.rest = " ".join(args[1:])

    def reply(self, txt):
        if not self.result:
            self.result = []
        self.result.append(txt)

    def show(self):
        for txt in self.result:
            try:
                print(txt)
            except:
               pass

    def wait(self):
        self.ready.wait()
        res = []
        for thr in self.thrs:
            res.append(thr.join())
        return res

class Handler(Object):

    def __init__(self):
        super().__init__()
        self.cmds = Object()
        self.packages = []
        self.queue = queue.Queue()
        self.stopped = False

    def cmd(self, txt):
        from zbot.csl import parse
        e = Event()
        e.txt = self.cfg.origtxt
        parse(e, e.txt)
        self.dispatch(e)
        return e

    @locked(dispatchlock)
    def dispatch(self, e):
        e.parse()
        if e.cmd in self.cmds:
            try:
                self.cmds[e.cmd](e)
            except Exception as ex:
                print(get_exception())
        e.show()
        e.ready.set()

    def handler(self):
        while not self.stopped:
            event = self.queue.get()
            if not event:
                break
            if not event.orig:
                event.orig = repr(self)
            if event.txt:
                launch(self.dispatch, event, name=event.txt.split()[0])
            else:
                event.ready.set()

    def load_mod(self, name):
        mod = direct(name)
        self.scan(mod)
        return mod

    def scan(self, mod):
        cmds = find_cmds(mod)
        update(self.cmds, cmds)

    def start(self):
        launch(self.handler)

    def stop(self):
        self.stopped = True
        self.queue.put(None)

    def walk(self, names, ignore=""):
        modules = []
        for name in names.split(","):
            if name in ignore.split(","):
                continue
            spec = importlib.util.find_spec(name)
            if not spec:
                continue
            pkg = importlib.util.module_from_spec(spec)
            pn = getattr(pkg, "__path__", None)
            if not pn:
                continue
            for mi in pkgutil.iter_modules(pn):
                mn = "%s.%s" % (name, mi.name)
                module = self.load_mod(mn)
                modules.append(module)
            self.packages.append(name)
        return modules

class Kernel(Handler):

    def __init__(self):
        super().__init__()
        self.ready = threading.Event()
        self.stopped = False
        self.cfg = Cfg()
        kernels.append(self)

    def announce(self, txt):
        pass

    def init(self, mns):
        mods = []
        thrs = []
        for mn in spl(mns):
            ms = ""
            for pn in self.packages:
                n = "%s.%s" % (pn, mn)
                spec = importlib.util.find_spec(n)
                if spec:
                    ms = n
                    break
            if not ms:
                continue
            try:
                mod = self.load_mod(ms)
            except (ModuleNotFoundError, ValueError):
                try:
                    mod = self.load_mod(mn)
                except (ModuleNotFoundError, ValueError) as ex:
                    if mn in str(ex):
                        continue
                    print(get_exception())
                    continue
            mods.append(mod)
            func = getattr(mod, "init", None)
            if func:
                thrs.append(launch(func, self, name=get_name(func)))
        for thr in thrs:
            thr.join()
        return mods

    def scandir(self, path):
        mods = []
        cdir(path + os.sep + "")
        for fn in os.listdir(path):
            if fn.startswith("_") or not fn.endswith(".py"):
                continue
            mn = "mods.%s" % fn[:-3]
            try:
                module = self.load_mod(mn)
            except Exception as ex:
                print(get_exception())
                continue
            mods.append(module)
        return mods

    def say(self, channel, txt):
        print(txt)

    def start(self):
        assert zbot.obj.workdir
        self.init(self.cfg.mods)
        super().start()

    def stop(self):
        self.stopped = True
        self.queue.put(None)

    def wait(self):
        while not self.stopped:
            time.sleep(60.0)

class Task(threading.Thread):

    def __init__(self, func, *args, name="noname", daemon=True):
        super().__init__(None, self.run, name, (), {}, daemon=daemon)
        self._name = name
        self._result = None
        self._queue = queue.Queue()
        self._queue.put((func, args))
        self.sleep = 0
        self.state = Object()

    def __iter__(self):
        return self

    def __next__(self):
        for k in dir(self):
            yield k

    def run(self):
        func, args = self._queue.get()
        self.setName(self._name)
        try:
            self._result = func(*args)
        except EOFError:
            _thread.interrupt_main()
        except Exception as _ex:
            print(get_exception())

    def join(self, timeout=None):
        super().join(timeout)
        return self._result

class Timer(Object):

    def __init__(self, sleep, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.sleep = sleep
        self.args = args
        self.name = kwargs.get("name", "")
        self.kwargs = kwargs
        self.state = Object()
        self.timer = None

    def run(self, *args, **kwargs):
        self.state.latest = time.time()
        launch(self.func, *self.args, **self.kwargs)

    def start(self):
        if not self.name:
            self.name = get_name(self.func)
        timer = threading.Timer(self.sleep, self.run, self.args, self.kwargs)
        timer.setName(self.name)
        timer.setDaemon(True)
        timer.sleep = self.sleep
        timer.state = self.state
        timer.state.starttime = time.time()
        timer.state.latest = time.time()
        timer.func = self.func
        timer.start()
        self.timer = timer
        return timer

    def stop(self):
        if self.timer:
            self.timer.cancel()

class Repeater(Timer):

    def run(self, *args, **kwargs):
        thr = launch(self.start, **kwargs)
        super().run(*args, **kwargs)
        return thr

bus = Bus()
kernels = []

def direct(name):
    return importlib.import_module(name)

def find_cmds(mod):
    cmds = {}
    for key, o in inspect.getmembers(mod, inspect.isfunction):
        if "event" in o.__code__.co_varnames:
            if o.__code__.co_argcount == 1:
                cmds[key] = o
    return cmds

def find_modules(pkgs, skip=None):
    modules = []
    for pkg in pkgs.split(","):
        if skip is not None and skip not in pkg:
            continue
        try:
            p = direct(pkg)
        except ModuleNotFoundError:
            continue
        for _key, m in inspect.getmembers(p, inspect.ismodule):
            if m not in modules:
                modules.append(m)
    return modules

def find_shorts(mn):
    shorts = Ol()
    for mod in find_modules(mn):
        for _key, o in inspect.getmembers(mod, inspect.isclass):
            if issubclass(o, Object):
                t = "%s.%s" % (o.__module__, o.__name__)
                shorts.append(o.__name__.lower(), t)
    return shorts

def get_exception(txt="", sep=" "):
    exctype, excvalue, tb = sys.exc_info()
    trace = traceback.extract_tb(tb)
    result = []
    for elem in trace:
        if elem[0].endswith(".py"):
            plugfile = elem[0][:-3].split(os.sep)
        else:
            plugfile = elem[0].split(os.sep)
        mod = []
        for element in plugfile[::-1]:
            mod.append(element)
            if "oq" in element:
                break
        ownname = ".".join(mod[::-1])
        result.append("%s:%s" % (ownname, elem[1]))
    res = "%s %s: %s %s" % (sep.join(result), exctype, excvalue, str(txt))
    del trace
    return res

def get_kernel():
    if kernels:
        return kernels[0]
    return Kernel()
       
def launch(func, *args, **kwargs):
    name = kwargs.get("name", get_name(func))
    t = Task(func, *args, name=name, daemon=True)
    t.start()
    return t

def list_files(wd):
    path = os.path.join(wd, "store")
    if not os.path.exists(path):
        return ""
    return "|".join(os.listdir(path))

def spl(txt):
    return iter([x for x in txt.split(",") if x])
