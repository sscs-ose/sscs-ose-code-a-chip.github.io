"""
opentcad/geometry/mesh.py — Gmsh mesh generation for semiconductor structures.

Claude Code note: gmsh coordinates are in mm. All inputs/outputs here are in um.
Convert: gmsh_mm = opentcad_um * 1e-3  (multiply by 0.001)
Convert: opentcad_um = gmsh_mm * 1e3   (multiply by 1000)

Key function: build_2d_mesh(structure, mesh_size_um) -> pyvista.UnstructuredGrid
The grid has:
  - point coordinates in um
  - cell_data["material_id"] as int32 (Material enum values)
  - 2D triangular elements (CellType.TRIANGLE)
"""
from __future__ import annotations
import numpy as np
import pyvista as pv
from .formats import Material


def build_2d_mesh(structure, mesh_size_um: float = 0.05) -> pv.UnstructuredGrid:
    """Generate a 2D triangular mesh for the given Structure.

    Args:
        structure: A Structure instance with layers, regions, contacts defined.
        mesh_size_um: Default element size [um]. Refinement to mesh_size_um/2
                      is applied near layer interfaces.

    Returns:
        pyvista UnstructuredGrid with triangular elements, coordinates in um,
        and cell_data["material_id"] set to Material enum int values.
    """
    import gmsh

    lc = mesh_size_um * 1e-3   # um → mm
    lc_fine = lc / 2

    if gmsh.isInitialized():
        gmsh.clear()
    else:
        # interruptible=False skips the SIGINT handler that gmsh
        # otherwise installs on init — the handler call fails from any
        # non-main thread (e.g. the Streamlit script-runner thread).
        gmsh.initialize(interruptible=False)

    try:
        gmsh.option.setNumber("General.Verbosity", 0)
        gmsh.model.add(structure.name)

        w_mm = structure.width_um * 1e-3

        layer_rect_tags = []
        layer_centroid_y_mm = []
        y_offset_mm = 0.0
        for layer in structure._layers:
            h_mm = layer.thickness_um * 1e-3
            tag = gmsh.model.occ.addRectangle(0.0, y_offset_mm, 0.0, w_mm, h_mm)
            layer_rect_tags.append(tag)
            layer_centroid_y_mm.append(y_offset_mm + h_mm / 2)
            y_offset_mm += h_mm

        # Region rectangles get fragmented into the layer stack so cells
        # inside the region can be assigned the region's material (not just
        # the layer's). This is how add_region(material=...) takes effect.
        region_rect_tags = []
        for reg in structure._regions:
            rx = reg.x_start * 1e-3
            ry = reg.y_start * 1e-3
            rw = (reg.x_end - reg.x_start) * 1e-3
            rh = (reg.y_end - reg.y_start) * 1e-3
            region_rect_tags.append(
                gmsh.model.occ.addRectangle(rx, ry, 0.0, rw, rh))

        # Glue layers and regions so all sub-surfaces share boundaries.
        all_tags = layer_rect_tags + region_rect_tags
        if len(all_tags) > 1:
            obj = [(2, all_tags[0])]
            tools = [(2, t) for t in all_tags[1:]]
            gmsh.model.occ.fragment(obj, tools)

        gmsh.model.occ.synchronize()

        # Map each post-fragment surface to a Material: region containment
        # wins (last-region-wins to match Structure._resolve_contacts), else
        # fall back to layer assignment by centroid y.
        surf_to_layer = {}
        surf_to_material = {}
        for dim, stag in gmsh.model.getEntities(dim=2):
            xmin, ymin, _, xmax, ymax, _ = gmsh.model.getBoundingBox(dim, stag)
            cx = 0.5 * (xmin + xmax)
            cy = 0.5 * (ymin + ymax)
            idx = min(range(len(layer_centroid_y_mm)),
                      key=lambda i: abs(layer_centroid_y_mm[i] - cy))
            layer = structure._layers[idx]
            surf_to_layer[stag] = layer
            material = layer.material
            for reg in structure._regions:
                rx0 = reg.x_start * 1e-3; rx1 = reg.x_end * 1e-3
                ry0 = reg.y_start * 1e-3; ry1 = reg.y_end * 1e-3
                if rx0 <= cx <= rx1 and ry0 <= cy <= ry1:
                    material = reg.material
            surf_to_material[stag] = material

        # Physical groups: one per surface, named after the Material enum.
        # Surfaces of the same material can share a group, but per-surface
        # is simpler and lets the device layer distinguish layers later.
        for stag, material in surf_to_material.items():
            pg = gmsh.model.addPhysicalGroup(2, [stag])
            gmsh.model.setPhysicalName(2, pg, material.name)

        # Identify horizontal interface curves (at y between adjacent layers).
        interface_y_mm = []
        y = 0.0
        for layer in structure._layers[:-1]:
            y += layer.thickness_um * 1e-3
            interface_y_mm.append(y)

        # Horizontal curve: span-y ≲ a nanometer. Gmsh's getBoundingBox
        # returns values with a ±1e-7 mm pad, so tolerances tighter than
        # a few nm silently reject every real edge.
        interface_curves = []
        atol = 1e-6   # mm (= 1 nm)
        for dim, ctag in gmsh.model.getEntities(dim=1):
            _, ymin, _, _, ymax, _ = gmsh.model.getBoundingBox(dim, ctag)
            if abs(ymax - ymin) > atol:
                continue
            cy = 0.5 * (ymin + ymax)
            if any(abs(cy - iy) < atol for iy in interface_y_mm):
                interface_curves.append(ctag)

        # Distance + Threshold field: lc_fine within ~lc of an interface,
        # ramping up to lc by 4*lc away. SizeMax acts as the bulk size.
        if interface_curves:
            dist_id, thresh_id = 1, 2
            gmsh.model.mesh.field.add("Distance", dist_id)
            gmsh.model.mesh.field.setNumbers(dist_id, "CurvesList", interface_curves)
            gmsh.model.mesh.field.setNumber(dist_id, "Sampling", 100)

            gmsh.model.mesh.field.add("Threshold", thresh_id)
            gmsh.model.mesh.field.setNumber(thresh_id, "InField", dist_id)
            gmsh.model.mesh.field.setNumber(thresh_id, "SizeMin", lc_fine)
            gmsh.model.mesh.field.setNumber(thresh_id, "SizeMax", lc)
            gmsh.model.mesh.field.setNumber(thresh_id, "DistMin", lc_fine)
            gmsh.model.mesh.field.setNumber(thresh_id, "DistMax", 2 * lc)
            gmsh.model.mesh.field.setAsBackgroundMesh(thresh_id)

            # Let the field drive sizing exclusively.
            gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
            gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)

        gmsh.option.setNumber("Mesh.Algorithm", 6)   # Frontal-Delaunay
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc_fine)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.optimize("Laplace2D")

        grid = _gmsh_to_pyvista(surf_to_material)
    finally:
        gmsh.finalize()

    return grid


def _gmsh_to_pyvista(surf_to_material: dict) -> pv.UnstructuredGrid:
    """Extract the current gmsh mesh into a pyvista UnstructuredGrid.

    Coordinates are converted from mm to um. Material IDs come from the
    surface-to-material map (resolved by region containment, falling back
    to layer), so every triangle gets the correct Material enum value.
    """
    import gmsh

    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    points = coords.reshape(-1, 3) * 1e3   # mm → um
    tag_to_idx = {int(t): i for i, t in enumerate(node_tags)}

    all_cells: list[int] = []
    all_mat_ids: list[int] = []

    for stag, material in surf_to_material.items():
        elem_types, elem_tags, elem_conn = gmsh.model.mesh.getElements(dim=2, tag=stag)
        mat_id = int(material)
        for et, etags, econn in zip(elem_types, elem_tags, elem_conn):
            if et != 2:   # type 2 = 3-node triangle
                continue
            conn = econn.reshape(len(etags), 3)
            for nodes in conn:
                all_cells.append(3)
                all_cells.extend(tag_to_idx[int(n)] for n in nodes)
                all_mat_ids.append(mat_id)

    if not all_mat_ids:
        raise RuntimeError("No triangular elements found in mesh. "
                           "Check that gmsh generated 2D elements.")

    cells = np.array(all_cells, dtype=np.int64)
    celltypes = np.full(len(all_mat_ids), pv.CellType.TRIANGLE, dtype=np.uint8)
    mat_ids = np.array(all_mat_ids, dtype=np.int32)

    grid = pv.UnstructuredGrid(cells, celltypes, points)
    grid.cell_data["material_id"] = mat_ids
    return grid


def _get_material_id_for_element(elem_tag: int) -> int:
    """Return Material int ID for a gmsh element by physical-group lookup.

    Resolves the entity that owns the element, finds its physical group(s),
    and maps the group name back to the Material enum. Falls back to VACUUM
    if no recognized physical group is found.
    """
    import gmsh

    _, _, dim, ent_tag = gmsh.model.mesh.getElement(elem_tag)
    for pg in gmsh.model.getPhysicalGroupsForEntity(dim, ent_tag):
        name = gmsh.model.getPhysicalName(dim, pg)
        try:
            return int(Material[name])
        except KeyError:
            continue
    return int(Material.VACUUM)
