"""
DJZ-ZeroENH-V1 - Deterministic Prompt Enhancement via Procedural Augmentation
ComfyUI Custom Node using ZeroBytes Position-is-Seed Methodology

Enhances input prompts with contextually appropriate additions using O(1) coordinate hashing.
Same (input_prompt, seed, intensity) → same enhanced output, always, everywhere.

V1 Features:
- Hardcoded default vocabulary (no external JSON required)
- Multi-category token classification
- Anti-pairing logic for semantic coherence
- Intensity control (minimal/light/moderate/full)
- Unclassified token preservation (LoRA triggers, embeddings)
- Maximum word limit enforcement
"""

import re
import struct

try:
    import xxhash
except ImportError:
    raise ImportError(
        "DJZ-ZeroENH requires xxhash. Install with: pip install xxhash"
    )


# =============================================================================
# V1 HARDCODED VOCABULARY (DEFAULT PROFILE)
# =============================================================================

DEFAULT_PROFILE = {
    "name": "Default",
    "description": "V1 vanilla enhancement - universal vocabulary for general image generation",
    "version": "1.0.0",
    
    "templates": [
        "{subject}, {environment}, {style}, {lighting}, {camera}, {details}, {mood} atmosphere",
        "{subject}, {environment}, {style}, {lighting}, {details}, {mood}",
        "{style}, {subject}, {environment}, {lighting}, {camera}, {details}",
        "{camera}, {subject}, {environment}, {style}, {lighting}, {details}",
        "{subject}, {environment}, {style}, {lighting}, {details}",
        "{mood} scene, {subject}, {environment}, {style}, {lighting}, {details}",
        "{subject}, {action}, {environment}, {style}, {lighting}, {details}",
        "{style}, {subject}, {environment}, {lighting}, {mood}, {details}"
    ],
    
    "pools": {
        "subject": [
            "a woman", "a man", "a young woman", "a young man", "an elderly woman",
            "an elderly man", "a child", "a teenager", "a couple", "a group of people",
            "a knight", "a wizard", "a witch", "a sorceress", "a necromancer",
            "a paladin", "a rogue", "an assassin", "a ranger", "a barbarian",
            "a druid", "a monk", "a bard", "a warlock", "an elven archer",
            "a dwarven smith", "an orc warrior", "a goblin", "a fairy", "a nymph",
            "a cyborg", "an android", "a robot", "a mech pilot", "an astronaut",
            "a space marine", "an alien", "a hacker", "a scientist", "a bounty hunter",
            "a samurai", "a ninja", "a viking", "a gladiator", "a pharaoh",
            "a geisha", "a shogun", "a roman soldier", "a medieval peasant", "a noble",
            "a detective", "a soldier", "a pilot", "a doctor", "an artist",
            "a musician", "a dancer", "an athlete", "a chef", "a photographer",
            "a dragon", "a phoenix", "a griffin", "a unicorn", "a werewolf",
            "a vampire", "a demon", "an angel", "a ghost", "a spirit",
            "a wolf", "a lion", "a tiger", "an eagle", "a raven",
            "a serpent", "a whale", "a shark", "a butterfly", "a spider",
            "a mechanical spider", "a clockwork automaton", "a golem", "a sentient statue",
            "a living shadow", "an elemental being", "a slime creature", "a treant"
        ],
        
        "action": [
            "standing in", "sitting in", "kneeling in", "floating above", "hovering over",
            "resting in", "meditating in", "posing in", "waiting in", "watching over",
            "walking through", "running through", "flying over", "swimming in", "climbing",
            "falling into", "descending into", "ascending toward", "emerging from", "diving into",
            "fighting in", "battling through", "defending", "attacking", "dueling in",
            "charging through", "retreating from", "ambushing in", "hunting in",
            "exploring", "discovering", "searching through", "investigating",
            "summoning power in", "casting a spell in", "channeling energy in",
            "communing with nature in", "praying in", "performing a ritual in",
            "transforming in", "shapeshifting in", "awakening in",
            "mourning in", "celebrating in", "contemplating in", "dreaming in"
        ],
        
        "environment": [
            "a dark forest", "an enchanted forest", "a misty forest", "a bamboo forest",
            "a snowy mountain", "a volcanic mountain", "a floating mountain",
            "a vast desert", "an oasis", "a canyon", "a waterfall", "a river",
            "a beach at sunset", "a stormy sea", "a coral reef", "an underwater cavern",
            "a medieval castle", "a ruined fortress", "a gothic cathedral",
            "an ancient temple", "a hidden shrine", "a sacred grove",
            "a wizard's tower", "an alchemist's laboratory", "a royal throne room",
            "a dungeon", "catacombs", "a crypt", "a graveyard at midnight",
            "a cyberpunk city", "a neon-lit alley", "a futuristic metropolis",
            "a space station", "an alien planet", "a terraformed moon",
            "a dystopian wasteland", "a post-apocalyptic city", "a megastructure",
            "a virtual reality world", "inside a computer mainframe",
            "a crystal cave", "a bioluminescent cavern", "a floating island",
            "the astral plane", "between dimensions", "the void",
            "a pocket dimension", "a mirror world", "a dream realm",
            "cherry blossom gardens", "an autumn forest", "a field of flowers",
            "under the northern lights", "during a solar eclipse"
        ],
        
        "style": [
            "photorealistic", "hyperrealistic", "cinematic", "film still",
            "documentary photography", "portrait photography", "fashion photography",
            "oil painting", "watercolor painting", "acrylic painting", "gouache",
            "charcoal drawing", "pencil sketch", "ink drawing", "fresco",
            "art nouveau", "art deco", "baroque", "renaissance", "romanticism",
            "impressionist", "expressionist", "surrealist", "cubist",
            "pre-raphaelite", "ukiyo-e", "chinese ink wash",
            "concept art", "digital painting", "matte painting", "3D render",
            "low poly 3D", "voxel art", "pixel art", "vector art",
            "anime style", "manga style", "studio ghibli style", "disney style",
            "pixar style", "cartoon style", "comic book style", "graphic novel style",
            "vaporwave aesthetic", "synthwave", "cyberpunk aesthetic", "solarpunk",
            "dark academia", "cottagecore", "steampunk", "dieselpunk", "biopunk",
            "dark souls style", "elden ring style", "final fantasy style"
        ],
        
        "lighting": [
            "golden hour lighting", "blue hour lighting", "harsh midday sun",
            "soft overcast light", "dappled forest light", "sunset backlight",
            "sunrise light", "moonlight", "starlight",
            "dramatic rim lighting", "chiaroscuro lighting", "spotlight",
            "harsh shadows", "silhouette lighting", "contre-jour",
            "neon lighting", "fluorescent lighting", "candlelight", "firelight",
            "bioluminescent glow", "magical glow", "holographic light",
            "volumetric lighting", "god rays", "light shafts", "foggy atmosphere",
            "misty atmosphere", "dusty atmosphere", "rainy atmosphere",
            "warm lighting", "cool lighting", "neutral lighting",
            "high contrast", "low key lighting", "high key lighting"
        ],
        
        "camera": [
            "extreme close-up", "close-up portrait", "medium shot", "full body shot",
            "wide shot", "extreme wide shot", "establishing shot",
            "eye level", "low angle shot", "high angle shot", "bird's eye view",
            "worm's eye view", "dutch angle", "overhead shot",
            "first person view", "over the shoulder", "point of view shot",
            "three-quarter view", "profile view", "frontal view", "rear view",
            "shallow depth of field", "deep focus", "bokeh background",
            "motion blur", "long exposure", "tilt-shift", "fisheye lens",
            "wide angle lens", "telephoto compression", "macro shot"
        ],
        
        "details": [
            "highly detailed", "intricate details", "fine details", "subtle details",
            "sharp focus", "crystal clear", "pristine quality",
            "4k", "8k", "high resolution", "ultra HD",
            "masterpiece", "award winning", "professional", "museum quality",
            "trending on artstation", "featured on behance", "gallery quality",
            "ray tracing", "global illumination", "subsurface scattering",
            "ambient occlusion", "realistic textures", "photogrammetry",
            "expressive brushwork", "visible brushstrokes", "smooth gradients",
            "rich colors", "vibrant palette", "muted tones", "monochromatic"
        ],
        
        "mood": [
            "serene", "peaceful", "tranquil", "joyful", "euphoric",
            "whimsical", "playful", "romantic", "hopeful", "triumphant",
            "ominous", "foreboding", "melancholic", "sorrowful", "tragic",
            "terrifying", "horrific", "unsettling", "disturbing",
            "mysterious", "enigmatic", "surreal", "dreamlike", "ethereal",
            "nostalgic", "bittersweet", "contemplative", "introspective",
            "tense", "intense", "chaotic", "explosive", "dynamic",
            "calm", "still", "quiet", "subtle", "understated",
            "epic", "grand", "intimate", "cozy", "lonely", "isolated"
        ]
    },
    
    "classification": {
        "subject": {
            "keywords": [
                "woman", "man", "girl", "boy", "person", "people", "child", "teen",
                "knight", "wizard", "witch", "warrior", "soldier", "samurai", "ninja",
                "dragon", "phoenix", "wolf", "lion", "tiger", "cat", "dog", "bird",
                "robot", "android", "cyborg", "alien", "demon", "angel", "ghost",
                "fairy", "elf", "dwarf", "orc", "goblin", "vampire", "werewolf"
            ],
            "patterns": [r"^a ", r"^an ", r"^the ", r"^my "]
        },
        "action": {
            "keywords": [
                "standing", "sitting", "walking", "running", "flying", "swimming",
                "fighting", "battling", "dancing", "singing", "playing", "reading",
                "casting", "summoning", "meditating", "praying", "sleeping", "dreaming",
                "exploring", "hunting", "searching", "watching", "waiting"
            ],
            "patterns": [r"ing\s+(in|on|at|through|over|above|below|near)"]
        },
        "environment": {
            "keywords": [
                "forest", "mountain", "desert", "ocean", "sea", "beach", "river",
                "city", "town", "village", "castle", "tower", "temple", "church",
                "cave", "cavern", "dungeon", "ruins", "wasteland", "garden",
                "space", "planet", "moon", "station", "void", "dimension", "realm"
            ],
            "patterns": [r"^in (a |an |the )?", r"^at (a |an |the )?", r"^inside"]
        },
        "style": {
            "keywords": [
                "photorealistic", "hyperrealistic", "realistic", "cinematic",
                "painting", "drawing", "sketch", "illustration", "render",
                "anime", "manga", "cartoon", "comic", "pixel", "voxel",
                "baroque", "renaissance", "impressionist", "surrealist",
                "cyberpunk", "steampunk", "solarpunk", "dieselpunk",
                "art nouveau", "art deco", "gothic", "victorian"
            ],
            "patterns": [r"style$", r"aesthetic$", r"^in the style of"]
        },
        "lighting": {
            "keywords": [
                "lighting", "light", "lit", "glow", "glowing", "illuminated",
                "shadow", "shadows", "sunlight", "moonlight", "starlight",
                "golden hour", "blue hour", "sunset", "sunrise", "dawn", "dusk",
                "neon", "fluorescent", "candlelight", "firelight", "torchlight"
            ],
            "patterns": [r"lighting$", r"light$", r"lit$"]
        },
        "camera": {
            "keywords": [
                "close-up", "closeup", "wide shot", "medium shot", "full body",
                "portrait", "angle", "view", "perspective", "lens",
                "bokeh", "depth of field", "dof", "focus", "blur",
                "fisheye", "telephoto", "macro", "tilt-shift"
            ],
            "patterns": [r"shot$", r"angle$", r"view$", r"^\d+mm"]
        },
        "details": {
            "keywords": [
                "detailed", "intricate", "sharp", "crisp", "clear",
                "4k", "8k", "hd", "uhd", "high resolution",
                "masterpiece", "quality", "professional", "award",
                "artstation", "behance", "trending"
            ],
            "patterns": [r"detailed$", r"quality$", r"^\d+k$"]
        },
        "mood": {
            "keywords": [
                "serene", "peaceful", "calm", "tranquil", "joyful", "happy",
                "dark", "ominous", "foreboding", "mysterious", "eerie",
                "epic", "dramatic", "intense", "dynamic", "chaotic",
                "melancholic", "sad", "nostalgic", "romantic", "dreamy"
            ],
            "patterns": [r"atmosphere$", r"mood$", r"feeling$", r"vibe$"]
        }
    },
    
    "rules": {
        "mandatory": ["details"],
        "never_override": ["subject"],
        "standard": ["style", "lighting", "environment", "camera"],
        "optional": ["mood", "action"]
    },
    
    "anti_pairs": {
        "underwater": ["sunset", "sunrise", "golden hour", "harsh sunlight", "dusty atmosphere"],
        "space station": ["golden hour", "forest light", "dappled"],
        "cave": ["golden hour", "blue hour", "sunset backlight", "harsh midday sun"],
        "night": ["harsh midday sun", "bright daylight", "golden hour"],
        "graveyard": ["joyful", "playful", "whimsical", "euphoric"],
        "sunny": ["ominous", "foreboding", "horrific", "terrifying"],
        "pixel art": ["ray tracing", "photogrammetry", "subsurface scattering", "hyperrealistic"],
        "watercolor": ["8k", "photogrammetry", "hyperrealistic", "ray tracing"],
        "sketch": ["ray tracing", "photogrammetry", "8k resolution"],
        "moonlight": ["harsh midday sun", "golden hour", "bright daylight"],
        "neon": ["candlelight", "firelight", "torchlight", "medieval"]
    }
}

# Ordered categories for deterministic iteration
ORDERED_CATEGORIES = ["subject", "action", "environment", "style", "lighting", "camera", "details", "mood"]

# Intensity fill rates
INTENSITY_RATES = {
    "minimal": 0.25,
    "light": 0.50,
    "moderate": 0.75,
    "full": 1.00
}

# Maximum output word count
MAX_WORDS = 150


# =============================================================================
# CORE HASH FUNCTIONS - O(1) Position-Based Selection
# =============================================================================

def enhancement_hash(seed: int, input_hash: int, coord: int) -> int:
    """
    Pure O(1) hash from seed + input_hash + coordinate.
    Uses xxhash32 for speed and cross-platform determinism.
    
    Coordinate layers:
    - 0: template selection
    - 1..N: category enhancement selection
    - 1000+: anti-pair conflict resolution
    - 2000+: intensity gap selection
    """
    # Mask to 32-bit to ensure values fit in unsigned int
    h = xxhash.xxh32(seed=seed & 0xFFFFFFFF)
    h.update(struct.pack('<II', input_hash & 0xFFFFFFFF, coord & 0xFFFFFFFF))
    return h.intdigest()


def hash_to_index(h: int, pool_size: int) -> int:
    """Map hash to valid index in any pool."""
    return h % pool_size


# =============================================================================
# PHASE 1: TOKENIZATION
# =============================================================================

def tokenize(prompt: str) -> list:
    """
    Split prompt into semantic tokens on standard delimiters.
    Preserves multi-word phrases as single tokens.
    """
    # Primary split on comma
    tokens = prompt.split(",")
    
    # Secondary split on other delimiters within tokens
    result = []
    for token in tokens:
        # Split on ' - ' and ' | ' but not hyphens within words
        sub_tokens = re.split(r'\s+-\s+|\s+\|\s+', token)
        for sub in sub_tokens:
            cleaned = sub.strip()
            if cleaned:
                result.append(cleaned)
    
    return result


# =============================================================================
# PHASE 2: CLASSIFICATION
# =============================================================================

def classify_token_multi(token: str, classification: dict) -> list:
    """
    Return ALL categories a token satisfies (multi-category assignment).
    Returns ["unclassified"] if no category matches.
    """
    categories = []
    token_lower = token.lower()
    
    for category, rules in classification.items():
        matched = False
        
        # Check keywords
        for keyword in rules.get("keywords", []):
            if keyword in token_lower:
                matched = True
                break
        
        # Check patterns if no keyword match
        if not matched:
            for pattern in rules.get("patterns", []):
                if re.search(pattern, token_lower):
                    matched = True
                    break
        
        if matched:
            categories.append(category)
    
    return categories if categories else ["unclassified"]


def classify_all_tokens(tokens: list, classification: dict) -> dict:
    """
    Classify all tokens, allowing multi-category assignment.
    Returns dict mapping category -> list of tokens.
    """
    classified = {cat: [] for cat in ORDERED_CATEGORIES}
    classified["unclassified"] = []
    
    for token in tokens:
        categories = classify_token_multi(token, classification)
        for cat in categories:
            if cat in classified:
                classified[cat].append(token)
    
    return classified


# =============================================================================
# PHASE 3: GAP FINDING & RULES
# =============================================================================

def find_gaps(classified: dict, pools: dict) -> list:
    """
    Find which categories are missing from the input.
    """
    present = {k for k, v in classified.items() if v and k != "unclassified"}
    all_pools = set(pools.keys())
    return sorted(list(all_pools - present))  # Sorted for determinism


def apply_category_rules(gaps: list, rules: dict, intensity: str) -> list:
    """
    Filter gaps based on category rules and intensity level.
    """
    final_gaps = []
    
    for gap in gaps:
        # Mandatory categories always included
        if gap in rules.get("mandatory", []):
            final_gaps.append(gap)
        # Standard categories included
        elif gap in rules.get("standard", []):
            final_gaps.append(gap)
        # Optional categories only at moderate+ intensity
        elif gap in rules.get("optional", []):
            if intensity in ["moderate", "full"]:
                final_gaps.append(gap)
    
    return final_gaps


def select_gaps_to_fill(seed: int, input_hash: int, gaps: list, intensity: str) -> list:
    """
    Deterministically select which gaps to fill based on intensity.
    Uses position-hash to score and rank gaps.
    """
    rate = INTENSITY_RATES.get(intensity, 0.75)
    
    if rate >= 1.0:
        return gaps
    
    num_to_fill = max(1, int(len(gaps) * rate))
    
    if num_to_fill >= len(gaps):
        return gaps
    
    # Score each gap with position-hash for deterministic selection
    gap_scores = []
    for i, gap in enumerate(gaps):
        h = enhancement_hash(seed, input_hash, 2000 + i)
        gap_scores.append((gap, h))
    
    # Sort by hash value (deterministic ordering)
    gap_scores.sort(key=lambda x: x[1])
    
    # Take top N
    return [g[0] for g in gap_scores[:num_to_fill]]


# =============================================================================
# PHASE 4: ENHANCEMENT SELECTION WITH ANTI-PAIRING
# =============================================================================

def build_forbidden_set(existing_tokens: list, anti_pairs: dict) -> set:
    """
    Build set of forbidden terms based on existing tokens and anti-pair rules.
    """
    forbidden = set()
    
    for token in existing_tokens:
        token_lower = token.lower()
        for trigger, incompatible in anti_pairs.items():
            if trigger in token_lower:
                forbidden.update(word.lower() for word in incompatible)
    
    return forbidden


def select_with_antipair_check(
    seed: int,
    input_hash: int,
    category_idx: int,
    pool: list,
    forbidden: set
) -> str:
    """
    Select enhancement with anti-pair avoidance.
    Uses shifted coordinates for conflict resolution.
    """
    # Primary selection
    h = enhancement_hash(seed, input_hash, category_idx)
    primary_idx = hash_to_index(h, len(pool))
    selection = pool[primary_idx]
    
    # Check for conflict
    selection_lower = selection.lower()
    if any(f in selection_lower for f in forbidden):
        # Use conflict-resolution coordinate layer
        conflict_coord = category_idx + 1000
        attempts = 0
        max_attempts = min(len(pool), 50)  # Cap attempts
        
        while attempts < max_attempts:
            h2 = enhancement_hash(seed, input_hash, conflict_coord + attempts)
            alt_idx = hash_to_index(h2, len(pool))
            alt_selection = pool[alt_idx]
            
            if not any(f in alt_selection.lower() for f in forbidden):
                return alt_selection
            attempts += 1
        
        # Fallback: return primary anyway (pool exhausted or all conflicting)
        return selection
    
    return selection


# =============================================================================
# PHASE 5: TEMPLATE SELECTION & FORMATTING
# =============================================================================

def select_template(seed: int, input_hash: int, templates: list) -> str:
    """Select template using position-hash at coordinate 0."""
    h = enhancement_hash(seed, input_hash, 0)
    idx = hash_to_index(h, len(templates))
    return templates[idx]


def safe_format_template(template: str, components: dict) -> str:
    """
    Format template with components, handling missing/empty values gracefully.
    """
    result = template
    
    for key, value in components.items():
        placeholder = "{" + key + "}"
        if value:
            result = result.replace(placeholder, value)
        else:
            # Remove placeholder
            result = result.replace(placeholder, "")
    
    # Clean up formatting artifacts - order matters!
    result = re.sub(r'\s+', ' ', result)  # Multiple spaces to single
    result = re.sub(r'\s*,\s*', ', ', result)  # Normalize comma spacing
    result = re.sub(r'(,\s*)+', ', ', result)  # Multiple commas to single
    result = re.sub(r'^\s*,\s*', '', result)  # Leading comma
    result = re.sub(r'\s*,\s*$', '', result)  # Trailing comma
    result = re.sub(r'\s*atmosphere\s*$', ' atmosphere', result)  # Fix atmosphere suffix
    result = re.sub(r'^\s*scene\s*,', '', result)  # Remove orphan "scene" at start
    result = result.strip()
    
    # Final cleanup - ensure no double commas remain
    while ',,' in result or ', ,' in result:
        result = result.replace(',,', ',').replace(', ,', ',')
    
    return result


# =============================================================================
# PHASE 6: MERGING & DEDUPLICATION
# =============================================================================

def merge_with_unclassified(enhanced: str, unclassified: list) -> str:
    """
    Append unclassified tokens (LoRA triggers, etc.) to enhanced prompt.
    """
    if not unclassified:
        return enhanced
    
    unclassified_str = ", ".join(unclassified)
    return f"{enhanced}, {unclassified_str}"


def deduplicate_prompt(prompt: str) -> str:
    """
    Remove semantic duplicates while preserving order.
    Uses simple stemming for dedup detection.
    """
    seen_stems = set()
    final_tokens = []
    
    tokens = [t.strip() for t in prompt.split(",") if t.strip()]
    
    for token in tokens:
        # Simple stemming for dedup
        stem = token.lower()
        # Remove common suffixes
        for suffix in ["ing", "ed", "ly", "s"]:
            if stem.endswith(suffix) and len(stem) > len(suffix) + 2:
                stem = stem[:-len(suffix)]
                break
        
        # Also check for word overlap
        words = set(stem.split())
        
        # Check if this stem or significant word overlap already seen
        is_duplicate = stem in seen_stems
        if not is_duplicate and len(words) > 0:
            for seen in seen_stems:
                seen_words = set(seen.split())
                overlap = words & seen_words
                if len(overlap) >= min(len(words), len(seen_words)) * 0.7:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            seen_stems.add(stem)
            final_tokens.append(token)
    
    return ", ".join(final_tokens)


# =============================================================================
# PHASE 7: LENGTH ENFORCEMENT
# =============================================================================

def enforce_length_limit(prompt: str, max_words: int = MAX_WORDS) -> str:
    """
    Truncate prompt if it exceeds maximum word count.
    Deterministic: always removes from end.
    """
    words = prompt.split()
    if len(words) <= max_words:
        return prompt
    
    # Truncate from end
    truncated = words[:max_words]
    result = " ".join(truncated)
    
    # Clean up trailing comma/whitespace
    result = result.rstrip(",").rstrip()
    
    return result


# =============================================================================
# MAIN ENHANCEMENT FUNCTION
# =============================================================================

def enhance_prompt(
    input_prompt: str,
    seed: int,
    intensity: str = "moderate",
    max_words: int = MAX_WORDS
) -> str:
    """
    Complete ZeroENH V1 enhancement algorithm.
    
    GUARANTEE: Same (input_prompt, seed, intensity) → identical output, always.
    
    Args:
        input_prompt: The prompt to enhance
        seed: World seed for deterministic selection
        intensity: Enhancement level (minimal/light/moderate/full)
        max_words: Maximum word count for output
    
    Returns:
        Enhanced prompt string
    """
    profile = DEFAULT_PROFILE
    
    # Handle empty input
    if not input_prompt or not input_prompt.strip():
        return input_prompt
    
    # === PHASE 1: TOKENIZE ===
    tokens = tokenize(input_prompt)
    
    # === PHASE 2: CLASSIFY (multi-category) ===
    classified = classify_all_tokens(tokens, profile["classification"])
    
    # === PHASE 3: FIND GAPS ===
    gaps = find_gaps(classified, profile["pools"])
    
    # === PHASE 3.5: APPLY CATEGORY RULES ===
    gaps = apply_category_rules(gaps, profile["rules"], intensity)
    
    # === PHASE 3.6: APPLY INTENSITY ===
    input_hash = xxhash.xxh32(input_prompt.encode()).intdigest()
    gaps = select_gaps_to_fill(seed, input_hash, gaps, intensity)
    
    # === PHASE 4: SELECT ENHANCEMENTS ===
    # Build forbidden set from all existing tokens
    existing_tokens = []
    for cat_tokens in classified.values():
        existing_tokens.extend(cat_tokens)
    
    forbidden = build_forbidden_set(existing_tokens, profile["anti_pairs"])
    
    enhancements = {}
    for i, gap in enumerate(sorted(gaps)):  # Sort for determinism
        pool = profile["pools"][gap]
        selection = select_with_antipair_check(
            seed, input_hash, i + 1,  # category_coord starts at 1
            pool, forbidden
        )
        enhancements[gap] = selection
    
    # === PHASE 5: SELECT TEMPLATE & BUILD COMPONENTS ===
    template = select_template(seed, input_hash, profile["templates"])
    
    components = {}
    for category in ORDERED_CATEGORIES:
        if category in classified and classified[category]:
            # User provided - keep original
            components[category] = ", ".join(classified[category])
        elif category in enhancements:
            # We selected enhancement
            components[category] = enhancements[category]
        else:
            # Gap not filled
            components[category] = ""
    
    # === PHASE 6: FORMAT & MERGE ===
    enhanced = safe_format_template(template, components)
    
    # Add unclassified tokens (LoRA triggers, etc.)
    enhanced = merge_with_unclassified(enhanced, classified.get("unclassified", []))
    
    # === PHASE 7: DEDUPLICATE ===
    enhanced = deduplicate_prompt(enhanced)
    
    # === PHASE 8: ENFORCE LENGTH ===
    enhanced = enforce_length_limit(enhanced, max_words)
    
    return enhanced


# =============================================================================
# COMFYUI NODE CLASS
# =============================================================================

class DJZZeroENHV1:
    """
    DJZ Zero ENH V1 - Deterministic Prompt Enhancement
    
    Enhances input prompts with contextually appropriate additions using
    position-is-seed methodology. Same (input, seed, intensity) always
    produces the same enhanced output.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Input prompt to enhance"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xFFFFFFFF,
                    "tooltip": "Seed for deterministic enhancement - same seed = same output"
                }),
                "intensity": (["minimal", "light", "moderate", "full"], {
                    "default": "moderate",
                    "tooltip": "Enhancement intensity: minimal=25%, light=50%, moderate=75%, full=100% of gaps filled"
                }),
            },
            "optional": {
                "max_words": ("INT", {
                    "default": 150,
                    "min": 10,
                    "max": 500,
                    "tooltip": "Maximum word count for output"
                }),
                "prefix": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Text to prepend to enhanced prompt"
                }),
                "suffix": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Text to append to enhanced prompt"
                }),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("enhanced_prompt",)
    OUTPUT_TOOLTIPS = ("Deterministically enhanced prompt",)
    FUNCTION = "enhance"
    CATEGORY = "DJZ-Nodes"
    DESCRIPTION = "Deterministically enhances prompts using position-is-seed methodology. Same inputs = same output, always."
    
    def enhance(self, prompt: str, seed: int, intensity: str,
                max_words: int = 150, prefix: str = "", suffix: str = "") -> tuple:
        """
        Enhance a prompt deterministically.
        
        Returns:
            Tuple containing the enhanced prompt string
        """
        # Perform enhancement
        enhanced = enhance_prompt(prompt, seed, intensity, max_words)
        
        # Apply prefix/suffix if provided
        if prefix:
            enhanced = f"{prefix} {enhanced}"
        if suffix:
            enhanced = f"{enhanced} {suffix}"
        
        return (enhanced,)
    
    @classmethod
    def IS_CHANGED(cls, prompt: str, seed: int, intensity: str,
                   max_words: int = 150, prefix: str = "", suffix: str = ""):
        """Ensure node updates when inputs change."""
        input_hash = xxhash.xxh32(prompt.encode()).intdigest()
        intensity_hash = xxhash.xxh32(intensity.encode()).intdigest()
        return enhancement_hash(seed ^ intensity_hash, input_hash, 0)


# =============================================================================
# COMFYUI REGISTRATION
# =============================================================================

NODE_CLASS_MAPPINGS = {
    "DJZ-ZeroENH-V1": DJZZeroENHV1,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DJZ-ZeroENH-V1": "DJZ Zero ENH V1",
}


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DJZ-ZeroENH-V1 - Deterministic Prompt Enhancement")
    print("=" * 70)
    
    # Test cases
    test_cases = [
        ("a cat", 42),
        ("a woman in a forest", 42),
        ("cyberpunk samurai, neon lighting", 12345),
        ("golden hour portrait", 999),
        ("a dragon XYZ F4L", 42),  # With LoRA triggers
        ("underwater scene with fish", 42),  # Anti-pair test
        ("", 42),  # Empty input
    ]
    
    print("\n[Determinism Verification]")
    print("-" * 70)
    
    for input_prompt, seed in test_cases:
        print(f"\nInput: \"{input_prompt}\" (seed={seed})")
        
        # Generate multiple times to verify determinism
        results = [enhance_prompt(input_prompt, seed, "moderate") for _ in range(5)]
        
        if len(set(results)) == 1:
            print(f"✓ DETERMINISTIC - All 5 runs identical")
            print(f"  Output: \"{results[0][:100]}{'...' if len(results[0]) > 100 else ''}\"")
        else:
            print(f"✗ NON-DETERMINISTIC - Multiple outputs detected!")
            for i, r in enumerate(results):
                print(f"  Run {i}: {r[:50]}...")
    
    print("\n[Intensity Comparison]")
    print("-" * 70)
    test_input = "a knight"
    test_seed = 42
    
    for intensity in ["minimal", "light", "moderate", "full"]:
        result = enhance_prompt(test_input, test_seed, intensity)
        word_count = len(result.split())
        print(f"\n{intensity.upper()} ({word_count} words):")
        print(f"  {result}")
    
    print("\n[Anti-Pair Test]")
    print("-" * 70)
    # Test that underwater doesn't get golden hour lighting
    underwater_result = enhance_prompt("underwater scene", 42, "full")
    print(f"Input: \"underwater scene\"")
    print(f"Output: \"{underwater_result}\"")
    if "golden hour" in underwater_result.lower() or "sunset" in underwater_result.lower():
        print("✗ Anti-pair FAILED - conflicting lighting detected")
    else:
        print("✓ Anti-pair working - no conflicting lighting")
    
    print("\n[LoRA Trigger Preservation]")
    print("-" * 70)
    lora_input = "a woman ohwx_person XYZ"
    lora_result = enhance_prompt(lora_input, 42, "moderate")
    print(f"Input: \"{lora_input}\"")
    print(f"Output: \"{lora_result}\"")
    if "ohwx_person" in lora_result and "XYZ" in lora_result:
        print("✓ LoRA triggers preserved")
    else:
        print("✗ LoRA triggers LOST")
    
    print("\n[Cross-Seed Verification]")
    print("-" * 70)
    # Same input with different seeds should produce different outputs
    test_input = "a warrior"
    seeds = [0, 42, 12345, 99999, 2147483647]
    results = {}
    for s in seeds:
        results[s] = enhance_prompt(test_input, s, "moderate")
    
    unique_results = len(set(results.values()))
    print(f"Input: \"{test_input}\" with {len(seeds)} different seeds")
    print(f"Unique outputs: {unique_results}/{len(seeds)}")
    if unique_results == len(seeds):
        print("✓ All seeds produce unique outputs")
    else:
        print("⚠ Some seeds produced identical outputs (may be expected for very different seeds)")
    
    for s, r in results.items():
        print(f"  Seed {s}: {r[:60]}...")
    
    print("\n[Order Independence Test]")
    print("-" * 70)
    # Verify that calling in different orders produces same results
    inputs = ["a cat", "a dog", "a bird", "a fish"]
    seed = 42
    
    forward_results = {inp: enhance_prompt(inp, seed, "moderate") for inp in inputs}
    reverse_results = {inp: enhance_prompt(inp, seed, "moderate") for inp in reversed(inputs)}
    
    all_match = all(forward_results[inp] == reverse_results[inp] for inp in inputs)
    if all_match:
        print("✓ Order-independent - same results regardless of call order")
    else:
        print("✗ Order-DEPENDENT - results vary by call order!")
    
    print("\n[Word Count Limit Test]")
    print("-" * 70)
    long_input = "a very detailed scene with many elements, cinematic lighting, epic atmosphere, highly detailed textures"
    result_default = enhance_prompt(long_input, 42, "full", max_words=150)
    result_short = enhance_prompt(long_input, 42, "full", max_words=20)
    
    print(f"Default limit (150): {len(result_default.split())} words")
    print(f"Short limit (20): {len(result_short.split())} words")
    
    if len(result_short.split()) <= 20:
        print("✓ Word limit enforced correctly")
    else:
        print("✗ Word limit NOT enforced")
    
    print("\n" + "=" * 70)
    print("Testing complete!")
    print("=" * 70)
