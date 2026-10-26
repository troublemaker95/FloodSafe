"""
test_algorithm.py - unit tests for FloodSafe's backtracking algorithm.
Run with:  python -m unittest -v
These tests never open the GUI. All grids are fixed, so results are deterministic.
"""

import unittest

from algorithm import (EMPTY, FLOOD, EXAMPLE_LAYOUT, EvacuationSolver,
                       InvalidMapError, make_empty_grid, parse_layout)


def grid_from(lines):
    """Helper: build (grid, start, shelter) from text. '#' flood, S start, H shelter."""
    return parse_layout(lines)


class RouteChecks(unittest.TestCase):
    """Base class with a helper that verifies a route is genuinely valid."""

    def assert_valid_route(self, grid, route, start, shelter):
        self.assertIsNotNone(route, "expected a route but got None")
        self.assertEqual(route[0], start)
        self.assertEqual(route[-1], shelter)
        self.assertEqual(len(route), len(set(route)), "route repeats a cell")
        for (r, c) in route:
            self.assertTrue(0 <= r < len(grid) and 0 <= c < len(grid[0]))
            self.assertNotEqual(grid[r][c], FLOOD, "route crosses a flooded cell")
        for (r1, c1), (r2, c2) in zip(route, route[1:]):
            self.assertEqual(abs(r1 - r2) + abs(c1 - c2), 1, "route has a jump")


class TestBacktracking(RouteChecks):

    def test_1_simple_valid_route(self):
        grid = make_empty_grid(5, 5)
        solver = EvacuationSolver(grid, (0, 0), (0, 3))
        route = solver.solve()
        self.assert_valid_route(grid, route, (0, 0), (0, 3))
        self.assertTrue(solver.success)
        self.assertEqual(route, [(0, 0), (0, 1), (0, 2), (0, 3)])  # fixed order: right

    def test_2_flood_forces_detour(self):
        grid, start, shelter = grid_from([
            "S.#..",
            "..#..",
            "..#.H",
            ".....",
        ])
        solver = EvacuationSolver(grid, start, shelter)
        route = solver.solve()
        self.assert_valid_route(grid, route, start, shelter)
        self.assertIn((3, 2), route)           # must pass through the only gap

    def test_3_unreachable_destination(self):
        grid, start, shelter = grid_from([
            "S....",
            ".###.",
            ".#H#.",
            ".###.",
            ".....",
        ])
        solver = EvacuationSolver(grid, start, shelter)
        self.assertIsNone(solver.solve())
        self.assertTrue(solver.finished)
        self.assertFalse(solver.success)
        self.assertEqual(solver.path, [])      # everything was undone

    def test_4_start_equals_destination(self):
        grid = make_empty_grid(4, 4)
        solver = EvacuationSolver(grid, (2, 2), (2, 2))
        self.assertEqual(solver.solve(), [(2, 2)])
        self.assertEqual(solver.backtracks, 0)
        self.assertEqual(solver.explored_nodes, 1)

    def test_5_no_traversable_route(self):
        # Everything is flooded except the start and the shelter.
        grid = [[FLOOD] * 5 for _ in range(5)]
        grid[0][0] = EMPTY
        grid[4][4] = EMPTY
        solver = EvacuationSolver(grid, (0, 0), (4, 4))
        self.assertIsNone(solver.solve())
        self.assertEqual(solver.explored_nodes, 1)
        self.assertEqual(solver.backtracks, 1)

    def test_6_dead_end_requires_backtracking(self):
        grid, start, shelter = grid_from([
            "..#..",
            "S###H",
            ".....",
        ])
        solver = EvacuationSolver(grid, start, shelter)
        route = solver.solve()
        self.assert_valid_route(grid, route, start, shelter)
        # The search first walks up into the pocket {(0,0),(0,1)} and must undo it.
        self.assertEqual(solver.backtracks, 2)
        self.assertNotIn((0, 0), route)
        self.assertEqual(len(route) - 1, 6)

    def test_7_invalid_or_missing_inputs(self):
        grid = make_empty_grid(5, 5)
        bad_cases = [
            (None, (4, 4)),          # no start
            ((0, 0), None),          # no shelter
            ((-1, 0), (4, 4)),       # start outside grid
            ((0, 0), (5, 5)),        # shelter outside grid
            ("ab", (4, 4)),          # wrong type
            ((0.5, 1), (4, 4)),      # non-integer coordinates
        ]
        for start, shelter in bad_cases:
            with self.subTest(start=start, shelter=shelter):
                with self.assertRaises(InvalidMapError):
                    EvacuationSolver(grid, start, shelter)
        flooded = make_empty_grid(3, 3)
        flooded[0][0] = FLOOD
        with self.assertRaises(InvalidMapError):
            EvacuationSolver(flooded, (0, 0), (2, 2))
        with self.assertRaises(InvalidMapError):
            EvacuationSolver([], (0, 0), (0, 0))
        with self.assertRaises(InvalidMapError):
            EvacuationSolver([[EMPTY, EMPTY], [EMPTY]], (0, 0), (0, 1))


class TestExtras(RouteChecks):

    def test_example_map_is_solvable_and_backtracks(self):
        grid, start, shelter = parse_layout(EXAMPLE_LAYOUT)
        solver = EvacuationSolver(grid, start, shelter)
        route = solver.solve()
        self.assert_valid_route(grid, route, start, shelter)
        self.assertGreater(solver.backtracks, 0)

    def test_open_15x15_unreachable_finishes_quickly(self):
        grid = make_empty_grid(15, 15)
        for c in (13, 14):                     # wall the shelter in the corner
            grid[13][c] = FLOOD
        grid[14][13] = FLOOD
        solver = EvacuationSolver(grid, (0, 0), (14, 14))
        self.assertIsNone(solver.solve())
        self.assertLessEqual(solver.explored_nodes, 15 * 15)

    def test_step_events_match_solve(self):
        grid, start, shelter = parse_layout(EXAMPLE_LAYOUT)
        stepper = EvacuationSolver(grid, start, shelter)
        events = list(stepper.steps())
        self.assertEqual(events[-1].kind, "found")
        self.assertEqual(sum(e.kind == "visit" for e in events), stepper.explored_nodes)
        self.assertEqual(sum(e.kind == "backtrack" for e in events), stepper.backtracks)
        self.assertEqual(stepper.route, EvacuationSolver(grid, start, shelter).solve())

    def test_solver_can_be_rerun_and_ignores_later_grid_edits(self):
        grid = make_empty_grid(4, 4)
        solver = EvacuationSolver(grid, (0, 0), (3, 3))
        first = solver.solve()
        grid[0][1] = FLOOD                     # caller edits grid afterwards
        second = solver.solve()                # solver kept its own copy
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
