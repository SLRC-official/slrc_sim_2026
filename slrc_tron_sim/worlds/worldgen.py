from pathlib import Path
import math

# -------- Spec constants --------
GRID_N = 25
CELL   = 0.40
GRID_LINE_W = 0.03
PATH_W = 0.05

GRID_SPAN = GRID_N * CELL   # 10.0 m
HALF = GRID_SPAN / 2.0      # 5.0 m

FLOOR_TH = 0.002
LINE_H   = 0.002
SQUARE_H = 0.003
PATH_H   = 0.004

# Slight lift to avoid z-fighting with floor
Z_FLOOR  = FLOOR_TH / 2.0
Z_LINES  = FLOOR_TH + LINE_H / 2.0 + 0.0002
Z_SQUARE = FLOOR_TH + SQUARE_H / 2.0 + 0.0004
Z_PATH   = FLOOR_TH + PATH_H / 2.0 + 0.0006

# -------- Fixed squares --------
RED_CELL  = (20, 3)
BLUE_CELL = (2, 24)

def cell_center(i, j):
    x = -HALF + (i + 0.5) * CELL
    y =  HALF - (j + 0.5) * CELL
    return x, y

# -------- Yellow loop path nodes --------
PATH_NODES = [
(2,2),(3,2),(4,2),(5,2),(6,2),(7,2),(8,2),(9,2),(10,2),(11,2),(12,2),(13,2),(14,2),(15,2),(16,2),(17,2),(18,2),
(18,1),(18,0),(19,0),(20,0),(21,0),(22,0),(23,0),
(23,1),(23,2),(23,3),(23,4),(23,5),(23,6),(23,7),(23,8),(23,9),(23,10),(23,11),(23,12),(23,13),(23,14),(23,15),(23,16),(23,17),(23,18),(23,19),(23,20),(23,21),(23,22),
(22,22),(21,22),(20,22),
(20,21),(20,20),(20,19),(20,18),(20,17),(20,16),(20,15),(20,14),(20,13),(20,12),(20,11),(20,10),(20,9),(20,8),
(19,8),(18,8),(17,8),(16,8),(15,8),(14,8),
(14,9),(14,10),(14,11),(14,12),
(13,12),(12,12),(11,12),(10,12),(9,12),(8,12),
(8,13),(8,14),
(9,14),(10,14),(11,14),(12,14),(13,14),(14,14),
(14,15),(14,16),(14,17),(14,18),(14,19),(14,20),(14,21),(14,22),
(13,22),(12,22),(11,22),(10,22),(9,22),(8,22),(7,22),(6,22),(5,22),(4,22),(3,22),(2,22),
(2,21),(2,20),(2,19),(2,18),
(3,18),(4,18),(5,18),
(5,17),(5,16),(5,15),(5,14),(5,13),(5,12),(5,11),
(4,11),(3,11),(2,11),
(2,10),(2,9),(2,8),(2,7),(2,6),(2,5),(2,4),(2,3)
]

# -------- Visual helper with emissive material --------
def box_visual(name, size_x, size_y, size_z, x, y, z,
               roll=0.0, pitch=0.0, yaw=0.0, rgba=(1,1,1,1)):
    r,g,b,a = rgba
    return f"""
      <visual name="{name}_vis">
        <pose>{x:.4f} {y:.4f} {z:.4f} {roll:.4f} {pitch:.4f} {yaw:.4f}</pose>
        <geometry>
          <box>
            <size>{size_x:.4f} {size_y:.4f} {size_z:.4f}</size>
          </box>
        </geometry>
        <material>
          <ambient>{r:.3f} {g:.3f} {b:.3f} {a:.3f}</ambient>
          <diffuse>{r:.3f} {g:.3f} {b:.3f} {a:.3f}</diffuse>
          <emissive>{r:.3f} {g:.3f} {b:.3f} {a:.3f}</emissive>
          <specular>0 0 0 1</specular>
        </material>
      </visual>
      <collision name="{name}_col">
        <pose>{x:.4f} {y:.4f} {z:.4f} {roll:.4f} {pitch:.4f} {yaw:.4f}</pose>
        <geometry>
          <box>
            <size>{size_x:.4f} {size_y:.4f} {size_z:.4f}</size>
          </box>
        </geometry>
      </collision>
""".rstrip()

# -------- Floor --------
def plane_model():
    return f"""
    <model name="floor">
      <static>true</static>
      <link name="link">
        <collision name="col">
          <pose>0 0 {Z_FLOOR:.4f} 0 0 0</pose>
          <geometry><box><size>50 50 {FLOOR_TH:.4f}</size></box></geometry>
        </collision>
        <visual name="vis">
          <pose>0 0 {Z_FLOOR:.4f} 0 0 0</pose>
          <geometry><box><size>50 50 {FLOOR_TH:.4f}</size></box></geometry>
          <material>
            <ambient>0.05 0.05 0.05 1</ambient>
            <diffuse>0.05 0.05 0.05 1</diffuse>
            <specular>0 0 0 1</specular>
          </material>
        </visual>
      </link>
    </model>
""".rstrip()

# -------- Grid lines --------
def grid_lines_model():
    parts = []
    for k in range(GRID_N + 1):
        x = -HALF + k * CELL
        parts.append(box_visual(
            name=f"v{k}",
            size_x=GRID_LINE_W,
            size_y=GRID_SPAN + GRID_LINE_W,
            size_z=LINE_H,
            x=x, y=0.0, z=Z_LINES,
            rgba=(1,1,1,1.0)
        ))
    for k in range(GRID_N + 1):
        y = HALF - k * CELL
        parts.append(box_visual(
            name=f"h{k}",
            size_x=GRID_SPAN + GRID_LINE_W,
            size_y=GRID_LINE_W,
            size_z=LINE_H,
            x=0.0, y=y, z=Z_LINES,
            rgba=(1,1,1,1.0)
        ))
    return f"""
    <model name="grid_lines">
      <static>true</static>
      <link name="link">
{chr(10).join(parts)}
      </link>
    </model>
""".rstrip()

# -------- Start & portal --------
def squares_model():
    rx, ry = cell_center(*RED_CELL)
    bx, by = cell_center(*BLUE_CELL)
    red = box_visual("portal_red", CELL, CELL, SQUARE_H, rx, ry, Z_SQUARE, rgba=(1.0,0.1,0.1,1.0))
    blue = box_visual("start_blue", CELL, CELL, SQUARE_H, bx, by, Z_SQUARE, rgba=(0.1,0.2,1.0,1.0))
    return f"""
    <model name="start_and_portal">
      <static>true</static>
      <link name="link">
{red}
{blue}
      </link>
    </model>
""".rstrip()

# -------- Hostile path --------
def path_model():
    parts = []
    nodes = PATH_NODES[:] + [PATH_NODES[0]]

    OVERLAP = 0.025  # 2.5 cm per end

    for idx in range(len(nodes) - 1):
        (i1, j1), (i2, j2) = nodes[idx], nodes[idx + 1]
        x1, y1 = cell_center(i1, j1)
        x2, y2 = cell_center(i2, j2)
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        if i2 != i1:
            sx, sy = (CELL + 2*OVERLAP), PATH_W
        else:
            sx, sy = PATH_W, (CELL + 2*OVERLAP)

        parts.append(box_visual(
            name=f"seg{idx}",
            size_x=sx, size_y=sy, size_z=PATH_H,
            x=mx, y=my, z=Z_PATH,
            rgba=(1.0, 0.85, 0.10, 1.0)  # proper yellow
        ))

    return f"""
    <model name="hostile_path">
      <static>true</static>
      <link name="link">
{chr(10).join(parts)}
      </link>
    </model>
""".rstrip()

# -------- SDF assembly --------
sdf = f"""<?xml version="1.0" ?>
<sdf version="1.9">
  <world name="slrc_arena_from_image">

    <gravity>0 0 -9.81</gravity>

    <scene>
      <ambient>0.6 0.6 0.6 1</ambient>
      <background>0 0 0 1</background>
      <shadows>false</shadows>
    </scene>

    <light name="sun" type="directional">
      <pose>-10 -10 30 0 0 0</pose>
      <direction>-0.3 0.3 -1</direction>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0 0 0 1</specular>
    </light>

{plane_model()}

{grid_lines_model()}

{squares_model()}

{path_model()}

  </world>
</sdf>
"""

out = Path("slrc_tron_sim/worlds/encom_grid.sdf")
out.write_text(sdf)
print(f"Wrote: {out.resolve()}")