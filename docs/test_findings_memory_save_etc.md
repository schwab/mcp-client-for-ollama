- ability to change models per agent type (this should work like the existing global model chooser but allow selection for each agent uniquely)
- show the models currently selected for each agent type
- ability to set the context size per agent via the application (all model settings should be configurable)
- ability to interupt planning state with ctrl+c without existing the application (sometimes planner gets stuck or models don't load so the user has to kill the process)
- ability to pull latest build from the github releases page and self-install updates
- display/show the model being used by each agent when it says like "Executing task_x (EXECUTOR)" add <model_name>
- make sure the built in tool calls like : builtin.update_config_section actually save the changes they make. This trace says it changed the settings, but they did not actually save.trace_20251216_204919.json
- this   trace_20251216_205351.json also attempted to change the setting, but it ended up with mangled json... (the whole memory section eneded up as a string )  "sessionSaveDirectory": ".config",
  "memory": "{\"enabled\": true}",
  "delegation": {
    "enabled": true,
    "collapsible_output": {
      "auto_collapse": true,
      "line_threshold": 20,
      "char_threshold": 1000
    },

