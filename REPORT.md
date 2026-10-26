# FloodSafe — Flood Emergency Evacuation Planner

**Course:** Design and Analysis of Algorithms (DAA)  
**Student:** ______________________  **Roll No.:** ____________  **Date:** ____________

## Abstract

FloodSafe is an educational desktop application, written in Python with Tkinter, that finds a feasible evacuation route on a grid-based town map containing user-marked flooded cells. The route is found with a hand-written recursive backtracking algorithm that can be run instantly, stepped one event at a time, or animated. The application reports explored cells, backtracks, route length and execution time. It is a simulation only and must not be used for real evacuation decisions.

## Problem statement

Given an R × C grid with blocked (flooded) cells, a start cell and a shelter cell, find a path of adjacent cells (up, right, down, left) from start to shelter that avoids all flooded cells, or report that none exists.

## Objectives

- Implement recursive backtracking without BFS/Dijkstra/A* or third-party libraries.
- Visualise choosing, exploring, rejecting and backtracking.
- Keep the algorithm independent of the GUI and verify it with unit tests.
- Analyse time and space complexity.

## Algorithm and implementation

`algorithm.py` implements `EvacuationSolver._search(cell)`, a recursive generator. It (1) marks the cell visited and appends it to the current path, (2) checks for the shelter, (3) tries neighbours in the order up, right, down, left, rejecting cells that are outside the grid, flooded or visited, (4) recurses, and (5) if no neighbour succeeds, pops the cell from the path (backtrack). Separate state is kept for the current path, visited cells, the successful route, explored-node count, backtrack count and current cell. Each search event is yielded, so the GUI can run it fully (Find Route), one event per click (Step) or one event per `after()` tick (Animate). Animation uses a token so callbacks scheduled before a Pause or Reset are ignored.

Dead-end cells remain in the visited set after backtracking. This keeps the search to O(R × C) cell entries and lets an unreachable shelter be detected quickly; the route found is feasible but not necessarily shortest.

## Complexity analysis

- Enumerating all simple paths with only a current-path check is exponential in the worst case (loosely O(3^(R·C))).
- This implementation, seeking one feasible route with visited cells retained: time O(R × C).
- Space: visited set, path and recursion stack are each at most R × C, so O(R × C).

## Test cases and results

Command: `python -m unittest -v` (executed in the development environment on Python 3.12.3 / Linux; **re-run it on your Windows machine and update this section with your own output**).

| # | Test case | Result |
|---|---|---|
| 1 | Simple map with valid route | OK |
| 2 | Flood wall forces a detour | OK |
| 3 | Unreachable destination | OK |
| 4 | Start equals destination | OK |
| 5 | No traversable route | OK |
| 6 | Dead end requires backtracking | OK |
| 7 | Invalid / missing start and destination | OK |
| 8–11 | Example map, 15×15 unreachable, step events, rerun | OK |

Observed output: `Ran 11 tests ... OK`.  
On the built-in example map the algorithm found a 41-move route, explored 48 cells and backtracked 6 times.

The GUI was smoke-tested headlessly (Find Route, Step, Animate, Pause/Resume, Reset during animation, unreachable shelter, same-cell case). Please also check it manually on Windows 11.

### Screenshots (add your own)

- **[SCREENSHOT 1: Initial empty grid]**
- **[SCREENSHOT 2: Example map loaded]**
- **[SCREENSHOT 3: Animation in progress with dead ends in pink]**
- **[SCREENSHOT 4: Final route found]**
- **[SCREENSHOT 5: "No route exists" message]**

## Limitations

Manual flood marking only; no real-time data; feasible (not shortest or safest) route; equal cell costs and 4-direction movement; fixed 15 × 15 grid.

## Conclusion

FloodSafe demonstrates recursive backtracking — choose, explore, reject, undo — through an interactive and testable application. It also shows why pruning with visited cells matters: it turns an exponential path enumeration into a linear-time reachability search, while the result remains a feasible rather than optimal route.
