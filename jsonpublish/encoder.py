""" Configurable JSON encoder for publishing Python objects"""

try:
    import simplejson as json
except ImportError:
    import json

from zope import proxy
from zope.interface import adapter
from zope.interface import Interface, providedBy, implementedBy
from repoze.lru import LRUCache

__all__ = (
    "JSONEncoder", "JSONEncoderSettingsProxy", "jsonsettings",
    "AdapterRegistry")

class IJSONSerializeable(Interface):
    """ Marker interface"""

class AdapterRegistry(object):

    _sentinel = object()

    def __init__(self):
        self.underlying = adapter.AdapterRegistry()
        self.cache = LRUCache(500)

    def lookup_adapter(self, typ):
        adapter = self.cache.get(typ, self._sentinel)
        if adapter is self._sentinel:
            adapter = self.underlying.lookup([typ], IJSONSerializeable, "")
            self.cache.put(typ, adapter)
        return adapter

    def register_adapter(self, typ, adapter):
        self.underlying.register(
            [implementedBy(typ)], IJSONSerializeable, "", adapter)
        # XXX: Cache eviction below isn't threadsafe, but at the same time it
        # isn't supposed to register_adapter call to be threadsafe.
        self.cache.data.pop(implementedBy(typ), None)

class JSONEncoder(json.JSONEncoder):

    def __init__(self, *args, **kwargs):
        if "adapters" in kwargs:
            self.adapters = kwargs.pop("adapters")
        else:
            self.adapters = AdapterRegistry()
        super(JSONEncoder, self).__init__(*args, **kwargs)

    def default(self, o, **settings):
        if proxy.isProxy(o, JSONEncoderSettingsProxy):
            o, settings = proxy.getProxiedObject(o), o.__json_settings__
        adapter = self.adapters.lookup_adapter(providedBy(o))
        if adapter is None:
            raise TypeError("%r is not JSON serializable" % o)
        return adapter(o, **settings)

class JSONEncoderSettingsProxy(proxy.ProxyBase):

    __slots__ = ("__json_settings__",)

    def __new__(cls, o, **settings):
        p = proxy.ProxyBase.__new__(cls, o)
        p.__json_settings__ = settings
        return p

    def __init__(self, o, **settings):
        pass

jsonsettings = JSONEncoderSettingsProxy