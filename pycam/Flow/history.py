import collections
import datetime

from pycam.Flow.parser import dump_yaml
from pycam.Utils.events import get_event_handler
import pycam.Utils.log

_log = pycam.Utils.log.get_logger()


class DataRevision(object):
    """ create a representation of the current state of all collections """

    def __init__(self):
        """ create a representation of the current state of all collections """
        self.timestamp = datetime.datetime.now()
        self.dump = dump_yaml()

    def __lt__(self, other):
        return (self.timestamp, self.dump) < (other.timestamp, other.dump)


class DataHistory(object):
    """ manage the revisions of the data collections """

    max_revision_count = 20
    subscribed_events = {"model-changed", "model-list-changed",
                         "tool-changed", "tool-list-changed",
                         "process-changed", "process-list-changed",
                         "bounds-changed", "bounds-list-changed",
                         "task-changed", "task-list-changed",
                         "toolpath-changed", "toolpath-list-changed"}

    def __init__(self):
        self._revisions = collections.deque([], self.max_revision_count)
        self._register_events()
        self._store_revision()

    def __del__(self):
        self._unregister_events()

    def _register_events(self):
        event_handler = get_event_handler()
        for event in self.subscribed_events:
            event_handler.register_event(event, self._store_revision)

    def _unregister_events(self):
        event_handler = get_event_handler()
        for event in self.subscribed_events:
            event_handler.unregister_event(event, self._store_revision)

    def _store_revision(self):
        _log.info("Storing a state revision (%d/%d)",
                  len(self._revisions), self.max_revision_count)
        self._revisions.append(DataRevision())
        get_event_handler().emit_event("history-changed")
