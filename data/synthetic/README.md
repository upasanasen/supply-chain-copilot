# Synthetic network data

`network.csv` is a **synthetic, illustrative** 8-node forest supply network
(harvest areas → terminals → mills/port) in a Småland-like region. It exists so
the inventory what-if tool has a concrete network to reason over.

Node capacities, demands and inventory levels are invented but sized to be
plausible against real Swedish forestry statistics (regional felling volumes and
mill intake scales). **No real company data is represented.**

Everything under `data/raw/` and `data/processed/` (weather, prices), by
contrast, is real public data with provenance recorded in
`data/raw/manifest.json`.
