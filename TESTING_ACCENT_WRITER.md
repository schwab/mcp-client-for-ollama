# Testing ACCENT_WRITER Agent

## Manual Test Instructions

### Prerequisites
1. Ensure v0.29.0 is installed: `pip show mcp-client-for-ollama | grep Version`
2. Start the MCP client with delegation enabled

### Test Scenario 1: Consistent Dialogue

**Start the client**:
```bash
ollmcp
```

**Enable delegation and memory**:
```
/delegation on
/memory on
```

**Test query**:
```
Review this dialogue for accent consistency:

Lady Ashford looked down her nose at the young man. "I am afraid I cannot permit such behavior in my establishment."

Jake shrugged. "Yeah, whatever. I'm outta here anyway."

"Indeed," Lady Ashford replied coolly. "That would be most prudent."
```

**Expected behavior**:
- PLANNER should recognize this as a dialogue review task
- PLANNER should assign to ACCENT_WRITER
- ACCENT_WRITER should:
  1. Initialize goal G_ACCENT_WRITER (first run)
  2. Create accent profiles for Lady Ashford (formal) and Jake (casual)
  3. Mark dialogue as CONSISTENT
  4. Store profiles in memory

### Test Scenario 2: Inconsistent Dialogue (Characters Swapped)

**Test query**:
```
Review this dialogue for accent consistency:

Jake straightened his collar and spoke carefully. "I believe we should proceed with the utmost caution in this matter."

Lady Ashford laughed. "Dude, you're totally overthinkin' this. Let's just do it!"
```

**Expected behavior**:
- ACCENT_WRITER should:
  1. Retrieve existing profiles for Lady Ashford and Jake
  2. Compare dialogue to established patterns
  3. Flag INCONSISTENCIES:
     - Jake speaking formally (should be casual)
     - Lady Ashford speaking casually (should be formal)
  4. Suggest corrections

### Test Scenario 3: Mixed Dialogue

**Test query**:
```
Review this dialogue for accent consistency:

Lady Ashford considered the proposal. "That is rather an interesting suggestion."

Jake grinned. "Yeah? I thought you'd like it."

Lady Ashford frowned. "But like, isn't it kinda risky though?"

Jake replied formally, "One must consider all potential ramifications before proceeding."
```

**Expected behavior**:
- ACCENT_WRITER should:
  1. Mark first two dialogue instances as CONSISTENT
  2. Flag third dialogue (Lady Ashford using "like" and "kinda") as INCONSISTENT
  3. Flag fourth dialogue (Jake using formal language) as INCONSISTENT
  4. Provide suggestions for each

### Test Scenario 4: Verify Memory Persistence

**Test query**:
```
Show me what you know about Lady Ashford's speech pattern
```

**Expected behavior**:
- Should be able to query the memory and retrieve accent profile
- Profile should include: formal, educated, no contractions, example phrases

### Verification Checklist

After running tests, verify:

- [ ] Goal G_ACCENT_WRITER was created in memory
- [ ] Features were created for each character (F_ACC_LADY_ASHFORD, F_ACC_JAKE)
- [ ] Agent correctly identified consistent dialogue
- [ ] Agent correctly flagged inconsistent dialogue
- [ ] Agent provided helpful suggestions
- [ ] Memory persists across queries (profiles remembered)
- [ ] Agent updates profiles as it learns more

## Automated Test (Alternative)

If you prefer automated testing, you can use the ollmcp directly:

```bash
# Test 1: Consistent dialogue
echo "Review this dialogue: Lady Ashford said 'I am afraid I must decline.' Jake said 'Yeah dude, whatever.'" | ollmcp --delegation --memory

# Test 2: Inconsistent dialogue
echo "Review this dialogue: Jake said 'I believe we should proceed cautiously.' Lady Ashford said 'Dude, let's just do it!'" | ollmcp --delegation --memory
```

## Expected Memory Structure

After tests, the memory should look like:

```
G_ACCENT_WRITER (Goal)
├── Description: "Maintain character accent and speech pattern consistency"
├── F_ACC_LADY_ASHFORD (Feature)
│   ├── Title: "Lady Ashford - Speech Pattern"
│   ├── Description: "Formal, educated, aristocratic..."
│   └── Acceptance Criteria: "All dialogue must match formality level..."
└── F_ACC_JAKE (Feature)
    ├── Title: "Jake - Speech Pattern"
    ├── Description: "Casual, street-smart, frequent slang..."
    └── Acceptance Criteria: "All dialogue must match casual patterns..."
```

## Troubleshooting

**If PLANNER doesn't assign to ACCENT_WRITER**:
- Check that query mentions "dialogue" or "accent" or "speech"
- Try: "Use ACCENT_WRITER to review this dialogue: ..."

**If agent doesn't initialize memory**:
- Check memory is enabled: `/memory on`
- Check agent has memory tools allowed (should be in agent definition)

**If agent errors on memory operations**:
- Check builtin tools are available
- Verify memory system is running

## Success Criteria

Test is successful if:
1. ✅ ACCENT_WRITER creates its goal on first run
2. ✅ Agent creates character profiles from dialogue
3. ✅ Agent correctly identifies consistent vs. inconsistent dialogue
4. ✅ Agent provides helpful suggestions for fixes
5. ✅ Memory persists across multiple queries
6. ✅ Agent retrieves and uses stored profiles in subsequent reviews
