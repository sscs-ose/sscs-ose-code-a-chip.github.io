"""
Common-Centroid Matrix Placement and Gradient Cancellation Engine
Implements Linear (1st-Order) and Quadratic (2nd-Order) Process Gradient Cancellation.
Author: NeuroDyn-AFE Team (IEEE SSCS Code-a-Chip ISSCC 2027)
"""

import numpy as np
from typing import List, Tuple, Dict, Any

class CommonCentroidPlacer:
    """
    Generates and verifies common-centroid device placement patterns.
    Guarantees zero centroid displacement (delta_x = 0, delta_y = 0) and zero
    quadratic moment displacement (delta_M2 = 0) between matched transistor pairs (M1/M2).
    """
    def __init__(self, rows: int = 1, cols: int = 8):
        self.rows = rows
        self.cols = cols

    def generate_optimal_2nd_order_centroid(self) -> np.ndarray:
        """
        Optimal 2nd-order common-centroid sequence for 8 active fingers (4 for A, 4 for B):
        Pattern: [A, B, B, A, B, A, A, B]
        Properties:
          - A indices: {0, 3, 5, 6} -> sum = 14, sum(x^2) = 0 + 9 + 25 + 36 = 70
          - B indices: {1, 2, 4, 7} -> sum = 14, sum(x^2) = 1 + 4 + 16 + 49 = 70
          - Linear gradient error: Delta_M1 = 14 - 14 = 0 (EXACT)
          - Quadratic gradient error: Delta_M2 = 70 - 70 = 0 (EXACT)
        Cancels both linear wafer tilts and radial thermal/packaging stresses!
        """
        return np.array(['A', 'B', 'B', 'A', 'B', 'A', 'A', 'B'])

    def generate_cross_quad_pattern(self) -> np.ndarray:
        """
        Standard 2D cross-quad 2x2 matrix:
        [[A, B],
         [B, A]]
        Centroid A = (0.5, 0.5), Centroid B = (0.5, 0.5). Exact match!
        """
        return np.array([['A', 'B'], ['B', 'A']])

    def generate_interdigitated_centroid(self, n_fingers_per_dev: int = 4) -> np.ndarray:
        """
        Generates 2 x (2 * n_fingers) common-centroid array:
        Row 0: [A, B, B, A, B, A, A, B ...]
        Row 1: [B, A, A, B, A, B, B, A ...]
        """
        unit_row0 = ['A', 'B', 'B', 'A', 'B', 'A', 'A', 'B']
        unit_row1 = ['B', 'A', 'A', 'B', 'A', 'B', 'B', 'A']
        repeats = max(1, n_fingers_per_dev // 4)
        
        row0 = unit_row0 * repeats
        row1 = unit_row1 * repeats
        return np.array([row0, row1])

    def verify_centroid_cancellation(self, matrix: np.ndarray) -> Dict[str, Any]:
        """
        Calculates 1st-order centroids and 2nd-order quadratic moments of devices A and B.
        Evaluates linear gradient error (G1) and quadratic curvature error (G2).
        """
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
            
        rows, cols = matrix.shape
        coords_A = []
        coords_B = []
        
        for r in range(rows):
            for c in range(cols):
                if matrix[r, c] == 'A':
                    coords_A.append((c, r))
                elif matrix[r, c] == 'B':
                    coords_B.append((c, r))
                    
        coords_A = np.array(coords_A, dtype=float)
        coords_B = np.array(coords_B, dtype=float)
        
        centroid_A = np.mean(coords_A, axis=0)
        centroid_B = np.mean(coords_B, axis=0)
        
        disp_1st = np.linalg.norm(centroid_A - centroid_B)
        
        # 2nd-order moment calculation along X axis (M2 = sum(x^2) / N)
        m2_A = np.mean(coords_A[:, 0] ** 2)
        m2_B = np.mean(coords_B[:, 0] ** 2)
        disp_2nd = np.abs(m2_A - m2_B)
        
        gradient_x = 1.0  # arbitrary unit/um
        error_cc = np.abs((centroid_A[0] - centroid_B[0]) * gradient_x)
        error_worst = (cols / 2.0) * gradient_x
        suppression_db = 20.0 * np.log10(error_worst / max(error_cc, 1e-9))
        
        return {
            "pattern": matrix.tolist() if rows > 1 else matrix.flatten().tolist(),
            "centroid_A": centroid_A.tolist(),
            "centroid_B": centroid_B.tolist(),
            "centroid_displacement_1st": disp_1st,
            "quadratic_moment_displacement_2nd": disp_2nd,
            "linear_suppression_dB": suppression_db,
            "is_perfect_1st_order": bool(disp_1st < 1e-6),
            "is_perfect_2nd_order": bool(disp_2nd < 1e-6)
        }

    def wrap_with_dummies(self, pattern_1d: np.ndarray) -> np.ndarray:
        """
        Surrounds the 1D active pattern with dummy transistors ('D') on both flanks
        to guarantee uniform optical proximity correction (OPC) and plasma etch environments.
        """
        if pattern_1d.ndim > 1:
            rows, cols = pattern_1d.shape
            dummy_matrix = np.full((rows + 2, cols + 2), 'D', dtype=object)
            dummy_matrix[1:-1, 1:-1] = pattern_1d
            return dummy_matrix
        else:
            return np.concatenate((['D'], pattern_1d, ['D']))
