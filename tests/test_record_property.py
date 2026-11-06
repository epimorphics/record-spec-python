"""Port of the Kotlin ``RecordPropertyTests`` (added with the #59 upstream fix)."""

from __future__ import annotations

from helpers import TestListener

from record_spec.model import Schema
from record_spec.model.events import PropertyModifiedEvent
from record_spec.model.property import RecordProperty


def _make_schema():
    schema = Schema()
    schema.create_record("http://example.org/rec/Foo", "http://example.org/def/Foo", "Foo")
    schema.create_record("http://example.org/rec/Bar", "http://example.org/def/Bar", "Bar")
    return schema


def test_range_returns_union_of_all_record_types():
    schema = _make_schema()
    foo = schema.resolve_record("http://example.org/rec/Foo")
    bar = schema.resolve_record("http://example.org/rec/Bar")
    rec = RecordProperty(schema, "foo", "https://schema.org/foo")
    rec.add_constraint("http://example.org/rec/Foo")
    rec.add_constraint("http://example.org/rec/Bar")
    assert foo in list(rec.range)
    assert bar in list(rec.range)


def test_add_constraint_notifies_change():
    schema = _make_schema()
    rec = RecordProperty(schema, "foo", "https://schema.org/foo")
    listener = TestListener()
    rec.add_listener(listener)
    rec.add_constraint("http://example.org/rec/Foo")
    assert len(listener.received) == 1
    event = listener.received[0]
    assert isinstance(event, PropertyModifiedEvent)
    assert event.property is rec


def test_remove_constraint_remove_by_index_raises_event_and_removes_item():
    schema = _make_schema()
    bar = schema.resolve_record("http://example.org/rec/Bar")
    rec = RecordProperty(schema, "foo", "https://schema.org/foo")
    rec.add_constraint("http://example.org/rec/Foo")
    rec.add_constraint("http://example.org/rec/Bar")

    listener = TestListener()
    rec.add_listener(listener)

    # The #59 regression: index 0 (the first constraint) must be removable.
    rec.remove_constraint(0)

    # Leaves only the Bar constraint
    assert len(rec.constraints) == 1
    assert rec.constraints[0].record == bar

    # Raises an event
    assert len(listener.received) == 1
    event = listener.received[0]
    assert isinstance(event, PropertyModifiedEvent)
    assert event.property is rec


def test_remove_constraint_remove_by_instance_raises_event_and_removes_item():
    schema = _make_schema()
    bar = schema.resolve_record("http://example.org/rec/Bar")
    rec = RecordProperty(schema, "foo", "https://schema.org/foo")
    rec.add_constraint("http://example.org/rec/Foo")
    rec.add_constraint("http://example.org/rec/Bar")

    listener = TestListener()
    rec.add_listener(listener)

    rec.remove_constraint(next(c for c in rec.constraints if c.record_ref == "http://example.org/rec/Foo"))

    # Leaves only the Bar constraint
    assert len(rec.constraints) == 1
    assert rec.constraints[0].record == bar

    # Raises an event
    assert len(listener.received) == 1
    event = listener.received[0]
    assert isinstance(event, PropertyModifiedEvent)
    assert event.property is rec


def test_remove_constraint_remove_by_index_is_silent_if_index_out_of_range():
    schema = _make_schema()
    rec = RecordProperty(schema, "foo", "https://schema.org/foo")
    rec.add_constraint("http://example.org/rec/Foo")
    rec.add_constraint("http://example.org/rec/Bar")

    listener = TestListener()
    rec.add_listener(listener)

    rec.remove_constraint(2)
    assert len(rec.constraints) == 2
    assert len(listener.received) == 0


def test_remove_constraint_remove_by_instance_is_silent_if_item_not_in_list():
    schema = _make_schema()
    rec = RecordProperty(schema, "foo", "https://schema.org/foo")
    rec.add_constraint("http://example.org/rec/Foo")
    rec.add_constraint("http://example.org/rec/Bar")
    to_remove = rec.constraints[0]
    rec.remove_constraint(to_remove)

    listener = TestListener()
    rec.add_listener(listener)
    rec.remove_constraint(to_remove)
    assert len(rec.constraints) == 1
    assert len(listener.received) == 0