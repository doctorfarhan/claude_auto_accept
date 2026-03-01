# Claude CLI Auto-Proceed for Cmder

Automatic confirmation handling for Claude Code CLI within Cmder terminal emulator.

## What This Does

This Cmder plugin automatically monitors your console and detects Claude Code CLI's "Do you want to proceed?" prompts, automatically accepting them by sending an Enter keypress. This creates a seamless, uninterrupted workflow when using Claude Code in Cmder.

### How It Works

The automation consists of two files that work together:

1. **`config/profile.d/claude_auto_accept.cmd`** - Startup script that launches the monitor automatically whenever Cmder opens
2. **`bin/claude_auto_accept.py`** - Python background process that:
   - Monitors the visible console screen buffer in real-time
   - Detects Claude Code's confirmation prompts ("Do you want to proceed?")
   - Automatically sends Enter keypress to accept (since "Yes" is selected by default)
   - Runs silently in the background with cooldown protection to prevent spam

## Installation

### Prerequisites

- **Cmder**
- **Python**
- **Claude Code CLI**

### Adding to Existing Cmder Installation

1. **Copy the Python script:**

   - Copy `claude_auto_accept.py` to `<your-cmder-root>/bin/`

2. **Copy the startup script:**

   - Copy `claude_auto_accept.cmd` to `<your-cmder-root>/config/profile.d/`

   > **Note:** The `profile.d` directory may not exist in older Cmder installations. Create it if needed:

3. **Restart Cmder**
   - Close all Cmder windows and reopen
   - The auto-accept plugin will activate automatically

### Troubleshooting

**Plugin not loading:**

- Verify Python is in your PATH: `where python`
- Check that both files exist in the correct locations
- Check Cmder's config for any conflicting settings

**Still seeing prompts:**

- The monitor has a 3-second cooldown between accepts
- Ensure the console window is focused and visible
- Check that you're using the standard Claude Code CLI

**Multiple instances:**

- The script uses console window locking to prevent multiple instances
- Each Cmder window gets its own monitor instance
- Lock files are stored in `%TEMP%` directory

## Uninstallation

To remove the auto-accept functionality:

1. Delete `<cmder-root>/config/profile.d/claude_auto_accept.cmd`
2. Delete `<cmder-root>/bin/claude_auto_accept.py`

## Configuration

### Customizing Detection

The Python script can be modified to detect additional prompts. Edit the `PROMPTS` list in `claude_auto_accept.py`:

```python
PROMPTS = [
    {
        "trigger": "Do you want to proceed?",
        "confirm": ["Yes", "No"],
    },
    # Add more prompt patterns here
]
```

### Adjusting Timing

You can adjust the monitoring behavior in the `main()` function:

```python
COOLDOWN = 3        # seconds after an accept before looking again
POLL     = 0.5      # seconds between screen reads
SETTLE   = 0.3      # seconds to wait after detection before sending key
```

## ⚠️ Disclaimers

### Important Warnings

**Automatic Acceptance Risk**

- This tool automatically accepts ALL "Do you want to proceed?" prompts from Claude Code CLI
- You will NOT be asked for confirmation before actions are executed
- Review Claude's planned actions carefully BEFORE they trigger the prompt
- This tool is designed for trusted workflows where you're confident in Claude's actions

**No Liability**

- This automation is provided AS-IS without any warranties
- Use at your own risk
- Always maintain backups of important work
- This is intended for personal development environments, not production systems

---
