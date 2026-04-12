#!/usr/bin/env python3
"""
AimBrain CLI — command the agent from the terminal.

Usage:
    python controller.py --host http://192.168.1.100:9777 --ping
    python controller.py --screenshot screen.jpg
    python controller.py --macro aim_shoot --params '{"duration": 500}'
    python controller.py --macros
    python controller.py --stats
    python controller.py --release

DonClaw mode:
    python controller.py --ocr
    python controller.py --find "Play"
    python controller.py --act "Play"
    python controller.py --donclaw-status
"""

import json
import argparse

from aimbrain.client import AimBrain


def main():
    parser = argparse.ArgumentParser(
        description="AimBrain CLI — control the Fortnite agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="http://localhost:9777", help="Agent URL")
    parser.add_argument("--ping", action="store_true", help="Ping the agent")
    parser.add_argument("--screenshot", type=str, metavar="FILE", help="Save screenshot")
    parser.add_argument("--macros", action="store_true", help="List available macros")
    parser.add_argument("--macro", type=str, help="Run a macro by name")
    parser.add_argument("--params", type=str, default="{}", help="JSON params for --macro")
    parser.add_argument("--stats", action="store_true", help="Show agent stats")
    parser.add_argument("--focus", action="store_true", help="Focus Fortnite window")
    parser.add_argument("--release", action="store_true", help="Release all held keys")

    # DonClaw commands
    parser.add_argument("--ocr", action="store_true", help="Get screen text via DonClaw OCR")
    parser.add_argument("--find", type=str, metavar="TEXT", help="Find text on screen via DonClaw")
    parser.add_argument("--act", type=str, metavar="TEXT", help="Click on text via DonClaw")
    parser.add_argument("--donclaw-status", action="store_true", help="Check DonClaw Node status")

    args = parser.parse_args()

    bot = AimBrain(host=args.host)

    if args.ping:
        print(json.dumps(bot.ping(), indent=2))
    elif args.screenshot:
        bot.save_screenshot(args.screenshot)
        print(f"Saved: {args.screenshot}")
    elif args.macros:
        for m in bot.list_macros():
            print(f"  • {m}")
        print(f"\n  {len(bot.list_macros())} macros available")
    elif args.macro:
        result = bot.macro(args.macro, **json.loads(args.params))
        print(json.dumps(result, indent=2))
    elif args.stats:
        print(json.dumps(bot.stats(), indent=2))
    elif args.focus:
        print(json.dumps(bot.focus_fortnite(), indent=2))
    elif args.release:
        print(json.dumps(bot.release_all(), indent=2))
    elif args.ocr:
        result = bot.ocr()
        print(json.dumps(result, indent=2))
    elif args.find:
        result = bot.find(args.find)
        print(json.dumps(result, indent=2))
    elif args.act:
        result = bot.act(args.act)
        print(json.dumps(result, indent=2))
    elif args.donclaw_status:
        result = bot.donclaw_status()
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
