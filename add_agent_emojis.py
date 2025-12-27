#!/usr/bin/env python3
"""
Add unique emojis to each agent for visual identification.
"""

import json
from pathlib import Path

agents_dir = Path(__file__).parent / "mcp_client_for_ollama/agents/definitions"

# Define emoji mapping for each agent
# Using multiple emojis where helpful to convey context
AGENT_EMOJIS = {
    "PLANNER": "📋✨",           # Planning clipboard + sparkles for strategy
    "FILE_EXECUTOR": "📂🔒",     # Folder + lock (path locking!)
    "TEST_EXECUTOR": "🧪✅",     # Test tube + checkmark
    "CONFIG_EXECUTOR": "⚙️🔧",   # Gear + wrench for configuration
    "MEMORY_EXECUTOR": "🧠💾",   # Brain + disk for memory tracking
    "SHELL_EXECUTOR": "🐚💻",    # Shell + computer
    "EXECUTOR": "⚡🔧",          # Lightning + wrench (deprecated but keep)
    "CODER": "👨‍💻✏️",            # Coder + pencil
    "READER": "👀📖",           # Eyes + book
    "DEBUGGER": "🐛🔍",         # Bug + magnifying glass
    "AGGREGATOR": "📊🔄",       # Chart + arrows for synthesis
    "INITIALIZER": "🚀⚡",      # Rocket + lightning for bootstrap
    "RESEARCHER": "🔬📚",       # Microscope + books
    "LYRICIST": "🎵✍️",         # Music + writing
    "SUNO_COMPOSER": "🎼🎹",    # Musical score + keyboard
    "STYLE_DESIGNER": "🎨✨",   # Palette + sparkles
    "OBSIDIAN": "📝🔮",         # Note + crystal ball
}

print("=" * 80)
print("Adding Emojis to Agent Definitions")
print("=" * 80)

# Find all agent JSON files
agent_files = list(agents_dir.glob("*.json"))

updated_count = 0
for agent_file in sorted(agent_files):
    try:
        with open(agent_file, 'r') as f:
            config = json.load(f)

        agent_type = config.get("agent_type", "UNKNOWN")

        if agent_type in AGENT_EMOJIS:
            emoji = AGENT_EMOJIS[agent_type]

            # Add emoji field
            config["emoji"] = emoji

            # Update display_name to include emoji at the start
            current_name = config.get("display_name", "")
            # Remove any existing emojis first (in case running multiple times)
            # Simple approach: if name doesn't start with emoji, add it
            if not any(e in current_name[:5] for e in AGENT_EMOJIS.values()):
                config["display_name"] = f"{emoji} {current_name}"
            else:
                # Replace existing emoji
                for old_emoji in AGENT_EMOJIS.values():
                    if current_name.startswith(old_emoji):
                        current_name = current_name[len(old_emoji):].strip()
                        break
                config["display_name"] = f"{emoji} {current_name}"

            # Save updated config
            with open(agent_file, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"✓ {emoji} {agent_type:20s} → {agent_file.name}")
            updated_count += 1
        else:
            print(f"⚠ {agent_type:20s} → No emoji defined (skipped)")

    except Exception as e:
        print(f"✗ Error processing {agent_file.name}: {e}")

print()
print("=" * 80)
print("Summary")
print("=" * 80)
print(f"Updated {updated_count} agent definitions with emojis")
print()
print("Emoji Legend:")
print("-" * 80)
for agent_type, emoji in sorted(AGENT_EMOJIS.items()):
    print(f"{emoji}  {agent_type:20s}")
print()
print("Agents will now display with their emojis in:")
print("  - UI headers and displays")
print("  - Logs and traces")
print("  - Planning outputs")
print("  - Agent mentions in responses")
