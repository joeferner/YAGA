import math
from typing import cast
import adsk.core
import adsk.fusion

from ...lib import fusion360utils as futil

tangent_line_count = 10
tangent_line_interval_deg = 5


class SpurGear:
    __root_diameter: float
    __root_diameter_expr: str
    __base_diameter: float
    __base_diameter_expr: str
    __pitch_diameter: float
    __pitch_diameter_expr: str
    __outside_diameter: float
    __outside_diameter_expr: str
    __involute_curve_mirror_offset_angle_expr: str

    def __init__(
            self,
            app: adsk.core.Application,
            pressure_angle_value: adsk.core.ValueCommandInput,
            number_of_teeth_value: adsk.core.ValueCommandInput,
            module_value: adsk.core.ValueCommandInput,
            gear_height_value: adsk.core.ValueCommandInput
    ):
        units_mgr = app.activeProduct.unitsManager
        pressure_angle = units_mgr.evaluateExpression(pressure_angle_value.expression, "deg")
        number_of_teeth = units_mgr.evaluateExpression(number_of_teeth_value.expression, "")
        module = units_mgr.evaluateExpression(module_value.expression, "cm")
        gear_height = units_mgr.evaluateExpression(gear_height_value.expression, "cm")

        # https://khkgears.net/new/gear_knowledge/abcs_of_gears-b/basic_gear_terminology_calculation.html
        # https://johnfsworkshop.org/home/processes-links/processes-removing-metal/the-milling-machine/the-milling-machine-workholding/worm-driven-rotary-devices/the-dividing-head/helical-milling-links/helical-milling-13-9-10/formulae-for-gears/
        self.__pitch_diameter = number_of_teeth * module  # PCD - D
        addendum = module  # addendum - a
        self.__base_diameter = self.__pitch_diameter * math.cos(pressure_angle)  # BC
        dedendum = self.__pitch_diameter - self.__base_diameter  # dedendum - b
        self.__root_diameter = self.__pitch_diameter - (2 * dedendum)  # ? - Dr
        self.__outside_diameter = (number_of_teeth + 2) * module  # OD - Do = ( N + 2 ) / P
        circular_pitch = module * math.pi  # CP

        diametral_pitch_expr = f"( 1 / ({module_value.expression}) )"
        self.__pitch_diameter_expr = f"( ({number_of_teeth_value.expression}) * ({module_value.expression}) )"
        self.__base_diameter_expr = f"( {self.__pitch_diameter_expr} * cos({pressure_angle_value.expression}) )"
        base_radius_expr = f"( {self.__base_diameter_expr} / 2 )"
        self.__root_diameter_expr = f"( (({number_of_teeth_value.expression}) * ({module_value.expression})) - (2 * (1.25 / (1 / ({module_value.expression})))) )"
        self.__outside_diameter_expr = f"( (({number_of_teeth_value.expression}) + 2) / (1 / ({module_value.expression})) )"
        base_circumference_expr = f"( PI * {self.__base_diameter_expr} )"
        tooth_thickness_expr = f"( {base_circumference_expr} / (({number_of_teeth_value.expression}) * 2) )"
        # https://khkgears.net/new/gear_knowledge/gear_technical_reference/tooth-thickness.html
        # f"( (PI / 2) + () ) * ({module_value.expression})"
        self.__involute_curve_mirror_offset_angle_expr = f"( (PI / 2) / ({diametral_pitch_expr}*1 mm) ) / ({base_circumference_expr}/1 mm) * 360 deg / 2"

    def create_component(self):
        comp = futil.create_new_component()
        sketch = self.__create_sketch(comp)
        sketch.isComputeDeferred = True
        center_point = sketch.originPoint
        root_circle = self.__create_root_circle(sketch, center_point)
        base_circle = self.__create_base_circle(sketch, center_point)
        pitch_circle = self.__create_pitch_circle(sketch, center_point)
        outside_circle = self.__create_outside_circle(sketch, center_point)
        involute_curve_mirror_line = self.__create_involute_curve_mirror_line(sketch, center_point, outside_circle)
        radius_line = self.__create_involute_curve_radius_construction_lines(sketch, center_point, base_circle)
        spline = self.__create_involute_curve(sketch, base_circle, radius_line, involute_curve_mirror_line)
        mirror_spline = self.__create_involute_curve_mirror(
            sketch,
            center_point,
            base_circle,
            involute_curve_mirror_line,
            spline
        )
        tooth_top_land = self.__create_tooth_top_land(sketch, center_point, spline, mirror_spline)
        sketch.isComputeDeferred = False
        return comp

    @staticmethod
    def __create_sketch(comp: adsk.fusion.Component) -> adsk.fusion.Sketch:
        sketch_plane = comp.xYConstructionPlane
        sketch = comp.sketches.add(sketch_plane)
        sketch.name = "SpurGear1"
        return sketch

    def __create_root_circle(
            self,
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint
    ) -> adsk.fusion.SketchCircle:
        root_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), self.__root_diameter / 2.0
        )
        sketch.geometricConstraints.addCoincident(root_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            root_circle,
            adsk.core.Point3D.create(-self.__root_diameter / 1.5, self.__root_diameter / 1.5, 0),
        )
        d.parameter.expression = self.__root_diameter_expr
        return root_circle

    def __create_base_circle(
            self,
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint
    ) -> adsk.fusion.SketchCircle:
        base_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), self.__base_diameter / 2.0
        )
        base_circle.isConstruction = True
        sketch.geometricConstraints.addCoincident(base_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            base_circle,
            adsk.core.Point3D.create(-self.__root_diameter / 1.5, self.__root_diameter / 1.4, 0),
        )
        d.parameter.expression = self.__base_diameter_expr
        return base_circle

    def __create_pitch_circle(
            self,
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint
    ) -> adsk.fusion.SketchCircle:
        pitch_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), self.__pitch_diameter / 2.0
        )
        pitch_circle.isConstruction = True
        sketch.geometricConstraints.addCoincident(pitch_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            pitch_circle,
            adsk.core.Point3D.create(-self.__root_diameter / 1.5, self.__root_diameter / 1.2, 0),
        )
        d.parameter.expression = self.__pitch_diameter_expr
        return pitch_circle

    def __create_outside_circle(
            self,
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint
    ) -> adsk.fusion.SketchCircle:
        outside_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), self.__outside_diameter / 2.0
        )
        outside_circle.isConstruction = True
        sketch.geometricConstraints.addCoincident(outside_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            outside_circle,
            adsk.core.Point3D.create(-self.__root_diameter / 1.5, self.__root_diameter / 1.3, 0),
        )
        d.parameter.expression = self.__outside_diameter_expr
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

    def __create_involute_curve_radius_construction_lines(
            self,
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            base_circle: adsk.fusion.SketchCircle
    ) -> list[adsk.fusion.SketchLine]:
        radius_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(self.__base_diameter / 2.0, 0, 0),
        )
        radius_line.isConstruction = True
        sketch.geometricConstraints.addCoincident(radius_line.startSketchPoint, center_point)
        sketch.geometricConstraints.addCoincident(radius_line.endSketchPoint, base_circle)

        # TODO manually draw these to avoid under constrained issue
        circular_pattern_input = sketch.geometricConstraints.createCircularPatternInput(
            [radius_line], radius_line.startSketchPoint
        )
        circular_pattern_input.quantity = adsk.core.ValueInput.createByString(f"{tangent_line_count}")
        circular_pattern_input.totalAngle = adsk.core.ValueInput.createByString(
            f"-{(tangent_line_count - 1) * tangent_line_interval_deg} deg"
        )
        circular_pattern = sketch.geometricConstraints.addCircularPattern(circular_pattern_input)

        radius_lines: list[adsk.fusion.SketchLine] = [radius_line]
        for entity in circular_pattern.createdEntities:
            line: adsk.fusion.SketchLine = cast(adsk.fusion.SketchLine, entity)
            radius_lines.append(line)

        return radius_lines

    def __create_involute_curve(
            self,
            sketch: adsk.fusion.Sketch,
            base_circle: adsk.fusion.SketchCircle,
            radius_lines: list[adsk.fusion.SketchLine],
            involute_curve_mirror_line: adsk.fusion.SketchLine
    ) -> adsk.fusion.SketchFittedSpline:
        spline_points = adsk.core.ObjectCollection.create()
        for i in range(len(radius_lines) - 1):
            radius_line: adsk.fusion.SketchLine = radius_lines[i]

            tangent_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
                radius_line.endSketchPoint,
                adsk.core.Point3D.create(self.__base_diameter, -self.__base_diameter, 0),
            )
            tangent_line.isConstruction = True
            sketch.geometricConstraints.addTangent(base_circle, tangent_line)
            spline_points.add(tangent_line.endSketchPoint)

            d = sketch.sketchDimensions.addDistanceDimension(
                tangent_line.startSketchPoint,
                tangent_line.endSketchPoint,
                adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                adsk.core.Point3D.create(self.__base_diameter, -self.__base_diameter, 0),
            )
            d.parameter.expression = (
                f"{len(radius_lines) - i - 1} * PI * {self.__base_diameter_expr} * ({tangent_line_interval_deg} deg / 360 deg)"
            )
        spline_points.add(radius_lines[len(radius_lines) - 1].endSketchPoint)

        # create dimension to place spline in correct location
        d = sketch.sketchDimensions.addAngularDimension(
            involute_curve_mirror_line,
            radius_lines[len(radius_lines) - 1],
            adsk.core.Point3D.create(self.__outside_diameter, -1, 0),
        )
        d.parameter.expression = self.__involute_curve_mirror_offset_angle_expr

        # create involute spline
        spline = sketch.sketchCurves.sketchFittedSplines.add(spline_points)
        return spline

    def __create_involute_curve_mirror(
            self,
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            base_circle: adsk.fusion.SketchCircle,
            involute_curve_mirror_line: adsk.fusion.SketchLine,
            spline: adsk.fusion.SketchFittedSpline
    ) -> adsk.fusion.SketchFittedSpline:
        spline_mirror_radius_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(self.__base_diameter / 2.0, 1, 0),
        )
        spline_mirror_radius_line.isConstruction = True
        sketch.geometricConstraints.addCoincident(spline_mirror_radius_line.startSketchPoint, center_point)
        sketch.geometricConstraints.addCoincident(spline_mirror_radius_line.endSketchPoint, base_circle)
        d = sketch.sketchDimensions.addAngularDimension(
            involute_curve_mirror_line,
            spline_mirror_radius_line,
            adsk.core.Point3D.create(self.__outside_diameter, 1, 0),
        )
        d.parameter.expression = self.__involute_curve_mirror_offset_angle_expr

        # create involute spline mirror
        mirror_spline, _ = futil.mirror_sketch_spline(sketch, spline, involute_curve_mirror_line)
        return mirror_spline

    def __create_tooth_top_land(
            self,
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            spline: adsk.fusion.SketchFittedSpline,
            mirror_spline: adsk.fusion.SketchFittedSpline
    ):
        tooth_top_land = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
            center_point, adsk.core.Point3D.create(self.__outside_diameter, -1, 0), 0.1
        )
        sketch.geometricConstraints.addCoincident(tooth_top_land.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            tooth_top_land,
            adsk.core.Point3D.create(self.__outside_diameter, 0, 0),
        )
        d.parameter.expression = self.__outside_diameter_expr
        sketch.geometricConstraints.addCoincident(tooth_top_land.startSketchPoint, spline)
        sketch.geometricConstraints.addCoincident(tooth_top_land.endSketchPoint, mirror_spline)
        return tooth_top_land
