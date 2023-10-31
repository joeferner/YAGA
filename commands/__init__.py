import adsk.core
from .spur_gear import entry as spur_gear
from ..lib import gear_drop_down as gear_drop_down_util

commands = [spur_gear]
app = adsk.core.Application.get()
ui = app.userInterface


# Assumes you defined a "start" function in each of your modules.
# The start function will be run when the add-in is started.
def start():
    for command in commands:
        command.start()


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        command.stop()

    gear_drop_down = gear_drop_down_util.get_gear_drop_down(ui)
    if gear_drop_down:
        gear_drop_down.deleteMe()
