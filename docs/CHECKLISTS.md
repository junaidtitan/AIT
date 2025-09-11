# Checklists

## Owner Checklist (Setup)
1. Enable YouTube Data API v3; create OAuth client (client ID/secret).
2. Generate API keys: OpenAI, ElevenLabs.
3. Create Slack webhook URL for approvals.
4. Provision Postgres (Cloud SQL/RDS), GCS/S3 bucket, Pub/Sub/SQS.
5. Create Prefect Cloud workspace + API key.
6. Provide brand kit (color `#0EA5E9`, Inter font, logo, intro animation).

## First-Run Checklist
- [ ] Cloud project created and billing enabled.
- [ ] Service account created + IAM roles applied.
- [ ] Secrets stored in Secret Manager.
- [ ] DB initialized with schema.
- [ ] GCS/S3 bucket created.
- [ ] Prefect worker deployed and healthy.
- [ ] `.env` populated locally for testing.
- [ ] Dry run of Vid 1 (Daily Exec Summary) with topic + script approvals.
- [ ] Pictory/CapCut API test with placeholder video.
- [ ] YouTube upload test (Unlisted).

## Content Review Checklist (QC Gate)
- [ ] All claims sourced (≥2 sources where possible).
- [ ] No policy-violating content (hate, medical, financial advice).
- [ ] Stock assets licensed + IDs tracked.
- [ ] Synthetic content label applied.
- [ ] Captions auto-generated + synced.
- [ ] Thumbnail text ≤4 words, no clickbait, brand color applied.
- [ ] Final review by Junaid.

## Next 48h Enhancements
- [ ] Slack interactive approvals (buttons).
- [ ] Thumbnail A/B testing (v2).
- [ ] Title optimization (bandit) (v2).
- [ ] Daily analytics digest (v2).
- [ ] CapCut CLI fallback rendering.
