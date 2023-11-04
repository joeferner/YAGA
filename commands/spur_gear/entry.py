import adsk.core
import os
import math
from ...lib import fusion360utils as futil
from ... import config
from ...lib import gear_drop_down as gear_drop_down_util

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_spurGear"
CMD_NAME = "Spur Gear"
CMD_Description = "Creates a spur gear"

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Create a command Definition.
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_definition:
        command_definition.deleteMe()
    command_definition = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(command_definition.commandCreated, command_created)

    # Add a button into the UI so the user can run the command.
    gear_drop_down = gear_drop_down_util.get_gear_drop_down(ui)
    control = gear_drop_down.controls.addCommand(command_definition)


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    gear_drop_down = gear_drop_down_util.get_gear_drop_down(ui)
    command_control = gear_drop_down.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f"{CMD_NAME} command_created")
    defaultLengthUnits = app.activeProduct.unitsManager.defaultLengthUnits

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    default_value = adsk.core.ValueInput.createByString("20 deg")
    inputs.addAngleValueCommandInput("pressure_angle", "Pressure Angle", default_value)

    default_value = adsk.core.ValueInput.createByString("20")
    inputs.addValueInput("number_of_teeth", "Number of Teeth", "", default_value)

    default_value = adsk.core.ValueInput.createByString("5 mm")
    inputs.addValueInput("module", "Module", "cm", default_value)

    default_value = adsk.core.ValueInput.createByString("5 mm")
    inputs.addValueInput("gear_height", "Gear Height", "cm", default_value)

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(
        args.command.executePreview,
        command_execute_preview,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.validateInputs,
        command_validate_input,
        local_handlers=local_handlers,
    )
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Execute Event")
    command_run(args)


def command_execute_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Execute Preview Event")
    command_run(args)


def command_run(args: adsk.core.CommandEventArgs):
    # See
    # https://www.youtube.com/watch?v=PGfIzIYITmU
    # https://www.instructables.com/Make-a-Gear-From-Scratch-in-Fusion-360/
    inputs = args.command.commandInputs
    pressure_angle_value: adsk.core.ValueCommandInput = inputs.itemById("pressure_angle")
    number_of_teeth_value: adsk.core.ValueCommandInput = inputs.itemById("number_of_teeth")
    module_value: adsk.core.ValueCommandInput = inputs.itemById("module")
    gear_height_value: adsk.core.ValueCommandInput = inputs.itemById("gear_height")
    tangent_line_count = 10
    tangent_line_interval_deg = 5

    unitsMgr = app.activeProduct.unitsManager
    pressure_angle = unitsMgr.evaluateExpression(pressure_angle_value.expression, "deg")
    number_of_teeth = unitsMgr.evaluateExpression(number_of_teeth_value.expression, "")
    module = unitsMgr.evaluateExpression(module_value.expression, "cm")
    gear_height = unitsMgr.evaluateExpression(gear_height_value.expression, "cm")

    # https://khkgears.net/new/gear_knowledge/abcs_of_gears-b/basic_gear_terminology_calculation.html
    # https://johnfsworkshop.org/home/processes-links/processes-removing-metal/the-milling-machine/the-milling-machine-workholding/worm-driven-rotary-devices/the-dividing-head/helical-milling-links/helical-milling-13-9-10/formulae-for-gears/
    pitch_diameter = number_of_teeth * module # PCD - D
    addendum = module # addendum - a
    base_diameter = pitch_diameter * math.cos(pressure_angle) # BC
    dedendum = pitch_diameter - base_diameter # dedendum - b
    root_diameter = pitch_diameter - (2 * dedendum) # ? - Dr
    outside_diameter = (number_of_teeth + 2) * module # OD - Do = ( N + 2 ) / P
    circular_pitch = module * math.pi # CP

    diametral_pitch_expr = f"( 1 / ({module_value.expression}) )"
    pitch_diameter_expr = f"( ({number_of_teeth_value.expression}) * ({module_value.expression}) )"
    base_diameter_expr = f"( {pitch_diameter_expr} * cos({pressure_angle_value.expression}) )"
    base_radius_expr = f"( {base_diameter_expr} / 2 )"
    root_diameter_expr = f"( (({number_of_teeth_value.expression}) * ({module_value.expression})) - (2 * (1.25 / (1 / ({module_value.expression})))) )"
    outside_diameter_expr = f"( (({number_of_teeth_value.expression}) + 2) / (1 / ({module_value.expression})) )"
    base_circumference_expr = f"( PI * {base_diameter_expr} )"
    tooth_thickness_expr = f"( {base_circumference_expr} / (({number_of_teeth_value.expression}) * 2) )"
    # https://khkgears.net/new/gear_knowledge/gear_technical_reference/tooth-thickness.html
    # f"( (PI / 2) + () ) * ({module_value.expression})"
    involute_curve_mirror_offset_angle_expr = f"( (PI / 2) / ({diametral_pitch_expr}*1 mm) ) / ({base_circumference_expr}/1 mm) * 360 deg / 2"

    # component
    comp = futil.create_new_component()

    # sketch
    sketch_plane = comp.xYConstructionPlane
    sketch = comp.sketches.add(sketch_plane)
    sketch.isComputeDeferred = True
    sketch.name = "SpurGear1"
    center_point = sketch.originPoint

    # root circle
    root_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), root_diameter / 2.0
    )
    sketch.geometricConstraints.addCoincident(root_circle.centerSketchPoint, center_point)
    d = sketch.sketchDimensions.addDiameterDimension(
        root_circle,
        adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.5, 0),
    )
    d.parameter.expression = root_diameter_expr

    # base circle
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

    # pitch circle
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

    # outside circle
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

    # involute curve mirror line
    involute_curve_mirror_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
        center_point, adsk.core.Point3D.create(1, 0, 0)
    )
    involute_curve_mirror_line.isConstruction = True
    sketch.geometricConstraints.addCoincident(involute_curve_mirror_line.endSketchPoint, outside_circle)
    sketch.geometricConstraints.addHorizontal(involute_curve_mirror_line)

    # involute curve center to tangent lines
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
    circular_pattern_input.quantity = adsk.core.ValueInput.createByString(f"{tangent_line_count}")
    circular_pattern_input.totalAngle = adsk.core.ValueInput.createByString(
        f"-{(tangent_line_count - 1) * tangent_line_interval_deg} deg"
    )
    circular_pattern = sketch.geometricConstraints.addCircularPattern(circular_pattern_input)

    radius_lines: list(adsk.fusion.SketchLine) = [radius_line]
    for entity in circular_pattern.createdEntities:
        line: adsk.fusion.SketchLine = entity
        radius_lines.append(line)

    spline_points = adsk.core.ObjectCollection.create()
    for i in range(len(radius_lines) - 1):
        radius_line: adsk.fusion.SketchLine = radius_lines[i]

        tangent_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            radius_line.endSketchPoint,
            adsk.core.Point3D.create(base_diameter, -base_diameter, 0),
        )
        tangent_line.isConstruction = True
        sketch.geometricConstraints.addTangent(base_circle, tangent_line)
        spline_points.add(tangent_line.endSketchPoint)

        d = sketch.sketchDimensions.addDistanceDimension(
            tangent_line.startSketchPoint,
            tangent_line.endSketchPoint,
            adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
            adsk.core.Point3D.create(base_diameter, -base_diameter, 0),
        )
        d.parameter.expression = (
            f"{len(radius_lines) - i - 1} * PI * {base_diameter_expr} * ({tangent_line_interval_deg} deg / 360 deg)"
        )
    spline_points.add(radius_lines[len(radius_lines) - 1].endSketchPoint)

    # create dimension to place spline in correct location
    d = sketch.sketchDimensions.addAngularDimension(
        involute_curve_mirror_line,
        radius_lines[len(radius_lines) - 1],
        adsk.core.Point3D.create(outside_diameter, -1, 0),
    )
    d.parameter.expression = involute_curve_mirror_offset_angle_expr

    # create involute spline
    spline = sketch.sketchCurves.sketchFittedSplines.add(spline_points)

    # create involute spline mirror radius
    spline_mirror_radius_line = sketch.sketchCurves.sketchLines.addByTwoPoints(
        adsk.core.Point3D.create(0, 0, 0),
        adsk.core.Point3D.create(base_diameter / 2.0, 1, 0),
    )
    spline_mirror_radius_line.isConstruction = True
    sketch.geometricConstraints.addCoincident(spline_mirror_radius_line.startSketchPoint, center_point)
    sketch.geometricConstraints.addCoincident(spline_mirror_radius_line.endSketchPoint, base_circle)
    d = sketch.sketchDimensions.addAngularDimension(
        involute_curve_mirror_line,
        spline_mirror_radius_line,
        adsk.core.Point3D.create(outside_diameter, 1, 0),
    )
    d.parameter.expression = involute_curve_mirror_offset_angle_expr
    
    # create involute spline mirror
    mirror_spline, _ = futil.mirror_sketch_spline(sketch, spline, involute_curve_mirror_line)

    # create tooth top land
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

    # finish up
    sketch.isComputeDeferred = False


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    # General logging for debug.
    futil.log(f"{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}")


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    inputs = args.inputs

    # Verify the validity of the input values. This controls if the OK button is enabled or not.
    valueInput = inputs.itemById("pressure_angle")
    if valueInput.value >= 0:
        args.areInputsValid = True
    else:
        args.areInputsValid = False


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Destroy Event")

    global local_handlers
    local_handlers = []
