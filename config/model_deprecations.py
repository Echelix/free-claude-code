"""Mapping of deprecated NVIDIA NIM model refs to their recommended replacements."""

# Keys are full model refs (provider/org/name); values are the drop-in replacement.
# Add an entry here whenever a NIM model is retired so the proxy self-heals .env files.
DEPRECATED_NVIDIA_NIM_MODELS: dict[str, str] = {
    "nvidia_nim/moonshotai/kimi-k2-thinking": "nvidia_nim/qwen/qwen3-next-80b-a3b-thinking",
    "nvidia_nim/moonshotai/kimi-k2-instruct": "nvidia_nim/qwen/qwen3.5-122b-a10b",
    "nvidia_nim/moonshotai/kimi-k2.6": "nvidia_nim/qwen/qwen3-next-80b-a3b-thinking",
}
