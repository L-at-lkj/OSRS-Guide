# 06: Sourcing and recency policy

## Source tiers
| Tier | What | Can support a VERIFIED fact? |
|---|---|---|
| **T1** | Jagex official: news posts, patch notes, dev blogs; wiki `Update:` pages (verbatim copies of Jagex posts); in-game text observed by the owner | Yes |
| **T2** | OSRS Wiki content pages, **pinned by revision id** (`index.php?oldid=`) | Yes |
| **T3** | Established community data and tools (RuneLite plugin data, wiki calculators, named rate sheets) | Only as a second source |
| **T4** | Reddit, forums, YouTube, SEO/AI fan sites | **Never**. Leads only |

## Rules
1. **Pin everything.** Wiki citations carry `revid`. `tools/wiki.py` returns it automatically. A wiki URL without one fails the research gate.
2. **Exact quotes.** Every source carries the line of wikitext or text that supports the claim.
3. **Independence.** The verifier fetches every source itself, after the research seal. It re-reads the researcher's revision *and* the current one: a change since means STALE.
4. **Two-source preference.** Danger-critical facts (max hits, aggression, wilderness levels, death rules) and anything new should have a T1 or a second independent T2/T3 source.
5. **Rates are ranges.** XP/hour depends on attention, gear and technique. A rate is stored with its assumptions, and the plan's chosen value must sit inside the verified range.
6. **Recency window.** Every job sweeps the **12 months up to today** plus announcements for the **next 30 days**. Content released within 30 days is `new_content`, carries a caveat, and adds the NEW_CONTENT flag where it is used.
7. **Memory is not a source.** Model training data is presumed stale. If it isn't sourced, it isn't a fact.
8. **Hardcore Worlds economy.** Main-game prices (wiki prices API) are only a proxy for the separate Hardcore Worlds GE, and are labelled that way.

## Why the wiki API rather than WebFetch
WebFetch hands back a model-written summary, which can drop or alter exact numbers. `tools/wiki.py` returns raw wikitext and a revision id, so what the researcher saw, what the verifier saw and what QA re-checks are all the same bytes.
