# Recovery State — 2025-09-17 20:45 UTC

This file captures the exact repository state after restoring the 2025-09-16 backup and replaying unrecoverable work. Use it as the single source of truth when picking up the effort tomorrow so no context is lost.

---

## 1. Repository Status Snapshot

- **Git branch**: `main`
- **relationship to remote**: `main...origin/main [ahead 3]`
- **uncommitted modifications (tracked files)**:
  - `docs/VERSION_HISTORY.md`
  - `src/config.py`
  - `src/editorial/script_daily.py`
  - `src/produce/shot_list_generator.py`
  - `src/produce/shotstack_dynamic.py`
  - `templates/prompt_script_daily.txt`
  - `unified_pipeline_test.py`
- **tracked deletions (expected)**: the old `pipeline_artifacts_20250916_*` directories and associated JSON/MP3/MP4 summaries were removed during cleanup.
- **untracked files (new/recovered work)**:
  - Documentation: `GOOGLE_SHEETS_SETUP.md`, `YOUTUBE_TRENDING_BOOST.md`
  - Debug helpers: `debug_gpt_response.json`, `pipeline_test.log`, `run_pipeline_test.sh`
  - Editorial modules: `src/editorial/{cta_generator.py,story_analyzer.py,structure_validator.py,text_utils.py,tone_enhancer.py,transition_generator.py}`
  - Ingest modules: `src/ingest/{simple_sheets_manager.py,youtube_trending.py,youtube_trending_simple.py}`
  - Produce modules: `src/produce/visual_styles.py`
  - Templates: `templates/{futurist_briefing_main.txt,cta_patterns.json,transition_phrases.json,segment_templates/}`
  - Tests: `tests/`, `test_pipeline_minimal.py`, `test_pipeline_stages.py`
  - Pipeline helpers: `unified_pipeline_test_partial.py`
  - Fresh pipeline outputs: `pipeline_artifacts_20250917_{213903,214221}/`

All of these correspond to the Futurist Briefing revamp, GPT-5 shot list parsing, Runway/Shotstack overlay work, and Sheets/YT trending ingestion. They must be recommitted to recreate the missing Git history.

---

## 2. Source-of-Truth Files (recovered & verified)

| Area | Files |
|------|-------|
| **Editorial** | `src/editorial/script_daily.py`, `story_analyzer.py`, `structure_validator.py`, `tone_enhancer.py`, `transition_generator.py`, `cta_generator.py`, `text_utils.py` |
| **Produce** | `src/produce/shot_list_generator.py`, `shotstack_dynamic.py`, `visual_styles.py` |
| **Ingest** | `src/ingest/simple_sheets_manager.py`, `youtube_trending.py`, `youtube_trending_simple.py` |
| **Templates** | `templates/futurist_briefing_main.txt`, `templates/segment_templates/{news,funding,policy,research}.txt`, `templates/cta_patterns.json`, `templates/transition_phrases.json`, `templates/prompt_script_daily.txt` |
| **Pipeline Orchestrator** | `unified_pipeline_test.py`, `unified_pipeline_test_partial.py`, `run_pipeline_test.sh`, `pipeline_test.log` |
| **Docs** | `GOOGLE_SHEETS_SETUP.md`, `YOUTUBE_TRENDING_BOOST.md`, `docs/VERSION_HISTORY.md` (updated entry pending) |
| **Tests** | `tests/` package, `test_pipeline_minimal.py`, `test_pipeline_stages.py` |

These files mirror the work logged in the missing commits (`7c48b02` through `89fe9fc`) and must be recommitted.

---

## 3. Immediate To‑Do List

1. **Validate the pipeline**
   - `python3 -m pytest tests`
   - `python3 unified_pipeline_test.py --output-dir pipeline_artifacts_$(date +%Y%m%d_%H%M%S)`
   - Confirm GPT‑5 shot list parsing works and the final MP4 renders with logos/text overlays.

2. **Recreate documentation**
   - Rewrite `docs/WORKLOG.md` summarising the latest artifacts/pipeline behaviour.
   - Extend `docs/VERSION_HISTORY.md` with an entry describing the recovery.

3. **Recommit recovered work**
   - Stage modified/untracked files.
   - Create logically grouped commits (or one comprehensive commit) describing the restorations.
   - Decide whether to keep or discard `debug_gpt_response.json` and other temporary helpers before committing.

4. **Synchronise with GitHub**
   - Push new commits to `origin/main` (likely `git push --force-with-lease` once history is restored).
   - Tag a restore point if desired.

5. **Create a fresh backup**
   - `tar -czf AIT_backup_$(date +%Y%m%d_%H%M%S).tar.gz ./AIT` once everything is green.

---

## 4. Environment & Configuration Notes

- `.env.vm` currently contains the reference configuration:
  ```bash
  APPROVAL_MODE=auto
  TIMEZONE=America/Los_Angeles
  PUBLISH_HOUR_PT=18
  RSS_FEEDS=https://openai.com/blog/rss,http://export.arxiv.org/rss/cs.AI
  ELEVENLABS_VOICE_ID=wBXNqKUATyqu0RtYt25i
  YOUTUBE_UPLOAD=true
  YOUTUBE_CLIENT_SECRETS=./oauth_client.json
  YOUTUBE_TOKEN_JSON=./oauth_token.json
  MODEL_NAME=gpt-4o
  MIN_WORDS=900
  MAX_WORDS=1100
  ```
- Ensure secrets (`OPENAI_API_KEY`, `SHOTSTACK_API_KEY`, `ELEVENLABS_API_KEY`, `RUNWAY_API_KEY`, Sheets credentials) are exported before running Stage 4+.
- Reconfirm Google Sheets structure matches expectations in `src/ingest/simple_sheets_manager.py` (Sources tab, Companies tab, Scoring tab).

---

## 5. Pipeline Verification Checklist (post-recovery)

- [ ] `tests/test_pipeline_stages.py` → ensures each stage returns expected data structures.
- [ ] `tests/test_pipeline_minimal.py` → smoke-test script generation.
- [ ] `python3 unified_pipeline_test.py` → end-to-end run with fresh artifacts.
- [ ] Inspect `pipeline_artifacts_<timestamp>/02_script/script_text_*.txt` to ensure the Futurist briefing format is intact (numbered blitz, what/so-what/now-what, polished CTA).
- [ ] Inspect `pipeline_artifacts_<timestamp>/06_timeline/timeline_*.json` for logo/text/screenshot/PiP tracks.
- [ ] Verify final MP4 (`/08_final/`) for logos, text overlays, and dynamic motion.

---

## 6. Outstanding Questions / Decisions

- Do we keep `debug_gpt_response.json`, `pipeline_test.log`, `run_pipeline_test.sh` under version control or treat them as local helpers only?
- Do we need the older pipeline artifact directories back in history? If not, commit the deletions; otherwise, restore before committing.
- Once documentation is updated, confirm whether a new `README` entry is needed for Sheets/YT trending configuration.

---

## 7. Quick Command Reference

```bash
# Stage & commit all recovered files once validated
git add docs/VERSION_HISTORY.md src/config.py src/editorial/*.py src/ingest/*.py \
        src/produce/*.py templates/* unified_pipeline_test.py unified_pipeline_test_partial.py \
        tests/ GOOGLE_SHEETS_SETUP.md YOUTUBE_TRENDING_BOOST.md

# Commit with a descriptive message
git commit -m "Restore Futurist briefing + Runway integration after backup rollback"

# Push (force-with-lease recommended because history was rewound earlier)
git push --force-with-lease origin main

# Run end-to-end after committing to produce fresh artifacts
python3 unified_pipeline_test.py --output-dir pipeline_artifacts_$(date +%Y%m%d_%H%M%S)
```

Keep this file updated if more changes land before you break for the day. Delete it once the recovered work is safely in Git and a new backup has been taken.

