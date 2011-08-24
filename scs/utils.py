"""scs.utils"""

from __future__ import absolute_import

import sys

from importlib import import_module

from celery.utils import get_symbol_by_name
from cl.utils.functional import promise, maybe_promise # noqa
from kombu.utils import gen_unique_id as uuid          # noqa
from kombu.utils import cached_property                # noqa
from unipath import Path as _Path

_pkg_cache = {}


def find_package(mod, _s=None):
    pkg = None
    _s = _s or mod
    if not mod:
        return
    if mod in _pkg_cache:
        pkg = _pkg_cache[_s] = _pkg_cache[mod]
    else:
        _mod = sys.modules[mod]
        if _mod.__package__:
            pkg = _pkg_cache[_s] = _mod.__package__
    return pkg or find_package('.'.join(mod.split('.')[:-1]), _s)


def find_symbol(origin, sym):
    return get_symbol_by_name(sym,
                package=find_package(getattr(origin, "__module__", None
                                        or origin.__class__.__module__)))


def instantiate(origin, sym, *args, **kwargs):
    return find_symbol(origin, sym)(*args, **kwargs)


class Path(_Path):
    """Path that can use the ``/`` operator to combine paths.

        >>> p = Path("foo")
        >>> p / "bar" / "baz"
        Path("foo/bar/baz")
    """

    def __div__(self, other):
        return Path(self, other)


def shellquote(v):
    # XXX Not currently used, but may be of use later,
    # and don't want to write it again.
    return "\\'".join("'" + p + "'" for p in v.split("'"))


def imerge_settings(a, b):
    """Merge two django settings modules,
    keys in ``b`` have precedence."""
    orig = import_module(a.SETTINGS_MODULE)
    for key, value in vars(b).iteritems():
        if not hasattr(orig, key):
            setattr(a, key, value)


def setup_logging(loglevel="INFO", logfile=None):
    from celery import current_app as celery
    from celery.utils import LOG_LEVELS
    if isinstance(loglevel, basestring):
        loglevel = LOG_LEVELS[loglevel]
    return celery.log.setup_logging_subsystem(loglevel, logfile)
