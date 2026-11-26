# Nightly check, 2026-11-26

Run every night by the sync job against the working project: every DOI is looked up at doi.org, and the region
data, evidence fields, figure files, tours and receptor maps are checked (`tools/qa_data.py --doi`).

| Item | Result |
|---|---|
| Regions | 186 |
| Evidence entries on regions | 549 |
| Stimulation cards | 93 |
| Evidence-tour items | 58 |
| Figures in use | 228 |
| DOIs checked at doi.org | 486 |
| DOIs not found | 0 |
| DOIs that could not be checked tonight | 0 |
| Other data findings | 7 |
| Run time | 1.3 min |

## Findings
- **evidence: claim over 110 chars** (2): default_mode_network.ev2 (114); superior_longitudinal_fasciculus.ev4 (111)
- **evidence: no DOI** (5): paracentral_lobule.ev1; inferior_temporal_gyrus.ev2; temporal_pole.ev1; premotor_cortex.ev2; mammillary_bodies.ev1
