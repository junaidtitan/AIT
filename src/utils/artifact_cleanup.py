#!/usr/bin/env python3
"""
Artifact Cleanup Utility for AIT Pipeline

Manages cleanup of pipeline artifacts with configurable retention policies.
Supports both manual and automated cleanup during pipeline runs.
"""

import os
import shutil
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanupStrategy(Enum):
    """Cleanup strategies for different environments"""
    AGGRESSIVE = "aggressive"  # Keep only last 3 runs
    MODERATE = "moderate"      # Keep last 7 runs or 7 days
    CONSERVATIVE = "conservative"  # Keep last 14 runs or 30 days
    ARCHIVE = "archive"        # Move to archive instead of delete


@dataclass
class CleanupConfig:
    """Configuration for artifact cleanup"""
    strategy: CleanupStrategy = CleanupStrategy.MODERATE
    max_age_days: int = 7
    max_runs_to_keep: int = 7
    archive_before_delete: bool = True
    archive_location: str = "archived_pipeline_runs"
    dry_run: bool = False
    exclude_patterns: List[str] = None
    min_free_space_gb: float = 10.0  # Minimum free space to maintain

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = []

        # Adjust settings based on strategy
        if self.strategy == CleanupStrategy.AGGRESSIVE:
            self.max_age_days = 3
            self.max_runs_to_keep = 3
        elif self.strategy == CleanupStrategy.CONSERVATIVE:
            self.max_age_days = 30
            self.max_runs_to_keep = 14


class ArtifactCleaner:
    """Handles cleanup of pipeline artifacts"""

    def __init__(self, base_path: str = "/home/junaidqureshi/AIT",
                 config: Optional[CleanupConfig] = None):
        self.base_path = Path(base_path)
        self.config = config or CleanupConfig()
        self.archive_path = self.base_path / self.config.archive_location

        # Create archive directory if needed
        if self.config.archive_before_delete:
            self.archive_path.mkdir(exist_ok=True)

    def find_artifact_directories(self) -> List[Tuple[Path, datetime]]:
        """Find all pipeline artifact directories with their creation times"""
        artifact_dirs = []

        # Pattern for pipeline artifact directories
        pattern = "pipeline_artifacts_*"

        for dir_path in self.base_path.glob(pattern):
            if dir_path.is_dir():
                # Extract timestamp from directory name
                try:
                    # Format: pipeline_artifacts_YYYYMMDD_HHMMSS
                    timestamp_str = dir_path.name.replace("pipeline_artifacts_", "")
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                    # Check if excluded
                    if not self._is_excluded(dir_path):
                        artifact_dirs.append((dir_path, timestamp))
                except ValueError as e:
                    logger.warning(f"Could not parse timestamp from {dir_path.name}: {e}")

        # Sort by timestamp (oldest first)
        artifact_dirs.sort(key=lambda x: x[1])
        return artifact_dirs

    def _is_excluded(self, path: Path) -> bool:
        """Check if path matches any exclude patterns"""
        for pattern in self.config.exclude_patterns:
            if pattern in str(path):
                return True
        return False

    def get_cleanup_candidates(self) -> List[Path]:
        """Identify directories that should be cleaned up"""
        artifact_dirs = self.find_artifact_directories()
        candidates = []

        if not artifact_dirs:
            logger.info("No artifact directories found")
            return candidates

        current_time = datetime.now()
        total_dirs = len(artifact_dirs)

        # Apply retention policies
        for dir_path, timestamp in artifact_dirs:
            age_days = (current_time - timestamp).days

            # Check age-based retention
            if age_days > self.config.max_age_days:
                candidates.append(dir_path)
                logger.debug(f"{dir_path.name} is {age_days} days old (max: {self.config.max_age_days})")

        # Check count-based retention (keep most recent N)
        if total_dirs > self.config.max_runs_to_keep:
            excess_count = total_dirs - self.config.max_runs_to_keep
            # Add oldest directories to candidates if not already included
            for dir_path, _ in artifact_dirs[:excess_count]:
                if dir_path not in candidates:
                    candidates.append(dir_path)
                    logger.debug(f"{dir_path.name} exceeds max run count")

        return candidates

    def get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.isfile(filepath):
                        total += os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"Error calculating size of {path}: {e}")
        return total

    def format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"

    def archive_directory(self, source: Path) -> bool:
        """Archive directory before deletion"""
        try:
            archive_dest = self.archive_path / source.name

            if archive_dest.exists():
                logger.warning(f"Archive already exists: {archive_dest}")
                # Add timestamp suffix to avoid collision
                suffix = datetime.now().strftime("_%H%M%S")
                archive_dest = self.archive_path / f"{source.name}{suffix}"

            logger.info(f"Archiving {source.name} to {archive_dest}")
            shutil.move(str(source), str(archive_dest))
            return True

        except Exception as e:
            logger.error(f"Failed to archive {source}: {e}")
            return False

    def delete_directory(self, path: Path) -> bool:
        """Safely delete a directory"""
        try:
            size = self.get_directory_size(path)
            logger.info(f"Deleting {path.name} ({self.format_bytes(size)})")
            shutil.rmtree(path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def check_disk_space(self) -> float:
        """Check available disk space in GB"""
        try:
            stat = os.statvfs(self.base_path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            return free_gb
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return float('inf')  # Assume unlimited if check fails

    def cleanup(self, force: bool = False) -> Dict[str, any]:
        """
        Perform cleanup of artifact directories

        Args:
            force: Override dry_run setting

        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            'directories_found': 0,
            'candidates_identified': 0,
            'directories_archived': 0,
            'directories_deleted': 0,
            'space_freed_bytes': 0,
            'errors': []
        }

        # Check disk space
        free_space_gb = self.check_disk_space()
        logger.info(f"Current free disk space: {free_space_gb:.2f} GB")

        # Find cleanup candidates
        candidates = self.get_cleanup_candidates()
        stats['candidates_identified'] = len(candidates)

        if not candidates:
            logger.info("No directories need cleanup")
            return stats

        # Calculate total space to be freed
        total_size = sum(self.get_directory_size(d) for d in candidates)
        logger.info(f"Found {len(candidates)} directories to clean ({self.format_bytes(total_size)})")

        # Perform cleanup
        for dir_path in candidates:
            size = self.get_directory_size(dir_path)

            if self.config.dry_run and not force:
                logger.info(f"[DRY RUN] Would clean: {dir_path.name} ({self.format_bytes(size)})")
                continue

            # Archive or delete based on configuration
            success = False
            if self.config.archive_before_delete and self.config.strategy != CleanupStrategy.ARCHIVE:
                if self.archive_directory(dir_path):
                    stats['directories_archived'] += 1
                    success = True
            elif self.config.strategy == CleanupStrategy.ARCHIVE:
                if self.archive_directory(dir_path):
                    stats['directories_archived'] += 1
                    success = True
            else:
                if self.delete_directory(dir_path):
                    stats['directories_deleted'] += 1
                    success = True

            if success:
                stats['space_freed_bytes'] += size
            else:
                stats['errors'].append(str(dir_path))

        # Clean up old archives if needed
        if free_space_gb < self.config.min_free_space_gb:
            logger.warning(f"Low disk space detected. Cleaning old archives...")
            self._cleanup_archives()

        # Log summary
        logger.info(f"Cleanup complete: {stats['directories_archived']} archived, "
                   f"{stats['directories_deleted']} deleted, "
                   f"{self.format_bytes(stats['space_freed_bytes'])} freed")

        return stats

    def _cleanup_archives(self):
        """Clean up old archives when disk space is low"""
        if not self.archive_path.exists():
            return

        archive_dirs = []
        for dir_path in self.archive_path.glob("pipeline_artifacts_*"):
            if dir_path.is_dir():
                # Get modification time
                mtime = datetime.fromtimestamp(dir_path.stat().st_mtime)
                archive_dirs.append((dir_path, mtime))

        # Sort by age (oldest first)
        archive_dirs.sort(key=lambda x: x[1])

        # Delete oldest archives
        for dir_path, _ in archive_dirs[:len(archive_dirs)//2]:  # Delete oldest half
            if self.delete_directory(dir_path):
                logger.info(f"Deleted old archive: {dir_path.name}")

    def save_config(self, path: Optional[str] = None):
        """Save current configuration to JSON file"""
        config_path = Path(path) if path else self.base_path / "cleanup_config.json"

        config_dict = {
            'strategy': self.config.strategy.value,
            'max_age_days': self.config.max_age_days,
            'max_runs_to_keep': self.config.max_runs_to_keep,
            'archive_before_delete': self.config.archive_before_delete,
            'archive_location': self.config.archive_location,
            'dry_run': self.config.dry_run,
            'exclude_patterns': self.config.exclude_patterns,
            'min_free_space_gb': self.config.min_free_space_gb
        }

        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)

        logger.info(f"Configuration saved to {config_path}")

    @classmethod
    def load_config(cls, path: str) -> 'ArtifactCleaner':
        """Load configuration from JSON file"""
        config_path = Path(path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            config_dict = json.load(f)

        # Convert strategy string back to enum
        config_dict['strategy'] = CleanupStrategy(config_dict['strategy'])

        config = CleanupConfig(**config_dict)
        base_path = config_path.parent if config_path.parent.name == "AIT" else "/home/junaidqureshi/AIT"

        return cls(base_path=base_path, config=config)


def cleanup_after_pipeline_run(pipeline_name: str = "pipeline",
                               keep_current: bool = True,
                               strategy: CleanupStrategy = CleanupStrategy.MODERATE):
    """
    Helper function to be called after pipeline runs

    Args:
        pipeline_name: Name of the pipeline that just ran
        keep_current: Whether to keep the current run's artifacts
        strategy: Cleanup strategy to use
    """
    logger.info(f"Running post-pipeline cleanup for {pipeline_name}")

    config = CleanupConfig(
        strategy=strategy,
        dry_run=False,
        archive_before_delete=True
    )

    if keep_current:
        # Add current run to exclude patterns
        current_timestamp = datetime.now().strftime("%Y%m%d_%H")
        config.exclude_patterns.append(f"pipeline_artifacts_{current_timestamp}")

    cleaner = ArtifactCleaner(config=config)
    stats = cleaner.cleanup()

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean up pipeline artifacts")
    parser.add_argument("--strategy", type=str,
                       choices=["aggressive", "moderate", "conservative", "archive"],
                       default="moderate",
                       help="Cleanup strategy to use")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be cleaned without actually doing it")
    parser.add_argument("--force", action="store_true",
                       help="Force cleanup even in dry-run mode")
    parser.add_argument("--save-config", type=str,
                       help="Save configuration to specified file")
    parser.add_argument("--load-config", type=str,
                       help="Load configuration from specified file")

    args = parser.parse_args()

    if args.load_config:
        cleaner = ArtifactCleaner.load_config(args.load_config)
    else:
        config = CleanupConfig(
            strategy=CleanupStrategy(args.strategy),
            dry_run=args.dry_run
        )
        cleaner = ArtifactCleaner(config=config)

    if args.save_config:
        cleaner.save_config(args.save_config)

    # Perform cleanup
    stats = cleaner.cleanup(force=args.force)

    # Print summary
    print("\nCleanup Summary:")
    print(f"  Candidates identified: {stats['candidates_identified']}")
    print(f"  Directories archived: {stats['directories_archived']}")
    print(f"  Directories deleted: {stats['directories_deleted']}")
    print(f"  Space freed: {cleaner.format_bytes(stats['space_freed_bytes'])}")

    if stats['errors']:
        print(f"  Errors: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"    - {error}")