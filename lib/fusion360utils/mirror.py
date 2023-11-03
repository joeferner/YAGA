import adsk
import math


def mirror_sketch_spline(
    sketch: adsk.fusion.Sketch, spline: adsk.fusion.SketchFittedSpline, mirror_line: adsk.fusion.SketchLine
) -> tuple[adsk.fusion.SketchFittedSpline, adsk.fusion.SymmetryConstraint]:
    # see https://stackoverflow.com/a/8954454/39431
    x1 = mirror_line.startSketchPoint.geometry.x
    x2 = mirror_line.endSketchPoint.geometry.x
    y1 = mirror_line.startSketchPoint.geometry.y
    y2 = mirror_line.endSketchPoint.geometry.y
    z = mirror_line.startSketchPoint.geometry.z

    a = y2 - y1
    b = -(x2 - x1)
    c = (-a * x1) - (b * y1)
    m = math.sqrt((a * a) + (b * b))
    a_p = a / m
    b_p = b / m
    c_p = c / m

    mirror_spline_points = adsk.core.ObjectCollection.create()
    for pt in spline.fitPoints:
        px = pt.geometry.x
        py = pt.geometry.y
        d = (a_p * px) + (b_p * py) + c_p
        px_p = px - (2 * a_p * d)
        py_p = py - (2 * b_p * d)
        mirror_spline_points.add(adsk.core.Point3D.create(px_p, py_p, z))
    mirror_spline = sketch.sketchCurves.sketchFittedSplines.add(mirror_spline_points)

    symmetry = sketch.geometricConstraints.addSymmetry(spline, mirror_spline, mirror_line)
    return mirror_spline, symmetry
