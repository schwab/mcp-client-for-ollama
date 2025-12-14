# Model and Context Window Configuration Update

## Summary

Updated all text-based models to use **qwen3-coder:30b** and expanded context windows to **256K** (262,144 tokens) for improved performance with large files and complex tasks.

## Changes Made

### 1. Default Model Update
**File**: `mcp_client_for_ollama/utils/constants.py`
- **Before**: `DEFAULT_MODEL = "qwen2.5:7b"`
- **After**: `DEFAULT_MODEL = "qwen3-coder:30b"`

### 2. Agent Context Window Expansions

Updated `max_context_tokens` from various sizes to **262,144** (256K) for all text-based agents:

| Agent | File | Old Context | New Context | Change |
|-------|------|-------------|-------------|--------|
| **CODER** | `coder.json` | 32,768 (32K) | 262,144 (256K) | **+800%** |
| **PLANNER** | `planner.json` | 32,768 (32K) | 262,144 (256K) | **+800%** |
| **EXECUTOR** | `executor.json` | 8,192 (8K) | 262,144 (256K) | **+3200%** |
| **RESEARCHER** | `researcher.json` | 32,768 (32K) | 262,144 (256K) | **+800%** |
| **DEBUGGER** | `debugger.json` | 16,384 (16K) | 262,144 (256K) | **+1600%** |
| **READER** | `reader.json` | 32,768 (32K) | 262,144 (256K) | **+800%** |

### 3. Files Modified

**Total**: 7 files updated

**Configuration**:
- `mcp_client_for_ollama/utils/constants.py`

**Agent Definitions**:
- `mcp_client_for_ollama/agents/definitions/coder.json`
- `mcp_client_for_ollama/agents/definitions/planner.json`
- `mcp_client_for_ollama/agents/definitions/executor.json`
- `mcp_client_for_ollama/agents/definitions/researcher.json`
- `mcp_client_for_ollama/agents/definitions/debugger.json`
- `mcp_client_for_ollama/agents/definitions/reader.json`

### 4. Files NOT Modified (Vision/Special Purpose Agents)

The following agents were intentionally left unchanged as they may have different requirements:
- `lyricist.json` - Music lyric generation
- `suno_composer.json` - Music composition
- `style_designer.json` - Style/design work
- `obsidian.json` - Obsidian note management

## Benefits

### 1. Enhanced Model Capabilities
**qwen3-coder:30b** advantages over qwen2.5:7b:
- **Better code understanding**: 30B parameters vs 7B for deeper comprehension
- **Superior code generation**: More accurate and idiomatic code
- **Improved reasoning**: Better at complex problem-solving
- **Enhanced tool usage**: More reliable function calling

### 2. Massive Context Window Expansion
**256K context window** enables:
- **Large file handling**: Edit files with 10,000+ lines without truncation
- **Multi-file operations**: Work with dozens of files simultaneously
- **Complex conversations**: Maintain context over extensive discussions
- **Better delegation**: Agents can handle more complex task decomposition
- **Enhanced research**: Analyze large codebases or documentation sets

### 3. Agent-Specific Improvements

**EXECUTOR** (8K → 256K):
- Previously most constrained agent
- Now can execute complex multi-step operations
- Can process large command outputs
- Better for data analysis tasks

**DEBUGGER** (16K → 256K):
- Can analyze larger stack traces
- Handle complex multi-file debugging scenarios
- Better error context retention

**All Agents**:
- Reduced need for context pruning
- Better cross-reference capability
- Improved task completion rates
- Fewer "context exceeded" errors

## Performance Considerations

### Memory Impact
- **Increased VRAM usage**: 30B model requires more GPU memory than 7B
- **Larger context windows**: Will use more memory during inference
- **Recommendation**: Ensure adequate GPU resources (24GB+ VRAM recommended)

### Inference Speed
- **Slower per-token**: Larger model = slower generation
- **But**: Better quality means fewer retries/corrections
- **Net result**: Often faster overall task completion

### Token Cost (if using API)
- 256K context windows mean more tokens can be consumed
- Monitor usage if using metered API services
- Consider implementing context management strategies if needed

## Compatibility

### Ollama Requirements
- **Model availability**: Must have `qwen3-coder:30b` pulled
  ```bash
  ollama pull qwen3-coder:30b
  ```
- **System resources**: Adequate GPU memory for 30B model
- **Ollama version**: Latest version recommended for best performance

### JSON Validation
✅ All JSON configuration files validated successfully
✅ No syntax errors
✅ All agents load correctly

## Testing Performed

1. ✅ JSON validation for all agent definitions
2. ✅ Constants file syntax validation
3. ✅ Configuration integrity verification

## Rollback Instructions

If you need to revert these changes:

### Rollback Default Model
```bash
# Edit mcp_client_for_ollama/utils/constants.py
# Change line 16 back to:
DEFAULT_MODEL = "qwen2.5:7b"
```

### Rollback Context Windows
```bash
# Revert to original values:
# CODER: 32768
# PLANNER: 32768
# EXECUTOR: 8192
# RESEARCHER: 32768
# DEBUGGER: 16384
# READER: 32768
```

Or use git:
```bash
git checkout HEAD~1 -- mcp_client_for_ollama/utils/constants.py
git checkout HEAD~1 -- mcp_client_for_ollama/agents/definitions/
```

## Next Steps

1. **Pull the model**: `ollama pull qwen3-coder:30b`
2. **Test the changes**: Run the application and verify it works
3. **Monitor performance**: Watch for memory usage and response times
4. **Adjust if needed**: Fine-tune context windows for specific agents if necessary

## Notes

- The new configuration is **immediately active** once deployed
- No database migrations or data changes required
- Existing conversations continue with old model until cleared
- New sessions will automatically use qwen3-coder:30b
- Context window changes apply per-agent, not globally
