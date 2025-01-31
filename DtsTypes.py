from collections import namedtuple
from struct import pack, unpack
from enum import Enum

import math

try:
	import mathutils
	from mathutils import Vector
except ImportError:
	class Vector:
		def __init__(self, v=None):
			if v == None:
				self.x = 0
				self.y = 0
				self.z = 0
			else:
				self.x, self.y, self.z = v

def bit(n):
	return 1 << n

class Box:
	def __init__(self, min, max):
		self.min = min
		self.max = max

	def __repr__(self):
		return "({}, {})".format(self.min, self.max)

class Quaternion:
	def __init__(self, x=0, y=0, z=0, w=1):
		self.x = x
		self.y = y
		self.z = z
		self.w = w

	def __mul__(self, other):
		return Quaternion(
			+self.x*other.w +self.y*other.z -self.z*other.y +self.w*other.x,
			-self.x*other.z +self.y*other.w +self.z*other.x +self.w*other.y,
			+self.x*other.y -self.y*other.x +self.z*other.w +self.w*other.z,
			-self.x*other.x -self.y*other.y -self.z*other.z +self.w*other.w)

	def __repr__(self):
		x = math.floor(self.x * 10000 + 0.5) / 10000
		y = math.floor(self.y * 10000 + 0.5) / 10000
		z = math.floor(self.z * 10000 + 0.5) / 10000
		w = math.floor(self.w * 10000 + 0.5) / 10000
		return "({}, {}, {}, {})".format(x, y, z, w)

	def __iter__(self):
		yield self.x
		yield self.y
		yield self.z
		yield self.w

	def to_blender(self):
		return mathutils.Quaternion((-self.w, self.x, self.y, self.z))

	def apply(self, v):
		v0 = v.x
		v1 = v.y
		v2 = v.z
		v3 = 0.0
		c0 = -self.x
		c1 = -self.y
		c2 = -self.z
		c3 = self.w
		s0 = self.x
		s1 = self.y
		s2 = self.z
		s3 = self.w
		ir0 = +c0*v3 +c1*v2 -c2*v1 +c3*v0
		ir1 = -c0*v2 +c1*v3 +c2*v0 +c3*v1
		ir2 = +c0*v1 -c1*v0 +c2*v3 +c3*v2
		ir3 = -c0*v0 -c1*v1 -c2*v2 +c3*v3
		r0 = +ir0*s3 +ir1*s2 -ir2*s1 +ir3*s0
		r1 = -ir0*s2 +ir1*s3 +ir2*s0 +ir3*s1
		r2 = +ir0*s1 -ir1*s0 +ir2*s3 +ir3*s2
		#r3 = -ir0*s0 -ir1*s1 -ir2*s2 +ir3*s3
		return Vector((r0, r1, r2))

class Node:
	def __init__(self, name, parent=-1):
		self.name = name
		self.parent = parent

		# Unused
		self.firstObject = -1
		self.firstChild = -1
		self.nextSibling = -1

	def write(self, stream):
		stream.write32(
			self.name, self.parent,
			self.firstObject, self.firstChild, self.nextSibling)

	@classmethod
	def read(cls, stream):
		obj = cls(stream.read32(), stream.read32())
		obj.firstObject = stream.read32()
		obj.firstChild = stream.read32()
		obj.nextSibling = stream.read32()
		return obj

class Object:
	def __init__(self, name, numMeshes, firstMesh, node):
		self.name = name
		self.numMeshes = numMeshes
		self.firstMesh = firstMesh
		self.node = node

		# Unused
		self.nextSibling = -1
		self.firstDecal = -1

	def write(self, stream):
		stream.write32(
			self.name, self.numMeshes, self.firstMesh,
			self.node, self.nextSibling, self.firstDecal)

	@classmethod
	def read(cls, stream):
		obj = cls(stream.read32(), stream.read32(), stream.read32(), stream.read32())
		obj.nextSibling = stream.read32()
		obj.firstDecal = stream.read32()
		return obj

class IflMaterial:
	def __init__(self, name, slot, firstFrame, time, numFrames):
		self.name = name
		self.slot = slot
		self.firstFrame = firstFrame
		self.time = time
		self.numFrames = numFrames

	def write(self, stream):
		stream.write32(
			self.name, self.slot, self.firstFrame,
			self.time, self.numFrames)

	@classmethod
	def read(cls, stream):
		return cls(
			stream.read32(), stream.read32(),
			stream.read32(), stream.read32(), stream.read32())

class Subshape:
	def __init__(self, firstNode, firstObject, firstDecal, numNodes, numObjects, numDecals):
		self.firstNode = firstNode
		self.firstObject = firstObject
		self.firstDecal = firstDecal
		self.numNodes = numNodes
		self.numObjects = numObjects
		self.numDecals = numDecals

class ObjectState:
	def __init__(self, vis, frame, matFrame):
		self.vis = vis
		self.frame = frame
		self.matFrame = matFrame

	def write(self, stream):
		stream.write_float(self.vis)
		stream.write32(self.frame, self.matFrame)

	@classmethod
	def read(cls, stream):
		return cls(stream.read_float(), stream.read32(), stream.read32())

class Trigger:
	StateOn = bit(31)
	InvertOnReverse = bit(30)

	def __init__(self, state, pos):
		self.state = state
		self.pos = pos

	def write(self, stream):
		stream.write32(self.state)
		stream.write_float(self.pos)

	@classmethod
	def read(cls, stream):
		return cls(stream.read32(), stream.read_float())

class DetailLevel:
	def __init__(self, name, subshape, objectDetail, size, avgError=-1.0, maxError=-1.0, polyCount=0):
		self.name = name
		self.subshape = subshape
		self.objectDetail = objectDetail
		self.size = size

		# Unused
		self.avgError = -1.0
		self.maxError = -1.0
		self.polyCount = 0

	def write(self, stream):
		stream.write32(self.name, self.subshape, self.objectDetail)
		stream.write_float(self.size, self.avgError, self.maxError)
		stream.write32(self.polyCount)

	@classmethod
	def read(cls, stream):
		obj = cls(stream.read32(), stream.read32(), stream.read32(), stream.read_float())
		obj.avgError = stream.read_float()
		obj.maxError = stream.read_float()
		obj.polyCount = stream.read32()
		return obj

class Primitive:
	Triangles = 0x00000000
	Strip = 0x40000000
	Fan = 0x80000000
	TypeMask = 0xC0000000
	Indexed = 0x20000000
	NoMaterial = 0x10000000
	MaterialMask = 0x0FFFFFFF

	def __init__(self, firstElement, numElements, type):
		self.firstElement = firstElement
		self.numElements = numElements
		self.type = type

	def write(self, stream):
		stream.write16(self.firstElement, self.numElements)
		stream.write32(self.type)

	@classmethod
	def read(cls, stream):
		return cls(stream.read16(), stream.read16(), stream.read32())

class Mesh:
	StandardType = 0
	SkinType = 1
	DecalType = 2
	SortedType = 3
	NullType = 4
	TypeMask = 7

	Billboard = bit(31)
	HasDetailTexture = bit(30)
	BillboardZAxis = bit(29)
	UseEncodedNormals = bit(28)

	def __init__(self, mtype):
		self.bounds = Box(Vector(), Vector())
		self.center = Vector()
		self.radius = 0
		self.numFrames = 1
		self.numMatFrames = 1
		self.vertsPerFrame = 1
		self.parent = -1
		self.type = mtype
		self.verts = []
		self.tverts = []
		self.normals = []
		self.enormals = []
		self.primitives = []
		self.indices = []
		self.mindices = []

	def get_type(self):
		return self.type & Mesh.TypeMask

	def get_flags(self, flag=0xFFFFFFFF):
		return self.type & flag

	def set_flags(self, flag):
		self.type |= flag

	def calculate_bounds(self, trans, rot):
		box = Box(
			Vector(( 10e30,  10e30,  10e30)),
			Vector((-10e30, -10e30, -10e30)))

		for vert in self.verts:
			co = rot.apply(vert) + trans

			box.min.x = min(box.min.x, co.x)
			box.min.y = min(box.min.y, co.y)
			box.min.z = min(box.min.z, co.z)
			box.max.x = max(box.max.x, co.x)
			box.max.y = max(box.max.y, co.y)
			box.max.z = max(box.max.z, co.z)

		return box

	def calculate_radius(self, trans, rot, center):
		radius = 0.0

		for vert in self.verts:
			tv = rot.apply(vert) + trans
			radius = max(radius, (tv - center).length)

		return radius

	def calculate_radius_tube(self, trans, rot, center):
		radius = 0

		for vert in self.verts:
			tv = rot.apply(vert) + trans
			delta = tv - center
			radius = max(radius, Vector((delta.x, delta.y)).length)

		return radius

	def write(self, stream):
		mtype = self.get_type()
		stream.write32(self.type)

		if mtype == Mesh.NullType:
			return

		stream.guard()
		stream.write32(self.numFrames, self.numMatFrames, self.parent)
		stream.write_box(self.bounds)
		stream.write_vec3(self.center)
		stream.write_float(self.radius)

		# Geometry data
		stream.write32(len(self.verts))
		for vert in self.verts:
			stream.write_vec3(vert)
		stream.write32(len(self.tverts))
		for tvert in self.tverts:
			stream.write_vec2(tvert)

		assert len(self.normals) == len(self.verts)
		assert len(self.enormals) == len(self.verts)
		for normal in self.normals:
			stream.write_vec3(normal)
		for enormal in self.enormals:
			stream.write8(enormal)

		# Primitives and other stuff
		stream.write32(len(self.primitives))
		for prim in self.primitives:
			prim.write(stream)

		#if stream.dtsVersion >= 25:
		stream.write32(len(self.indices))
		stream.write16(*self.indices)
		stream.write32(len(self.mindices))
		stream.write16(*self.mindices)
		stream.write32(self.vertsPerFrame)
		stream.write32(self.get_flags())
		stream.guard()

		mtype = self.get_type()

		if mtype != Mesh.StandardType:
			raise ValueError("cannot write non standard mesh")

	def read_standard_mesh(self, stream):
		stream.guard()

		self.numFrames = stream.read32()
		self.numMatFrames = stream.read32()
		self.parent = stream.read32()
		self.bounds = stream.read_box()
		self.center = stream.read_vec3()
		self.radius = stream.read_float()

		# Geometry data
		n_vert = stream.read32()
		self.verts = [stream.read_vec3() for i in range(n_vert)]
		n_tvert = stream.read32()
		self.tverts = [stream.read_vec2() for i in range(n_tvert)]
		self.normals = [stream.read_vec3() for i in range(n_vert)]
		# TODO: don't read this when not relevant
		self.enormals = [stream.read8() for i in range(n_vert)]

		# Primitives and other stuff
		self.primitives = [Primitive.read(stream) for i in range(stream.read32())]
		self.indices = [stream.read16() for i in range(stream.read32())]
		self.mindices = [stream.read16() for i in range(stream.read32())]
		self.vertsPerFrame = stream.read32()
		self.set_flags(stream.read32())

		stream.guard()

	def read_skin_mesh(self, stream):
		self.read_standard_mesh(stream)

		numVerts = sz = stream.read32()
		self.verts = [stream.read_vec3() for i in range(sz)]

		self.normals = [stream.read_vec3() for i in range(numVerts)]
		self.enormals = [stream.read8() for i in range(numVerts)]

		sz = stream.read32()
		self.initialTransforms = [[stream.read32() for i in range(16)] for i in range(sz)]
		sz = stream.read32()
		self.vertexIndexList = [stream.read32() for i in range(sz)]
		self.boneIndexList = [stream.read32() for i in range(sz)]
		self.weightList = [stream.read32() for i in range(sz)]
		sz = stream.read32()
		self.nodeIndexList = [stream.read32() for i in range(sz)]

		stream.guard()

		# allocShape32(0)

	@classmethod
	def read(cls, stream):
		mtype = stream.read32() & Mesh.TypeMask
		mesh = cls(mtype)

		if mtype == Mesh.StandardType:
			mesh.read_standard_mesh(stream)
		elif mtype == Mesh.SkinType:
			mesh.read_skin_mesh(stream)
		# others here
		elif mtype == Mesh.NullType:
			pass
		else:
			raise ValueError("don't know how to read {} mesh".format(mtype))

		return mesh

class Material:
	SWrap            = 0x00000001
	TWrap            = 0x00000002
	Translucent      = 0x00000004
	Additive         = 0x00000008
	Subtractive      = 0x00000010
	SelfIlluminating = 0x00000020
	NeverEnvMap      = 0x00000040
	NoMipMap         = 0x00000080
	MipMapZeroBorder = 0x00000100
	IFLMaterial      = 0x08000000
	IFLFrame         = 0x10000000
	DetailMap        = 0x20000000
	BumpMap          = 0x40000000
	ReflectanceMap   = 0x80000000
	AuxiliaryMask    = 0xE0000000

	def __init__(self, name="", flags=0,
		reflectanceMap=-1, bumpMap=-1, detailMap=-1,
		detailScale=1.0, reflectance=0.0):
		self.name = name
		self.flags = flags
		self.reflectanceMap = reflectanceMap
		self.bumpMap = bumpMap
		self.detailMap = detailMap
		self.detailScale = detailScale
		self.reflectance = reflectance

def read_bit_set(fd):
	dummy, numWords = unpack("<ii", fd.read(8))
	words = unpack(str(numWords) + "i", fd.read(4 * numWords))
	total = len(words) * 32
	return [(words[i >> 5] & (1 << (i & 31))) != 0 for i in range(total)]

def write_bit_set(fd, bits):
	numWords = int(math.ceil(len(bits) / 32.0))
	words = [0] * numWords

	for i, bit in enumerate(bits):
		if bit:
			words[i >> 5] |= 1 << (i & 31)

	fd.write(pack("<ii", numWords, numWords))

	for word in words:
		fd.write(pack("<i", word))

class Sequence:
	UniformScale = bit(0)
	AlignedScale = bit(1)
	ArbitraryScale = bit(2)
	Blend = bit(3)
	Cyclic = bit(4)
	MakePath = bit(5)
	IflInit = bit(6)
	HasTranslucency = bit(7)

	def __init__(self):
		# todo: get rid of this
		self.nameIndex = -1
		self.name = None
		self.flags = 0
		self.numKeyframes = 0
		self.duration = 0
		self.priority = 0
		self.firstGroundFrame = 0
		self.numGroundFrames = 0
		self.baseRotation = 0
		self.baseTranslation = 0
		self.baseScale = 0
		self.baseObjectState = 0
		self.baseDecalState = 0
		self.firstTrigger = 0
		self.numTriggers = 0
		self.toolBegin = 0

		self.rotationMatters = []
		self.translationMatters = []
		self.scaleMatters = []
		self.decalMatters = []
		self.iflMatters = []
		self.visMatters = []
		self.frameMatters = []
		self.matFrameMatters = []

	def write(self, fd, writeIndex=True):
		if writeIndex:
			fd.write(pack("<i", self.nameIndex))
		fd.write(pack("<I", self.flags))
		fd.write(pack("<i", self.numKeyframes))
		fd.write(pack("<f", self.duration))
		fd.write(pack("<i", self.priority))
		fd.write(pack("<i", self.firstGroundFrame))
		fd.write(pack("<i", self.numGroundFrames))
		fd.write(pack("<i", self.baseRotation))
		fd.write(pack("<i", self.baseTranslation))
		fd.write(pack("<i", self.baseScale))
		fd.write(pack("<i", self.baseObjectState))
		fd.write(pack("<i", self.baseDecalState))
		fd.write(pack("<i", self.firstTrigger))
		fd.write(pack("<i", self.numTriggers))
		fd.write(pack("<f", self.toolBegin))

		write_bit_set(fd, self.rotationMatters)
		write_bit_set(fd, self.translationMatters)
		write_bit_set(fd, self.scaleMatters)
		write_bit_set(fd, self.decalMatters)
		write_bit_set(fd, self.iflMatters)
		write_bit_set(fd, self.visMatters)
		write_bit_set(fd, self.frameMatters)
		write_bit_set(fd, self.matFrameMatters)

	@classmethod
	def read_bit_set(cls, fd):
		dummy = unpack("i", fd.read(4))[0]
		numWords = unpack("i", fd.read(4))[0]
		return unpack(str(numWords) + "i", fd.read(4 * numWords))

	@classmethod
	def read(cls, fd, readIndex=True):
		seq = cls()

		if readIndex:
			seq.nameIndex = unpack("i", fd.read(4))[0]
		seq.flags = unpack("I", fd.read(4))[0]
		seq.numKeyframes = unpack("i", fd.read(4))[0]
		seq.duration = unpack("f", fd.read(4))[0]
		seq.priority = unpack("i", fd.read(4))[0]
		seq.firstGroundFrame = unpack("i", fd.read(4))[0]
		seq.numGroundFrames = unpack("i", fd.read(4))[0]
		seq.baseRotation = unpack("i", fd.read(4))[0]
		seq.baseTranslation = unpack("i", fd.read(4))[0]
		seq.baseScale = unpack("i", fd.read(4))[0]
		seq.baseObjectState = unpack("i", fd.read(4))[0]
		seq.baseDecalState = unpack("i", fd.read(4))[0]
		seq.firstTrigger = unpack("i", fd.read(4))[0]
		seq.numTriggers = unpack("i", fd.read(4))[0]
		seq.toolBegin = unpack("f", fd.read(4))[0]

		seq.rotationMatters = read_bit_set(fd)
		seq.translationMatters = read_bit_set(fd)
		seq.scaleMatters = read_bit_set(fd)
		seq.decalMatters = read_bit_set(fd)
		seq.iflMatters = read_bit_set(fd)
		seq.visMatters = read_bit_set(fd)
		seq.frameMatters = read_bit_set(fd)
		seq.matFrameMatters = read_bit_set(fd)

		return seq
