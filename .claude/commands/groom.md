---
description: Groom the Vivid Pay backlog with the product-owner agent and propose the next ticket
argument-hint: [optional focus, e.g. an epic like VPAY-6, or a question]
---

Use the `product-owner` agent to groom the Vivid Pay backlog. Focus, if any: $ARGUMENTS

The agent must orient itself from `VISION.md`, `ROADMAP.md`, the ADRs and Jira before proposing anything,
show its proposed stories for the owner's approval before creating them, and finish by recommending
the next ticket to build.

When the agent returns, relay its proposal faithfully, including anything it could not check and anything
the owner has to do. If the owner approves, have the agent create or update the tickets and report the keys.
Do not change ticket statuses and do not edit code.
