"""Port of the Kotlin ``MixinTests``."""

from __future__ import annotations

import pytest
from helpers import TestListener

from record_spec.exceptions import PropertyClashException
from record_spec.model import Schema
from record_spec.values import XSD


def test_create_property():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    mixin.create_literal_property("p", "http://example.org/p", required=True, repeatable=False).add_constraint(
        XSD + "string"
    )
    assert len(list(mixin.properties)) == 1


def test_create_property_throws_on_short_code_clash():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    mixin.create_literal_property("p", "http://example.org/p", required=True, repeatable=False).add_constraint(
        XSD + "string"
    )
    with pytest.raises(PropertyClashException):
        mixin.create_literal_property("p", "http://example.org/def/p", required=True, repeatable=False).add_constraint(
            XSD + "string"
        )
    assert len(list(mixin.properties)) == 1


def test_create_property_throws_on_uri_clash():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    mixin.create_literal_property("p", "http://example.org/p", required=True, repeatable=False).add_constraint(
        XSD + "string"
    )
    with pytest.raises(PropertyClashException):
        mixin.create_literal_property("foo", "http://example.org/p", required=True, repeatable=False).add_constraint(
            XSD + "string"
        )
    assert len(list(mixin.properties)) == 1


def test_add_property_notifies_listeners():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    test_listener = TestListener()
    mixin.add_listener(test_listener)
    mixin.create_literal_property("p", "http://example.org/p", required=True, repeatable=False).add_constraint(
        XSD + "string"
    )
    assert len(test_listener.received) == 2
    assert test_listener.received[0].event_name == "mixinModified"


def test_remove_property_by_short_code():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    mixin.create_literal_property("p", "http://example.org/p", required=True, repeatable=False).add_constraint(
        XSD + "string"
    )
    mixin.remove_property("p")
    assert len(list(mixin.properties)) == 0


def test_remove_property_by_instance():
    schema = Schema()
    mixin = schema.create_mixin("http://example.org/mixinA")
    p = mixin.create_literal_property("p", "http://example.org/p", required=True, repeatable=False)
    p.add_constraint(XSD + "string")
    mixin.remove_property(p)
    assert len(list(mixin.properties)) == 0