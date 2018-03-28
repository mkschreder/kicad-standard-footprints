from KicadModTree import *
import re
import csv
import os
import shutil

import sys
sys.path.insert(0, "/usr/lib/freecad/lib/")
import FreeCAD
import FreeCADGui
import Import
import Draft
import Part
import Mesh
from FootprintDatabase import *

# BGA + Pin Qty + C or N + Pitch P + Ball Columns X Ball Rows _ Body Length X Body Width X Height
def gen_bga(code):
	parts = re.split("([A-Z]+)(\d+)C(\d+)P(\d+)X(\d+)_(\d+)X(\d+)X(\d+)(.*)([LMN])", code)
	n = 2;
	pin_count = int(parts[2]);
	pitch_idx = int(parts[3]);
	pitch = float(parts[3]) / 100;
	ball_col = int(parts[4]);
	ball_row = int(parts[5]);
	L = float(parts[6]) / 100;
	W = float(parts[7]) / 100;
	H = float(parts[8]) / 100;
	Type = parts[10];
	xbase = -(ball_col * pitch / 2);
	ybase = -(ball_row * pitch / 2);

	kicad_mod = Footprint(code)

	# land diameter is calculated from pitch
	# ball diameter, landing diameter
	land_diameter = {
		150: [0.75, 0.55],
		127: [0.75, 0.55],
		100: [0.60, 0.45],
		80: [0.50, 0.40],
		75: [0.45, 0.35],
		65: [0.40, 0.30],
		50: [0.30, 0.25],
		40: [0.25, 0.20],
		30: [0.20, 0.15],
		25: [0.15, 0.10]
	};
	
	pad_diameter = land_diameter[pitch_idx][1];

	GF = 0.8;
	if Type == 'N':
		GF = 0.8;
	elif Type == 'M':
		GF = 1;
	elif Type == 'L':
		GF = 0.4;
	
	# size of the alignment fab box
	GY = W + GF;
	GX = L + GF;

	kicad_mod.setDescription("BGA, "+str(pin_count)+" pins, L:"+str(L)+", W:"+str(W)+", H:"+str(H))
	kicad_mod.setTags("BGA-"+str(pin_count))

	# set general values
	kicad_mod.append(Text(type='reference', text='REF**', at=[0, ybase - 2], layer='F.SilkS'))
	kicad_mod.append(Text(type='value', text=footprint_name, at=[0, -ybase + 2], layer='F.Fab'))

	# create silscreen
	kicad_mod.append(RectLine(start=[xbase - GF, ybase - GF], end=[-xbase + GF, -ybase + GF], layer='F.Fab'))
	kicad_mod.append(RectLine(start=[xbase, ybase], end=[-xbase, -ybase], layer='F.SilkS'))
	#kicad_mod.append(Line(start=[-G/2, -X/2], end=[G/2, -X/2], layer='F.SilkS'))

	# create courtyard
	#kicad_mod.append(RectLine(start=[-GX/2, -GY/2], end=[GX/2, GY/2], layer='F.CrtYd'))

	# create pads
	for ypin in range(1, ball_row):
		for xpin in range(1, ball_col):
			pin_name = chr(ord('A')+ypin-1) + str(xpin);
			kicad_mod.append(Pad(number=pin_name, type=Pad.TYPE_SMT, shape=Pad.SHAPE_CIRCLE, at=[xbase + xpin * pitch, ybase + ypin * pitch], size=[pad_diameter, pad_diameter], layers=Pad.LAYERS_SMT, solder_mask_margin=0.05));

	# add model
	#kicad_mod.append(Model(filename="example.3dshapes/example_footprint.wrl",
	#					   at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))
	return kicad_mod

def gen_molded_package(kicad_mod, device_type, L, W, PlaceDensity):
	if PlaceDensity == 'N':
		GF = W * 0.2 * 2;
	elif PlaceDensity == 'M':
		GF = W * 0.4 * 2;
	elif PlaceDensity == 'L':
		GF = W * 0.1 * 2;

	WF = 0.8;
	if W < 1:
		WF = 1;
	
	# pad width
	PW = X = W * WF;
	# pad length
	PL = Y = L * 0.4;
	# distance between pads	
	C = L;

	# size of the alignment fab box
	GY = W + GF;
	GX = L + PL + GF;

	# size of the part in imperial units
	IL = int(100 * L / 24.5);
	IW = int(100 * W / 24.5);
	ILString = str(IL).rjust(2, '0')+str(IW).rjust(2, '0');

	# solder mask margin
	MaskMargin = min(PW, PL) * 0.1

	kicad_mod.setDescription("Surface Mount "+device_type+" Molded 2 Pins, "+ILString+", "+str(L)+"mm X "+str(W)+"mm")
	kicad_mod.setTags(ILString + " " +str(int(L*10)).rjust(2, '0')+str(int(W*10)).rjust(2, '0'))

	# set general values
	kicad_mod.append(Text(type='reference', text='REF**', at=[0, -W/2 - 1], layer='F.SilkS'))
	kicad_mod.append(Text(type='value', text=footprint_name, at=[0, W/2 + 1], layer='F.Fab'))

	# polarity tab width
	PTW = 1.4 * PL / 2;

	# create fab outline that also shows diode polarity
	kicad_mod.append(RectLine(start=[-L/2, -W/2], end=[L/2, W/2], layer='F.Fab'))
	kicad_mod.append(FilledRect(start=[-L/2, -W/2], end=[-L/2 + PTW, W/2], layer='F.Fab'))

	# generate silkscreen that covers diode outline at the top and at the bottom
	#if device_type == "Diode":
	'''
	if W > 1:
		R = min(W, L)*0.1;
		kicad_mod.append(Circle(center=[-L/2 - PL / 2 - R * 2, -W / 2], radius=R, layer='F.SilkS'))
	else:
		kicad_mod.append(Line(start=[-L/2 - PL / 2 - 0.2, -W/2], end=[-L/2 - PL / 2 - 0.2, W/2], layer='F.SilkS'))
	elif device_type == "Capacitor, Polarized":
		# insert a plus sign beside the positive lead
		sign_size = 0.4;
		sign_x = -C/2 - PL - sign_size / 2;
		sign_y = -PW / 2;
		kicad_mod.append(Line(start=[sign_x - sign_size, sign_y], end=[sign_x + sign_size, sign_y], layer='F.SilkS'))
		kicad_mod.append(Line(start=[sign_x, sign_y - sign_size], end=[sign_x, sign_y + sign_size], layer='F.SilkS'))
	'''

	kicad_mod.append(Line(start=[-L/2, -W/2 + PW / 2], end=[-L/2, -W/2], layer='F.SilkS'))
	#kicad_mod.append(Line(start=[-L/2 + PTW, -W/2 + PW / 2], end=[-L/2 + PTW, -W/2], layer='F.SilkS'))
	kicad_mod.append(Line(start=[L/2, -W/2], end=[L/2, -W/2 + PW / 2], layer='F.SilkS'))
	kicad_mod.append(Line(start=[-L/2, -W/2], end=[L/2, -W/2], layer='F.SilkS'))

	kicad_mod.append(Line(start=[-L/2, W/2 - PW / 2], end=[-L/2, W/2], layer='F.SilkS'))
	#kicad_mod.append(Line(start=[-L/2 + PTW, W/2 - PW / 2], end=[-L/2 + PTW, W/2], layer='F.SilkS'))
	kicad_mod.append(Line(start=[L/2, W/2], end=[L/2, W/2 - PW / 2], layer='F.SilkS'))
	kicad_mod.append(Line(start=[-L/2, W/2], end=[L/2, W/2], layer='F.SilkS'))

	# positive pin marking on both sides
	mark_x = -L / 2 - PL / 2 - min(min(W, L)*0.2, 0.6);
	kicad_mod.append(Line(start=[mark_x, -W/2], end=[mark_x, W/2], layer='F.SilkS'))
	kicad_mod.append(Line(start=[-L/2 + PTW, -W/2], end=[-L/2 + PTW, W/2], layer='F.SilkS'))

	# create courtyard
	kicad_mod.append(RectLine(start=[-GX/2, -GY/2], end=[GX/2, GY/2], layer='F.CrtYd'))

	# create pads
	kicad_mod.append(Pad(number=1, type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT, at=[-C/2, 0], size=[PL, PW], layers=Pad.LAYERS_SMT, solder_mask_margin=MaskMargin));
	kicad_mod.append(Pad(number=2, type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT, at=[C/2, 0], size=[PL, PW], layers=Pad.LAYERS_SMT, solder_mask_margin=MaskMargin));


#  DIOC + Body Length + Body Width X Height 
#  DIOM + Body Length + Body Width X Height 
#  DIOMELF + Body Length + Body Diameter
#  DIOSC + Body Length X Body Width X Height - Pin Qty
def gen_dio(code):
	parts = re.split("([A-Z]+)(\d\d)(\d\d)X(\d+)([LMN])", code)

	code = parts[1];
	L = float(parts[2])/10
	W = float(parts[3])/10
	H = float(parts[4])/100
	PlaceDensity = parts[5]

	kicad_mod = Footprint(code)

	BaseTypes = {
		"DIOC": "Chip",
		"DIOM": "Molded",
		"DIOMELF": "MELF",
		"DIOSC": "Side Concave"
	};

	if code == "DIOC":
		gen_chip_package(kicad_mod, "Diode", L, W, PlaceDensity);
	elif code == "DIOM":
		gen_molded_package(kicad_mod, "Diode", L, W, PlaceDensity);
	else:
		raise "Unknown device "+code;

	# add model
	#kicad_mod.append(Model(filename="example.3dshapes/example_footprint.wrl",
	#					   at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))
	return kicad_mod;

# generate a chip capacitor footprint. Basically the same as chip resistor but we may want to adjust a few parameters
def gen_cap(code):
	parts = re.split("([A-Z]+)(\d\d)(\d\d)X(\d+)([LMN])", code)
	variant = parts[1];
	L = float(parts[2])/10
	W = float(parts[3])/10
	H = float(parts[4])/100
	PlaceDensity = parts[5]
	
	# include imperial units in the name for easy selection
	IL = int(100 * L / 24.5);
	IW = int(100 * W / 24.5);
	ILString = str(IL).rjust(2, '0')+str(IW).rjust(2, '0');

	kicad_mod = Footprint(code + "_" + ILString)

	if variant == "CAPC":
		gen_chip_package(kicad_mod, "Capacitor", L, W, PlaceDensity);
	elif variant == "CAPM":
		gen_molded_package(kicad_mod, "Capacitor", L, W, PlaceDensity);
	elif variant == "CAPMP":
		gen_molded_package(kicad_mod, "Capacitor, Polarized", L, W, PlaceDensity);
	else:
		raise "Unknown component type "+variant;

	# add model
	#kicad_mod.append(Model(filename="example.3dshapes/example_footprint.wrl",
	#					   at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))
	return kicad_mod;

# generate a chip capacitor footprint. Basically the same as chip resistor but we may want to adjust a few parameters
def gen_ind(code):
	parts = re.split("([A-Z]+)(\d+)X(\d+)([LMN])", code)
	variant = parts[1];
	L = float(parts[2][:len(parts[2])//2])/10
	W = float(parts[2][len(parts[2])//2:])/10
	H = float(parts[3])/100
	PlaceDensity = parts[4]
	
	# include imperial units in the name for easy selection
	IL = int(100 * L / 24.5);
	IW = int(100 * W / 24.5);
	ILString = str(IL).rjust(2, '0')+str(IW).rjust(2, '0');

	kicad_mod = Footprint(code + "_" + ILString)

	if variant == "INDC":
		gen_chip_package(kicad_mod, "Inductor", L, W, PlaceDensity);
	elif variant == "INDM":
		gen_molded_package(kicad_mod, "Inductor", L, W, PlaceDensity);
	else:
		raise "Unknown component type "+variant;

	# add model
	#kicad_mod.append(Model(filename="example.3dshapes/example_footprint.wrl",
	#					   at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))
	return kicad_mod;


dispatch = {
	"BGA": gen_bga,
	"CAPC": gen_cap,
	"CAPAE": gen_cap,
	"CAPMP": gen_cap,
	"DIOC": gen_dio,
	"DIOM": gen_dio,
	"DIOMELF": gen_dio,
	"DIOSC": gen_dio,
	"INDM": gen_ind
};

KISYSMOD="footprints/"
KISYS3DMOD="packages3d/"

files = [
	"chip_resistors.csv",
	"chip_capacitors.csv",
	"chip_inductors.csv"
]

for dbname in files:
	if not os.path.exists("data/"+dbname):
		continue;
	db = FootprintDatabase();
	db.load("data/"+dbname);
	for fp in db.Footprints:
		print("Generating footprint "+fp.props["NAME"]);

		lib = fp.props["TYPE"]+".3dshapes"
		if not os.path.exists("packages3d/"+lib):
			os.makedirs("packages3d/"+lib)
		fp.mesh.write(u"./packages3d/"+lib+"/"+fp.props["NAME"]+".wrl")

		file_handler = KicadFileHandler(fp.footprint)

		module = KISYSMOD+fp.props["TYPE"]+'.pretty/';
		if not os.path.exists(module):
			os.makedirs(module);

		file_handler.writeFile(module+fp.props["NAME"]+'.kicad_mod')

sys.exit(0);

if not os.path.exists(KISYSMOD):
	os.makedirs(KISYSMOD);

if not os.path.exists(KISYS3DMOD):
	os.makedirs(KISYS3DMOD);

with open('genipc.csv', 'rb') as csvfile:
	reader = csv.reader(csvfile, delimiter=',', quotechar='"')
	for row in reader:
		if len(row) < 1: continue;
		name = row[0];

		ctype = re.split("([A-Z]+)", name)[1];
		if not dispatch[ctype]: continue;

		for Type in ["M", "N", "L"]:
			footprint_name = name + Type;

			# init kicad footprint
			kicad_mod = dispatch[ctype](footprint_name)
			#kicad_mod.setAttribute("smd")

			# output kicad model
			file_handler = KicadFileHandler(kicad_mod)

			module = KISYSMOD+ctype+'.pretty/';
			if not os.path.exists(module):
				os.makedirs(module);

			file_handler.writeFile(module+footprint_name+'.kicad_mod')
