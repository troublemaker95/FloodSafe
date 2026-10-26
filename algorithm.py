"""
algorithm.py - Core recursive backtracking logic for FloodSafe.

This module has NO dependency on Tkinter, so it can be unit-tested on its own.

The search is written as a *recursive generator*: every meaningful search
event ("visit", "backtrack", "found", "fail") is yielded to the caller.
  * The GUI can call next() once per click  -> "Step" button
  * The GUI can call next() from after()    -> "Animate" button
  * solve() simply drains the generator     -> "Find Route" button
All three use exactly the same algorithm.

NOTE: it finds a FEASIBLE route, not necessarily the SHORTEST one.
"""

import sys
from collections import namedtuple

# ---- Cell values stored in the grid (only terrain; search state is separate) ----
EMPTY = 0   # traversable
FLOOD = 1   # blocked

# Fixed neighbour order: up, right, down, left  as (row_change, col_change)
DIRECTIONS = [(-1, 0), (0, 1), (1, 0), (0, -1)]

# One search event. kind is "visit", "backtrack", "found" or "fail".
Event = namedtuple("Event", ["kind", "cell"])


class InvalidMapError(ValueError):
    """Raised when the grid, start or shelter is missing or invalid."""


def make_empty_grid(rows, cols):
    """Return a rows x cols grid with every cell traversable."""
    return [[EMPTY] * cols for _ in range(rows)]


# A predefined demo map: '.' empty, '#' flooded, 'S' start, 'H' shelter (15 x 15).
# The direct line to the shelter is blocked, and there are dead-end pockets.
EXAMPLE_LAYOUT = [
    "...............",
    ".......#.......",
    "......##.......",
    "..####.#.#####.",
    "......##.#.....",
    ".#####.#.#.###.",
    ".#.....#...#...",
    ".#S#####.###.#.",
    ".#.#.....#...#.",
    ".#.#.###.#.###.",
    "...#.#.#...#...",
    ".###.#.#####.#.",
    ".....#.......#H",
    ".#####.#######.",
    "...............",
]


def parse_layout(lines):
    """Convert a list of strings into (grid, start, shelter)."""
    grid, start, shelter = [], None, None
    for r, line in enumerate(lines):
        row = []
        for c, ch in enumerate(line):
            if ch == "#":
                row.append(FLOOD)
            else:
                row.append(EMPTY)
                if ch == "S":
                    start = (r, c)
                elif ch == "H":
                    shelter = (r, c)
        grid.append(row)
    return grid, start, shelter


class EvacuationSolver:
    """Recursive backtracking search from a start cell to a shelter cell."""

    def __init__(self, grid, start, shelter):
        self._validate(grid, start, shelter)
        self.grid = [list(row) for row in grid]      # private copy
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.start = tuple(start)
        self.shelter = tuple(shelter)
        # The search can go as deep as the number of cells, so make sure Python allows it.
        needed = self.rows * self.cols * 2 + 200
        if sys.getrecursionlimit() < needed:
            sys.setrecursionlimit(needed)
        self.reset_state()

    # ------------------------------------------------------------------ state
    def reset_state(self):
        """Clear all search state (separate pieces of state, as required)."""
        self.path = []             # cells on the CURRENT path (grows/shrinks)
        self.visited = set()       # every cell the search has ever entered
        self.route = None          # the successful route (copy of path) or None
        self.explored_nodes = 0    # number of cells entered
        self.backtracks = 0        # number of times we undid a path choice
        self.current = None        # cell currently being examined
        self.finished = False
        self.success = False

    # ------------------------------------------------------------- validation
    @staticmethod
    def _validate(grid, start, shelter):
        if not grid or not grid[0]:
            raise InvalidMapError("The grid is empty.")
        cols = len(grid[0])
        if any(len(row) != cols for row in grid):
            raise InvalidMapError("The grid rows must all have the same length.")
        rows = len(grid)
        for name, cell in (("start", start), ("shelter", shelter)):
            if cell is None:
                raise InvalidMapError("Please select a %s cell first." % name)
            try:
                r, c = cell
            except (TypeError, ValueError):
                raise InvalidMapError("The %s must be a (row, col) pair." % name)
            if not (isinstance(r, int) and isinstance(c, int)):
                raise InvalidMapError("The %s must use integer coordinates." % name)
            if not (0 <= r < rows and 0 <= c < cols):
                raise InvalidMapError("The %s is outside the grid." % name)
            if grid[r][c] == FLOOD:
                raise InvalidMapError("The %s is on a flooded cell." % name)

    # ---------------------------------------------------------------- helpers
    def _is_valid_move(self, cell):
        """A candidate is rejected if it is outside the grid, flooded, or visited."""
        r, c = cell
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return False
        if self.grid[r][c] == FLOOD:
            return False
        if cell in self.visited:
            return False
        return True

    # -------------------------------------------------------------- algorithm
    def _search(self, cell):
        """
        Recursive backtracking. Returns True if the shelter is reachable from `cell`.
        It is a generator, so it yields an Event at each meaningful step.
        """
        # 1. Choose: put this cell on the current path and mark it visited.
        self.visited.add(cell)
        self.path.append(cell)
        self.explored_nodes += 1
        self.current = cell
        yield Event("visit", cell)

        # 2. Goal test: have we reached the shelter?
        if cell == self.shelter:
            self.route = list(self.path)
            self.success = True
            self.finished = True
            yield Event("found", cell)
            return True

        # 3. Explore neighbours in the fixed order up, right, down, left.
        r, c = cell
        for dr, dc in DIRECTIONS:
            neighbour = (r + dr, c + dc)
            if not self._is_valid_move(neighbour):
                continue                                  # reject
            if (yield from self._search(neighbour)):      # recurse
                return True                               # propagate success upward

        # 4. Dead end: UNDO the choice (backtrack) and return to the previous cell.
        # The cell stays in `visited`: it is already proven useless, which stops the
        # search from re-exploring it and keeps the work at O(R x C) for one route.
        self.path.pop()
        self.backtracks += 1
        self.current = self.path[-1] if self.path else None
        yield Event("backtrack", cell)
        return False

    def steps(self):
        """Generator over all events of one complete search (resets state first)."""
        self.reset_state()
        found = yield from self._search(self.start)
        if not found:
            self.finished = True
            self.success = False
            yield Event("fail", self.start)

    def solve(self):
        """Run the whole search at once. Returns the route (list of cells) or None."""
        for _ in self.steps():
            pass
        return self.route
