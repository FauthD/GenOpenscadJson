#!/usr/bin/env python3

import argparse
from pathlib import Path
import os
import json
import yaml
from yaml.loader import SafeLoader
from collections import ChainMap
import itertools

'''Some constants'''
parameterSets="parameterSets"
design_default_values="design default values"

'''The translator in a class'''
class Runner():
	def __init__(self):
		self.input_files = []
		self.output_file = ""
		self.split_dir = ""
		self.customs_in = []
		self.customs_out = {}
		self.customs_out[parameterSets] = {}
		self.customs_out["fileFormatVersion"] = "1"
		self.verbose=False
		self.list=False

	'''Parse the command line'''
	def cmdline(self):
		parser = argparse.ArgumentParser()

		parser.add_argument("input_files", nargs='*', action="append")
		parser.add_argument("-d", "--directory", action="append", default=[])
		parser.add_argument("-o", "--output", action="store")
		parser.add_argument("-s", "--split", action="store")
		parser.add_argument("-v", "--verbose", action="store_true")
		parser.add_argument("-l", "--list", action="store_true")

		args = parser.parse_args()
		self.output_file = args.output
		self.split_dir = args.split
		self.verbose = args.verbose
		self.list = args.list

		if((self.output_file==None) and (self.split_dir==None) and (not self.list)):
			print("Either an output file or a split destination directory or list must be specified")
			raise SystemExit(1)

		self.input_files = list(itertools.chain(*args.input_files)) 
		for dir in args.directory:
			target_dir = Path(dir)

			if not target_dir.exists():
				print("The target directory {} doesn't exist".format(dir))
				raise SystemExit(1)

			for entry in target_dir.iterdir():
				self.input_files.append(os.path.join(target_dir, entry.name))

	'''Read a yaml or json file'''
	def parse_file(self, path):
		name = os.path.splitext(os.path.basename(path))[0]
		ext = os.path.splitext(os.path.basename(path))[1]

		with open(path, 'r') as f:
			if((ext=='.yaml') or (ext=='.yml')):
				data = list(yaml.load_all(f, Loader=SafeLoader))[0]
			elif (ext=='.json'):
				data = json.load(f)
			else:
				print("Skiped file {}".format(path))
				data = None

			if(data != None):
				flavour = {}
				flavour[name] = data
				self.customs_in.append(flavour)

	'''Read all listed yaml or json files'''
	def parse_files(self):
		for f in self.input_files:
			self.parse_file(f)

	'''Fill the flavour with values from default'''
	def expand(self, flavour):
		for name in flavour:
			part_list = flavour[name]

			# now handle the flavours if they exist
			if ('default' in part_list):
				default = part_list['default']
				if(default==None):
					default={}
				parts = part_list['parts']
				if(parts==None):
					parts={}

				for part in parts.items():
					part_name = name + '_' + part[0]
					n = default.copy()
					n.update(part[1])
					if(self.verbose):
						print("Expanding {}".format(part_name))
					self.customs_out[parameterSets][part_name]=n.copy()

			# handle design_default_values if they exist
			elif (design_default_values in part_list):
				if(self.verbose):
					print("Handling {}".format(design_default_values))
				n = part_list[design_default_values].copy()
				self.customs_out[parameterSets][design_default_values]=n.copy()
			else:
				# here we can read a normal customizer file from openscad
				if(self.verbose):
					print("Handling openscad json file")
				self.customs_out=part_list.copy()

	'''Fill the flavours with values from default'''
	def expands(self):
		for f in self.customs_in:
			self.expand(f)

	'''Print a list a flavours to be used in make'''
	def show_list(self):
		lst=''
		for key in self.customs_out[parameterSets].keys():
			if(key != design_default_values):
				lst += key +' '
		print(lst)

	def write_json(self):
		with open(self.output_file, 'w') as f:
			json.dump(self.customs_out, f, sort_keys=False, indent=4)

	def write_yaml(self):
		with open(self.output_file, 'w') as f:
			yaml.dump(self.customs_out, f)

	'''Write either a yaml or json file'''
	def write(self):
		if(not self.list):
			if(self.verbose):
				print("Creating {}".format(self.output_file))
			ext = os.path.splitext(os.path.basename(self.output_file))[1]
			if (ext=='.json'):
				self.write_json()
			elif((ext=='.yaml') or (ext=='.yml')):
				self.write_yaml()
		else:
			self.show_list()

	'''Split the flavours into separate files for easier comparisons'''
	def split(self):
		os.makedirs(self.split_dir, exist_ok=True)
		
		flavours = self.customs_out[parameterSets]
		for key in flavours:
			single = {key: flavours[key]}
			filename=os.path.join(self.split_dir, key)
			if(self.verbose):
				print("Creating {}".format(filename))
			with open(filename, 'w') as f:
				yaml.dump(single, f)


if __name__ == "__main__":
	r = Runner()
	r.cmdline()
	r.parse_files()
	r.expands()
	if (r.split_dir != None):
		r.split()
	else:
		r.write()
