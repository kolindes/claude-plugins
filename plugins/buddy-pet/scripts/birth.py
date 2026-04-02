#!/usr/bin/env python3
"""
Birth script for buddy-pet plugin.
Reads companion from ~/.claude.json, computes bones, registers buddy via API.
"""

import os
import sys

# Add scripts dir to path for common import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def main():
    # 1. Check if already registered
    config = common.load_config()
    if config and config.get("buddy_token"):
        buddy_id = config.get("buddy_id", "unknown")
        print(f"Already registered. Buddy ID: {buddy_id}. Use /buddy-delete first.")
        return

    # 2. Read companion data from ~/.claude.json
    companion = common.read_companion_data()
    if not companion:
        print("No companion found in ~/.claude.json. Hatch a companion in Claude Code first.")
        return

    user_id = common.get_user_id()
    if user_id == "anon":
        print("Could not determine user ID from ~/.claude.json. Sign in to Claude Code first.")
        return

    # 3. Compute hashes
    user_hash = common.compute_user_hash(user_id)
    instance_id = common.compute_instance_id()

    # 4. Build birth request
    birth_data = {
        "user_hash": user_hash,
        "instance_id": instance_id,
        "companion": {
            "name": companion.get("name", ""),
            "personality": companion.get("personality", ""),
            "hatched_at": companion.get("hatched_at", 0),
            "species": companion.get("species", ""),
            "rarity": companion.get("rarity", ""),
            "eye": companion.get("eye", ""),
            "hat": companion.get("hat", ""),
            "shiny": companion.get("shiny", False),
            "base_stats": companion.get("base_stats", {}),
        },
        "plugin_version": common.PLUGIN_VERSION,
    }

    # 5. POST /guild/buddy/birth -> get buddy_token directly
    print("Registering buddy...")
    status, resp = common.http_post("/guild/buddy/birth", birth_data)

    if status == 0:
        print(f"Failed to connect to API: {resp.get('error', 'unknown error')}")
        return

    if status not in (200, 201):
        error = resp.get("error", resp.get("message", f"HTTP {status}"))
        print(f"Birth failed: {error}")
        return

    buddy_token = resp.get("buddy_token", "")
    buddy_id = resp.get("buddy_id", "")

    if not buddy_token:
        print(f"Unexpected response (no buddy_token): {resp}")
        return

    # 6. Save config
    api_url = common.get_api_url()
    new_config = {
        "buddy_token": buddy_token,
        "buddy_id": buddy_id,
        "api_url": api_url,
    }
    common.save_config(new_config)

    name = companion.get("name", "buddy")
    buddy_name = resp.get("buddy", {}).get("name", name)
    print(f"BUDDY born! Name: {buddy_name}, ID: {buddy_id}")


if __name__ == "__main__":
    main()
