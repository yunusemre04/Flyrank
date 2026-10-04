from ..errors import ProviderError


def build_provider(settings):
    if settings.provider == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(settings)
    if settings.provider == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(settings)
    if settings.provider == "mock":
        from .mock import MockProvider
        return MockProvider(settings)
    raise ProviderError(f"unknown PROVIDER '{settings.provider}' (use gemini | ollama | mock)", retriable=False)
