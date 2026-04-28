# RFC-009 — Mask provider protocol shape

> Status · Draft v0.1
> TA anchor ·/components/ai-providers ·/contracts/mcp-tools
> Related · ADR-007, ADR-021, ADR-022, RFC-004
> Closes into · ADR (pending) — locks the Protocol shape
> Why this is an RFC · ADR-007 commits to BYOA via pluggable providers. RFC-004 chooses the v1 default. But the actual `MaskingProvider` Protocol shape — the parameters, return types, error contracts — is open. This shape will be the hardest thing to change later: every provider implementation is bound to it. Getting it close-to-right now matters; the alternative is a v2 break that disrupts every external provider.

## The question

What's the right shape for the `MaskingProvider` Protocol such that:
- The bundled coarse-agent provider implements it cleanly
- The sibling SAM-based provider (`chemigram-masker-sam`) implements it cleanly
- A future hosted/cloud provider can implement it without contortions
- A future specialist provider (e.g., `chemigram-masker-fish`, trained on marine life) fits naturally
- Caching, retry, and error reporting are clean

## Use cases

- Agent calls `generate_mask(image_id, "subject")` → engine routes to configured provider → receives a PNG.
- Agent calls `generate_mask(image_id, "fish", prompt="adult tuna in left third of frame")` → provider with prompt support uses it; provider without ignores it gracefully.
- Provider takes 3 seconds; engine returns a placeholder while masking runs in background. (Async or not?)
- Same target masked twice (session interrupted, resumed); cache returns the prior result.
- Provider fails (model error, API outage). Engine surfaces the error to the agent without crashing the session.

## Goals

- Protocol fits multiple provider styles (local model, hosted service, agent-vision-coarse, specialist)
- Caching works without provider-side complexity
- Error handling is consistent across providers
- Async-friendly (without forcing async on simple synchronous providers)

## Constraints

- TA/components/ai-providers — pluggable via Protocol
- TA/constraints/byoa — engine doesn't bundle ML
- ADR-022 — masks integrate with the mask registry

## Proposed approach

**Synchronous Protocol with optional async support.** Providers that want async can implement the async method too; engine prefers async if available, falls back to sync.

```python
@dataclass
class MaskRequest:
    image_id: str
    render_path: Path           # current preview to mask against
    target: str                 # "subject", "sky", "highlights", etc.
    prompt: str | None
    name: str | None            # optional symbolic name (default: "current_<target>_mask")
    request_id: str             # for caching/dedup


@dataclass
class MaskResult:
    success: bool
    mask_path: Path | None      # PNG file
    diagnostics: dict           # provider name, generation params, cache hit/miss
    quality_estimate: Literal["approximate", "production"] | None
    error_message: str | None   # if success=False


class MaskingProvider(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def supports_prompts(self) -> bool: ...
    @property
    def quality_tier(self) -> Literal["approximate", "production"]: ...

    def generate(self, request: MaskRequest) -> MaskResult: ...

    # Optional async variant. Engine calls this if available.
    async def generate_async(self, request: MaskRequest) -> MaskResult:
        return self.generate(request)
```

**Caching:** the engine wraps providers. Cache key = `(image_id, target, prompt, render_hash)`. Cache lives in the mask registry. Provider doesn't see cache; engine asks once, stores result, returns from cache on subsequent same requests.

**Provider configuration:** `~/.chemigram/config.toml`:

```toml
[masking]
provider = "sam"   # or "coarse_agent" or "custom"

[masking.sam]
mcp_server = "chemigram-masker-sam"
model = "sam2_hiera_b"

[masking.coarse_agent]
# uses the photo agent's vision; no extra config
```

**Provider registration via MCP:** when a provider is an MCP server (e.g., `chemigram-masker-sam`), it registers itself via MCP service discovery. The engine discovers it from `config.toml`.

**Error reporting:** failures return `MaskResult(success=False, error_message="...")` rather than raising. The agent sees the error in tool result; can choose to fall back to a different provider, retry, or abort the operation.

## Alternatives considered

- **Full async-only Protocol:** rejected — forces async on simple synchronous providers (e.g., the coarse_agent). Mixing sync calls across the engine adds complexity without clear benefit at v1's scale.

- **Streaming results (provider yields multiple masks):** rejected — masks are single results per call. If a provider can produce multiple candidate masks, the engine model is "choose the best one before returning"; if multiple-mask comparison becomes a real use case, revisit later.

- **Promote `prompt` to required parameter:** rejected — forces providers without prompt support to implement a no-op. Optional with `supports_prompts` introspection is cleaner.

- **Embed caching in the provider Protocol (each provider implements its cache):** rejected — gives providers more responsibility than they should have. Engine-side cache is one place; cache invalidation is one logic path.

- **Use a different approach entirely (provider chain, pipeline of maskers):** considered for future. v1 has one configured provider per request; chains can be added later if a clear use case emerges.

## Trade-offs

- The Protocol adds one method (`generate`) plus three properties (`name`, `supports_prompts`, `quality_tier`). Slight verbosity for simple providers, but the introspection is what makes the engine's caching and reporting correct.
- `MaskResult.diagnostics` is a free dict; provider-specific fields can land there. The agent reads it as opaque metadata. Mild typing weakness; acceptable for evolution speed.
- Async-optional means the engine has two code paths (call sync; call async). Mitigated: Python's `asyncio.iscoroutinefunction` checks make this cleanly conditional.

## Open questions

- **Is `quality_estimate` per-mask or per-provider?** Provider-level (declared) and per-mask (in `diagnostics`) both have value. Proposed: provider-level via `quality_tier`, per-mask via `diagnostics["confidence"]` if the provider supports it.
- **Versioning the Protocol.** When the Protocol shape evolves (e.g., future v2 adds streaming or chains), how do existing providers handle it? Proposed: providers declare `protocol_version`; engine warns or rejects mismatched providers.
- **MCP-server providers vs in-process providers.** Both need to work. Proposed: in-process for the bundled `coarse_agent`; MCP-server for any external provider. Both implement the same Python Protocol; the MCP wrapper layer translates.
- **Mask file format.** Specified as PNG (8-bit grayscale, single channel). Should we allow other formats (16-bit, alpha)? Proposed: PNG 8-bit grayscale is sufficient for v1. Document limitations.
- **Render hash for caching.** The cache key includes `render_hash` — but rendering is non-deterministic with `--apply-custom-presets false`? Proposed: hash of the synthesized XMP serves as the render hash (each XMP produces one render; same XMP → same render).

## How this closes

This RFC closes into:
- **An ADR locking the `MaskingProvider` Protocol shape** as proposed.
- **An ADR for the engine-side caching mechanism** (cache key, lifecycle, invalidation).
- **An ADR or amendment to ADR-022** specifying how the registry integrates with the Protocol.

## Links

- TA/components/ai-providers
- ADR-007, ADR-021, ADR-022
- RFC-004 (default masking provider)
