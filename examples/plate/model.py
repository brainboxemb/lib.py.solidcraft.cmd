"""A complete native Plate, written as SCPC commands, NOT as a Forge model.

Compare models/basic/plate/scpf/model.py in the CAD project.
Everything below is already a SolidCraft command ID or parameter.
"""
from scpc import Script

script = Script()

for name, value in (("length", 100), ("width", 60), ("thickness", 10)):
    script.add("parameters.add", name=name, expression=str(value), unit="mm")

script.add("sketch.create", plane="XY", name="Plate footprint")
script.add("sketch.rectangle.two_point",
           p0=["-length / 2", "-width / 2"],
           p1=["length / 2", "width / 2"])
script.add("sketch.finish")
script.add("solid.extrude", distance="thickness", body_name="Plate")

# These are the native SolidCraft edge positions, not a SCPC fillet helper.
script.add("solid.fillet", body="Plate", radius=2,
           edges=[[-50, -30, 5], [50, -30, 5],
                  [50, 30, 5], [-50, 30, 5]])
for x, y in ((-35, -15), (35, -15), (35, 15), (-35, 15)):
    script.add("solid.hole", position=[x, y, 10],
               diameter=8, targets=["Plate"])
