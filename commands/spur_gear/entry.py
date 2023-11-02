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
    curve_point_count = 10

    unitsMgr = app.activeProduct.unitsManager
    pressure_angle = unitsMgr.evaluateExpression(pressure_angle_value.expression, "deg")
    number_of_teeth = unitsMgr.evaluateExpression(number_of_teeth_value.expression, "")
    module = unitsMgr.evaluateExpression(module_value.expression, "cm")
    gear_height = unitsMgr.evaluateExpression(gear_height_value.expression, "cm")

    pitch_diameter = number_of_teeth * module
    diametral_pitch = 1 / module
    addendum = 1 / diametral_pitch
    dedendum = 1.25 / diametral_pitch
    root_diameter = pitch_diameter - (2 * dedendum)
    base_diameter = pitch_diameter * math.cos(pressure_angle)
    outside_diameter = (number_of_teeth + 2) / diametral_pitch

    pitch_diameter_expr = f"( ({number_of_teeth_value.expression}) * ({module_value.expression}) )"
    base_diameter_expr = f"( {pitch_diameter_expr} * cos({pressure_angle_value.expression}) )"
    base_radius_expr = f"( {base_diameter_expr} / 2 )"
    root_diameter_expr = f"( (({number_of_teeth_value.expression}) * ({module_value.expression})) - (2 * (1.25 / (1 / ({module_value.expression})))) )"
    outside_diameter_expr = f"( (({number_of_teeth_value.expression}) + 2) / (1 / ({module_value.expression})) )"
    base_circumference_expr = f"( 2 * {math.pi} * ({base_diameter_expr} / 2) )"
    tooth_thickness_expr = f"( {base_circumference_expr} / (({number_of_teeth_value.expression}) * 2) )"

    # component
    comp = futil.create_new_component()

    # sketch
    sketch_plane = comp.xYConstructionPlane
    base_sketch = comp.sketches.add(sketch_plane)
    base_sketch.isComputeDeferred = True
    base_sketch.name = "SpurGear1"
    center_point = base_sketch.originPoint

    # root circle
    root_circle = base_sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), root_diameter / 2.0
    )
    base_sketch.geometricConstraints.addCoincident(root_circle.centerSketchPoint, center_point)
    d = base_sketch.sketchDimensions.addDiameterDimension(
        root_circle,
        adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.5, 0),
    )
    d.parameter.expression = root_diameter_expr

    # base circle
    base_circle = base_sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), base_diameter / 2.0
    )
    base_circle.isConstruction = True
    base_sketch.geometricConstraints.addCoincident(base_circle.centerSketchPoint, center_point)
    d = base_sketch.sketchDimensions.addDiameterDimension(
        base_circle,
        adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.4, 0),
    )
    d.parameter.expression = base_diameter_expr

    # outside circle
    outside_circle = base_sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), outside_diameter / 2.0
    )
    outside_circle.isConstruction = True
    base_sketch.geometricConstraints.addCoincident(outside_circle.centerSketchPoint, center_point)
    d = base_sketch.sketchDimensions.addDiameterDimension(
        outside_circle,
        adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.3, 0),
    )
    d.parameter.expression = outside_diameter_expr

    # pitch circle
    pitch_circle = base_sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), pitch_diameter / 2.0
    )
    pitch_circle.isConstruction = True
    base_sketch.geometricConstraints.addCoincident(pitch_circle.centerSketchPoint, center_point)
    d = base_sketch.sketchDimensions.addDiameterDimension(
        pitch_circle,
        adsk.core.Point3D.create(-root_diameter / 1.5, root_diameter / 1.2, 0),
    )
    d.parameter.expression = pitch_diameter_expr

    # involute curve mirror line
    involute_curve_mirror_line = base_sketch.sketchCurves.sketchLines.addByTwoPoints(
        center_point, adsk.core.Point3D.create(1, 0, 0)
    )
    involute_curve_mirror_line.isConstruction = True
    # base_sketch.geometricConstraints.addCoincident(involute_curve_mirror_line.startSketchPoint, center_point)
    base_sketch.geometricConstraints.addCoincident(involute_curve_mirror_line.endSketchPoint, outside_circle)
    base_sketch.geometricConstraints.addHorizontal(involute_curve_mirror_line)

    # involute curve
    curve_points = adsk.core.ObjectCollection.create()
    for t in range(0, curve_point_count):
        curve_points.add(adsk.core.Point3D.create(t + 1, t + 1, 0))

    spline = base_sketch.sketchCurves.sketchFittedSplines.add(curve_points)

    t = 0
    involute_size_expr = f"( ({outside_diameter_expr} - {base_diameter_expr}) / 2 )"
    for pt in spline.fitPoints:
        if t == 0:
            t_expr = "0"
        else:
            t_expr = f"( (({involute_size_expr} / ({curve_point_count} - 1)) * {t}) )"

        dist_from_center_to_point_expr = f"( ({base_diameter_expr} / 2) + {t_expr} )"

        # Calculate the other side of the right-angle triangle defined by the base circle and the current distance radius.
        # This is also the length of the involute chord as it comes off of the base circle.
        triangle_side_expr = f"( sqrt( ({dist_from_center_to_point_expr} ^ 2) - ({base_radius_expr} ^ 2) ) )"

        # Calculate the angle of the involute.
        alpha_expr = f"( {triangle_side_expr} / {base_radius_expr} )"

        # Calculate the angle where the current involute point is.
        theta_expr = f"( {alpha_expr} - acos({base_radius_expr} / {dist_from_center_to_point_expr}) )"

        # Calculate the coordinates of the involute point.
        # x_expr = f"( {dist_from_center_to_point_expr} * cos({theta_expr}) )"
        # y_expr = "1" # f"( {dist_from_center_to_point_expr} * sin({theta_expr}) )"

        theta_expr = f"sqrt(100 * {dist_from_center_to_point_expr})".replace('mm', '')

        line = base_sketch.sketchCurves.sketchLines.addByTwoPoints(center_point, pt.geometry)
        line.isConstruction = True
        # base_sketch.geometricConstraints.addCoincident(line.startSketchPoint, center_point)
        base_sketch.geometricConstraints.addCoincident(line.endSketchPoint, pt)

        d = base_sketch.sketchDimensions.addDistanceDimension(
            center_point,
            pt,
            adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
            adsk.core.Point3D.create(1, 1, 0),
        )
        d.parameter.expression = dist_from_center_to_point_expr

        d = base_sketch.sketchDimensions.addAngularDimension(
            involute_curve_mirror_line,
            line,
            adsk.core.Point3D.create(10, 0.1, 0),
        )
        try:
            d.parameter.expression = theta_expr
        except:
            futil.log(f"invalid expr {theta_expr}")

        t = t + 1

    # finish up
    base_sketch.isComputeDeferred = False


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
