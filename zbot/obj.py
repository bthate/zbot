# OQ - write your own commands.
#
# object library (obj)

"provides json file backend object load/save persitence. uses read only versioned objects."

import datetime, importlib, inspect, json, os, random, sys, time, types, uuid, _thread

def __dir__():
    return ("ENOCLASS", "ENOFILENAME", "Object", "Ol", "Cfg", "Db", "Default", "edit",
            "all", "deleted", "find", "lasttype", "lastfn", "os", "format", "get_type", "get",
            "items", "keys", "last", "load", "register", "save", "search", "sys", "values", "update")

savelock = _thread.allocate_lock()
workdir = ""

class ENOCLASS(Exception):
    "no class found"

class ENOFILENAME(Exception):
    "argument is no filename"

class Object:

    "pure clean namespace object (no methods)."

    __slots__ = ("__dict__", "__stamp__")

    def __init__(self):
        timestamp = str(datetime.datetime.now()).split()
        self.__stamp__ = os.path.join(get_type(self), str(uuid.uuid4()), os.sep.join(timestamp))

    def __delitem__(self, k):
        del self.__dict__[k]

    def __getitem__(self, k, d=None):
        return self.__dict__.get(k, d)

    def __iter__(self):
        return iter(self.__dict__.keys())

    def __len__(self):
        return len(self.__dict__)

    def __lt__(self, o):
        return len(self) < len(o)

    def __setitem__(self, k, v):
        self.__dict__[k] = v
        return self.__dict__[k]

    def __str__(self):
        return json.dumps(self, default=default, indent=4, sort_keys=True)

class Ol(Object):

    "list of objects."

    def append(self, key, value):
        "add an value to the list at key."
        if key not in self:
            self[key] = []
        if isinstance(value, type(list)):
            self[key].extend(value)
        else:
            if value not in self[key]:
                self[key].append(value)

    def update(self, d):
        "d is a dictinary to update the corresponding lists with."
        for k, v in d.items():
            self.append(k, v)

class Default(Object):

    "provide default string value."

    def __getattr__(self, k):
        if k not in self:
            return ""
        return self.__dict__[k]

class Cfg(Default):

    "default config."

def all(otype, selector=None, index=None, timed=None):
    "otype is the module.class, selector is key/value, index is into that result, timed is with 'from' and 'to' items."
    nr = -1
    if selector is None:
        selector = {}
    for fn in objs(otype, timed):
        o = hook(fn)
        if selector and not search(o, selector):
            continue
        if "_deleted" in o and o._deleted:
            continue
        nr += 1
        if index is not None and nr != index:
            continue
        yield o


def cdir(path):
    "create a directory or nop if it already exists."
    if os.path.exists(path):
        return
    res = ""
    path2, _fn = os.path.split(path)
    for p in path2.split(os.sep):
        res += "%s%s" % (p, os.sep)
        padje = os.path.abspath(os.path.normpath(res))
        try:
            os.mkdir(padje)
            os.chmod(padje, 0o700)
        except (IsADirectoryError, NotADirectoryError, FileExistsError):
            pass

def default(o):
    "return jsonable string of object"
    if isinstance(o, Object):
        return vars(o)
    if isinstance(o, dict):
        return o.items()
    if isinstance(o, list):
        return iter(o)
    if isinstance(o, (type(str), type(True), type(False), type(int), type(float))):
        return o
    return repr(o)

def deleted(otype):
    "otype is the object type to show the deleted versions of."
    for fn in objs(otype):
        o = hook(fn)
        if "_deleted" not in o or not o._deleted:
            continue
        yield o

def edit(o, setter, skip=False):
    "setters is a dictionary with key,values to edit."
    try:
        setter = vars(setter)
    except (TypeError, ValueError):
        pass
    if not setter:
        setter = {}
    count = 0
    for key, value in setter.items():
        if skip and value == "":
            continue
        count += 1
        if value in ["True", "true"]:
            o[key] = True
        elif value in ["False", "false"]:
            o[key] = False
        else:
            o[key] = value
    return count

def fntime(daystr):
    "return timestamp derived from the filename."
    daystr = daystr.replace("_", ":")
    datestr = " ".join(daystr.split(os.sep)[-2:])
    try:
        datestr, rest = datestr.rsplit(".", 1)
    except ValueError:
        rest = ""
    try:
        t = time.mktime(time.strptime(datestr, "%Y-%m-%d %H:%M:%S"))
        if rest:
            t += float("." + rest)
    except ValueError:
        t = 0
    return t

def find(otype, selector=None, index=None, timed=None):
    "otype is the module.class, selector is key/value, index is into that result, timed is with 'from' and 'to' items."
    nr = -1
    if selector is None:
        selector = {}
    for fn in objs(otype, timed):
        o = hook(fn)
        if selector and not search(o, selector):
            continue
        if "_deleted" in o and o._deleted:
            continue
        nr += 1
        if index is not None and nr != index:
            continue
        yield o

def find_event(e):
    "find objects based on event data."
    nr = -1
    for fn in objs(e.otype, e.timed):
        o = hook(fn)
        if e.gets and not search(o, e.gets):
            continue
        if "_deleted" in o and o._deleted:
            continue
        nr += 1
        if e.index is not None and nr != e.index:
            continue
        yield o

def format(o, keylist=None, pure=False, skip=None):
    "keys is list of keys to display, pure is with or without parameter names, skip skips value."
    if not keylist:
        keylist = vars(o).keys()
    res = []
    txt = ""
    for key in keylist:
        if skip and key in skip:
            continue
        if key == "stamp":
            continue
        try:
            val = o[key]
        except KeyError:
            continue
        if not val:
            continue
        val = str(val).strip()
        val = val.replace("\n", "")
        res.append((key, val))
    for k, v in res:
        if pure:
            txt += "%s%s" % (v, " ")
        else:
            txt += "%s=%s%s" % (k, v, " ")
    return txt.strip()

def get(o, k, d=None):
    "k is ket to get, d is default."
    try:
        res = o.get(k, d)
    except (TypeError, AttributeError):
        res = o.__dict__.get(k, d)
    return res

def get_cls(name):
    "name is the module.class name (qualified name) of the to be constructed object."
    try:
        modname, clsname = name.rsplit(".", 1)
    except:
        raise ENOCLASS(name)
    if modname in sys.modules:
        mod = sys.modules[modname]
    else:
        mod = importlib.import_module(modname)
    return getattr(mod, clsname)

def get_name(o):
    "o is object to get name from."
    t = type(o)
    if t == types.ModuleType:
        return o.__name__
    try:
        n = "%s.%s" % (o.__self__.__class__.__name__, o.__name__)
    except AttributeError:
        try:
            n = "%s.%s" % (o.__class__.__name__, o.__name__)
        except AttributeError:
            try:
                n = o.__class__.__name__
            except AttributeError:
                n = o.__name__
    return n

def get_type(o):
    "return the qualified modulename.Classname name of an object."
    t = type(o)
    if t == type:
        try:
            return "%s.%s" % (o.__module__, o.__name__)
        except AttributeError:
            pass
    return str(type(o)).split()[-1][1:-2]

def hook(fn):
    "reconstruct the object with proper class derived from the filename."
    if fn.count(os.sep) > 3:
        oname = fn.split(os.sep)[-4:]
    else:
        oname = fn.split(os.sep)
    t = oname[0]
    if not t:
        raise ENOFILENAME(fn)
    o = get_cls(t)()
    load(o, fn)
    return o

def hooked(d):
    "d is a dictionary that uses the stamp value to reconstruct the corresponding class."
    if "stamp" in dir(d):
        t = d["stamp"].split(os.sep)[0]
        if not t:
            return d
        o = get_cls(t)()
        update(o, d)
        del o["stamp"]
        return o
    return d

def items(o):
    "o is object to get items from."
    try:
        return o.items()
    except (TypeError, AttributeError):
        return o.__dict__.items()

def keys(o):
    "o is object to return list of keys from."
    try:
        return o.keys()
    except (TypeError, AttributeError):
        return o.__dict__.keys()

def last(o):
    "o is the object to show the last version on disk of."
    path, l = lastfn(str(get_type(o)))
    if  l:
        update(o, l)
        o.__stamp__ = path

def lasttype(otype):
    "otype is the object (module.class) to the last saved object of."
    fns = objs(otype)
    if fns:
        return hook(fns[-1])

def lastfn(otype):
    "otype is the type to return the last object and it's filename for."
    fns = objs(otype)
    if fns:
        fn = fns[-1]
        return (fn, hook(fn))
    return (None, None)

def load(o, path):
    "o is object to load the data into, path is the filename to read from."
    assert path
    assert workdir
    o.__stamp__ = path
    lpath = os.path.join(workdir, "store", path)
    cdir(lpath)
    with open(lpath, "r") as ofile:
        try:
            v = json.load(ofile, object_hook=hooked)
        except json.decoder.JSONDecodeError as ex:
            print(path, ex)
            return
        if v:
            if isinstance(v, Object):
                o.__dict__.update(vars(v))
            else:
                o.__dict__.update(v)
    unstamp(o)

def locked(l):
    "l is the lock the provide a descriptor for."
    def lockeddec(func, *args, **kwargs):
        def lockedfunc(*args, **kwargs):
            l.acquire()
            res = None
            try:
                res = func(*args, **kwargs)
            finally:
                l.release()
            return res
        lockedfunc.__doc__ = func.__doc__
        return lockedfunc
    return lockeddec

def names(name, timed=None):
    "return all filenames that have name in their filename."
    if not name:
        return []
    assert workdir
    p = os.path.join(workdir, "store", name) + os.sep
    res = []
    for rootdir, _dirs, files in os.walk(p, topdown=False):
        for fn in files:
            fnn = os.path.join(rootdir, fn).split(os.path.join(workdir, "store"))[-1]
            ftime = fntime(fnn)
            if timed and "from" in timed and timed["from"] and ftime < timed["from"]:
                continue
            if timed and timed.to and ftime > timed.to:
                continue
            res.append(os.sep.join(fnn.split(os.sep)[1:]))
    return sorted(res, key=fntime)

def objs(name, timed=None):
    "return last versions of object with name in their filename."
    if not name:
        return []
    assert workdir
    p = os.path.join(workdir, "store", name) + os.sep
    res = []
    d = ""
    for rootdir, dirs, _files in os.walk(p, topdown=False):
        if dirs:
            d = sorted(dirs)[-1]
            if d.count("-") == 2:
                dd = os.path.join(rootdir, d)
                fls = sorted(os.listdir(dd))
                if fls:
                    p = os.path.join(dd, fls[-1])
                    if timed and "from" in timed and timed["from"] and fntime(p) < timed["from"]:
                        continue
                    if timed and timed.to and fntime(p) > timed.to:
                        continue
                    res.append(p)
    return sorted(res, key=fntime)

def register(o, k, v):
    "o is the object to register key (k) an value (v)."
    o[k] = v

@locked(savelock)
def save(o, stime=None):
    "o is the object to save, stime is option provided timestamp."
    assert workdir
    if stime:
        o.__stamp__ = os.path.join(get_type(o), str(uuid.uuid4()),
                                   stime + "." + str(random.randint(0, 100000)))
    else:
        timestamp = str(datetime.datetime.now()).split()
        if getattr(o, "__stamp__", None):
            try:
                spl = o.__stamp__.split(os.sep)
                spl[-2] = timestamp[0]
                spl[-1] = timestamp[1]
                o.__stamp__ = os.sep.join(spl)
            except AttributeError:
                pass
        if not getattr(o, "__stamp__", None):
            o.__stamp__ = os.path.join(get_type(o), str(uuid.uuid4()), os.sep.join(timestamp))
    opath = os.path.join(workdir, "store", o.__stamp__)
    cdir(opath)
    with open(opath, "w") as ofile:
        json.dump(stamp(o), ofile, default=default)
    os.chmod(opath, 0o444)
    return o.__stamp__

def scan(o, txt):
    "txt is text to scan for in every object's value."
    for _k, v in items(o):
        if txt in str(v):
            return True
    return False

def search(o, s):
    "o is is the object to search for string s in, s is string to match in values."
    ok = False
    for k, v in items(s):
        vv = get(o, k)
        if v not in str(vv):
            ok = False
            break
        ok = True
    return ok

def stamp(o):
    "o is the object to provide with filename stamps."
    for k in xdir(o):
        oo = getattr(o, k, None)
        if isinstance(oo, Object):
            stamp(oo)
            oo.__dict__["stamp"] = oo.__stamp__
            o[k] = oo
        else:
            continue
    o.__dict__["stamp"] = o.__stamp__
    return o

def unstamp(o):
    "remove filename stamps."
    for k in xdir(o):
        oo = getattr(o, k, None)
        if isinstance(oo, Object):
            del oo.__dict__["stamp"]
        else:
            continue
    try:
        del o.__dict__["stamp"]
    except KeyError:
        pass
    return o

def update(o, d):
    "o is the object to update with dict or other Object."
    if isinstance(d, Object):
        return o.__dict__.update(vars(d))
    return o.__dict__.update(d)

def values(o):
    " o is the object to return values from."
    try:
        return o.values()
    except (TypeError, AttributeError):
        return o.__dict__.values()

def xdir(o, skip=None):
    "o is the object get a dir() from, skip is the string as skip value"
    res = []
    for k in dir(o):
        if skip is not None and skip in k:
            continue
        res.append(k)
    return res
