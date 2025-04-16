import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import math
import struct
import random
import os
import sys

GRID = 256

def clamp(v, mi, ma):
    return max(mi, min(ma, v))

def resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return filename

def load_palette_png(filename):
    path = resource_path(filename)
    image = Image.open(path).convert("RGBA")
    pixels = list(image.getdata())
    if len(pixels) != 256:
        raise ValueError("Palette must be 256x1 pixels")
    return pixels

def normalize(x, y, z):
    l = math.sqrt(x*x + y*y + z*z)
    return (x/l, y/l, z/l) if l > 0 else (0, 1, 0)

def generate_tree(params):
    random.seed(int(params["seed"]))

    voxels = np.zeros((GRID, GRID, GRID), dtype=np.uint8)
    trunk_vox, leaf_vox = [], []
    gLeaves = []

    size = clamp(params["size"], 0.1, 3.0)
    twisted = clamp(params["twisted"], 0, 3)
    trunkheight = params["trunkheight"] * 10
    density = clamp(params["branchdensity"], 0, 3) * 30
    branchlength = clamp(params["branchlength"], 0, 3) * size * 20
    branchdir = clamp(params["branchdir"], -5, 5)
    leaves = clamp(params["leaves"], 0, 2)

    trunk_width = size * params.get("trunksize", 2)
    max_iter = math.floor(100 * size / 5)
    fixed_size = 5
    twisted = twisted / max_iter

    def draw_line(x0, y0, z0, x1, y1, z1, r):
        steps = int(math.dist([x0, y0, z0], [x1, y1, z1]) * 2)
        for i in range(steps + 1):
            t = i / steps
            x = x0 + t * (x1 - x0)
            y = y0 + t * (y1 - y0)
            z = z0 + t * (z1 - z0)
            for dx in range(-math.ceil(r), math.ceil(r)+1):
                for dy in range(-math.ceil(r), math.ceil(r)+1):
                    for dz in range(-math.ceil(r), math.ceil(r)+1):
                        if dx*dx + dy*dy + dz*dz <= r*r:
                            xi, yi, zi = int(x+dx), int(y+dy), int(z+dz)
                            if 0 <= xi < GRID and 0 <= yi < GRID and 0 <= zi < GRID:
                                trunk_vox.append((xi, yi, zi))

    def get_branch_size(i):
        t = (i - 1) / max_iter
        return (1 - t * t) * trunk_width

    def branch(x, y, z, dx, dy, dz, l):
        steps = math.ceil(l / 3)
        l = l / steps
        for _ in range(steps):
            x1 = x + dx * l
            y1 = y + dy * l
            z1 = z + dz * l
            dx += random.uniform(-1/steps, 1/steps)
            dy += random.uniform(-1/steps, 1/steps) + 0.4 / steps
            dz += random.uniform(-1/steps, 1/steps)
            dx, dy, dz = normalize(dx, dy, dz)
            draw_line(x, y, z, x1, y1, z1, 0)
            gLeaves.append((x1, y1, z1))
            x, y, z = x1, y1, z1

    def generate_branches(x, y, z, dx, dy, dz, i):
        l = fixed_size
        s0 = get_branch_size(i)
        x1 = x + dx * l
        y1 = y + dy * l
        z1 = z + dz * l
        draw_line(x, y, z, x1, y1, z1, s0)

        if y1 > trunkheight:
            b = (1.0 - i / max_iter) * density + 1
            for _ in range(int(b)):
                a = random.uniform(0.0, math.tau)
                idx = math.cos(a)
                idy = random.uniform(0.5, 1.0) * branchdir
                idz = math.sin(a)
                idx, idy, idz = normalize(idx, idy, idz)
                il = (1.0 - i / max_iter) * branchlength * random.uniform(0.5, 1.5)
                t = random.uniform(0.0, 1.0)
                x2 = x + (x1 - x) * t
                y2 = y + (y1 - y) * t
                z2 = z + (z1 - z) * t
                branch(x2, y2, z2, idx, idy, idz, il + 3)

        if i < max_iter:
            var = i * 0.1 * twisted
            dx2 = dx + random.uniform(-var, var)
            dy2 = dy + random.uniform(-var, var)
            dz2 = dz + random.uniform(-var, var)
            dx2, dy2, dz2 = normalize(dx2, dy2, dz2)
            generate_branches(x1, y1, z1, dx2, dy2, dz2, i + 1)
        else:
            gLeaves.append((x1, y1, z1))
            gLeaves.append(((x + x1)/2, (y + y1)/2, (z + z1)/2))

    def generate_leaves():
        chunks = math.ceil(3 * leaves)
        leavesPerChunk = math.ceil(3 * leaves)
        for x, y, z in gLeaves:
            for _ in range(chunks):
                x2, y2, z2 = int(x), int(y), int(z)
                for _ in range(leavesPerChunk):
                    leaf_vox.append((x2, y2, z2))
                    d = random.randint(1, 6)
                    if d == 1: x2 -= 1
                    elif d == 2: x2 += 1
                    elif d in (3, 4): y2 -= 1
                    elif d == 5: z2 -= 1
                    else: z2 += 1

    generate_branches(GRID//2, 0, GRID//2, 0, 1, 0, 1)
    generate_leaves()

    # Color trunk
    random.shuffle(trunk_vox)
    for i, (x, y, z) in enumerate(trunk_vox):
        voxels[x, y, z] = 57 if i < len(trunk_vox) // 2 else 65

    # Color leaves
    random.shuffle(leaf_vox)
    for i, (x, y, z) in enumerate(leaf_vox):
        if 0 <= x < GRID and 0 <= y < GRID and 0 <= z < GRID:
            voxels[x, y, z] = 9 if i < len(leaf_vox) // 2 else 17

    # Save .vox
    palette = load_palette_png("slider_tree.png")
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
                    data += struct.pack('<4B', x, z, y, c)

    out += b'XYZI' + struct.pack('<ii', 4 + len(data), 0)
    out += struct.pack('<i', len(data) // 4)
    out += data

    out += b'RGBA' + struct.pack('<ii', 1024, 0)
    for color in palette:
        out += struct.pack('<4B', *color)

    with open("pinegen_output.vox", "wb") as f:
        f.write(out)

    return True

# === GUI ===

def run_gui():
    def generate():
        try:
            params = {
                "size": size_var.get(),
                "twisted": twist_var.get(),
                "trunksize": trunk_var.get(),
                "trunkheight": trunkheight_var.get(),
                "branchdensity": density_var.get(),
                "branchlength": length_var.get(),
                "branchdir": direction_var.get(),
                "leaves": leaves_var.get(),
                "seed": seed_var.get()
            }
            generate_tree(params)
            status.set("✅ Generated pinegen_output.vox!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            status.set("⚠️ Generation failed")

    root = tk.Tk()
    root.title("Pinegen 🌲 Voxel Pine Tree Generator")
    root.geometry("700x700")
    frm = ttk.Frame(root, padding=10)
    frm.pack(fill="both", expand=True)

    try:
        brand_img = Image.open(resource_path("pinegen_brand.png"))
        brand_img.thumbnail((650, 200))
        brand_img_tk = ImageTk.PhotoImage(brand_img)
        ttk.Label(frm, image=brand_img_tk).pack(pady=(0, 5))
    except:
        pass

    ttk.Label(frm, text="by NGNT • v1.1", font=("Arial", 15, "italic")).pack(pady=(0, 15))

    size_var         = tk.DoubleVar(value=1.0)
    twist_var        = tk.DoubleVar(value=0.5)
    trunk_var        = tk.DoubleVar(value=2.0)
    trunkheight_var  = tk.DoubleVar(value=1.0)
    density_var      = tk.DoubleVar(value=1.0)
    length_var       = tk.DoubleVar(value=1.0)
    direction_var    = tk.DoubleVar(value=-0.5)
    leaves_var       = tk.DoubleVar(value=1.0)
    seed_var         = tk.IntVar(value=1)
    status           = tk.StringVar(value="Ready")

    sliders = [
        ("Size", size_var, 0.1, 3.0),
        ("Twist", twist_var, 0.0, 3.0),
        ("Trunk Size", trunk_var, 1.0, 3.0),
        ("Trunk Height", trunkheight_var, 0.0, 5.0),
        ("Branch Density", density_var, 0.0, 3.0),
        ("Branch Length", length_var, 0.0, 3.0),
        ("Branch Direction", direction_var, -5.0, 5.0),
        ("Leafiness", leaves_var, 0.0, 2.0),
        ("Seed", seed_var, 1, 9999)
    ]

    tooltips = {
        "Size": "Controls overall size/scale of the pine tree",
        "Twist": "How wiggly the main trunk is",
        "Trunk Size": "Scales the width of the pine tree's trunk",
        "Trunk Height": "How tall before branches appear",
        "Branch Density": "How many side branches appear",
        "Branch Length": "How far the branches grow outward",
        "Branch Direction": "How tilted the branches grow",
        "Leafiness": "How many leaves are created",
        "Seed": "Controls the random variation (same seed = same tree)"
    }

    default_values = {label: var.get() for label, var, *_ in sliders}

    for label, var, mn, mx in sliders:
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=4)

        ttk.Label(row, text=label).pack(side="left", padx=(0, 5))
        val_label = ttk.Label(row, text=f"{var.get():.2f}" if isinstance(var.get(), float) else str(var.get()))
        val_label.pack(side="right")

        def make_callback(v=var, lbl=val_label):
            def update_val(_):
                val = f"{v.get():.2f}" if isinstance(v.get(), float) else str(v.get())
                lbl.config(text=val)
            return update_val

        def make_reset(v=var, l=label, lbl=val_label):
            def reset():
                v.set(default_values[l])
                lbl.config(text=f"{v.get():.2f}" if isinstance(v.get(), float) else str(v.get()))
            return reset

        ttk.Button(row, text="⭯", width=3, command=make_reset()).pack(side="right", padx=5)
        ttk.Scale(row, from_=mn, to=mx, variable=var, orient="horizontal", command=make_callback()).pack(fill="x", padx=5)

        row.bind("<Enter>", lambda e, l=label: status.set(tooltips.get(l, "")))
        row.bind("<Leave>", lambda e: status.set(""))

    ttk.Button(frm, text="🌲 Generate Pine Tree", command=generate).pack(pady=10)
    ttk.Label(frm, textvariable=status).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    run_gui()