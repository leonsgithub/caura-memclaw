Short answer: give both agents the SKILL.md operating manual — that's the doc written for the agent (how/why/when to use the tools). AGENT-INSTALL.md and README.md are for the human setting things up, not for the agent's working context.

Which variant of SKILL.md depends on how each agent connects:

Agent	If it connects via…	Give it
Claude (Claude Code / Cursor / any MCP client)	MCP	static/skills/memclaw/SKILL.md
Hermes	MCP	static/skills/memclaw/SKILL.md
Hermes	OpenClaw gateway plugin	plugin/skills/memclaw/SKILL.md
The two variants are the same manual; the plugin copy additionally explains the auto-injected keystones / auto-recall / auto-write backstop that the OpenClaw plugin runs for you. If an agent isn't on OpenClaw, use the static copy.

For Claude Code specifically, you don't hand it the file manually — install it as a skill so it loads on demand:


curl -s "http://localhost:8000/api/v1/install-skill" | bash
# or copy to ~/.claude/skills/memclaw/SKILL.md
The per-tool parameter docs (the 20 tool descriptions) are delivered automatically over MCP — SKILL.md is the layer on top that tells the agent which tool when and why, which is exactly what I just completed coverage for.