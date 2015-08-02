from struct import pack, unpack, calcsize
from array import array

from .DtsTypes import *

# Shortcut for reading & writing struct data from & to a file descriptor
def ws(fd, spec, *values):
	fd.write(pack(spec, *values))

def read_multi(fd, count, spec):
	spec = str(count) + spec
	return unpack(spec, fd.read(calcsize(spec)))

class DtsOutputStream(object):
	def __init__(self, dtsVersion=24, exporterVersion=0):
		self.dtsVersion = dtsVersion
		self.exporterVersion = exporterVersion
		self.sequence = 0
		self.buffer32 = []
		self.buffer16 = []
		self.buffer8  = []

	def guard(self, specific=None):
		if specific != None:
			assert specific == self.sequence
		self.write32(self.sequence)
		self.write16(self.sequence)
		self.write8(self.sequence)
		self.sequence = self.sequence + 1

	def flush(self, fd):
		print("flush")

		# Force all buffers to have a size multiple of 4 bytes
		if len(self.buffer16) % 2 == 1: self.buffer16.append(0)
		while len(self.buffer8) % 4 != 0: self.buffer8.append(0)

		end32  =         len(self.buffer32)
		end16  = end32 + len(self.buffer16) // 2
		end8   = end16 + len(self.buffer8 ) // 4

		fd.write(pack("hhiii",
			self.dtsVersion, self.exporterVersion,
			end8, end32, end16))
		fd.write(pack(str(len(self.buffer32)) + "i", *self.buffer32))
		fd.write(pack(str(len(self.buffer16)) + "h", *self.buffer16))
		fd.write(pack(str(len(self.buffer8 )) + "b", *self.buffer8 ))

	def write32(self, *values):
		for value in values:
			assert type(value) == int, "type is {}, must be {}".format(type(value), int)
		self.buffer32.extend(values)

	def write16(self, *values):
		for value in values:
			assert type(value) == int, "type is {}, must be {}".format(type(value), int)
		self.buffer16.extend(values)

	def write8(self, *values):
		for value in values:
			assert type(value) == int, "type is {}, must be {}".format(type(value), int)
		self.buffer8.extend(values)

	def write_float(self, *values):
		self.write32(*map(lambda f: unpack("i", pack("f", f))[0], values))

	def write_string(self, string):
		self.write8(*string.encode("ascii"))
		self.write8(0)

	def write_point(self, point):
		self.write_float(point.x, point.y, point.z)

	def write_point2d(self, point):
		self.write_float(point.x, point.y)

	def write_box(self, box):
		self.write_point(box.min)
		self.write_point(box.max)

	def write_quat(self, quat):
		self.write16(
			int(quat.x * 32767.0),
			int(quat.y * 32767.0),
			int(quat.z * 32767.0),
			int(quat.w * 32767.0))

class DtsInputStream(object):
	def __init__(self, fd):
		self.sequence = 0
		self.dtsVersion, self.exporterVersion = unpack("hh", fd.read(4))
		end8, end32, end16 = unpack("iii", fd.read(12))
		num32 = end32
		num16 = (end16 - end32) * 2
		num8  = (end8  - end16) * 4
		self.buffer32 = array("i", read_multi(fd, num32, "i"))
		self.buffer16 = array("h", read_multi(fd, num16, "h"))
		self.buffer8  = array("b", read_multi(fd, num8 , "b"))
		self.tell32 = 0
		self.tell16 = 0
		self.tell8  = 0

	def guard(self, specific=None):
		if specific != None:
			assert specific == self.sequence
		assert self.sequence == self.read32()
		assert self.sequence == self.read16()
		assert self.sequence == self.read8()
		self.sequence = self.sequence + 1

	def read32(self):
		if self.tell32 >= len(self.buffer32):
			raise EOFError()

		data = self.buffer32[self.tell32]
		self.tell32 += 1
		return data

	def read16(self):
		if self.tell16 >= len(self.buffer16):
			raise EOFError()

		data = self.buffer16[self.tell16]
		self.tell16 += 1
		return data

	def read8(self):
		if self.tell8 >= len(self.buffer8):
			raise EOFError()

		data = self.buffer8[self.tell8]
		self.tell8 += 1
		return data

	def read_float(self):
		return unpack("f", pack("i", self.read32()))[0]

	def read_string(self):
		buffer = bytearray()
		while True:
			byte = self.read8()
			if byte == 0:
				break
			else:
				buffer.append(byte)
		return "".join(map(chr, buffer))

	def read_point(self):
		return Point(self.read_float(), self.read_float(), self.read_float())

	def read_point2d(self):
		return Point2D(self.read_float(), self.read_float())

	def read_box(self):
		return Box(self.read_point(), self.read_point())

	def read_quat(self):
		return Quaternion(
			self.read16() / 32767.0,
			self.read16() / 32767.0,
			self.read16() / 32767.0,
			self.read16() / 32767.0)

class DtsShape(object):
	def __init__(self):
		self.nodes = []
		self.objects = []
		self.decals = []
		self.subshapes = []
		self.iflmaterials = []
		self.materials = []
		self.default_rotations = []
		self.default_translations = []
		self.node_rotations = []
		self.node_translations = []
		self.node_scales_uniform = []
		self.node_scales_aligned = []
		self.node_scales_arbitrary = []
		self.node_scalerots_uniform = []
		self.ground_translations = []
		self.ground_rotations = []
		self.objectstates = []
		self.decalstates = []
		self.triggers = []
		self.detail_levels = []
		self.meshes = []
		self.sequences = []
		self.names = []
		self._names_lookup = {}

		self.smallest_size = 0.0
		self.smallest_detail_level = 0
		self.radius = 0.0
		self.radius_tube = 0.0
		print("point is", Point)
		print("tuple is", tuple)
		self.center = Point(0.0, 0.0, 0.0)
		self.bounds = Box(Point(0.0, 0.0, 0.0), Point(0.0, 0.0, 0.0))

	def name(self, string):
		index = self._names_lookup.get(string.lower())

		if index == None:
			index = len(self.names)
			self.names.append(string)
			self._names_lookup[string.lower()] = index

		return index

	def get_world(self, nodeid):
		chain = [nodeid]

		while self.nodes[nodeid].parent != -1:
			nodeid = self.nodes[nodeid].parent
			chain.append(nodeid)

		trans = Point(0, 0, 0)
		rot = Quaternion(0, 0, 0, 1)

		for i in reversed(chain):
			trans += rot.apply(self.default_rotations[i])
			rot = self.default_rotations[i] * rot

		return trans, rot

	def save(self, fd, dtsVersion=24):
		stream = DtsOutputStream(dtsVersion)

		# Header
		stream.write32(
			len(self.nodes),
			len(self.objects),
			len(self.decals),
			len(self.subshapes),
			len(self.iflmaterials),
			len(self.node_rotations),
			len(self.node_translations),
			len(self.node_scales_uniform),
			len(self.node_scales_aligned),
			len(self.node_scales_arbitrary),
			len(self.ground_translations),
			len(self.objectstates),
			len(self.decalstates),
			len(self.triggers),
			len(self.detail_levels),
			len(self.meshes),
			len(self.names),
		)
		stream.write32(int(self.smallest_size))
		stream.write32(self.smallest_detail_level)
		stream.guard(0)

		# Bounds
		stream.write_float(self.radius, self.radius_tube)
		stream.write_point(self.center)
		stream.write_box(self.bounds)
		stream.guard(1)

		# Nodes
		for node in self.nodes:
			node.write(stream)
		stream.guard(2)

		# Objects
		for obj in self.objects:
			obj.write(stream)
		stream.guard(3)

		# Decals
		for decal in self.decals:
			decal.write(stream)
		stream.guard(4)

		# IFL materials
		for ifl in self.iflmaterials:
			ifl.write(stream)
		stream.guard(5)

		# Subshapes
		for sub in self.subshapes:
			stream.write32(sub.firstNode)
		for sub in self.subshapes:
			stream.write32(sub.firstObject)
		for sub in self.subshapes:
			stream.write32(sub.firstDecal)
		stream.guard(6)
		for sub in self.subshapes:
			stream.write32(sub.numNodes)
		for sub in self.subshapes:
			stream.write32(sub.numObjects)
		for sub in self.subshapes:
			stream.write32(sub.numDecals)
		stream.guard(7)

		# Default translations and rotations
		assert len(self.default_rotations) == len(self.nodes)
		assert len(self.default_translations) == len(self.nodes)

		for i in range(len(self.nodes)):
			stream.write_quat(self.default_rotations[i])
			stream.write_point(self.default_translations[i])

		# Animation translations and rotations
		for point in self.node_translations:
			stream.write_point(point)
		for quat in self.node_rotations:
			stream.write_point(quat)
		stream.guard(8)

		# Default scales
		for point in self.node_scales_uniform:
			stream.write_point(point) # shouldn't this be float!?
		for point in self.node_scales_aligned:
			stream.write_point(point)
		for point in self.node_scales_arbitrary:
			stream.write_point(point)
		if dtsVersion >= 26:
			for quat in self.node_scalerots_arbitrary:
				stream.write_quat(quat)
		stream.guard(9)

		# Ground transformations
		assert len(self.ground_translations) == len(self.ground_rotations)
		for point in self.ground_translations:
			self.write_point(point)
		for quat in self.ground_rotations:
			self.write_quat(quat)
		stream.guard(10)

		# Object states
		for state in self.objectstates:
			state.write(stream)
		stream.guard(11)

		# Decal states
		for state in self.decalstates:
			state.write(stream)
		stream.guard(12)

		# Triggers
		for trigger in self.triggers:
			trigger.write(stream)
		stream.guard(13)

		# Detail levels
		for lod in self.detail_levels:
			lod.write(stream)
		stream.guard(14)

		# Meshes
		for mesh in self.meshes:
			mesh.write(stream)
		stream.guard()

		# Names
		for name in self.names:
			stream.write_string(name)
		stream.guard()

		# Finished with the 3-buffer section
		stream.flush(fd)

		# Sequences
		ws(fd, "i", len(self.sequences))

		for seq in self.sequences:
			raise RuntimeError()

		# Materials
		ws(fd, "b", 0x1)
		ws(fd, "i", len(self.materials))

		for mat in self.materials:
			if dtsVersion >= 26:
				ws(fd, "i", len(mat.name))
			else:
				ws(fd, "b", len(mat.name))

			fd.write(mat.name.encode("ascii"))
		for mat in self.materials:
			ws(fd, "i", mat.flags)
		for mat in self.materials:
			ws(fd, "i", mat.reflectanceMap)
		for mat in self.materials:
			ws(fd, "i", mat.bumpMap)
		for mat in self.materials:
			ws(fd, "i", mat.detailMap)
		if dtsVersion == 25:
			for mat in self.materials:
				fd.write(b"\x00\x00\x00\x00")
		for mat in self.materials:
			ws(fd, "f", mat.detailScale)
		for mat in self.materials:
			ws(fd, "f", mat.reflectance)

	def load(self, fd):
		stream = DtsInputStream(fd)

		# Header
		n_node = stream.read32()
		n_object = stream.read32()
		n_decal = stream.read32()
		n_subshape = stream.read32()
		n_ifl = stream.read32()

		if stream.dtsVersion < 22:
			n_noderotation = stream.read32()
			n_noderotation -= n_node
			n_nodetranslation = n_noderotation
			n_nodescaleuniform = 0
			n_nodescalealigned = 0
			n_nodescalearbitrary = 0
		else:
			n_noderotation = stream.read32()
			n_nodetranslation = stream.read32()
			n_nodescaleuniform = stream.read32()
			n_nodescalealigned = stream.read32()
			n_nodescalearbitrary = stream.read32()

		if stream.dtsVersion > 23:
			n_groundframe = stream.read32()
		else:
			n_groundframe = 0

		n_objectstate = stream.read32()
		n_decalstate = stream.read32()
		n_trigger = stream.read32()
		n_detaillevel = stream.read32()
		n_mesh = stream.read32()

		if stream.dtsVersion < 23:
			n_skin = stream.read32()
		else:
			n_skin = 0

		n_name = stream.read32()
		self.smallest_size = stream.read_float()
		self.smallest_detail_level = stream.read32()
		stream.guard()

		# Misc geometry properties
		self.radius = stream.read_float()
		self.radius_tube = stream.read_float()
		self.center = stream.read_point()
		self.bounds = stream.read_box()
		stream.guard()

		# Primary data
		self.nodes = [Node.read(stream) for i in range(n_node)]
		stream.guard()
		self.objects = [Object.read(stream) for i in range(n_object)]
		stream.guard()
		self.decals = [Decal.read(stream) for i in range(n_decal)]
		stream.guard()
		self.iflmaterials = [IflMaterial.read(stream) for i in range(n_ifl)]
		stream.guard()

		# Subshapes
		self.subshapes = [Subshape(0, 0, 0, 0, 0, 0) for i in range(n_subshape)]
		for i in range(n_subshape):
			self.subshapes[i].firstNode = stream.read32()
		for i in range(n_subshape):
			self.subshapes[i].firstObject = stream.read32()
		for i in range(n_subshape):
			self.subshapes[i].firstDecal = stream.read32()
		stream.guard()
		for i in range(n_subshape):
			self.subshapes[i].numNodes = stream.read32()
		for i in range(n_subshape):
			self.subshapes[i].numObjects = stream.read32()
		for i in range(n_subshape):
			self.subshapes[i].numDecals = stream.read32()
		stream.guard()

		# MeshIndexList (obsolete data)
		if stream.dtsVersion < 16:
			for i in range(stream.read32()):
				stream.read32()

		# Default translations and rotations
		self.default_rotations = [None] * n_node
		self.default_translations = [None] * n_node

		for i in range(n_node):
			self.default_rotations[i] = stream.read_quat()
			self.default_translations[i] = stream.read_point()

		# Animation translations and rotations
		self.node_translations = [stream.read_point() for i in range(n_nodetranslation)]
		self.node_rotations = [stream.read_quat() for i in range(n_noderotation)]
		stream.guard()

		# Default scales
		if stream.dtsVersion > 21:
			self.node_scales_uniform = [stream.read_point() for i in range(n_nodescaleuniform)]
			self.node_scales_aligned = [stream.read_point() for i in range(n_nodescalealigned)]
			self.node_scales_arbitrary = [stream.read_point() for i in range(n_nodescalearbitrary)]
			stream.guard()
		else:
			self.node_scales_uniform = [None] * n_nodescaleuniform
			self.node_scales_aligned = [None] * n_nodescalealigned
			self.node_scales_arbitrary = [None] * n_nodescalearbitrary
		# ???
		# print(stream.dtsVersion)
		# print(stream.sequence)
		# if stream.dtsVersion > 21:
		# 	what1 = stream.read32()
		# 	what2 = stream.read32()
		# 	what3 = stream.read32()
		# 	stream.guard()

		# Ground transformations
		if stream.dtsVersion > 23:
			self.ground_translations = [stream.read_point() for i in range(n_groundframe)]
			self.ground_rotations = [stream.read_quat() for i in range(n_groundframe)]
			stream.guard()
		else:
			self.ground_translations = [None] * n_groundframe
			self.ground_rotations = [None] * n_groundframe

		# Object states
		self.objectstates = [ObjectState.read(stream) for i in range(n_objectstate)]
		stream.guard()

		# Decal states
		self.decalstates = [stream.read32() for i in range(n_decalstate)]
		stream.guard()

		# Triggers
		self.triggers = [Trigger.read(stream) for i in range(n_trigger)]
		stream.guard()

		# Detail levels
		self.detail_levels = [DetailLevel.read(stream) for i in range(n_detaillevel)]
		stream.guard()

		# Meshes
		self.meshes = [Mesh.read(stream) for i in range(n_mesh)]
		stream.guard()

		# Names
		self.names = [None] * n_name
		self._names_lookup = {}

		for i in range(n_name):
			self.names[i] = stream.read_string()
			self._names_lookup[self.names[i]] = i

		stream.guard()

		self.alpha_in = [None] * n_detaillevel
		self.alpha_out = [None] * n_detaillevel

		if stream.dtsVersion >= 26:
			for i in range(n_detaillevel):
				self.alphaIn[i] = stream.read32()
			for i in range(n_detaillevel):
				self.alphaOut[i] = stream.read32()

		# Done with the tribuffer section
		n_sequence = unpack("i", fd.read(4))[0]
		self.sequences = [None] * n_sequence

		for i in range(n_sequence):
			self.sequences[i].append(Sequence.read(fd))

		material_type = unpack("b", fd.read(1))[0]
		assert material_type == 0x1

		n_material = unpack("i", fd.read(4))[0]
		self.materials = [Material() for i in range(n_material)]

		for i in range(n_material):
			if stream.dtsVersion >= 26:
				length = unpack("i", fd.read(4))[0]
			else:
				length = unpack("B", fd.read(1))[0]

			self.materials[i].name = fd.read(length).decode("ascii")

		for i in range(n_material):
			self.materials[i].flags = unpack("I", fd.read(4))[0]
		for i in range(n_material):
			self.materials[i].reflectanceMap = unpack("i", fd.read(4))[0]
		for i in range(n_material):
			self.materials[i].bumpMap = unpack("i", fd.read(4))[0]
		for i in range(n_material):
			self.materials[i].detailMap = unpack("i", fd.read(4))[0]

		if stream.dtsVersion == 25:
			for i in range(n_material):
				fd.read(4)

		for i in range(n_material):
			self.materials[i].detailScale = unpack("f", fd.read(4))[0]
		for i in range(n_material):
			self.materials[i].reflectance = unpack("f", fd.read(4))[0]