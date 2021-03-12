# Automatic Lighting
A Home Assistant custom component that provides a set of events and services to facilitate more advanced lighting setups with Home Assistant's default automation and blueprint engine

## Blueprints
Idle Lighting (Kelvin):\
https://raw.githubusercontent.com/mathias-jakobsen/ha-blueprints/main/automation/mathias-jakobsen/al_idle_kelvin.yaml

Active Lighting (Kelvin):\
https://raw.githubusercontent.com/mathias-jakobsen/ha-blueprints/main/automation/mathias-jakobsen/al_active_kelvin.yaml

Active Lighting (Adaptive):\
https://raw.githubusercontent.com/mathias-jakobsen/ha-blueprints/main/automation/mathias-jakobsen/al_active_adaptive.yaml

## Features
- Provides events and services to set ambient and triggered lighting through Home Assistant automations and blueprints.
- Detects manual control of lights, blocking itself for a set time period to prevent unwanted interference.

## Install
1. Add https://github.com/mathias-jakobsen/automatic_lighting.git to HACS as an integration.
2. Install the component through HACS.
3. Restart Home Assistant.

## Configuration
This integration can only be configured through the frontend by going to Configuration -> Integrations -> ( + Add Integration ) -> Automatic Lighting. To access the options, click the 'Options' button under your newly added integration.

### Options
It is possible to define which light entities belong to which light group entity (e.g. created in deconz). It is not required, but will enhance the way unused lights will be turned off.

| Name | Description | Default | Type |
| ---- | ----------- | ------- | ---- |
| block_timeout | The time (in seconds) the integration is blocked. | 300 | int
| light_groups | The light groups definitions. Uncheck a definition to delete it. | [] | list
| entity_id | The entity id of the light group to create a definition for. | | str
| entities | The entities that is part of the light group entity. | [] | list

## Usage
1. Import the blueprints (see the "Blueprints" section) into your Home Assistant instance.
2. Use the blueprints to create awesome automations!
