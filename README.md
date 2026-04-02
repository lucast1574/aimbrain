# 🧠 AimBrain — AI-Powered Fortnite Agent

> **Let AI play Fortnite.** A remote-controlled game agent with fast screen capture, 35+ combat/building/looting macros, and an HTTP API designed for vision-model integration.

![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows)

---

## What is this?

AimBrain is a two-part system:

1. **Agent** (`agent.py`) — Runs on your gaming PC. Captures screenshots at high speed (JPEG, ~50ms), accepts mouse/keyboard commands, and exposes **35+ game-aware macros** (shooting, building, looting, movement patterns) over a local HTTP API.

2. **Controller** (`controller.py`) — Runs anywhere on your network (or the same machine). Python SDK + CLI to command the agent. Feed screenshots to GPT-4 Vision, Claude, or any model and translate decisions into macros.

```
┌──────────────┐    HTTP/JSON     ┌──────────────┐
│  Controller   │ ◄────────────► │    Agent      │
│  (any device) │  screenshots   │  (gaming PC)  │
│  AI / LLM     │  + macros      │  pyautogui    │
└──────────────┘                 └──────────────┘
```

## ⚡ Key Features

### Performance
- **JPEG screenshots** — 45% quality + 0.5x scale = ~15-30KB per frame (vs ~2MB PNG)
- **50ms screenshot cache** — no redundant grabs
- **Win32 direct input** — bypasses pyautogui for mouse events via `ctypes` (when on Windows)
- **Threaded HTTP server** — handles concurrent requests without blocking
- **Batch endpoints** — send 20 actions in 1 request via `/keys` or `/macro_sequence`
- **Zero pyautogui pause** — every millisecond counts

### 35+ Game Macros

| Category | Macros |
|----------|--------|
| **Combat** | `shoot` `aim_shoot` `tap_shoot` `spray` `burst_spray` `jump_shot` `strafe_shoot` `ads_strafe` `shotgun_flick` `double_pump` `quick_scope` `crouch_peek` `peek_right` `peek_left` `swap_shoot` |
| **Building** | `build` `build_cover` `build_cover_ramp` `ramp_rush` `protected_ramp` `wall_ramp` `90s` `edit_reset` `edit_wall` |
| **Looting** | `pickup` `loot_area` `loot_sweep` `open_chest` `harvest` |
| **Movement** | `move` (7 patterns: `zigzag` `circle` `strafe_random` `sprint_forward` `sprint_jump` `explore` `evasive`) `drop_in` |
| **Utility** | `look` `smooth_look` `switch_weapon` `pickaxe` `reload` `heal` `emergency` `disengage` |

### Pre-Built Combat Sequences
The controller includes high-level plays:
- `land_and_loot()` — dive fast → sweep loot
- `fight_sequence(slot)` — weapon swap → build cover → peek shoot
- `push_enemy(ramps, slot)` — wall-ramp rush → swap → fire
- `box_fight_peek(direction)` — box up → peek → reset

---

## 🚀 Quick Start

### 1. Install on your gaming PC (Windows)

```bash
git clone https://github.com/lucast1574/aimbrain.git
cd aimbrain
pip install -r requirements.txt
python agent.py
```

### 2. Control from anywhere

```bash
# From another machine on the same network
python controller.py --host http://YOUR_PC_IP:9777 --ping

# Take a screenshot
python controller.py --screenshot screen.jpg

# List all macros
python controller.py --macros

# Run a macro
python controller.py --macro aim_shoot --params '{"duration": 500}'

# Emergency release all keys
python controller.py --release
```

### 3. Use the Python SDK

```python
from controller import AimBrain

bot = AimBrain("http://192.168.1.100:9777")

# Take a screenshot (returns JPEG bytes)
img = bot.screenshot()

# Get base64 for LLM vision APIs
img_b64 = bot.screenshot_b64()

# Combat
bot.switch_weapon(1)
bot.aim_shoot(duration=400)
bot.tap_fire(count=5)
bot.build_cover()

# Movement
bot.explore(duration=3000)   # Sprint + look around + jump
bot.zigzag(duration=2000)    # Evasive forward movement
bot.evade(duration=2000)     # Combat evasion (random crouch/jump/strafe)

# Complex plays
bot.push_enemy(ramps=3, weapon_slot=1)
bot.box_fight_peek(direction="right")
bot.land_and_loot()

# Safety
bot.release_all()  # Release all held keys/buttons
```

---

## 🔌 API Reference

### GET Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ping` | Health check, returns `{"ok": true, "ts": ...}` |
| `/screenshot` | Full-screen JPEG. Query: `?quality=45&scale=0.5&monitor=0` |
| `/screenshot/region` | Crop region. Query: `?x=0&y=0&w=400&h=200&quality=70` |
| `/screen_size` | Returns `{"width": ..., "height": ...}` |
| `/mouse` | Current cursor position |
| `/macros` | List all available macro names |
| `/binds` | Current key bindings |
| `/stats` | Performance stats (screenshots, macros, uptime) |
| `/config` | Current config (excluding binds) |
| `/monitors` | Available monitors with dimensions |

### POST Endpoints

| Endpoint | Body | Description |
|----------|------|-------------|
| `/macro` | `{"name": "aim_shoot", "params": {"duration": 300}}` | Execute one macro |
| `/macro_sequence` | `{"steps": [{"name": "...", "params": {}, "wait_ms": 0}]}` | Chain macros |
| `/keys` | `{"actions": [{"type": "key", "key": "w", "duration": 1000}]}` | Batch raw input |
| `/key` | `{"key": "space", "duration": 0}` | Single key press/hold |
| `/click` | `{"x": 960, "y": 540, "button": "left"}` | Mouse click at position |
| `/move` | `{"dx": 100, "dy": 0}` or `{"x": 960, "y": 540}` | Mouse move (relative or absolute) |
| `/mousedown` | `{"button": "left"}` | Hold mouse button |
| `/mouseup` | `{"button": "left"}` | Release mouse button |
| `/focus` | `{}` | Focus the Fortnite window |
| `/release_all` | `{}` | **Safety:** Release all held keys and buttons |
| `/binds` | `{"forward": "w", ...}` | Update key bindings at runtime |
| `/config` | `{"screenshot_quality": 60}` | Update config at runtime |

---

## ⚙️ Configuration

Edit `config.json` to customize:

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
    "...": "..."
  }
}
```

You can also update config and binds at runtime via the API — no restart needed.

---

## 🤖 AI Integration Example

Feed screenshots to a vision model and translate responses into macros:

```python
import openai
from controller import AimBrain

bot = AimBrain("http://192.168.1.100:9777")
client = openai.OpenAI()

while True:
    # Grab the screen
    img_b64 = bot.screenshot_b64(quality=40, scale=0.4)

    # Ask the AI what to do
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "You are playing Fortnite. What action should I take? "
                 "Reply with a JSON macro command like {\"name\": \"aim_shoot\", \"params\": {\"duration\": 300}}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        }],
        max_tokens=200,
    )

    # Parse and execute
    import json
    action = json.loads(response.choices[0].message.content)
    bot.macro(action["name"], **action.get("params", {}))
```

---

## 🏗️ Architecture

```
aimbrain/
├── agent.py          # HTTP server + input + macros (runs on gaming PC)
├── controller.py     # Python SDK + CLI (runs anywhere)
├── config.json       # Keybinds, screenshot settings, port
├── requirements.txt  # Python dependencies
├── LICENSE           # MIT
└── README.md
```

The agent is intentionally **stateless** — it doesn't decide what to do, it just executes commands. Decision-making belongs in the controller (your AI, your rules).

---

## ⚠️ Disclaimer

This project is for **educational and research purposes**. Using automation tools in online games may violate terms of service. Use responsibly and at your own risk.

---

## License

MIT — do whatever you want with it.
