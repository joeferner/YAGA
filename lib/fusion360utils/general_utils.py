#  Copyright 2022 by Autodesk, Inc.
#  Permission to use, copy, modify, and distribute this software in object code form
#  for any purpose and without fee is hereby granted, provided that the above copyright
#  notice appears in all copies and that both that copyright notice and the limited
#  warranty and restricted rights notice below appear in all supporting documentation.
#
#  AUTODESK PROVIDES THIS PROGRAM "AS IS" AND WITH ALL FAULTS. AUTODESK SPECIFICALLY
#  DISCLAIMS ANY IMPLIED WARRANTY OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR USE.
#  AUTODESK, INC. DOES NOT WARRANT THAT THE OPERATION OF THE PROGRAM WILL BE
#  UNINTERRUPTED OR ERROR FREE.

import traceback
import adsk.core
import adsk.fusion

app = adsk.core.Application.get()
ui = app.userInterface

# Attempt to read DEBUG flag from parent config.
try:
    from ... import config

    DEBUG = config.DEBUG
except Exception:
    DEBUG = False


def log(
        message: str,
        level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel,
        force_console: bool = False,
):
    """Utility function to easily handle logging in your app.

    Arguments:
    message -- The message to log.
    level -- The logging severity level.
    force_console -- Forces the message to be written to the Text Command window.
    """
    # Always print to console, only seen through IDE.
    print(message)

    # Log all errors to Fusion log file.
    if level == adsk.core.LogLevels.ErrorLogLevel:
        log_type = adsk.core.LogTypes.FileLogType
        app.log(message, level, log_type)

    # If config.DEBUG is True write all log messages to the console.
    if DEBUG or force_console:
        log_type = adsk.core.LogTypes.ConsoleLogType
        app.log(message, level, log_type)


def handle_error(name: str, show_message_box: bool = False):
    """Utility function to simplify error handling.

    Arguments:
    name -- A name used to label the error.
    show_message_box -- Indicates if the error should be shown in the message box.
                        If False, it will only be shown in the Text Command window
                        and logged to the log file.
    """

    log("===== Error =====", adsk.core.LogLevels.ErrorLogLevel)
    log(f"{name}\n{traceback.format_exc()}", adsk.core.LogLevels.ErrorLogLevel)

    # If desired you could show an error as a message box.
    if show_message_box:
        ui.messageBox(f"{name}\n{traceback.format_exc()}")


def find_profiles(curves: list[adsk.fusion.SketchCurve]) -> list[adsk.fusion.Profile]:
    if len(curves) == 0:
        return []
    profiles: [adsk.fusion.Profile] = []
    sketch = curves[0].parentSketch
    for profile in sketch.profiles:
        if profile_contains_curves(profile, curves):
            profiles.append(profile)
    return profiles


def profile_contains_curves(profile: adsk.fusion.Profile, curves: list[adsk.fusion.SketchCurve]) -> bool:
    for curve in curves:
        if not profile_contains_curve(profile, curve):
            return False
    return True


def profile_contains_curve(profile: adsk.fusion.Profile, curve: adsk.fusion.SketchCurve) -> bool:
    for loop in profile.profileLoops:
        for profile_curve in loop.profileCurves:
            if profile_curve.sketchEntity == curve:
                return True
    return False


def find_smallest_profile(profiles: list[adsk.fusion.Profile]) -> adsk.fusion.Profile:
    smallest_profile = None
    smallest_profile_area = 0
    for profile in profiles:
        area = (abs(profile.boundingBox.maxPoint.x - profile.boundingBox.minPoint.x)
                * abs(profile.boundingBox.maxPoint.y - profile.boundingBox.minPoint.y))
        if smallest_profile is None or area < smallest_profile_area:
            smallest_profile = profile
            smallest_profile_area = area
    return smallest_profile
