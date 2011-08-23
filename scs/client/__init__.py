"""scs.client"""

from __future__ import absolute_import

from dictshield import fields

from . import base
from ..utils import cached_property


# XXX `requests` does not currently seem to support using the
#     data argument with PUT requests.


class Instance(base.Model):
    name = fields.StringField(max_length=200)
    broker = fields.StringField(max_length=200)
    pool = fields.StringField(max_length=200)
    min_concurrency = fields.IntField()
    max_concurrency = fields.IntField()
    is_enabled = fields.BooleanField()
    queue_names = fields.ListField(fields.StringField(max_length=200))

    def __repr__(self):
        return "<Instance: %r>" % (self.name, )


class Queue(base.Model):
    name = fields.StringField(max_length=200, required=True)
    exchange = fields.StringField(max_length=200, required=False)
    exchange_type = fields.StringField(max_length=200, required=False)
    routing_key = fields.StringField(max_length=200, required=False)
    options = fields.StringField(max_length=None)

    def __repr__(self):
        return "<Queue: %r>" % (self.name, )


class Client(base.Client):
    app = "scs"

    class Instances(base.Section):

        class Model(Instance):

            class Consumers(base.Section):

                def __init__(self, client, name):
                    base.Section.__init__(self, client)
                    self.path = self.client.path / name / "queues"

                def create_model(self, data, *args, **kwargs):
                    return data

            def __init__(self, *args, **kwargs):
                base.Model.__init__(self, *args, **kwargs)
                self.consumers = self.Consumers(self.parent, name=self.name)
                self.path = self.parent.path / self.name

            def stats(self):
                return self.parent.stats(self.name)

            def autoscale(self, max=None, min=None):
                return self.parent.autoscale(self.name, max=max, min=min)

            class LazyQueues(object):

                def __init__(self, instance):
                    self.instance = instance

                def __iter__(self):
                    return self.instance._get_queues()

                def __getitem__(self, index):
                    return self._eval[index]

                def __contains__(self, queue):
                    if isinstance(queue, Queue):
                        queue = queue.name
                    return queue in self.instance.queue_names

                def __len__(self):
                    return len(self._eval)

                def __repr__(self):
                    return repr(self._eval)

                @cached_property
                def _eval(self):
                    return list(iter(self))

            def _get_queues(self):
                return (self.parent.client.queues.get(name)
                            for name in self.queue_names)

            @property
            def queues(self):
                return self.LazyQueues(self)

        def add(self, name=None, broker=None, nowait=False):
            # name is optional for instances
            return base.Section.add(self, name, nowait, broker=broker)

        def stats(self, name):
            return self.GET(self.path / name / "stats")

        def autoscale(self, name, max=None, min=None):
            return self.POST(self.path / name / "autoscale",
                             params={"max": max, "min": min})

        def create_model(self, data, *args, **kwargs):
            data["queue_names"] = data.pop("queues", None)
            return base.Section.create_model(self, data, *args, **kwargs)

    class Queues(base.Section):

        class Model(Queue):
            pass

        def add(self, name, exchange=None, exchange_type=None,
                routing_key=None, nowait=False, **options):
            options = self.serialize(options) if options else None
            return base.Section.add(self, name, nowait,
                                    exchange=exchange,
                                    exchange_type=exchange_type,
                                    routing_key=routing_key,
                                    options=options)

    def __init__(self, url=None, app=None, info=None):
        super(Client, self).__init__(url)
        self.app = app
        self.instances = self.Instances(self)
        self.queues = self.Queues(self)
        self.info = info or {}

    def add(self, name, broker=None):
        return self.create_model(name, self.root("POST", name,
                                 data={"broker": broker}))

    def get(self, name=None):
        return self.create_model(name, self.root("GET", name or self.app))

    def delete(self, name=None):
        return self.root("DELETE", name or self.app)

    def all(self):
        return self.root("GET")

    def build_url(self, path):
        url = self.url
        if self.app:
            url += "/" + self.app
        return url + str(path)

    def create_model(self, name, info):
        return self.clone(app=name, info=base.AttributeDict(info))

    def clone(self, app=None, info=None):
        return self.__class__(url=self.url, app=app, info=info)

    def __repr__(self):
        return "<Client: %r>" % (self.build_url(""), )
