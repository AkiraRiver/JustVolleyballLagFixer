extends RefCounted

# [mod/perf] disk caches for work the game redoes on every launch:
# hair fitted to the head mesh (ModelRig._fit_hair) and the face-art centres
# read back from the GPU (FaceParts). One folder per game build, so an update
# never reuses stale data; older folders are deleted. The demo and the full
# game share user://, so each keeps its own root.

const BUILD: = "__BUILD_ID__"
static var ROOT: = "user://jv_mod_cache" if LaunchGate.is_demo() else "user://jv_mod_cache_full"

static var _dir_ok: = false
static var _kv: ConfigFile = null

static func dir() -> String:
	var d: = ROOT.path_join(BUILD)
	if not _dir_ok:
		_dir_ok = true
		DirAccess.make_dir_recursive_absolute(d)
		for old in DirAccess.get_directories_at(ROOT):
			if old != BUILD:
				_rm_tree(ROOT.path_join(old))
	return d

static func _rm_tree(path: String) -> void:
	for f in DirAccess.get_files_at(path):
		DirAccess.remove_absolute(path.path_join(f))
	for sub in DirAccess.get_directories_at(path):
		_rm_tree(path.path_join(sub))
	DirAccess.remove_absolute(path)

static func get_value(key: String, default: Variant = null) -> Variant:
	if _kv == null:
		_kv = ConfigFile.new()
		_kv.load(dir().path_join("values.cfg"))
	# a null default counts as "no default" for ConfigFile and logs an error
	return _kv.get_value("v", key) if _kv.has_section_key("v", key) else default

static func put_value(key: String, value: Variant) -> void:
	get_value(key)
	_kv.set_value("v", key, value)
	_kv.save(dir().path_join("values.cfg"))



static func hair_key(name: String, flip: bool) -> String:
	return "hair_%s_%d" % [name.validate_filename(), int(flip)]

# fitted meshes for `parts` (as built by ModelRig._fit_collect), or [] on a miss.
# Materials are not stored; they come back from the source meshes.
static func hair_load(key: String, parts: Array) -> Array:
	var out: Array = []
	for i in parts.size():
		var p: = dir().path_join("%s_%d.res" % [key, i])
		if not FileAccess.file_exists(p):
			return []
		var m: = ResourceLoader.load(p, "", ResourceLoader.CACHE_MODE_IGNORE) as ArrayMesh
		var src: = (parts[i][0] as MeshInstance3D).mesh
		if m == null or src == null or m.get_surface_count() != src.get_surface_count():
			return []
		for si in m.get_surface_count():
			m.surface_set_material(si, src.surface_get_material(si))
		out.append(m)
	return out

static func hair_save(key: String, meshes: Array) -> void:
	for i in meshes.size():
		var src: = meshes[i] as ArrayMesh
		if src == null:
			return
		var m: = src.duplicate() as ArrayMesh
		for si in m.get_surface_count():
			m.surface_set_material(si, null)
		ResourceSaver.save(m, dir().path_join("%s_%d.res" % [key, i]), ResourceSaver.FLAG_COMPRESS)
