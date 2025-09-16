# Pipeline Artifact Cleanup Documentation

## Overview
The AIT pipeline generates artifacts during each run (scripts, audio files, research data, etc.). To prevent disk space issues, we've implemented an automated cleanup system.

## Components

### 1. Cleanup Utility
- **Location**: `src/utils/artifact_cleanup.py`
- **Features**:
  - Configurable retention policies
  - Multiple cleanup strategies
  - Archive before delete option
  - Disk space monitoring
  - Dry-run mode for testing

### 2. Cleanup Strategies

#### Aggressive
- Keep last 3 pipeline runs
- Delete artifacts older than 3 days
- Best for development environments

#### Moderate (Default)
- Keep last 5 pipeline runs
- Delete artifacts older than 7 days
- Balanced approach for most use cases

#### Conservative
- Keep last 14 pipeline runs
- Delete artifacts older than 30 days
- Best for production where history matters

#### Archive
- Move to archive directory instead of deleting
- Useful for compliance/audit requirements

### 3. Configuration
- **File**: `cleanup_config.json`
- **Settings**:
  ```json
  {
    "strategy": "moderate",
    "max_age_days": 7,
    "max_runs_to_keep": 5,
    "archive_before_delete": true,
    "archive_location": "archived_pipeline_runs",
    "min_free_space_gb": 5.0
  }
  ```

## Usage

### Manual Cleanup

#### Dry Run (Preview)
```bash
python3 src/utils/artifact_cleanup.py --dry-run
```

#### Execute Cleanup
```bash
python3 src/utils/artifact_cleanup.py --strategy moderate
```

#### Force Aggressive Cleanup
```bash
python3 src/utils/artifact_cleanup.py --strategy aggressive --force
```

### Automated Cleanup

#### After Pipeline Runs
Run the cleanup utility after executing the unified pipeline:
```bash
python3 unified_pipeline_test.py --sample-script
python3 src/utils/artifact_cleanup.py --strategy moderate
```

#### Via Shell Script
```bash
./scripts/cleanup_artifacts.sh
```

#### Via Cron Job
Add to crontab for daily cleanup at 2 AM:
```bash
0 2 * * * /home/junaidqureshi/AIT/scripts/cleanup_artifacts.sh >> /var/log/ait_cleanup.log 2>&1
```

### Integration in Python Code

```python
from src.utils.artifact_cleanup import cleanup_after_pipeline_run, CleanupStrategy

# After pipeline completion
stats = cleanup_after_pipeline_run(
    pipeline_name="my_pipeline",
    keep_current=True,
    strategy=CleanupStrategy.MODERATE
)

print(f"Freed {stats['space_freed_bytes'] / (1024**3):.2f} GB")
```

## Directory Structure

```
AIT/
├── pipeline_artifacts_YYYYMMDD_HHMMSS/  # Active artifacts
├── archived_pipeline_runs/              # Archived artifacts
│   └── pipeline_artifacts_*/           # Old runs moved here
└── cleanup_config.json                  # Configuration file
```

## Best Practices

1. **Development**: Use aggressive strategy, run cleanup after each test
2. **Production**: Use moderate/conservative strategy with archiving
3. **Low Disk Space**: Script automatically cleans archives when < 5GB free
4. **Important Runs**: Add to exclude_patterns in config to preserve
5. **Monitoring**: Check cleanup logs regularly for errors

## Troubleshooting

### Cleanup Not Working
- Check permissions on artifact directories
- Verify cleanup_config.json is valid JSON
- Run with --dry-run to see what would be cleaned

### Too Aggressive
- Adjust max_age_days and max_runs_to_keep in config
- Switch to conservative strategy
- Enable archive_before_delete

### Disk Still Full
- Check archived_pipeline_runs/ directory
- Consider more aggressive strategy
- Manually clean other large files (logs, temp files)

## Future Improvements
- [ ] Cloud storage integration for long-term archives
- [ ] Compress artifacts before archiving
- [ ] Email alerts for cleanup failures
- [ ] Web dashboard for artifact management
- [ ] Selective artifact preservation (keep only final videos)
