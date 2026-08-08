# ===== START OF FILE apps/content_studio/providers/__init__.py =====
# Provider registry.
#
# get_provider(name) lazily imports and constructs the requested provider, so
# importing this package never drags in requests/PIL or fails because an
# optional dependency is missing — you only pay for the provider you ask for.
#
# 'fal' and 'replicate' are the two primary aggregators; 'runway' is an optional
# image-to-video extra; 'mock' runs fully offline (tests/demos).

from apps.content_studio.providers.base import MediaProvider, ProviderError

PROVIDER_NAMES = ("mock", "fal", "replicate", "runway")


### Registry
def get_provider(name, **kwargs):
    """Construct a provider by name.

    :param name: one of PROVIDER_NAMES.
    :param kwargs: forwarded to the provider constructor (output_dir, model
                   overrides, api_key, ...).
    :return: a MediaProvider instance.
    :raises ValueError: for an unknown provider name.
    """
    key = (name or "").strip().lower()
    if key == "mock":
        from apps.content_studio.providers.mock import MockProvider
        return MockProvider(**kwargs)
    if key == "fal":
        from apps.content_studio.providers.fal import FalProvider
        return FalProvider(**kwargs)
    if key == "replicate":
        from apps.content_studio.providers.replicate import ReplicateProvider
        return ReplicateProvider(**kwargs)
    if key == "runway":
        from apps.content_studio.providers.runway import RunwayProvider
        return RunwayProvider(**kwargs)
    raise ValueError(f"Unknown provider {name!r}. Choose one of {PROVIDER_NAMES}.")

__all__ = ["MediaProvider", "ProviderError", "get_provider", "PROVIDER_NAMES"]

# ===== END OF FILE apps/content_studio/providers/__init__.py =====
