KiCad IPC footprint generator

# KiCad IPC Wizard

**Licence:** GNU GPLv3+

## About

This set of python scripts generates standard footprints for a variety of
components and uses IPC naming convention as main source of information. So to
add a new resistor package for a chip resistor you would typically only need to
add an identifier like "RESC1508X04N" for a 1508 (0603) resistor of height 0.4
for standard board density (N). The scripts will then generate kicad footprint
as well as simple 3D model (currently just a box) using FreeCAD python
interface.

It thus becomes easy to change a large number of footprints and the best thing
is that footprints can all follow a well defined standard.

Note however that there is no guarantee that any given footprint follows IPC
standard precisely, however over time and with people's contributions we can
probably get it really close.

## Requirements

You will need FreeCAD installed to build vrml models. 
