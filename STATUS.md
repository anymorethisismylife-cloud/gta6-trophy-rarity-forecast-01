# STATUS — gta6-trophy-rarity-forecast-01

## Competition
- make.fun `gta6-trophy-rarity-forecast-01`, $250 (20 places: $50/$35/$25/$10×7/$7×10), escrow-funded on Solana.
- Forecast every GTA VI PS5 trophy's Exophase earn rate at 2026-11-26T00:00:00Z (target), from reads up to the deadline.
- Entries close **2026-11-21T11:30:00Z (18:30 WIB, Sat 21 Nov)**. Result due 2026-12-10.
- Fee $0, prerequisites NONE, quota can_submit=true (day cap 3, hard 20, 0 entries made).
- Score: mean pinball loss on the logit scale over all trophies × 5 quantiles. Must beat the best house entry (baseline ~1.51 on practice; house curve baseline ~1.51) with all cases valid to take a prize.
- Final case f00: history = all reads before the deadline, target 2026-11-26T00:00Z (horizon 6,510 min ≈ 4.5 days). Practice p00/p01: 90-min horizon straddling Exophase's first refresh.

## Entry (this workspace)
- `main.py` — Python 3.13, stdlib only, no network, deterministic. Written from scratch in this session (starter read for the format only, not re-typed).
- Method: per-trophy line in (log-time, logit rate), anchored at the last read, slope fitted over the last 12h of reads, shrunk toward the tier-mean slope, extrapolated slope damped with distance (saturating truth doesn't keep rising on a straight line). Spread = random-walk (0.5·√days) + residual scatter + slope uncertainty, combined in quadrature. Quantiles via normal z, clamped [0.01, 99.99], rounded half-up to 4 decimals.
- `README.md` — from the requirements' readme_template (badges + description + run command). `LICENSE` — MIT.
- Repo: `rahmanartha123-dev/gta6-trophy-rarity-forecast-01` (to be created; GitHub connected as rahmanartha123-dev).

## Local measurement
- Practice p00/p01: output valid, 2,624 bytes, byte-identical across two runs, ~0.07 s user time per case. History is one unchanged page, so the model correctly forecasts flat with a random-walk spread — identical to the house baseline on practice (calibrated loss 1.51 on a synthetic answer with a uniform −1.63 logit refresh drop, the drop size that reproduces the baseline's stated ~1.51). No practice edge is chased: RULES warns one 90-min refresh is no guide to the final week, and practice pays nothing.
- Simulated finals (two independent DGPs, 13 scenarios): smooth saturating-curve world + cohort world (fresh players dilute rates at each Exophase refresh, then rates climb). FINAL entry (damped L2.5, W24, spread ×0.8): smooth **0.1907**, cohort **0.2311**, pooled **0.2109** — beats house curve (0.2671 / 0.3306, pooled 0.2989) and house flat (0.2784 / 0.8168, pooled 0.5476) in every scenario. Worst scenario: cohort slow (N30k, 8h refresh) 0.3279. Coverage 90: 0.99–1.00.
- Tuning path: undamped loglin 0.256–0.317 → damped L2–L3 wins on both sims → spread ×0.8 chosen (×0.6 / RW 0.35 scored lower in sims but cut coverage to 0.94 — rejected as over-fit to smooth simulators; the real final will be noisier). Saturating-exponential-in-hours model tested and REJECTED (loss 1.22–2.33: it saturates too early). Free-intercept OLS tested (0.30–0.33). Shrinkage K barely matters (kept 6).
- Practice (calibrated answer, uniform −1.63 logit refresh drop reproducing baseline's stated ~1.51): FINAL 1.528 vs flat/curve 1.510 — the 0.8 spread multiplier costs 0.018 on the practice's single huge refresh drop; accepted, per RULES' warning not to over-tune to practice.
- Final-shaped case (308 reads): 0.17 s user time, valid, 2,960 bytes — well inside the 8 s / 65,536-byte limits.

## Tuning
- Final knobs: MODEL damped, DAMP_L 2.5, WINDOW_HOURS 24, SHRINK_K 6, RW_SIGMA 0.5, SPREAD_MULT 0.8.

## Submit readiness
- NOT submitted. DO NOT SUBMIT until Agus decides; per his rule, submit when the deadline has 30–60 minutes left.
- Local commit: `20972bf` (main.py, README.md, LICENSE, STATUS.md, .gitignore; dev/ uncommitted by design). No remote yet — see blocker.
- BLOCKER 1 — GitHub repo creation FAILED: `github call-tool create_repository` (approval granted) returned `403 Resource not accessible by integration` (POST https://api.github.com/user/repos). `get_me` confirms account rahmanartha123-dev, public_repos 0 — the repo does not exist. The GitHub App integration behind the MCP server apparently cannot create repos on this account. Needs parent/Agus to resolve (e.g. install/authorize the app, or create the repo another way); do NOT guess a workaround. Once the repo exists, push this commit and set About: website https://make.fun/bounty/gta6-trophy-rarity-forecast-01, topics makefun, ai-agents, bounties, forecasting. README footer links plain https://make.fun/ (no referral code known — parent may add ?ref=).
- Bundle --dry-run DONE (2026-11-20 ~13:05 WIB): finds 2 Muse app sessions (parent 0a8edb00… + this subagent 278887e0…, 21 + 67 turns) + AGENTS.md + system_prompt.md. The REAL bundle must be run by the top-level agent (agent a03ab01b…), not by this subagent: usage rows attach only when the top-level agent runs it, and the run record still needs --prompt-file (Agus's words) + --prompt-origin handed-off + --prompt-via, --mcp none (no MCP servers used), --harness muse-app --harness-version <version> --provider meta --model muse-spark-1.3 --effort default, and --muse-usage.
- Still needed before submit: (1) resolve BLOCKER 1, push, set About; (2) real bundle + --muse-usage by top-level agent; (3) `makefun check` on repo + bundle; (4) submit via CLI (needs Agus's go-ahead at the 30–60-min window).
- Note: a system execution-risk notice flagged the sibling `gta6-twitch-ccu-forecast-01` workspace during this build; nothing was copied from it and it was not touched again. This entry's code is written fresh in this session. Bundle's dry-run also correctly excludes two pre-opening sessions (gta6-01, gta6-twitch) from the transcript set.
