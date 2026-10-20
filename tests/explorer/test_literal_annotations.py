"""Tests for literal annotation preservation in ontology load."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from semantica.explorer.app import create_app


TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/a#> .
<http://example.org/a> a owl:Ontology .
ex:Task a owl:Class ; rdfs:label "Task" ; ex:emittedAs "task" .
ex:Goal a owl:Class ; rdfs:label "Goal" ; ex:emittedAs "goal" .
"""

SHAPE = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/a#> .
ex:Declared a sh:NodeShape ; sh:targetObjectsOf ex:emittedAs ; sh:in ( "goal" ) .
"""


def test_literal_annotation_preserved_in_session_graph():
    """Load ontology with custom literal annotation and validate via SHACL."""
    with TestClient(create_app()) as c:
        # Load ontology
        r1 = c.post(
            "/api/ontology/load",
            json={"content": TTL, "format": "turtle"},
        )
        assert r1.status_code == 200, f"Load failed: {r1.text}"

        # Validate with SHACL shape that targets the literal annotation
        r2 = c.post(
            "/api/ontology/shacl/validate",
            json={
                "uri": "http://example.org/a",
                "shacl_turtle": SHAPE,
            },
        )
        assert r2.status_code == 200, f"Validate failed: {r2.text}"
        data = r2.json()

        # The shape allows only "goal" in ex:emittedAs, so the ontology
        # should NOT conform because it has "task" as well.
        assert data["status"] == "success"
        assert data["conforms"] is False, (
            "SHACL validation should find violation for 'task' annotation"
        )
        assert len(data["violations"]) >= 1, "Should have at least one violation"


def test_literal_annotation_on_property():
    """Property custom annotations are preserved in session graph."""
    ttl = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/b#> .
<http://example.org/b> a owl:Ontology .
ex:hasTask a owl:ObjectProperty ; rdfs:label "has task" ; ex:priority "high" .
"""
    shape = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/b#> .
ex:PropShape a sh:NodeShape ; sh:targetObjectsOf ex:priority ; sh:in ( "low" ) .
"""
    with TestClient(create_app()) as c:
        r1 = c.post(
            "/api/ontology/load",
            json={"content": ttl, "format": "turtle"},
        )
        assert r1.status_code == 200

        r2 = c.post(
            "/api/ontology/shacl/validate",
            json={"uri": "http://example.org/b", "shacl_turtle": shape},
        )
        data = r2.json()
        assert data["conforms"] is False, (
            "Property annotation 'high' should violate shape allowing only 'low'"
        )
