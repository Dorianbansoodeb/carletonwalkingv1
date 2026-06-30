#!/usr/bin/env python3
"""Download Carleton campus drive network from OSM (OSMnx) and export MARS GeoJSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import osmnx as ox
from patch_graph_for_mars import patch_graph_for_mars
from pyproj import Transformer
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "resources" / "campus_drive_graph.geojson"

CAMPUS_QUERY = "Carleton University, Ottawa, Ontario, Canada"
CONSOLIDATE_TOLERANCE_M = 12.0
ENDPOINT_TOL_M = 1.0

# Parking lots and off-network exits (lat, lon) — same as DEVS data_creation.py
MARKERS = {
    "P1": (45.3813, -75.7021),
    "P2": (45.3839, -75.6964),
    "P3": (45.3847, -75.6919),
    "P4": (45.3857, -75.6950),
    "Ravensrd Exit": (45.3851, -75.6903),
    "Stadium Exit": (45.3881, -75.6927),
}

SPLIT_AT = ("P1", "P2", "P4")
CONNECT_AT = ("P3", "Ravensrd Exit", "Stadium Exit")


def _edge_linestring(graph, u, v, _key, data):
    geom = data.get("geometry")
    if geom is not None:
        return geom
    xu, yu = graph.nodes[u]["x"], graph.nodes[u]["y"]
    xv, yv = graph.nodes[v]["x"], graph.nodes[v]["y"]
    return LineString([(xu, yu), (xv, yv)])


def _new_node_id(graph):
    return int(max(graph.nodes)) + 1


def add_marker_node_and_connect(graph, latlon, to_proj, to_ll, name, edge_name):
    lat, lon = latlon
    x, y = to_proj.transform(lon, lat)
    connect_to = ox.distance.nearest_nodes(graph, X=x, Y=y)
    marker_id = _new_node_id(graph)
    graph.add_node(
        marker_id,
        x=float(x),
        y=float(y),
        lon=float(lon),
        lat=float(lat),
        street_node=name,
    )
    x2, y2 = graph.nodes[connect_to]["x"], graph.nodes[connect_to]["y"]
    geom = LineString([(x, y), (x2, y2)])
    attrs = {
        "u": marker_id,
        "v": connect_to,
        "name": edge_name,
        "highway": "tertiary",
        "oneway": False,
        "geometry": geom,
        "length": float(geom.length),
        "maxspeed": "Unknown",
    }
    graph.add_edge(marker_id, connect_to, **attrs)
    graph.add_edge(
        connect_to,
        marker_id,
        **{**attrs, "u": connect_to, "v": marker_id},
    )
    return marker_id


def cut_line_at_distance(line: LineString, dist: float):
    if dist <= 0.0 or dist >= line.length:
        return None, None
    coords = list(line.coords)
    acc = 0.0
    for i in range(len(coords) - 1):
        p0 = Point(coords[i])
        p1 = Point(coords[i + 1])
        seg_len = p0.distance(p1)
        if acc + seg_len >= dist:
            t = (dist - acc) / seg_len if seg_len else 0.0
            x = coords[i][0] + t * (coords[i + 1][0] - coords[i][0])
            y = coords[i][1] + t * (coords[i + 1][1] - coords[i][1])
            cut_pt = (x, y)
            first_coords = coords[: i + 1] + [cut_pt]
            second_coords = [cut_pt] + coords[i + 1 :]
            if len(first_coords) < 2 or len(second_coords) < 2:
                return None, None
            return LineString(first_coords), LineString(second_coords)
        acc += seg_len
    return None, None


def split_nearest_edge_with_point(graph, latlon, to_proj, to_ll, name):
    lat, lon = latlon
    x, y = to_proj.transform(lon, lat)
    pt = Point(x, y)
    u, v, key = ox.distance.nearest_edges(graph, X=x, Y=y)
    data = graph.get_edge_data(u, v, key)
    geom = _edge_linestring(graph, u, v, key, data)
    snapped = geom.interpolate(geom.project(pt))
    d_along = float(geom.project(snapped))
    u_pt = Point(graph.nodes[u]["x"], graph.nodes[u]["y"])
    v_pt = Point(graph.nodes[v]["x"], graph.nodes[v]["y"])
    if snapped.distance(u_pt) <= ENDPOINT_TOL_M:
        return u
    if snapped.distance(v_pt) <= ENDPOINT_TOL_M:
        return v
    g1, g2 = cut_line_at_distance(geom, d_along)
    if g1 is None or g2 is None:
        nearest = ox.distance.nearest_nodes(graph, X=snapped.x, Y=snapped.y)
        if Point(graph.nodes[nearest]["x"], graph.nodes[nearest]["y"]).distance(snapped) <= ENDPOINT_TOL_M:
            return nearest
        raise RuntimeError(f"Could not split edge for marker {name!r}.")
    new_id = _new_node_id(graph)
    lon_new, lat_new = to_ll.transform(snapped.x, snapped.y)
    graph.add_node(
        new_id,
        x=float(snapped.x),
        y=float(snapped.y),
        lon=float(lon_new),
        lat=float(lat_new),
        street_node=name,
    )
    edges_to_split = []
    if graph.has_edge(u, v):
        for k, d in graph.get_edge_data(u, v).items():
            edges_to_split.append((u, v, k, d))
    if graph.has_edge(v, u):
        for k, d in graph.get_edge_data(v, u).items():
            edges_to_split.append((v, u, k, d))
    for a, b, k, _ in edges_to_split:
        graph.remove_edge(a, b, k)

    def add_split_edge(a, b, geom_piece, template):
        attrs = dict(template)
        attrs["geometry"] = geom_piece
        attrs["length"] = float(geom_piece.length)
        attrs["u"] = a
        attrs["v"] = b
        graph.add_edge(a, b, **attrs)

    g1_start = Point(list(g1.coords)[0])
    g1_end = Point(list(g1.coords)[-1])
    if min(g1_start.distance(u_pt), g1_end.distance(u_pt)) <= min(
        g1_start.distance(v_pt), g1_end.distance(v_pt)
    ):
        first, second = g1, g2
    else:
        first, second = g2, g1
    for a, b, _k, d in edges_to_split:
        if a == u and b == v:
            add_split_edge(u, new_id, first, d)
            add_split_edge(new_id, v, second, d)
        else:
            add_split_edge(v, new_id, second, d)
            add_split_edge(new_id, u, first, d)
    return new_id


def recompute_edge_lengths(graph):
    for _u, _v, _k, data in graph.edges(keys=True, data=True):
        geom = data.get("geometry")
        if geom is not None:
            data["length"] = float(geom.length)
        else:
            x1, y1 = graph.nodes[_u]["x"], graph.nodes[_u]["y"]
            x2, y2 = graph.nodes[_v]["x"], graph.nodes[_v]["y"]
            data["length"] = float(LineString([(x1, y1), (x2, y2)]).length)


def fix_graph_for_mars(path: Path) -> None:
    patch_graph_for_mars(path)


def export_geojson(graph, path: Path) -> None:
    graph_wgs84 = ox.project_graph(graph, to_crs="EPSG:4326")
    _nodes, edges = ox.graph_to_gdfs(graph_wgs84)
    edges = edges.reset_index()
    if "name" not in edges.columns:
        edges["name"] = "Unnamed"
    else:
        edges["name"] = edges["name"].fillna("Unnamed")
    if "maxspeed" not in edges.columns:
        edges["maxspeed"] = "Unknown"
    else:
        edges["maxspeed"] = edges["maxspeed"].fillna("Unknown").apply(
            lambda x: x[0] if isinstance(x, list) and x else x
        )
    if "oneway" not in edges.columns:
        edges["oneway"] = False
    else:
        edges["oneway"] = edges["oneway"].fillna(False)
    edges["sim_roads"] = [[] for _ in range(len(edges))]
    edges.to_file(path, driver="GeoJSON")
    fix_graph_for_mars(path)


def build_graph():
    print(f"Geocoding {CAMPUS_QUERY!r}...")
    campus = ox.geocode_to_gdf(CAMPUS_QUERY)
    polygon = campus.geometry.iloc[0]

    print("Downloading drive network (network_type=drive)...")
    graph = ox.graph_from_polygon(polygon, network_type="drive")
    graph = ox.project_graph(graph)
    graph = ox.consolidate_intersections(
        graph, tolerance=CONSOLIDATE_TOLERANCE_M, rebuild_graph=True
    )

    proj_crs = graph.graph["crs"]
    to_proj = Transformer.from_crs("EPSG:4326", proj_crs, always_xy=True)
    to_ll = Transformer.from_crs(proj_crs, "EPSG:4326", always_xy=True)

    print("Splitting edges at parking markers...")
    for name in SPLIT_AT:
        split_nearest_edge_with_point(graph, MARKERS[name], to_proj, to_ll, name)

    print("Adding parking / exit connectors...")
    add_marker_node_and_connect(
        graph, MARKERS["P3"], to_proj, to_ll, "P3", "P3 connector"
    )
    add_marker_node_and_connect(
        graph,
        MARKERS["Ravensrd Exit"],
        to_proj,
        to_ll,
        "Ravensrd Exit",
        "Ravensrd Exit connector",
    )
    add_marker_node_and_connect(
        graph,
        MARKERS["Stadium Exit"],
        to_proj,
        to_ll,
        "Stadium Exit",
        "Stadium Exit connector",
    )

    recompute_edge_lengths(graph)
    return graph


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    print(f"Exporting {OUT_PATH}...")
    export_geojson(graph, OUT_PATH)
    print(f"Done. {len(graph.edges)} directed edges.")


if __name__ == "__main__":
    main()
