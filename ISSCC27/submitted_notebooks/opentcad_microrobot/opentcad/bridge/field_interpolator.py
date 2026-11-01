"""
opentcad/bridge/field_interpolator.py

Transfer doping fields from process mesh to device mesh.
Uses hybrid RBF (bulk) + nearest-neighbor (junction boundary) interpolation
to preserve junction sharpness. See bridge/CLAUDE.md for design rationale.

Key test: tests/bridge/test_field_interpolator.py::test_junction_depth_preserved
Criterion: junction depth preserved within 5% for Gaussian profile.
"""
from __future__ import annotations
import warnings
import numpy as np
from scipy.interpolate import NearestNDInterpolator, RBFInterpolator


def interpolate_doping_field(
    src_points: np.ndarray,
    src_nd: np.ndarray,
    src_na: np.ndarray,
    dst_points: np.ndarray,
    junction_proximity_um: float = 0.03,
    rbf_neighbors: int = 20,
    rbf_smoothing: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate Nd, Na from source mesh to destination mesh.
    
    Args:
        src_points: Source coordinates [um], shape (N, 2) or (N, 3)
        src_nd: Donor concentration [cm^-3], shape (N,)
        src_na: Acceptor concentration [cm^-3], shape (N,)
        dst_points: Destination coordinates [um], shape (M, 2) or (M, 3)
        junction_proximity_um: Switch to NN within this radius of junction [um]
        rbf_neighbors: RBF neighbor count (speed vs accuracy tradeoff)
        rbf_smoothing: RBF smoothing (0=exact, small positive for noisy data)
    
    Returns:
        (dst_nd, dst_na) at destination nodes [cm^-3]
    """
    FLOOR = 1e5  # cm^-3, below intrinsic — effectively undoped

    src_nd_s = np.maximum(src_nd, FLOOR)
    src_na_s = np.maximum(src_na, FLOOR)
    log_nd = np.log10(src_nd_s)
    log_na = np.log10(src_na_s)

    # Strip dimensions with near-zero variance (e.g. 1D profiles given as 2D arrays
    # with all x=0). RBFInterpolator requires the monomial matrix to have full column
    # rank; degenerate dimensions cause a LinAlgError.
    src_active, dst_active = _strip_degenerate_dims(src_points, dst_points)

    # Build RBF interpolators
    try:
        rbf_nd = RBFInterpolator(src_active, log_nd,
                                  neighbors=min(rbf_neighbors, len(src_points)),
                                  smoothing=rbf_smoothing)
        rbf_na = RBFInterpolator(src_active, log_na,
                                  neighbors=min(rbf_neighbors, len(src_points)),
                                  smoothing=rbf_smoothing)
    except Exception as e:
        warnings.warn(f"RBF failed ({e}), using nearest-neighbor fallback.")
        nn = NearestNDInterpolator(src_points, np.stack([log_nd, log_na], axis=1))
        r = nn(dst_points)
        dst_nd = np.maximum(10.0 ** r[:, 0], 0.0)
        dst_na = np.maximum(10.0 ** r[:, 1], 0.0)
        return dst_nd, dst_na

    # Find junction nodes and nearby destinations
    junction_nodes = _find_junction_nodes(src_points, src_nd - src_na)
    near_jn = _points_near_set(dst_points, src_points[junction_nodes], junction_proximity_um)

    log_dst_nd = np.empty(len(dst_points))
    log_dst_na = np.empty(len(dst_points))

    bulk = ~near_jn
    if np.any(bulk):
        log_dst_nd[bulk] = rbf_nd(dst_active[bulk]).ravel()
        log_dst_na[bulk] = rbf_na(dst_active[bulk]).ravel()
    if np.any(near_jn):
        nn_nd = NearestNDInterpolator(src_points, log_nd)
        nn_na = NearestNDInterpolator(src_points, log_na)
        log_dst_nd[near_jn] = nn_nd(dst_points[near_jn])
        log_dst_na[near_jn] = nn_na(dst_points[near_jn])

    dst_nd = 10.0 ** log_dst_nd
    dst_na = 10.0 ** log_dst_na
    dst_nd = np.where(dst_nd <= FLOOR * 1.01, 0.0, dst_nd)
    dst_na = np.where(dst_na <= FLOOR * 1.01, 0.0, dst_na)
    return np.maximum(dst_nd, 0.0), np.maximum(dst_na, 0.0)


def _strip_degenerate_dims(src: np.ndarray,
                            dst: np.ndarray,
                            tol: float = 1e-10) -> tuple[np.ndarray, np.ndarray]:
    """Remove dimensions where src has near-zero variance.

    RBFInterpolator requires the monomial matrix to have full column rank.
    If all source points share the same x-coordinate (a 1D profile expressed
    as a 2D array), the x column is constant and the matrix is singular.
    Stripping those dimensions reduces the problem to its intrinsic dimensionality.

    Args:
        src: Source points, shape (N, D).
        dst: Destination points, shape (M, D). Must have same D.
        tol: Variance below this is considered degenerate.

    Returns:
        (src_active, dst_active): Arrays with degenerate columns removed.
        Shape is (N, D') and (M, D') where D' <= D.
    """
    variances = np.var(src, axis=0)
    active_dims = variances > tol
    if not np.any(active_dims):
        # Pathological case: all points identical. Keep first dim to avoid 0-D array.
        active_dims[0] = True
    return src[:, active_dims], dst[:, active_dims]


def _find_junction_nodes(points: np.ndarray, net_doping: np.ndarray,
                          neighbor_radius_factor: float = 2.0) -> np.ndarray:
    """Find nodes where net doping changes sign in their neighborhood."""
    from scipy.spatial import KDTree
    tree = KDTree(points)
    dists, _ = tree.query(points, k=2)
    radius = neighbor_radius_factor * np.median(dists[:, 1])
    is_pos = net_doping > 0
    junction_nodes = []
    for i in range(len(points)):
        idxs = tree.query_ball_point(points[i], radius)
        if len(idxs) >= 2:
            nb = is_pos[idxs]
            if nb.any() and (~nb).any():
                junction_nodes.append(i)
    return np.array(junction_nodes, dtype=int)


def _points_near_set(query: np.ndarray, refs: np.ndarray,
                      radius_um: float) -> np.ndarray:
    """Boolean mask: which query points are within radius_um of any ref."""
    if len(refs) == 0:
        return np.zeros(len(query), dtype=bool)
    from scipy.spatial import KDTree
    tree = KDTree(refs)
    near = tree.query_ball_point(query, radius_um)
    return np.array([len(n) > 0 for n in near], dtype=bool)