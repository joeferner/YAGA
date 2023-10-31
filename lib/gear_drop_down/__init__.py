from ... import config
import os

GEAR_DROP_DOWN_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_gear_drop_down_id"
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")


def get_gear_drop_down(ui):
    workspace = ui.workspaces.itemById("FusionSolidEnvironment")
    panel = workspace.toolbarPanels.itemById("SolidCreatePanel")
    gear_drop_down = panel.controls.itemById(GEAR_DROP_DOWN_ID)
    if not gear_drop_down:
        gear_drop_down = panel.controls.addDropDown(
            "Gear", ICON_FOLDER, GEAR_DROP_DOWN_ID
        )
    return gear_drop_down
