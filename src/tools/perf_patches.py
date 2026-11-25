# Performance patches. Each entry swaps one snippet of a decompiled game script.

from jvpatch import P

PC = 'preload("res://game/mods/perf_cache.gd")'
LITE = 'preload("res://game/mods/perf_lite.gd")'

PERF_PATCHES = [
    P("game/ui/boot/boot_intro.gd", "preload during the splash", """
func _ready() -> void :
    UiStyle.dark = false
""", """
func _ready() -> void :
    UiStyle.dark = false
    preload("res://game/mods/perf_boot.gd").start()
"""),

    # hair fit: try the disk cache before computing, store what was computed
    P("game/character/model_rig.gd", "hair fit disk cache", """
    var key: = fit_key(parts, _head_mesh)
    if not _fit_meshes.has(key):

        for pass_i in 2:
            var fitted: = _fit_build(parts, hf)
            for i in parts.size():
                (parts[i][0] as MeshInstance3D).mesh = fitted[i]
        var keep: Array = []
        for pt in parts:
            keep.append((pt[0] as MeshInstance3D).mesh)
        _fit_meshes[key] = keep
        return
""", """
    var key: = fit_key(parts, _head_mesh)
    var __names: = CharacterConfig.hair_meshes()
    var __dk: = %s.hair_key(__names[_hair_style], _hair_flipped)\\
    if _hair_style > 0 and _hair_style < __names.size() else ""
    if not _fit_meshes.has(key) and __dk != "":
        var __disk: = %s.hair_load(__dk, parts)
        if __disk.size() == parts.size():
            _fit_meshes[key] = __disk
    if not _fit_meshes.has(key):

        for pass_i in 2:
            var fitted: = _fit_build(parts, hf)
            for i in parts.size():
                (parts[i][0] as MeshInstance3D).mesh = fitted[i]
        var keep: Array = []
        for pt in parts:
            keep.append((pt[0] as MeshInstance3D).mesh)
        _fit_meshes[key] = keep
        if __dk != "":
            %s.hair_save(__dk, keep)
        return
""" % (PC, PC, PC)),

    # the background warm-up (HairWarm.prefit) also reads/writes the cache
    P("game/character/hair_warm.gd", "prefit disk cache hit", """
    if key == "" or ModelRig._fit_meshes.has(key):
        inst.free()
        _fitting.erase(id)
        _fitted[id] = true
        return
""", """
    var __dk: = %s.hair_key(CharacterConfig.hair_meshes()[style], flip)
    if key != "" and not ModelRig._fit_meshes.has(key):
        var __disk: = %s.hair_load(__dk, parts)
        if __disk.size() == parts.size():
            ModelRig._fit_meshes[key] = __disk
    if key == "" or ModelRig._fit_meshes.has(key):
        inst.free()
        _fitting.erase(id)
        _fitted[id] = true
        return
""" % (PC, PC)),

    P("game/character/hair_warm.gd", "prefit disk cache store", """
        ModelRig._fit_meshes[key] = keep
""", """
        ModelRig._fit_meshes[key] = keep
        %s.hair_save(__dk, keep)
""" % PC),

    # face-art centres: GPU readback (get_image) only once per game build
    P("game/character/face_parts.gd", "used_center cache", """
static func used_center(feature: String, idx: int) -> Vector2:
    var key: = "%s:%d" % [feature, idx]
    if _centers.has(key):
        return _centers[key]
""", """
static func used_center(feature: String, idx: int) -> Vector2:
    var key: = "%s:%d" % [feature, idx]
    if _centers.has(key):
        return _centers[key]
    var __c = """ + PC + """.get_value("fc:" + key)
    if __c is Vector2:
        _centers[key] = __c
        return __c
"""),

    P("game/character/face_parts.gd", "used_center store", """
            c = Vector2(ctr.x / img.get_width(), ctr.y / img.get_height())
    _centers[key] = c
""", """
            c = Vector2(ctr.x / img.get_width(), ctr.y / img.get_height())
    _centers[key] = c
    """ + PC + """.put_value("fc:" + key, c)
"""),

    P("game/character/face_parts.gd", "half_center cache", """
    var key: = "%s:%d:%s" % [feature, idx, "r" if right else "l"]
    if _centers.has(key):
        return _centers[key]
""", """
    var key: = "%s:%d:%s" % [feature, idx, "r" if right else "l"]
    if _centers.has(key):
        return _centers[key]
    var __c = """ + PC + """.get_value("fc:" + key)
    if __c is Vector2:
        _centers[key] = __c
        return __c
"""),

    P("game/character/face_parts.gd", "half_center store", """
            c = Vector2(ctr.x / region.get_width(), ctr.y / region.get_height())
    _centers[key] = c
""", """
            c = Vector2(ctr.x / region.get_width(), ctr.y / region.get_height())
    _centers[key] = c
    """ + PC + """.put_value("fc:" + key, c)
"""),

    P("game/character/model_rig.gd", "blush centre cache", """
    var ck: = "%s:%s" % [key, "r" if right else "l"]
    if _blush_center_cache.has(ck):
        return _blush_center_cache[ck]
""", """
    var ck: = "%s:%s" % [key, "r" if right else "l"]
    if _blush_center_cache.has(ck):
        return _blush_center_cache[ck]
    var __c = """ + PC + """.get_value("bc:" + ck)
    if __c is Vector2:
        _blush_center_cache[ck] = __c
        return __c
"""),

    P("game/character/model_rig.gd", "blush centre store", """
            c = Vector2(ctr.x / sub.get_width(), ctr.y / sub.get_height())
    _blush_center_cache[ck] = c
""", """
            c = Vector2(ctr.x / sub.get_width(), ctr.y / sub.get_height())
    _blush_center_cache[ck] = c
    """ + PC + """.put_value("bc:" + ck, c)
"""),

    # kneepads/shoes are cut into left/right halves on every rig build, triangle
    # by triangle; the source meshes are shared and the halves never edited, so
    # one cut per source mesh is enough
    P("game/character/model_rig.gd", "leg split memo", """
func _split_mesh_by_x(mesh: Mesh) -> Dictionary:
""", """
static var __split_memo: = {}

func _split_mesh_by_x(mesh: Mesh) -> Dictionary:
    if mesh != null and __split_memo.has(mesh):
        return __split_memo[mesh]
    var __out: = __split_mesh_by_x_raw(mesh)
    if mesh != null and not __out.is_empty():
        __split_memo[mesh] = __out
    return __out

func __split_mesh_by_x_raw(mesh: Mesh) -> Dictionary:
"""),

    # lighter stages (perf_lite.gd, set in jv_mod_lite.cfg)
    P("game/stage/stage.gd", "lite: stage setting overrides", """
static func val(id: String, key: String, default: Variant) -> Variant:
""", """
static func val(id: String, key: String, default: Variant) -> Variant:
    var __lite: Variant = """ + LITE + """.stage_override(key)
    if __lite != null:
        return __lite
"""),

    P("game/court/gym_crowd.gd", "lite: no stand crowd", """
        shade: Dictionary = {}) -> void :
""", """
        shade: Dictionary = {}) -> void :
    if """ + LITE + """.enabled("crowd"):
        return
"""),

    P("game/main/main.gd", "lite: dress the stage", """
    _setup_sand_deform(id)
    _setup_grass(id)
""", """
    _setup_sand_deform(id)
    _setup_grass(id)
    """ + LITE + """.dress(_stage_shell, id)
"""),

    P("game/main/main.gd", "lite: no nationals live feed", """
    if _stage_shell != null and _stage_shell.has_method("show_live_feed"):
""", """
    if _stage_shell != null and _stage_shell.has_method("show_live_feed")\
    and not """ + LITE + """.enabled("backdrop"):
"""),

    P("game/court/sand_deform.gd", "lite: no footprints", """
func _process(_delta: float) -> void :
""", """
func _process(_delta: float) -> void :
    # the trail texture still gets its first clears, then stops redrawing
    if """ + LITE + """.enabled("trails") and _clear_frames <= 0:
        if _vp != null and _vp.render_target_update_mode != SubViewport.UPDATE_DISABLED:
            _vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
        _pending.clear()
        return
"""),
]

# lighter-stage hooks the demo build may not have yet
for _p in PERF_PATCHES:
    if _p["name"].startswith("lite:"):
        _p["optional"] = True

PERF_FILES = ["game/mods/perf_cache.gd", "game/mods/perf_boot.gd", "game/mods/perf_lite.gd"]
