# Example session

Tool outputs below are **real values** from the committed data (reproduce them
with `python -m copilot.cli demo`). The agent's replies are an illustrative
transcript of chat mode — your exact wording will vary run to run; the numbers
will not, because they come from the deterministic tools.

---

**you>** If a windstorm cuts harvest supply by 40% for six weeks, which node stocks out first and how bad is it?

```
[tool] stockout_whatif({"supply_reduction_pct": 40, "duration_weeks": 6})
```

**copilot>** The Export Port Kalmar is the first to breach its safety stock (week 3, vs week 4 for both mills), and all three demand nodes hit full stockout in week 5.

Over the 6-week event the network fill rate drops to **92.8%**, with **5,840 m³ of unmet demand**: 2,532 m³ at Pulp Mill Mönsterås, 2,348 m³ at Sawmill Vislanda, 960 m³ at the port. Baseline weekly supply of 14,600 m³ falls to 8,760 m³ under the scenario.

Note this projection runs on the synthetic illustrative network with pro-rata allocation — treat the ranking and orders of magnitude as the signal, not the exact volumes.

---

**you>** Are we seeing any storm signal in the actual weather data right now?

```
[tool] storm_risk_summary({})
```

**copilot>** No critical signal in the observed window (late April – early September 2026, real SMHI data). None of the three stations recorded a gust at or above the 21 m/s critical threshold. Peak was 19.7 m/s at Ljungby A on 2026-07-07 — the same day Växjö A hit its max of 18.4 m/s, so that was a region-wide wind event that came close to the caution range but not to harvest-stopping levels.

---

**you>** How are sawlog prices moving?

```
[tool] price_summary({"assortment": "Sawlogs", "region": "Götaland"})
```

**copilot>** Softening. Götaland sawlogs are at **1,252 SEK/m³** in 2026Q2 (preliminary), down **7.6% quarter-over-quarter** and **8.9% year-over-year**. For context, the series since 2019 has ranged 530–1,389 SEK/m³, so prices remain historically high despite the pullback. (Real Swedish Forest Agency data.)

---

**you>** What will the sawlog price be in 2028?

**copilot>** I can't forecast that — my price tool provides historical official statistics through 2026Q2, and I don't extrapolate numbers. What I can tell you is the current level and trend (1,252 SEK/m³, falling ~8% QoQ), which you could feed into a proper forecasting model with demand-side drivers if you need a 2028 view.
