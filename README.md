# 🧠 AimBrain — AI-Powered Fortnite Agent

> **Let AI play Fortnite.** A modular, remote-controlled game agent with 35+ combat/building/looting macros and an HTTP API. Now with **DonClaw Node** integration for zero-screenshot OCR-based control.

![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows)

---

## What is this?

AimBrain is a two-part system with two operating modes:

### Local Mode (original)
Runs directly on your gaming PC with pyautogui + mss for screenshots and input.

### DonClaw Mode (recommended) 🆕
Routes all input through **DonClaw Node** running on the gaming PC. Uses **OCR text instead of screenshots** — the AI reads text, not images. 50x faster processing.

```
┌──────────────────┐    HTTP/JSON     ┌──────────────────┐    HTTP/JSON     ┌──────────────┐
│    AI / LLM      │ ◄────────────► │   AimBrain API   │ ◄────────────► │  DonClaw Node │
│  (any device)    │  OCR text +    │   (NUC/server)   │  OCR + input   │  (gaming PC)  │
│                  │  macros        │   port 9777      │                │  port 9800    │
└──────────────────┘                └──────────────────┘                └──────────────┘
```

**Key rule: In DonClaw mode, NEVER use screenshots. OCR text only.**

---

## 📁 Project Structure

```
aimbrain/
├── __init__.py          # Package metadata + version
├── __main__.py          # python -m aimbrain entry point
├── config.py            # Config loading, runtime updates, singleton
├── donclaw.py           # 🆕 DonClaw Node adapter (OCR, input, sequences)
├── input.py             # Dual-backend: DonClaw or local pyautogui
├── screenshot.py        # JPEG capture (local) or OCR proxy (DonClaw)
├── server.py            # Threaded HTTP server, all endpoints
├── client.py            # Python SDK for remote control
└── macros/
    ├── __init__.py      # Macro registry (auto-collects all submodules)
    ├── combat.py        # Shooting, aiming, peeking, weapon combos
    ├── building.py      # Walls, ramps, boxes, 90s, edits
    ├── movement.py      # Movement patterns (zigzag, explore, evasive)
    ├── looting.py       # Pickup, chests, harvesting, area sweeps
    └── utility.py       # Camera, weapons, heal, emergency, disengage

controller.py            # CLI tool: command the agent from terminal
config.json              # User-editable settings + keybinds + DonClaw config
```

---

## ⚡ Key Features

### DonClaw Integration 🆕
- **Zero screenshots** — OCR text only, no images sent to AI
- **OCR in ~200ms** — local text recognition on the gaming PC
- **Smart click** — `/act` finds text and clicks it in one call
- **Sequences** — chain multiple actions atomically
- **Remote control** — AimBrain runs on your NUC/server, DonClaw on gaming PC

### 35+ Game Macros

| Category | Macros |
|----------|--------|
| **Combat** | `shoot` `aim_shoot` `tap_shoot` `spray` `burst_spray` `jump_shot` `strafe_shoot` `ads_strafe` `shotgun_flick` `double_pump` `quick_scope` `crouch_peek` `peek_right` `peek_left` `swap_shoot` |
| **Building** | `build` `build_cover` `build_cover_ramp` `ramp_rush` `protected_ramp` `wall_ramp` `90s` `edit_reset` `edit_wall` |
| **Looting** | `pickup` `loot_area` `loot_sweep` `open_chest` `harvest` |
| **Movement** | `move` (7 patterns: `zigzag` `circle` `strafe_random` `sprint_forward` `sprint_jump` `explore` `evasive`) `drop_in` |
| **Utility** | `look` `smooth_look` `switch_weapon` `pickaxe` `reload` `heal` `emergency` `disengage` |

All macros work transparently through either backend (local or DonClaw).

---

## 🚀 Quick Start

### DonClaw Mode (recommended)

**Prerequisites:** DonClaw Node running on your gaming PC (port 9800).

#### 1. Clone and configure

```bash
git clone https://github.com/lucast1574/aimbrain.git
cd aimbrain
pip install -r requirements.txt
```

Edit `config.json`:
```json
{
  "donclaw": {
    "enabled": true,
    "host": "http://GAMING_PC_IP:9800",
    "timeout": 10
  }
}
```

#### 2. Start the agent (on NUC/server)

```bash
python -m aimbrain
```

#### 3. Use it

```bash
# Check DonClaw connection
python controller.py --donclaw-status

# Read screen text (no screenshots!)
python controller.py --ocr

# Find text on screen
python controller.py --find "Play"

# Click on text
python controller.py --act "Play"

# Run macros (routed through DonClaw)
python controller.py --macro aim_shoot --params '{"duration": 500}'
```

#### 4. Python SDK with DonClaw

```python
from aimbrain.client import AimBrain

bot = AimBrain("http://NUC_IP:9777")

# Read screen (OCR text, no images!)
text = bot.ocr()
print(text)

# Find and click text
bot.find("Play")
bot.act("Play")

# Chain DonClaw actions
bot.donclaw_sequence([
    {"action": "focus", "name": "fortnite"},
    {"action": "wait", "ms": 1000},
    {"action": "find_click", "text": "Play", "smooth": True},
])

# Macros still work (routed through DonClaw input)
bot.aim_shoot(duration=400)
bot.build_cover()
bot.explore(duration=3000)
```

### Local Mode (original)

Set `"donclaw": {"enabled": false}` in config.json to use local pyautogui/mss.
See original setup instructions below.

#### 1. Install on your gaming PC (Windows)

```bash
pip install -r requirements.txt
python -m aimbrain
```

#### 2. Control from anywhere

```bash
python controller.py --host http://GAMING_PC_IP:9777 --ping
python controller.py --screenshot screen.jpg
python controller.py --macro aim_shoot --params '{"duration": 500}'
```

---

## 🔌 API Reference

### GET Endpoints

| Endpoint | DonClaw | Description |
|----------|---------|-------------|
| `/ping` | ✅ | Health check + backend info |
| `/ocr` | ✅ only | Get all screen text as JSON (no screenshots!) |
| `/find?q=text` | ✅ only | Find text on screen + coordinates |
| `/donclaw/status` | ✅ only | DonClaw Node health check |
| `/screenshot` | local only | Full screen JPEG (or OCR JSON in DonClaw mode) |
| `/screenshot/region` | local only | Region crop JPEG |
| `/macros` | ✅ | List all macro names |
| `/binds` | ✅ | Current key bindings |
| `/stats` | ✅ | Performance stats + backend info |
| `/config` | ✅ | Current settings |
| `/mouse` | ✅ | Cursor position |
| `/screen_size` | ✅ | Monitor dimensions |
| `/monitors` | local only | All monitors |

### POST Endpoints

| Endpoint | DonClaw | Description |
|----------|---------|-------------|
| `/act` | ✅ only | Find text + smart click (OCR-based) |
| `/donclaw/sequence` | ✅ only | Chain DonClaw actions |
| `/macro` | ✅ | Execute one macro |
| `/macro_sequence` | ✅ | Chain macros |
| `/keys` | ✅ | Batch raw input actions |
| `/key` | ✅ | Single key press/hold |
| `/click` | ✅ | Mouse click |
| `/move` | ✅ | Mouse move |
| `/mousedown` / `/mouseup` | ✅ | Hold/release mouse |
| `/focus` | ✅ | Focus window (DonClaw or PowerShell) |
| `/release_all` | ✅ | Safety: release all held keys |
| `/binds` | ✅ | Update keybinds |
| `/config` | ✅ | Update settings |

---

## ⚙️ Configuration

```json
{
  "port": 9777,
  "monitor": 0,
  "screenshot_quality": 45,
  "screenshot_scale": 0.5,
  "screenshot_cache_ms": 50,
  "log_requests": false,
  "donclaw": {
    "enabled": true,
    "host": "http://192.168.18.6:9800",
    "timeout": 10
  },
  "binds": {
    "forward": "w",
    "build_wall": "z",
    "..."
  }
}
```

---

## 🤖 AI Integration Example (DonClaw Mode)

```python
import json
import openai
from aimbrain.client import AimBrain

bot = AimBrain("http://NUC_IP:9777")
client = openai.OpenAI()

while True:
    # Read screen as TEXT, not image
    screen_text = json.dumps(bot.ocr(), indent=2)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content":
                f"You are playing Fortnite. Here is the screen text (OCR):\n\n"
                f"{screen_text}\n\n"
                f"Respond with a JSON macro: {{\"name\": \"macro_name\", \"params\": {{...}}}}"
        }],
        max_tokens=200,
    )

    action = json.loads(response.choices[0].message.content)
    bot.macro(action["name"], **action.get("params", {}))
```

---

## ⚠️ Disclaimer

This project is for **educational and research purposes**. Using automation tools in online games may violate terms of service. Use responsibly and at your own risk.

---

## License

MIT — do whatever you want with it.
