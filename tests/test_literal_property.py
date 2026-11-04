"""Port of the Kotlin ``LiteralPropertyTests``."""

from __future__ import annotations

from helpers import TestListener

from record_spec.model import LiteralProperty, events
from record_spec.values import RDF_LANG_STRING, XSD


def test_range_returns_union_of_all_datatypes():
    lit = LiteralProperty("label", "https://schema.org/label")
    lit.add_constraint(XSD + "string")
    lit.add_constraint(RDF_LANG_STRING)
    assert lit.range == [XSD + "string", RDF_LANG_STRING]


def test_range_suppresses_duplicates():
    lit = LiteralProperty("age", "https://schema.org/age")
    lit.add_constraint(XSD + "integer", min_inclusive="100")
    lit.add_constraint(XSD + "integer", max_inclusive="-100")
    assert len(lit.range) == 1
    assert lit.range == [XSD + "integer"]


def test_add_constraint_notifies_change():
    lit = LiteralProperty("label", "https://schema.org/label")
    listener = TestListener()
    lit.add_listener(listener)
    lit.add_constraint(XSD + "string")
    assert len(listener.received) == 1
    event = listener.received[0]
    assert isinstance(event, events.PropertyModifiedEvent)
    assert event.property is lit


def test_remove_constraint_remove_by_index_raises_event_and_removes_item():
    lit = LiteralProperty("label", "https://schema.org/label")
    lit.add_constraint(XSD + "string")
    lit.add_constraint(RDF_LANG_STRING)

    listener = TestListener()
    lit.add_listener(listener)

    lit.remove_constraint(0)

    # Leaves only rdfLangString constraint
    assert len(lit.constraints) == 1
    assert lit.constraints[0].datatype == RDF_LANG_STRING

    # Raises an event
    assert len(listener.received) == 1
    event = listener.received[0]
    assert isinstance(event, events.PropertyModifiedEvent)
    assert event.property is lit


def test_remove_constraint_remove_by_instance_raises_event_and_removes_item():
    lit = LiteralProperty("label", "https://schema.org/label")
    lit.add_constraint(XSD + "string")
    lit.add_constraint(RDF_LANG_STRING)

    listener = TestListener()
    lit.add_listener(listener)

    lit.remove_constraint(next(c for c in lit.constraints if c.datatype == RDF_LANG_STRING))

    # Leaves only xsd:string constraint
    assert len(lit.constraints) == 1
    assert lit.constraints[0].datatype == XSD + "string"

    # Raises an event
    assert len(listener.received) == 1
    event = listener.received[0]
    assert isinstance(event, events.PropertyModifiedEvent)
    assert event.property is lit


def test_remove_constraint_remove_by_index_is_silent_if_index_out_of_range():
    lit = LiteralProperty("label", "https://schema.org/label")
    lit.add_constraint(XSD + "string")
    lit.add_constraint(RDF_LANG_STRING)

    listener = TestListener()
    lit.add_listener(listener)

    lit.remove_constraint(2)
    assert len(lit.constraints) == 2
    assert len(listener.received) == 0


def test_remove_constraint_remove_by_instance_is_silent_if_item_not_in_list():
    lit = LiteralProperty("label", "https://schema.org/label")
    lit.add_constraint(XSD + "string")
    lit.add_constraint(RDF_LANG_STRING)
    to_remove = lit.constraints[0]
    lit.remove_constraint(to_remove)

    listener = TestListener()
    lit.add_listener(listener)
    lit.remove_constraint(to_remove)
    assert len(lit.constraints) == 1
    assert len(listener.received) == 0