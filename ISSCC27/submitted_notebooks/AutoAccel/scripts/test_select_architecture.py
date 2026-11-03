
import unittest

from select_architecture import select_architecture


class TestArchitectureSelector(unittest.TestCase):

    def test_conventional_wins_at_8_bits(self):
        row = {
            "width": 8,
            "conventional_cells": 404,
            "karatsuba_cells": 492,
        }
        winner, reduction = select_architecture(row)

        self.assertEqual(winner, "Conventional")
        self.assertAlmostEqual(reduction, 17.8862, places=3)

    def test_karatsuba_wins_at_16_bits(self):
        row = {
            "width": 16,
            "conventional_cells": 1903,
            "karatsuba_cells": 1685,
        }
        winner, reduction = select_architecture(row)

        self.assertEqual(winner, "Karatsuba")
        self.assertAlmostEqual(reduction, 11.4556, places=3)

    def test_karatsuba_wins_at_64_bits(self):
        row = {
            "width": 64,
            "conventional_cells": 34837,
            "karatsuba_cells": 21581,
        }
        winner, reduction = select_architecture(row)

        self.assertEqual(winner, "Karatsuba")
        self.assertGreater(reduction, 38.0)

    def test_equal_counts_produce_tie(self):
        row = {
            "width": 32,
            "conventional_cells": 1000,
            "karatsuba_cells": 1000,
        }
        winner, reduction = select_architecture(row)

        self.assertEqual(winner, "Tie")
        self.assertEqual(reduction, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
