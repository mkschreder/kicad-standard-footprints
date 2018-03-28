import csv
import re
from ComponentChip import *

class FootprintProperty(object):
	def __init__(self, value):
		self.value = value;
	def __get__(self, obj, objtype):
		return self.value
	def __str__(self):
		return str(self.value)

class FootprintDescriptor(object):
	def __init__(self, props):
		self.props = props;
		if not props["NAME"]:
			raise "Missing IPC name"
		# parse the properties and generate a set of fields for this particular descriptor
		ctype = re.split("([A-Z]+)", props["NAME"])[1];
		if not ctype:
			raise "Could not parse out component type from name "+props["NAME"];
		for k in props:
			setattr(self.__class__, k, FootprintProperty(props[k]));

class FootprintDatabase(object):
	def __init__(self):
		self.footprints = [];

	@property
	def Footprints(self):
		return self.footprints;

	def load(self, csv_name):
		with open(csv_name, 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=';', quotechar='"')
			row_num = 0;
			props = {};
			name_row = [];
			for row in reader:
				if row_num == 0:
					# load names
					for i in range(0, len(row)):
						props[row[i]] = None;
					if not "NAME" in props:
						raise "CSV file should have a title row with valid property names";
					name_row = row;
					row_num += 1;
					continue
				
				for i in range(0, len(row)):
					props[name_row[i]] = row[i];

				props["TYPE"] = re.split("([A-Z]+)", props["NAME"])[1];
				if props["TYPE"] in ["RESC", "CAPC", "DIOC", "LEDC"]:
					fp = ComponentChip(props);	

				self.footprints.append(fp)
