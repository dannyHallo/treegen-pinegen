import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import math
import struct
import random
import subprocess
import platform
import os
import sys

GRID = 256

def clamp(v, mi, ma):
    return max(mi, min(ma, v))

def resource_path(filename):
    """Get path to resource for PyInstaller --onefile"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return filename

def load_palette_png(filename):
    path = resource_path(filename)
    image = Image.open(path).convert("RGBA")
    pixels = list(image.getdata())
    if len(pixels) != 256:
        raise ValueError("Palette must be exactly 256 pixels wide")
    return pixels

TREE_PALETTE_MAP = {
    "tree_default.png": {"leaves": [9, 17], "trunk": [57, 65]},
    "tree_basic.png":   {"leaves": list(range(9, 17)), "trunk": list(range(57, 65))},
    "autumn.png":       {"leaves": list(range(9, 17)), "trunk": list(range(57, 65))},
    "birch.png":        {"leaves": list(range(9, 17)), "trunk": list(range(57, 65))},
    "blossom.png":      {"leaves": list(range(9, 25)), "trunk": list(range(57, 65))},
    "dead.png":         {"leaves": list(range(9, 17)), "trunk": list(range(57, 65))},
    "oak1.png":         {"leaves": list(range(9, 17)), "trunk": list(range(65, 73))},
    "oak2.png":         {"leaves": list(range(9, 17)), "trunk": list(range(57, 65))},
    "tree_sapling.png": {"leaves": list(range(9, 17)), "trunk": list(range(57, 65))}
}

def generate_treegen_tree(params, palette_name):
    random.seed(params['seed'])

    palette_path = resource_path(os.path.join("palettes", palette_name))
    palette = load_palette_png(palette_path)
    palette_key = os.path.basename(palette_name)
    palette_config = TREE_PALETTE_MAP.get(palette_key, TREE_PALETTE_MAP["tree_default.png"])
    leaf_indices = palette_config["leaves"]
    trunk_indices = palette_config["trunk"]

    voxels = np.zeros((GRID, GRID, GRID), dtype=np.uint8)
    gLeaves = []

    size = 150 * params['size'] / params['iterations']
    gTrunkSize = params['trunksize'] * params['size'] * 6
    wide = min(params['wide'], 0.95)
    gBranchLength0 = size * (1 - wide)
    gBranchLength1 = size * wide

    def normalize(x, y, z):
        l = math.sqrt(x*x + y*y + z*z)
        return (x/l, y/l, z/l) if l > 0 else (0, 0, 1)

    trunk_voxels = []

    def draw_line(x0, y0, z0, x1, y1, z1, r0, r1):
        steps = int(math.dist([x0, y0, z0], [x1, y1, z1]) * 2)
        for i in range(steps + 1):
            t = i / steps
            x = x0 + t * (x1 - x0)
            y = y0 + t * (y1 - y0)
            z = z0 + t * (z1 - z0)
            r = r0 + t * (r1 - r0)
            for dx in range(-math.ceil(r), math.ceil(r)+1):
                for dy in range(-math.ceil(r), math.ceil(r)+1):
                    for dz in range(-math.ceil(r), math.ceil(r)+1):
                        if dx*dx + dy*dy + dz*dz <= r*r:
                            vx = int(x+dx)
                            vy = int(y+dy)
                            vz = int(z+dz)
                            if 0 <= vx < GRID and 0 <= vy < GRID and 0 <= vz < GRID:
                                trunk_voxels.append((vx, vy, vz))

    def get_branch_length(i):
        t = math.sqrt(i / params['iterations'])
        return gBranchLength0 + t * (gBranchLength1 - gBranchLength0)

    def get_branch_size(i):
        t = math.sqrt(i / params['iterations'])
        return (1 - t) * gTrunkSize

    def get_branch_angle(i):
        t = math.sqrt(i / params['iterations'])
        return 2.0 * params['spread'] * t

    def get_branch_prob(i):
        return math.sqrt(i / params['iterations'])

    def branches(x, y, z, dx, dy, dz, i):
        l = get_branch_length(i)
        s0 = get_branch_size(i)
        s1 = get_branch_size(i+1)
        x1 = x + dx * l
        y1 = y + dy * l
        z1 = z + dz * l
        draw_line(x, y, z, x1, y1, z1, s0, s1)

        if i < (params['iterations'] - 1):
            b = 1
            var = i * 0.2 * params['twisted']
            if random.random() < get_branch_prob(i):
                b = 2
                var = get_branch_angle(i)
            for _ in range(b):
                dx2 = dx + random.uniform(-var, var)
                dy2 = dy + random.uniform(-var, var)
                dz2 = dz + random.uniform(-var, var)
                dx2, dy2, dz2 = normalize(dx2, dy2, dz2)
                branches(x1, y1, z1, dx2, dy2, dz2, i + 1)
        else:
            gLeaves.append((x1, y1, z1))
            gLeaves.append(((x + x1)/2, (y + y1)/2, (z + z1)/2))

    leaf_voxels = []

    def add_leaves():
        for pos in gLeaves:
            x1, y1, z1 = map(int, pos)
            for _ in range(int(5 * params['leaves'])):
                x2, y2, z2 = x1, y1, z1
                for _ in range(int(50 * params['leaves'])):
                    leaf_voxels.append((x2, y2, z2))
                    d = random.randint(1, 6)
                    if d == 1: x2 -= 1
                    elif d == 2: x2 += 1
                    elif d in (3, 4):
                        z2 += 1 if random.uniform(-1, 1) < params['gravity'] else -1
                    elif d == 5: y2 -= 1
                    else: y2 += 1

        random.shuffle(leaf_voxels)
        for i, (x, y, z) in enumerate(leaf_voxels):
            idx = leaf_indices[i % len(leaf_indices)]
            if 0 <= x < GRID and 0 <= y < GRID and 0 <= z < GRID:
                if voxels[x, y, z] == 0:
                    voxels[x, y, z] = idx

    branches(GRID//2, GRID//2, 0, 0, 0, 1, 0)
    add_leaves()

    # for simplicity, only use the first color from the palette
    for _, (x, y, z) in enumerate(trunk_voxels):
        voxels[x, y, z] = trunk_indices[0]

    voxel_data = bytearray()
    for x in range(GRID):
        for y in range(GRID):
            for z in range(GRID):
                c = voxels[x, y, z]
                if c > 0:
                    voxel_data += struct.pack('<4B', x, y, z, c)

    size_chunk = b'SIZE' + struct.pack('<ii', 12, 0)
    size_chunk += struct.pack('<iii', GRID, GRID, GRID)

    xyzi_payload = struct.pack('<i', len(voxel_data) // 4) + voxel_data
    xyzi_chunk = b'XYZI' + struct.pack('<ii', len(xyzi_payload), 0) + xyzi_payload

    rgba_payload = b''.join(struct.pack('<4B', *color) for color in palette)
    rgba_chunk = b'RGBA' + struct.pack('<ii', len(rgba_payload), 0) + rgba_payload

    main_content = size_chunk + xyzi_chunk + rgba_chunk
    main_chunk = b'MAIN' + struct.pack('<ii', 0, len(main_content)) + main_content
    vox_file = b'VOX ' + struct.pack('<i', 150) + main_chunk

    counter_file = "treegen_counter.txt"
    if os.path.exists(counter_file):
        with open(counter_file, "r") as f:
            try:
                current = int(f.read().strip())
            except ValueError:
                current = 1
    else:
        current = 1

    output_dir = os.path.join("output", "tree")
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"treegen_output{current}.vox")

    with open(filename, "wb") as f:
        f.write(vox_file)

    with open(counter_file, "w") as f:
        f.write(str(current + 1))

    return filename

def build_treegen_gui(tab):
    # === Branding Image
    try:
        img = Image.open(resource_path("treegen_brand.png"))
        img.thumbnail((650, 200))
        img_tk = ImageTk.PhotoImage(img)
        label = ttk.Label(tab, image=img_tk)
        label.image = img_tk
        label.pack(pady=(0, 10))
    except:
        pass

    ttk.Label(tab, text="Treegen v1.3 🌳 by NGNT", font=("Arial", 14, "bold")).pack()

    # === Palette dropdown
    tree_palette_path = resource_path("palettes/tree")
    palette_files = [f for f in os.listdir(tree_palette_path) if f.endswith(".png")]
    palette_var = tk.StringVar(value=palette_files[0])
    palette_row = ttk.Frame(tab)
    palette_row.pack(fill="x", pady=4)
    ttk.Label(palette_row, text="Palette").pack(side="left", padx=(0, 5))
    palette_dropdown = ttk.Combobox(palette_row, textvariable=palette_var, values=palette_files, state="readonly")
    palette_dropdown.pack(fill="x", expand=True)

    # === Sliders
    controls = {
        "size":        tk.DoubleVar(value=1.6),
        "trunksize":   tk.DoubleVar(value=1.0),
        "spread":      tk.DoubleVar(value=0.5),
        "twisted":     tk.DoubleVar(value=0.5),
        "leaves":      tk.DoubleVar(value=1.0),
        "gravity":     tk.DoubleVar(value=0.0),
        "iterations":  tk.IntVar(value=12),
        "wide":        tk.DoubleVar(value=0.5),
        "seed":        tk.IntVar(value=1),
        "open_after":  tk.BooleanVar(value=True),
        "status":      tk.StringVar(value="Ready")
    }

    slider_defs = [
        ("Size", controls["size"], 0.1, 3.0),
        ("Trunk Size", controls["trunksize"], 0.1, 3.0),
        ("Spread", controls["spread"], 0.0, 1.0),
        ("Twist", controls["twisted"], 0.0, 1.0),
        ("Leafiness", controls["leaves"], 0.0, 3.0),
        ("Gravity", controls["gravity"], -1.0, 1.0),
        ("Iterations", controls["iterations"], 5, 15),
        ("Wide", controls["wide"], 0.0, 1.0),
        ("Seed", controls["seed"], 1, 9999)
    ]

    tree_tooltips = {
        "Size": "Controls overall height/scale of the tree",
        "Trunk Size": "How thick the trunk appears",
        "Spread": "How much branches spread out sideways",
        "Twist": "How twisted or chaotic the branches are",
        "Leafiness": "Controls how many leaves spawn",
        "Gravity": "Positive pulls leaves up, negative pulls down",
        "Iterations": "How complex/tall the tree structure is",
        "Wide": "Controls base vs top branch bias (0 = base, 1 = top)",
        "Seed": "Seed for randomness — same number = same tree"
    }

    defaults = {label: var.get() for label, var, *_ in slider_defs}

    for label, var, mn, mx in slider_defs:
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=4)

        ttk.Label(row, text=label).pack(side="left", padx=(0, 5))
        val_label = ttk.Label(row, text=f"{var.get():.2f}" if isinstance(var.get(), float) else str(var.get()))
        val_label.pack(side="right")

        def make_callback(v=var, lbl=val_label):
            def update_val(_):
                lbl.config(text=f"{v.get():.2f}" if isinstance(v.get(), float) else str(v.get()))
            return update_val

        def make_reset(v=var, l=label, lbl=val_label):
            def reset():
                v.set(defaults[l])
                lbl.config(text=f"{v.get():.2f}" if isinstance(v.get(), float) else str(v.get()))
            return reset

        ttk.Button(row, text="⭯", width=3, command=make_reset()).pack(side="right", padx=5)
        ttk.Scale(row, from_=mn, to=mx, variable=var, orient="horizontal", command=make_callback()).pack(fill="x", padx=5)

        # ✅ Tooltip bindings
        row.bind("<Enter>", lambda e, l=label: controls["status"].set(tree_tooltips.get(l, "")))
        row.bind("<Leave>", lambda e: controls["status"].set("Ready"))

    ttk.Checkbutton(tab, text="Open file after generation", variable=controls["open_after"]).pack(pady=(5, 0))

    def generate():
        try:
            params = {k: v.get() for k, v in controls.items() if k not in ("status", "open_after")}
            filename = generate_treegen_tree(params, os.path.join("tree", palette_var.get()))
            controls["status"].set(f"✅ Generated {filename}!")
            if controls["open_after"].get():
                if platform.system() == "Windows":
                    os.startfile(filename)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", filename])
                else:
                    subprocess.call(["xdg-open", filename])
        except Exception as e:
            messagebox.showerror("Error", str(e))
            controls["status"].set("⚠️ Generation failed")

    ttk.Button(tab, text="🌳 Generate Tree", command=generate).pack(pady=10)
    ttk.Label(tab, textvariable=controls["status"]).pack(pady=5)

    return controls

# === MAIN ENTRYPOINT ===
def run_gui():
    root = tk.Tk()
    root.title("Voxel Tree Generator Studio")
    root.geometry("750x850")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    tree_tab = ttk.Frame(notebook)

    notebook.add(tree_tab, text="Treegen 🌳")

    build_treegen_gui(tree_tab)

    root.mainloop()


if __name__ == "__main__":
    run_gui()