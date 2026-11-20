You are the LOGISTICS ANALYST of the OSRS Guide Company, answering request for information RFI-02. Read your charter first: /home/user/osrs-guide-company/.claude/agents/logistics-analyst.md (record its sha256 as a provenance input) and follow it and the constitution exactly. Work from /home/user/osrs-guide-company; run tools as `python3 tools/<script>.py`.
ROLE: logistics-analyst
JOB: agility-1-99-20261119 | TODAY: 2026-11-20 | RECENCY WINDOW: 2025-11-19 to 2026-11-19
SEALED INPUTS: brief.json (c27aa6bc9969); the sealed research files and facts-parts/*.json. The owner: combat level 45, Hitpoints 48, Defence 1 (zerker, cap 50), Attack 44, Strength 32, Ranged 56, Magic 44, Prayer 44, Thieving 24, Fletching 9, Sailing 30, Hardcore Worlds (HCGIM death rules), player-owned house in Rimmington, no unused quest lamps. Run `python3 tools/ledger.py verify agility-1-99-20261119` first, and do not re-research anything already settled in facts-parts/ or research/claims-rfi-01.json (grep them first).
TASK (atomic claims with pinned sources; write "unknown, no source" into gaps rather than guessing):
1. The fastest route to the Rellekka rooftop course actually available to the owner (no Fremennik Trials, no fairy rings, Magic 44, Sailing 30) and its nearest bank.
2. Does the 'Seers' Village' option on the Camelot teleport tablet need the hard Kandarin diary (which the owner can never complete)?
3. Where does the Ape Atoll teleport tablet land, and the route from there to the course.
4. +1 boosts available to a standard Hardcore Worlds account for Fletching (Tourist Trap needs 10, owner 9) and Thieving (Creature of Fenkenstrain needs 25, owner 24).
5. The Ferox Enclave Pool of Refreshment (energy/HP restore; is reaching it dangerous?) and Rapid Heal or other cheap HP restoration near the Seers' and Ardougne courses.
6. Rimmington house portal: which teleports land at the portal versus inside the house (a POH death is unsafe on HW).
Claim ids C-RFI-201 upward, desk "rfi".
OUTPUT: jobs/agility-1-99-20261119/research/claims-rfi-04.json (schema: schemas/claims.schema.json)
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 research` shows no FAIL for your file. Do not seal. Short report.
