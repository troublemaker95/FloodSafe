"""
main.py - FloodSafe GUI (Tkinter). Run with:  python main.py

All path-finding is done by algorithm.EvacuationSolver; this file only draws
the grid, handles clicks and drives the solver's event generator.
"""

import time
import tkinter as tk

from algorithm import (EMPTY, FLOOD, EXAMPLE_LAYOUT, EvacuationSolver,
                       InvalidMapError, make_empty_grid, parse_layout)

ROWS, COLS, CELL = 15, 15, 32
FONT = "Segoe UI"

# ------------------------------------------------------------------- colours
BG, PANEL, TEXT, MUTED = "#F1F5F9", "#FFFFFF", "#0F172A", "#64748B"
ACCENT, HEADER = "#2563EB", "#0F3D6B"
COLORS = {
    "empty": "#F8FAFC", "flood": "#1D4ED8", "start": "#16A34A", "shelter": "#EA580C",
    "current": "#A855F7", "path": "#FDE68A", "rejected": "#FCA5A5", "route": "#4ADE80",
}
LEGEND = [
    ("start", "Start (S)"), ("shelter", "Safe shelter (H)"),
    ("flood", "Flooded (blocked)"), ("empty", "Empty (free)"),
    ("current", "Current cell"), ("path", "Explored: on current path"),
    ("rejected", "Explored: dead end (rejected)"), ("route", "Final route"),
]

INSTRUCTIONS = (
    "1. Choose Set Start / Set Shelter / Mark Flood, then click the grid "
    "(Mark Flood: click or drag to toggle).\n"
    "2. Press Find Route (instant), Step (one event) or Animate.\n"
    "Tip: 'Generate Example' loads a ready-made map."
)


class FloodSafeApp:
    def __init__(self, root):
        self.root = root
        root.title("FloodSafe \u2014 Emergency Evacuation Planner")
        root.configure(bg=BG)
        root.resizable(False, False)

        # ---- map state
        self.grid = make_empty_grid(ROWS, COLS)
        self.start = None
        self.shelter = None
        self.mode = "flood"
        self.drag_value = None
        self.last_drag_cell = None

        # ---- search state
        self.solver = None          # EvacuationSolver for the current run
        self.stepper = None         # its event generator (None when no run is active)
        self.final_route = set()
        self.elapsed = 0.0          # seconds spent inside the algorithm

        # ---- animation state
        self.animating = False
        self.paused = False
        self.after_id = None
        self.token = 0              # bumped on every cancel; stale callbacks check it

        self.build_ui()
        self.set_mode("flood")
        self.render_all()
        self.update_stats()
        self.say("Welcome! Load the example map or build your own, then press Find Route.")

    # =================================================================== UI
    def build_ui(self):
        header = tk.Frame(self.root, bg=HEADER, padx=16, pady=10)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(header, text="\U0001F30A FloodSafe \u2014 Emergency Evacuation Planner",
                 bg=HEADER, fg="white", font=(FONT, 17, "bold")).pack(anchor="w")
        tk.Label(header, text="Find a feasible route to a safe shelter that avoids flooded "
                 "areas, using recursive backtracking.", bg=HEADER, fg="#BFDBFE",
                 font=(FONT, 10)).pack(anchor="w")

        # ---- left: grid + status
        left = tk.Frame(self.root, bg=BG, padx=12, pady=10)
        left.grid(row=1, column=0, sticky="n")
        self.canvas = tk.Canvas(left, width=COLS * CELL, height=ROWS * CELL, bg=PANEL,
                                highlightthickness=1, highlightbackground="#CBD5E1")
        self.canvas.pack()
        self.rects, self.texts = {}, {}
        for r in range(ROWS):
            for c in range(COLS):
                x, y = c * CELL, r * CELL
                self.rects[(r, c)] = self.canvas.create_rectangle(
                    x + 1, y + 1, x + CELL, y + CELL, outline="#E2E8F0")
                self.texts[(r, c)] = self.canvas.create_text(
                    x + CELL / 2 + 1, y + CELL / 2 + 1, text="", fill="white",
                    font=(FONT, 10, "bold"))
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        status = tk.LabelFrame(left, text=" Status ", bg=BG, fg=TEXT, font=(FONT, 9, "bold"))
        status.pack(fill="x", pady=(8, 0))
        self.status_var = tk.StringVar()
        tk.Label(status, textvariable=self.status_var, bg=BG, fg=ACCENT, anchor="w",
                 justify="left", wraplength=COLS * CELL - 20,
                 font=(FONT, 10, "bold")).pack(fill="x", padx=6, pady=(4, 2))
        log_frame = tk.Frame(status, bg=BG)
        log_frame.pack(fill="x", padx=6, pady=(0, 6))
        self.log = tk.Text(log_frame, height=5, width=60, bg=PANEL, fg=TEXT, relief="flat",
                           font=("Consolas", 9), state="disabled", wrap="word")
        scroll = tk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="x", expand=True)

        # ---- right: controls
        right = tk.Frame(self.root, bg=BG, padx=4, pady=10)
        right.grid(row=1, column=1, sticky="n", padx=(0, 12))

        how = tk.LabelFrame(right, text=" How to use ", bg=BG, fg=TEXT, font=(FONT, 9, "bold"))
        how.pack(fill="x")
        tk.Label(how, text=INSTRUCTIONS, bg=BG, fg=MUTED, justify="left", wraplength=300,
                 font=(FONT, 9)).pack(padx=6, pady=4, anchor="w")

        edit = tk.LabelFrame(right, text=" Edit map ", bg=BG, fg=TEXT, font=(FONT, 9, "bold"))
        edit.pack(fill="x", pady=(8, 0))
        row = tk.Frame(edit, bg=BG)
        row.pack(fill="x", padx=6, pady=4)
        self.mode_buttons = {}
        for key, label in (("start", "Set Start"), ("shelter", "Set Shelter"),
                           ("flood", "Mark Flood")):
            b = tk.Button(row, text=label, width=10, relief="raised", font=(FONT, 9),
                          command=lambda k=key: self.set_mode(k))
            b.pack(side="left", padx=2)
            self.mode_buttons[key] = b
        row2 = tk.Frame(edit, bg=BG)
        row2.pack(fill="x", padx=6, pady=(0, 6))
        self.button(row2, "Generate Example", self.load_example, "#0EA5E9").pack(
            side="left", expand=True, fill="x", padx=2)
        self.button(row2, "Reset", self.reset_all, "#64748B").pack(
            side="left", expand=True, fill="x", padx=2)

        run = tk.LabelFrame(right, text=" Run algorithm ", bg=BG, fg=TEXT,
                            font=(FONT, 9, "bold"))
        run.pack(fill="x", pady=(8, 0))
        r1 = tk.Frame(run, bg=BG)
        r1.pack(fill="x", padx=6, pady=(4, 2))
        self.button(r1, "Find Route", self.find_route, ACCENT).pack(
            side="left", expand=True, fill="x", padx=2)
        self.button(r1, "Step", self.step, "#7C3AED").pack(
            side="left", expand=True, fill="x", padx=2)
        r2 = tk.Frame(run, bg=BG)
        r2.pack(fill="x", padx=6, pady=2)
        self.button(r2, "Animate", self.animate, "#059669").pack(
            side="left", expand=True, fill="x", padx=2)
        self.pause_btn = self.button(r2, "Pause", self.toggle_pause, "#D97706")
        self.pause_btn.pack(side="left", expand=True, fill="x", padx=2)
        r3 = tk.Frame(run, bg=BG)
        r3.pack(fill="x", padx=6, pady=(2, 6))
        tk.Label(r3, text="Speed:", bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="left")
        self.delay = tk.IntVar(value=120)
        tk.Scale(r3, from_=400, to=10, orient="horizontal", variable=self.delay,
                 showvalue=False, bg=BG, highlightthickness=0, length=200).pack(
            side="left", padx=4)
        tk.Label(r3, text="slow \u2192 fast", bg=BG, fg=MUTED, font=(FONT, 8)).pack(side="left")

        legend = tk.LabelFrame(right, text=" Legend ", bg=BG, fg=TEXT, font=(FONT, 9, "bold"))
        legend.pack(fill="x", pady=(8, 0))
        for i, (key, label) in enumerate(LEGEND):
            tk.Label(legend, bg=COLORS[key], width=2, relief="solid", bd=1).grid(
                row=i, column=0, padx=(6, 4), pady=1)
            tk.Label(legend, text=label, bg=BG, fg=TEXT, font=(FONT, 9), anchor="w").grid(
                row=i, column=1, sticky="w")

        stats = tk.LabelFrame(right, text=" Statistics ", bg=BG, fg=TEXT,
                              font=(FONT, 9, "bold"))
        stats.pack(fill="x", pady=(8, 0))
        self.stat_vars = {}
        for i, name in enumerate(("Explored cells", "Backtracks", "Route length (moves)",
                                  "Execution time")):
            tk.Label(stats, text=name + ":", bg=BG, fg=MUTED, font=(FONT, 9)).grid(
                row=i, column=0, sticky="w", padx=6)
            var = tk.StringVar(value="-")
            tk.Label(stats, textvariable=var, bg=BG, fg=TEXT,
                     font=(FONT, 9, "bold")).grid(row=i, column=1, sticky="e", padx=6)
            self.stat_vars[name] = var
        stats.columnconfigure(1, weight=1)

        # ---- footer disclaimer
        tk.Label(self.root, bg="#FEF3C7", fg="#92400E", font=(FONT, 9), pady=6,
                 wraplength=COLS * CELL + 320, justify="center",
                 text="\u26A0 Educational simulation only. Flooded cells are marked manually; "
                      "results are NOT real flood data and must not be used for real evacuation "
                      "decisions. The route found is feasible, not necessarily the shortest."
                 ).grid(row=2, column=0, columnspan=2, sticky="ew")

        self.update_buttons()

    @staticmethod
    def button(parent, text, command, color):
        return tk.Button(parent, text=text, command=command, bg=color, fg="white",
                         activebackground=color, activeforeground="white",
                         font=(FONT, 10, "bold"), relief="flat", padx=8, pady=4,
                         cursor="hand2")

    # ============================================================== messages
    def say(self, message):
        """Update the headline status and append it to the log."""
        self.status_var.set(message)
        self.log_line(message)

    def log_line(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 300:    # keep the log short
            self.log.delete("1.0", "50.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def update_stats(self):
        s = self.solver
        if s is None:
            for var in self.stat_vars.values():
                var.set("-")
            return
        self.stat_vars["Explored cells"].set(str(s.explored_nodes))
        self.stat_vars["Backtracks"].set(str(s.backtracks))
        self.stat_vars["Route length (moves)"].set(
            str(len(s.route) - 1) if s.route else "-")
        self.stat_vars["Execution time"].set("%.3f ms" % (self.elapsed * 1000))

    def update_buttons(self):
        self.pause_btn.configure(text="Resume" if self.paused else "Pause",
                                 state="normal" if self.animating else "disabled")

    # ================================================================ drawing
    def render_all(self):
        for r in range(ROWS):
            for c in range(COLS):
                self.render_cell((r, c))

    def render_cell(self, cell):
        """Pick a colour by priority: start/shelter > route > flood > search state."""
        s = self.solver
        is_start, is_shelter = cell == self.start, cell == self.shelter
        is_current = (s is not None and not s.finished and cell == s.current)
        text = ""
        if is_start and is_shelter:
            key, text = "start", "S/H"
        elif is_start:
            key, text = "start", "S"
        elif is_shelter:
            key, text = "shelter", "H"
        elif is_current:
            key = "current"
        elif cell in self.final_route:
            key = "route"
        elif self.grid[cell[0]][cell[1]] == FLOOD:
            key = "flood"
        elif s is not None and cell in s.path:
            key = "path"
        elif s is not None and cell in s.visited:
            key = "rejected"
        else:
            key = "empty"
        self.canvas.itemconfigure(self.rects[cell], fill=COLORS[key],
                                  outline="#A855F7" if is_current else "#E2E8F0",
                                  width=3 if is_current else 1)
        self.canvas.itemconfigure(self.texts[cell], text=text)
        if is_current:
            self.canvas.tag_raise(self.rects[cell])
            self.canvas.tag_raise(self.texts[cell])

    # ============================================================= map editing
    def set_mode(self, mode):
        self.mode = mode
        for key, b in self.mode_buttons.items():
            b.configure(bg=ACCENT if key == mode else "#E2E8F0",
                        fg="white" if key == mode else TEXT)

    def cell_at(self, event):
        c, r = event.x // CELL, event.y // CELL
        return (r, c) if 0 <= r < ROWS and 0 <= c < COLS else None

    def on_press(self, event):
        cell = self.cell_at(event)
        if cell is None:
            return
        r, c = cell
        if self.mode == "start":
            if self.grid[r][c] == FLOOD:
                self.say("Cannot place the start on a flooded cell. Unmark the flood first.")
                return
            self.clear_search()
            self.start = cell
            self.refresh_cells()
            self.say("Start set at row %d, column %d." % (r, c))
        elif self.mode == "shelter":
            if self.grid[r][c] == FLOOD:
                self.say("Cannot place the shelter on a flooded cell. Unmark the flood first.")
                return
            self.clear_search()
            self.shelter = cell
            self.refresh_cells()
            self.say("Shelter set at row %d, column %d." % (r, c))
        else:                                       # flood mode: toggle, then paint on drag
            if cell in (self.start, self.shelter):
                self.say("The start and shelter cells cannot be flooded.")
                self.drag_value = None
                return
            self.drag_value = EMPTY if self.grid[r][c] == FLOOD else FLOOD
            self.paint_flood(cell)

    def on_drag(self, event):
        if self.mode != "flood" or self.drag_value is None:
            return
        cell = self.cell_at(event)
        if cell is not None and cell != self.last_drag_cell:
            self.paint_flood(cell)

    def on_release(self, _event):
        self.drag_value = None
        self.last_drag_cell = None

    def paint_flood(self, cell):
        self.last_drag_cell = cell
        if cell in (self.start, self.shelter):
            return                                  # never flood start/shelter
        r, c = cell
        if self.grid[r][c] != self.drag_value:
            self.clear_search()                     # old results no longer match the map
            self.grid[r][c] = self.drag_value
            self.render_cell(cell)

    def refresh_cells(self):
        self.render_all()

    def load_example(self):
        self.clear_search()
        self.grid, self.start, self.shelter = parse_layout(EXAMPLE_LAYOUT)
        self.render_all()
        self.say("Example map loaded. Try Find Route, Step or Animate.")

    def reset_all(self):
        self.clear_search()
        self.grid = make_empty_grid(ROWS, COLS)
        self.start = self.shelter = None
        self.render_all()
        self.update_stats()
        self.say("Reset. The grid is empty - set a start, a shelter and some flooded cells.")

    # ============================================================ search control
    def cancel_animation(self):
        """Stop any animation and invalidate callbacks that are already scheduled."""
        self.token += 1
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.animating = False
        self.paused = False
        self.update_buttons()

    def clear_search(self):
        """Forget the current run (keeps the map)."""
        self.cancel_animation()
        self.solver = None
        self.stepper = None
        self.final_route = set()
        self.elapsed = 0.0
        self.render_all()
        self.update_stats()

    def prepare_solver(self):
        """Create a fresh solver from the current map. Returns False if input is invalid."""
        try:
            self.solver = EvacuationSolver(self.grid, self.start, self.shelter)
        except InvalidMapError as error:
            self.solver = None
            self.say("Cannot search: %s" % error)
            return False
        self.stepper = self.solver.steps()
        self.final_route = set()
        self.elapsed = 0.0
        self.render_all()
        self.update_stats()
        return True

    def advance(self, quiet=False):
        """Run ONE search event. Returns True while the search should continue."""
        t0 = time.perf_counter()
        try:
            event = next(self.stepper)
        except StopIteration:
            event = None
        self.elapsed += time.perf_counter() - t0
        if event is None:
            self.finish()
            return False
        if event.kind in ("found", "fail"):
            self.finish()
            return False
        if not quiet:
            r, c = event.cell
            if event.kind == "visit":
                self.log_line("Exploring (%d,%d); path length %d" % (r, c, len(self.solver.path)))
                self.status_var.set("Exploring cell (%d, %d)" % (r, c))
            else:
                self.log_line("Dead end at (%d,%d); backtracking" % (r, c))
                self.status_var.set("Dead end at (%d, %d) - backtracking" % (r, c))
            self.render_all()
            self.update_stats()
        return True

    def finish(self):
        s = self.solver
        self.stepper = None
        self.animating = False
        self.paused = False
        self.token += 1
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if s.success:
            self.final_route = set(s.route)
            moves = len(s.route) - 1
            if moves == 0:
                self.say("Start and shelter are the same cell: route length 0.")
            else:
                self.say("Route found: %d moves (feasible, not necessarily shortest)." % moves)
        else:
            self.say("No route exists: the shelter is unreachable from the start "
                     "(%d cells explored)." % s.explored_nodes)
        self.render_all()
        self.update_stats()
        self.update_buttons()

    def find_route(self):
        self.clear_search()
        if not self.prepare_solver():
            return
        while self.stepper is not None:
            self.advance(quiet=True)

    def step(self):
        if self.animating and not self.paused:
            self.say("An animation is running. Press Pause before stepping.")
            return
        if self.stepper is None:                    # start a new run
            self.clear_search()
            if not self.prepare_solver():
                return
            self.say("Step mode: press Step to advance one search event.")
        self.advance()

    def animate(self):
        if self.animating:
            if self.paused:
                self.toggle_pause()                 # Animate while paused = resume
            return                                  # already running: ignore (no duplicates)
        if self.stepper is None:                    # nothing in progress: start fresh
            self.clear_search()
            if not self.prepare_solver():
                return
        self.animating, self.paused = True, False
        self.token += 1
        self.update_buttons()
        self.schedule_tick()

    def schedule_tick(self):
        self.after_id = self.root.after(self.delay.get(), self.tick, self.token)

    def tick(self, token):
        if token != self.token or not self.animating or self.paused:
            return                                  # stale callback: do nothing
        self.after_id = None
        if self.advance():
            self.schedule_tick()

    def toggle_pause(self):
        if not self.animating:
            return
        if self.paused:
            self.paused = False
            self.say("Animation resumed.")
            self.schedule_tick()
        else:
            self.paused = True
            self.token += 1
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            self.say("Animation paused. Press Resume, or use Step.")
        self.update_buttons()


def main():
    root = tk.Tk()
    FloodSafeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
