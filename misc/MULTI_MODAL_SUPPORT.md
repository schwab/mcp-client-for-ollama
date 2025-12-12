# Multi-Modal Support (Image Analysis)

## Overview

The MCP Client for Ollama now supports multi-modal capabilities, enabling you to analyze images using vision-capable models. This feature allows you to extract information from screenshots, diagrams, charts, and photos directly within your workflow.

## Features

- 🖼️ **Image Analysis**: Analyze images using vision models (llava, bakllava, cogvlm, etc.)
- 🔍 **Auto-Detection**: Automatically finds and uses available vision models
- ⚙️ **Configuration**: Set preferred vision models for consistent results
- 🎯 **Agent Integration**: EXECUTOR, READER, and RESEARCHER agents support image analysis
- 📁 **Format Support**: PNG, JPG, JPEG, GIF, BMP, WEBP
- 💾 **Persistence**: Vision model preferences saved across sessions

## Quick Start

### 1. Install a Vision Model

First, ensure you have a vision-capable model installed on your Ollama server:

```bash
# Install llava (recommended for general use)
ollama pull llava

# Or install other vision models
ollama pull bakllava          # Optimized for speed
ollama pull llava-llama3      # Based on Llama 3
ollama pull cogvlm            # Strong visual understanding
ollama pull moondream         # Lightweight option
```

### 2. Using Image Analysis

Once you have a vision model installed, you can start analyzing images immediately:

```bash
# Start the client
ollmcp

# In the chat, ask about an image
You: What's in the image at screenshots/error.png?
AI: [Analyzes the image and describes what it sees]

# Or use delegation
d analyze the diagram at docs/architecture.png and explain it
```

## Vision Model Management

### List Available Vision Models

Use the `list-vision-models` command to see all vision-capable models on your server:

```
lvm
```
or
```
list-vision-models
```

**Output example:**
```
Vision-Capable Models on Ollama Server:

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Model Name        ┃ Size   ┃ Modified   ┃ Current ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ llava:latest      │ 4.7 GB │ 2025-01-10 │    ✓    │
│ bakllava:latest   │ 4.4 GB │ 2025-01-05 │         │
│ llava-llama3      │ 5.2 GB │ 2024-12-20 │         │
└───────────────────┴────────┴────────────┴─────────┘

Use 'set-vision-model' or 'svm' to select a model
```

### Set Preferred Vision Model

Use the `set-vision-model` command to choose which model to use for image analysis:

```
svm
```
or
```
set-vision-model
```

**Interactive selection:**
```
Available Vision Models:
  1. llava:latest
  2. bakllava:latest
  3. llava-llama3

Enter model number (or model name), or 'c' to cancel: 1

✓ Vision model set to: llava:latest
This model will be used for all image analysis tasks
```

## The `builtin.read_image` Tool

### Tool Description

The `builtin.read_image` tool is automatically available as a built-in tool. It handles:
- Image path validation and security
- Image format detection
- Base64 encoding
- Vision model selection (auto or configured)
- API communication with Ollama

### Tool Parameters

```json
{
  "name": "builtin.read_image",
  "description": "Analyze an image using a vision model",
  "parameters": {
    "image_path": {
      "type": "string",
      "required": true,
      "description": "Path to the image file (relative to current directory)"
    },
    "prompt": {
      "type": "string",
      "required": false,
      "description": "Question or instruction about the image",
      "default": "Describe what you see in this image in detail."
    }
  }
}
```

### How It Works

1. **Path Validation**: Ensures the image path is safe and within the working directory
2. **Format Check**: Validates the file is a supported image format
3. **Base64 Encoding**: Converts the image to base64 for API transmission
4. **Model Selection**:
   - Checks for user-configured vision model in config
   - If not configured, auto-detects first available vision model
   - Verifies the model exists on the Ollama server
5. **API Call**: Sends the image and prompt to Ollama's `/api/generate` endpoint
6. **Response**: Returns the vision model's analysis

## Agent Integration

Three agents have been updated to support image analysis:

### EXECUTOR Agent
- Can analyze images as part of command execution tasks
- Useful for processing multiple images with bash/Python scripts
- Example: "Use Python to list all PNG files and analyze each one"

### READER Agent
- Can analyze images when reading and understanding codebases
- Useful for examining screenshots of errors or UI
- Example: "Read the codebase and analyze the error screenshot"

### RESEARCHER Agent
- Can analyze diagrams, screenshots, and charts when researching
- Useful for understanding architecture diagrams or data visualizations
- Example: "Research the project architecture and analyze the diagram at docs/arch.png"

## Usage Examples

### Basic Image Analysis

```
You: What's in the image at test.png?
AI: [Uses builtin.read_image to analyze and responds]
```

### Error Screenshot Analysis

```
You: I'm getting an error. Can you check screenshots/error.png and tell me what's wrong?
AI: [Analyzes the error screenshot and provides diagnosis]
```

### Diagram Understanding

```
You: Explain the system architecture shown in docs/architecture-diagram.png
AI: [Analyzes the diagram and provides detailed architectural explanation]
```

### Chart Data Extraction

```
You: Read the chart at reports/sales-2024.jpg and summarize the key trends
AI: [Extracts data from chart and provides analysis]
```

### Multi-Image Analysis via Delegation

```bash
# Use delegation for complex multi-image tasks
d scan the screenshots directory, analyze each image, and create a summary report
```

### Batch Processing

```
You: Find all PNG files in the test-results directory and analyze each one for failures
AI: [Uses EXECUTOR to list files, then analyzes each image]
```

## Supported Vision Models

The tool automatically detects these vision model families:

- **llava** - General-purpose vision model (recommended)
- **llava-llama3** - Based on Llama 3 architecture
- **llava-phi3** - Based on Phi-3, optimized for efficiency
- **bakllava** - Optimized for speed
- **cogvlm** - Strong visual understanding
- **cogvlm2** - Improved version of CogVLM
- **moondream** - Lightweight, fast inference
- **minicpm-v** - Efficient multi-modal model
- **obsidian** - Specialized vision model

### Model Selection Strategy

**Auto-Detection Algorithm:**
1. Checks if user has configured a preferred model
2. If configured, validates it exists and uses it
3. If not configured, searches for models containing vision keywords
4. Uses the first available vision model found
5. Returns error if no vision models are available

**Recommended Models:**
- **For accuracy**: `llava:latest` or `cogvlm`
- **For speed**: `bakllava:latest` or `moondream`
- **For efficiency**: `llava-phi3` or `minicpm-v`

## Supported Image Formats

The following image formats are supported:
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- GIF (`.gif`)
- BMP (`.bmp`)
- WEBP (`.webp`)

## Configuration

### Vision Model Setting

The vision model preference is stored in `~/.config/ollmcp/config.json`:

```json
{
  "vision_model": "llava:latest",
  "model": "qwen2.5:7b",
  ...
}
```

### Configuration Commands

- `save-config` (sc): Saves current configuration including vision model
- `load-config` (lc): Loads configuration including vision model preference
- `reset-config` (rc): Resets to defaults (clears vision model preference)

## Security Considerations

### Path Validation

The tool includes security measures to prevent unauthorized file access:
- Only accepts relative paths (no absolute paths)
- Validates paths stay within the working directory
- Prevents path traversal attacks (e.g., `../../../etc/passwd`)
- Checks file existence before reading

### Safe Usage

```bash
# ✅ Safe - relative path within project
analyze image.png

# ✅ Safe - subdirectory
analyze screenshots/error.png

# ❌ Blocked - absolute path
analyze /etc/passwd

# ❌ Blocked - path traversal
analyze ../../../secret.png
```

## Troubleshooting

### No Vision Models Found

**Error:**
```
Error: No vision-capable model found on Ollama server.
Please install a vision model like 'llava' using: ollama pull llava
```

**Solution:**
Install a vision model:
```bash
ollama pull llava
```

### Configured Model Not Found

**Error:**
```
Error: Configured vision model 'llava:13b' not found on Ollama server.
```

**Solutions:**
1. Install the missing model: `ollama pull llava:13b`
2. Select a different model: `svm`
3. Remove the configuration to use auto-detection: `reset-config`

### Image File Not Found

**Error:**
```
Error: Image file 'screenshot.png' does not exist.
```

**Solution:**
- Check the file path is correct
- Ensure the path is relative to your current working directory
- Verify the file exists: `ls screenshot.png`

### Unsupported Image Format

**Error:**
```
Error: 'image.tiff' does not appear to be a supported image file.
Supported formats: .png, .jpg, .jpeg, .gif, .bmp, .webp
```

**Solution:**
Convert the image to a supported format:
```bash
convert image.tiff image.png
```

### Connection Error

**Error:**
```
Error: Failed to connect to Ollama server at http://localhost:11434.
Make sure Ollama is running.
```

**Solution:**
1. Start Ollama: `ollama serve`
2. Check Ollama is running: `ollama list`
3. Verify OLLAMA_HOST environment variable if using custom host

## Performance Considerations

### Image Size

Large images will take longer to process:
- **Small images (<1MB)**: Fast analysis (2-5 seconds)
- **Medium images (1-5MB)**: Moderate speed (5-15 seconds)
- **Large images (>5MB)**: Slower processing (15-30+ seconds)

**Optimization tip:** Resize images before analysis if full resolution isn't needed:
```bash
convert large-image.png -resize 1920x1080 optimized-image.png
```

### Model Performance

Different models have different performance characteristics:

| Model | Speed | Accuracy | Memory | Best For |
|-------|-------|----------|--------|----------|
| moondream | ⚡⚡⚡ | ⭐⭐ | 2GB | Quick scans |
| bakllava | ⚡⚡ | ⭐⭐⭐ | 4GB | Balanced use |
| llava | ⚡ | ⭐⭐⭐⭐ | 5GB | Detailed analysis |
| cogvlm | ⚡ | ⭐⭐⭐⭐⭐ | 7GB | Complex visuals |

## Integration with Agent Delegation

### Using with Delegation

The agent delegation system can leverage image analysis for complex workflows:

```bash
# Example: Analyze all screenshots in a directory
d list all PNG files in screenshots, analyze each image, and create a markdown report with findings

# Example: Bug analysis workflow
d read the error log, analyze the screenshot at debug.png, and suggest fixes

# Example: Documentation generation
d scan all diagram images in docs/, analyze each, and generate a documentation summary
```

### Multi-Agent Workflows

**Scenario: Complete bug report analysis**

```
User: d analyze the bug report workflow

PLANNER creates tasks:
1. READER - Read bug report text file
2. EXECUTOR - Analyze screenshot.png using builtin.read_image
3. RESEARCHER - Synthesize findings and suggest solutions

Result: Comprehensive bug analysis with both text and visual context
```

## API Reference

### Vision Model Detection Function

```python
def _detect_vision_models(ollama_url: str) -> List[str]:
    """
    Detect available vision models on Ollama server.

    Args:
        ollama_url: Ollama API endpoint URL

    Returns:
        List of vision model names
    """
```

### Configuration Functions

```python
def get_vision_model() -> Optional[str]:
    """Get configured vision model from config."""

def set_vision_model(model_name: str) -> bool:
    """Set preferred vision model in config."""

def list_vision_models() -> List[Dict]:
    """List all available vision models with metadata."""
```

## Future Enhancements

Potential future improvements:
- [ ] Support for multiple images in a single analysis
- [ ] Image preprocessing options (crop, rotate, enhance)
- [ ] Vision model performance benchmarking
- [ ] OCR-specific optimizations
- [ ] Video frame analysis
- [ ] Real-time camera input support

## See Also

- [Agent Delegation User Guide](agent-delegation-user-guide.md)
- [Auto-Load Configuration](auto_load_configuration.md)
- [Builtin Tools](builtin_file_access_tools.md)

## Support

For issues or questions about multi-modal support:
1. Check this documentation first
2. Review troubleshooting section
3. Open an issue on GitHub with:
   - Ollama version: `ollama version`
   - Vision model: `ollama list | grep llava`
   - Error messages and logs
   - Image format and size

---

**Last Updated**: December 2025
