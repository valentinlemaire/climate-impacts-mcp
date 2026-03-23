"""Tests for country boundary extraction from world-atlas TopoJSON."""

from __future__ import annotations

from climate_impacts_mcp.boundaries import (
    ISO_ALPHA3_TO_NUMERIC,
    extract_country_topojson,
)


SAMPLE_WORLD_TOPO = {
    "type": "Topology",
    "objects": {
        "countries": {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Polygon", "arcs": [[0, 1]], "id": "276"},  # DEU
                {"type": "MultiPolygon", "arcs": [[[2]], [[3, 4]]], "id": "250"},  # FRA
            ],
        }
    },
    "arcs": [
        [[0, 0], [1, 0]],    # arc 0
        [[1, 0], [0, 1]],    # arc 1
        [[10, 10], [11, 10]], # arc 2
        [[20, 20], [21, 20]], # arc 3
        [[21, 20], [20, 21]], # arc 4
    ],
    "transform": {"scale": [0.01, 0.01], "translate": [0, 0]},
}


def test_extract_polygon():
    result = extract_country_topojson(SAMPLE_WORLD_TOPO, "276")
    assert result is not None
    assert result["type"] == "Topology"
    geom = result["objects"]["country"]["geometries"][0]
    assert geom["type"] == "Polygon"
    assert geom["id"] == "276"
    # Should have 2 arcs (indices 0 and 1, remapped to 0 and 1)
    assert len(result["arcs"]) == 2
    assert result["arcs"][0] == [[0, 0], [1, 0]]
    assert result["arcs"][1] == [[1, 0], [0, 1]]
    assert "transform" in result


def test_extract_multipolygon():
    result = extract_country_topojson(SAMPLE_WORLD_TOPO, "250")
    assert result is not None
    geom = result["objects"]["country"]["geometries"][0]
    assert geom["type"] == "MultiPolygon"
    # Should have 3 arcs (indices 2, 3, 4 remapped to 0, 1, 2)
    assert len(result["arcs"]) == 3
    # Remapped arcs: original 2->0, 3->1, 4->2
    assert geom["arcs"] == [[[0]], [[1, 2]]]


def test_extract_not_found():
    result = extract_country_topojson(SAMPLE_WORLD_TOPO, "999")
    assert result is None


def test_extract_negative_arc_indices():
    """Negative arc indices mean reversed arcs (~i)."""
    topo = {
        "type": "Topology",
        "objects": {
            "countries": {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "Polygon", "arcs": [[0, ~1]], "id": "100"},
                ],
            }
        },
        "arcs": [
            [[0, 0], [1, 0]],  # arc 0
            [[1, 0], [0, 1]],  # arc 1
            [[9, 9], [8, 8]],  # arc 2 (unused)
        ],
    }
    result = extract_country_topojson(topo, "100")
    assert result is not None
    assert len(result["arcs"]) == 2
    geom = result["objects"]["country"]["geometries"][0]
    # Arc ~1 should be remapped: original index 1 -> new index 1, so ~1 stays ~1
    assert geom["arcs"] == [[0, ~1]]


def test_iso_mapping_has_common_countries():
    assert ISO_ALPHA3_TO_NUMERIC["USA"] == "840"
    assert ISO_ALPHA3_TO_NUMERIC["DEU"] == "276"
    assert ISO_ALPHA3_TO_NUMERIC["CRI"] == "188"
    assert ISO_ALPHA3_TO_NUMERIC["FRA"] == "250"
    assert ISO_ALPHA3_TO_NUMERIC["IND"] == "356"
