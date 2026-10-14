# Original-constraint feasibility certificate

This is a post-hoc diagnosis, not fresh evidence.

At least 4 of 30 declared development paths are impossible even in an optimistic oracle relaxation. Thus the original sample can pass at most 26/30, below the requested 27/30.

| Seed | Demand | Maximum optimistic fulfilled units | Fill upper bound | Required units | Necessary uniform allowance |
|---|---:|---:|---:|---:|---:|
| 20001 | 35117 | 33293 | 94.8059% | 33362 | $18,062.47 |
| 20007 | 30676 | 28727 | 93.6465% | 29143 | $18,413.15 |
| 20016 | 33501 | 31517 | 94.0778% | 31826 | $18,305.22 |
| 20023 | 32693 | 30347 | 92.8242% | 31059 | $18,678.09 |

The allowance column is a necessary lower bound only, not a sufficient budget or recommendation. See ../../docs/feasibility_v2.md for the proof and reproduction instructions. No old artifact or operating constraint was changed.
