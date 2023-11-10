import math
import adsk.core
import adsk.fusion
from typing import cast

from ...lib import fusion360utils as futil


# https://khkgears.net/new/gear_knowledge/abcs_of_gears-b/basic_gear_terminology_calculation.html
class SpurGear:
    @staticmethod
    def create_component(
            app: adsk.core.Application,
            pressure_angle_value: adsk.core.ValueCommandInput,
            number_of_teeth_value: adsk.core.ValueCommandInput,
            module_value: adsk.core.ValueCommandInput,
            root_fillet_radius_value: adsk.core.ValueCommandInput,
            gear_height_value: adsk.core.DistanceValueCommandInput,
            rotation_value: adsk.core.ValueCommandInput,
            backlash_value: adsk.core.ValueCommandInput,
            preview: bool,
            name: str | None,
    ):
        design = adsk.fusion.Design.cast(app.activeProduct)
        units_mgr = app.activeProduct.unitsManager

        pressure_angle = units_mgr.evaluateExpression(pressure_angle_value.expression, "deg")
        pressure_angle_expr = f"({pressure_angle_value.expression})"

        number_of_teeth = units_mgr.evaluateExpression(number_of_teeth_value.expression, "")
        number_of_teeth_expr = f"({number_of_teeth_value.expression})"

        module = units_mgr.evaluateExpression(module_value.expression, "cm")
        module_expr = f"({module_value.expression})"

        root_fillet_radius_expr = f"({root_fillet_radius_value.expression})"

        gear_height_expr = f"({gear_height_value.expression})"

        rotation_expr = f"({rotation_value.expression})"

        backlash_expr = f"({backlash_value.expression})"

        # dedendum (hf)
        dedendum = 1.25 * module
        dedendum_expr = f"( 1.25 * {module_expr} )"

        # pitch (p) - Pitch is the distance between corresponding points on adjacent teeth
        pitch = math.pi * module
        pitch_expr = f"( PI * {module_expr} )"

        # tooth thickness (s)
        tooth_thickness = pitch / 2
        tooth_thickness_expr = f"( {pitch_expr} / 2 )"
        half_tooth_thickness_expr = f"( {tooth_thickness_expr} / 2 )"

        # create component
        comp_occurrence = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = comp_occurrence.component
        if name:
            comp.name = name

        sketch_plane = comp.xYConstructionPlane
        sketch_circles = comp.sketches.add(sketch_plane)
        if name:
            sketch_circles.name = f"{name}_circles"
        sketch_circles.isComputeDeferred = True
        center_point = sketch_circles.originPoint

        # reference/pitch circle (d)
        pitch_diameter = number_of_teeth * module
        pitch_diameter_expr = f"( {number_of_teeth_expr} * {module_expr} )"
        _, pitch_diameter_expr = SpurGear.__create_pitch_circle(
            sketch_circles,
            center_point,
            pitch_diameter,
            pitch_diameter_expr,
            name
        )
        backlash_angle_expr = f"(({backlash_expr} / 4 / (PI * {pitch_diameter_expr})) * 360 deg)"

        # root circle (df)
        root_diameter = pitch_diameter - (2 * dedendum)
        root_diameter_expr = f"( {pitch_diameter_expr} - (2 * {dedendum_expr}) )"
        root_circle, root_diameter_expr = SpurGear.__create_root_circle(
            sketch_circles, center_point, root_diameter, root_diameter_expr, name
        )
        root_circle_profiles = futil.find_profiles([root_circle])
        root_circle_extrude = comp.features.extrudeFeatures.addSimple(
            root_circle_profiles[0],
            adsk.core.ValueInput.createByString(gear_height_expr),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        if name:
            root_circle_extrude.name = f"{name}_circle"
            root_circle_extrude.bodies.item(0).name = f"{name}_circle"

        # base circle (db)
        base_diameter = pitch_diameter * math.cos(pressure_angle)
        base_diameter_expr = f"( {pitch_diameter_expr} * cos({pressure_angle_expr}) )"
        base_circle, base_diameter_expr = SpurGear.__create_base_circle(
            sketch_circles,
            center_point,
            base_diameter,
            base_diameter_expr,
            root_diameter,
            name
        )

        # tip/outside circle (da)
        outside_diameter = (pitch_diameter + 2) * module
        outside_diameter_expr = f"( {pitch_diameter_expr} + (2 * {module_expr}) )"
        outside_circle, outside_diameter_expr = SpurGear.__create_outside_circle(
            sketch_circles,
            center_point,
            outside_diameter,
            outside_diameter_expr,
            root_diameter,
            name
        )

        sketch_circles.isComputeDeferred = False

        if preview:
            sketch_circles.isVisible = True
        else:
            sketch_circles.isVisible = False

            center_axis_input = comp.constructionAxes.createInput()
            center_axis_input.setByCircularFace(root_circle_extrude.faces[0])
            center_axis = comp.constructionAxes.add(center_axis_input)
            if name:
                center_axis.name = f"{name}_centerAxis"

            # resizing a gear confuses Fusion 360, so we need to put the tooth top land on a separate sketch to force
            # the computations in the correct order
            sketch_tooth_profile = comp.sketches.add(sketch_plane)
            if name:
                sketch_tooth_profile.name = f"{name}_toothProfile"

            center_point = sketch_tooth_profile.originPoint
            base_circle = cast(adsk.fusion.SketchCircle, sketch_tooth_profile.project(base_circle).item(0))
            root_circle = cast(adsk.fusion.SketchCircle, sketch_tooth_profile.project(root_circle).item(0))
            outside_circle = cast(adsk.fusion.SketchCircle, sketch_tooth_profile.project(outside_circle).item(0))

            sketch_tooth_profile.isComputeDeferred = True

            # tooth
            involute_curve_mirror_line = SpurGear.__create_involute_curve_mirror_line(
                sketch_tooth_profile, center_point, outside_circle
            )

            involute_curve_mirror_offset_angle_expr = (
                f"( ({half_tooth_thickness_expr} / (PI * {root_diameter_expr})) * 360 deg - {backlash_angle_expr})"
            )

            tangent_line_count = 10
            tangent_line_interval_deg = 5

            spline = SpurGear.__create_involute_curve(
                sketch_tooth_profile,
                base_circle,
                involute_curve_mirror_line,
                center_point,
                base_diameter,
                base_diameter_expr,
                involute_curve_mirror_offset_angle_expr,
                tangent_line_count,
                tangent_line_interval_deg,
                True,
            )
            mirror_spline = SpurGear.__create_involute_curve(
                sketch_tooth_profile,
                base_circle,
                involute_curve_mirror_line,
                center_point,
                base_diameter,
                base_diameter_expr,
                involute_curve_mirror_offset_angle_expr,
                tangent_line_count,
                tangent_line_interval_deg,
                False,
            )

            # create lines from involute curve to root circle
            dedendum_line_a = SpurGear.__create_dedendum_line(sketch_tooth_profile, center_point, spline)
            dedendum_line_b = SpurGear.__create_dedendum_line(sketch_tooth_profile, center_point, mirror_spline)

            # draw root fillet radius
            root_fillet_radius_a, root_fillet_radius_expr = SpurGear.__create_root_fillet_radius(
                sketch_tooth_profile, dedendum_line_a, root_circle, root_fillet_radius_expr, tooth_thickness, name
            )
            root_fillet_radius_b, _ = SpurGear.__create_root_fillet_radius(
                sketch_tooth_profile, dedendum_line_b, root_circle, root_fillet_radius_expr, tooth_thickness, name
            )

            sketch_tooth_profile.isComputeDeferred = False
            sketch_tooth_profile.isVisible = False

            sketch_tooth = comp.sketches.add(sketch_plane)
            if name:
                sketch_tooth.name = f"{name}_tooth"

            center_point = sketch_tooth.originPoint
            spline = cast(adsk.fusion.SketchFittedSpline, sketch_tooth.project(spline).item(0))
            mirror_spline = cast(adsk.fusion.SketchFittedSpline, sketch_tooth.project(mirror_spline).item(0))
            root_circle = cast(adsk.fusion.SketchCircle, sketch_tooth.project(root_circle).item(0))
            base_circle = cast(adsk.fusion.SketchCircle, sketch_tooth.project(base_circle).item(0))
            dedendum_line_a = cast(adsk.fusion.SketchLine, sketch_tooth.project(dedendum_line_a).item(0))
            dedendum_line_b = cast(adsk.fusion.SketchLine, sketch_tooth.project(dedendum_line_b).item(0))
            root_fillet_radius_a = cast(adsk.fusion.SketchArc, sketch_tooth.project(root_fillet_radius_a).item(0))
            root_fillet_radius_b = cast(adsk.fusion.SketchArc, sketch_tooth.project(root_fillet_radius_b).item(0))

            SpurGear.__create_tooth_top_land(
                sketch_tooth,
                center_point,
                spline,
                mirror_spline,
                outside_diameter,
                outside_diameter_expr,
            )

            # extrude tooth
            tooth_feature = SpurGear.__extrude_tooth(
                comp,
                gear_height_expr,
                spline,
                mirror_spline,
                root_circle,
                base_circle,
                dedendum_line_a,
                dedendum_line_b,
                root_fillet_radius_a,
                root_fillet_radius_b,
                name,
            )

            SpurGear.__create_tooth_rotation(
                comp,
                tooth_feature,
                center_axis,
                rotation_expr,
                name
            )

            # rotate tooth
            tooth_pattern = SpurGear.__create_tooth_circular_pattern(
                comp, tooth_feature, root_circle, number_of_teeth_expr, name
            )

            # group features into one
            group = design.timeline.timelineGroups.add(
                comp_occurrence.timelineObject.index, tooth_pattern.timelineObject.index
            )
            if name:
                group.name = name

        return

    @staticmethod
    def __create_root_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            root_diameter: float,
            root_diameter_expr: str,
            name: str | None,
    ) -> [adsk.fusion.SketchCircle, str]:
        root_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), root_diameter / 2.0
        )
        sketch.geometricConstraints.addCoincident(root_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            root_circle,
            adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.5, 0),
        )
        d.parameter.expression = root_diameter_expr
        if name:
            d.parameter.name = f"{name}_rootDiameter"
        return root_circle, d.parameter.name

    @staticmethod
    def __create_base_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            base_diameter: float,
            base_diameter_expr: str,
            root_diameter: float,
            name: str | None,
    ) -> [adsk.fusion.SketchCircle, str]:
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
        if name:
            d.parameter.name = f"{name}_baseDiameter"
        return base_circle, d.parameter.name

    @staticmethod
    def __create_pitch_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            pitch_diameter: float,
            pitch_diameter_expr: str,
            name: str | None,
    ) -> [adsk.fusion.SketchCircle, str]:
        pitch_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), pitch_diameter / 2.0
        )
        pitch_circle.isConstruction = True
        sketch.geometricConstraints.addCoincident(pitch_circle.centerSketchPoint, center_point)
        d = sketch.sketchDimensions.addDiameterDimension(
            pitch_circle,
            adsk.core.Point3D.create(-pitch_diameter / 1.5, pitch_diameter / 1.2, 0),
        )
        d.parameter.expression = pitch_diameter_expr
        if name:
            d.parameter.name = f"{name}_pitchDiameter"
        return pitch_circle, d.parameter.name

    @staticmethod
    def __create_outside_circle(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            outside_diameter: float,
            outside_diameter_expr: str,
            root_diameter: float,
            name: str | None,
    ) -> [adsk.fusion.SketchCircle, str]:
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
        if name:
            d.parameter.name = f"{name}_outsideDiameter"
        return outside_circle, d.parameter.name

    @staticmethod
    def __create_involute_curve_mirror_line(
            sketch: adsk.fusion.Sketch, center_point: adsk.fusion.SketchPoint, outside_circle: adsk.fusion.SketchCircle
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
            involute_curve_mirror_line: adsk.fusion.SketchLine,
            involute_curve_mirror_offset_angle_expr: str,
            tangent_line_count: int,
            tangent_line_interval_deg: float,
            clockwise: bool,
    ) -> list[adsk.fusion.SketchLine]:
        if clockwise:
            sign = 1
        else:
            sign = -1

        radius_lines: list[adsk.fusion.SketchLine] = []
        for i in range(tangent_line_count):
            if i == 0:
                y = -sign
            else:
                y = sign * (i + 1)
            radius_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
                adsk.core.Point3D.create(0, 0, 0),
                adsk.core.Point3D.create(base_diameter / 2.0, y, 0),
            )
            radius_line.isConstruction = True
            sketch.geometricConstraints.addCoincident(radius_line.startSketchPoint, center_point)
            sketch.geometricConstraints.addCoincident(radius_line.endSketchPoint, base_circle)

            if i == 0:
                d = sketch.sketchDimensions.addAngularDimension(
                    involute_curve_mirror_line, radius_line, adsk.core.Point3D.create(base_diameter, -sign, 0)
                )
                d.parameter.expression = involute_curve_mirror_offset_angle_expr
            else:
                d = sketch.sketchDimensions.addAngularDimension(
                    radius_lines[0], radius_line, adsk.core.Point3D.create(base_diameter, sign, 0)
                )
                d.parameter.expression = f"{i + 1} * {tangent_line_interval_deg} deg"

            radius_lines.append(radius_line)

        return radius_lines

    @staticmethod
    def __create_involute_curve(
            sketch: adsk.fusion.Sketch,
            base_circle: adsk.fusion.SketchCircle,
            involute_curve_mirror_line: adsk.fusion.SketchLine,
            center_point: adsk.fusion.SketchPoint,
            base_diameter: float,
            base_diameter_expr: str,
            involute_curve_mirror_offset_angle_expr: str,
            tangent_line_count: int,
            tangent_line_interval_deg: float,
            clockwise: bool,
    ) -> adsk.fusion.SketchFittedSpline:
        spline_points = adsk.core.ObjectCollection.create()

        radius_lines = SpurGear.__create_involute_curve_radius_construction_lines(
            sketch,
            center_point,
            base_circle,
            base_diameter,
            involute_curve_mirror_line,
            involute_curve_mirror_offset_angle_expr,
            tangent_line_count,
            tangent_line_interval_deg,
            clockwise,
        )

        if clockwise:
            sign = -1
        else:
            sign = 1

        spline_points.add(radius_lines[0].endSketchPoint)
        for i in range(1, len(radius_lines)):
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
                f"{i + 1} * PI * {base_diameter_expr} * ({tangent_line_interval_deg} deg / 360 deg)"
            )

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
            outside_diameter_expr: str,
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

    @staticmethod
    def __create_dedendum_line(
            sketch: adsk.fusion.Sketch,
            center_point: adsk.fusion.SketchPoint,
            involute_curve_spline: adsk.fusion.SketchFittedSpline,
    ) -> adsk.fusion.SketchLine:
        line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(1, 1, 0),
            adsk.core.Point3D.create(2, 2, 0),
        )
        sketch.geometricConstraints.addCoincident(line.startSketchPoint, center_point)
        sketch.geometricConstraints.addCoincident(line.endSketchPoint, involute_curve_spline.startSketchPoint)
        return line

    @staticmethod
    def __extrude_tooth(
            comp: adsk.fusion.Component,
            gear_height_expr: str,
            spline: adsk.fusion.SketchFittedSpline,
            mirror_spline: adsk.fusion.SketchFittedSpline,
            root_circle: adsk.fusion.SketchCircle,
            base_circle: adsk.fusion.SketchCircle,
            dedendum_line_a: adsk.fusion.SketchLine,
            dedendum_line_b: adsk.fusion.SketchLine,
            root_fillet_radius_a: adsk.fusion.SketchArc,
            root_fillet_radius_b: adsk.fusion.SketchArc,
            name: str | None,
    ) -> adsk.fusion.Feature:
        profiles = adsk.core.ObjectCollection.create()

        # two profiles will be found the inside of tooth profile and all the way around the circle profile
        # we want the smaller of the two
        found_profiles = futil.find_profiles([dedendum_line_a, dedendum_line_b, root_circle, base_circle])
        if len(found_profiles) != 2:
            raise Exception(f"expected 2 profile, found {len(found_profiles)} for spur gear tooth (root)")
        profiles.add(futil.find_smallest_profile(found_profiles))

        # same here, we will find the inner and outer profiles
        found_profiles = futil.find_profiles([base_circle, spline, mirror_spline])
        if not (len(found_profiles) == 1 or len(found_profiles) == 2):
            raise Exception(f"expected 1 or 2 profile, found {len(found_profiles)} for spur gear tooth (tip)")
        profiles.add(futil.find_smallest_profile(found_profiles))

        # root fillet radius
        found_profiles = futil.find_profiles([root_fillet_radius_a, dedendum_line_a, root_circle])
        if not (len(found_profiles) == 1 or len(found_profiles) == 2):
            raise Exception(
                f"expected 1 or 2 profile, found {len(found_profiles)} for spur gear tooth (fillet radius a)"
            )
        profiles.add(futil.find_smallest_profile(found_profiles))

        found_profiles = futil.find_profiles([root_fillet_radius_b, dedendum_line_b, root_circle])
        if not (len(found_profiles) == 1 or len(found_profiles) == 2):
            raise Exception(
                f"expected 1 or 2 profile, found {len(found_profiles)} for spur gear tooth (fillet radius b)"
            )
        profiles.add(futil.find_smallest_profile(found_profiles))

        tooth_feature = comp.features.extrudeFeatures.addSimple(
            profiles,
            adsk.core.ValueInput.createByString(gear_height_expr),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        if name:
            tooth_feature.name = f"{name}_tooth"
            tooth_feature.bodies.item(0).name = f"{name}_tooth0"
        return tooth_feature

    @staticmethod
    def __create_tooth_rotation(
            comp: adsk.fusion.Component,
            tooth_feature: adsk.fusion.Feature,
            center_axis: adsk.fusion.ConstructionAxis,
            rotation_expr: str,
            name: str | None,
    ) -> adsk.fusion.MoveFeature:
        occurrence = comp.parentDesign.rootComponent.occurrencesByComponent(comp)[0]
        center_axis = center_axis.createForAssemblyContext(occurrence)
        move_create_input = adsk.core.ObjectCollection.create()
        move_create_input.add(tooth_feature.bodies[0])
        move_input = comp.features.moveFeatures.createInput2(move_create_input)
        move_input.defineAsRotate(center_axis, adsk.core.ValueInput.createByString(rotation_expr))
        feature = comp.features.moveFeatures.add(move_input)
        if name:
            feature.name = f"{name}_rotation"

        return feature

    @staticmethod
    def __create_tooth_circular_pattern(
            comp: adsk.fusion.Component,
            tooth_feature: adsk.fusion.Feature,
            root_circle: adsk.fusion.SketchCircle,
            number_of_teeth_expr: str,
            name: str | None,
    ) -> adsk.fusion.CircularPatternFeature:
        entities = adsk.core.ObjectCollection.create()
        entities.add(tooth_feature.bodies[0])
        axis = root_circle
        feature_input = comp.features.circularPatternFeatures.createInput(entities, axis)
        feature_input.quantity = adsk.core.ValueInput.createByString(number_of_teeth_expr)
        pattern = comp.features.circularPatternFeatures.add(feature_input)
        if name:
            pattern.name = f"{name}_toothCircularPattern"
            for i in range(len(pattern.bodies)):
                body = pattern.bodies.item(i)
                body.name = f"{name}_tooth{i + 1}"
        return pattern

    @staticmethod
    def __create_root_fillet_radius(
            sketch: adsk.fusion.Sketch,
            dedendum_line: adsk.fusion.SketchLine,
            root_circle: adsk.fusion.SketchCircle,
            root_fillet_radius_expr: str,
            tooth_thickness: float,
            name: str | None,
    ) -> [adsk.fusion.SketchArc, str]:
        x = root_circle.boundingBox.maxPoint.x
        if dedendum_line.boundingBox.maxPoint.y > 0:
            arc = sketch.sketchCurves.sketchArcs.addByThreePoints(
                adsk.core.Point3D.create(x, tooth_thickness, 0),  # point along root circle
                adsk.core.Point3D.create(x + 1, tooth_thickness * 0.5, 0),  # mid point
                adsk.core.Point3D.create(x + 2, tooth_thickness * 0.5, 0),  # point along dedendum line
            )
            sketch.geometricConstraints.addCoincident(arc.startSketchPoint, root_circle)
            sketch.geometricConstraints.addCoincident(arc.endSketchPoint, dedendum_line)
        else:
            arc = sketch.sketchCurves.sketchArcs.addByThreePoints(
                adsk.core.Point3D.create(x + 2, -tooth_thickness * 0.5, 0),  # point along dedendum line
                adsk.core.Point3D.create(x + 1, -tooth_thickness * 0.5, 0),  # mid point
                adsk.core.Point3D.create(x, -tooth_thickness, 0),  # point along root circle
            )
            sketch.geometricConstraints.addCoincident(arc.endSketchPoint, root_circle)
            sketch.geometricConstraints.addCoincident(arc.startSketchPoint, dedendum_line)

        d = sketch.sketchDimensions.addRadialDimension(
            arc,
            adsk.core.Point3D.create(1, 1, 0),
        )
        d.parameter.expression = root_fillet_radius_expr
        if name:
            d.parameter.name = f"{name}_rootFilletRadius"

        sketch.geometricConstraints.addTangent(root_circle, arc)
        sketch.geometricConstraints.addTangent(dedendum_line, arc)

        return arc, d.parameter.name
