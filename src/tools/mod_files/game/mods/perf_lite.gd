extends RefCounted

# [mod/perf] lighter stages, set in (REGLAGES.bat writes it), saved in
# user://jv_mod_lite.cfg. Applies when a stage is built (next match or menu
# court), never to gameplay: collisions, lines and the ball are untouched.
#   crowd     background people (beach walkers/sitters, arena and gym stands)
#   trails    footprints in the sand (a 1024px texture redrawn every frame)
#             and the finely cut sand floor they need
#   anim      purely decorative motion (waves, cloud ripples, floating cubes)
#   backdrop  extra scenery: beach town/boardwalk/props, grass hills/trees,
#             sun patches on gym floors (a big see-through quad), the floating
#             cubes/spheres of the void, and the nationals live-feed screens
#             (a second render of the match every 3 frames; see main.gd patch)

const PATH: = "user://jv_mod_lite.cfg"
const KEYS: = ["crowd", "trails", "anim", "backdrop"]
const LABELS: = {
	"crowd": "no background people",
	"trails": "no footprints in the sand",
	"anim": "no moving scenery (sea, clouds, cubes)",
	"backdrop": "no extra scenery (town, hills, sun patches, arena screens)",
}

# stage ids are looked up through Stage.info(id).venue, so these are by kit
const BACKDROP_NODES: = {
	"beach": ["City", "Boardwalk", "BeachProps", "Lamps", "Palms", "BeachTown"],
	"grass": ["Hills", "Trees"],
	"school": ["Sunlight"],
	"training": ["FloorGleam"],
	"void": ["SpaceCubes", "SpaceSpheres"],
}
# scripts whose _process only animates scenery
const ANIM_SCRIPTS: = ["ocean_time.gd", "cloud_ripples.gd", "space_cubes.gd", "space_spheres.gd"]

static var on: = {"crowd": true, "trails": true, "anim": true, "backdrop": true}
static var _loaded: = false

static func _load() -> void:
	if _loaded:
		return
	_loaded = true
	var cf: = ConfigFile.new()
	if cf.load(PATH) != OK:
		return
	for k in KEYS:
		on[k] = bool(cf.get_value("lite", k, on[k]))

static func enabled(key: String) -> bool:
	_load()
	return bool(on.get(key, false))

static func set_enabled(key: String, value: bool) -> void:
	_load()
	on[key] = value
	var cf: = ConfigFile.new()
	for k in KEYS:
		cf.set_value("lite", k, on[k])
	cf.save(PATH)

# Stage.val hook: per-stage settings the game already reads
static func stage_override(key: String) -> Variant:
	match key:
		"beach_people":
			return false if enabled("crowd") else null
		"sand_tess":
			return 48 if enabled("trails") else null
	return null

# called by main once the stage shell, sand and grass are in place
static func dress(shell: Node, id: String) -> void:
	if shell == null:
		return
	if enabled("anim"):
		for n in shell.find_children("*", "", true, false):
			var s: Script = n.get_script()
			if s != null and String(s.resource_path).get_file() in ANIM_SCRIPTS:
				n.set_process(false)
	if enabled("backdrop"):
		var kit: = String(Stage.info(id).get("venue", "")).get_file().get_basename()
		for nm in BACKDROP_NODES.get(kit, []):
			var n: = shell.get_node_or_null(NodePath(nm)) as Node3D
			if n != null:
				n.visible = false
				n.process_mode = Node.PROCESS_MODE_DISABLED
