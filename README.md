# 🧠 AimBrain — AI-Powered Fortnite Agent

> **Let AI play Fortnite.** A modular, remote-controlled game agent with fast screen capture, 35+ combat/building/looting macros, and an HTTP API designed for vision-model integration.

![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows)

---

## What is this?

AimBrain is a two-part system:

1. **Agent** (`aimbrain/`) — Runs on your gaming PC. Captures screenshots at high speed (JPEG, ~50ms), accepts mouse/keyboard commands, and exposes **35+ game-aware macros** over a local HTTP API.

2. **Client SDK** (`aimbrain/client.py`) — Runs anywhere on your network. Python SDK + CLI to command the agent. Feed screenshots to GPT-4 Vision, Claude, or any model and translate decisions into macros.

```
┌──────────────┐    HTTP/JSON     ┌──────────────┐
│    Client     │ ◄────────────► │    Agent      │
│  (any device) │  screenshots   │  (gaming PC)  │
│  AI / LLM     │  + macros      │  pyautogui    │
└──────────────┘                 └──────────────┘
```

---

## 📁 Project Structure

```
aimbrain/
├── __init__.py          # Package metadata + version
├── __main__.py          # python -m aimbrain entry point
├── config.py            # Config loading, runtime updates, singleton
├── input.py             # Low-level mouse/keyboard (Win32 + pyautogui)
├── screenshot.py        # Fast JPEG capture, caching, region crops
├── server.py            # Threaded HTTP server, all endpoints
├── client.py            # Python SDK for remote control
└── macros/
    ├── __init__.py      # Macro registry (auto-collects all submodules)
    ├── combat.py        # Shooting, aiming, peeking, weapon combos
    ├── building.py      # Walls, ramps, boxes, 90s, edits
    ├── movement.py      # Movement patterns (zigzag, explore, evasive)
    ├── looting.py       # Pickup, chests, harvesting, area sweeps
    └── utility.py       # Camera, weapons, heal, emergency, disengage

agent.py                 # Thin entry: starts the server
controller.py            # CLI tool: command the agent from terminal
config.json              # User-editable settings + keybinds
requirements.txt
```

Each module has a **single responsibility**:
- **config** handles all settings — no globals scattered around
- **input** is the only module that touches pyautogui/ctypes
- **screenshot** is the only module that touches mss/PIL
- **macros/** each file is one gameplay domain — easy to add new ones
- **server** wires everything together into HTTP endpoints

---

## ⚡ Key Features

### Performance
- **JPEG screenshots** — 45% quality + 0.5x scale = ~15-30KB per frame
- **50ms screenshot cache** — no redundant grabs
- **Win32 direct input** — bypasses pyautogui for mouse via `ctypes`
- **Threaded HTTP** — concurrent requests, no blocking
- **Batch endpoints** — 20 actions in 1 request via `/keys` or `/macro_sequence`
- **Zero pause** — `pyautogui.PAUSE = 0` globally

### 35+ Game Macros

| Category | Macros |
|----------|--------|
| **Combat** | `shoot` `aim_shoot` `tap_shoot` `spray` `burst_spray` `jump_shot` `strafe_shoot` `ads_strafe` `shotgun_flick` `double_pump` `quick_scope` `crouch_peek` `peek_right` `peek_left` `swap_shoot` |
| **Building** | `build` `build_cover` `build_cover_ramp` `ramp_rush` `protected_ramp` `wall_ramp` `90s` `edit_reset` `edit_wall` |
| **Looting** | `pickup` `loot_area` `loot_sweep` `open_chest` `harvest` |
| **Movement** | `move` (7 patterns: `zigzag` `circle` `strafe_random` `sprint_forward` `sprint_jump` `explore` `evasive`) `drop_in` |
| **Utility** | `look` `smooth_look` `switch_weapon` `pickaxe` `reload` `heal` `emergency` `disengage` |

### Pre-Built Combat Sequences
```python
bot.land_and_loot()                        # Dive fast → sweep loot
bot.fight_sequence(weapon_slot=1)          # Weapon → cover → peek shoot
bot.push_enemy(ramps=3, weapon_slot=1)     # Wall-ramp rush → swap → fire
bot.box_fight_peek(direction="right")      # Box up → peek → reset
```

---

## 🚀 Quick Start

### 1. Install on your gaming PC (Windows)

```bash
git clone https://github.com/lucast1574/aimbrain.git
cd aimbrain
pip install -r requirements.txt
```

### 2. Start the agent

```bash
# Option A: entry script
python agent.py

# Option B: module
python -m aimbrain
```

### 3. Control from anywhere

```bash
# CLI
python controller.py --host http://YOUR_PC_IP:9777 --ping
python controller.py --screenshot screen.jpg
python controller.py --macros
python controller.py --macro aim_shoot --params '{"duration": 500}'
python controller.py --stats
python controller.py --release
```

### 4. Python SDK

```python
from aimbrain.client import AimBrain

bot = AimBrain("http://192.168.1.100:9777")

# Screenshots
img = bot.screenshot()              # Raw JPEG bytes
img_b64 = bot.screenshot_b64()      # Base64 for LLM APIs

# Combat
bot.switch_weapon(1)
bot.aim_shoot(duration=400)
bot.tap_fire(count=5)
bot.build_cover()

# Movement
bot.explore(duration=3000)
bot.zigzag(duration=2000)
bot.evade(duration=2000)

# Complex plays
bot.push_enemy(ramps=3, weapon_slot=1)
bot.box_fight_peek(direction="right")

# Safety
bot.release_all()
```

---

## 🔌 API Reference

### GET Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ping` | Health check (`{"ok": true, "version": "3.0.0", "ts": ...}`) |
| `/screenshot` | Full screen JPEG. Query: `?quality=45&scale=0.5&monitor=0` |
| `/screenshot/region` | Region crop. Query: `?x=0&y=0&w=400&h=200&quality=70` |
| `/screen_size` | Monitor dimensions |
| `/mouse` | Current cursor position |
| `/macros` | List all macro names + count |
| `/binds` | Current key bindings |
| `/stats` | Performance stats (screenshots, macros, uptime, idle) |
| `/config` | Current settings (without binds) |
| `/monitors` | All monitors with dimensions |

### POST Endpoints

| Endpoint | Body | Description |
|----------|------|-------------|
| `/macro` | `{"name": "aim_shoot", "params": {"duration": 300}}` | Execute one macro |
| `/macro_sequence` | `{"steps": [{"name": "...", "params": {}, "wait_ms": 0}]}` | Chain macros |
| `/keys` | `{"actions": [{"type": "key", "key": "w", "duration": 1000}]}` | Batch raw input |
| `/key` | `{"key": "space", "duration": 0}` | Single key press/hold |
| `/click` | `{"x": 960, "y": 540, "button": "left"}` | Mouse click |
| `/move` | `{"dx": 100, "dy": 0}` or `{"x": 960, "y": 540}` | Mouse move |
| `/mousedown` / `/mouseup` | `{"button": "left"}` | Hold/release mouse |
| `/focus` | `{}` | Focus the Fortnite window |
| `/release_all` | `{}` | **Safety:** release all held keys + buttons |
| `/binds` | `{"forward": "w"}` | Update keybinds at runtime |
| `/config` | `{"screenshot_quality": 60}` | Update settings at runtime |

---

## ⚙️ Configuration

Edit `config.json`:

```json
{
  "port": 9777,
  "monitor": 0,
  "screenshot_quality": 45,
  "screenshot_scale": 0.5,
  "screenshot_cache_ms": 50,
  "log_requests": false,
  "binds": {
    "forward": "w",
    "build_wall": "z",
    "..."
  }
}
```

Config and binds can also be updated at runtime via API — no restart needed.

---

## 🤖 AI Integration Example

```python
import json
import openai
from aimbrain.client import AimBrain

bot = AimBrain("http://192.168.1.100:9777")
client = openai.OpenAI()

while True:
    img_b64 = bot.screenshot_b64(quality=40, scale=0.4)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text":
                    "You are playing Fortnite. Analyze the screen and respond with "
                    "a JSON macro: {\"name\": \"macro_name\", \"params\": {...}}"},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        }],
        max_tokens=200,
    )

    action = json.loads(response.choices[0].message.content)
    bot.macro(action["name"], **action.get("params", {}))
```

---

## 🧩 Adding Custom Macros

1. Pick the right file in `aimbrain/macros/` (or create a new one)
2. Write your function using primitives from `aimbrain.input`
3. Add it to the module's `MACROS` dict
4. It's automatically available via the API — no other changes needed

```python
# aimbrain/macros/combat.py

def my_combo():
    """My custom combo."""
    key_down("sprint")
    shoot(200)
    key_up("sprint")

MACROS["my_combo"] = lambda p: my_combo()
```

---

## ⚠️ Disclaimer

This project is for **educational and research purposes**. Using automation tools in online games may violate terms of service. Use responsibly and at your own risk.

---

## License

MIT — do whatever you want with it.
