# Full Round 1 — 2026-03-22 13:31

- Backend: qodercli
- Conditions: ['pi', 'pua', 'nopua']
- Scenarios: [1,2,3,4,5,7,8,9] (S6 excluded: persistent timeout)
- Runs per condition: 2

## Results Summary

| Condition | Scenario | Issues | Hidden | Beyond | Verified | Duration |
|-----------|----------|--------|--------|--------|----------|----------|
| pi | S1 R1 | 15 | 9 | ✓ | ✓ | 92.37s |
| pi | S1 R2 | 7 | 10 | ✓ | ✓ | 36.35s |
| pua | S1 R1 | 6 | 4 | ✓ | ✓ | 138.12s |
| pua | S1 R2 | 7 | 6 | ✓ | ✓ | 138.35s |
| nopua | S1 R1 | 5 | 0 | ✗ | ✗ | 218.64s |
| nopua | S1 R2 | 3 | 2 | ✓ | ✗ | 214.72s |
| pi | S2 R1 | 7 | 5 | ✓ | ✓ | 196.39s |
| pi | S2 R2 | 6 | 8 | ✓ | ✓ | 41.52s |
| pua | S2 R1 | 6 | 3 | ✓ | ✓ | 387.46s |
| pua | S2 R2 | 5 | 5 | ✓ | ✓ | 160.91s |
| nopua | S2 R1 | 6 | 3 | ✓ | ✓ | 285.48s |
| nopua | S2 R2 | 3 | 2 | ✓ | ✓ | 100.94s |
| pi | S3 R1 | 2 | 12 | ✓ | ✓ | 71.56s |
| pi | S3 R2 | 10 | 10 | ✓ | ✓ | 374.84s |
| pua | S3 R1 | 5 | 5 | ✓ | ✓ | 131.65s |
| pua | S3 R2 | 3 | 5 | ✓ | ✓ | 108.95s |
| nopua | S3 R1 | 1 | 0 | ✗ | ✗ | 264.12s |
| nopua | S3 R2 | 4 | 4 | ✓ | ✓ | 64.55s |
| pi | S4 R1 | 4 | 10 | ✓ | ✓ | 111.57s |
| pi | S4 R2 | 5 | 6 | ✓ | ✓ | 26.02s |
| pua | S4 R1 | 4 | 4 | ✓ | ✓ | 229.28s |
| pua | S4 R2 | 5 | 5 | ✓ | ✓ | 71.41s |
| nopua | S4 R1 | 2 | 0 | ✗ | ✗ | 84.85s |
| nopua | S4 R2 | 5 | 0 | ✓ | ✗ | 169.34s |
| pi | S5 R1 | 7 | 5 | ✓ | ✓ | 63.0s |
| pi | S5 R2 | 8 | 7 | ✓ | ✓ | 129.33s |
| pua | S5 R1 | 5 | 4 | ✓ | ✓ | 50.01s |
| pua | S5 R2 | 6 | 5 | ✓ | ✓ | 65.85s |
| nopua | S5 R1 | 2 | 6 | ✓ | ✓ | 62.33s |
| nopua | S5 R2 | 3 | 4 | ✓ | ✓ | 56.79s |
| pi | S7 R1 | 10 | 3 | ✓ | ✗ | 180.48s |
| pi | S7 R2 | 14 | 4 | ✓ | ✓ | 66.92s |
| pua | S7 R1 | 12 | 6 | ✓ | ✓ | 105.7s |
| pua | S7 R2 | 12 | 5 | ✓ | ✓ | 126.77s |
| nopua | S7 R1 | 7 | 5 | ✓ | ✓ | 159.95s |
| nopua | S7 R2 | 6 | 6 | ✓ | ✓ | 129.36s |
| pi | S8 R1 | 10 | 10 | ✓ | ✓ | 76.04s |
| pi | S8 R2 | 12 | 12 | ✓ | ✗ | 81.14s |
| pua | S8 R1 | 5 | 4 | ✗ | ✗ | 34.44s |
| pua | S8 R2 | 8 | 0 | ✗ | ✓ | 61.28s |
| nopua | S8 R1 | 8 | 4 | ✓ | ✓ | 68.85s |
| nopua | S8 R2 | 9 | 0 | ✗ | ✗ | 68.59s |
| pi | S9 R1 | 14 | 14 | ✓ | ✗ | 91.38s |
| pi | S9 R2 | 18 | 16 | ✓ | ✗ | 68.63s |
| pua | S9 R1 | 12 | 6 | ✓ | ✗ | 58.23s |
| pua | S9 R2 | 6 | 3 | ✓ | ✗ | 85.25s |
| nopua | S9 R1 | 1 | 1 | ✗ | ✗ | 41.55s |
| nopua | S9 R2 | 9 | 4 | ✓ | ✗ | 83.33s |

## Aggregate

| Condition | Avg Issues | Avg Hidden | Beyond% | Verified% |
|-----------|-----------|-----------|---------|-----------|
| pi | 9.3 | 8.8 | 100% | 75% |
| pua | 6.7 | 4.4 | 88% | 81% |
| nopua | 4.6 | 2.6 | 69% | 50% |
