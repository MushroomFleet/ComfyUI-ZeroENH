# ComfyUI-ZeroENH

**Deterministic Prompt Enhancement via Procedural Augmentation**

# Part of the DJZ-Zerobytes 0(1) procedural collection
https://github.com/MushroomFleet/ComfyUI-DJZ-ZeroPrompt
https://github.com/MushroomFleet/ComfyUI-ZeroENH
https://github.com/MushroomFleet/ComfyUI-ZeroEDIT-nodes

ZeroENH enhances input prompts with contextually appropriate additions using O(1) coordinate hashing. The same `(input_prompt, seed, intensity)` combination always produces identical enhanced output - everywhere, every time.

## Features

- **Perfect Reproducibility**: Same inputs = same outputs, guaranteed
- **Sub-100ms Latency**: No LLM inference required
- **Zero Cost**: Pure local computation
- **Full Auditability**: Every enhancement selection traceable to hash coordinates
- **Intensity Control**: Choose enhancement level (minimal/light/moderate/full)
- **Anti-Pairing Logic**: Prevents semantically incoherent combinations
- **LoRA/Embedding Preservation**: Unclassified tokens pass through unchanged

## Installation

### Via ComfyUI Manager (Recommended)

Search for "ZeroENH" in ComfyUI Manager and click Install.

### Manual Installation

1. Navigate to your ComfyUI custom nodes directory:
   ```bash
   cd ComfyUI/custom_nodes
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/MushroomFleet/ComfyUI-ZeroENH.git
   ```

3. Install dependencies:
   ```bash
   cd ComfyUI-ZeroENH
   pip install -r requirements.txt
   ```

4. Restart ComfyUI

## Nodes

All nodes are found under the `DJZ-Nodes` category.

### DJZ Zero ENH V1

Hardcoded default vocabulary - no external files required.

**Inputs:**

| Input | Type | Description |
|-------|------|-------------|
| `prompt` | STRING | Input prompt to enhance |
| `seed` | INT | Seed for deterministic enhancement (0 to 4294967295) |
| `intensity` | COMBO | Enhancement level: minimal (25%), light (50%), moderate (75%), full (100%) |
| `max_words` | INT | Maximum word count for output (default: 150) |
| `prefix` | STRING | Text to prepend to enhanced prompt |
| `suffix` | STRING | Text to append to enhanced prompt |

**Output:**

| Output | Type | Description |
|--------|------|-------------|
| `enhanced_prompt` | STRING | The deterministically enhanced prompt |

---

### DJZ Zero ENH V2

Custom JSON profile support with theme-specific vocabularies.

**Inputs:**

| Input | Type | Description |
|-------|------|-------------|
| `prompt` | STRING | Input prompt to enhance |
| `profile` | COMBO | Select enhancement profile (auto-discovered from `/profiles` folder) |
| `seed` | INT | Seed for deterministic enhancement (0 to 4294967295) |
| `intensity` | COMBO | Enhancement level: minimal (25%), light (50%), moderate (75%), full (100%) |
| `max_words` | INT | Maximum word count for output (default: 150) |
| `prefix` | STRING | Text to prepend to enhanced prompt |
| `suffix` | STRING | Text to append to enhanced prompt |

**Output:**

| Output | Type | Description |
|--------|------|-------------|
| `enhanced_prompt` | STRING | The deterministically enhanced prompt |

---

### DJZ Zero ENH Profile Info

Utility node to display profile statistics.

**Inputs:**

| Input | Type | Description |
|-------|------|-------------|
| `profile` | COMBO | Select profile to inspect |

**Output:**

| Output | Type | Description |
|--------|------|-------------|
| `info` | STRING | Formatted profile statistics (pool sizes, combinations, rules) |

---

## Included Profiles

The following profiles are included in the `nodes/profiles/` directory:

| Profile | Description |
|---------|-------------|
| `default.json` | Universal vocabulary for general image generation (V1-compatible) |
| `cyberpunk.json` | Neon-noir dystopian vocabulary (Blade Runner, Ghost in the Shell, Akira aesthetics) |

### Creating Custom Profiles

Add `.json` files to the `nodes/profiles/` directory. They will be auto-discovered on ComfyUI restart.

Profile structure:
```json
{
  "name": "Profile Name",
  "description": "What this profile does",
  "version": "1.0.0",
  "type": "enhancement",
  "templates": ["..."],
  "pools": {
    "subject": ["..."],
    "action": ["..."],
    "environment": ["..."],
    "style": ["..."],
    "lighting": ["..."],
    "camera": ["..."],
    "details": ["..."],
    "mood": ["..."]
  },
  "classification": {...},
  "rules": {...},
  "anti_pairs": {...}
}
```

## How It Works

ZeroENH uses the **ZeroBytes position-is-seed methodology**:

1. **Tokenization**: Split input prompt into semantic tokens
2. **Classification**: Identify which categories are present (subject, environment, style, lighting, camera, details, mood, action)
3. **Gap Finding**: Detect missing categories
4. **Hash Selection**: Use `xxhash32(seed + input_hash + coordinate)` to select enhancements from vocabulary pools
5. **Anti-Pairing**: Avoid semantically incompatible combinations
6. **Template Assembly**: Merge original tokens with enhancements
7. **Deduplication**: Remove redundant elements
8. **Length Enforcement**: Truncate if exceeding word limit

### Determinism Guarantee

```
hash(seed, input_hash, coordinate) % pool_size → selection index
```

This is a pure mathematical function with no state or randomness. The same coordinates always produce the same selection.

## Enhancement Categories

| Category | Description | Example Keywords |
|----------|-------------|------------------|
| Subject | Main entity/character | woman, dragon, robot |
| Action | Movement/activity | standing, running, flying |
| Environment | Setting/location | forest, city, space station |
| Style | Visual aesthetic | photorealistic, anime, oil painting |
| Lighting | Light conditions | golden hour, neon, moonlight |
| Camera | Shot/angle/lens | close-up, wide shot, bokeh |
| Details | Quality modifiers | highly detailed, 8k, masterpiece |
| Mood | Emotional atmosphere | serene, ominous, epic |

## Intensity Levels

| Level | Gap Fill Rate | Description |
|-------|---------------|-------------|
| `minimal` | 25% | Add only critical missing elements |
| `light` | 50% | Subtle enhancement |
| `moderate` | 75% | Balanced enhancement (default) |
| `full` | 100% | Fill all detected gaps |

## Anti-Pairing Examples

ZeroENH prevents semantically incoherent combinations:

- `underwater` will not get `golden hour` or `sunset` lighting
- `cave` will not get `blue hour` or `sunset backlight`
- `pixel art` will not get `ray tracing` or `photogrammetry`
- `graveyard` will not get `joyful` or `playful` mood

## Usage Examples

### Minimal Input
```
Input:  "a cat"
Seed:   42
Intensity: moderate

Output: "photorealistic a cat resting in a cozy room, soft window light,
        close-up portrait, highly detailed, peaceful atmosphere"
```

### Partial Input (preserves existing elements)
```
Input:  "cyberpunk samurai, neon lighting, cinematic"
Seed:   12345
Intensity: moderate

Output: "cyberpunk samurai standing in a neon-lit alley, cinematic,
        neon lighting, low angle shot, 8k, intense atmosphere"
```

### With LoRA Triggers (preserved unchanged)
```
Input:  "a woman ohwx_person XYZ"
Seed:   42
Intensity: moderate

Output: "a woman in a dark forest, photorealistic, golden hour lighting,
        medium shot, highly detailed, mysterious atmosphere, ohwx_person, XYZ"
```

## Comparison with LLM Enhancement

| Aspect | LLM Enhancement | ZeroENH |
|--------|-----------------|---------|
| Latency | 30-60 seconds | <100ms |
| Determinism | Non-deterministic | Perfect reproducibility |
| Cost | API call per prompt | Zero (local compute) |
| Auditability | Black box | Full visibility |
| Customization | Prompt engineering | JSON vocabulary (V2) |
| Offline | Requires API | Fully offline |

## Roadmap

- **V1** (Complete): Hardcoded default vocabulary - proves determinism works
- **V2** (Complete): Custom JSON profiles with theme-specific vocabularies
- **Future**: Additional themed profiles (fantasy.json, portrait.json, anime.json, etc.)

## Related Projects

This node is part of the DJZ-Nodes ecosystem and shares the position-is-seed methodology with:
- [DJZ-ZeroPrompt](https://github.com/MushroomFleet/DJZ-ZeroPrompt) - Full prompt generation from nothing
- [Added-Typos](https://github.com/MushroomFleet/Added-Typos) - Deterministic text corruption

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Developed by [MushroomFleet](https://github.com/MushroomFleet)

Based on the ZeroBytes Position-is-Seed methodology for deterministic procedural generation.

## Citation

### Academic Citation

If you use this codebase in your research or project, please cite:

```bibtex
@software{comfyui_zeroenh,
  title = {ComfyUI-ZeroENH: Deterministic Prompt Enhancement via Procedural Augmentation},
  author = {Drift Johnson},
  year = {2025},
  url = {https://github.com/MushroomFleet/ComfyUI-ZeroENH},
  version = {1.0.0}
}
```

### Donate:

[![Ko-Fi](https://cdn.ko-fi.com/cdn/kofi3.png?v=3)](https://ko-fi.com/driftjohnson)
