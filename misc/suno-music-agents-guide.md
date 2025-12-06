# Suno Music Generation Agents

**Created**: 2025-12-06
**Purpose**: Specialized agents for creating AI-generated music using Suno AI

## Overview

Three new specialized agents have been added to the delegation system to support AI music generation with Suno. These agents work together to transform song ideas and lyrics into properly formatted, Suno-ready files that can be used to generate professional-quality music.

## The Three Agents

### 1. LYRICIST - Song Lyricist

**Agent Type**: `LYRICIST`
**Display Name**: Song Lyricist
**File**: `mcp_client_for_ollama/agents/definitions/lyricist.json`

#### Purpose
Writes original song lyrics with proper structure, rhyme schemes, and emotional depth.

#### Capabilities
- Write original song lyrics in various genres (pop, hip-hop, rock, country, R&B, indie)
- Structure songs with verses, choruses, bridges, pre-choruses, and outros
- Create genre-appropriate rhyme schemes (AABB, ABAB, ABCB, etc.)
- Match lyrics to specified moods and themes
- Write ad-libs and vocal embellishments in parentheses: `(oh yeah)`, `(hey!)`, `(uh huh)`
- Adapt lyrics for different vocal styles

#### Configuration
- **Temperature**: 0.8 (high creativity)
- **Loop Limit**: 2
- **Max Context**: 32,768 tokens
- **Tools**: Read-only filesystem access
- **Forbidden**: Cannot write files, execute commands

#### Output Format
```
[Intro]
Optional intro lyrics...

[Verse 1]
First verse lyrics here
With proper line breaks

[Chorus]
Catchy, memorable hook
Repeat key phrases (oh yeah)

[Verse 2]
Continue the story
Maintain rhyme scheme

[Bridge]
Contrasting section
Emotional shift

[Chorus]
Final chorus with ad-libs (hey!)

[Outro]
Closing lines...
```

#### Genre-Specific Guidelines
- **Pop**: Catchy hooks, simple language, relatable themes
- **Hip-hop/Rap**: Complex wordplay, internal rhymes, rhythm-focused
- **Rock**: Powerful imagery, emotional intensity, storytelling
- **Country**: Narrative-driven, conversational tone, specific details
- **R&B/Soul**: Emotional vulnerability, smooth flow, romantic themes
- **Indie**: Unique perspectives, poetic imagery, authenticity

---

### 2. STYLE_DESIGNER - Music Style Designer

**Agent Type**: `STYLE_DESIGNER`
**Display Name**: Music Style Designer
**File**: `mcp_client_for_ollama/agents/definitions/style_designer.json`

#### Purpose
Creates style prompts, genre descriptions, and metatags for Suno AI music generation within the 120-character limit.

#### Capabilities
- Craft precise 120-character style prompts for Suno AI
- Select appropriate genres and subgenres
- Specify instrumentation and production techniques
- Define mood, tempo, and energy levels
- Mix genres creatively for unique sounds
- Design metatag structures for song sections

#### Configuration
- **Temperature**: 0.7 (balanced creativity and precision)
- **Loop Limit**: 2
- **Max Context**: 32,768 tokens
- **Tools**: Read-only filesystem access
- **Forbidden**: Cannot write files, execute commands

#### Style Prompt Structure
```
[Genre] [Mood] [Instrumentation] [Tempo/BPM] [Production style]
```

#### Examples
```
Upbeat indie pop, clean electric guitar, steady kick, warm bass, catchy synth, positive, 120 BPM

Dark synthwave, melancholic, pulsing 808 bass, atmospheric pads, robotic male vocals, 85 BPM

Gospel soul, joyful, organ, tambourine, choir harmonies, uplifting, hand claps, 95 BPM
```

#### Suno AI Best Practices
1. **Be Specific**: Include genre, mood, instrumentation, and tempo
2. **Use Descriptions, Not Commands**: "Upbeat pop track" not "Create upbeat pop"
3. **Limit Instruments**: 2-3 instruments max to avoid dilution
4. **Avoid Conflicts**: Don't combine "slow" with "high energy"
5. **No Artist Names**: Describe style instead of referencing artists
6. **Front-Load**: Place most important elements in first 20-30 characters

#### Recommended Metatags

**Structure Tags**:
- `[Intro]` `[Verse]` `[Pre-Chorus]` `[Chorus]` `[Bridge]` `[Outro]`

**Mood/Energy Tags**:
- `[Mood: Uplifting]` `[Energy: High]` `[Energy: Low]`

**Instrument Tags**:
- `[Instrument: Warm Rhodes]` `[Instrument: Strings (Legato)]`

**Vocal Style Tags**:
- `[Vocal Style: Whisper]` `[Vocal Effect: Reverb]` `[Vocal Effect: Autotune]`

**Production Tags**:
- `[Fade Out]` `[End]` `[Build Up]` `[Drop]` `[Break Down]`
- `[Add tension → remove drums → expose vocals]`

#### Output Format
```
Style Prompt: [120-character description]
Recommended Metatags: [List of relevant metatags]
Production Notes: [Any additional guidance]
```

---

### 3. SUNO_COMPOSER - Suno Music Composer

**Agent Type**: `SUNO_COMPOSER`
**Display Name**: Suno Music Composer
**File**: `mcp_client_for_ollama/agents/definitions/suno_composer.json`

#### Purpose
Combines lyrics, style prompts, and metatags into complete Suno AI-ready music files with proper formatting.

#### Capabilities
- Read and analyze lyrics from previous tasks or files
- Integrate style prompts and genre descriptions
- Format songs with proper metatag structure
- Create complete Suno-ready text files
- Optimize song structure for AI music generation
- Add production notes and formatting instructions
- Create multiple variations (acoustic, remix, etc.)

#### Configuration
- **Temperature**: 0.6 (precise formatting)
- **Loop Limit**: 3
- **Max Context**: 32,768 tokens
- **Tools**: Read and write filesystem access
- **Forbidden**: Cannot execute commands or delete files

#### Complete Suno File Format
```
[Style Prompt: Upbeat indie pop, clean guitar, steady kick, warm bass, catchy synth, 120 BPM]

[Intro]
Optional intro lyrics or instrumental cue

[Verse 1]
Lyrics here with natural line breaks
Keep syllable flow consistent

[Chorus]
Catchy, memorable hook
Repeat key phrases (oh yeah)

[Verse 2]
Continue the story
Maintain rhyme scheme

[Chorus]
Repeat chorus exactly or with variation

[Bridge]
Contrasting section
Emotional shift or perspective change

[Chorus]
Final chorus with ad-libs (hey!)

[Outro]
Closing lines or [Fade Out]
```

#### Advanced Formatting Techniques

**Ad-libs**: Use parentheses
```
(oh yeah), (hey!), (uh huh), (come on)
```

**Emphasis**: Use ALL CAPS for different vocal tone
```
I NEED you now (need you)
```

**Sound Effects**: Use asterisks
```
*record scratch*, *crowd cheers*, *guitar feedback*
```

**Extended Syllables**: Use hyphenation
```
yeaaah, nooo, whooooa
```

#### File Naming Convention
```
[song-title]_[genre]_suno.txt
```

Examples:
- `summer_love_pop_suno.txt`
- `midnight_drive_synthwave_suno.txt`
- `rise_up_gospel_suno.txt`

---

## Workflow Examples

### Example 1: Simple Song Creation

**User Request**: "Create a happy pop song about summer"

**Delegation Plan**:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Write upbeat pop lyrics about summer fun and sunshine",
      "agent_type": "LYRICIST",
      "dependencies": [],
      "expected_output": "Complete song lyrics with verse-chorus structure"
    },
    {
      "id": "task_2",
      "description": "Create upbeat pop style prompt with bright instrumentation, 120 BPM",
      "agent_type": "STYLE_DESIGNER",
      "dependencies": [],
      "expected_output": "120-character style prompt and recommended metatags"
    },
    {
      "id": "task_3",
      "description": "Combine lyrics and style into complete Suno file named summer_vibes_pop_suno.txt",
      "agent_type": "SUNO_COMPOSER",
      "dependencies": ["task_1", "task_2"],
      "expected_output": "Complete Suno-ready text file"
    }
  ]
}
```

### Example 2: Genre-Mixing Song

**User Request**: "Create a dark synthwave meets hip-hop track about cyberpunk themes"

**Delegation Plan**:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Write cyberpunk-themed lyrics mixing rap verses with synthwave choruses",
      "agent_type": "LYRICIST",
      "dependencies": [],
      "expected_output": "Lyrics with hip-hop verses and melodic choruses"
    },
    {
      "id": "task_2",
      "description": "Design dark synthwave hip-hop fusion style with 808s, synth pads, 85 BPM",
      "agent_type": "STYLE_DESIGNER",
      "dependencies": [],
      "expected_output": "Genre-mixing style prompt with production metatags"
    },
    {
      "id": "task_3",
      "description": "Create Suno file with advanced metatags for genre transitions",
      "agent_type": "SUNO_COMPOSER",
      "dependencies": ["task_1", "task_2"],
      "expected_output": "Formatted file: neon_nights_synthwave_hip_hop_suno.txt"
    }
  ]
}
```

### Example 3: Multiple Variations

**User Request**: "Create a love ballad with both acoustic and full band versions"

**Delegation Plan**:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Write emotional love ballad lyrics with intimate verses and powerful chorus",
      "agent_type": "LYRICIST",
      "dependencies": [],
      "expected_output": "Complete ballad lyrics"
    },
    {
      "id": "task_2",
      "description": "Create acoustic ballad style prompt: acoustic guitar, soft vocals, intimate, 70 BPM",
      "agent_type": "STYLE_DESIGNER",
      "dependencies": [],
      "expected_output": "Acoustic version style prompt"
    },
    {
      "id": "task_3",
      "description": "Create full band ballad style prompt: piano, strings, drums, powerful vocals, 75 BPM",
      "agent_type": "STYLE_DESIGNER",
      "dependencies": [],
      "expected_output": "Full band version style prompt"
    },
    {
      "id": "task_4",
      "description": "Combine lyrics with acoustic style for first version",
      "agent_type": "SUNO_COMPOSER",
      "dependencies": ["task_1", "task_2"],
      "expected_output": "eternal_love_acoustic_suno.txt"
    },
    {
      "id": "task_5",
      "description": "Combine same lyrics with full band style for second version",
      "agent_type": "SUNO_COMPOSER",
      "dependencies": ["task_1", "task_3"],
      "expected_output": "eternal_love_full_band_suno.txt"
    }
  ]
}
```

### Example 4: Lyrics Refinement Workflow

**User Request**: "I have lyrics in a file, create a Suno version with proper formatting and style"

**Delegation Plan**:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Read existing lyrics from my_lyrics.txt and analyze genre/mood",
      "agent_type": "READER",
      "dependencies": [],
      "expected_output": "Lyrics content and genre analysis"
    },
    {
      "id": "task_2",
      "description": "Based on analysis, create appropriate style prompt and metatags",
      "agent_type": "STYLE_DESIGNER",
      "dependencies": ["task_1"],
      "expected_output": "Matching style prompt"
    },
    {
      "id": "task_3",
      "description": "Format existing lyrics with proper metatags and style prompt",
      "agent_type": "SUNO_COMPOSER",
      "dependencies": ["task_1", "task_2"],
      "expected_output": "Properly formatted Suno file"
    }
  ]
}
```

---

## Best Practices

### For LYRICIST Tasks
- Specify the genre, mood, and theme clearly
- Mention any specific song structure preferences
- Indicate desired rhyme scheme if important
- Request specific emotional tone or perspective
- Example: "Write upbeat pop lyrics about overcoming obstacles, verse-chorus-verse-chorus-bridge-chorus structure, ABAB rhyme scheme"

### For STYLE_DESIGNER Tasks
- Provide genre and mood preferences
- Mention any specific instruments or sounds desired
- Indicate tempo range (slow, medium, fast, or specific BPM)
- Specify energy level (low, medium, high)
- Example: "Create dark electronic style prompt with heavy bass, atmospheric pads, 90 BPM, moody and intense"

### For SUNO_COMPOSER Tasks
- Ensure lyrics are available (from LYRICIST or existing file)
- Ensure style prompt is available (from STYLE_DESIGNER)
- Specify desired filename
- Request variations if needed
- Mention any special formatting requirements
- Example: "Combine lyrics and style into complete file with fade out ending, save as track_name_genre_suno.txt"

---

## Integration with Existing Agents

### Common Multi-Agent Workflows

**EXECUTOR → LYRICIST → STYLE_DESIGNER → SUNO_COMPOSER**
- EXECUTOR can run tasks in parallel (LYRICIST and STYLE_DESIGNER simultaneously)
- SUNO_COMPOSER waits for both dependencies

**READER → STYLE_DESIGNER → SUNO_COMPOSER**
- When working with existing lyrics files
- READER analyzes content, STYLE_DESIGNER creates matching style

**RESEARCHER → LYRICIST → STYLE_DESIGNER → SUNO_COMPOSER**
- RESEARCHER analyzes multiple song examples or references
- LYRICIST writes based on research insights
- Complete workflow for complex requests

---

## Suno AI Reference Information

### Key Constraints
- **Style Prompt Limit**: 120 characters maximum
- **No Artist References**: Cannot use specific artist names (describe style instead)
- **Metatag Placement**: Most effective in first 20-30 words
- **Instrument Limit**: 2-3 instruments recommended for best results

### Common Genres Supported
Pop, Rock, Hip-Hop, R&B, Soul, Country, Electronic, EDM, House, Techno, Trance, Dubstep, Trap, Drum & Bass, Indie, Alternative, Folk, Acoustic, Jazz, Blues, Reggae, Latin, Gospel, Classical, Ambient, Lo-fi, Vaporwave, Synthwave, Chillwave, Metal, Punk, Grunge, Emo, Ska

### Common Moods/Emotions
Happy, Sad, Energetic, Calm, Aggressive, Romantic, Melancholic, Uplifting, Dark, Bright, Intense, Relaxed, Nostalgic, Euphoric, Anxious, Peaceful, Triumphant, Mysterious, Playful, Dramatic

### Common Tempos
- **Slow**: 60-80 BPM (ballads, slow jams)
- **Medium**: 80-120 BPM (pop, rock, hip-hop)
- **Fast**: 120-180 BPM (dance, electronic, punk)
- **Very Fast**: 180+ BPM (drum & bass, speed metal)

---

## Troubleshooting

### Issue: Lyrics don't match the style
**Solution**: Ensure LYRICIST and STYLE_DESIGNER receive consistent genre/mood information in their task descriptions.

### Issue: Style prompt exceeds 120 characters
**Solution**: STYLE_DESIGNER is trained to stay within limit. If over, ask it to condense while keeping key elements.

### Issue: Song structure feels wrong
**Solution**: Provide specific structure in LYRICIST task description (e.g., "verse-chorus-verse-chorus-bridge-chorus-chorus").

### Issue: Metatags not working as expected
**Solution**: Ensure metatags are placed at section boundaries and are concise (1-3 words). Use recommended metatags from STYLE_DESIGNER output.

### Issue: Need multiple versions
**Solution**: Use SUNO_COMPOSER multiple times with different style prompts but same lyrics, or create variations in the task description.

---

## Research Sources

This implementation is based on 2025 Suno AI best practices from:

- [Mastering Suno Prompts: The Ultimate 2025 Guide](https://skywork.ai/skypage/en/Mastering-Suno-Prompts:-The-Ultimate-2025-Guide-to-AI-Music-Creation/1975069867135528960)
- [Suno AI Meta Tags & Song Structure Guide](https://jackrighteous.com/en-us/pages/suno-ai-meta-tags-guide)
- [Guide to Suno AI Prompting: Metatags Explained](https://www.titanxt.io/post/guide-to-suno-ai-prompting-metatags-explained)
- [Suno AI Wiki - List of Metatags](https://sunoaiwiki.com/resources/2024-05-13-list-of-metatags/)
- [Suno Prompts Guide](https://www.litmedia.ai/resource-music-tips/suno-prompts/)
- [AI Music Prompts Guide 2025](https://musicsmith.ai/blog/ai-music-generation-prompts-best-practices)

---

## Future Enhancements

Potential additions to consider:

1. **MUSIC_REVIEWER**: Agent to analyze generated Suno outputs and suggest improvements
2. **REMIX_DESIGNER**: Agent specialized in creating remix variations of existing songs
3. **PLAYLIST_CURATOR**: Agent to organize multiple songs into thematic playlists
4. **LYRICS_TRANSLATOR**: Agent to adapt lyrics to different languages while maintaining rhythm
5. **GENRE_ANALYZER**: Agent to analyze reference tracks and extract style characteristics

---

## Quick Reference

### Agent Selection Guide

| Task | Use Agent | Temperature |
|------|-----------|-------------|
| Write original song lyrics | LYRICIST | 0.8 |
| Create style prompt/metatags | STYLE_DESIGNER | 0.7 |
| Format complete Suno file | SUNO_COMPOSER | 0.6 |
| Analyze existing lyrics | READER | 0.3 |
| Research song themes/styles | RESEARCHER | 0.6 |

### File Locations
- **Agent Definitions**: `mcp_client_for_ollama/agents/definitions/`
  - `lyricist.json`
  - `style_designer.json`
  - `suno_composer.json`

### Example Task Description Templates

**LYRICIST**:
```
"Write [mood] [genre] lyrics about [theme], [structure], [rhyme scheme]"
```

**STYLE_DESIGNER**:
```
"Create [genre] style prompt with [instruments], [mood], [tempo] BPM"
```

**SUNO_COMPOSER**:
```
"Combine lyrics and style into Suno file: [filename]_suno.txt with [special formatting]"
```

---

**Last Updated**: 2025-12-06
**Version**: 1.0
**Status**: Production Ready
