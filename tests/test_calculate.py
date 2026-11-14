import unittest
from calculate import (
    calc_op,
    calc_possession_plate,
    calc_distributions,
    extract_percent,
    get_level_folder,
    normalize_title,
    COMBO_BONUSES,
)
from sync import calc_single_rating, is_sega_maintenance, validate_clal_token


class TestCalculate(unittest.TestCase):
    def test_extract_percent(self):
        self.assertEqual(extract_percent(None), 0.0)
        self.assertEqual(extract_percent(100.5), 100.5)
        self.assertEqual(extract_percent(99), 99.0)
        self.assertEqual(extract_percent("100.8520%"), 100.852)
        self.assertEqual(extract_percent(" 97.5% "), 97.5)
        self.assertEqual(extract_percent("100.0"), 100.0)
        self.assertEqual(extract_percent(""), 0.0)
        self.assertEqual(extract_percent("invalid"), 0.0)

    def test_calc_op_unplayed_and_below_s(self):
        self.assertEqual(calc_op(False, "14.0", "AP+", "101.0%"), 0.0)
        self.assertEqual(calc_op(True, "14.0", None, "96.9999%"), 0.0)
        self.assertEqual(calc_op(True, "14.0", "AP+", "0%"), 0.0)

    def test_calc_op_known_spec_example(self):
        # Level 14.2 cleared with 100.8520%, FC+:
        # Base: 81.0 + Bonus: 0.75 + Score: 3.195 = 84.945 (rounds to 84.95 for display)
        op = calc_op(True, "14.2", "FC+", "100.8520%")
        self.assertEqual(op, 84.945)

    def test_calc_op_theoretical_max(self):
        # 101.0% with AP+ lamp reaches (level + 3.0) * 5.0
        level = 14.5
        expected_max = (level + 3.0) * 5.0
        op = calc_op(True, level, "AP+", "101.0%")
        self.assertEqual(op, expected_max)

    def test_calc_op_clamped_to_max(self):
        level = 13.0
        max_op = (level + 3.0) * 5.0
        op = calc_op(True, level, "AP+", "102.5%")
        self.assertEqual(op, max_op)

    def test_calc_op_tiers(self):
        level = 12.0
        # S: 97.0 <= score < 98.0
        self.assertEqual(calc_op(True, level, None, "97.0%"), level * 5.0)

        # S+: 98.0 <= score < 99.0
        self.assertEqual(calc_op(True, level, None, "98.0%"), (level + 0.5) * 5.0)

        # SS: 99.0 <= score < 99.5
        self.assertEqual(calc_op(True, level, None, "99.0%"), (level + 1.0) * 5.0)

        # SS+: 99.5 <= score < 100.0
        self.assertEqual(calc_op(True, level, None, "99.5%"), (level + 1.5) * 5.0)

        # SSS: 100.0
        self.assertEqual(calc_op(True, level, None, "100.0%"), (level + 2.0) * 5.0)

    def test_calc_possession_plate(self):
        # Rainbow (4)
        self.assertEqual(calc_possession_plate(99.0, 99.50), 4)
        self.assertEqual(calc_possession_plate(100.0, 99.80), 4)

        # Platinum (3)
        self.assertEqual(calc_possession_plate(98.0, 99.00), 3)
        self.assertEqual(calc_possession_plate(99.0, 99.10), 3)

        # Gold (2)
        self.assertEqual(calc_possession_plate(98.0, 97.50), 2)
        self.assertEqual(calc_possession_plate(99.5, 98.20), 2)

        # Silver (1)
        self.assertEqual(calc_possession_plate(97.0, 90.0), 1)
        self.assertEqual(calc_possession_plate(97.5, 50.0), 1)

        # None (0)
        self.assertEqual(calc_possession_plate(96.999, 99.9), 0)
        self.assertEqual(calc_possession_plate(0.0, 0.0), 0)

    def test_get_level_folder(self):
        self.assertEqual(get_level_folder("1"), "1")
        self.assertEqual(get_level_folder("6.7"), "6")  # Levels < 7 do not have +
        self.assertEqual(get_level_folder("7.0"), "7")
        self.assertEqual(get_level_folder("7.5"), "7")
        self.assertEqual(get_level_folder("7.6"), "7+")
        self.assertEqual(get_level_folder("13.0"), "13")
        self.assertEqual(get_level_folder("13.5"), "13")
        self.assertEqual(get_level_folder("13.6"), "13+")
        self.assertEqual(get_level_folder("13.7"), "13+")
        self.assertEqual(get_level_folder("14.9"), "14+")
        self.assertEqual(get_level_folder("15.0"), "15")

    def test_calc_single_rating(self):
        # Level 13.7, 100.9903% (SSS+): cap 100.5, coeff 22.4 -> floor(13.7 * 22.4 * 100.5 / 100) = 308
        self.assertEqual(calc_single_rating(13.7, 100.9903), 308)
        # Level 14.0, 100.5%: 14.0 * 22.4 * 1.005 = 315.168 -> 315
        self.assertEqual(calc_single_rating(14.0, 100.5), 315)
        # Level 12.0, 97.0% (S): 12.0 * 20.0 * 0.97 = 232.8 -> 232
        self.assertEqual(calc_single_rating(12.0, 97.0), 232)

    def test_normalize_title(self):
        self.assertEqual(normalize_title("  Link  "), "Link")
        self.assertEqual(normalize_title("Bad&#160;Apple!!"), "Bad Apple!!")
        self.assertEqual(normalize_title("D✪N’T  ST✪P"), "D✪N'T ST✪P")
        self.assertEqual(normalize_title(""), "\u200b")

    def test_calc_distributions(self):
        charts = [
            {"played": True, "percent": "100.6%", "lamp": "AP+"},
            {"played": True, "percent": "99.8%", "lamp": "FC+"},
            {"played": True, "percent": "97.2%", "lamp": None},
            {"played": False, "percent": "100.0%", "lamp": "AP"},
        ]
        ranks, lamps = calc_distributions(charts)
        self.assertEqual(ranks["SSS+"], 1)
        self.assertEqual(ranks["SSS"], 1)
        self.assertEqual(ranks["SS+"], 2)
        self.assertEqual(ranks["SS"], 2)
        self.assertEqual(ranks["S+"], 2)
        self.assertEqual(ranks["S"], 3)
        self.assertEqual(lamps["AP+"], 1)
        self.assertEqual(lamps["FC+"], 1)
        self.assertEqual(lamps["AP"], 0)
        self.assertEqual(lamps["FC"], 0)

    def test_validate_clal_token(self):
        valid = "a" * 64
        self.assertEqual(validate_clal_token(valid), valid)
        self.assertEqual(validate_clal_token(f"  {valid}  "), valid)

        # Wrong length
        with self.assertRaises(ValueError):
            validate_clal_token("a" * 63)
        with self.assertRaises(ValueError):
            validate_clal_token("a" * 65)

        # Invalid non-hex characters
        with self.assertRaises(ValueError):
            validate_clal_token("z" * 64)
        with self.assertRaises(ValueError):
            validate_clal_token("clal=" + "a" * 64)
        with self.assertRaises(ValueError):
            validate_clal_token("cookie; _t=123")


if __name__ == "__main__":
    unittest.main()
