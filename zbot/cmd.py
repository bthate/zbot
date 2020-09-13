# ZBOT - 24/7 channel daemon.
#
#

import time
import threading

from zbot.obj import Object, get, get_type, update
from zbot.csl import elapsed, starttime
from zbot.hdl import get_kernel, find_modules

def __dir__():
    return ("cmd", "krn", "mds", "tsk", "ver", "wd")

k = get_kernel()

def cmd(event):
    event.reply(",".join(sorted(k.cmds)))

def mds(event):
    event.reply(",".join([m.__name__.split(".")[-1] for m in find_modules("madbot")]))

def tsk(event):
    psformat = "%-8s %-50s"
    result = []
    for thr in sorted(threading.enumerate(), key=lambda x: x.getName()):
        if str(thr).startswith("<_"):
            continue
        d = vars(thr)
        o = Object()
        update(o, d)
        if get(o, "sleep", None):
            up = o.sleep - int(time.time() - o.state.latest)
        else:
            up = int(time.time() - starttime)
        result.append((up, thr.getName(), o))
    nr = -1
    for up, thrname, o in sorted(result, key=lambda x: x[0]):
        nr += 1
        res = "%s %s" % (nr, psformat % (elapsed(up), thrname[:60]))
        if res:
            event.reply(res.rstrip())

def ver(event):
    for mod in k.walk("zbot"):
        try:
            event.reply("%s %s" % (mod.__name__, mod.__version__))
        except AttributeError:
            continue
