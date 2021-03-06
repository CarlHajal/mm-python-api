---
tag: m092
title: Set Axis Steps-per-unit
brief: Set the number of steps-per-mm or steps-per-inch.

experimental: false
group: planner

codes:
  - M92

long:
  - Use `M92` to set the steps-per-unit for one or more axes. This setting affects how many steps will be done for each unit of movement. Units will be in steps/mm unless *inch* mode is set with [`G20`](/docs/gcode/G020.html) (which requires `INCH_MODE_SUPPORT`).

notes:
  - |
    Get the current steps-per-unit settings with `M503`.

    With `EEPROM_SETTINGS` enabled:

    - This setting for all axes is saved with `M500` and loaded with `M501`.
    - `M502` resets steps-per-unit for all axes to the values from `DEFAULT_AXIS_STEPS_PER_UNIT`.

parameters:
  -
    tag: X
    optional: true
    description: X steps per unit
    values:
      -
        tag: steps
        type: float
  -
    tag: Y
    optional: true
    description: Y steps per unit
    values:
      -
        tag: steps
        type: float
  -
    tag: Z
    optional: true
    description: Z steps per unit
    values:
      -
        tag: steps
        type: float
  -
    tag: E
    optional: true
    description: E steps per unit
    values:
      -
        tag: steps
        type: float
  -
    tag: T
    optional: true
    description: Target extruder (Requires `DISTINCT_E_FACTORS`)
    values:
      -
        tag: index
        type: int

example:
  -
    pre: Set E steps for a new extruder
    code: M92 E688.4

---
