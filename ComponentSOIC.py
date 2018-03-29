from KicadModTree import *
import re
import os
import sys

sys.path.insert(0, "/usr/lib/freecad/lib/")
import FreeCAD
import FreeCADGui
import Import
import Draft
import Part
import Mesh
from FootprintDatabase import *
from Component import *

class ComponentSOIC(object):
	def __init__(self, props):
		p = self.props = props.copy();

		print("Parsing SOIC: "+p["NAME"]);

		if not p["TYPE"] in ["SOIC"]:
			raise BaseException("SOIC component generator can only be used on SOIC packages: "+p["NAME"])

		parts = re.split("([A-Z]+)(\d+)P(\d+)X(\d+)[_*]?([A-Z]*)?-(\d+)([LMN])", p["NAME"])
		if len(parts) < 2:
			raise BaseException("SOIC: Could not parse name: "+p["NAME"]);

		p["TYPE"] = parts[1];
		p["PITCH"] = float(parts[2])/100;
		# all soics are 1.27 pitch.
		if int(p["PITCH"] * 100) != 127:
			raise BaseException("SOIC package must have 1.27 pitch! (found: "+str(p["PITCH"])+")")
		p["BODY_WIDTH_WITH_PINS"] = float(parts[3])/100
		p["BODY_HEIGHT_WITH_PINS"] = float(parts[4])/100
		p["PIN_COUNT"] = int(parts[6]);
		p["THERMAL_PAD"] = 0;
		if parts[5] == "HS":
			p["THERMAL_PAD"] = 1;
			p["PIN_COUNT"] -= 1;
		density = parts[7] or "N"
		if density == "L":
			p["COURTYARD"] = 0.1;
		if density == "N":
			p["COURTYARD"] = 0.25;
		if density == "M":
			p["COURTYARD"] = 0.5;

		# calculate other parameters
		# usually pins stick out 1mm and we have one on each side
		p["BODY_WIDTH"] = p["BODY_WIDTH_WITH_PINS"] - 2;
		# body sticks out about half a millimeter to the sides
		p["BODY_LENGTH"] = (p["PIN_COUNT"] / 2 - 1) * p["PITCH"] + 1;
		p["BODY_HEIGHT"] = p["BODY_HEIGHT_WITH_PINS"];

		# fixed widt
		p["PAD_WIDTH"] = 0.6;
		p["PAD_LENGTH"] = 1.55;

		# distance between pad rows center to center
		p["PAD_DISTANCE"] = p["BODY_WIDTH"] + 0.7 * 2;

		# courtyard needs to be calculated based on maximum of pad size and body size
		p["COURTYARD_WIDTH"] = p["PAD_DISTANCE"] + p["PAD_LENGTH"] + p["COURTYARD"] * 2;
		p["COURTYARD_LENGTH"] = p["BODY_LENGTH"] + p["COURTYARD"] * 2;

		p["THERMAL_PAD_WIDTH"] = p["BODY_WIDTH"] - 1.6
		p["THERMAL_PAD_LENGTH"] = p["BODY_LENGTH"] - 1.9

		# silkscreen for resistor consists of two parallel lines drawn in the middle
		# width is the distance between the lines and length is the length of the lines
		p["SILKSCREEN_WIDTH"] = p["BODY_WIDTH"];
		# ensure some distance from the pads themselves
		p["SILKSCREEN_LENGTH"] = p["BODY_LENGTH"];


		p["SOLDER_MASK_MARGIN"] = 0.07;

		self.generate();

	def generate(self):
		p = self.props;

		kicad_mod = Footprint(p["NAME"]);

		kicad_mod.setDescription("SOIC, Body size "+str(p["BODY_LENGTH"])+"mm X "+str(p["BODY_WIDTH"])+"mm")

		# set general values
		kicad_mod.append(Text(type='reference', text='REF**', at=[0, -p["COURTYARD_WIDTH"]/2 - 1], layer='F.SilkS'))
		kicad_mod.append(Text(type='value', text=p["NAME"], at=[0, p["COURTYARD_WIDTH"]/2 + 1], layer='F.Fab'))

		# create fabrication layer
		kicad_mod.append(RectLine(start=[-p["BODY_WIDTH"]/2, -p["BODY_LENGTH"]/2], end=[p["BODY_WIDTH"]/2, p["BODY_LENGTH"]/2], layer='F.Fab'))
		
		# create silscreen
		kicad_mod.append(RectLine(start=[-p["BODY_WIDTH"]/2, -p["BODY_LENGTH"]/2], end=[p["BODY_WIDTH"]/2, p["BODY_LENGTH"]/2], layer='F.SilkS'))

		# create courtyard
		kicad_mod.append(RectLine(start=[-p["COURTYARD_WIDTH"]/2, -p["COURTYARD_LENGTH"]/2], end=[p["COURTYARD_WIDTH"]/2, p["COURTYARD_LENGTH"]/2], layer='F.CrtYd'))

		# create pads
		pin_start_y = ((p["PIN_COUNT"] / 2 - 1) * p["PITCH"]) / 2;
		for pn in range(0, p["PIN_COUNT"] / 2):
			pin_y = -pin_start_y + pn * p["PITCH"];
			kicad_mod.append(Pad(number=pn + 1, type=Pad.TYPE_SMT, shape=Pad.SHAPE_ROUNDED_RECT, at=[-p["PAD_DISTANCE"]/2, pin_y], size=[p["PAD_LENGTH"], p["PAD_WIDTH"]], layers=Pad.LAYERS_SMT, solder_mask_margin=p["SOLDER_MASK_MARGIN"]));
			kicad_mod.append(Pad(number=p["PIN_COUNT"] - pn, type=Pad.TYPE_SMT, shape=Pad.SHAPE_ROUNDED_RECT, at=[p["PAD_DISTANCE"]/2, pin_y], size=[p["PAD_LENGTH"], p["PAD_WIDTH"]], layers=Pad.LAYERS_SMT, solder_mask_margin=p["SOLDER_MASK_MARGIN"]));

		# create thermal pad
		if p["THERMAL_PAD"]: 
			kicad_mod.append(Pad(number=p["PIN_COUNT"] + 1, type=Pad.TYPE_SMT, shape=Pad.SHAPE_ROUNDED_RECT, at=[0, 0], size=[p["THERMAL_PAD_WIDTH"], p["THERMAL_PAD_LENGTH"]], layers=Pad.LAYERS_SMT, solder_mask_margin=p["SOLDER_MASK_MARGIN"]));
		# generate 3d model
		scale = 1 / 2.54;
		box = Part.makeBox(p["BODY_WIDTH"] * scale, p["BODY_LENGTH"] * scale, p["BODY_HEIGHT"] * scale)
		box.translate(FreeCAD.Vector(-p["BODY_WIDTH"]/2 * scale, -p["BODY_LENGTH"]/2 * scale, 0));
		mesh=Mesh.Mesh()
		mesh.addFacets(box.tessellate(0.01))

		# add the model to module but use kicad system paths
		# this assumes all libraries are installed into kicad system directory
		kicad_mod.append(Model(filename="${KISYS3DMOD}/"+p["TYPE"]+".3dshapes/"+p["NAME"]+".wrl", at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))

		self.mesh = mesh;
		self.footprint = kicad_mod;

