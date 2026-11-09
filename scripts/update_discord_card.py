#!/usr/bin/env python3
"""Generate the Discord community SVG from public Discord endpoints.

No bot token required. Never fabricates live figures when an API is unavailable.
"""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

GUILD_ID = "1112920281367973900"
INVITE_CODE = "programador"
OUTPUT = Path(__file__).resolve().parents[1] / "public" / "community-card.svg"


def fetch(url):
    req = Request(url, headers={"User-Agent": "SarahAlirielGitHubREADME/1.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=15) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"Note: couldn't read {url}: {exc}")
        return {}


def fmt(number):
    return f"{number:,}" if isinstance(number, int) and number >= 0 else "—"


def main():
    widget = fetch(f"https://discord.com/api/guilds/{GUILD_ID}/widget.json")
    invite = fetch(f"https://discord.com/api/v10/invites/{INVITE_CODE}?with_counts=true")
    guild = invite.get("guild") or {}
    # Validate invite guild to avoid accidentally advertising a different server.
    if guild.get("id") and guild["id"] != GUILD_ID:
        print("Invite points to a different guild; ignoring invite counts")
        invite = {}
    online = widget.get("presence_count")
    if not isinstance(online, int):
        online = invite.get("approximate_presence_count")
    members = invite.get("approximate_member_count")
    online_text, members_text = fmt(online), fmt(members)
    title = escape(widget.get("name") or guild.get("name") or "Servidor dos Programadores")
    # Presentation stays consistent with the profile design.
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="208" viewBox="0 0 680 208" role="img" aria-labelledby="title desc">
<title id="title">{title}</title>
<desc id="desc">Discord developer community. {online_text} online, {members_text} members. Click the image to join.</desc>
<rect width="680" height="208" rx="18" fill="#38271F"/>
<rect x="24" y="24" width="76" height="76" rx="16" fill="#E8D8C9"/>
<text x="62" y="69" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-weight="800" font-size="21" fill="#38271F">SdP</text>
<text x="116" y="51" font-family="Montserrat,Arial,Helvetica,sans-serif" font-weight="700" font-size="23" fill="#F8F2EB">Servidor dos Programadores</text>
<circle cx="123" cy="77" r="5" fill="#8CC6A4"/>
<text x="136" y="82" font-family="Inter,Arial,Helvetica,sans-serif" font-size="15" fill="#D7BFAE">{escape(online_text)} Online</text>
<circle cx="287" cy="77" r="5" fill="#B99A82"/>
<text x="300" y="82" font-family="Inter,Arial,Helvetica,sans-serif" font-size="15" fill="#D7BFAE">{escape(members_text)} Members</text>
<rect x="24" y="119" width="632" height="62" rx="12" fill="#E8D8C9"/>
<text x="340" y="157" text-anchor="middle" font-family="Montserrat,Arial,Helvetica,sans-serif" font-weight="700" font-size="19" fill="#38271F">Join my dev community ↗</text>
</svg>
'''
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Don't overwrite previously known good counts with unavailable API values.
    if online_text == "—" and members_text == "—" and OUTPUT.exists():
        print("Both sources unavailable; retaining existing SVG")
        return
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUTPUT}: online={online_text}, members={members_text}")


if __name__ == "__main__":
    main()
