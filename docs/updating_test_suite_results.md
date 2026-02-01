# Integrating Latest os_llm_testing_suite Results into ollmcp

**Version**: 0.45.32
**Date**: 2026-01-26

## Overview

This document describes how to integrate the latest test results from os_llm_testing_suite into ollmcp's model intelligence system, ensuring the most current performance data is used for model selection.

## Current Integration

### How It Works Today

**File**: `mcp_client_for_ollama/models/performance_store.py`

```python
class PerformanceStore:
    def __init__(self, test_suite_path: Optional[str] = None):
        """Initialize performance store.

        Default path: ~/project/os_llm_testing_suite/results
        """
        self.test_suite_path = test_suite_path or "~/project/os_llm_testing_suite/results"
        self.models: Dict[str, ModelPerformance] = {}
        self.last_update: Optional[datetime] = None

        self.load_test_results()  # Loads on initialization
```

**Loading Process**:
1. Scans `~/project/os_llm_testing_suite/results/` directory
2. Finds all `report_*.json` files recursively
3. Parses each JSON file to extract:
   - Model name
   - Overall score
   - Tier scores (1, 2, 3)
   - Dimension scores (tool_selection, parameters, planning, etc.)
   - Test count
   - Timestamp
   - Temperature setting
4. **Keeps best result per model** (highest overall_score)
5. Stores in memory for fast lookups

### Test Results Directory Structure

```
~/project/os_llm_testing_suite/results/
├── granite4_3b/
│   ├── report_granite4_3b_temp0_2_20260126_162552.json  ← Latest
│   ├── report_granite4_3b_temp0_2_20260125_213807.json
│   └── ... (older runs)
├── qwen2.5_32b/
│   ├── report_qwen2.5_32b_temp0_2_20260126_145230.json
│   └── ...
└── ... (other models)
```

**Key**: Each directory contains multiple test runs. PerformanceStore automatically picks the best scoring run.

## Getting Latest Test Results

### Method 1: Automatic Update on Restart (Current Behavior)

**How**: Results are loaded when ollmcp starts

**Pros**:
- ✅ Simple - just restart ollmcp
- ✅ No code changes needed
- ✅ Always picks best result per model

**Cons**:
- ❌ Requires restart to see new results
- ❌ No notification when new results available

**Usage**:
```bash
# Run new tests in os_llm_testing_suite
cd ~/project/os_llm_testing_suite
python -m llm_test_suite --model granite4:3b --temperature 0.2

# Restart ollmcp to load new results
ollmcp
```

### Method 2: Runtime Reload (Recommended Addition)

**Proposal**: Add CLI command to reload test results without restarting

**Implementation**:

```python
# In mcp_client_for_ollama/models/performance_store.py

class PerformanceStore:
    def reload(self) -> Dict[str, str]:
        """Reload test results from disk.

        Returns:
            Dictionary with reload summary:
            - models_before: Count before reload
            - models_after: Count after reload
            - new_models: List of newly added models
            - updated_models: List of models with improved scores
        """
        # Track previous state
        models_before = set(self.models.keys())
        scores_before = {k: v.overall_score for k, v in self.models.items()}

        # Reload
        self.models = {}
        self.load_test_results()

        # Track changes
        models_after = set(self.models.keys())
        new_models = list(models_after - models_before)
        updated_models = [
            model for model in models_after & models_before
            if self.models[model].overall_score > scores_before[model]
        ]

        return {
            "models_before": len(models_before),
            "models_after": len(models_after),
            "new_models": new_models,
            "updated_models": updated_models,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
```

**CLI Command**:

```python
# In mcp_client_for_ollama/client.py

async def reload_test_results(self):
    """Reload test suite results from disk"""

    if not hasattr(self, 'delegation_client') or not self.delegation_client:
        self.console.print("[yellow]Delegation not enabled - no test results to reload[/yellow]")
        return

    if not hasattr(self.delegation_client, 'model_selector') or not self.delegation_client.model_selector:
        self.console.print("[yellow]Model intelligence not enabled[/yellow]")
        return

    # Reload
    self.console.print("[cyan]Reloading test suite results...[/cyan]")
    summary = self.delegation_client.model_selector.store.reload()

    # Display summary
    self.console.print(Panel(
        f"[green]Test Results Reloaded[/green]\n\n"
        f"Models tracked: {summary['models_after']} "
        f"({summary['models_before']} → {summary['models_after']})\n\n"
        f"New models: {len(summary['new_models'])}\n"
        + (f"  • {', '.join(summary['new_models'])}\n" if summary['new_models'] else "") +
        f"\nUpdated models: {len(summary['updated_models'])}\n"
        + (f"  • {', '.join(summary['updated_models'])}\n" if summary['updated_models'] else "") +
        f"\nLast update: {summary['last_update']}",
        title="Test Results",
        border_style="green"
    ))

# Add to main loop query handling
if query.lower() in ['reload-tests', 'rt']:
    await self.reload_test_results()
    continue
```

**Usage**:
```bash
# In ollmcp CLI
> reload-tests
# or
> rt

# Output:
┌─────── Test Results ────────┐
│ Test Results Reloaded       │
│                             │
│ Models tracked: 32 (30 → 32)│
│                             │
│ New models: 2               │
│   • mistral:7b              │
│   • phi-4:14b               │
│                             │
│ Updated models: 3           │
│   • granite4:3b             │
│   • qwen2.5:32b             │
│   • qwen3:30b-a3b           │
│                             │
│ Last update: 2026-01-26T... │
└─────────────────────────────┘
```

### Method 3: Auto-Watch for New Results (Advanced)

**Proposal**: Use file system watching to auto-reload when new test results appear

**Implementation**:

```python
# New file: mcp_client_for_ollama/models/test_watcher.py

import time
from pathlib import Path
from typing import Callable
import threading

class TestResultsWatcher:
    """Watch test results directory for changes and auto-reload"""

    def __init__(self,
                 results_dir: str,
                 on_change_callback: Callable,
                 check_interval: int = 60):
        """Initialize watcher.

        Args:
            results_dir: Path to test results directory
            on_change_callback: Function to call when changes detected
            check_interval: Seconds between checks (default: 60)
        """
        self.results_dir = Path(results_dir).expanduser()
        self.on_change = on_change_callback
        self.check_interval = check_interval
        self.last_check = {}
        self.running = False
        self.thread = None

    def start(self):
        """Start watching for changes"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        logger.info(f"Test results watcher started (checking every {self.check_interval}s)")

    def stop(self):
        """Stop watching"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _watch_loop(self):
        """Main watch loop"""
        while self.running:
            try:
                changed = self._check_for_changes()
                if changed:
                    logger.info(f"Detected {len(changed)} new/updated test results")
                    self.on_change(changed)
            except Exception as e:
                logger.error(f"Error in test watcher: {e}")

            time.sleep(self.check_interval)

    def _check_for_changes(self) -> List[Path]:
        """Check for new or modified test result files.

        Returns:
            List of changed file paths
        """
        if not self.results_dir.exists():
            return []

        changed = []

        # Find all JSON report files
        for json_file in self.results_dir.rglob("report_*.json"):
            mtime = json_file.stat().st_mtime

            # Check if new or modified
            if (str(json_file) not in self.last_check or
                mtime > self.last_check[str(json_file)]):
                changed.append(json_file)
                self.last_check[str(json_file)] = mtime

        return changed
```

**Integration**:

```python
# In mcp_client_for_ollama/agents/delegation_client.py

from ..models.test_watcher import TestResultsWatcher

class DelegationClient:
    def __init__(self, ...):
        # ... existing init ...

        # Start test results watcher if intelligence enabled
        if self.intelligence_enabled and self.model_selector:
            def on_results_changed(changed_files):
                logger.info(f"Auto-reloading test results ({len(changed_files)} files changed)")
                self.model_selector.store.reload()
                self.console.print("[dim]✓ Test results auto-reloaded[/dim]")

            self.test_watcher = TestResultsWatcher(
                results_dir=self.model_selector.store.test_suite_path,
                on_change_callback=on_results_changed,
                check_interval=300  # Check every 5 minutes
            )
            self.test_watcher.start()
```

**Pros**:
- ✅ Automatic - no manual reload needed
- ✅ Always uses latest data
- ✅ Notifies user when data updated

**Cons**:
- ❌ More complex
- ❌ Background thread overhead
- ❌ Could miss changes if ollmcp not running

**Configuration**:

```json
// In config.json
{
  "model_intelligence": {
    "enabled": true,
    "test_suite_path": "~/project/os_llm_testing_suite/results",
    "auto_reload": true,
    "reload_interval": 300  // 5 minutes
  }
}
```

## Manual Update Process

### Step-by-Step: Getting Latest Results

#### 1. Run New Tests (in os_llm_testing_suite)

```bash
cd ~/project/os_llm_testing_suite

# Test specific model
python -m llm_test_suite --model granite4:3b --temperature 0.2

# Test all available models
python -m llm_test_suite --all-models --temperature 0.2

# Test with different temperature
python -m llm_test_suite --model qwen2.5:32b --temperature 0.5
```

**Results saved to**: `~/project/os_llm_testing_suite/results/{model_name}/report_*.json`

#### 2. Verify Results

```bash
# Check latest result for granite4:3b
ls -lt ~/project/os_llm_testing_suite/results/granite4_3b/ | head -5

# View summary
cat ~/project/os_llm_testing_suite/results/granite4_3b/report_*.md | tail -50
```

#### 3. Update ollmcp

**Option A: Restart**
```bash
# Exit ollmcp
> exit

# Start again (auto-loads latest)
ollmcp
```

**Option B: Reload (if implemented)**
```bash
# In running ollmcp session
> reload-tests
```

#### 4. Verify Update

```bash
# Check which models are loaded
> show-agent-models
# or
> sam
```

### Validation

**Check test data is loaded**:

```python
# In ollmcp Python console (if available)
from mcp_client_for_ollama.models import PerformanceStore

store = PerformanceStore()
print(f"Loaded {len(store.models)} models")
print(f"Last update: {store.last_update}")

# Check specific model
perf = store.get_model_performance("granite4:3b")
if perf:
    print(f"granite4:3b score: {perf.overall_score}")
    print(f"Timestamp: {perf.timestamp}")
```

## Update Frequency Recommendations

### Development Phase
- **Frequency**: After every test suite run
- **Method**: Manual restart or reload command
- **Reason**: Rapid iteration, frequent model testing

### Production Use
- **Frequency**: Daily or weekly
- **Method**: Auto-watch (check every 5-30 minutes)
- **Reason**: Balance freshness with stability

### Model Releases
- **Frequency**: Immediately after testing new models
- **Method**: Reload command
- **Reason**: Want to use new models ASAP

## Handling Test Result Changes

### New Model Added

**Scenario**: You test a new model (e.g., "llama4:70b")

**What Happens**:
1. Test results saved to `results/llama4_70b/report_*.json`
2. PerformanceStore reload discovers new model
3. Model becomes available for selection
4. Selector ranks it against existing models

**User Action**: None required if auto-reload enabled, otherwise use `reload-tests`

### Model Score Improved

**Scenario**: You retest granite4:3b with better prompts, score improves from 84.0 → 88.0

**What Happens**:
1. New result saved with higher score
2. PerformanceStore keeps best result (88.0)
3. Model selection updated to use new score
4. granite4:3b may now be selected for more tasks

**User Action**: Reload to activate improved score

### Model Score Decreased

**Scenario**: You test with different temperature, score drops from 88.4 → 82.0

**What Happens**:
1. New result saved with lower score
2. **PerformanceStore keeps PREVIOUS best result** (88.4)
3. Lower-scoring run ignored
4. No change to model selection

**Why**: Store always keeps highest-scoring run per model

**Override**: To force use of lower score, delete higher-scoring JSON files

## Troubleshooting

### Issue 1: No Test Results Found

**Symptom**:
```
WARNING: Test suite results not found at /home/user/project/os_llm_testing_suite/results
Model intelligence will use fallback selection without performance data
```

**Solutions**:
1. **Check path exists**:
   ```bash
   ls ~/project/os_llm_testing_suite/results
   ```

2. **Check results exist**:
   ```bash
   find ~/project/os_llm_testing_suite/results -name "report_*.json" | wc -l
   ```

3. **Specify custom path**:
   ```python
   from mcp_client_for_ollama.models import PerformanceStore
   store = PerformanceStore(test_suite_path="/custom/path/to/results")
   ```

4. **Set in config**:
   ```json
   {
     "model_intelligence": {
       "test_suite_path": "/custom/path/to/results"
     }
   }
   ```

### Issue 2: Old Data Being Used

**Symptom**: Model selection not reflecting recent test improvements

**Solutions**:
1. **Check timestamps**:
   ```bash
   # Find newest test result
   find ~/project/os_llm_testing_suite/results -name "report_*.json" -exec ls -lt {} + | head -5
   ```

2. **Force reload**:
   ```bash
   # In ollmcp
   > reload-tests
   ```

3. **Restart ollmcp**:
   ```bash
   # Exit and restart
   > exit
   ollmcp
   ```

### Issue 3: Wrong Model Being Selected

**Symptom**: Expected qwen2.5:32b but granite4:3b selected

**Debug Steps**:

1. **Check test data**:
   ```python
   from mcp_client_for_ollama.models import PerformanceStore

   store = PerformanceStore()

   # Check both models
   for model in ["qwen2.5:32b", "granite4:3b"]:
       perf = store.get_model_performance(model)
       if perf:
           print(f"{model}: score={perf.overall_score}, tier2={perf.tier_scores.get('2', 0)}")
   ```

2. **Check agent requirements**:
   ```python
   from mcp_client_for_ollama.models import AGENT_REQUIREMENTS

   req = AGENT_REQUIREMENTS.get("SHELL_EXECUTOR")
   print(f"Min score: {req['min_score']}")
   print(f"Min tier: {req['min_tier']}")
   print(f"Critical dims: {req['critical_dimensions']}")
   ```

3. **Test selection logic**:
   ```python
   from mcp_client_for_ollama.models import ModelSelector

   selector = ModelSelector(performance_store=store)

   # Get recommendations
   recs = selector.get_recommendations("SHELL_EXECUTOR", top_k=5)
   for i, rec in enumerate(recs, 1):
       print(f"{i}. {rec['model']}: score={rec['score']:.1f}")
   ```

## Best Practices

### 1. Keep Test Results Organized

**Structure**:
```
~/project/os_llm_testing_suite/results/
├── granite4_3b/
│   ├── report_granite4_3b_temp0_2_20260126_162552.json  ← Latest production
│   ├── report_granite4_3b_temp0_5_20260125_032223.json  ← Experimental
│   └── archive/
│       └── ... (old runs)
└── ...
```

**Cleanup Old Results**:
```bash
# Keep only latest 5 runs per model
cd ~/project/os_llm_testing_suite/results

for model_dir in */; do
  cd "$model_dir"
  ls -t report_*.json | tail -n +6 | xargs -r rm
  cd ..
done
```

### 2. Document Test Conditions

**Add metadata to test runs**:
```bash
# When running tests, use descriptive filenames
python -m llm_test_suite \
  --model granite4:3b \
  --temperature 0.2 \
  --output-prefix "production"

# Result: report_granite4_3b_production_temp0_2_20260126.json
```

### 3. Version Control Test Results

**Track changes in git**:
```bash
cd ~/project/os_llm_testing_suite

# Commit new results
git add results/granite4_3b/report_*.json
git commit -m "Update granite4:3b test results - improved score to 88.0"
```

### 4. Automate Testing

**Cron job for nightly tests**:
```bash
# crontab -e

# Test all models nightly at 2 AM
0 2 * * * cd ~/project/os_llm_testing_suite && python -m llm_test_suite --all-models --temperature 0.2 > /tmp/llm_test.log 2>&1
```

## Summary

### Current State (0.45.32)
- ✅ Automatic loading on startup
- ✅ Finds all report_*.json files
- ✅ Keeps best result per model
- ✅ Default path: ~/project/os_llm_testing_suite/results
- ❌ No runtime reload
- ❌ No auto-watch
- ❌ No update notifications

### Recommended Implementations

**Priority 1**: Reload command (`reload-tests`)
- Simple to implement
- Immediate user control
- No background overhead

**Priority 2**: Show test data info command
- Display loaded models
- Show last update timestamp
- Identify missing models

**Priority 3**: Auto-watch with notifications
- Background file monitoring
- Automatic reload on changes
- User notifications

### Quick Reference

**Load latest results**:
```bash
# Option 1: Restart ollmcp
exit
ollmcp

# Option 2: Reload (if implemented)
> reload-tests
```

**Check what's loaded**:
```bash
> show-agent-models
# Shows model assignments and scores
```

**Run new tests**:
```bash
cd ~/project/os_llm_testing_suite
python -m llm_test_suite --model <model_name> --temperature 0.2
```

---

**Status**: Documentation complete, reload command recommended for 0.45.33
