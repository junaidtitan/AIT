# Product Roadmap — JunaidQ AI News Channel

This roadmap reflects the clarified strategy: **AI News only**, 4 video formats, approvals required, no evergreen content. It is structured into 3 major versions across 12 months.

---

## 🎬 Video Formats
- **Vid 1 (Daily Exec Summary)**: What happened yesterday in AI — fast, concise, benchmark/news focus.
- **Vid 2 (Topic of the Day)**: e.g. “5 astonishing achievements in AI in the last 30 days” with visual references.
- **Vid 3 (Paper/Tool Review)**: Research paper summaries or tool comparisons.
- **Vid 4 (Weekly Roundup)**: Drama, comments, interviews, funding, acquisitions, breakthroughs.

---

## v1 (Months 0–3) — MVP: Daily Exec Summary
- Build Vid 1 end-to-end (ingest → approvals → script → TTS → video → upload).
- Approvals: **mandatory** (topic, script, QC before publish).
- Infra: Prefect Cloud, GCP/AWS serverless stack, Postgres, GCS/S3.
- Outputs: 1 daily video (Vid 1 only).
- Costs: ignored, assume optimized unlimited budget.
- Deliverable: **First automated daily exec summary video.**

---

## v2 (Months 3–6) — Expanded Formats + Analytics
- Add **Vid 2 (Topic of the Day)**.
- Add **Vid 3 (Paper/Tool Review)**.
- Features:
  - Title + thumbnail A/B testing.
  - Daily Slack/Email reporting digest.
  - Define unique positioning (voice, branding, visual identity).
- Add **GitHub Actions CI/CD**:
  - Lint + test on PRs.
  - Auto-deploy Prefect flows.
  - Sync docs if needed.
- Outputs: 2–3 videos/day.

---

## v3 (Months 6–12) — Scale & Weekly Format
- Add **Vid 4 (Weekly Roundup)**.
- Full analytics optimization loop:
  - Hook retention tuning.
  - Thumbnail/title CTR optimization.
- Monetization focus:
  - Sponsorships, affiliates, courses planning.
- Governance:
  - Optional automation of approvals as fallback.
- Multi-format scaling (optionally Shorts).
- Outputs: 3 daily + 1 weekly (~22–25 vids/week).

---

## 🧩 Key Principles
- **No evergreen content** — current AI news only.
- **Approvals mandatory** — Junaid reviews and can replace content.
- **Focus on YouTube** only in v1; other platforms later.
- **Ignore costs** (build production-grade with optimized unlimited budget).

---

## 📅 Milestone Summary
- **Month 1–3**: Daily Exec Summary automated.
- **Month 3–6**: Add Topic of the Day + Paper/Tool Review; analytics + CI/CD.
- **Month 6–12**: Add Weekly Roundup; monetize + scale.
