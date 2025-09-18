# LangGraph Implementation Plan — Stage 1 & Stage 2 (Production Grade)

## 1. Environment & Dependency Baseline
- Introduce pinned dependency manifest (`pyproject.toml` or `requirements.lock`) covering: `langgraph==0.6.7`, `langchain-core==0.3.76`, `langchain==0.3.27`, `langchain-openai==0.3.33`, `httpx==0.27.2`, `pydantic==2.7.4`, `orjson==3.10.7`, `tenacity==8.3.0`, `aiofiles==23.2.1`, `anyio==4.4.0`, `python-dotenv==1.0.1`, `xxhash==3.5.0` (allow transitive installs of `langgraph-checkpoint` and `langgraph-sdk` to satisfy `langgraph` runtime needs).
- Add `scripts/bootstrap_langgraph.sh` to install dependencies, export `LANGCHAIN_TRACING_V2`, `LANGGRAPH_STUDIO_TOKEN`, `LANGGRAPH_PROJECT`, and create `.env.langgraph` template.
- Extend `src/config.py` with LangGraph toggles (`USE_LANGGRAPH`, `LANGGRAPH_CHECKPOINT_DIR`, async timeouts, retry factors); document defaults in `docs/UPDATED_PLAN.md`.

## 2. Shared Models & Utilities
- Create `src/models/stories.py` and `src/models/scripts.py` with `pydantic.BaseModel` definitions (`StorySource`, `StoryInput`, `StoryEnriched`, `ScoredStory`, `SegmentDraft`, `ScriptDraft`, `ValidationReport`, `PipelineDiagnostics`).
- Implement `src/utils/content_normalizer.py` for canonical URLs, dedupe hashing, token cleansing; add `src/utils/async_helpers.py` with bounded semaphore + `tenacity` retry utilities.
- Define `src/utils/errors.py` containing `StageFailure`, `FetchTimeout`, `ValidationFailure`; update legacy pipeline to raise structured exceptions instead of silent fallbacks.

## 3. Stage 1 Refactors (Pre-Graph)
- Convert `src/ingest/rss_arxiv.py` to expose async `fetch_rss_async` (via `httpx.AsyncClient`, per-feed timeout, retries, structured errors) while preserving sync wrapper.
- Update `src/ingest/simple_sheets_manager.py` to return `List[StorySource]`, execute Google Sheets read in thread pool (`anyio.to_thread.run_sync`), and emit status enums rather than prints.
- Wrap YouTube trending ingestion with async interface returning typed payloads.
- Enhance `src/rank/select.py` to consume dynamic weights (sheet/config), perform dedupe using `content_normalizer`, and return `List[ScoredStory]`.
- Add regression coverage in `tests/test_stage1_pregraph.py` for empty feeds, partial fetch failures, dedupe collisions, and weight overrides.

## 4. Stage 1 Graph Construction
- Create `src/graphs/__init__.py` exporting `build_research_graph`.
- Define `ResearchState(BaseModel)` in `src/graphs/state.py` capturing `sources`, `raw`, `enriched`, `scored`, `selected`, `diagnostics`, `errors`, `checkpoints`.
- Implement node modules:
  - `nodes/fetchers.py`: async RSS, Sheets, YouTube nodes returning stories + diagnostics.
  - `nodes/mergers.py`: merge, dedupe, provenance tracking.
  - `nodes/enrichers.py`: full-text extraction with concurrency guard and readability cleanup.
  - `nodes/rankers.py`: scoring + top-K selection.
- Compose `src/graphs/research_graph.py` using `StateGraph` with parallel fetch subgraph, conditional edges for missing sources, and checkpoint configuration targeting `LANGGRAPH_CHECKPOINT_DIR` (local/GCS).
- Export LangGraph manifest via `GraphApp(workflows={"research": graph})` and save to `src/graphs/langgraph_app.json` for Studio.

## 5. Stage 2 Refactors (Pre-Graph)
- Decompose `ScriptGenerator` into pure helpers: `analyze_stories`, `build_segments`, `compose_script`, `apply_tone`, `validate_script`, `finalize_script`.
- Lazy-load templates with `functools.lru_cache`; raise explicit missing-template errors.
- Update tone/CTA/transition utilities to accept typed inputs and emit typed outputs.
- Expand `StructureValidator` to return severity, metrics dict, and recommended action codes within `ValidationReport`.
- Extend `tests/test_editorial.py` to cover validator failure, tone disabled paths, regeneration scenarios, missing-template errors.

## 6. Stage 2 Graph Construction
- Define `ScriptState(BaseModel)` in `src/graphs/state.py` including `selected_stories`, `analysis`, `segments`, `drafts`, `tone_pass`, `validation`, `final_script`, `attempts`, `errors`, `human_review`.
- Implement nodes:
  - `nodes/analyzers.py`: wraps `analyze_stories`.
  - `nodes/segment_builder.py`: builds segments (supports parallel generation for deep dives).
  - `nodes/prompt_generators.py`: materialize `langchain` prompt objects for Studio edits.
  - `nodes/tone.py`: conditional tone node honoring config.
  - `nodes/validator.py`: runs structure validation; branches depending on severity.
  - `nodes/regenerate.py`: performs controlled regeneration when validation fails.
  - `nodes/assembly.py`: composes final script artifacts.
- Compose `src/graphs/script_graph.py` with conditional paths (manual review hook, regeneration loop) and checkpoint metadata capturing drafts.

## 7. Unified Pipeline & Toggle
- Build `src/graphs/pipeline_graph.py` to link research + script graphs, mapping `ResearchState.selected` to `ScriptState.selected_stories`.
- Add CLI `src/unified_langgraph_pipeline.py` with resume/checkpoint options, artifact path overrides, and sanity checks.
- Update `unified_pipeline_test.py` to honor `--use-langgraph`, invoke `GraphApp`, and persist artifacts matching legacy structure for diffing.
- Maintain legacy pipeline behind `USE_LANGGRAPH` config for rollback.

## 8. Instrumentation & Studio Integration
- Implement `src/graphs/instrumentation.py` registering logging/telemetry callbacks (console, Python logging, optional OTEL).
- Create `LANGGRAPH.yaml` describing workflows, input schema, env vars, checkpoint locations for Studio.
- Document Studio usage (launch command, prompt editing, checkpoint resume) in `docs/UPDATED_PLAN.md`.

## 9. Testing, QA, Benchmarking
- Add `tests/test_research_graph.py` (pytest-asyncio) mocking fetchers to validate state transitions, checkpoint writes, error propagation.
- Add `tests/test_script_graph.py` covering happy path, validator failure, regeneration, manual review branch.
- Create integration test `tests/test_langgraph_pipeline.py` comparing pipeline outputs against golden artifacts.
- Implement `scripts/verify_langgraph.sh` running unit + integration suites and `langgraph` smoke test.
- Benchmark parallel ingestion vs. legacy sequential; record metrics in `docs/PIPELINE_BENCHMARK_ANALYSIS.md`.

## 10. Documentation & Rollout
- Refresh `README.md`, `PROJECT_STATUS_20250918.md`, and `docs/UPDATED_PLAN.md` with LangGraph instructions and status.
- Produce rollout checklist (parallel run duration, comparison tasks, rollback steps).
- Prepare training collateral (e.g., Loom walkthrough) for Studio prompt editing and manual review flow.

## 11. Operationalization
- Configure checkpoint persistence to GCS when `ASSET_CACHE_BUCKET` present; reuse upload helper from voiceover stage.
- Schedule automation (Prefect/Cron) invoking LangGraph pipeline with resume support.
- Set up monitoring hooks (log alerts, Slack notifications on `StageFailure`, summary artifacts to approval channel).
- Plan staged cutover: run dual pipelines, compare outputs, flip `USE_LANGGRAPH` to `true`, retain legacy for emergency rollback, then deprecate once stable.

---

# Execution Plan by Week

## Week 0 — Preparation
- Finalize dependency manifest, run bootstrap script, update documentation with new env vars.

## Week 1 — Shared Infrastructure
- Implement shared models/utilities/errors.
- Refactor Stage 1 fetchers + ranking for async typed outputs.
- Add `tests/test_stage1_pregraph.py` and ensure legacy pipeline still passes.

## Week 2 — Stage 1 Graph
- Build `ResearchState`, nodes, and `research_graph` with checkpointing + logging.
- Export `langgraph_app.json` and add `tests/test_research_graph.py`.
- Benchmark research graph vs. legacy ingestion.

## Week 3 — Stage 2 Refactor
- Decompose `ScriptGenerator`, update validators, extend editorial tests.
- Confirm legacy sequential pipeline remains functional.

## Week 4 — Stage 2 Graph
- Implement `ScriptState`, nodes, regeneration/manual review logic, and `script_graph`.
- Add `tests/test_script_graph.py` for graph-level coverage.

## Week 5 — Unified Graph & Tooling
- Compose `pipeline_graph`, add CLI runner, toggle integration.
- Update `unified_pipeline_test.py`, create `tests/test_langgraph_pipeline.py`.
- Finalize instrumentation, Studio manifest, bootstrap/verify scripts.

## Week 6 — Documentation & Rollout Prep
- Refresh docs, status report, plan appendices.
- Capture benchmark deltas and update `PIPELINE_BENCHMARK_ANALYSIS.md`.
- Share training material (Studio usage, manual review flow).

## Week 7 — Parallel Run & QA
- Run LangGraph + legacy pipelines side-by-side; compare artifacts.
- Resolve discrepancies, validate Studio prompt edits with stakeholders.
- Harden alerting/checkpoint resume procedures.

## Week 8 — Production Cutover
- Enable `USE_LANGGRAPH=true` once parity proven.
- Monitor metrics, respond to alerts, document fallback.
- Conduct post-launch review, log follow-up backlog items.

## Post-Launch
- Continue enhancement backlog (adaptive scoring, additional sources, script A/B paths).
- Integrate checkpoints with Prefect/monitoring, remove obsolete legacy paths after stabilization.
