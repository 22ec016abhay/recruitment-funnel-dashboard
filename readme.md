# 📊 Recruitment Funnel & Source-of-Hire Analytics

> **End-to-End People Analytics Dashboard & SQL ETL Pipeline**  
> *Analyzing 1,500 candidate lifecycles to optimize hiring efficiency, conversion bottlenecks, and recruiter velocity.*

---

## 📌 Executive Summary & Key Findings
1. **Source Efficiency vs. Volume:** Employee Referrals deliver the highest conversion rate (~14.2%), while LinkedIn acts as the primary volume driver (42 total hires).
2. **Funnel Bottlenecks:** The steepest conversion drop occurs at the **Interview-to-Offer stage (33.3% pass rate)**, highlighting an opportunity to refine early candidate screening.
3. **Velocity Variance:** Recruiter time-to-hire ranges from 28.4 to 44.1 days ($n \ge 10$), indicating a 15.7-day speed spread that requires workload-adjusted evaluation.
4. **Cohort Maturity Insight:** Unadjusted monthly hire rates for recent cohorts (Aug–Sep 2026) show artificial drop-offs due to active `In Process` candidates; mature cohort filtering reveals a stable ~9% baseline conversion.

---

## 🛠 Project Architecture & Tech Stack
- **Data Engineering:** Python (`pandas`), SQLite3
- **Database & Querying:** SQLite syntax compliance, Views, Window Functions (`LAG`, `RANK`)
- **BI & Visualization:** Power BI Desktop (Midnight Teal Custom Theme, DAX Measures, RLS)
- **AI Infrastructure (Prep):** Privacy-compliant schema design (`schema.md`), parameter validation, read-only connection isolation.