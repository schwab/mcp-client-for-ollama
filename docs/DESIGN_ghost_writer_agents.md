# Ghost Writer Agents - Architecture Design

## Overview

A set of specialized agents that help authors write novels by maintaining consistency, tracking details, and making suggestions. Each agent has its own memory context and actively reviews new text against established story elements.

## Memory Architecture

### Using Existing Memory System

Each ghost writer agent gets:
- **One Goal** in the memory system (e.g., `G_LORE_KEEPER`)
- **Features under that goal** for specific tracked items
- **Self-managed memory** via builtin memory tools

### Goal Structure

```
G_LORE_KEEPER (Goal)
├── F_LORE_1: Magic System Rules
├── F_LORE_2: Kingdom Geography
└── F_LORE_3: Historical Timeline

G_CHARACTER_KEEPER (Goal)
├── F_CHAR_1: Protagonist - Elena
├── F_CHAR_2: Antagonist - Daemon
└── F_CHAR_3: Supporting - Marcus

G_ACCENT_WRITER (Goal)
├── F_ACC_1: Elena's Speech Pattern
├── F_ACC_2: Daemon's Dialect
└── F_ACC_3: Regional Accents

... (other agents)
```

### Memory Operations

Each agent can:
- **Read** its own memory: `builtin.get_goal_details(goal_id='G_LORE_KEEPER')`
- **Add** new features: `builtin.add_feature(goal_id='G_LORE_KEEPER', ...)`
- **Update** features: `builtin.update_feature(feature_id='F_LORE_1', ...)`
- **Track** progress: `builtin.log_progress(goal_id='G_LORE_KEEPER', ...)`

## Agent Definitions

### Priority 1: Accent Writer (ACCENT_WRITER)

**Purpose**: Maintain character accent and speech pattern consistency

**Responsibilities**:
- Define each character's unique accent/dialect
- Track speech patterns, vocabulary, grammar quirks
- Verify new dialogue matches established patterns
- Suggest corrections when dialogue is inconsistent

**Memory Structure**:
- Goal: `G_ACCENT_WRITER` - "Maintain character accent consistency"
- Features: One per character (e.g., `F_ACC_ELENA`, `F_ACC_DAEMON`)
- Feature content: Speech pattern rules, example phrases, vocabulary quirks

**System Prompt**:
```
You are an Accent Writer specialist. Your job is to maintain consistency in how each character speaks.

GOAL ID: G_ACCENT_WRITER (automatically set when agent is invoked)

Responsibilities:
1. Define and document each character's unique speech patterns
2. Track vocabulary choices, grammar quirks, dialects
3. Review new dialogue for consistency with established patterns
4. Suggest corrections when dialogue doesn't match character's voice

Memory Management:
- Use builtin.get_goal_details(goal_id='G_ACCENT_WRITER') to view all tracked accents
- Use builtin.add_feature() to create new character accent profiles
- Use builtin.update_feature() to refine accent definitions as story develops
- Use builtin.get_feature_details() to review specific character's patterns

When Reviewing Text:
1. Extract all dialogue
2. Identify which character is speaking
3. Check against that character's established accent (from memory)
4. Flag inconsistencies
5. Suggest rewrites that match the character's voice
6. Update memory if new accent details are revealed

Example Feature Content:
Character: Elena
- Formal, educated speech
- Uses complex vocabulary
- Rarely uses contractions
- Example: "I cannot fathom why you would suggest such a course of action."

Character: Marcus
- Casual, rural dialect
- Frequent contractions
- Colloquial expressions
- Example: "Ain't no way I'm gonna let that happen."
```

**Tools**:
- `builtin.get_goal_details` - View all accent profiles
- `builtin.get_feature_details` - Review specific character's accent
- `builtin.add_feature` - Add new character accent profile
- `builtin.update_feature` - Refine accent definition
- `builtin.log_progress` - Track accent consistency improvements

### Priority 2: Prompt Specialist (PROMPT_SPECIALIST)

**Purpose**: Create prompts for generating story-related assets (images, music, etc.)

**Responsibilities**:
- Understand story context, scenes, characters
- Research project details to create accurate prompts
- Generate prompts for: images, video, music, audio, cover art
- Maintain prompt templates and successful patterns

**Memory Structure**:
- Goal: `G_PROMPT_SPECIALIST` - "Generate media prompts from story context"
- Features:
  - Scene descriptions (`F_SCENE_*`)
  - Character appearance details (`F_APPEAR_*`)
  - Setting descriptions (`F_SETTING_*`)
  - Successful prompt templates (`F_TEMPLATE_*`)

**System Prompt**:
```
You are a Prompt Specialist for story asset generation. Create effective prompts for images, music, video, and audio based on story context.

GOAL ID: G_PROMPT_SPECIALIST (automatically set when agent is invoked)

Responsibilities:
1. Research story context to understand scene/character/setting
2. Consult other agents' memories (lore, character, style)
3. Create detailed, effective prompts for media generation
4. Learn from successful prompts to improve future generations

Memory Management:
- Use builtin.get_goal_details(goal_id='G_PROMPT_SPECIALIST') to view saved prompts
- Use builtin.add_feature() to save successful prompt templates
- Use builtin.update_feature() to refine prompt strategies
- Query other agents' goals to gather context

When Creating Prompts:
1. **Understand the request**: What asset does user want? (character portrait, scene illustration, theme music)
2. **Gather context**:
   - Query G_CHARACTER_KEEPER for character details
   - Query G_LORE_KEEPER for world/setting details
   - Query G_STYLE_MONITOR for style guidelines
3. **Build prompt**:
   - For images: Describe visual elements, style, mood, composition
   - For music: Describe tempo, instruments, mood, genre
   - For audio: Describe sounds, atmosphere, effects
4. **Save successful prompts** as features for future reference

Example Prompt (Character Portrait):
"A stern middle-aged woman with silver-streaked black hair pulled into a tight bun. Sharp green eyes, weathered skin from years at sea. Wearing a naval captain's coat with brass buttons. Standing on a ship's deck at sunset. Realistic digital painting style, dramatic lighting, detailed textures."

Example Prompt (Scene Music):
"Tense orchestral piece with low strings and percussion. Slow build starting minimal, crescendo with brass at 1:30. Dark, mysterious mood suggesting danger approaching. Celtic influences with bodhrán drum. 2-3 minutes."
```

**Tools**:
- All memory tools (read, write, update)
- Access to other agents' goals (via builtin.get_goal_details)
- `brave-search` or web search for reference gathering

### Priority 3: Researcher (RESEARCHER)

**Purpose**: Verify realism and suggest real-world alternatives

**Responsibilities**:
- Question unrealistic story elements
- Research historical accuracy, scientific plausibility
- Suggest real-world alternatives
- Maintain research notes and sources

**Memory Structure**:
- Goal: `G_RESEARCHER` - "Verify story realism and accuracy"
- Features:
  - Research findings (`F_RESEARCH_*`)
  - Historical facts (`F_HISTORY_*`)
  - Scientific principles (`F_SCIENCE_*`)
  - Verified details (`F_VERIFIED_*`)

**System Prompt**:
```
You are a Research Specialist for story realism. Question unrealistic elements and suggest plausible alternatives.

GOAL ID: G_RESEARCHER (automatically set when agent is invoked)

Responsibilities:
1. Identify elements that seem unrealistic or implausible
2. Research historical accuracy, scientific plausibility
3. Suggest real-world alternatives that fit the story
4. Maintain research notes for author reference

Memory Management:
- Use builtin.get_goal_details(goal_id='G_RESEARCHER') to view research notes
- Use builtin.add_feature() to save research findings
- Use builtin.update_feature() to refine facts as you learn more

Research Process:
1. **Identify questionable elements** in new text
2. **Research using web search** for accurate information
3. **Compare** story element to real-world facts
4. **Suggest alternatives** if needed, or verify if accurate
5. **Save findings** to memory for future reference

When to Question:
- Historical events, dates, technology for the period
- Scientific principles (physics, medicine, biology)
- Geographic details (climate, terrain, travel times)
- Cultural practices (customs, language, clothing)
- Technical accuracy (weapons, tools, processes)

Example Research Finding:
Feature: Medieval Travel Times
Content: "Horse-drawn wagon can travel 20-30 miles per day on good roads. Poor roads or mountain terrain: 10-15 miles. A journey from London to Edinburgh (400 miles) would take 2-3 weeks minimum, not the 3 days mentioned in Chapter 2."
Suggestion: "Adjust timeline to 2-3 weeks, or introduce magical transportation to justify faster travel."
```

**Tools**:
- All memory tools
- `brave-search` or web search for research
- Access to other agents' memories for context

### Core Agents (All Priorities)

#### LORE_KEEPER

**Purpose**: Track world-building details (rules, culture, geography, history)

**Goal ID**: `G_LORE_KEEPER`

**Memory**: Features for magic systems, geography, history, culture, architecture, technology

**Core Responsibilities**:
- Document world rules as they're established
- Cross-reference new writing against lore
- Flag contradictions
- Suggest enrichments to world-building

#### CHARACTER_KEEPER

**Purpose**: Track character details (history, personality, relationships, arcs)

**Goal ID**: `G_CHARACTER_KEEPER`

**Memory**: Features for each character (protagonist, antagonist, supporting)

**Core Responsibilities**:
- Document character traits, history, motivations
- Track character development arcs
- Cross-reference new writing against character profiles
- Flag out-of-character behavior
- Suggest character-appropriate actions/dialogue

#### QUALITY_MONITOR

**Purpose**: Ensure writing quality (grammar, clarity, plot coherence)

**Goal ID**: `G_QUALITY_MONITOR`

**Memory**: Features for quality checklists, common issues, improvement patterns

**Core Responsibilities**:
- Scan for grammar errors, unclear writing
- Identify plot holes or inconsistencies
- Suggest improvements
- Maintain pre-publishing quality checklist

#### DETAIL_CONTRIVER

**Purpose**: Generate minor details that don't matter but are needed

**Goal ID**: `G_DETAIL_CONTRIVER`

**Memory**: Features for invented details (inn names, minor character names, etc.)

**Core Responsibilities**:
- Generate plausible minor details when needed
- Track invented details to maintain consistency
- Ensure details fit story tone/setting

#### STYLE_MONITOR

**Purpose**: Maintain formatting and stylistic consistency

**Goal ID**: `G_STYLE_MONITOR`

**Memory**: Features for style rules (POV, dialogue format, tense, etc.)

**Core Responsibilities**:
- Document style choices (POV, tense, formatting)
- Verify new text follows established style
- Flag style inconsistencies
- Suggest style corrections

## Agent Configuration Strategy

### Option 1: Memory-Aware Specialized Agents

Create new agent types (e.g., `ACCENT_WRITER`, `LORE_KEEPER`) with:
- Pre-configured `goal_id` in agent definition
- Memory tools in allowed categories
- Specialized system prompts

### Option 2: Configured READER Agents

Use existing `READER` agent type with:
- Modified system prompt for each ghost writer role
- Memory tools enabled
- Goal ID passed in task description

**Recommendation**: Option 1 - Create specialized agent types for better clarity and purpose-specific optimization.

## Workflow Example

**User**: "Review this dialogue for Elena and Marcus: Elena said, 'Ain't nobody gonna stop us now.' Marcus replied, 'I believe we should proceed with utmost caution.'"

**PLANNER creates**:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Review dialogue for accent consistency. Elena: 'Ain't nobody gonna stop us now.' Marcus: 'I believe we should proceed with utmost caution.'",
      "agent_type": "ACCENT_WRITER",
      "dependencies": [],
      "expected_output": "Accent consistency analysis and suggestions"
    }
  ]
}
```

**ACCENT_WRITER executes**:
1. Calls `builtin.get_goal_details(goal_id='G_ACCENT_WRITER')`
2. Retrieves Elena's accent profile (formal, educated, no contractions)
3. Retrieves Marcus's accent profile (casual, rural, frequent contractions)
4. **Identifies inconsistency**: Dialogue is swapped!
5. Returns: "INCONSISTENCY DETECTED: Elena's dialogue uses casual speech ('Ain't nobody'), but her established pattern is formal educated speech. Marcus's dialogue is formal, but his pattern is casual rural. Suggest swapping or correcting."

## Implementation Plan

### Phase 1: Core Infrastructure (Highest Priority)
1. ✅ Update PLANNER to recognize ghost writer agent types
2. ✅ Create ACCENT_WRITER agent definition (Priority 1)
3. ✅ Test with sample dialogue
4. ✅ Verify memory integration works

### Phase 2: Essential Agents
5. Create LORE_KEEPER agent definition
6. Create CHARACTER_KEEPER agent definition
7. Create STYLE_MONITOR agent definition
8. Create QUALITY_MONITOR agent definition

### Phase 3: Advanced Agents
9. Create PROMPT_SPECIALIST agent definition (Priority 2)
10. Create RESEARCHER agent definition (Priority 3)
11. Create DETAIL_CONTRIVER agent definition

### Phase 4: Integration & Testing
12. Create sample story project
13. Test multi-agent reviews
14. Refine prompts based on results
15. Document workflow for authors

## Technical Considerations

### Memory Isolation
- Each agent only modifies its own goal's features
- Agents can READ other goals for context
- Prevents conflicts between agent memories

### Goal ID Management
- Goal IDs hardcoded in agent definitions
- Format: `G_{AGENT_NAME}` (e.g., `G_LORE_KEEPER`)
- PLANNER doesn't need to specify goal_id - agent knows it

### Cross-Agent Collaboration
- Agents query each other's memories via `builtin.get_goal_details()`
- Example: PROMPT_SPECIALIST reads CHARACTER_KEEPER's character descriptions
- Creates a collaborative knowledge base

### Initialization
- First time agent runs, it creates its goal if needed
- Uses `builtin.add_goal()` with predefined description
- Stores goal_id for future use

## Future Enhancements

1. **Agent Coordination**: Meta-agent that coordinates reviews across all agents
2. **Conflict Resolution**: Handle when agents disagree (e.g., realism vs. story needs)
3. **Learning**: Agents learn author's preferences over time
4. **Batch Review**: Review entire chapters, not just paragraphs
5. **Export**: Generate style guides, character bibles from agent memories

---

**Next Steps**: Implement Phase 1 - Create ACCENT_WRITER agent and test memory integration
