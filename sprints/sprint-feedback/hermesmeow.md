# Honcho vs MemClaw Comparison

## Overview
| Dimension                    | Honcho                                      | MemClaw                                              | Notes |
|-----------------------------|---------------------------------------------|------------------------------------------------------|-------|
| **Type**                    | Native Hermes memory backend                | External standalone MCP server                       | Honcho = zero extra infra |
| **Primary Strength**        | Simplicity & tight Hermes integration       | Advanced memory + **procedural memory**              | MemClaw is significantly more capable |
| **Procedural Memory**       | None                                        | Full support (`procedure_suggest`, `record`, reliability scoring, quarantine) | Major MemClaw advantage |
| **Multi-Agent Isolation**   | Basic                                       | Explicit `agent_id`, trust levels, `scope_agent`/`scope_team`/`scope_fleet` | MemClaw much stronger |
| **Cross-Profile / Cross-VM**| Possible but manual                         | Designed for it (headers + fleet scoping)            | MemClaw wins |
| **Governance**              | None                                        | Keystone rules (mandatory policies)                  | MemClaw only |
| **Structured Data**         | No                                          | Yes (`memclaw_doc` collections with semantic search) | MemClaw only |
| **Reliability / Learning**  | Basic                                       | Strong (`evolve` loop, procedure reliability scoring) | MemClaw only |
| **Tuning & Recall Control** | Limited                                     | `memclaw_tune` (top_k, similarity, freshness, graph hops, etc.) | MemClaw only |
| **Setup Complexity**        | Very low (`hermes memory setup`)            | Medium (MCP config + headers + registration)         | Honcho wins |
| **Operational Overhead**    | Minimal                                     | External service + monitoring                        | Honcho wins |
| **Maturity in Hermes**      | First-class supported backend               | Newer / custom deployment                            | Honcho currently more stable |

## Pros & Cons

### Honcho
**Pros**
- Native, minimal friction
- No extra services to run
- Sufficient for most single-agent or small-team use
- Easy to enable/disable via config

**Cons**
- No procedural memory
- Weak multi-agent namespace control
- No reliability scoring or procedure learning
- No keystone rules or governance layer

### MemClaw
**Pros**
- Rich procedural memory system with automatic reliability tracking
- Strong, explicit multi-agent and multi-repo scoping
- Keystone rules (can enforce mandatory behavior)
- Structured document collections + semantic search
- Tunable recall + evolve feedback loop
- Built for cross-VM / cross-profile memory sharing

**Cons**
- Requires running and maintaining an external service
- More configuration (headers, registration, scoping discipline)
- Namespace isolation is **not automatic** — must choose and enforce a model (`fleet` or
