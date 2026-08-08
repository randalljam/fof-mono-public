# ===== START OF FILE apps/content_studio/__init__.py =====
# Content studio: generate short animations, video clips, and audio (speech /
# music / sfx) from verbal descriptions — then verify every output so broken
# results (extra/duplicated limbs, melted faces, identity drift, garbled speech)
# get caught and regenerated instead of shipped.
#
# Primary generation backends: fal.ai and Replicate (aggregators covering
# Seedance video, MiniMax speech, and many more), plus an offline mock.
#
# Importing this package is dependency-light: Pillow/anthropic/requests are only
# loaded by the code paths that actually need them (the codec, the visual
# verifier's default asker, and the HTTP providers respectively).

from apps.content_studio.models import (
    MediaRequest, AnimationRequest, VideoRequest, AudioRequest, MediaResult,
    FrameIssue, VerifyResult, PipelineResult, VISUAL_KINDS, AUDIO_KINDS,
)
from apps.content_studio.verify import (
    VisualVerifier, apply_policy, anthropic_vision_asker,
)
from apps.content_studio.verify_audio import (
    AudioVerifier, audio_policy, text_similarity,
)
from apps.content_studio.pipeline import generate_and_verify, default_verifier_for
from apps.content_studio.providers import get_provider, PROVIDER_NAMES

__all__ = [
    "MediaRequest", "AnimationRequest", "VideoRequest", "AudioRequest",
    "MediaResult", "FrameIssue", "VerifyResult", "PipelineResult",
    "VISUAL_KINDS", "AUDIO_KINDS",
    "VisualVerifier", "apply_policy", "anthropic_vision_asker",
    "AudioVerifier", "audio_policy", "text_similarity",
    "generate_and_verify", "default_verifier_for",
    "get_provider", "PROVIDER_NAMES",
]

# ===== END OF FILE apps/content_studio/__init__.py =====
