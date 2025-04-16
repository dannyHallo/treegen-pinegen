🌳 PINEGEN - Voxel Tree Generator
=================================

pinegen is a simple, standalone tool for generating beautiful procedural trees in the .vox format — perfect for Teardown, MagicaVoxel, or any voxel-based project.

🎨 FEATURES
-----------
- Procedural tree generation with customizable parameters
- Easy-to-use graphical interface
- Trees export as .vox files ready for use
- Custom color palette support (via slider_tree.png)
- Automatically uses built-in trunk and leaf color slots (index 57/65 and 9/17)

📁 INCLUDED FILES
-----------------
- pinegen_gui.exe ............. The application (double-click to run)
- slider_tree.png ......... Color palette file (256x1 PNG, used in export)
- pinegen_brand.png ........GUI header image
- README.txt .............. This file
- requirements.txt ........ Only needed for advanced users (not required to run .exe)

🧰 HOW TO USE
-------------
1. Launch **pinegen_gui.exe**
2. Adjust the sliders to your liking
3. Click "🌳 Generate Tree"
4. Your tree will be saved as `pinegen_output.vox` in the same folder

✨ That’s it! Open it in MagicaVoxel or drop it into your mod.

🌈 COLOR PALETTE
----------------
The tool uses specific palette indices:
- Leaves: index 9 and 17
- Trunk:  index 57 and 65

To change tree colors, edit the `slider_tree.png` palette using any image editor or replace it with your own 256x1 PNG palette.

🧡 CREDITS
----------
Created with Python, pixels, and tree magic.