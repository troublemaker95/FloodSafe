# FloodSafe — Flood Emergency Evacuation Planner

A desktop simulator (Python + Tkinter) that uses **recursive backtracking** to find a feasible route from a starting location to a safe shelter on a grid-based town map while avoiding flooded cells.

> ⚠️ **Disclaimer:** FloodSafe is an **educational simulation**. Flooded cells are marked manually, there is no real-time flood data, and the results must **never** be used for real emergency evacuation decisions.

## Problem statement

Given an R × C grid where some cells are flooded (blocked), a start cell and a shelter cell, find a sequence of adjacent cells (up/right/down/left) from the start to the shelter that never enters a flooded cell. If no such route exists, report that clearly.

## Motivation and real-world relevance

During floods, roads become impassable and evacuation routes must be re-planned quickly. Route planning on a map with blocked areas is a classic graph-search problem. This project demonstrates how backtracking explores choices, hits dead ends, undoes decisions and tries alternatives — in a visual way that is easy to explain in a DAA course.

## Features

- 15 × 15 interactive grid with Start, Shelter, Flooded, Explored, Current and Final-route cells
- Set Start / Set Shelter / Mark Flood (click or drag to toggle)
- **Find Route** (instant), **Step** (one search event), **Animate** (using Tkinter `after()`), **Pause/Resume**, speed slider
- Reset and **Generate Example** buttons
- Live statistics: explored cells, backtracks, route length, execution time
- Colour legend, status message area and event log
- Safe handling of edge cases (no start/shelter, same cell, unreachable shelter, reset during animation, repeated clicks)
- Algorithm separated from the GUI and covered by unit tests

## Technology stack

Python 3 (tested with 3.12), Tkinter, standard library only. No database, API keys, internet access or third-party packages.

## How the application works

`algorithm.py` contains `EvacuationSolver`, a **recursive generator**. Each time the search enters a cell, backtracks from a dead end, finds the shelter, or fails, it yields an event. The GUI (`main.py`) simply pulls events from this generator:

- **Find Route** consumes all events at once.
- **Step** consumes one event per click.
- **Animate** consumes one event per `root.after()` tick (the UI never freezes; no `time.sleep`).

All three modes therefore run the *same* algorithm.

## Install and run on Windows 11

1. Install Python 3 from <https://www.python.org/downloads/>. On the first installer screen tick **“Add python.exe to PATH”**. (Tkinter is included by default.)
2. Open the project folder in a terminal (PowerShell or the VS Code terminal) and run:

```powershell
python --version
python main.py
```

(If `python` is not found, try `py main.py`.)

Run the tests (no GUI opens):

```powershell
python -m unittest -v
```

## How to operate the GUI

1. Click **Generate Example** for a ready-made map, *or* build your own:
   - **Set Start**, then click a cell.
   - **Set Shelter**, then click a cell.
   - **Mark Flood**, then click or drag over cells to toggle flooding. Start and shelter cannot be flooded.
2. Press **Find Route**, **Step** or **Animate**. Use **Pause/Resume** while animating and the **Speed** slider to change the delay.
3. Editing the map after a search clears the old search results. **Reset** empties the grid and cancels any animation.

### Colour legend

| Colour | Meaning |
|---|---|
| Dark green “S” | Start |
| Orange “H” | Safe shelter |
| Dark blue | Flooded (blocked) |
| White/grey | Empty, traversable |
| Purple (outlined) | Cell currently being examined |
| Yellow | Explored, on the current path |
| Pink | Explored and rejected (dead end, backtracked) |
| Light green | Final route |

## Algorithm explanation

Neighbours are tried in a fixed order: **up, right, down, left**. For the current cell the algorithm:

1. Marks it as visited and adds it to the current path (*choose*).
2. If it is the shelter, saves the path as the route and stops (*goal test*).
3. For each neighbour in order, rejects it if it is outside the grid, flooded, or already visited; otherwise recurses (*explore*).
4. If no neighbour leads to the shelter, removes the cell from the path and returns (*undo / backtrack*).

A cell that was explored and rejected is **not** the same as a flooded cell: flooded cells are terrain (blue), rejected cells are search history (pink).

**Important design note.** Cells stay in the `visited` set even after backtracking. The current path is tracked separately and *is* undone. Without this, a plain "avoid cells on the current path" rule would try every simple path, which is exponential even on a small open grid and would make an unreachable shelter practically impossible to detect. Keeping dead ends marked is still backtracking, but limits the work for one feasible route to O(R × C) cell entries.

**The route is feasible, not necessarily the shortest** — it depends on the neighbour order. Shortest-path problems need BFS, Dijkstra or A\*, which are intentionally not used here.

### Pseudocode

```text
search(cell):
    visited.add(cell); path.append(cell); explored += 1
    if cell == shelter:
        route = copy(path); return True
    for (dr, dc) in [UP, RIGHT, DOWN, LEFT]:
        next = (cell.row + dr, cell.col + dc)
        if next is outside grid or flooded or in visited: continue
        if search(next): return True
    path.pop(); backtracks += 1        # undo the choice
    return False

solve(): return search(start)          # False => shelter unreachable
```

### Worked example

```text
row0:  . . # . .
row1:  S # # # H
row2:  . . . . .
```

Start (1,0), shelter (1,4).
1. Enter (1,0). Up (0,0) is valid → enter (0,0).
2. From (0,0): up is outside, right (0,1) is valid → enter (0,1).
3. From (0,1): up outside, right (0,2) flooded, down (1,1) flooded, left (0,0) visited → **dead end, backtrack** (1).
4. Back at (0,0): right done, down (1,0) visited, left outside → **backtrack** (2).
5. Back at (1,0): right (1,1) flooded; down (2,0) valid → continue along row 2 to (2,4), then up to (1,4) = shelter.

Result: route length 6 moves, 2 backtracks (verified by unit test 6).

## Complexity analysis

Let the grid have R rows and C columns, N = R × C.

- **Worst case, enumerating all simple paths:** the number of self-avoiding paths grows **exponentially** with N, so a backtracking search that only forbids cells on the *current* path has exponential worst-case time, roughly O(3^N) as a loose upper bound (≤ 3 new choices per step).
- **This implementation (finding one feasible route, visited cells kept):** each cell is entered at most once and each entry examines 4 neighbours, so time is **O(R × C)**.
- **Space:** the visited set, grid copy and current path are each at most R × C, and the recursion depth is at most R × C, so space is **O(R × C)**.

The exact complexity therefore depends on the search representation and on whether *all* paths or only *one feasible* path is sought.

## Limitations

- Prototype: flood areas are marked manually; no real map or live data.
- Finds a feasible route, not the shortest or safest one.
- Only 4-direction movement; every cell has equal cost; no flood depth/risk levels.
- Fixed 15 × 15 grid.

## Test cases and expected results

Run `python -m unittest -v`. All tests use fixed grids and no GUI.

| # | Test | Expected |
|---|---|---|
| 1 | Simple open map | Valid route `(0,0)→(0,3)` |
| 2 | Flood wall forces detour | Valid route via the only gap |
| 3 | Shelter enclosed by flood | No route; path fully undone |
| 4 | Start equals shelter | Route of one cell, 0 backtracks |
| 5 | All cells flooded except start and shelter | No route |
| 6 | Dead-end pocket | Valid route, 2 backtracks, 6 moves |
| 7 | Missing / invalid / flooded start or shelter, bad grid | `InvalidMapError` |
| extra | Example map, 15×15 unreachable, step events vs solve, rerun | pass |

## Project folder structure

```text
FloodSafe/
├── main.py             # Tkinter GUI
├── algorithm.py        # Backtracking logic (no GUI code)
├── test_algorithm.py   # Unit tests
├── README.md
├── REPORT.md
├── requirements.txt    # no third-party dependencies
└── .gitignore
```

## Future enhancements

- Weighted cells / flood depth and a shortest-path comparison (BFS, Dijkstra, A\*)
- Multiple shelters and moving flood simulation
- Adjustable grid size, save/load maps
- Diagonal movement and exporting screenshots

## License

Add a license of your choice (e.g. MIT) before publishing.
