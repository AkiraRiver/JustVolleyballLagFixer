extends RefCounted

# [lag fixer] started from the intro splash: loads on worker threads what the
# title, the menu and every character build would otherwise load one by one
# on the main thread (scenes, hair models, face art). Later load() calls then
# get the cached resource instead of blocking.

const SCENES: = [
	"res://game/ui/title.tscn",
	"res://game/ui/menu.tscn",
	"res://game/main/main.tscn",
]

static var _started: = false

# what a bug report needs, in godot.log
static func _report() -> void:
	var lite: = preload("res://game/mods/perf_lite.gd")
	var on: Array = []
	for k in lite.KEYS:
		if lite.enabled(k):
			on.append(k)
	print("[lag fixer] build %s | %s %s | %s | gpu: %s (%s) api %s | render thread model %s | args %s | light stages %s" % [
		preload("res://game/mods/perf_cache.gd").BUILD,
		OS.get_name(), OS.get_version(),
		RenderingServer.get_current_rendering_driver_name(),
		RenderingServer.get_video_adapter_name(), RenderingServer.get_video_adapter_vendor(),
		RenderingServer.get_video_adapter_api_version(),
		str(ProjectSettings.get_setting("rendering/driver/threads/thread_model", "?")),
		str(OS.get_cmdline_args()), str(on)])

static func start() -> void:
	if _started:
		return
	_started = true
	_report()
	# scenes first: the title is waited on as soon as the splash ends, and the
	# worker pool serves requests in order
	var paths: Array = SCENES.duplicate()
	# stage venues: the menu's practice court and every match load one
	# synchronously (only the stages this build ships, 3 in the demo; the full
	# game ships 9, so there only the ones the menu and the last match use)
	var want: = {Stage.home(): true, "void": true,
		String(GameConfig.freeplay_stage): true, String(GameConfig.stage): true}
	for id in Stage.STAGES:
		if Stage.in_build(String(id)) and (LaunchGate.is_demo() or want.has(String(id))):
			var s: = Stage.info(String(id))
			for k in ["venue", "look"]:
				if String(s.get(k, "")) != "":
					paths.append(String(s[k]))
	for f in FaceParts.FEATURES:
		for p in FaceParts.options(f):
			paths.append(p)
			var base: = String(p).get_basename()
			for suf in ["_iris", "_fill", "_line", "_lash"]:
				paths.append(base + suf + ".png")
	for f in DirAccess.get_files_at("res://game/character/faces/blush"):
		paths.append("res://game/character/faces/blush/" + f.trim_suffix(".import").trim_suffix(".remap"))
	var hair: = CharacterConfig.hair_meshes()
	for i in range(1, hair.size()):
		paths.append(ModelRig.HAIR_DIR % hair[i])
	var facial: = CharacterConfig.facial_hair_meshes()
	for i in range(1, facial.size()):
		paths.append("%s/%s.blend" % [CharacterConfig.FACIAL_HAIR_DIR, facial[i]])
	var seen: = {}
	for p in paths:
		if seen.has(p) or not String(p).begins_with("res://"):
			continue
		seen[p] = true
		if ResourceLoader.exists(p) and not ResourceLoader.has_cached(p):
			ResourceLoader.load_threaded_request(p)
	# fit every hairstyle to the head on worker threads (the game's own
	# HairWarm, normally started after the title); results go to the disk
	# cache, so this is only real work on the first launch of a game build
	var tree: = Engine.get_main_loop() as SceneTree
	var cached: = 0
	for f in DirAccess.get_files_at(preload("res://game/mods/perf_cache.gd").dir()):
		if f.begins_with("hair_"):
			cached += 1
	if tree != null and cached < hair.size():
		tree.create_timer(0.6).timeout.connect( func(): _warm_hair())

static func _warm_hair() -> void:
	CharacterPortrait.HairWarm.warm_all(false)
	CharacterPortrait.HairWarm.warm_all(true)
