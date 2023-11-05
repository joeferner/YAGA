import adsk.core
import adsk.fusion
import os
import math
from typing import cast
import time
from pathlib import Path

from .spur_gear import SpurGear
from ...lib import fusion360utils as futil
from ... import config
from ...lib import gear_drop_down as gear_drop_down_util

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_spurGear"
CMD_NAME = "Spur Gear"
CMD_Description = "Creates a spur gear"
ATTRIBUTE_GROUP_NAME = "YAGA_SpurGear"

RESOURCES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

_error_message = adsk.core.TextBoxCommandInput.cast(None)
_units: str | None = None
_help_pressure_angle: str | None = None


# Executed when add-in is run.
def start():
    # Create a command Definition.
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_definition:
        command_definition.deleteMe()
    command_definition = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, RESOURCES_FOLDER)

    global _help_pressure_angle
    _help_pressure_angle = Path(os.path.join(RESOURCES_FOLDER, "help/pressure_angle.html")).read_text()

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(command_definition.commandCreated, command_created)

    # Add a button into the UI so the user can run the command.
    gear_drop_down = gear_drop_down_util.get_gear_drop_down(ui)
    gear_drop_down.controls.addCommand(command_definition)


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
    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs
    design = adsk.fusion.Design.cast(app.activeProduct)
    default_units = design.unitsManager.defaultLengthUnits

    # Determine whether to use inches or millimeters as the initial default.
    global _units
    if default_units == "in" or default_units == "ft":
        _units = "in"
    else:
        _units = "mm"

    # help image
    i = inputs.addImageCommandInput("gearImageMetric", "", "commands/spur_gear/resources/gear-metric.png")
    i.isFullWidth = True

    # pressure angle
    attr = design.attributes.itemByName(ATTRIBUTE_GROUP_NAME, "pressureAngle")
    if attr:
        default_value = attr.value
    else:
        default_value = "20 deg"
    i = inputs.addValueInput(
        "pressure_angle", "Pressure Angle", "deg", adsk.core.ValueInput.createByString(default_value)
    )
    i.tooltip = "Pressure angle is the leaning angle of a gear tooth, an element determining the tooth profile."
    i.tooltipDescription = _help_pressure_angle

    # number of teeth
    attr = design.attributes.itemByName(ATTRIBUTE_GROUP_NAME, "numTeeth")
    if attr:
        default_value = attr.value
    else:
        default_value = "20"
    i = inputs.addValueInput(
        "number_of_teeth", "Number of Teeth", "", adsk.core.ValueInput.createByString(default_value)
    )
    i.minimumValue = 1

    # module
    attr = design.attributes.itemByName(ATTRIBUTE_GROUP_NAME, "module")
    if attr:
        default_value = attr.value
    else:
        default_value = "5 mm"
    i = inputs.addValueInput("module", "Module", "mm", adsk.core.ValueInput.createByString(default_value))
    i.tooltip = ("The unit of size that indicates how big or small a gear is. It is the ratio of the reference "
                 "diameter of the gear divided by the number of teeth. The larger the module the larger the gear.")

    # root fillet radius
    attr = design.attributes.itemByName(ATTRIBUTE_GROUP_NAME, "rootFilletRadius")
    if attr:
        default_value = attr.value
    else:
        default_value = "1 mm"
    i = inputs.addValueInput(
        "rootFilletRadius", "Root Fillet Radius", "mm", adsk.core.ValueInput.createByString(default_value)
    )
    i.tooltip = "The small radius that connects the tooth profile to the root circle."

    # thickness
    attr = design.attributes.itemByName(ATTRIBUTE_GROUP_NAME, "thickness")
    if attr:
        default_value = attr.value
    else:
        default_value = "5 mm"
    i = inputs.addDistanceValueCommandInput(
        "thickness", "Gear Height", adsk.core.ValueInput.createByString(default_value)
    )
    i.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(0, 0, 1))

    # error message
    global _error_message
    _error_message = inputs.addTextBoxCommandInput("errorMessage", "", "", 2, True)
    _error_message.isFullWidth = True

    # handlers
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
    command_run(args, False)


def command_execute_preview(args: adsk.core.CommandEventArgs):
    command_run(args, True)


def command_run(args: adsk.core.CommandEventArgs, preview: bool):
    start_time = time.time()
    design = adsk.fusion.Design.cast(app.activeProduct)
    inputs = args.command.commandInputs
    pressure_angle_value = cast(adsk.core.ValueCommandInput, inputs.itemById("pressure_angle"))
    number_of_teeth_value = cast(adsk.core.ValueCommandInput, inputs.itemById("number_of_teeth"))
    module_value = cast(adsk.core.ValueCommandInput, inputs.itemById("module"))
    root_fillet_radius_value = cast(adsk.core.ValueCommandInput, inputs.itemById("rootFilletRadius"))
    thickness_value = cast(adsk.core.DistanceValueCommandInput, inputs.itemById("thickness"))

    name = futil.find_next_name(design, "SpurGear")

    SpurGear.create_component(
        app,
        pressure_angle_value=pressure_angle_value,
        number_of_teeth_value=number_of_teeth_value,
        module_value=module_value,
        root_fillet_radius_value=root_fillet_radius_value,
        gear_height_value=thickness_value,
        preview=preview,
        name=name,
    )

    if not preview:
        design.attributes.add(ATTRIBUTE_GROUP_NAME, "pressureAngle", pressure_angle_value.expression)
        design.attributes.add(ATTRIBUTE_GROUP_NAME, "numTeeth", number_of_teeth_value.expression)
        design.attributes.add(ATTRIBUTE_GROUP_NAME, "module", module_value.expression)
        design.attributes.add(ATTRIBUTE_GROUP_NAME, "thickness", thickness_value.expression)

    end_time = time.time()
    futil.log(f"create took {end_time - start_time}")


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    pass


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    inputs = args.inputs
    design = adsk.fusion.Design.cast(app.activeProduct)
    args.areInputsValid = True

    pressure_angle_value = cast(adsk.core.AngleValueCommandInput, inputs.itemById("pressure_angle"))
    number_of_teeth_value = cast(adsk.core.ValueCommandInput, inputs.itemById("number_of_teeth"))
    module_value = cast(adsk.core.DistanceValueCommandInput, inputs.itemById("module"))
    root_fillet_radius_value = cast(adsk.core.DistanceValueCommandInput, inputs.itemById("rootFilletRadius"))

    # verify pressure angle
    if pressure_angle_value.value < math.radians(0):
        args.areInputsValid = False
        _error_message.text = "Pressure angle must be greater than 0"
        return
    if pressure_angle_value.value > math.radians(45):
        args.areInputsValid = False
        _error_message.text = "Pressure angle must be less than than 45 degrees"
        return

    # verify pressure angle
    if number_of_teeth_value.value < 1:
        args.areInputsValid = False
        _error_message.text = "Must have at least 1 tooth"
        return

    pitch = math.pi * module_value.value
    tooth_thickness = pitch / 2
    if root_fillet_radius_value.value > tooth_thickness * 0.4:
        args.areInputsValid = False
        max_value = design.unitsManager.formatInternalValue(tooth_thickness * 0.4, _units, True)
        _error_message.text = f"The root fillet radius is too large. It must be less than {max_value}"
        return

    # prevent change handler from firing over and over again
    if _error_message.text != "":
        _error_message.text = ""


# This event handler is called when the command terminates.
def command_destroy(_args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
