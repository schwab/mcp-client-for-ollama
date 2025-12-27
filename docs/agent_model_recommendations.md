# Agent Model Recommendations

## Current State
- **PLANNER**: qwen2.5-coder:14b (explicitly configured)
- **All Other Agents**: Use global default model

## Analysis by Agent Category

### 1. Planning & Reasoning Agents

**Requirements**: Strong reasoning, structured JSON output, complex decision-making

**PLANNER** (Currently: qwen2.5-coder:14b ✅)
- **Recommendation**: **Keep qwen2.5-coder:14b** or upgrade to qwen2.5-coder:32b
- **Rationale**:
  - Needs strong reasoning to decompose complex queries
  - Must follow detailed guidelines (212+ lines of system prompt)
  - Produces structured JSON output
  - 14b is good balance of speed/capability
  - 32b would provide better guideline adherence (for persistent issues)
- **Alternative**: qwen2.5:32b (if pure reasoning more important than code context)

**INITIALIZER** (Currently: global)
- **Recommendation**: **qwen2.5-coder:14b** (same as PLANNER)
- **Rationale**:
  - Similar task to PLANNER (structured goal/feature creation)
  - Needs JSON output
  - Bootstraps memory from user queries
  - Same model as PLANNER for consistency

---

### 2. Code-Focused Agents

**Requirements**: Code understanding, precise modifications, low hallucination

**CODER** (Currently: global, temp 0.5)
- **Recommendation**: **qwen2.5-coder:32b** or **deepseek-coder-v2:16b**
- **Rationale**:
  - Needs BEST code generation capabilities
  - Makes actual code modifications
  - Larger model = fewer bugs introduced
  - This is where quality matters most
- **Budget Alternative**: qwen2.5-coder:14b (still very capable)

**DEBUGGER** (Currently: global, temp 0.5)
- **Recommendation**: **qwen2.5-coder:32b** or **deepseek-coder-v2:16b**
- **Rationale**:
  - Needs strong code analysis
  - Must identify subtle bugs
  - Same tier as CODER for quality
- **Budget Alternative**: qwen2.5-coder:14b

**READER** (Currently: global, temp 0.3)
- **Recommendation**: **qwen2.5-coder:14b**
- **Rationale**:
  - Read-only, no modifications
  - Doesn't need largest model
  - 14b sufficient for code analysis
  - Lower temp (0.3) means less variety needed

---

### 3. Execution Agents (Speed & Reliability Critical)

**Requirements**: Fast, reliable, low hallucination, simple operations

**FILE_EXECUTOR** (Currently: global, temp 0.3)
- **Recommendation**: **qwen2.5:7b** (fastest)
- **Rationale**:
  - Simple operations (read, list, validate paths)
  - Speed matters (users wait for file operations)
  - Low temp + simple task = 7b is sufficient
  - Path validation is mechanical, doesn't need large model
- **Alternative**: qwen2.5:14b if global is already 14b

**TEST_EXECUTOR** (Currently: global, temp 0.3)
- **Recommendation**: **qwen2.5:7b** (fastest)
- **Rationale**:
  - Just runs pytest and reports results
  - No code modification
  - Speed critical for test feedback loop
  - Simple task, 7b sufficient

**CONFIG_EXECUTOR** (Currently: global, temp 0.3)
- **Recommendation**: **qwen2.5:7b**
- **Rationale**:
  - Simple config get/set operations
  - Low temperature
  - Speed matters for config queries

**MEMORY_EXECUTOR** (Currently: global, temp 0.3)
- **Recommendation**: **qwen2.5:14b**
- **Rationale**:
  - Needs some reasoning for validation
  - "Never mark complete if tests failed" requires logic
  - Conditional task execution
  - 14b for better validation logic
- **Budget Alternative**: qwen2.5:7b if speed critical

**SHELL_EXECUTOR** (Currently: global, temp 0.4)
- **Recommendation**: **qwen2.5:14b**
- **Rationale**:
  - Handles diverse tasks (bash, Python, MCP tools)
  - More complex than simple executors
  - Needs reasoning for MCP tool usage
  - 14b for flexibility

**EXECUTOR** (Deprecated, Currently: global, temp 0.4)
- **Recommendation**: **qwen2.5:14b** (but prefer specialized executors)
- **Rationale**: General purpose, keep as fallback

---

### 4. Synthesis & Analysis Agents

**Requirements**: Coherence, clarity, information integration

**AGGREGATOR** (Currently: global, temp 0.2)
- **Recommendation**: **qwen2.5:14b** or **qwen2.5:32b**
- **Rationale**:
  - Synthesizes multiple agent outputs
  - Needs coherence and clarity
  - Final user-facing output
  - Very low temp (0.2) = consistency
  - 32b would provide best synthesis quality
- **Optimal**: qwen2.5:32b for best user experience

**RESEARCHER** (Currently: global, temp 0.6)
- **Recommendation**: **qwen2.5:14b** or **qwen2.5:32b**
- **Rationale**:
  - Analyzes code patterns
  - Synthesizes information
  - Medium temp allows some variety
  - 32b for deeper analysis

---

### 5. Creative Agents

**Requirements**: Creativity, variety, natural language fluency

**LYRICIST** (Currently: global, temp 0.8)
- **Recommendation**: **llama3.1:8b** or **mistral:7b-instruct**
- **Rationale**:
  - Creative writing task
  - High temperature (0.8) needs variety
  - Llama/Mistral better at creative prose than Qwen
  - Not a code task, don't need coder model
- **Alternative**: qwen2.5:14b (less creative but more structured)

**STYLE_DESIGNER** (Currently: global, temp 0.7)
- **Recommendation**: **llama3.1:8b** or **mistral:7b-instruct**
- **Rationale**:
  - Creative style descriptions
  - High temperature
  - Benefits from Llama's language skills

**SUNO_COMPOSER** (Currently: global, temp 0.6)
- **Recommendation**: **qwen2.5:14b**
- **Rationale**:
  - Combines structured elements (lyrics + style + metatags)
  - Medium temp
  - More structured than pure creative
  - Qwen good for structured combination

---

### 6. Writing Agents

**OBSIDIAN** (Currently: global, temp 0.5)
- **Recommendation**: **qwen2.5:14b**
- **Rationale**:
  - Markdown writing
  - Structured format
  - Medium temp for some variety
  - Qwen handles markdown well

---

## Recommended Configuration by Priority

### Priority 1: Core Quality (Most Important)
```json
{
  "PLANNER": "qwen2.5-coder:32b",        // Better guideline adherence
  "CODER": "qwen2.5-coder:32b",          // Best code quality
  "DEBUGGER": "qwen2.5-coder:32b",       // Best bug detection
  "AGGREGATOR": "qwen2.5:32b"            // Best final output
}
```

### Priority 2: Speed (Fast Execution)
```json
{
  "FILE_EXECUTOR": "qwen2.5:7b",         // Fastest file ops
  "TEST_EXECUTOR": "qwen2.5:7b",         // Fastest test execution
  "CONFIG_EXECUTOR": "qwen2.5:7b"        // Fastest config queries
}
```

### Priority 3: Balanced (Good Performance)
```json
{
  "INITIALIZER": "qwen2.5-coder:14b",    // Match PLANNER
  "MEMORY_EXECUTOR": "qwen2.5:14b",      // Validation logic
  "SHELL_EXECUTOR": "qwen2.5:14b",       // Diverse tasks
  "RESEARCHER": "qwen2.5:14b",           // Analysis
  "READER": "qwen2.5-coder:14b",         // Code reading
  "OBSIDIAN": "qwen2.5:14b",             // Markdown writing
  "SUNO_COMPOSER": "qwen2.5:14b"         // Structured combination
}
```

### Priority 4: Creative (Natural Language)
```json
{
  "LYRICIST": "llama3.1:8b",             // Creative writing
  "STYLE_DESIGNER": "llama3.1:8b"        // Creative descriptions
}
```

---

## Budget-Conscious Configuration

If you want to minimize resource usage while maintaining quality:

```json
{
  "PLANNER": "qwen2.5-coder:14b",        // Keep current
  "CODER": "qwen2.5-coder:14b",          // Still good quality
  "DEBUGGER": "qwen2.5-coder:14b",       // Still capable
  "AGGREGATOR": "qwen2.5:14b",           // Good synthesis
  "FILE_EXECUTOR": "qwen2.5:7b",         // Speed matters
  "TEST_EXECUTOR": "qwen2.5:7b",         // Speed matters
  "CONFIG_EXECUTOR": "qwen2.5:7b",       // Speed matters
  "MEMORY_EXECUTOR": "qwen2.5:7b",       // Budget option
  "SHELL_EXECUTOR": "qwen2.5:14b",       // Needs reasoning
  "RESEARCHER": "qwen2.5:14b",           // Needs analysis
  "LYRICIST": "qwen2.5:14b",             // Budget creative
  "STYLE_DESIGNER": "qwen2.5:14b",       // Budget creative
  "Global Default": "qwen2.5:14b"        // Catch-all
}
```

---

## Performance vs. Cost Trade-offs

### Model Size Impact
- **7b models**: ~4GB RAM, ~2-3 tok/sec, excellent for simple tasks
- **14b models**: ~8GB RAM, ~1-2 tok/sec, good balance
- **32b models**: ~18GB RAM, ~0.5-1 tok/sec, best quality

### When to Use Larger Models
1. **PLANNER** - Complex reasoning, guideline adherence issues
2. **CODER** - Code quality critical, bugs are expensive
3. **AGGREGATOR** - User-facing output quality matters
4. **DEBUGGER** - Bug detection worth the cost

### When Smaller Models Are Fine
1. **Executors** - Mechanical tasks, speed matters
2. **Test Execution** - Simple run and report
3. **File Operations** - Path validation is straightforward
4. **Config Management** - Simple get/set operations

---

## Implementation Strategy

### Phase 1: Critical Quality Improvements
1. Upgrade CODER to qwen2.5-coder:32b (biggest quality impact)
2. Upgrade AGGREGATOR to qwen2.5:32b (user-facing quality)
3. Keep PLANNER at qwen2.5-coder:14b (unless guideline issues persist)

### Phase 2: Speed Optimizations
1. Set FILE_EXECUTOR to qwen2.5:7b
2. Set TEST_EXECUTOR to qwen2.5:7b
3. Set CONFIG_EXECUTOR to qwen2.5:7b

### Phase 3: Specialized Assignments
1. Set MEMORY_EXECUTOR to qwen2.5:14b (validation logic)
2. Set SHELL_EXECUTOR to qwen2.5:14b (diverse tasks)
3. Set LYRICIST/STYLE_DESIGNER to llama3.1:8b (creative)

---

## Notes

1. **Model Availability**: Ensure models are pulled before configuring
   ```bash
   ollama pull qwen2.5:7b
   ollama pull qwen2.5:14b
   ollama pull qwen2.5:32b
   ollama pull qwen2.5-coder:14b
   ollama pull qwen2.5-coder:32b
   ollama pull llama3.1:8b
   ```

2. **Temperature Settings**: Current temperatures are well-tuned, keep them!
   - Executors: 0.3-0.4 (consistency)
   - Analysis: 0.5-0.6 (balanced)
   - Creative: 0.7-0.8 (variety)

3. **Testing**: After changing models, test:
   - PLANNER still includes file paths in all tasks
   - CODER produces clean, correct code
   - FILE_EXECUTOR is noticeably faster
   - AGGREGATOR produces clear, coherent summaries

4. **VRAM Considerations**: Running multiple 32b models may require significant RAM
   - Consider 1-2 large models (CODER, AGGREGATOR)
   - Keep most agents at 7b-14b
   - Let model pool handle swapping

5. **Future**: As better models emerge (Llama 4, Qwen 3, etc.), re-evaluate
