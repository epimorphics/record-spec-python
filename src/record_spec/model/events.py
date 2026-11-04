"""The model event system: change notification for schema elements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from record_spec.model import Mixin, Property, Record


class Event:
    """Base class for all model events."""

    def __init__(self, event_name: str):
        self.event_name = event_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.event_name!r})"


class EventListener(ABC):
    """Interface for objects that receive model events."""

    @abstractmethod
    def on_event(self, event: Event) -> None: ...


class EventSourceMixin:
    """Mixin providing event-listener registration and notification.

    Classes using this mixin must call ``super().__init__()`` (cooperatively)
    or otherwise invoke :meth:`_init_listeners`.
    """

    def _init_listeners(self) -> None:
        self._listeners: set[EventListener] = set()

    def add_listener(self, listener: EventListener) -> None:
        if not hasattr(self, "_listeners"):
            self._init_listeners()
        self._listeners.add(listener)

    def remove_listener(self, listener: EventListener) -> None:
        if hasattr(self, "_listeners"):
            self._listeners.discard(listener)

    def notify_event(self, event: Event) -> None:
        for listener in list(getattr(self, "_listeners", ())):
            listener.on_event(event)


class RecordModifiedEvent(Event):
    """Event raised when a record is modified."""

    def __init__(self, record: Record):
        super().__init__("recordModified")
        self.record = record


class MixinModifiedEvent(Event):
    """Event raised when a mixin is modified."""

    def __init__(self, mixin: Mixin):
        super().__init__("mixinModified")
        self.mixin = mixin


class PropertyModifiedEvent(Event):
    """Event raised when a property is modified."""

    def __init__(self, prop: Property):
        super().__init__("propertyModified")
        self.property = prop