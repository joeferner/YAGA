import math
import adsk.core
import adsk.fusion


# https://khkgears.net/new/gear_knowledge/abcs_of_gears-b/basic_gear_terminology_calculation.html
class Rack:
    @staticmethod
    def create_component(
            app: adsk.core.Application,
            pressure_angle_value: adsk.core.ValueCommandInput,
            number_of_teeth_value: adsk.core.ValueCommandInput,
            module_value: adsk.core.ValueCommandInput,
            root_fillet_radius_value: adsk.core.ValueCommandInput,
            gear_thickness_value: adsk.core.DistanceValueCommandInput,
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

        root_fillet_radius = root_fillet_radius_value.value
        root_fillet_radius_expr = f"({root_fillet_radius_value.expression})"

        gear_thickness_expr = f"({gear_thickness_value.expression})"

        backlash_expr = f"({backlash_value.expression})"

        # dedendum (hf)
        dedendum = 1.25 * module
        dedendum_expr = f"( 1.25 * {module_expr} )"

        # pitch (p) - Pitch is the distance between corresponding points on adjacent teeth
        pitch = math.pi * module
        pitch_expr = f"( PI * {module_expr} )"

        # tooth thickness (s)
        tooth_thickness_expr = f"( {pitch_expr} / 2 )"

        # height
        height_expr = f"({module_expr} + {dedendum_expr})"

        # bottom box height
        bottom_box_height_expr = f"1 {units_mgr.defaultLengthUnits}"

        # create component
        comp_occurrence = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = comp_occurrence.component
        if name:
            comp.name = name

        # construction sketch
        construction_sketch = Rack.__create_construction_sketch(
            comp,
            dedendum_expr,
            number_of_teeth_expr,
            pitch_expr,
            name
        )

        # tooth sketch
        tooth_sketch = Rack.__create_tooth_sketch(
            comp,
            pitch_expr,
            tooth_thickness_expr,
            pressure_angle_expr,
            height_expr,
            dedendum_expr,
            bottom_box_height_expr,
            root_fillet_radius_expr,
            name,
        )

        # extrude tooth
        tooth_extrude = Rack.__extrude_tooth(comp, tooth_sketch, gear_thickness_expr, name)

        if not preview:
            construction_sketch.isVisible = False

        # linear pattern for number of teeth
        tooth_pattern = Rack.__create_tooth_linear_pattern(
            comp, tooth_extrude,
            direction_one_entity=comp.xConstructionAxis,
            direction_two_entity=comp.yConstructionAxis,
            number_of_teeth_expr=number_of_teeth_expr,
            pitch_expr=pitch_expr,
            name=name
        )

        # group features into one
        group = design.timeline.timelineGroups.add(
            comp_occurrence.timelineObject.index, tooth_pattern.timelineObject.index
        )
        if name:
            group.name = name

        return

    @staticmethod
    def __create_construction_sketch(
            comp: adsk.fusion.Component,
            dedendum_expr: str,
            number_of_teeth_expr: str,
            pitch_expr: str,
            name: str | None
    ) -> adsk.fusion.Sketch:
        sketch_plane = comp.xYConstructionPlane
        sketch = comp.sketches.add(sketch_plane)
        if name:
            sketch.name = f"{name}_construction"
        center_point = sketch.originPoint
        sketch.isComputeDeferred = True

        pitch_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(1, 10, 0),
            adsk.core.Point3D.create(10, 10, 0),
        )
        pitch_line.isConstruction = True
        sketch.geometricConstraints.addHorizontal(pitch_line)
        sketch.geometricConstraints.addVerticalPoints(pitch_line.startSketchPoint, center_point)

        d = sketch.sketchDimensions.addDistanceDimension(
            pitch_line.startSketchPoint,
            center_point,
            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            adsk.core.Point3D.create(1, 10, 0),
        )
        d.parameter.expression = dedendum_expr
        if name:
            d.parameter.name = f"{name}_dedendum"

        d = sketch.sketchDimensions.addDistanceDimension(
            pitch_line.startSketchPoint,
            pitch_line.endSketchPoint,
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            adsk.core.Point3D.create(1, 10, 0),
        )
        d.parameter.expression = f"{number_of_teeth_expr} * {pitch_expr}"
        if name:
            d.parameter.name = f"{name}_pitchConstructionLength"

        sketch.isComputeDeferred = False

        return sketch

    @staticmethod
    def __create_tooth_sketch(
            comp: adsk.fusion.Component,
            pitch_expr: str,
            tooth_thickness_expr: str,
            pressure_angle_expr: str,
            height_expr: str,
            dedendum_expr: str,
            bottom_box_height_expr: str,
            root_fillet_radius_expr: str,
            name: str | None,
    ) -> adsk.fusion.Sketch:
        sketch_plane = comp.xYConstructionPlane
        sketch = comp.sketches.add(sketch_plane)
        if name:
            sketch.name = f"{name}_tooth"
        center_point = sketch.originPoint
        sketch.isComputeDeferred = True

        # draw root line left
        root_line_left = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(1, 1, 0),
            adsk.core.Point3D.create(2, 1, 0),
        )
        sketch.geometricConstraints.addCoincident(root_line_left.startSketchPoint, center_point)
        sketch.geometricConstraints.addHorizontal(root_line_left)

        # draw gear face left
        face_line_left = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(10, 10, 0),
            adsk.core.Point3D.create(20, 20, 0),
        )
        sketch.geometricConstraints.addCoincident(face_line_left.startSketchPoint, root_line_left.endSketchPoint)

        d = sketch.sketchDimensions.addAngularDimension(
            root_line_left, face_line_left, adsk.core.Point3D.create(0, 10, 0)
        )
        d.parameter.expression = f"{pressure_angle_expr} + 90 deg"
        if name:
            d.parameter.name = f"{name}_faceAngle"

        d = sketch.sketchDimensions.addDistanceDimension(
            face_line_left.startSketchPoint,
            face_line_left.endSketchPoint,
            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            adsk.core.Point3D.create(0, 5, 0),
        )
        d.parameter.expression = f"{height_expr}"
        if name:
            d.parameter.name = f"{name}_height"

        # draw tooth top land
        top_land = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(11, 11, 0),
            adsk.core.Point3D.create(21, 21, 0),
        )
        sketch.geometricConstraints.addHorizontal(top_land)
        sketch.geometricConstraints.addCoincident(top_land.startSketchPoint, face_line_left.endSketchPoint)

        # draw gear face right
        face_line_right = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(22, 22, 0),
            adsk.core.Point3D.create(30, 5, 0),
        )
        sketch.geometricConstraints.addCoincident(face_line_right.startSketchPoint, top_land.endSketchPoint)

        d = sketch.sketchDimensions.addAngularDimension(
            root_line_left, face_line_right, adsk.core.Point3D.create(0, 10, 0)
        )
        d.parameter.expression = f"90 deg - {pressure_angle_expr}"
        if name:
            d.parameter.name = f"{name}_faceAngleRight"

        # draw root line right
        root_line_right = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(31, 1, 0),
            adsk.core.Point3D.create(31, 1, 0),
        )
        sketch.geometricConstraints.addHorizontal(root_line_right)
        sketch.geometricConstraints.addCoincident(root_line_right.startSketchPoint, face_line_right.endSketchPoint)

        d = sketch.sketchDimensions.addDistanceDimension(
            face_line_right.startSketchPoint,
            root_line_right.endSketchPoint,
            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            adsk.core.Point3D.create(0, 5, 0),
        )
        d.parameter.expression = f"{height_expr}"
        if name:
            d.parameter.name = f"{name}_height"

        # draw bottom box right
        bottom_box_right = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(32, 1, 0),
            adsk.core.Point3D.create(32, -5, 0),
        )
        sketch.geometricConstraints.addVertical(bottom_box_right)
        sketch.geometricConstraints.addCoincident(root_line_right.endSketchPoint, bottom_box_right.startSketchPoint)
        d = sketch.sketchDimensions.addDistanceDimension(
            bottom_box_right.startSketchPoint,
            bottom_box_right.endSketchPoint,
            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            adsk.core.Point3D.create(0, 10, 0),
        )
        d.parameter.expression = bottom_box_height_expr
        if name:
            d.parameter.name = f"{name}_offsetHeight"

        # draw bottom box right
        bottom_box_left = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(1, 1, 0),
            adsk.core.Point3D.create(1, -5, 0),
        )
        sketch.geometricConstraints.addVertical(bottom_box_left)
        sketch.geometricConstraints.addCoincident(root_line_left.startSketchPoint, bottom_box_left.startSketchPoint)
        sketch.geometricConstraints.addEqual(bottom_box_right, bottom_box_left)

        # draw bottom box bottom
        bottom_box_bottom = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(1, -1, 0),
            adsk.core.Point3D.create(10, -1, 0),
        )
        sketch.geometricConstraints.addHorizontal(bottom_box_bottom)
        sketch.geometricConstraints.addCoincident(bottom_box_bottom.startSketchPoint, bottom_box_left.endSketchPoint)
        sketch.geometricConstraints.addCoincident(bottom_box_bottom.endSketchPoint, bottom_box_right.endSketchPoint)

        # left root fillet
        root_fillet_left = sketch.sketchCurves.sketchArcs.addFillet(
            root_line_left,
            root_line_left.endSketchPoint.geometry,
            face_line_left,
            face_line_left.startSketchPoint.geometry,
            0.01,
        )
        d = sketch.sketchDimensions.addRadialDimension(root_fillet_left, adsk.core.Point3D.create(0, 10, 0))
        d.parameter.expression = root_fillet_radius_expr
        if name:
            d.parameter.name = f"{name}_rootFilletRadius"

        # right root fillet
        root_fillet_right = sketch.sketchCurves.sketchArcs.addFillet(
            face_line_right,
            face_line_right.endSketchPoint.geometry,
            root_line_right,
            root_line_right.startSketchPoint.geometry,
            0.01,
        )
        sketch.geometricConstraints.addEqual(root_fillet_left, root_fillet_right)

        # tooth thickness/width
        d = sketch.sketchDimensions.addDistanceDimension(
            root_line_left.startSketchPoint,
            root_line_right.endSketchPoint,
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            adsk.core.Point3D.create(1, -1, 0),
        )
        d.parameter.expression = pitch_expr
        if name:
            d.parameter.name = f"{name}_pitch"

        # draw tooth center line
        center_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(11, 10, 0),
            adsk.core.Point3D.create(10, -1, 0),
        )
        center_line.isConstruction = True
        sketch.geometricConstraints.addVertical(center_line)
        sketch.geometricConstraints.addMidPoint(center_line.startSketchPoint, top_land)
        sketch.geometricConstraints.addMidPoint(center_line.endSketchPoint, bottom_box_bottom)

        # draw pitch line
        pitch_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(1, 10, 0),
            adsk.core.Point3D.create(10, 10, 0),
        )
        pitch_line.isConstruction = True
        sketch.geometricConstraints.addHorizontal(pitch_line)
        sketch.geometricConstraints.addCoincident(pitch_line.startSketchPoint, face_line_left)
        sketch.geometricConstraints.addCoincident(pitch_line.endSketchPoint, face_line_right)

        d = sketch.sketchDimensions.addDistanceDimension(
            pitch_line.startSketchPoint,
            root_line_left.startSketchPoint,
            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            adsk.core.Point3D.create(1, 10, 0),
        )
        d.parameter.expression = dedendum_expr
        if name:
            d.parameter.name = f"{name}_dedendum"

        # tooth thickness dimension
        d = sketch.sketchDimensions.addDistanceDimension(
            pitch_line.startSketchPoint,
            pitch_line.endSketchPoint,
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            adsk.core.Point3D.create(1, -1, 0),
        )
        d.parameter.expression = tooth_thickness_expr
        if name:
            d.parameter.name = f"{name}_toothThickness"

        sketch.isComputeDeferred = False
        return sketch

    @staticmethod
    def __extrude_tooth(
            comp: adsk.fusion.Component, sketch: adsk.fusion.Sketch, gear_thickness_expr: str, name: str
    ) -> adsk.fusion.ExtrudeFeature:
        profile = sketch.profiles[0]

        rack_feature = comp.features.extrudeFeatures.addSimple(
            profile,
            adsk.core.ValueInput.createByString(gear_thickness_expr),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        if name:
            rack_feature.name = f"{name}"
            rack_feature.bodies.item(0).name = f"{name}"
        return rack_feature

    @staticmethod
    def __create_tooth_linear_pattern(
            comp: adsk.fusion.Component,
            tooth_extrude: adsk.fusion.ExtrudeFeature,
            direction_one_entity: adsk.core.Base,
            direction_two_entity: adsk.core.Base,
            number_of_teeth_expr: str,
            pitch_expr: str,
            name: str | None,
    ) -> adsk.fusion.RectangularPatternFeature:
        entities = adsk.core.ObjectCollection.create()
        entities.add(tooth_extrude.bodies[0])
        feature_input = comp.features.rectangularPatternFeatures.createInput(
            entities,
            direction_one_entity,
            adsk.core.ValueInput.createByString(number_of_teeth_expr),
            adsk.core.ValueInput.createByString(pitch_expr),
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType,
        )
        feature_input.setDirectionTwo(
            direction_two_entity,
            adsk.core.ValueInput.createByReal(1),
            adsk.core.ValueInput.createByReal(1)
        )
        pattern = comp.features.rectangularPatternFeatures.add(feature_input)
        if name:
            pattern.name = f"{name}_toothLinearPattern"
            for i in range(len(pattern.bodies)):
                body = pattern.bodies.item(i)
                body.name = f"{name}_tooth{i + 1}"
        return pattern
