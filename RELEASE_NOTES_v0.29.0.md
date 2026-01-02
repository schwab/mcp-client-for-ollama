# Release Notes - v0.29.0: Ghost Writer Agents 🗣️✍️

**Release Date**: December 26, 2025
**Type**: Feature Release
**Breaking Changes**: None

---

## 🎉 Major New Feature: Ghost Writer Agents System

This release introduces the **Ghost Writer Agents** system - a set of specialized agents designed to help authors write novels by maintaining consistency, tracking story details, and providing intelligent suggestions.

### ✨ New: ACCENT_WRITER Agent

The first ghost writer agent is now available: **ACCENT_WRITER** 🗣️✍️

**Purpose**: Maintains character speech pattern consistency throughout a story

**Capabilities**:
- ✅ Defines and tracks each character's unique accent, dialect, and speech patterns
- ✅ Reviews dialogue for consistency with established character voices
- ✅ Flags inconsistencies and provides character-appropriate suggestions
- ✅ Self-manages memory via dedicated goal `G_ACCENT_WRITER`
- ✅ Learns and updates character profiles as the story develops
- ✅ Tracks speech evolution (e.g., character gaining education)

**Example Usage**:
```
Review this dialogue for accent consistency:

Lady Ashford said, "I am afraid I cannot permit such behavior."
Jake said, "Yeah, whatever. I'm outta here anyway."
```

**ACCENT_WRITER will**:
1. Create accent profiles for each character
2. Analyze formality, vocabulary, grammar patterns
3. Verify dialogue matches established patterns
4. Store profiles in persistent memory for future reference

### 🏗️ Architecture Highlights

**Self-Managed Memory System**:
- Each ghost writer agent has its own dedicated goal in memory
- Agents manage their own features (character profiles, rules, etc.)
- Memory persists across sessions
- Agents can query each other's knowledge for context

**Memory Structure**:
```
G_ACCENT_WRITER (Goal)
├── F_ACC_LADY_ASHFORD (Feature)
│   └── Formal, educated, aristocratic speech pattern
└── F_ACC_JAKE (Feature)
    └── Casual, street-smart, slang-heavy speech pattern
```

### 📋 Coming Soon

This release establishes the foundation for additional ghost writer agents:

**Priority 2**:
- 📋 **PROMPT_SPECIALIST** - Creates prompts for story-related media (images, music, etc.)

**Priority 3**:
- 📋 **RESEARCHER** - Verifies realism and suggests real-world alternatives

**Core Agents**:
- 📋 **LORE_KEEPER** - Tracks world rules, culture, geography, history
- 📋 **CHARACTER_KEEPER** - Tracks character details, arcs, relationships
- 📋 **QUALITY_MONITOR** - Scans for grammar, clarity, plot issues
- 📋 **DETAIL_CONTRIVER** - Generates minor needed details
- 📋 **STYLE_MONITOR** - Maintains formatting consistency

### 📚 Documentation

Complete documentation for ghost writer agents:
- `docs/DESIGN_ghost_writer_agents.md` - Architecture and design
- `docs/ghost_writer_progress.md` - Implementation progress and testing
- `docs/TESTING_ACCENT_WRITER.md` - Comprehensive testing guide
- `test_accent_writer_dialogue.md` - Sample test scenarios

### 🔧 Technical Details

**Files Added**:
- `mcp_client_for_ollama/agents/definitions/accent_writer.json` - ACCENT_WRITER agent definition

**Files Modified**:
- `mcp_client_for_ollama/agents/definitions/planner.json` - Added ghost writer agent recognition
- `mcp_client_for_ollama/__init__.py` - Version bump to 0.29.0
- `pyproject.toml` - Version bump to 0.29.0

**Agent Configuration**:
- **Model**: qwen2.5:32b (high quality for nuanced accent analysis)
- **Temperature**: 0.3 (consistent but creative suggestions)
- **Loop Limit**: 10 (allows thorough analysis)
- **Tools**: Memory management (builtin tools)

### 🧪 Testing

To test ACCENT_WRITER:

1. Start the client:
   ```bash
   ollmcp
   ```

2. Enable delegation and memory:
   ```
   /delegation on
   /memory on
   ```

3. Try a sample query:
   ```
   Review this dialogue: Lady Ashford said "I am quite certain." Jake said "Yeah dude."
   ```

See `docs/ghost_writer_progress.md` for complete testing instructions.

### 🎯 Use Cases

Perfect for:
- 📖 Novel writers maintaining character voice consistency
- ✍️ Screenwriters tracking character dialogue patterns
- 🎭 Game writers managing multiple character voices
- 📝 Story editors reviewing dialogue consistency

### 🔄 Backward Compatibility

Fully backward compatible:
- No breaking changes
- Existing agents and workflows unaffected
- New agent adds functionality without disrupting existing features

### 🐛 Bug Fixes

This release also includes fixes from v0.28.5 and v0.28.6:
- ✅ Python batch operations for data passing (v0.28.5)
- ✅ Enhanced PLANNER pattern detection (v0.28.6)
- ✅ STAY ON TASK violations addressed
- ✅ Improved batch operation handling

### 📦 Installation

```bash
pip install --upgrade mcp-client-for-ollama==0.29.0
```

Or install from wheel:
```bash
pip install dist/mcp_client_for_ollama-0.29.0-py3-none-any.whl
```

### 🙏 Acknowledgments

Special thanks to our author users who requested this feature and provided valuable feedback on character voice consistency tracking!

---

## Full Changelog

### Added
- 🆕 ACCENT_WRITER agent for character speech pattern consistency
- 🆕 Ghost writer agent architecture with self-managed memory
- 🆕 Comprehensive testing documentation and sample dialogues
- 🆕 PLANNER support for ghost writer agent assignment

### Changed
- 📝 PLANNER updated with ghost writer agent recognition
- 📝 Enhanced agent assignment decision tree

### Fixed
- ✅ Inherited fixes from v0.28.5 and v0.28.6

### Documentation
- 📚 Added DESIGN_ghost_writer_agents.md
- 📚 Added ghost_writer_progress.md
- 📚 Added TESTING_ACCENT_WRITER.md
- 📚 Added test_accent_writer_dialogue.md

---

**Release Package**: `mcp_client_for_ollama-0.29.0-py3-none-any.whl`
**Size**: 223KB
**Python**: >=3.10
**License**: MIT
