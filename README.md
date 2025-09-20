# JunaidQ AI News — Monorepo v0.2

This repository contains **all code, documents, and strategies** for building the JunaidQ AI News channel.

## Structure
- `docs/`  
  - Original canvases: Project, Channel, Checklists, Decision Log, Risks, Backlog  
  - Updated docs: UPDATED_PLAN.md, UPDATED_ARCHITECTURE.md, UPDATED_MILESTONES.md, PRODUCT_ROADMAP.md  
  - Business docs: HIGH_VALUE_STRATEGY.md  
- `projects/junaidq-ai-news/` — existing code from export  
- `starter/` — Prefect starter pipeline (Daily Exec Summary, v1)

## Editorial Strategy (v0.2)
- **News only**, no evergreen content.
- **Videos per day**: 3 (Exec Summary, Topic of the Day, Paper/Tool Review).
- **Weekly**: Roundup video.
- **Approvals mandatory** at topic, script, and QC stages.

## Product Roadmap
- **v1 (0–3 months)**: Build Vid 1 (Daily Exec Summary).
- **v2 (3–6 months)**: Add Vid 2 + Vid 3, analytics, CI/CD.
- **v3 (6–12 months)**: Add Vid 4 (Weekly Roundup), monetize + scale.

## Getting Started
1. Install dependencies from `projects/` or `starter/`.
2. Copy `.env.example` to `.env` and add keys.
3. Run `python3 unified_pipeline_test.py --sample-script` to exercise the unified pipeline locally.
4. Run `scripts/bootstrap_langgraph.sh` to install LangGraph-specific dependencies and create `.env.langgraph`.
5. Execute `python3 -m src.unified_langgraph_pipeline --max-attempts 2` to try the LangGraph research+script pipeline with controlled regeneration and manual-review fallbacks.

TODO: add `youtube_transcript_api` to the pinned requirements so transcript-based boosts work in every environment.

## Git Setup
```bash
git init
git add .
git commit -m "Initial import v0.2"
git branch -M main
git remote add origin <YOUR_REMOTE>
git push -u origin main
```
