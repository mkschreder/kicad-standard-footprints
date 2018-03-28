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


class ComponentChip(object):
	def __init__(self, props):
		p = self.props = props.copy();
		if not p["TYPE"] in ["RESC", "CAPC", "INDC"]:
			raise BaseException("Chip component generator can only be used on chip components (Resistors, Capacitors and Inductors): "+p["NAME"])

		# parse IPC name for a resistor and fill out essential properties
		parts = re.split("([A-Z]+)(\d+)X(\d+)([LMN])", p["NAME"])
		size = parts[2];
		size_x = size[:len(size)/2];
		size_y = size[len(size)/2:];
		p["TYPE"] = parts[1];
		p["BODY_LENGTH"] = float(size_x)/10
		p["BODY_WIDTH"] = float(size_y)/10
		p["BODY_HEIGHT"] = float(parts[3])/10
		density = parts[5] or "N"
		if density == "L":
			p["COURTYARD"] = 0.1;
		if density == "N":
			p["COURTYARD"] = 0.25;
		if density == "M":
			p["COURTYARD"] = 0.5;

		p["BODY_LENGTH_IN"] = round(p["BODY_LENGTH"] / 2.54, 2);
		p["BODY_WIDTH_IN"] = round(p["BODY_WIDTH"] / 2.54, 2);

		# these need to be revised!
		# typically pad width from edge under the body is 0.2 of the length
		p["BODY_PAD_LENGTH"] = p["BODY_LENGTH"] * 0.2;
		p["BODY_PAD_WIDTH"] = p["BODY_WIDTH"];
		
		# landing pad length is between 1.7 and 2.2 in datasheets
		p["PAD_LENGTH"] = p["BODY_PAD_LENGTH"] * 2;
		# landing pad width is set to 1.1 of the body width
		p["PAD_WIDTH"] = p["BODY_PAD_WIDTH"] * 1.1;
		# by default we make the body end in the middle of the pad so pad distance is body length
		p["PAD_DISTANCE"] = p["BODY_LENGTH"];

		# we calculate the courtyard based on bounds around the pads plus the density setting
		p["COURTYARD_LENGTH"] = p["PAD_DISTANCE"] + p["PAD_LENGTH"] + p["COURTYARD"] * 2;
		p["COURTYARD_WIDTH"] = p["PAD_WIDTH"] + p["COURTYARD"] * 2;

		# silkscreen for resistor consists of two parallel lines drawn in the middle
		# width is the distance between the lines and length is the length of the lines
		p["SILKSCREEN_WIDTH"] = p["BODY_WIDTH"];
		# ensure some distance from the pads themselves
		p["SILKSCREEN_LENGTH"] = (p["PAD_DISTANCE"] - p["PAD_LENGTH"]) * 0.7;

		# solder mask margin is just constant for now
		p["SOLDER_MASK_MARGIN"] = 0.05;

		self.generate()

	def generate(self):
		p = self.props;

		IL = int(10 * p["BODY_LENGTH_IN"]);
		IW = int(10 * p["BODY_LENGTH_IN"]);
		ILString = str(IL).rjust(2, '0')+str(IW).rjust(2, '0');
		kicad_mod = Footprint(p["NAME"]);

		if p["TYPE"] == "RESC":
			kicad_mod.setDescription("Surface Mount Chip Resistor, 2 Pins, "+ILString+", "+str(p["BODY_LENGTH"])+"mm X "+str(p["BODY_WIDTH"])+"mm")
		elif p["TYPE"] == "CAPC":
			kicad_mod.setDescription("Surface Mount Chip Capacitor, 2 Pins, "+ILString+", "+str(p["BODY_LENGTH"])+"mm X "+str(p["BODY_WIDTH"])+"mm")
		elif p["TYPE"] == "INDC":
			kicad_mod.setDescription("Surface Mount Chip Inductor, 2 Pins, "+ILString+", "+str(p["BODY_LENGTH"])+"mm X "+str(p["BODY_WIDTH"])+"mm")

		kicad_mod.setTags(ILString + " " +str(int(p["BODY_LENGTH"]*10)).rjust(2, '0')+str(int(p["BODY_WIDTH"]*10)).rjust(2, '0'))

		# set general values
		kicad_mod.append(Text(type='reference', text='REF**', at=[0, -p["COURTYARD_WIDTH"] - 1], layer='F.SilkS'))
		kicad_mod.append(Text(type='value', text=p["NAME"], at=[0, p["COURTYARD_WIDTH"] + 1], layer='F.Fab'))

		# create fabrication layer
		kicad_mod.append(RectLine(start=[-p["BODY_LENGTH"]/2, -p["BODY_WIDTH"]/2], end=[p["BODY_LENGTH"]/2, p["BODY_WIDTH"]/2], layer='F.Fab'))

		# create silscreen
		kicad_mod.append(Line(start=[-p["SILKSCREEN_LENGTH"]/2, p["SILKSCREEN_WIDTH"]/2], end=[p["SILKSCREEN_LENGTH"]/2, p["SILKSCREEN_WIDTH"]/2], layer='F.SilkS'))
		kicad_mod.append(Line(start=[-p["SILKSCREEN_LENGTH"]/2, -p["SILKSCREEN_WIDTH"]/2], end=[p["SILKSCREEN_LENGTH"]/2, -p["SILKSCREEN_WIDTH"]/2], layer='F.SilkS'))

		# create courtyard
		kicad_mod.append(RectLine(start=[-p["COURTYARD_LENGTH"]/2, -p["COURTYARD_WIDTH"]/2], end=[p["COURTYARD_LENGTH"]/2, p["COURTYARD_WIDTH"]/2], layer='F.CrtYd'))

		# create pads
		kicad_mod.append(Pad(number=1, type=Pad.TYPE_SMT, shape=Pad.SHAPE_ROUNDED_RECT, at=[-p["PAD_DISTANCE"]/2, 0], size=[p["PAD_LENGTH"], p["PAD_WIDTH"]], layers=Pad.LAYERS_SMT, solder_mask_margin=p["SOLDER_MASK_MARGIN"]));
		kicad_mod.append(Pad(number=2, type=Pad.TYPE_SMT, shape=Pad.SHAPE_ROUNDED_RECT, at=[p["PAD_DISTANCE"]/2, 0], size=[p["PAD_LENGTH"], p["PAD_WIDTH"]], layers=Pad.LAYERS_SMT, solder_mask_margin=p["SOLDER_MASK_MARGIN"]));

		# generate 3d model
		scale = 1 / 2.54;
		box = Part.makeBox(p["BODY_LENGTH"] * scale, p["BODY_WIDTH"] * scale, p["BODY_HEIGHT"] * scale)
		box.translate(FreeCAD.Vector(-p["BODY_LENGTH"]/2 * scale, -p["BODY_WIDTH"]/2 * scale, 0));
		mesh=Mesh.Mesh()
		mesh.addFacets(box.tessellate(0.01))

		# add the model to module but use kicad system paths
		# this assumes all libraries are installed into kicad system directory
		kicad_mod.append(Model(filename="${KISYS3DMOD}/"+p["TYPE"]+".3dshapes/"+p["NAME"]+".wrl", at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))

		self.mesh = mesh;
		self.footprint = kicad_mod;

		return kicad_mod;

