# 05: Danger model (Danger Score, DS 0–100)

On Hardcore Worlds the cost of a death is fixed and total: the run ends. So the Danger Score estimates **how likely this step is to get you killed**, considering who you are at that point (your HP and level), how long you'll be exposed, and how well-understood the hazard is.

## 1. Factors (each rated 0–5 by the Risk Officer, with evidence)

| Factor | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| **Lethality** (worst credible damage vs *your* HP then) | no damage source | chip only | ≤10% HP per hit | ≤25% HP, or stacking poison | ≤50% HP, or multi-attacker burst | can exceed current HP in 1–2 ticks, or unavoidable/typeless |
| **PvP exposure** | none | world-hop risk only | low wildy, singles, low traffic | wildy with traffic | multi-combat / PK route | notorious hotspot |
| **Escape difficulty** | walk/teleport instantly | short walk | teleport delayed / long exit | instance/cutscene, or wildy ≤20 | wildy 21–30 / no-teleport zone | wildy 30+, teleblock, or locked fight |
| **Attention needed** | fully AFK-safe | AFK-safe above an HP threshold | periodic checks | constant attention | prayer switching / mechanics | tick-precise |
| **Disconnect risk** | harmless | might take a hit | low-damage aggressors nearby | keep taking damage after a DC | DC costs a lot of HP | DC likely fatal |
| **Unpredictability** | deterministic | small known RNG | RNG within known bounds | random spawns / aggression | venom, multi-attackers, stacking | undocumented / brand-new |
| **Exposure** (time) | momentary | <5 min | <30 min | a few hours | tens of hours | bulk of a 100+ h grind |
| **Knowledge gap** | 2 independent T1 sources | minor caveats | single-source | disputed facts | content <30 days old | unverified facts |

## 2. Formula (`tools/danger.py`)
```
T = max(lethality, pvp)                                   threat
C = max(escape, attention, disconnect, unpredictability)  loss of control
DS = min(100, round(100 · T/5 · (0.35 + 0.13·C) · (0.80 + 0.04·exposure) + 2·knowledge))
```
- **No threat means no danger.** If nothing can hurt you (T = 0), DS is only the small knowledge term.
- **Threat is multiplied by loss of control.** A hard-hitting monster you can walk away from scores far lower than the same monster in a locked instance.
- **Exposure scales the score from 80% to 100%.** Long grinds compound small risks.
- **Knowledge gaps add points.** Uncertainty is itself a danger.

## 3. Hazard-flag floors (minimum DS whatever the factors say)
| Flag | Floor | Flag | Floor |
|---|---|---|---|
| PVP_HOTSPOT | 75 | WILDERNESS | 45 |
| LOCKED_INSTANCE_LETHAL | 70 | DISCONNECT_FATAL | 45 |
| ONE_SHOT_POSSIBLE | 65 | UNVERIFIED_MECHANIC | 45 |
| DEEP_WILDERNESS | 65 | NEW_CONTENT (<30 days) | 25 |
| HW_UNSAFE_ACTIVITY | 10 | informational: POISON_OR_VENOM, AGGRESSIVE_NPCS_ON_ROUTE, LOW_HP_SKILLING_DAMAGE, TELEPORT_RESTRICTED, QUEST_BOSS | 0 |

## 4. Raw vs residual
- **Raw DS**: the step with no precautions.
- **Residual DS**: after the **mandatory** mitigations. Each mitigation can lower a factor by at most 3 and must cite evidence that it works. A flag is removed only by a mitigation that cites facts.
- **No perfect mitigation:** when raw ≥ 25, residual is never below 30% of raw.
- The guide shows both. Routes are judged on **residual**, so the guide always prints the mitigations it relied on.

## 5. Tiers and caps
| Tier | DS | Meaning |
|---|---|---|
| Safe | 0–9 | nothing here should kill you |
| Low | 10–24 | stay attentive and follow the precautions |
| Moderate | 25–44 | real hazard; precautions and stop conditions matter |
| High | 45–64 | experienced players with full prep only |
| Severe | 65–84 | a plausible death; avoid unless essential |
| Critical | 85–100 | run-ending risk; never on a default route |

Owner caps: **cautious 24 · standard 44 (your default) · bold 64**.
- The `safest` route must stay under the cap, unless no alternative exists and **you** accept the step.
- Any Critical residual needs your recorded acceptance on any route.
- The guide marks steps above the cap with a red ribbon. You can change the cap in the guide and the page re-evaluates instantly.

## 6. Hardcore Worlds death classification (per step)
`UNSAFE_DEATH` is the default. `SAFE_DEATH` needs a verified fact from the official Hardcore Worlds rules. `NO_DEATH_POSSIBLE` only when there is no damage source at all. Activities that are safe deaths for HCIM but **unsafe on Hardcore Worlds** get the `HW_UNSAFE_ACTIVITY` flag, so nobody carries HCIM habits over.

## 7. Worked examples (illustrative)
- Rooftop course at low level, failures deal a few damage, HP 10, hours of exposure. L=2, A=2, E=3 → `100·0.4·0.61·0.92 ≈ 22` → **Low**. With "keep HP ≥ 7, eat early" (L −1): `100·0.2·0.61·0.92 ≈ 11` → **Low**.
- A Wilderness course (level 50+ wildy): L=4, P=5, X=5, A=3, E=4 → `100·1.0·1.0·0.96 = 96` → **Critical** (DEEP_WILDERNESS floor 65 is exceeded anyway).
