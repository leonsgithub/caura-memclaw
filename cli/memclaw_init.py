"""memclaw-init — setup assistant for a MemClaw deployment.

Usage:
    python -m cli.memclaw_init --url http://192.168.1.53:8001
    python -m cli.memclaw_init --url http://192.168.1.53:8001 --agent-id my-agent
    python -m cli.memclaw_init --url http://192.168.1.53:8001 --key sk-...
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def _health(client: httpx.Client, url: str) -> dict:
    resp = client.get(f"{url}/health", timeout=5)
    resp.raise_for_status()
    return resp.json()


def _agent_info(client: httpx.Client, url: str, agent_id: str) -> dict | None:
    resp = client.get(f"{url}/agents/{agent_id}", timeout=5)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _mcp_block(url: str, key: str | None) -> str:
    cfg: dict = {"url": f"{url}/mcp"}
    if key:
        cfg["headers"] = {"X-API-Key": key}
    return json.dumps(
        {"mcpServers": {"memclaw": cfg}},
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify MemClaw connectivity and print MCP config."
    )
    parser.add_argument("--url", required=True, help="MemClaw base URL (e.g. http://192.168.1.53:8001)")
    parser.add_argument("--key", default=None, help="API key (MEMCLAW_API_KEY)")
    parser.add_argument("--agent-id", default=None, dest="agent_id", help="Agent ID to verify")
    args = parser.parse_args(argv)

    url = args.url.rstrip("/")
    headers = {"X-API-Key": args.key} if args.key else {}

    with httpx.Client(headers=headers) as client:
        try:
            health = _health(client, url)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            print(f"ERROR: Cannot reach {url} — {exc}", file=sys.stderr)
            return 1
        except httpx.HTTPStatusError as exc:
            print(f"ERROR: Health check failed ({exc.response.status_code})", file=sys.stderr)
            return 1

        status = health.get("status", "unknown")
        print(f"MemClaw health: {status}  ({url})")

        if args.agent_id:
            try:
                info = _agent_info(client, url, args.agent_id)
            except httpx.HTTPStatusError as exc:
                print(f"ERROR: Agent lookup failed ({exc.response.status_code})", file=sys.stderr)
                return 1
            if info:
                print(f"Agent '{args.agent_id}' found (trust={info.get('trust_level', '?')})")
            else:
                print(f"Agent '{args.agent_id}' not yet registered — will auto-create on first write")

        print("\nAdd to ~/.claude/settings.json → mcpServers:")
        print(_mcp_block(url, args.key))
        return 0


if __name__ == "__main__":
    sys.exit(main())
