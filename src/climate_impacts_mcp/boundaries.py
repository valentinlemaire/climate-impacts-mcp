"""Country boundary extraction from world-atlas TopoJSON."""

from __future__ import annotations

# ISO 3166-1 alpha-3 → numeric code mapping.
# Used to look up countries in the world-atlas TopoJSON (which uses numeric IDs).
ISO_ALPHA3_TO_NUMERIC: dict[str, str] = {
    "AFG": "004", "ALB": "008", "DZA": "012", "ASM": "016", "AND": "020",
    "AGO": "024", "ATG": "028", "ARG": "032", "ARM": "051", "AUS": "036",
    "AUT": "040", "AZE": "031", "BHS": "044", "BHR": "048", "BGD": "050",
    "BRB": "052", "BLR": "112", "BEL": "056", "BLZ": "084", "BEN": "204",
    "BTN": "064", "BOL": "068", "BIH": "070", "BWA": "072", "BRA": "076",
    "BRN": "096", "BGR": "100", "BFA": "854", "BDI": "108", "CPV": "132",
    "KHM": "116", "CMR": "120", "CAN": "124", "CAF": "140", "TCD": "148",
    "CHL": "152", "CHN": "156", "COL": "170", "COM": "174", "COG": "178",
    "COD": "180", "CRI": "188", "CIV": "384", "HRV": "191", "CUB": "192",
    "CYP": "196", "CZE": "203", "DNK": "208", "DJI": "262", "DMA": "212",
    "DOM": "214", "ECU": "218", "EGY": "818", "SLV": "222", "GNQ": "226",
    "ERI": "232", "EST": "233", "SWZ": "748", "ETH": "231", "FJI": "242",
    "FIN": "246", "FRA": "250", "GAB": "266", "GMB": "270", "GEO": "268",
    "DEU": "276", "GHA": "288", "GRC": "300", "GRD": "308", "GTM": "320",
    "GIN": "324", "GNB": "624", "GUY": "328", "HTI": "332", "HND": "340",
    "HUN": "348", "ISL": "352", "IND": "356", "IDN": "360", "IRN": "364",
    "IRQ": "368", "IRL": "372", "ISR": "376", "ITA": "380", "JAM": "388",
    "JPN": "392", "JOR": "400", "KAZ": "398", "KEN": "404", "KIR": "296",
    "PRK": "408", "KOR": "410", "KWT": "414", "KGZ": "417", "LAO": "418",
    "LVA": "428", "LBN": "422", "LSO": "426", "LBR": "430", "LBY": "434",
    "LIE": "438", "LTU": "440", "LUX": "442", "MDG": "450", "MWI": "454",
    "MYS": "458", "MDV": "462", "MLI": "466", "MLT": "470", "MHL": "584",
    "MRT": "478", "MUS": "480", "MEX": "484", "FSM": "583", "MDA": "498",
    "MCO": "492", "MNG": "496", "MNE": "499", "MAR": "504", "MOZ": "508",
    "MMR": "104", "NAM": "516", "NRU": "520", "NPL": "524", "NLD": "528",
    "NZL": "554", "NIC": "558", "NER": "562", "NGA": "566", "MKD": "807",
    "NOR": "578", "OMN": "512", "PAK": "586", "PLW": "585", "PAN": "591",
    "PNG": "598", "PRY": "600", "PER": "604", "PHL": "608", "POL": "616",
    "PRT": "620", "QAT": "634", "ROU": "642", "RUS": "643", "RWA": "646",
    "KNA": "659", "LCA": "662", "VCT": "670", "WSM": "882", "SMR": "674",
    "STP": "678", "SAU": "682", "SEN": "686", "SRB": "688", "SYC": "690",
    "SLE": "694", "SGP": "702", "SVK": "703", "SVN": "705", "SLB": "090",
    "SOM": "706", "ZAF": "710", "SSD": "728", "ESP": "724", "LKA": "144",
    "SDN": "729", "SUR": "740", "SWE": "752", "CHE": "756", "SYR": "760",
    "TWN": "158", "TJK": "762", "TZA": "834", "THA": "764", "TLS": "626",
    "TGO": "768", "TON": "776", "TTO": "780", "TUN": "788", "TUR": "792",
    "TKM": "795", "TUV": "798", "UGA": "800", "UKR": "804", "ARE": "784",
    "GBR": "826", "USA": "840", "URY": "858", "UZB": "860", "VUT": "548",
    "VEN": "862", "VNM": "704", "YEM": "887", "ZMB": "894", "ZWE": "716",
    "PSE": "275", "XKX": "-99", "NCL": "540", "SOL": "090", "GUF": "254",
    "PRI": "630", "ESH": "732", "ATF": "260", "FLK": "238",
}


def _collect_arc_indices(arcs_nested: list) -> set[int]:
    """Recursively collect all arc indices from a TopoJSON geometry's arcs."""
    indices: set[int] = set()
    for item in arcs_nested:
        if isinstance(item, list):
            indices.update(_collect_arc_indices(item))
        else:
            indices.add(~item if item < 0 else item)
    return indices


def _remap_arcs(arcs_nested: list, index_map: dict[int, int]) -> list:
    """Recursively remap arc indices using the provided mapping."""
    result = []
    for item in arcs_nested:
        if isinstance(item, list):
            result.append(_remap_arcs(item, index_map))
        else:
            if item < 0:
                result.append(~index_map[~item])
            else:
                result.append(index_map[item])
    return result


def extract_country_topojson(world_topo: dict, numeric_id: str) -> dict | None:
    """Extract a single country's TopoJSON from the world-atlas topology.

    Returns a minimal self-contained TopoJSON with only the country's geometry
    and its referenced arcs. Returns None if the country is not found.
    """
    objects = world_topo.get("objects", {})
    countries_obj = objects.get("countries")
    if not countries_obj:
        return None

    geometries = countries_obj.get("geometries", [])

    # Find the country geometry by numeric ID
    country_geom = None
    for geom in geometries:
        if geom.get("id") == numeric_id:
            country_geom = geom
            break

    if country_geom is None:
        return None

    geom_arcs = country_geom.get("arcs", [])
    if not geom_arcs:
        # Geometry with no arcs (e.g., a Point) — return as-is
        return {
            "type": "Topology",
            "objects": {"country": {"type": "GeometryCollection", "geometries": [country_geom]}},
            "arcs": [],
        }

    # Collect all referenced arc indices and build remapping
    arc_indices = sorted(_collect_arc_indices(geom_arcs))
    index_map = {old: new for new, old in enumerate(arc_indices)}

    new_geom = {
        "type": country_geom["type"],
        "arcs": _remap_arcs(geom_arcs, index_map),
    }
    if "id" in country_geom:
        new_geom["id"] = country_geom["id"]
    if "properties" in country_geom:
        new_geom["properties"] = country_geom["properties"]

    result: dict = {
        "type": "Topology",
        "objects": {
            "country": {
                "type": "GeometryCollection",
                "geometries": [new_geom],
            }
        },
        "arcs": [world_topo["arcs"][i] for i in arc_indices],
    }
    if "transform" in world_topo:
        result["transform"] = world_topo["transform"]

    return result
