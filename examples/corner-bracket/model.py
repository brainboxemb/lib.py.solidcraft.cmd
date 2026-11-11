"""Library example for SCPC's native SolidCraft 0.30.1 qualification.

The matching CAD project source lives in
2026-011-02.cad.solidcraft/models/component-examples/corner-bracket/scpc/model.py.
This self-contained copy is kept here for running tests without Forge.

Reference physical result (actual native CAD CI):
  BRep X=-12..60, Y=-12..12, Z=-60..12 mm
  Volume approximately 36771.08744 mm³
  Features: sketch, extrude, fillet, three chamfers.
"""
"""CornerBracket in native SolidCraft commands (no dependency on SCPF).

This is intentionally explicit: the command IDs, sketch profile and
edge-selection points are the native SolidCraft API. SCPC does not recreate
the bracket geometry in Python; it simply sends these commands.

Important: the edge positions below are for the **current 60/12/24 mm
reference bracket**. Unlike the parametrized Forge implementation, changing
a dimension here also requires reviewing the edge-selector positions.
"""
from scpc import Script

script = Script()
for name, value in (
    ("bracket_width", 24),
    ("horizontal_arm_length", 60),
    ("wall_thickness", 12),
    ("arm_end_chamfer", 3),
    ("outer_corner_chamfer", 6),
    ("vertical_arm_length", 60),
    ("inside_corner_radius", 4),
    ("elephant_foot_relief", 0.6),
    ("side_edge_chamfer", 2),
):
    script.add("parameters.add", name=name, expression=str(value), unit="mm")

# This is the same XZ outline as the reviewed standalone printed bracket.
# Native sketch.line accepts points and (optional) stable corner labels.
script.add("sketch.create", plane="XZ", name="Profile")
script.add("sketch.line",
    points=[
        [0, 0],
        ["horizontal_arm_length", 0],
        ["horizontal_arm_length", "-(wall_thickness - (arm_end_chamfer))"],
        ["horizontal_arm_length - (arm_end_chamfer)", "-(wall_thickness)"],
        ["(-(wall_thickness)) + (outer_corner_chamfer)", "-(wall_thickness)"],
        ["-(wall_thickness)", "-(wall_thickness - (outer_corner_chamfer))"],
        ["-(wall_thickness)", "-((-(vertical_arm_length)) + (arm_end_chamfer))"],
        ["(-(wall_thickness)) + (arm_end_chamfer)", "-(-(vertical_arm_length))"],
        [0, "-(-(vertical_arm_length))"],
    ],
    closed=True,
    ids=["i_corner", "o_hor_tip", "o_hor_bevel", "o_hor",
         "o_corner", "o_vert", "o_vert_bevel", "o_vert_end", "v_tip"],
)
script.add("sketch.finish")
script.add("solid.extrude", distance="bracket_width",
           direction="symmetric", body_name="CornerBracket")

# One concave inner fillet and three native chamfers; no screw holes.
script.add("solid.fillet", edges=[[0, 0, 0]],
           radius=4, body="CornerBracket")
script.add("solid.chamfer", edges=[[60, 0, 0], [0, 0, -60]],
           distance="elephant_foot_relief", body="CornerBracket")

# These positions select the two outside broad faces, including the
# mitred end edges. They are reference coordinates, not Python CSG.
outside_edges = [
    [60, -12, 4.5], [58.5, -12, 10.5], [25.5, -12, 12],
    [-9, -12, 9], [-12, -12, -25.5],
    [-10.5, -12, -58.5], [-4.5, -12, -60],
    [60, 12, 4.5], [58.5, 12, 10.5], [25.5, 12, 12],
    [-9, 12, 9], [-12, 12, -25.5],
    [-10.5, 12, -58.5], [-4.5, 12, -60],
]
script.add("solid.chamfer", edges=outside_edges,
           distance="side_edge_chamfer", body="CornerBracket")
script.add("solid.chamfer", edges=[[30, -12, 0], [30, 12, 0]],
           distance="elephant_foot_relief", body="CornerBracket")
