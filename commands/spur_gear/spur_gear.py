import math
from typing import cast
import adsk.core
import adsk.fusion

from ...lib import fusion360utils as futil

tangent_line_count = 10
tangent_line_interval_deg = 5


# https://khkgears.net/new/gear_knowledge/abcs_of_gears-b/basic_gear_terminology_calculation.html
# https://johnfsworkshop.org/home/processes-links/processes-removing-metal/the-milling-machine/the-milling-machine-workholding/worm-driven-rotary-devices/the-dividing-head/helical-milling-links/helical-milling-13-9-10/formulae-for-gears/
class SpurGear:
    @staticmethod
    def create_component(
            app: adsk.core.Application,
            pressure_angle_value: adsk.core.ValueCommandInput,
            number_of_teeth_value: adsk.core.ValueCommandInput,
            module_value: adsk.core.ValueCommandInput,
            gear_height_value: adsk.core.ValueCommandInput,
            name_prefix: str | None = None
    ):
        units_mgr = app.activeProduct.unitsManager

        pressure_angle = units_mgr.evaluateExpression(pressure_angle_value.expression, "deg")
        pressure_angle_expr = f"({pressure_angle_value.expression})"

        number_of_teeth = units_mgr.evaluateExpression(number_of_teeth_value.expression, "")
        number_of_teeth_expr = f"({number_of_teeth_value.expression})"

        module = units_mgr.evaluateExpression(module_value.expression, "cm")
        module_expr = f"({module_value.expression})"

        gear_height = units_mgr.evaluateExpression(gear_height_value.expression, "cm")

        # reference/pitch diameter (d)
        pitch_diameter = number_of_teeth * module
        pitch_diameter_expr = f"( {number_of_teeth_expr} * {module_expr} )"

        # dedendum (hf)
        dedendum = 1.25 * module
        dedendum_expr = f'( 1.25 * {module_expr} )'

        # root diameter (df)
        root_diameter = pitch_diameter - (2 * dedendum)
        root_diameter_expr = f'( {pitch_diameter_expr} - (2 * {dedendum_expr}) )'

        # base diameter (db)
        base_diameter = pitch_diameter * math.cos(pressure_angle)
        base_diameter_expr = f"( {pitch_diameter_expr} * cos({pressure_angle_expr}) )"

        # tip/outside diameter (da)
        outside_diameter = (pitch_diameter + 2) * module
        outside_diameter_expr = f"( {pitch_diameter_expr} + (2 * {module_expr}) )"

        # pitch (p) - Pitch is the distance between corresponding points on adjacent teeth
        pitch = math.pi * module
        pitch_expr = f"( PI * {module_expr} )"

        # tooth thickness (s)
        tooth_thickness = pitch / 2
        tooth_thickness_expr = f"( {pitch_expr} / 2 )"
        half_tooth_thickness_expr = f"( {tooth_thickness_expr} / 2 )"

        involute_curve_mirror_offset_angle_expr = f"( ({half_tooth_thickness_expr} / (PI * {root_diameter_expr})) * 360 deg )"

        comp = futil.create_new_component()
        sketch = SpurGear.__create_sketch(comp)
        sketch.isComputeDeferred = True
        center_point = sketch.originPoint
        root_circle = SpurGear.__create_root_circle(sketch, center_point, root_diameter, root_diameter_expr, name_prefix)
        base_circle = SpurGear.__create_base_circle(
            sketch,
            center_point,
            base_diameter,
            base_diameter_expr,
            root_diameter,
            name_prefix
        )
        pitch_circle = SpurGear.__create_pitch_circle(
            sketch,
            center_point,
            pitch_diameter,
            pitch_diameter_expr,
            root_diameter,
            name_prefix
        )
        outside_circle = SpurGear.__create_outside_circle(
            sketch,
            center_point,
            outside_diameter,
            outside_diameter_expr,
            root_diameter,
            name_prefix
        )
        involute_curve_mirror_line = SpurGear.__create_involute_curve_mirror_line(sketch, center_point, outside_circle)
        spline = SpurGear.__create_involute_curve(
            sketch,
            base_circle,
            involute_curve_mirror_line,
            center_point,
            base_diameter,
            base_diameter_expr,
            outside_diameter,
            involute_curve_mirror_offset_angle_expr,
            True
        )
        mirror_spline = SpurGear.__create_involute_curve(
            sketch,
            base_circle,
            involute_curve_mirror_line,
            center_point,
            base_diameter,
            base_diameter_expr,
            outside_diameter,
            involute_curve_mirror_offset_angle_expr,
            False
        )
        tooth_top_land = SpurGear.__create_tooth_top_land(
            sketch,
            center_point,
            spline,
            mirror_spline,
            outside_diameter,
            outside_diameter_expr,
        )
        sketch.isComputeDeferred = False
        return comp

    @staticmethod
    def __create_sketch(comp: adsk.fusion.Component) -> adsk.fusion.Sketch:
        sketch_plane = comp.xYConstructionPlane
        sketch = comp.sketches.add(sketch_plane)
        sketch.name = "SpurGear1"
        return sketch

    @staticmethod
    def __create_root_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            root_diameter: float,
            root_diameter_expr: str,
            name_prefix: str | None
    ) -> adsk.fusion.SketchCircle:
        root_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), root_diameter / 2.0
        )
        sketch.geometricConstraints.addCoincident(root_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            root_circle,
            adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.5, 0),
        )
        d.parameter.expression = root_diameter_expr
        if name_prefix:
            d.parameter.name = f"{name_prefix}_root_diameter"
        return root_circle

    @staticmethod
    def __create_base_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            base_diameter: float,
            base_diameter_expr: str,
            root_diameter: float,
            name_prefix: str | None
    ) -> adsk.fusion.SketchCircle:
        base_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), base_diameter / 2.0
        )
        base_circle.isConstruction = True
        sketch.geometricConstraints.addCoincident(base_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            base_circle,
            adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.4, 0),
        )
        d.parameter.expression = base_diameter_expr
        if name_prefix:
            d.parameter.name = f"{name_prefix}_base_diameter"
        return base_circle

    @staticmethod
    def __create_pitch_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            pitch_diameter: float,
            pitch_diameter_expr: str,
            root_diameter: float,
            name_prefix: str | None
    ) -> adsk.fusion.SketchCircle:
        pitch_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), pitch_diameter / 2.0
        )
        pitch_circle.isConstruction = True
        sketch.geometricConstraints.addCoincident(pitch_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            pitch_circle,
            adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.2, 0),
        )
        d.parameter.expression = pitch_diameter_expr
        if name_prefix:
            d.parameter.name = f"{name_prefix}_pitch_diameter"
        return pitch_circle

    @staticmethod
    def __create_outside_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            outside_diameter: float,
            outside_diameter_expr: str,
            root_diameter: float,
            name_prefix: str | None
    ) -> adsk.fusion.SketchCircle:
        outside_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), outside_diameter / 2.0
        )
        outside_circle.isConstruction = True
        sketch.geometricConstraints.addCoincident(outside_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            outside_circle,
            adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.3, 0),
        )
        d.parameter.expression = outside_diameter_expr
        if name_prefix:
            d.parameter.name = f"{name_prefix}_outside_diameter"
        return outside_circle

    @staticmethod
    def __create_involute_curve_mirror_line(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            outside_circle: adsk.fusion.SketchCircle
    ) -> adsk.fusion.SketchLine:
        involute_curve_mirror_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            center_point, adsk.core.Point3D.create(1, 0, 0)
        )
        involute_curve_mirror_line.isConstruction = True
        sketch.geometricConstraints.addCoincident(involute_curve_mirror_line.endSketchPoint, outside_circle)
        sketch.geometricConstraints.addHorizontal(involute_curve_mirror_line)
        return involute_curve_mirror_line

    @staticmethod
    def __create_involute_curve_radius_construction_lines(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            base_circle: adsk.fusion.SketchCircle,
            base_diameter: float,
            clockwise: bool
    ) -> list[adsk.fusion.SketchLine]:
        radius_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(base_diameter / 2.0, 0, 0),
        )
        radius_line.isConstruction = True
        sketch.geometricConstraints.addCoincident(radius_line.startSketchPoint, center_point)
        sketch.geometricConstraints.addCoincident(radius_line.endSketchPoint, base_circle)

        # TODO manually draw these to avoid under constrained issue
        circular_pattern_input = sketch.geometricConstraints.createCircularPatternInput(
            [radius_line], radius_line.startSketchPoint
        )
        if clockwise:
            sign_expr = '-'
        else:
            sign_expr = ''
        circular_pattern_input.quantity = adsk.core.ValueInput.createByString(f"{tangent_line_count}")
        circular_pattern_input.totalAngle = adsk.core.ValueInput.createByString(
            f"{sign_expr}{(tangent_line_count - 1) * tangent_line_interval_deg} deg"
        )
        circular_pattern = sketch.geometricConstraints.addCircularPattern(circular_pattern_input)

        radius_lines: list[adsk.fusion.SketchLine] = [radius_line]
        for entity in circular_pattern.createdEntities:
            line: adsk.fusion.SketchLine = cast(adsk.fusion.SketchLine, entity)
            radius_lines.append(line)

        return radius_lines

    @staticmethod
    def __create_involute_curve(
            sketch: adsk.fusion.Sketch,
            base_circle: adsk.fusion.SketchCircle,
            involute_curve_mirror_line: adsk.fusion.SketchLine,
            center_point: adsk.fusion.SketchPoint,
            base_diameter: float,
            base_diameter_expr: str,
            outside_diameter: float,
            involute_curve_mirror_offset_angle_expr: str,
            clockwise: bool
    ) -> adsk.fusion.SketchFittedSpline:
        spline_points = adsk.core.ObjectCollection.create()

        radius_lines = SpurGear.__create_involute_curve_radius_construction_lines(
            sketch,
            center_point,
            base_circle,
            base_diameter,
            clockwise
        )

        if clockwise:
            sign = -1
        else:
            sign = 1

        for i in range(len(radius_lines) - 1):
            radius_line: adsk.fusion.SketchLine = radius_lines[i]

            tangent_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
                radius_line.endSketchPoint,
                adsk.core.Point3D.create(base_diameter, sign * base_diameter, 0),
            )
            tangent_line.isConstruction = True
            sketch.geometricConstraints.addTangent(base_circle, tangent_line)
            spline_points.add(tangent_line.endSketchPoint)

            d = sketch.sketchDimensions.addDistanceDimension(
                tangent_line.startSketchPoint,
                tangent_line.endSketchPoint,
                adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                adsk.core.Point3D.create(base_diameter, sign * base_diameter, 0),
            )
            d.parameter.expression = (
                f"{len(radius_lines) - i - 1} * PI * {base_diameter_expr} * ({tangent_line_interval_deg} deg / 360 deg)"
            )
        spline_points.add(radius_lines[len(radius_lines) - 1].endSketchPoint)

        # create dimension to place spline in correct location
        d = sketch.sketchDimensions.addAngularDimension(
            involute_curve_mirror_line,
            radius_lines[len(radius_lines) - 1],
            adsk.core.Point3D.create(outside_diameter, sign, 0),
        )
        d.parameter.expression = involute_curve_mirror_offset_angle_expr

        # create involute spline
        spline = sketch.sketchCurves.sketchFittedSplines.add(spline_points)
        return spline

    @staticmethod
    def __create_tooth_top_land(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            spline: adsk.fusion.SketchFittedSpline,
            mirror_spline: adsk.fusion.SketchFittedSpline,
            outside_diameter: float,
            outside_diameter_expr: str
    ):
        tooth_top_land = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
            center_point, adsk.core.Point3D.create(outside_diameter, -1, 0), 0.1
        )
        sketch.geometricConstraints.addCoincident(tooth_top_land.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            tooth_top_land,
            adsk.core.Point3D.create(outside_diameter, 0, 0),
        )
        d.parameter.expression = outside_diameter_expr
        sketch.geometricConstraints.addCoincident(tooth_top_land.startSketchPoint, spline)
        sketch.geometricConstraints.addCoincident(tooth_top_land.endSketchPoint, mirror_spline)
        return tooth_top_land
