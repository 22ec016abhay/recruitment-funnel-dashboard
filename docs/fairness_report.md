# AI #5 - Fairness and adverse-impact check (real dataset)

Source: `sql/recruitment.db`, read-only. Gender is used only in this analysis and never in an LLM prompt.

**What this is:** a check of selection rates by gender in this dataset, using 95% Wilson intervals, Fisher exact tests, the 4/5ths screening ratio and stratified views.

**What this is not:** a legal adverse-impact analysis. The 4/5ths rule is a screening heuristic. Real hiring decisions need legal and domain review.

## Scope: all applicants (n = 1500)

Gender counts: {'Male': 778, 'Female': 676, 'Non-binary': 46}

### Selection rates by stage (cumulative reach, 95% Wilson CI)

| gender     | stage       |   n |   reached |   rate_pct |   ci95_low_pct |   ci95_high_pct |   pass_from_prev_pct | low_n   |
|:-----------|:------------|----:|----------:|-----------:|---------------:|----------------:|---------------------:|:--------|
| Female     | Screened    | 676 |       322 |      47.63 |          43.89 |           51.4  |                47.63 | False   |
| Female     | Interviewed | 676 |       170 |      25.15 |          22.02 |           28.55 |                52.8  | False   |
| Female     | Offered     | 676 |        52 |       7.69 |           5.91 |            9.95 |                30.59 | False   |
| Female     | Hired       | 676 |        39 |       5.77 |           4.25 |            7.79 |                75    | False   |
| Male       | Screened    | 778 |       497 |      63.88 |          60.45 |           67.18 |                63.88 | False   |
| Male       | Interviewed | 778 |       269 |      34.58 |          31.32 |           37.99 |                54.12 | False   |
| Male       | Offered     | 778 |        96 |      12.34 |          10.21 |           14.84 |                35.69 | False   |
| Male       | Hired       | 778 |        75 |       9.64 |           7.76 |           11.92 |                78.12 | False   |
| Non-binary | Screened    |  46 |        33 |      71.74 |          57.45 |           82.68 |                71.74 | True    |
| Non-binary | Interviewed |  46 |        17 |      36.96 |          24.52 |           51.4  |                51.52 | True    |
| Non-binary | Offered     |  46 |         4 |       8.7  |           3.43 |           20.32 |                23.53 | True    |
| Non-binary | Hired       |  46 |         4 |       8.7  |           3.43 |           20.32 |               100    | True    |

### Adverse-impact ratio vs highest-rate group with n >= 50

| stage       | gender     |   n |   rate_pct | reference_group   |   reference_rate_pct |   impact_ratio | below_4_5ths   | low_n   |
|:------------|:-----------|----:|-----------:|:------------------|---------------------:|---------------:|:---------------|:--------|
| Screened    | Female     | 676 |      47.63 | Male              |                63.88 |          0.746 | True           | False   |
| Screened    | Male       | 778 |      63.88 | Male              |                63.88 |          1     | False          | False   |
| Screened    | Non-binary |  46 |      71.74 | Male              |                63.88 |          1.123 | False          | True    |
| Interviewed | Female     | 676 |      25.15 | Male              |                34.58 |          0.727 | True           | False   |
| Interviewed | Male       | 778 |      34.58 | Male              |                34.58 |          1     | False          | False   |
| Interviewed | Non-binary |  46 |      36.96 | Male              |                34.58 |          1.069 | False          | True    |
| Offered     | Female     | 676 |       7.69 | Male              |                12.34 |          0.623 | True           | False   |
| Offered     | Male       | 778 |      12.34 | Male              |                12.34 |          1     | False          | False   |
| Offered     | Non-binary |  46 |       8.7  | Male              |                12.34 |          0.705 | False          | True    |
| Hired       | Female     | 676 |       5.77 | Male              |                 9.64 |          0.599 | True           | False   |
| Hired       | Male       | 778 |       9.64 | Male              |                 9.64 |          1     | False          | False   |
| Hired       | Non-binary |  46 |       8.7  | Male              |                 9.64 |          0.902 | False          | True    |

### Fisher exact test, Female vs Male, per stage

| comparison     | stage       |   Female_reached |   Female_n |   Male_reached |   Male_n |   p_value_two_sided |
|:---------------|:------------|-----------------:|-----------:|---------------:|---------:|--------------------:|
| Female vs Male | Screened    |              322 |        676 |            497 |      778 |              0      |
| Female vs Male | Interviewed |              170 |        676 |            269 |      778 |              0.0001 |
| Female vs Male | Offered     |               52 |        676 |             96 |      778 |              0.004  |
| Female vs Male | Hired       |               39 |        676 |             75 |      778 |              0.0062 |

### Stratified by source (Mantel-Haenszel OR for Female vs Male hire = 0.591)

| source          |   Female_n |   Female_hired |   Male_n |   Male_hired |   Female_rate_pct |   Male_rate_pct | low_n   |
|:----------------|-----------:|---------------:|---------:|-------------:|------------------:|----------------:|:--------|
| Company Website |        109 |              1 |      114 |           10 |              0.92 |            8.77 | True    |
| Indeed          |         99 |              8 |      120 |            5 |              8.08 |            4.17 | True    |
| Job Fair        |        105 |              2 |      116 |            4 |              1.9  |            3.45 | True    |
| LinkedIn        |        172 |              9 |      200 |           18 |              5.23 |            9    | True    |
| Naukri          |        104 |              9 |      111 |            9 |              8.65 |            8.11 | True    |
| Referral        |         87 |             10 |      117 |           29 |             11.49 |           24.79 | False   |

### Stratified by department (Mantel-Haenszel OR for Female vs Male hire = 0.574)

| department      |   Female_n |   Female_hired |   Male_n |   Male_hired |   Female_rate_pct |   Male_rate_pct | low_n   |
|:----------------|-----------:|---------------:|---------:|-------------:|------------------:|----------------:|:--------|
| Engineering     |        160 |              9 |      153 |           14 |              5.62 |            9.15 | True    |
| Finance         |        137 |              4 |      178 |           24 |              2.92 |           13.48 | True    |
| Human Resources |         75 |              5 |       57 |            5 |              6.67 |            8.77 | True    |
| Marketing       |        119 |              8 |      146 |           16 |              6.72 |           10.96 | True    |
| Operations      |         58 |              3 |       78 |            2 |              5.17 |            2.56 | True    |
| Product         |         61 |              6 |       87 |            6 |              9.84 |            6.9  | True    |
| Sales           |         66 |              4 |       79 |            8 |              6.06 |           10.13 | True    |

### Stratified by exp_band (Mantel-Haenszel OR for Female vs Male hire = 0.575)

| exp_band   |   Female_n |   Female_hired |   Male_n |   Male_hired |   Female_rate_pct |   Male_rate_pct | low_n   |
|:-----------|-----------:|---------------:|---------:|-------------:|------------------:|----------------:|:--------|
| <3 yrs     |        273 |             11 |      326 |           36 |              4.03 |           11.04 | False   |
| 3-7 yrs    |        167 |              9 |      180 |           15 |              5.39 |            8.33 | True    |
| 7+ yrs     |        236 |             19 |      272 |           24 |              8.05 |            8.82 | False   |

## Scope: excluding In Process (n = 1329)

Gender counts: {'Male': 691, 'Female': 594, 'Non-binary': 44}

### Selection rates by stage (cumulative reach, 95% Wilson CI)

| gender     | stage       |   n |   reached |   rate_pct |   ci95_low_pct |   ci95_high_pct |   pass_from_prev_pct | low_n   |
|:-----------|:------------|----:|----------:|-----------:|---------------:|----------------:|---------------------:|:--------|
| Female     | Screened    | 594 |       282 |      47.47 |          43.49 |           51.49 |                47.47 | False   |
| Female     | Interviewed | 594 |       150 |      25.25 |          21.93 |           28.9  |                53.19 | False   |
| Female     | Offered     | 594 |        49 |       8.25 |           6.3  |           10.74 |                32.67 | False   |
| Female     | Hired       | 594 |        39 |       6.57 |           4.84 |            8.85 |                79.59 | False   |
| Male       | Screened    | 691 |       434 |      62.81 |          59.14 |           66.33 |                62.81 | False   |
| Male       | Interviewed | 691 |       242 |      35.02 |          31.56 |           38.65 |                55.76 | False   |
| Male       | Offered     | 691 |        90 |      13.02 |          10.72 |           15.74 |                37.19 | False   |
| Male       | Hired       | 691 |        75 |      10.85 |           8.75 |           13.39 |                83.33 | False   |
| Non-binary | Screened    |  44 |        31 |      70.45 |          55.78 |           81.84 |                70.45 | True    |
| Non-binary | Interviewed |  44 |        16 |      36.36 |          23.78 |           51.13 |                51.61 | True    |
| Non-binary | Offered     |  44 |         4 |       9.09 |           3.59 |           21.16 |                25    | True    |
| Non-binary | Hired       |  44 |         4 |       9.09 |           3.59 |           21.16 |               100    | True    |

### Adverse-impact ratio vs highest-rate group with n >= 50

| stage       | gender     |   n |   rate_pct | reference_group   |   reference_rate_pct |   impact_ratio | below_4_5ths   | low_n   |
|:------------|:-----------|----:|-----------:|:------------------|---------------------:|---------------:|:---------------|:--------|
| Screened    | Female     | 594 |      47.47 | Male              |                62.81 |          0.756 | True           | False   |
| Screened    | Male       | 691 |      62.81 | Male              |                62.81 |          1     | False          | False   |
| Screened    | Non-binary |  44 |      70.45 | Male              |                62.81 |          1.122 | False          | True    |
| Interviewed | Female     | 594 |      25.25 | Male              |                35.02 |          0.721 | True           | False   |
| Interviewed | Male       | 691 |      35.02 | Male              |                35.02 |          1     | False          | False   |
| Interviewed | Non-binary |  44 |      36.36 | Male              |                35.02 |          1.038 | False          | True    |
| Offered     | Female     | 594 |       8.25 | Male              |                13.02 |          0.634 | True           | False   |
| Offered     | Male       | 691 |      13.02 | Male              |                13.02 |          1     | False          | False   |
| Offered     | Non-binary |  44 |       9.09 | Male              |                13.02 |          0.698 | False          | True    |
| Hired       | Female     | 594 |       6.57 | Male              |                10.85 |          0.606 | True           | False   |
| Hired       | Male       | 691 |      10.85 | Male              |                10.85 |          1     | False          | False   |
| Hired       | Non-binary |  44 |       9.09 | Male              |                10.85 |          0.838 | False          | True    |

### Fisher exact test, Female vs Male, per stage

| comparison     | stage       |   Female_reached |   Female_n |   Male_reached |   Male_n |   p_value_two_sided |
|:---------------|:------------|-----------------:|-----------:|---------------:|---------:|--------------------:|
| Female vs Male | Screened    |              282 |        594 |            434 |      691 |              0      |
| Female vs Male | Interviewed |              150 |        594 |            242 |      691 |              0.0002 |
| Female vs Male | Offered     |               49 |        594 |             90 |      691 |              0.0068 |
| Female vs Male | Hired       |               39 |        594 |             75 |      691 |              0.0077 |

### Stratified by source (Mantel-Haenszel OR for Female vs Male hire = 0.599)

| source          |   Female_n |   Female_hired |   Male_n |   Male_hired |   Female_rate_pct |   Male_rate_pct | low_n   |
|:----------------|-----------:|---------------:|---------:|-------------:|------------------:|----------------:|:--------|
| Company Website |         95 |              1 |      100 |           10 |              1.05 |           10    | True    |
| Indeed          |         87 |              8 |      103 |            5 |              9.2  |            4.85 | True    |
| Job Fair        |         97 |              2 |      110 |            4 |              2.06 |            3.64 | True    |
| LinkedIn        |        152 |              9 |      179 |           18 |              5.92 |           10.06 | True    |
| Naukri          |         94 |              9 |      101 |            9 |              9.57 |            8.91 | True    |
| Referral        |         69 |             10 |       98 |           29 |             14.49 |           29.59 | False   |

### Stratified by department (Mantel-Haenszel OR for Female vs Male hire = 0.577)

| department      |   Female_n |   Female_hired |   Male_n |   Male_hired |   Female_rate_pct |   Male_rate_pct | low_n   |
|:----------------|-----------:|---------------:|---------:|-------------:|------------------:|----------------:|:--------|
| Engineering     |        144 |              9 |      136 |           14 |              6.25 |           10.29 | True    |
| Finance         |        122 |              4 |      164 |           24 |              3.28 |           14.63 | True    |
| Human Resources |         64 |              5 |       50 |            5 |              7.81 |           10    | True    |
| Marketing       |        102 |              8 |      128 |           16 |              7.84 |           12.5  | True    |
| Operations      |         50 |              3 |       69 |            2 |              6    |            2.9  | True    |
| Product         |         52 |              6 |       72 |            6 |             11.54 |            8.33 | True    |
| Sales           |         60 |              4 |       72 |            8 |              6.67 |           11.11 | True    |

### Stratified by exp_band (Mantel-Haenszel OR for Female vs Male hire = 0.58)

| exp_band   |   Female_n |   Female_hired |   Male_n |   Male_hired |   Female_rate_pct |   Male_rate_pct | low_n   |
|:-----------|-----------:|---------------:|---------:|-------------:|------------------:|----------------:|:--------|
| <3 yrs     |        241 |             11 |      284 |           36 |              4.56 |           12.68 | False   |
| 3-7 yrs    |        149 |              9 |      163 |           15 |              6.04 |            9.2  | True    |
| 7+ yrs     |        204 |             19 |      244 |           24 |              9.31 |            9.84 | False   |

## Limits

- Non-binary (n = 46) is below the 50-person threshold: reported, flagged, not interpreted, never a reference group.
- Stratified cells are small; the Mantel-Haenszel odds ratio is a pooled summary, not a verdict.
- The repository does not show how the synthetic data were generated, so this analysis cannot say what causes any gap.
- The project spec states that a female disparity was planted (conversion factor 0.75). The generator notebook in this repo does not contain that factor, so this report does not treat it as established.
