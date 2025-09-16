"""
RunwayML Visual Director
Implements Director's visual protocol with AI-powered scene generation
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
from .runway_client import RunwayMLClient, RunwayJob


@dataclass
class VisualLayer:
    """Represents a visual layer in the composition"""
    layer_type: str  # base_video, logo, text, screenshot, pip
    content: Any
    timing: Dict[str, float]
    effects: List[str]
    metadata: Dict[str, Any]


class RunwayVisualDirector:
    """
    Orchestrates visual elements per Director's requirements:
    - No static visuals
    - Motion is mandatory
    - Futuristic aesthetic
    - Seamless integration
    """

    def __init__(self):
        """Initialize visual director with RunwayML client"""
        self.client = RunwayMLClient()
        self.logo_registry = self._load_logo_registry()
        self.style_guide = self._load_style_guide()

    async def direct_segment(self, segment: Dict, timing: Dict) -> Dict:
        """
        Apply complete visual direction to a segment

        Args:
            segment: Shot list segment with voiceover, keywords, etc.
            timing: Duration and offset information

        Returns:
            Visual plan with all layers and effects
        """
        visual_plan = {
            "segment_id": segment.get("id", "unknown"),
            "duration": timing.get("duration", 5.0),
            "layers": [],
            "transitions": []
        }

        # Layer 1: Base B-roll (Generated or Enhanced)
        base_layer = await self._create_base_layer(segment, timing)
        visual_plan["layers"].append(base_layer)

        # Layer 2: Logo Overlays (First Mentions)
        entities = self._extract_entities(segment)
        if entities:
            logo_layer = await self._create_logo_layer(entities, timing)
            visual_plan["layers"].append(logo_layer)

        # Layer 3: Text Overlays (Keywords, Data Points)
        text_elements = self._extract_text_elements(segment)
        if text_elements:
            text_layer = await self._create_text_layer(text_elements, timing)
            visual_plan["layers"].append(text_layer)

        # Layer 4: Screenshot Enhancement
        if segment.get("source_url"):
            screenshot_layer = await self._enhance_screenshot(
                segment["source_url"],
                segment.get("highlight_text"),
                timing
            )
            visual_plan["layers"].append(screenshot_layer)

        # Layer 5: Picture-in-Picture if needed
        if self._needs_pip(segment):
            pip_layer = await self._create_pip_layout(segment, timing)
            visual_plan["layers"].append(pip_layer)

        # Add transitions between segments
        visual_plan["transitions"] = self._plan_transitions(segment)

        return visual_plan

    async def _create_base_layer(self, segment: Dict, timing: Dict) -> VisualLayer:
        """
        Generate or enhance base video layer

        Decision tree:
        1. If no assets available -> Generate with AI
        2. If low quality assets -> Enhance with AI
        3. If good assets -> Use directly with effects
        """
        # Check if we should generate B-roll
        should_generate = (
            segment.get("generate_broll", True) or
            not segment.get("assets") or
            len(segment.get("assets", [])) == 0
        )

        if should_generate:
            # Generate B-roll with AI
            prompt = self._build_visual_prompt(segment)

            job = await self.client.generate_video(
                prompt=prompt,
                duration=timing["duration"],
                style="futuristic tech documentary",
                seed=42  # Consistency across regenerations
            )

            completed_job = await self.client.wait_for_completion(job)

            return VisualLayer(
                layer_type="base_video",
                content=completed_job.result_url,
                timing={"start": 0, "duration": timing["duration"]},
                effects=["color_grade_tech", "slight_vignette", "motion_blur"],
                metadata={
                    "source": "ai_generated",
                    "prompt": prompt,
                    "job_id": completed_job.job_id
                }
            )
        else:
            # Use existing asset with enhancement
            asset = segment["assets"][0]

            # Enhance if needed
            if asset.get("quality", "medium") == "low":
                enhance_job = await self.client.enhance_video(
                    video_url=asset["url"],
                    upscale=True,
                    stabilize=True,
                    style="cinematic_tech"
                )
                enhanced = await self.client.wait_for_completion(enhance_job)
                video_url = enhanced.result_url
            else:
                video_url = asset["url"]

            return VisualLayer(
                layer_type="base_video",
                content=video_url,
                timing={"start": 0, "duration": timing["duration"]},
                effects=["color_correction", "sharpening"],
                metadata={"source": "stock_enhanced", "original": asset["url"]}
            )

    def _build_visual_prompt(self, segment: Dict) -> str:
        """
        Build optimized prompt for video generation based on segment content

        Incorporates:
        - Keywords from segment
        - Segment type (news, research, funding, policy)
        - Director's visual requirements
        - Consistent style guidelines
        """
        keywords = segment.get("keywords", ["AI", "technology"])
        segment_type = segment.get("segment_type", "news")
        voiceover = segment.get("voiceover", "")

        # Base prompts by segment type
        base_prompts = {
            "news": f"Futuristic newsroom with holographic displays showing {', '.join(keywords[:2])}, floating data visualizations, glass interfaces",
            "research": f"High-tech laboratory with quantum computers, {keywords[0]} visualization on screens, scientists working, blue lighting",
            "funding": f"Modern corporate boardroom with financial data projections, growth charts about {keywords[0]}, city skyline view",
            "policy": f"Government building interior with digital policy documents, {keywords[0]} regulations on screens, formal atmosphere"
        }

        base = base_prompts.get(segment_type, base_prompts["news"])

        # Add Director's requirements
        director_modifiers = [
            "cinematic lighting",
            "dynamic camera movement",
            "depth of field",
            "slight motion blur on transitions",
            "futuristic aesthetic",
            "4K quality",
            "professional color grading"
        ]

        # Combine into final prompt
        full_prompt = f"{base}, {', '.join(director_modifiers)}"

        # Add specific visual cues from voiceover
        if "breakthrough" in voiceover.lower():
            full_prompt += ", dramatic lighting change, energy surge effect"
        if "risk" in voiceover.lower() or "threat" in voiceover.lower():
            full_prompt += ", red warning lights, alert displays"
        if "success" in voiceover.lower() or "achievement" in voiceover.lower():
            full_prompt += ", celebration visuals, positive energy"

        return full_prompt

    def _extract_entities(self, segment: Dict) -> List[Dict]:
        """
        Extract company/organization entities for logo placement

        Returns list of entities with timing information
        """
        entities = []
        voiceover = segment.get("voiceover", "").lower()

        # Company patterns
        companies = {
            "openai": ["openai", "gpt", "chatgpt"],
            "google": ["google", "deepmind", "gemini", "alphabet"],
            "anthropic": ["anthropic", "claude"],
            "meta": ["meta", "facebook", "llama"],
            "microsoft": ["microsoft", "azure", "copilot"]
        }

        for company, patterns in companies.items():
            for pattern in patterns:
                if pattern in voiceover:
                    # Find first mention position
                    position = voiceover.index(pattern)
                    word_position = len(voiceover[:position].split())

                    entities.append({
                        "name": company,
                        "mention_position": position,
                        "word_position": word_position,
                        "pattern_matched": pattern
                    })
                    break  # Only first mention

        # Sort by appearance order
        entities.sort(key=lambda x: x["mention_position"])

        return entities

    def _extract_text_elements(self, segment: Dict) -> List[Dict]:
        """
        Extract text overlay requirements:
        - Technical jargon
        - Data points/statistics
        - Key phrases
        """
        text_elements = []
        voiceover = segment.get("voiceover", "")

        # Technical terms that need explanation
        jargon_patterns = {
            r"\b(transformer|llm|gpt|neural network|quantum)\b": "technical",
            r"\b\d+[xX]?\s*(faster|better|improvement|increase)\b": "data_point",
            r"\b\d+%\b": "percentage",
            r"\b\$?\d+[BMK]?\b": "number"
        }

        for pattern, element_type in jargon_patterns.items():
            matches = re.finditer(pattern, voiceover, re.IGNORECASE)
            for match in matches:
                text_elements.append({
                    "text": match.group(),
                    "type": element_type,
                    "position": match.start(),
                    "style": self._get_text_style(element_type)
                })

        return text_elements

    def _get_text_style(self, element_type: str) -> str:
        """Map element type to visual style"""
        styles = {
            "technical": "keyword",      # Futuristic font with glow
            "data_point": "data_highlight",  # Large, pulsing green
            "percentage": "statistic",   # Bold with animation
            "number": "metric"           # Clean, professional
        }
        return styles.get(element_type, "default")

    async def _create_logo_layer(self, entities: List[Dict], timing: Dict) -> VisualLayer:
        """Create logo overlay layer per Director's specs"""
        logo_configs = []

        for i, entity in enumerate(entities[:2]):  # Max 2 logos per segment
            # Calculate appearance timing based on word position
            words_per_second = 2.5  # Average speaking rate
            appearance_time = entity["word_position"] / words_per_second

            logo_configs.append({
                "company": entity["name"],
                "position": "top_right" if i == 0 else "top_left",
                "timing": {
                    "start": appearance_time,
                    "duration": 3.5  # Director spec: 3-4 seconds
                },
                "animation": {
                    "in": "scale_fade",
                    "out": "fade",
                    "scale_from": 0.8,
                    "scale_to": 1.0
                }
            })

        return VisualLayer(
            layer_type="logos",
            content=logo_configs,
            timing={"start": 0, "duration": timing["duration"]},
            effects=["drop_shadow", "subtle_glow"],
            metadata={"entities": entities}
        )

    async def _create_text_layer(self, text_elements: List[Dict], timing: Dict) -> VisualLayer:
        """Create text overlay layer with animations"""
        text_configs = []

        for element in text_elements:
            # Calculate timing based on position in voiceover
            words_before = element["position"] / 5  # Rough character to word conversion
            appearance_time = words_before / 2.5  # Words per second

            config = {
                "text": element["text"],
                "style": element["style"],
                "timing": {
                    "start": appearance_time,
                    "duration": 2.5  # Standard display time
                },
                "animation": self._get_text_animation(element["type"]),
                "position": self._get_text_position(element["type"])
            }

            text_configs.append(config)

        return VisualLayer(
            layer_type="text_overlays",
            content=text_configs,
            timing={"start": 0, "duration": timing["duration"]},
            effects=["motion_tracking", "depth_parallax"],
            metadata={"element_count": len(text_elements)}
        )

    def _get_text_animation(self, text_type: str) -> Dict:
        """Get animation config for text type"""
        animations = {
            "technical": {
                "in": "typewriter",
                "out": "fade",
                "speed": "fast"
            },
            "data_point": {
                "in": "scale_pulse",
                "out": "shrink",
                "pulse_count": 3
            },
            "percentage": {
                "in": "count_up",
                "out": "fade",
                "duration": 1.0
            }
        }
        return animations.get(text_type, {"in": "fade", "out": "fade"})

    def _get_text_position(self, text_type: str) -> str:
        """Get position for text type"""
        positions = {
            "technical": "center",
            "data_point": "center_large",
            "percentage": "bottom_third",
            "number": "top_center"
        }
        return positions.get(text_type, "bottom")

    async def _enhance_screenshot(self,
                                  screenshot_url: str,
                                  highlight_text: Optional[str],
                                  timing: Dict) -> VisualLayer:
        """Apply Ken Burns and highlighting to screenshots"""
        enhancements = {
            "ken_burns": {
                "start": {"scale": 1.0, "x": 0, "y": 0},
                "end": {"scale": 1.3, "x": 0.1, "y": -0.05},
                "easing": "ease_in_out"
            }
        }

        if highlight_text:
            enhancements["highlight"] = {
                "text": highlight_text,
                "style": "trace_animation",
                "color": "#FFFF00",
                "timing": {"delay": 1.0, "duration": 2.0}
            }

        # Add holographic frame per Director's spec
        enhancements["frame"] = {
            "style": "holographic_monitor",
            "effects": ["scan_lines", "glow", "reflection"]
        }

        return VisualLayer(
            layer_type="screenshot",
            content=screenshot_url,
            timing={"start": 0, "duration": timing["duration"]},
            effects=["ken_burns", "enhance_clarity"],
            metadata={"enhancements": enhancements}
        )

    def _needs_pip(self, segment: Dict) -> bool:
        """Determine if segment needs PiP layout"""
        # PiP for comparisons or when showing speaker
        keywords = ["versus", "compared", "meanwhile", "however", "alternatively"]
        voiceover = segment.get("voiceover", "").lower()

        return any(keyword in voiceover for keyword in keywords)

    async def _create_pip_layout(self, segment: Dict, timing: Dict) -> VisualLayer:
        """Create Picture-in-Picture layout"""
        pip_config = {
            "layout": "corner",  # or "split", "floating"
            "main_content": "primary_video",
            "pip_content": "comparison_video",
            "pip_scale": 0.25,
            "pip_position": "top_right",
            "border": {
                "width": 3,
                "color": "#00FFFF",
                "glow": True
            },
            "animation": {
                "in": "slide_fade",
                "out": "fade"
            }
        }

        return VisualLayer(
            layer_type="pip",
            content=pip_config,
            timing={"start": 0, "duration": min(timing["duration"], 8)},  # Max 8 seconds
            effects=["smooth_transition", "border_glow"],
            metadata={"layout_type": "picture_in_picture"}
        )

    def _plan_transitions(self, segment: Dict) -> List[Dict]:
        """Plan transitions between visual elements"""
        return [
            {
                "type": "crossfade",
                "duration": 0.5,
                "easing": "ease_in_out"
            }
        ]

    def _load_logo_registry(self) -> Dict:
        """Load company logo registry"""
        return {
            "openai": {"url": "gs://yta-main-assets/logos/openai.png", "color": "#000000"},
            "google": {"url": "gs://yta-main-assets/logos/google.png", "color": "#4285F4"},
            "anthropic": {"url": "gs://yta-main-assets/logos/anthropic.png", "color": "#7C3AED"},
            "meta": {"url": "gs://yta-main-assets/logos/meta.png", "color": "#0866FF"},
            "microsoft": {"url": "gs://yta-main-assets/logos/microsoft.png", "color": "#00BCF2"}
        }

    def _load_style_guide(self) -> Dict:
        """Load visual style guide"""
        return {
            "colors": {
                "primary": "#00FFFF",
                "secondary": "#FF00FF",
                "success": "#00FF00",
                "warning": "#FFFF00",
                "danger": "#FF0000"
            },
            "fonts": {
                "primary": "Orbitron",
                "secondary": "Inter",
                "monospace": "Roboto Mono"
            },
            "effects": {
                "glow_intensity": 0.5,
                "motion_blur": 0.3,
                "vignette": 0.2
            }
        }

    async def close(self):
        """Clean up resources"""
        await self.client.close()