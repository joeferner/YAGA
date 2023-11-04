import adsk.core
import os
from typing import cast

from .spur_gear import SpurGear
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
    pressure_angle_value = cast(adsk.core.ValueCommandInput, inputs.itemById("pressure_angle"))
    number_of_teeth_value = cast(adsk.core.ValueCommandInput, inputs.itemById("number_of_teeth"))
    module_value = cast(adsk.core.ValueCommandInput, inputs.itemById("module"))
    gear_height_value = cast(adsk.core.ValueCommandInput, inputs.itemById("gear_height"))

    spur_gear = SpurGear()
    spur_gear.create_component(
        app,
        pressure_angle_value=pressure_angle_value,
        number_of_teeth_value=number_of_teeth_value,
        module_value=module_value,
        gear_height_value=gear_height_value,
        name_prefix="spur_gear1"
    )


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
    value_input = cast(adsk.core.ValueCommandInput, inputs.itemById("pressure_angle"))
    if value_input.value >= 0:
        args.areInputsValid = True
    else:
        args.areInputsValid = False


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f"{CMD_NAME} Command Destroy Event")

    global local_handlers
    local_handlers = []
