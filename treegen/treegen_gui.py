import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import math
import struct
import random

GRID = 256

def clamp(v, mi, ma):
    return max(mi, min(ma, v))

def load_palette_png(filename):
    """Loads a 256x1 .png file and returns a list of 256 RGBA tuples"""
    path = resource_path(filename)
    image = Image.open(path).convert("RGBA")
    pixels = list(image.getdata())
    if len(pixels) != 256:
        raise ValueError("Palette PNG must be exactly 256 pixels wide")
    return pixels
    
import sys
import os

def resource_path(filename):
    """Get path to resource for PyInstaller --onefile"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return filename

def generate_tree(params):
    random.seed(params['seed'])
    
    trunk_indices = [57, 65]
    leaf_indices = [9, 17]
    voxels = np.zeros((GRID, GRID, GRID), dtype=np.uint8)
    gLeaves = []

    size = 150 * params['size'] / params['iterations']
    gTrunkSize = params['trunksize'] * params['size'] * 6
    wide = min(params['wide'], 0.95)  # max value slightly under 1.0
    gBranchLength0 = size * (1 - wide)
    gBranchLength1 = size * wide

    def set_voxel(x, y, z, color):
        if 0 <= x < GRID and 0 <= y < GRID and 0 <= z < GRID:
            voxels[x, y, z] = color

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
        t = math.sqrt((i - 1) / params['iterations'])
        return gBranchLength0 + t * (gBranchLength1 - gBranchLength0)

    def get_branch_size(i):
        t = math.sqrt((i - 1) / params['iterations'])
        return (1 - t) * gTrunkSize

    def get_branch_angle(i):
        t = math.sqrt((i - 1) / params['iterations'])
        return 2.0 * params['spread'] * t

    def get_branch_prob(i):
        return math.sqrt((i - 1) / params['iterations'])

    def branches(x, y, z, dx, dy, dz, i):
        l = get_branch_length(i)
        s0 = get_branch_size(i)
        s1 = get_branch_size(i+1)

        x1 = x + dx * l
        y1 = y + dy * l
        z1 = z + dz * l

        draw_line(x, y, z, x1, y1, z1, s0, s1)  # color removed!

        if i < params['iterations']:
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
        # STEP 1: Generate leaf voxel positions
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

        # STEP 2: Assign leaf color: 50% index 9, 50% index 17
        random.shuffle(leaf_voxels)
        mid = len(leaf_voxels) // 2
        for i, (x, y, z) in enumerate(leaf_voxels):
            idx = leaf_indices[0] if i < mid else leaf_indices[1]
            if 0 <= x < GRID and 0 <= y < GRID and 0 <= z < GRID:
                voxels[x, y, z] = idx

    branches(GRID//2, GRID//2, 0, 0, 0, 1, 1)
    add_leaves()
    
    # === Assign trunk color: 50% index 57, 50% index 65 ===
    random.shuffle(trunk_voxels)
    mid = len(trunk_voxels) // 2
    for i, (x, y, z) in enumerate(trunk_voxels):
        idx = trunk_indices[0] if i < mid else trunk_indices[1]
        voxels[x, y, z] = idx

    out = bytearray()
    out += b'VOX ' + struct.pack('<i', 150)
    out += b'MAIN' + struct.pack('<ii', 0, 0)
    out += b'SIZE' + struct.pack('<ii', 12, 0)
    out += struct.pack('<iii', GRID, GRID, GRID)

    data = bytearray()
    for x in range(GRID):
        for y in range(GRID):
            for z in range(GRID):
                c = voxels[x, y, z]
                if c > 0:
                    data += struct.pack('<4B', x, y, z, c)

    out += b'XYZI'
    out += struct.pack('<ii', 4 + len(data), 0)
    out += struct.pack('<i', len(data) // 4)
    out += data

    # trunk_color = load_vox_palette(resource_path("trunk-oak.vox"))[1]
    # leaf_color = load_vox_palette(resource_path("leaf.vox"))[1]
    palette = load_palette_png("slider_tree.png")
    # palette[1] = trunk_color
    # palette[2] = leaf_color

    out += b'RGBA'
    out += struct.pack('<ii', 1024, 0)
    for c in palette:
        out += struct.pack('<4B', *c)

    with open("treegen_output.vox", "wb") as f:
        f.write(out)

    return True

def run_gui():
    def generate():
        params = {
            "size": size_var.get(),
            "trunksize": trunk_var.get(),
            "spread": spread_var.get(),
            "twisted": twist_var.get(),
            "leaves": leaves_var.get(),
            "gravity": gravity_var.get(),
            "iterations": iter_var.get(),
            "wide": wide_var.get(),
            "seed": seed_var.get()
        }
        try:
            generate_tree(params)
            status.set("✅ Generated treegen_output.vox!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            status.set("⚠️ Generation failed")

    root = tk.Tk()
    root.title("treegen - Voxel Tree Generator 🌳")
    root.geometry("700x700")
    frm = ttk.Frame(root, padding=10)
    frm.pack(fill="both", expand=True)

    # === Branding image at top
    try:
        brand_img = Image.open(resource_path("treegen_brand.png"))
        brand_img.thumbnail((650, 200))
        brand_img_tk = ImageTk.PhotoImage(brand_img)
        brand_label = ttk.Label(frm, image=brand_img_tk)
        brand_label.image = brand_img_tk
        brand_label.pack(pady=(0, 10))
    except:
        pass

    ttk.Label(frm, text="by NGNT • v1.1", font=("Arial", 15, "italic")).pack(pady=(0, 15))

    size_var = tk.DoubleVar(value=1.0)
    trunk_var = tk.DoubleVar(value=1.0)
    spread_var = tk.DoubleVar(value=0.5)
    twist_var = tk.DoubleVar(value=0.5)
    leaves_var = tk.DoubleVar(value=1.0)
    gravity_var = tk.DoubleVar(value=0.0)
    iter_var = tk.IntVar(value=12)
    status = tk.StringVar(value="Ready")
    seed_var = tk.IntVar(value=1)
    wide_var = tk.DoubleVar(value=0.5)

    sliders = [
        ("Size", size_var, 0.1, 3.0),
        ("Trunk Size", trunk_var, 0.1, 3.0),
        ("Spread", spread_var, 0.0, 1.0),
        ("Twist", twist_var, 0.0, 1.0),
        ("Leafiness", leaves_var, 0.0, 3.0),
        ("Gravity", gravity_var, -1.0, 1.0),
        ("Iterations", iter_var, 5, 15),
        ("Wide", wide_var, 0.0, 1.0),
        ("Seed", seed_var, 1, 9999)
    ]
    
    seed_row = ttk.Frame(frm)
    seed_row.pack(fill="x", pady=(10, 4))

    tooltips = {
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

    default_values = {
        "Size": 1.0,
        "Trunk Size": 1.0,
        "Spread": 0.5,
        "Twist": 0.5,
        "Leafiness": 1.0,
        "Gravity": 0.0,
        "Iterations": 12,
        "Wide": 0.5,
        "Seed": 1
    }

    for label, var, mn, mx in sliders:
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=4)

        label_widget = ttk.Label(row, text=label)
        label_widget.pack(side="left", padx=(0, 5))

        # 👇 Move the tooltip to the full slider row instead of just the label
        row.bind("<Enter>", lambda e, l=label: status.set(tooltips.get(l, "")))
        row.bind("<Leave>", lambda e: status.set(""))

        val_label = ttk.Label(row, text=f"{var.get():.2f}")
        val_label.pack(side="right")

        def make_callback(v=var, lbl=val_label):
            def update_val(_):
                lbl.config(text=f"{v.get():.2f}" if isinstance(v.get(), float) else str(v.get()))
            return update_val

        def make_reset(v=var, l=label, lbl=val_label):
            def reset():
                v.set(default_values[l])
                lbl.config(text=f"{v.get():.2f}" if isinstance(v.get(), float) else str(v.get()))
            return reset

        reset_btn = ttk.Button(row, text="⭯", width=3, command=make_reset())
        reset_btn.pack(side="right", padx=5)

        sld = ttk.Scale(row, from_=mn, to=mx, variable=var, orient="horizontal", command=make_callback())
        sld.pack(fill="x", padx=5)

    ttk.Button(frm, text="🌳 Generate Tree", command=generate).pack(pady=10)
    ttk.Label(frm, textvariable=status).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    run_gui()