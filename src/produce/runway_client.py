"""
RunwayML API Client for AI-powered video generation
Production-ready with retries, caching, and error handling
"""

import os
import httpx
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import backoff
from google.cloud import storage
import hashlib
import json


class RunwayAssetType(Enum):
    """RunwayML asset generation types"""
    VIDEO_GEN = "gen3_turbo"  # Text-to-video
    STYLE_TRANSFER = "style_transfer"
    GREEN_SCREEN = "green_screen"
    MOTION_TRACK = "motion_tracking"
    UPSCALE = "super_resolution"
    INPAINT = "inpainting"
    COMPOSE = "compose"


@dataclass
class RunwayJob:
    """RunwayML job tracking"""
    job_id: str
    status: str
    job_type: RunwayAssetType
    result_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None


class RunwayMLClient:
    """
    Production-ready RunwayML API client with:
    - Exponential backoff retry logic
    - GCS caching for results
    - Job status polling
    - Error handling
    """

    def __init__(self):
        """Initialize RunwayML client with API credentials"""
        self.api_key = os.environ.get('RUNWAY_API_KEY')
        if not self.api_key:
            raise ValueError("RUNWAY_API_KEY not found in environment")

        self.base_url = "https://api.runwayml.com/v1"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        # GCS for caching
        try:
            self.gcs_client = storage.Client()
            self.cache_bucket = self.gcs_client.bucket('yta-runway-cache')
        except Exception as e:
            print(f"Warning: GCS caching disabled: {e}")
            self.cache_bucket = None

    @backoff.on_exception(backoff.expo, httpx.HTTPError, max_tries=3)
    async def generate_video(self,
                            prompt: str,
                            duration: float = 5.0,
                            style: str = "futuristic",
                            seed: Optional[int] = None) -> RunwayJob:
        """
        Generate video from text using Gen-3 Turbo

        Args:
            prompt: Text description of desired video
            duration: Video duration in seconds (max 10)
            style: Visual style modifier
            seed: Optional seed for reproducibility

        Returns:
            RunwayJob object for tracking
        """
        # Add style modifiers for consistency
        enhanced_prompt = f"{prompt}, {style} style, cinematic lighting, high quality, 4K"

        # Cache check
        cache_key = self._generate_cache_key(enhanced_prompt, duration, seed)
        cached_result = await self._check_cache(cache_key)
        if cached_result:
            return cached_result

        # API request
        payload = {
            "prompt": enhanced_prompt,
            "duration_seconds": min(duration, 10),  # Max 10 seconds
            "aspect_ratio": "16:9",
            "motion_amount": "medium",
            "camera_movement": "dynamic"
        }

        if seed is not None:
            payload["seed"] = seed

        response = await self.client.post(
            f"{self.base_url}/gen3/turbo",
            json=payload
        )

        response.raise_for_status()
        data = response.json()

        return RunwayJob(
            job_id=data.get("id", "unknown"),
            status="processing",
            job_type=RunwayAssetType.VIDEO_GEN,
            metadata={
                "prompt": prompt,
                "duration": duration,
                "cache_key": cache_key
            }
        )

    async def enhance_video(self,
                           video_url: str,
                           upscale: bool = True,
                           stabilize: bool = True,
                           style: Optional[str] = None) -> RunwayJob:
        """
        Enhance existing video with AI

        Args:
            video_url: URL of video to enhance
            upscale: Apply super resolution
            stabilize: Apply stabilization
            style: Optional style transfer

        Returns:
            RunwayJob object for tracking
        """
        payload = {
            "input_url": video_url,
            "operations": []
        }

        if upscale:
            payload["operations"].append({
                "type": "upscale",
                "scale": 2
            })

        if stabilize:
            payload["operations"].append({
                "type": "stabilize",
                "strength": 0.8
            })

        if style:
            payload["operations"].append({
                "type": "style_transfer",
                "style": style
            })

        response = await self.client.post(
            f"{self.base_url}/enhance",
            json=payload
        )

        response.raise_for_status()
        data = response.json()

        return RunwayJob(
            job_id=data.get("id"),
            status="processing",
            job_type=RunwayAssetType.UPSCALE,
            metadata={"input": video_url, "operations": payload["operations"]}
        )

    async def compose_final(self,
                           video_segments: List[str],
                           voiceover: str,
                           transitions: str = "crossfade",
                           output_settings: Dict[str, Any] = None) -> RunwayJob:
        """
        Compose final video from segments

        Args:
            video_segments: List of video URLs
            voiceover: Audio URL
            transitions: Transition style between segments
            output_settings: Export configuration

        Returns:
            RunwayJob object for tracking
        """
        payload = {
            "segments": video_segments,
            "audio": voiceover,
            "transitions": transitions,
            "output": output_settings or {
                "resolution": "1920x1080",
                "fps": 30,
                "codec": "h264",
                "quality": "high"
            }
        }

        response = await self.client.post(
            f"{self.base_url}/compose",
            json=payload
        )

        response.raise_for_status()
        data = response.json()

        return RunwayJob(
            job_id=data.get("id"),
            status="processing",
            job_type=RunwayAssetType.COMPOSE,
            metadata={"segments": len(video_segments)}
        )

    async def wait_for_completion(self,
                                 job: RunwayJob,
                                 timeout: int = 300,
                                 poll_interval: float = 2.0) -> RunwayJob:
        """
        Poll for job completion with exponential backoff

        Args:
            job: RunwayJob to monitor
            timeout: Maximum wait time in seconds
            poll_interval: Initial poll interval

        Returns:
            Completed RunwayJob with result URL
        """
        start = asyncio.get_event_loop().time()
        current_interval = poll_interval

        while asyncio.get_event_loop().time() - start < timeout:
            response = await self.client.get(f"{self.base_url}/jobs/{job.job_id}")

            if response.status_code == 404:
                # Job not found, might be cached
                if job.metadata and job.metadata.get("cache_key"):
                    cached = await self._check_cache(job.metadata["cache_key"])
                    if cached:
                        return cached
                raise Exception(f"Job {job.job_id} not found")

            response.raise_for_status()
            data = response.json()

            job.status = data.get("status", "unknown")

            if job.status == "completed":
                job.result_url = data.get("output_url")
                # Cache successful result
                if job.result_url and job.metadata and job.metadata.get("cache_key"):
                    await self._cache_result(job)
                return job
            elif job.status == "failed":
                job.error = data.get("error", "Unknown error")
                raise Exception(f"Job failed: {job.error}")

            await asyncio.sleep(current_interval)
            current_interval = min(current_interval * 1.5, 30)  # Exponential backoff

        raise TimeoutError(f"Job {job.job_id} timed out after {timeout}s")

    def _generate_cache_key(self, *args) -> str:
        """Generate cache key from parameters"""
        cache_string = json.dumps(args, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()

    async def _check_cache(self, cache_key: str) -> Optional[RunwayJob]:
        """Check if result exists in cache"""
        if not self.cache_bucket:
            return None

        blob_name = f"cache/{cache_key}.json"
        blob = self.cache_bucket.blob(blob_name)

        if blob.exists():
            data = json.loads(blob.download_as_text())
            return RunwayJob(
                job_id=data["job_id"],
                status="completed",
                job_type=RunwayAssetType[data["job_type"]],
                result_url=data["result_url"],
                metadata=data.get("metadata")
            )

        return None

    async def _cache_result(self, job: RunwayJob):
        """Cache successful result in GCS"""
        if not self.cache_bucket or not job.result_url:
            return

        cache_key = job.metadata.get("cache_key")
        if not cache_key:
            return

        # Save job data
        blob_name = f"cache/{cache_key}.json"
        blob = self.cache_bucket.blob(blob_name)

        cache_data = {
            "job_id": job.job_id,
            "job_type": job.job_type.name,
            "result_url": job.result_url,
            "metadata": job.metadata
        }

        blob.upload_from_string(
            json.dumps(cache_data),
            content_type="application/json"
        )

        # Also download and cache the actual video
        try:
            video_blob_name = f"videos/{cache_key}.mp4"
            video_blob = self.cache_bucket.blob(video_blob_name)

            async with self.client.stream("GET", job.result_url) as response:
                video_blob.upload_from_string(
                    await response.aread(),
                    content_type="video/mp4"
                )

            # Update job with cached URL
            job.result_url = f"gs://yta-runway-cache/{video_blob_name}"
        except Exception as e:
            print(f"Warning: Failed to cache video file: {e}")

    async def close(self):
        """Clean up client connections"""
        await self.client.aclose()


# Convenience functions for synchronous usage
def create_runway_client() -> RunwayMLClient:
    """Factory function to create RunwayML client"""
    return RunwayMLClient()


async def generate_ai_video(prompt: str, duration: float = 5.0) -> str:
    """
    Simple wrapper for video generation

    Args:
        prompt: Video description
        duration: Duration in seconds

    Returns:
        Video URL
    """
    client = create_runway_client()
    try:
        job = await client.generate_video(prompt, duration)
        completed = await client.wait_for_completion(job)
        return completed.result_url
    finally:
        await client.close()