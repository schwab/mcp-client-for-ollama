# Memory Tools Guide

## Overview

The Memory System provides persistent, multi-session agent workflows based on the Anthropic memory pattern. It enables agents to maintain context across sessions and work collaboratively on long-running projects with structured goals and features.

This guide documents all available memory tools that you can use interactively through the AI.

## Table of Contents

- [Setup](#setup)
- [Quick Reference](#quick-reference)
- [Viewing Tools](#viewing-tools)
- [Interactive Management Tools](#interactive-management-tools)
- [Progress Tracking Tools](#progress-tracking-tools)
- [Common Workflows](#common-workflows)
- [Best Practices](#best-practices)

---

## Setup

### Enable Memory System

```
> memory-enable (or 'me')
```

The system will automatically reload - no restart needed.

### Create a New Session

```
> memory-new (or 'mn')
```

Select a domain (coding, research, operations, content, general) and provide a description. The INITIALIZER agent will create structured goals and features.

### Resume an Existing Session

```
> memory-resume (or 'mr')
```

Select from available sessions to continue where you left off.

### Check Session Status

```
> memory-status (or 'mst')
```

View the current active session and its progress.

---

## Quick Reference

### Viewing Tools
| Tool | Purpose | Example Request |
|------|---------|----------------|
| `get_memory_state` | View all goals and features | "Show me the overall status" |
| `get_goal_details` | View a specific goal | "Show me G1" |
| `get_feature_details` | View a specific feature | "What's F2 about?" |

### Goal Management
| Tool | Purpose | Example Request |
|------|---------|----------------|
| `add_goal` | Add a new goal | "Add a goal for implementing authentication" |
| `update_goal` | Modify goal description/constraints | "Update G1 to require OAuth" |
| `remove_goal` | Delete a goal | "Remove goal G3" |

### Feature Management
| Tool | Purpose | Example Request |
|------|---------|----------------|
| `add_feature` | Add a new feature to a goal | "Add a login endpoint feature to G1" |
| `update_feature` | Modify feature properties | "Change F2's priority to high" |
| `remove_feature` | Delete a feature | "Remove feature F5" |
| `move_feature` | Move feature to different goal | "Move F3 to G2" |

### Progress Tracking
| Tool | Purpose | Example Request |
|------|---------|----------------|
| `update_feature_status` | Mark feature status | "Mark F1 as completed" |
| `log_progress` | Record what was done | "Log progress on implementing login" |
| `add_test_result` | Record test results | "Add test result for F2" |

### Session Management
| Tool | Purpose | Example Request |
|------|---------|----------------|
| `update_session_description` | Update session metadata | "Change session description to..." |

---

## Viewing Tools

### `builtin.get_memory_state`

**Purpose:** Get complete overview of the entire memory session.

**Parameters:** None

**Returns:**
- Session ID, domain, description
- Overall progress percentage
- All goals with their features and statuses

**Example:**
```
User: "Show me the overall status"
AI: [calls get_memory_state()]

Output:
Session: auth-system_20251219_143022
Domain: coding
Description: JWT authentication system implementation

Progress:
  Completed: 3/8 features (37.5%)

Goals:
  G1: Implement user authentication [in_progress]
    ✓ F1: POST /register endpoint
    ⟳ F2: POST /login with JWT
    ○ F3: Token validation middleware
```

**When to use:**
- Getting the big picture
- Checking overall progress
- Seeing all goals at once

---

### `builtin.get_goal_details`

**Purpose:** Get focused view of a single goal with feature summary.

**Parameters:**
- `goal_id` (required): ID of the goal (e.g., "G1")

**Returns:**
- Goal description and status
- List of constraints
- Progress bar (completed/total features)
- Feature list with status icons, priorities, assignees
- Criteria counts for each feature

**Example:**
```
User: "Show me what's in G1"
AI: [calls get_goal_details(goal_id="G1")]

Output:
======================================================================
GOAL G1: Implement user authentication
Status: in_progress
======================================================================

Constraints:
  • Must use bcrypt for password hashing
  • JWT tokens expire after 24 hours
  • Must handle rate limiting

Progress: 1/3 features (33%)

Features:
  ✓ F1: POST /register endpoint → CODER
      4 criteria defined
  ⟳ F2: [HIGH] POST /login with JWT generation → CODER
      5 criteria defined
  ○ F3: Token validation middleware
      3 criteria defined

💡 Use builtin.get_feature_details to see details about a specific feature
```

**When to use:**
- Reviewing a specific goal
- Planning work on a goal
- Checking goal progress

---

### `builtin.get_feature_details`

**Purpose:** Get detailed information about a specific feature.

**Parameters:**
- `feature_id` (required): ID of the feature (e.g., "F1")

**Returns:**
- Parent goal reference
- Feature description and status
- Complete list of pass/fail criteria
- Required tests
- Recent test results (if any)
- Notes (if any)

**Example:**
```
User: "What's F2 about?"
AI: [calls get_feature_details(feature_id="F2")]

Output:
Parent Goal: G1 - Implement user authentication
======================================================================
FEATURE: F2
Description: POST /login with JWT token generation
Status: in_progress

Pass/Fail Criteria:
  1. Accepts username and password in request body
  2. Returns 200 with JWT token for valid credentials
  3. Returns 401 for invalid credentials
  4. Token expires after 24 hours
  5. Token includes user ID and permissions

Required Tests:
  - test_login_success_returns_token
  - test_login_invalid_credentials_401
  - test_token_expiration
  - test_token_contains_user_id
```

**When to use:**
- Understanding what a feature requires
- Reviewing acceptance criteria
- Checking test results
- Before starting work on a feature

---

## Interactive Management Tools

### Goal Management

#### `builtin.add_goal`

**Purpose:** Add a new high-level goal to your session.

**Parameters:**
- `description` (required): Clear description of the goal
- `constraints` (optional): List of constraints or requirements

**Returns:** Confirmation with new goal ID

**Example:**
```
User: "Add a goal for implementing password reset functionality"
AI: [calls add_goal(
      description="Implement password reset flow",
      constraints=[
        "Must send email verification",
        "Reset links expire after 1 hour",
        "Must prevent brute force attacks"
      ]
    )]

Output:
✓ Added new goal G4:
  Description: Implement password reset flow
  Constraints: 3
  Features: 0 (add features with add_feature tool)
```

**When to use:**
- New requirements emerge
- Expanding project scope
- Organizing work into logical groups

---

#### `builtin.update_goal`

**Purpose:** Modify an existing goal's description or constraints.

**Parameters:**
- `goal_id` (required): ID of the goal to update
- `description` (optional): New description
- `add_constraints` (optional): List of constraints to add
- `remove_constraints` (optional): List of constraints to remove

**Returns:** Confirmation with changes made

**Example:**
```
User: "Update G1 to require OAuth instead of JWT"
AI: [calls update_goal(
      goal_id="G1",
      description="Implement OAuth 2.0 authentication",
      add_constraints=["Must support Google OAuth provider"],
      remove_constraints=["JWT tokens expire after 24 hours"]
    )]

Output:
✓ Updated goal G1:
  Updated description, Added 1 constraint(s), Removed 1 constraint(s)
  Current description: Implement OAuth 2.0 authentication
  Constraints: 3
```

**When to use:**
- Requirements change
- Clarifying goals
- Adding technical constraints
- Refining scope

---

#### `builtin.remove_goal`

**Purpose:** Delete a goal and all its features.

**Parameters:**
- `goal_id` (required): ID of the goal to remove
- `confirm` (required): Must be `true` to actually delete (safety check)

**Returns:** Confirmation or warning if not confirmed

**Example:**
```
User: "Remove goal G3, we're not doing that anymore"
AI: [calls remove_goal(goal_id="G3", confirm=false)]

Output:
⚠️  Goal G3 has 4 feature(s).
To confirm deletion, call with confirm=True

AI: [calls remove_goal(goal_id="G3", confirm=true)]

Output:
✓ Removed goal G3
  Deleted 4 associated feature(s)
```

**When to use:**
- Scope reduction
- Removing obsolete goals
- Project pivot

---

### Feature Management

#### `builtin.add_feature`

**Purpose:** Add a new feature to an existing goal.

**Parameters:**
- `goal_id` (required): ID of the goal to add feature to
- `description` (required): Clear description of the feature
- `criteria` (optional): List of pass/fail acceptance criteria
- `tests` (optional): List of test names
- `priority` (optional): "high", "medium", or "low" (default: "medium")
- `assigned_to` (optional): Agent type or person name

**Returns:** Confirmation with new feature ID

**Example:**
```
User: "Add a feature to G1 for email verification during registration"
AI: [calls add_feature(
      goal_id="G1",
      description="Email verification for new user registration",
      criteria=[
        "Sends verification email upon registration",
        "User cannot log in until email verified",
        "Verification links expire after 24 hours",
        "Resend verification option available"
      ],
      tests=[
        "test_verification_email_sent",
        "test_unverified_user_cannot_login",
        "test_expired_link_rejected",
        "test_resend_verification"
      ],
      priority="high",
      assigned_to="CODER"
    )]

Output:
✓ Added new feature F4 to goal G1:
  Description: Email verification for new user registration
  Priority: high
  Criteria: 4
  Tests: 4
  Assigned to: CODER
```

**When to use:**
- Breaking down goals into tasks
- New requirements emerge
- Adding implementation details

---

#### `builtin.update_feature`

**Purpose:** Modify an existing feature's properties.

**Parameters:**
- `feature_id` (required): ID of the feature to update
- `description` (optional): New description
- `add_criteria` (optional): List of criteria to add
- `remove_criteria` (optional): List of criteria to remove
- `add_tests` (optional): List of test names to add
- `remove_tests` (optional): List of test names to remove
- `priority` (optional): New priority ("high", "medium", "low")
- `assigned_to` (optional): New assignee

**Returns:** Confirmation with changes made

**Example:**
```
User: "Add rate limiting criteria to F2 and change priority to high"
AI: [calls update_feature(
      feature_id="F2",
      add_criteria=["Must rate limit to 5 attempts per minute"],
      add_tests=["test_rate_limiting"],
      priority="high"
    )]

Output:
✓ Updated feature F2:
  Added 1 criterion/criteria, Added 1 test(s), Changed priority to high
  Current description: POST /login with JWT generation
  Priority: high
  Criteria: 6
  Tests: 5
```

**When to use:**
- Refining requirements
- Adding edge cases
- Changing priorities
- Reassigning work

---

#### `builtin.remove_feature`

**Purpose:** Delete a feature from its parent goal.

**Parameters:**
- `feature_id` (required): ID of the feature to remove
- `confirm` (required): Must be `true` to actually delete (safety check)

**Returns:** Confirmation or warning if not confirmed

**Example:**
```
User: "Remove feature F7, it's out of scope"
AI: [calls remove_feature(feature_id="F7", confirm=true)]

Output:
✓ Removed feature F7
  From goal: G2
```

**When to use:**
- Scope reduction
- Removing completed or obsolete features
- Cleaning up

---

#### `builtin.move_feature`

**Purpose:** Move a feature from one goal to another.

**Parameters:**
- `feature_id` (required): ID of the feature to move
- `target_goal_id` (required): ID of the goal to move it to

**Returns:** Confirmation with source and destination

**Example:**
```
User: "Move F5 to G3, it fits better there"
AI: [calls move_feature(feature_id="F5", target_goal_id="G3")]

Output:
✓ Moved feature F5
  From: G1
  To: G3
```

**When to use:**
- Reorganizing features
- Better goal alignment
- Restructuring project

---

### Session Management

#### `builtin.update_session_description`

**Purpose:** Update the current session's description.

**Parameters:**
- `description` (required): New session description

**Returns:** Confirmation with old and new descriptions

**Example:**
```
User: "Update the session description to focus on OAuth instead of JWT"
AI: [calls update_session_description(
      description="OAuth 2.0 authentication system with Google provider"
    )]

Output:
✓ Updated session description
  Old: JWT authentication system implementation
  New: OAuth 2.0 authentication system with Google provider
```

**When to use:**
- Project focus changes
- Keeping metadata current
- Clarifying session purpose

---

## Progress Tracking Tools

### `builtin.update_feature_status`

**Purpose:** Update the status of a feature.

**Parameters:**
- `feature_id` (required): ID of the feature to update
- `status` (required): New status ("pending", "in_progress", "completed", "failed", "blocked")
- `notes` (optional): Notes about the update

**Returns:** Confirmation with status change

**Example:**
```
User: "Mark F2 as completed"
AI: [calls update_feature_status(
      feature_id="F2",
      status="completed",
      notes="All tests passing, deployed to staging"
    )]

Output:
✓ Updated feature F2: in_progress → completed
  Description: POST /login with JWT generation
  5 criteria defined
  Notes: All tests passing, deployed to staging
```

**When to use:**
- After completing work
- When blocked
- After test failures
- Starting new work

---

### `builtin.log_progress`

**Purpose:** Log a progress entry to record what actions were taken.

**Parameters:**
- `agent_type` (required): Type of agent (e.g., "CODER", "EXECUTOR", "USER")
- `action` (required): Short description of the action
- `outcome` (required): Outcome ("success", "failure", "partial", "blocked")
- `details` (required): Detailed description of what was done
- `feature_id` (optional): Related feature ID
- `artifacts_changed` (optional): List of files/artifacts modified

**Returns:** Confirmation with progress entry

**Example:**
```
AI: [calls log_progress(
      agent_type="CODER",
      action="Implemented login endpoint",
      outcome="success",
      details="Created POST /login endpoint with JWT generation, password validation, and rate limiting",
      feature_id="F2",
      artifacts_changed=["src/routes/auth.py", "tests/test_auth.py"]
    )]

Output:
✓ Progress logged:
  Agent: CODER
  Action: Implemented login endpoint
  Outcome: success
  Feature: F2
  Files changed: src/routes/auth.py, tests/test_auth.py
```

**When to use:**
- After completing work
- Recording decisions
- Tracking what changed
- Collaboration handoffs

---

### `builtin.add_test_result`

**Purpose:** Add a test result to a feature. Auto-updates feature status based on test results.

**Parameters:**
- `feature_id` (required): ID of the feature being tested
- `test_id` (required): ID/name of the test
- `passed` (required): Whether the test passed (boolean)
- `details` (optional): Details about the test
- `output` (optional): Test output

**Returns:** Confirmation with auto-updated feature status

**Example:**
```
AI: [calls add_test_result(
      feature_id="F2",
      test_id="test_login_success_returns_token",
      passed=true,
      details="Login with valid credentials returns JWT token"
    )]

Output:
✓ Test result added:
  Feature: F2
  Test: test_login_success_returns_token
  Result: PASS
  Feature status auto-updated to: in_progress
```

**When to use:**
- After running tests
- Recording test failures
- Tracking test coverage
- Auto-updating feature status

---

## Common Workflows

### Starting a New Project

```
1. Enable memory system
   > memory-enable

2. Create new session
   > memory-new
   → Select domain (e.g., "coding")
   → Describe project (e.g., "Build REST API for task management")

3. Review generated goals
   User: "Show me the overall status"
   AI: [calls get_memory_state()]

4. Refine as needed
   User: "Add a goal for implementing webhooks"
   AI: [calls add_goal(...)]
```

### Working on a Feature

```
1. Review the feature
   User: "Show me F3"
   AI: [calls get_feature_details(feature_id="F3")]

2. Start work
   User: "Mark F3 as in progress"
   AI: [calls update_feature_status(feature_id="F3", status="in_progress")]

3. Make changes
   [code implementation happens]

4. Record progress
   AI: [calls log_progress(
         agent_type="CODER",
         action="Implemented webhook endpoint",
         outcome="success",
         feature_id="F3"
       )]

5. Run tests
   AI: [calls add_test_result(
         feature_id="F3",
         test_id="test_webhook_delivery",
         passed=true
       )]

6. Complete
   User: "Mark F3 as completed"
   AI: [calls update_feature_status(feature_id="F3", status="completed")]
```

### Adapting to Changing Requirements

```
1. User realizes requirements changed
   User: "Actually, we need to use OAuth instead of JWT for G1"

2. Update goal
   AI: [calls update_goal(
         goal_id="G1",
         description="Implement OAuth 2.0 authentication"
       )]

3. Update affected features
   User: "Update F2 to generate OAuth tokens instead"
   AI: [calls update_feature(
         feature_id="F2",
         description="POST /login with OAuth 2.0 token generation",
         add_criteria=["Must support Google OAuth provider"]
       )]

4. Add new features as needed
   User: "Add a feature for OAuth callback handling"
   AI: [calls add_feature(
         goal_id="G1",
         description="OAuth callback endpoint for provider redirects"
       )]
```

### Resuming a Session

```
1. Resume session
   > memory-resume
   → Select session from list

2. Check status
   User: "What's the current status?"
   AI: [calls get_memory_state()]

3. Find next task
   User: "Show me what's pending in G1"
   AI: [calls get_goal_details(goal_id="G1")]

4. Continue work
   User: "Let's work on F5"
   AI: [calls get_feature_details(feature_id="F5")]
```

---

## Best Practices

### Goal Organization

- **Keep goals high-level**: Goals should be major milestones or functional areas
- **Use 2-5 goals per session**: More becomes hard to manage
- **Add constraints early**: Define technical requirements upfront
- **Update as you learn**: Refine goals as understanding grows

### Feature Definition

- **Make features atomic**: Each feature should be completable in one focused session
- **Write testable criteria**: Use specific, verifiable pass/fail conditions
- **Include test names**: Define tests upfront, even if not implemented yet
- **Set realistic priorities**: Not everything can be high priority
- **Assign ownership**: Use `assigned_to` to track who's working on what

### Status Management

- **Update status frequently**: Keep status current as work progresses
- **Use "blocked" status**: When stuck, mark as blocked and log why
- **Log progress regularly**: Record what you did and what changed
- **Add test results**: Let test results auto-update feature status

### Session Hygiene

- **Clean up completed features**: Remove or archive when done
- **Remove obsolete goals**: Don't keep goals that are no longer relevant
- **Update session description**: Keep metadata current
- **Review regularly**: Periodic review keeps memory accurate

### Collaboration

- **Use progress logging**: Log what you did for the next person
- **Add detailed notes**: Explain decisions and blockers
- **Assign features**: Clear ownership prevents duplicate work
- **Update descriptions**: Keep feature/goal text current

### Memory Queries

- **Use specific views**: `get_goal_details` instead of full `get_memory_state`
- **Check before modifying**: Review current state before changes
- **Verify changes**: Use viewing tools to confirm updates
- **Navigate hierarchically**: Session → Goal → Feature

---

## Tips

### For Users

- **Be specific in requests**: "Add a high-priority feature to G1 for API rate limiting"
- **Review before confirming**: Check deletions with `confirm=false` first
- **Use natural language**: The AI understands conversational requests
- **Reference IDs**: Use goal/feature IDs (G1, F2) for precision

### For the AI

- **Always call viewing tools**: Show users what they're asking about
- **Confirm before deleting**: Use the confirm parameter for safety
- **Provide context**: Include parent goal info when showing features
- **Update status**: Log progress after completing work
- **Be conversational**: Explain what tools you're calling and why

---

## Troubleshooting

### "Memory tools not available"

**Cause:** Memory system not enabled or no active session

**Solution:**
1. Enable memory: `memory-enable`
2. Create or resume session: `memory-new` or `memory-resume`

### "Feature/Goal not found"

**Cause:** Invalid ID or ID doesn't exist in current session

**Solution:**
1. Check available IDs: Use `get_memory_state` or `get_goal_details`
2. Verify spelling: IDs are case-sensitive (G1, not g1)

### Changes not persisting

**Cause:** Session not properly loaded or saved

**Solution:**
1. Check active session: `memory-status`
2. Verify changes: Use viewing tools to confirm
3. If issues persist, resume session again

### Too many features to see

**Cause:** Using `get_memory_state` when you want focused view

**Solution:**
- Use `get_goal_details` for single goal
- Use `get_feature_details` for single feature

---

## Summary

The memory system provides 14 powerful tools organized into four categories:

**Viewing (3 tools):** Quick navigation at different levels
- `get_memory_state` - Complete overview
- `get_goal_details` - Single goal focus
- `get_feature_details` - Single feature focus

**Goal Management (3 tools):** Structure your project
- `add_goal` - Create new goals
- `update_goal` - Modify goals
- `remove_goal` - Delete goals

**Feature Management (4 tools):** Define and organize work
- `add_feature` - Create new features
- `update_feature` - Modify features
- `remove_feature` - Delete features
- `move_feature` - Reorganize features

**Progress Tracking (3 tools):** Record what happened
- `update_feature_status` - Mark progress
- `log_progress` - Record actions
- `add_test_result` - Track testing

**Session Management (1 tool):** Maintain metadata
- `update_session_description` - Update session info

Use these tools naturally through conversation with the AI to create, modify, and track your long-running projects!
