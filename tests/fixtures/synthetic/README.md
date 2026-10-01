# Synthetic fixtures

Everything in this directory is **fabricated test data**, not CFBD data. Raw
requests built from these fixtures use `provider = 'SYNTHETIC'` so they can never
be mistaken for real observations in the ledger, snapshots, or evaluation results.

No forecasting performance may be reported from synthetic data. It exists to
exercise contracts (cutoffs, immutability, score support, tie-breaks) and for
parameter-recovery checks where the true effects are known by construction.
