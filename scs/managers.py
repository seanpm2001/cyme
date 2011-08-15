"""scs.managers"""

from __future__ import absolute_import

from anyjson import serialize
from celery import current_app as celery
from celery.utils import gen_unique_id
from djcelery.managers import ExtendedManager


class BrokerManager(ExtendedManager):

    def get_default(self):
        conf = celery.conf
        broker, _ = self.get_or_create(
                        hostname=conf.BROKER_HOST or "127.0.0.1",
                        userid=conf.BROKER_USER or "guest",
                        password=conf.BROKER_PASSWORD or "guest",
                        port=conf.BROKER_PORT or 5672,
                        virtual_host=conf.BROKER_VHOST or "/")
        return broker


class NodeManager(ExtendedManager):

    def enabled(self):
        return self.filter(is_enabled=True)

    def disabled(self):
        return self.filter(is_enabled=False)

    def _maybe_queues(self, queues):
        acc = []
        Queue = self.Queue
        if isinstance(queues, basestring):
            queues = queues.split(",")
        for queue in queues:
            if not isinstance(queue, Queue):
                queue, _ = Queue._default_manager.get_or_create(name=queue)
            acc.append(queue)
        return [q.name for q in acc]

    def add(self, nodename=None, queues=None, max_concurrency=1,
            min_concurrency=1, broker=None):
        nodename = nodename or gen_unique_id()

        node = self.create(name=nodename or gen_unique_id(),
                           max_concurrency=max_concurrency,
                           min_concurrency=min_concurrency)
        needs_save = False
        if queues:
            node.queues = self._maybe_queues(queues)
            needs_save = True
        if broker:
            node._broker = broker
            needs_save = True
        if needs_save:
            node.save()
        return node

    def modify(self, nodename, queues, max_concurrency=None,
            min_concurrency=None):
        node = self.get(name=nodename)
        node.queues = self._maybe_queues(queues)
        node.max_concurrency = max_concurrency
        node.min_concurrency = min_concurrency
        node.save()
        return node

    def remove(self, nodename):
        node = self.get(name=nodename)
        node.delete()
        return node

    def enable(self, nodename):
        node = self.get(name=nodename)
        node.enable()
        return node

    def disable(self, nodename):
        node = self.get(name=nodename)
        node.disable()
        return node

    def remove_queue_from_nodes(self, queue, **query):
        nodes = []
        for node in self.filter(**query).iterator():
            if queue in node.queues:
                node.queues.remove(queue)
                node.save()
                nodes.append(node)
        return nodes

    def add_queue_to_nodes(self, queue, **query):
        nodes = []
        for node in self.filter(**query).iterator():
            node.queues.add(queue)
            node.save()
            nodes.append(node)
        return nodes

    @property
    def Queue(self):
        return self.model.Queue

    @property
    def queues(self):
        return self.Queue._default_manager


class QueueManager(ExtendedManager):

    def enabled(self):
        return self.filter(is_enabled=True)

    def _add(self, name, **declaration):
        q, _ = self.get_or_create(name=name, defaults=declaration)
        return q

    def add(self, name, exchange=None, exchange_type=None,
            routing_key=None, **options):
        options = serialize(options) if options else None
        return self._add(name, exchange=exchange, exchange_type=exchange_type,
                               routing_key=routing_key, options=options)
