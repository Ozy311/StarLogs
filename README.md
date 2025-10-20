<div align="center">

![StarLogs Logo](static/starlogs.png)

# StarLogs
### Star Citizen Log Parser & Event Tracker

![Version](https://img.shields.io/badge/version-0.9.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Python](https://img.shields.io/badge/python-3.8+-blue)

**Real-time Star Citizen log monitoring with web dashboard**

*FOR THE CUBE!* 🟨

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Screenshots](#screenshots) • [Development](#development)

</div>

---

## Overview

StarLogs is a comprehensive Star Citizen log parser that monitors your game logs in real-time, tracks combat events, and provides a beautiful web-based dashboard to view your gaming session statistics. Perfect for tracking PvE/PvP kills, deaths, disconnects, and analyzing your gameplay.

## Features

### 🎯 Core Functionality
- **Real-time log monitoring** - Automatically detects and monitors active Star Citizen game logs
- **Event tracking** - PvE kills, PvP kills, deaths, actor stalls, disconnects, and **vehicle destructions**
- **Vehicle destruction tracking** - Monitors ship soft deaths (disabled) and full destructions with automatic crew kill correlation
- **Enhanced event details** - Ship/location extraction, weapon class info, attack direction analysis
- **System information** - Extracts CPU, GPU, RAM, OS details from logs
- **Multi-version support** - Detects and manages multiple game installations (LIVE, PTU, EPTU)

### 🌐 Web Dashboard
- **Live streaming** - Server-Sent Events (SSE) for real-time updates
- **Beautiful UI** - Dark theme with yellow/blue accents matching Star Citizen aesthetics
- **Event filtering** - Toggle visibility for different event types
- **Statistics panel** - Live counters for all event types
- **Log viewer** - Raw log output with auto-scroll
- **Historical browser** - Browse and analyze past gaming sessions from LogBackups
- **HTML export** - Generate standalone HTML reports for offline viewing

### 🖥️ Console Interface (TUI)
- **Rich console** - Text-based UI with real-time stats
- **Process monitoring** - Shows if StarCitizen.exe is running
- **Interactive options** - Press 'O' to configure settings
- **Status indicators** - Real-time event counters and system status

### ⚙️ Advanced Features
- **Multi-drive detection** - Automatically finds Star Citizen installations across all drives
- **Custom paths** - Add non-standard installation locations
- **Port configuration** - Change web server port (default: 3111)
- **Version switching** - Monitor different game environments on the fly
- **Debug mode** - Comprehensive logging for troubleshooting

---

## Installation

### ⚠️ Windows Defender Warning

**IMPORTANT:** Windows Defender may flag the executable as a threat because it is **unsigned** (no code signing certificate). This is a **false positive**.

**The executable is safe.** Source code is fully available in this repository for verification.

**To run the executable:**

1. **When Windows Defender blocks the download:**
   - Click "Show more" → "Keep anyway"
   - Or download from GitHub releases (already verified by GitHub's security)

2. **When Windows Defender quarantines after extraction:**
   - Open **Windows Security** → **Virus & threat protection** → **Protection history**
   - Find the `StarLogs-v0.8.2.zip` or `StarLogs.exe` entry
   - Click **Actions** → **Allow**
   - Or click **Restore** to put it back

3. **To permanently allow (recommended):**
   - Open **Windows Security** → **Virus & threat protection** → **Manage settings**
   - Scroll to **Exclusions** → **Add or remove exclusions**
   - Click **Add an exclusion** → **Folder**
   - Select the extracted `StarLogs` folder

**Why is this happening?**
- The executable is **unsigned** (code signing certificates cost $100-400/year)
- It has network capabilities (Flask web server for dashboard)
- It creates/modifies files (config file)
- Windows flags new/unknown executables from small developers

**Verification:**
- Source code is open and auditable
- Built with Nuitka (compiles Python to C)
- No obfuscation or suspicious code
- [VirusTotal scan results](#) (coming soon)

**Alternative:** Run from Python source (see below) to avoid any warnings.

---

### Requirements
- **Windows 10/11** (Star Citizen is Windows-only)
- **Python 3.8+** (only if running from source)
- **Star Citizen** installed

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Ozy311/StarLogs.git
   cd StarLogs
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run StarLogs**
   ```bash
   python starlogs.py
   ```

4. **Open web dashboard**
   ```
   http://localhost:3111
   ```

### Virtual Environment (Recommended for Development)

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run StarLogs
python starlogs.py
```

---

## Usage

### First Run

On first launch, StarLogs will:
1. Scan all drives for Star Citizen installations
2. Display detected versions (LIVE, PTU, EPTU)
3. Prompt you to select which version to monitor
4. Create a config file (`starlogs_config.json`)
5. Start the web server on port 3111
6. Open the web dashboard automatically

### Console Interface

The TUI console shows:
```
┌─────────────────────────────────────────────┐
│ StarLogs v0.8.0                             │
│ StarCitizen.exe: Running (PID: 12345)       │
│ Game: LIVE (G:\...\Game.log)                │
├─────────────────────────────────────────────┤
│ PvE: 45  PvP: 12  Deaths: 7  Stalls: 2     │
│ Web: http://localhost:3111                  │
└─────────────────────────────────────────────┘

[Q] Quit  [O] Options  [R] Restart
```

**Keyboard Controls:**
- `Q` - Quit application
- `O` - Open options menu (port, debug mode, about)
- `R` - Restart monitoring (reloads config)

### Web Dashboard

#### Main Features

**Header:**
- Logo (starlogs.png)
- Version selector dropdown (switch between LIVE/PTU/EPTU)
- Settings button (⚙️)
- History button (📜)
- Export button (💾)
- **[NEW] WiFi Connection Indicator** - Real-time server status (🟢 Connected / 🔴 Disconnected / 🟡 Connecting)
- **[NEW] Theme Toggle** - Switch between Dark and Light modes
- **[NEW] About Button** - Opens unified About page with donation link
- **[NEW] Mobile Hamburger Menu** - Responsive navigation for small screens

**Event Summary Section:**
- **[NEW] Filter Toggle** - Collapsible "Filters" button to hide/show filter badges
- **[NEW] Invert Button** - Toggle all filter selections with single click
- Clear Events button
- Reprocess Log button
- Event filtering checkboxes for all event types (including vehicle destructions, FPS combat, suicides)
- Statistics panel with real-time counters for:
  - Ship PvE/PvP kills
  - Deaths
  - FPS PvE/PvP kills and FPS deaths
  - Soft Deaths and Full Destructions
  - Disconnects and Actor Stalls
  - Suicides and Corpses

**Event List:**
- Live-updating event feed (newest first)
- Click ▼ on section header to fully collapse/expand widget (frees up space)
- Click individual badges to hide/show specific event types
- Events now include:
  - 📍 Ship/Location (e.g., "890 Jump")
  - 🎯 Weapon & class (e.g., "Ballistic Cannon (S4)")
  - 💥 Damage type (e.g., "Explosion", "Crash")
  - 🧭 Attack direction (e.g., "from Behind", "from Above")
  - 👥 Crew members (click (+N crew) to expand crew details)
  - Victim/Killer IDs

**Raw Log Viewer:**
- **[NEW] Wrap Text Toggle** - Enable/disable text wrapping for long log lines
- Auto-scroll checkbox (remembers preference)
- Clear button
- Live log output with auto-scroll to newest entries

**Controls:**
- **[NEW] Full Widget Collapse** - Clicking section headers collapses entire widget to save space
- **Reprocess Log** - Reparse entire current log file
- **Auto-scroll** - Toggle automatic scrolling for events/logs
- **[NEW] Wrap Text** - Toggle text wrapping in Raw Log Viewer
- **Preferences Persist** - All UI preferences saved to browser localStorage

#### Mobile Responsiveness

**Responsive Breakpoints:**
- **Desktop (> 900px):** All buttons visible, full layout
- **Tablet/Mobile (≤ 900px):** 
  - Header buttons hidden
  - Version selector moved to hamburger menu
  - History/Export buttons moved to hamburger menu
  - Settings button moved to hamburger menu
  - Connection/Theme/About icons remain on far right until ultra-mobile
  - Hamburger menu ☰ appears with flyout options

**Mobile Menu Features:**
- Version selector (with current version display)
- History browser
- Export current log
- Settings
- Clean, touch-friendly layout with icons

#### Settings Menu

**Games Tab:**
- View all detected Star Citizen installations
- Add custom installation paths
- Switch active monitoring version
- Remove custom paths

**General Tab:**
- **[NEW] Theme selector** (Dark/Light mode) - Also accessible from header theme toggle button
- Web server port configuration
- Restart warning for port changes
- **[NEW] Log poll interval** (0.1-10.0 seconds) - Requires restart

**About Tab:**
- **[NEW] Donation section** with PayPal link (https://paypal.me/Ozy311)
- Version information
- Author and organization
- Feature list
- License information

#### Historical Log Browser

**Access:** Click 📜 History button

**Features:**
- Browse LogBackups for any game version
- Sort by date, size, or name
- Quick analysis showing event counts
- View full analysis with:
  - Event statistics (including vehicle destructions, FPS combat)
  - Session uptime
  - System information
  - Build details
  - Event timeline (last 50 events)
- Export to standalone HTML report

**HTML Exports:**
- Self-contained (all styles embedded)
- Dark theme matching main UI
- **[NEW] Vehicle destruction events** with crew details
- **[NEW] FPS combat events** with weapon info
- Includes all event details with icons
- Perfect for sharing sessions with friends

### Configuration File

`starlogs_config.json` stores:
```json
{
  "installations": {
    "LIVE": {
      "path": "G:\\Roberts Space Industries\\StarCitizen\\LIVE",
      "log_path": "G:\\...\\LIVE\\Game.log",
      "version": "LIVE",
      "build_number": "10275505",
      "build_date": "2025-09-19",
      "is_active": true
    }
  },
  "active_version": "LIVE",
  "web_port": 3111,
  "auto_detect": true,
  "custom_installations": [],
  "debug_mode": false
}
```

**Fields:**
- `installations` - Detected game installations
- `active_version` - Currently monitored version
- `web_port` - Web server port (default: 3111)
- `auto_detect` - Enable automatic installation detection
- `custom_installations` - User-added paths
- `debug_mode` - Enable verbose logging to `starlogs_debug.log`

### Event Types

| Event | Description | Details Captured |
|-------|-------------|------------------|
| **PvE Kill** | Player killed NPC (vehicle) | Weapon, damage type, ship/location, direction |
| **PvP Kill** | Player killed player (vehicle) | Weapon, damage type, ship/location, direction |
| **Death** | Player was killed (vehicle) | Killer, damage type, ship/location |
| **FPS PvE Kill** | Player killed NPC on foot | Weapon, location, timestamp |
| **FPS PvP Kill** | Player killed player on foot | Weapon, location, timestamp |
| **FPS Death** | Player was killed on foot | Killer, damage type, location |
| **Soft Death** | Vehicle disabled/crippled (0→1) | Ship name, attacker, damage type, crew count |
| **Destruction** | Vehicle fully destroyed (→2) | Ship name, attacker, damage type, crew count |
| **Suicide** | Player killed themselves | Player name, damage type, timestamp |
| **Corpse** | Player corpse state (death confirmation) | Player name, corpse status |
| **Actor Stall** | Game freeze/crash | Player name, stall type, duration |
| **Disconnect** | Network disconnect | Timestamp, reason |

**Vehicle Destruction System:**
- **Soft Death (Level 0→1)** - Ship disabled but salvageable, orange indicator, crew can potentially survive
- **Full Destruction (Level 1→2 or 0→2)** - Ship exploded and gone, red indicator, crew kills recorded
- **Automatic Crew Correlation** - Links crew member deaths to vehicle destruction events within 200ms timestamp window
- **Vehicle ID Extraction** - Converts vehicle IDs (e.g., "ANVL_Paladin_6763231335005") to ship names
- **Expandable Crew Details** - Click "(+N crew)" in event card to see individual crew member names
- **Damage Type Color Coding:**
  - Combat (red) - Ship-to-ship weapon damage
  - Collision (orange) - Ship collisions or ramming
  - SelfDestruct (purple) - Player-initiated self-destruct
  - GameRules (gray) - Server cleanup/despawn/timeout
- **PvP/PvE Classification** - Distinguishes player-caused destructions from NPC/environment

**FPS Combat Tracking:**
- **FPS PvE (Cyan)** - On-foot kills of NPCs, distinct from vehicle PvE
- **FPS PvP (Purple)** - On-foot player kills, separate counter from vehicle PvP
- **FPS Death (Yellow)** - Deaths while on foot (including suicides)
- **Weapon Details** - Captures weapon names and classifications when available
- **Location Tracking** - Records zone/location for on-foot combat
- **Filterable** - Independent filters for each FPS event type

**Enhanced Details (when available):**
- **Ship/Location** - Extracted from zone strings (e.g., "890 Jump", "Gladius")
- **Weapon Class** - Full weapon classification (ballistic, energy, etc.)
- **Attack Direction** - Calculated from direction vectors (from Left, from Behind, etc.)
- **System Info** - CPU, GPU, RAM, OS, performance index

---

## Screenshots

### Main Dashboard
Real-time monitoring with live event feed and statistics.

![Main Dashboard](docs/screenshots/dashboard-main.png)

### Live Events
Combat events with enhanced details including ship types, weapon info, and attack directions.

![Live Events](docs/screenshots/dashboard-events.png)

### Settings - Games
Manage multiple Star Citizen installations (LIVE, PTU, EPTU) with auto-detection.

![Settings Games](docs/screenshots/settings-games.png)

### Settings - General
Configure theme and web server port.

![Settings General](docs/screenshots/settings-general.png)

### Settings - About
Version information and complete feature list.

![Settings About](docs/screenshots/settings-about.png)

### Historical Log Browser
Browse and analyze past gaming sessions from LogBackups directory.

![History Browser](docs/screenshots/history-browser.png)

### Log Analysis
Detailed analysis with event statistics, session uptime, system specs, and event timeline.

![History Analysis](docs/screenshots/history-analysis.png)

### Vehicle Destruction Tracking (New in v0.9.0)
Real-time vehicle destruction events with automatic crew kill correlation and damage type color coding.

![Vehicle Destruction Events](docs/screenshots/vehicle-destruction-events.png)

### Crew Details Expansion
Click on crew indicators to see individual crew member names from destroyed ships.

![Crew List Expanded](docs/screenshots/vehicle-destruction-crew-expanded.png)

---

## Advanced Usage

### Command-Line Arguments

```bash
# Specify game version
python starlogs.py --version LIVE

# Custom port
python starlogs.py --port 5000

# Debug mode
python starlogs.py --debug

# Multiple options
python starlogs.py --version PTU --port 8080 --debug
```

### Debug Mode

Enable debug logging:
1. Console: Press `O` → Enable Debug Mode
2. Web UI: Settings → General → Enable Debug Mode
3. Command line: `python starlogs.py --debug`

**Debug files:**
- `starlogs_debug.log` - Detailed application logs
- `starlogs_error.log` - Error messages only

### Custom Installation Paths

If StarLogs doesn't detect your installation:

**Via Web UI:**
1. Click ⚙️ Settings
2. Go to Games tab
3. Click "+ Add Custom Path"
4. Enter path to game directory (e.g., `E:\Games\StarCitizen\LIVE`)
5. Click "Validate Path"
6. If valid, click "Add & Monitor"

**Via Config:**
Edit `starlogs_config.json` and add to `custom_installations`:
```json
"custom_installations": [
  "E:\\Games\\StarCitizen\\LIVE"
]
```

### Multi-Version Setup

To monitor multiple versions:
1. StarLogs automatically detects LIVE, PTU, EPTU
2. Use version dropdown to switch between them
3. Each version maintains separate statistics
4. History browser shows logs for selected version

---

## Development

### Project Structure

```
StarLogs/
├── starlogs.py              # Main entry point
├── web_server.py            # Flask web server & API
├── log_monitor.py           # Real-time log file monitoring
├── event_parser.py          # Event pattern matching & parsing
├── game_detector.py         # Star Citizen installation detection
├── config_manager.py        # Configuration management
├── tui_console.py           # Text-based console interface
├── process_monitor.py       # Game process detection
├── offline_analyzer.py      # Historical log analysis
├── html_generator.py        # Static HTML report generation
├── version.py               # Version information
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore patterns
├── LICENSE                 # MIT License
├── README.md               # This file
├── static/                 # Web assets
│   ├── app.js             # Dashboard JavaScript
│   ├── style.css          # Main styles
│   ├── history.css        # History browser styles
│   └── starlogs.png       # Logo
└── templates/             # HTML templates
    └── index.html        # Dashboard template
```

### Building Executable (Windows)

StarLogs uses **Nuitka** as the primary build tool (recommended for releases), with **PyInstaller** available as an alternative for single-executable preference.

**Why two build options?**
- **Nuitka (Primary):** Compiles Python to native C code, fewer antivirus false positives vs PyInstaller, better performance
- **PyInstaller (Alternative):** Produces single `.exe` file (no extracted dependencies), but higher false positive rates on unsigned executables

#### Requirements

**For Nuitka:**
- Python 3.13
- Visual Studio Build Tools (C++ compiler)
- Nuitka: `pip install nuitka`

**For PyInstaller:**
- Python 3.8+
- PyInstaller: `pip install pyinstaller`

#### Build with Nuitka (Recommended)

```bash
# Run the Nuitka build script
build_nuitka.bat

# Output directory structure
dist\nuitka\
  ├── StarLogs.exe       # Main executable
  ├── *.dll              # Required libraries
  ├── static\            # Web assets
  └── templates\         # HTML templates
```

**Distribution:** Package the entire `dist\nuitka\` folder. Users can run `StarLogs.exe` directly. Config saves alongside the executable.

#### Build with PyInstaller (Alternative)

```bash
# Run the PyInstaller build script
build_pyinstaller.bat

# Output
dist\pyinstaller\StarLogs.exe  # Single executable (~80MB, self-extracting)
```

**Distribution:** Single file, no dependencies to package. **However, note:**
- Unsigned PyInstaller executables often trigger higher antivirus false positive rates
- Users may see "Windows Defender" warnings more frequently
- Recommend shipping Nuitka build for public releases
- PyInstaller useful for custom/private builds

#### Why Nuitka?

- Compiles Python to native C code (faster execution)
- Significantly fewer antivirus false positives vs PyInstaller
- Better compatibility with Rich TUI library
- More stable with onfile extractions
- Recommended for public releases

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Development Guidelines:**
- Follow PEP 8 style guide
- Add docstrings to all functions
- Update documentation for new features
- Test with multiple SC versions (LIVE, PTU)
- Include the tagline "FOR THE CUBE!" in feature docs 🟨

---

## Troubleshooting

### StarLogs won't start
- Check Python version: `python --version` (requires 3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port availability: Another app might be using port 3111

### Game installation not detected
- Verify Star Citizen is installed
- Check installation path contains `StarCitizen\LIVE` folder
- Add custom path via Settings → Games → Add Custom Path

### Events not showing
1. Ensure Star Citizen is running
2. Check correct version is selected (LIVE vs PTU)
3. Click "Reprocess Log" button
4. Verify log file exists: `StarCitizen\LIVE\Game.log`

### Web dashboard not loading
- Check console for errors
- Verify web server started (look for "Running on http://...")
- Try different browser
- Check firewall isn't blocking port 3111

### "Port already in use" error
1. Change port via TUI: Press `O` → Change Port
2. Or edit `starlogs_config.json`: Change `web_port` value
3. Restart StarLogs

---

## Known Issues

### Version 0.9.0 Focus Areas

The following items are known and under active investigation for the next release (v0.9.1):

1. **NPC Classification (NEW in 4.3.2+)** - Some newly added NPCs in Star Citizen 4.3.2 and later are not yet recognized by the pattern database, potentially causing them to be flagged as PvP kills instead of PvE.
   - **Workaround:** Check event details for killer/victim names; report unrecognized NPCs on GitHub
   - **Status:** Pattern database being updated for latest NPCs

2. **Event Parser Edge Cases** - Some legitimate combat events are occasionally missed due to minor log format variations or regex pattern mismatches.
   - **Status:** Refining regex patterns for comprehensive log coverage

### Troubleshooting

#### "Port already in use" error
1. Another StarLogs instance is running
2. Use `netstat -ano | findstr :8080` (Windows) to find process
3. Terminate the process or choose a different port in Settings

#### Connection shows "Disconnected"
1. Check that StarLogs server is running (check TUI console)
2. Verify port is correct (default: 3111)
3. Check Windows Firewall isn't blocking the connection
4. Try restarting refreshing browser
5. Restart StarLogs server

#### Events not showing
1. Ensure Star Citizen is running
2. Check correct version is selected (LIVE vs PTU)
3. Click "Reprocess Log" button
4. Verify log file exists: `StarCitizen\LIVE\Game.log`
5. Check Connection indicator shows "Connected" (green)

#### Web dashboard not loading
1. Check browser console for errors
2. Verify web server started (look for "Running on http://...")
3. Try a different browser
4. Clear browser cache (`Ctrl+Shift+Delete`)

---

## Changelog

### Version 0.9.0 (2025-10-19) - Vehicle Destruction System & UI Redesign

See [CHANGELOG_0.9.0.md](.cursor/docs/CHANGELOG_0.9.0.md) for comprehensive v0.9.0 release notes including all features, technical details, and upgrade instructions.

**Highlights:**
- ✨ Vehicle destruction tracking (Soft Death & Full Destruction)
- 🔗 Automatic crew kill correlation
- 🎨 New header icons (WiFi, Theme, About)
- 📱 Mobile responsive hamburger menu
- 🎯 Enhanced FPS combat tracking
- 💾 Filter preferences persistence
- ⚡ Performance optimizations with polling-based log monitoring

### Version 0.8.2 (Previous)
- Event detail enhancements
- Historical log browser improvements
- UI refinements and bug fixes

### Version 0.8.0
- Historical log browser
- HTML export functionality
- Settings management overhaul
- Multi-version support improvements

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **CIG (Cloud Imperium Games)** - For creating Star Citizen
- **CUBE Organization** - For motivation and testing
- **Star Citizen Community** - For feedback and support

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Ozy311/StarLogs/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Ozy311/StarLogs/discussions)

---

<div align="center">

**Made with ❤️ by Ozy311**

*FOR THE CUBE!* 🟨

</div>
