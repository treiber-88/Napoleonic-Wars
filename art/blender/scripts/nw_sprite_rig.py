
import bpy, math
from mathutils import Vector
PX_PER_M = 6.0
SUPERSAMPLE = 4
def setup_projection(scn, cam, frame_px, target_z=0.0, px_per_m=PX_PER_M, supersample=SUPERSAMPLE):
    """RA projection: camera at 45 deg; the image is rendered sqrt(2) short vertically and the
    sprite converter stretches it back, giving unforeshortened ground and 1:1 heights."""
    tilt = math.radians(45)
    target = Vector((0, 0, target_z))
    cam.location = target + Vector((0, -math.sin(tilt) * 200, math.cos(tilt) * 200))
    cam.rotation_euler = (tilt, 0, 0)
    cam.data.type = 'ORTHO'
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.ortho_scale = frame_px / px_per_m
    cam.data.clip_end = 1000
    r = scn.render
    r.pixel_aspect_x = r.pixel_aspect_y = 1.0
    r.resolution_x = frame_px * supersample
    r.resolution_y = round(frame_px * supersample / math.sqrt(2))
    r.resolution_percentage = 100
