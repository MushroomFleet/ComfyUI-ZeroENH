"""
DJZ-ZeroENH-V2 - Deterministic Prompt Enhancement with Custom Profiles
ComfyUI Custom Node using ZeroBytes Position-is-Seed Methodology

Enhances input prompts with contextually appropriate additions using O(1) coordinate hashing.
Same (input_prompt, seed, intensity, profile) → same enhanced output, always, everywhere.

V2 Features:
- JSON profile support for customizable vocabulary pools
- Auto-discovery of custom profiles from /profiles directory
- Profile inheritance (extends: "base.json")
- Backward compatible with V1 default vocabulary
- Profile statistics via info node
"""

import json
import os
import re
import struct
from pathlib import Path

try:
    import xxhash
except ImportError:
    raise ImportError(
        "DJZ-ZeroENH requires xxhash. Install with: pip install xxhash"
    )


# =============================================================================
# PROFILE MANAGEMENT
# =============================================================================

def get_profiles_dir() -> Path:
    """Get the profiles directory path."""
    return Path(__file__).parent / "profiles"


def discover_profiles() -> list:
    """
    Discover all available JSON profiles.
    Returns list of profile filenames (without path).
    """
    profiles_dir = get_profiles_dir()
    
    if not profiles_dir.exists():
        profiles_dir.mkdir(parents=True, exist_ok=True)
        return ["default.json"]
    
    profiles = sorted([
        f.name for f in profiles_dir.glob("*.json")
        if f.is_file()
    ])
    
    # Ensure default is first if it exists
    if "default.json" in profiles:
        profiles.remove("default.json")
        profiles.insert(0, "default.json")
    
    return profiles if profiles else ["default.json"]


def load_profile(profile_name: str) -> dict:
    """
    Load a profile from JSON file, resolving inheritance if specified.
    Returns complete profile dict with all fields populated.
    """
    profiles_dir = get_profiles_dir()
    profile_path = profiles_dir / profile_name
    
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_name}")
    
    with open(profile_path, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    # Handle inheritance
    if "extends" in profile:
        base_name = profile["extends"]
        base_path = profiles_dir / base_name
        
        if not base_path.exists():
            raise FileNotFoundError(f"Base profile not found: {base_name}")
        
        with open(base_path, 'r', encoding='utf-8') as f:
            base = json.load(f)
        
        # Merge: profile overrides base
        profile = merge_profiles(base, profile)
    
    # Validate required fields
    validate_profile(profile, profile_name)
    
    return profile


def merge_profiles(base: dict, child: dict) -> dict:
    """
    Merge child profile into base profile.
    Child values override base values.
    """
    merged = {**base}
    
    # Metadata from child
    merged["name"] = child.get("name", base.get("name", "Unknown"))
    merged["description"] = child.get("description", base.get("description", ""))
    merged["version"] = child.get("version", base.get("version", "1.0.0"))
    merged["type"] = child.get("type", base.get("type", "enhancement"))
    
    # Templates: use child's if provided, else base
    if "templates" in child and child["templates"]:
        merged["templates"] = child["templates"]
    
    # Pools: child pools override base pools entirely (per-pool)
    merged["pools"] = {**base.get("pools", {})}
    for pool_name, pool_items in child.get("pools", {}).items():
        merged["pools"][pool_name] = pool_items
    
    # Classification: merge with child overriding
    merged["classification"] = {**base.get("classification", {})}
    for cat_name, cat_rules in child.get("classification", {}).items():
        merged["classification"][cat_name] = cat_rules
    
    # Rules: child overrides base entirely if provided
    if "rules" in child:
        merged["rules"] = child["rules"]
    
    # Anti-pairs: merge with child additions
    merged["anti_pairs"] = {
        **base.get("anti_pairs", {}),
        **child.get("anti_pairs", {})
    }
    
    return merged


def validate_profile(profile: dict, profile_name: str):
    """Validate that profile has required fields."""
    if "templates" not in profile or not profile["templates"]:
        raise ValueError(f"Profile {profile_name} missing 'templates' field")
    if "pools" not in profile or not profile["pools"]:
        raise ValueError(f"Profile {profile_name} missing 'pools' field")


def calculate_combinations(profile: dict) -> int:
    """Calculate total unique enhancement combinations for a profile."""
    total = len(profile.get("templates", []))
    for pool in profile.get("pools", {}).values():
        if pool:
            total *= len(pool)
    return total


# =============================================================================
# DEFAULT PROFILE (FALLBACK)
# =============================================================================

DEFAULT_PROFILE = {
    "name": "Default (Built-in)",
    "description": "Built-in fallback profile matching V1 vocabulary",
    "version": "1.0.0",
    "type": "enhancement",
    
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
            "patterns": ["^a ", "^an ", "^the ", "^my "]
        },
        "action": {
            "keywords": [
                "standing", "sitting", "walking", "running", "flying", "swimming",
                "fighting", "battling", "dancing", "singing", "playing", "reading",
                "casting", "summoning", "meditating", "praying", "sleeping", "dreaming",
                "exploring", "hunting", "searching", "watching", "waiting"
            ],
            "patterns": ["ing\\s+(in|on|at|through|over|above|below|near)"]
        },
        "environment": {
            "keywords": [
                "forest", "mountain", "desert", "ocean", "sea", "beach", "river",
                "city", "town", "village", "castle", "tower", "temple", "church",
                "cave", "cavern", "dungeon", "ruins", "wasteland", "garden",
                "space", "planet", "moon", "station", "void", "dimension", "realm"
            ],
            "patterns": ["^in (a |an |the )?", "^at (a |an |the )?", "^inside"]
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
            "patterns": ["style$", "aesthetic$", "^in the style of"]
        },
        "lighting": {
            "keywords": [
                "lighting", "light", "lit", "glow", "glowing", "illuminated",
                "shadow", "shadows", "sunlight", "moonlight", "starlight",
                "golden hour", "blue hour", "sunset", "sunrise", "dawn", "dusk",
                "neon", "fluorescent", "candlelight", "firelight", "torchlight"
            ],
            "patterns": ["lighting$", "light$", "lit$"]
        },
        "camera": {
            "keywords": [
                "close-up", "closeup", "wide shot", "medium shot", "full body",
                "portrait", "angle", "view", "perspective", "lens",
                "bokeh", "depth of field", "dof", "focus", "blur",
                "fisheye", "telephoto", "macro", "tilt-shift"
            ],
            "patterns": ["shot$", "angle$", "view$", "^\\d+mm"]
        },
        "details": {
            "keywords": [
                "detailed", "intricate", "sharp", "crisp", "clear",
                "4k", "8k", "hd", "uhd", "high resolution",
                "masterpiece", "quality", "professional", "award",
                "artstation", "behance", "trending"
            ],
            "patterns": ["detailed$", "quality$", "^\\d+k$"]
        },
        "mood": {
            "keywords": [
                "serene", "peaceful", "calm", "tranquil", "joyful", "happy",
                "dark", "ominous", "foreboding", "mysterious", "eerie",
                "epic", "dramatic", "intense", "dynamic", "chaotic",
                "melancholic", "sad", "nostalgic", "romantic", "dreamy"
            ],
            "patterns": ["atmosphere$", "mood$", "feeling$", "vibe$"]
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
    profile: dict,
    intensity: str = "moderate",
    max_words: int = MAX_WORDS
) -> str:
    """
    Complete ZeroENH V2 enhancement algorithm with profile support.
    
    GUARANTEE: Same (input_prompt, seed, profile, intensity) → identical output, always.
    
    Args:
        input_prompt: The prompt to enhance
        seed: World seed for deterministic selection
        profile: Loaded profile dict with pools, templates, classification, etc.
        intensity: Enhancement level (minimal/light/moderate/full)
        max_words: Maximum word count for output
    
    Returns:
        Enhanced prompt string
    """
    # Handle empty input
    if not input_prompt or not input_prompt.strip():
        return input_prompt
    
    # Get profile components with fallbacks
    classification = profile.get("classification", DEFAULT_PROFILE["classification"])
    pools = profile.get("pools", DEFAULT_PROFILE["pools"])
    templates = profile.get("templates", DEFAULT_PROFILE["templates"])
    rules = profile.get("rules", DEFAULT_PROFILE["rules"])
    anti_pairs = profile.get("anti_pairs", DEFAULT_PROFILE["anti_pairs"])
    
    # === PHASE 1: TOKENIZE ===
    tokens = tokenize(input_prompt)
    
    # === PHASE 2: CLASSIFY (multi-category) ===
    classified = classify_all_tokens(tokens, classification)
    
    # === PHASE 3: FIND GAPS ===
    gaps = find_gaps(classified, pools)
    
    # === PHASE 3.5: APPLY CATEGORY RULES ===
    gaps = apply_category_rules(gaps, rules, intensity)
    
    # === PHASE 3.6: APPLY INTENSITY ===
    input_hash = xxhash.xxh32(input_prompt.encode()).intdigest()
    gaps = select_gaps_to_fill(seed, input_hash, gaps, intensity)
    
    # === PHASE 4: SELECT ENHANCEMENTS ===
    # Build forbidden set from all existing tokens
    existing_tokens = []
    for cat_tokens in classified.values():
        existing_tokens.extend(cat_tokens)
    
    forbidden = build_forbidden_set(existing_tokens, anti_pairs)
    
    enhancements = {}
    for i, gap in enumerate(sorted(gaps)):  # Sort for determinism
        if gap in pools and pools[gap]:
            pool = pools[gap]
            selection = select_with_antipair_check(
                seed, input_hash, i + 1,  # category_coord starts at 1
                pool, forbidden
            )
            enhancements[gap] = selection
    
    # === PHASE 5: SELECT TEMPLATE & BUILD COMPONENTS ===
    template = select_template(seed, input_hash, templates)
    
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
# COMFYUI NODE CLASS - MAIN ENHANCER
# =============================================================================

class DJZZeroENHV2:
    """
    DJZ Zero ENH V2 - Deterministic Prompt Enhancement with Custom Profiles
    
    Enhances input prompts with contextually appropriate additions using
    position-is-seed methodology. Same (input, seed, intensity, profile) always
    produces the same enhanced output.
    
    V2 adds JSON profile support for customizable vocabulary pools.
    """
    
    # Class-level cache for profiles
    _profile_cache: dict = {}
    
    @classmethod
    def INPUT_TYPES(cls):
        # Discover available profiles
        profiles = discover_profiles()
        
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Input prompt to enhance"
                }),
                "profile": (profiles, {
                    "default": profiles[0] if profiles else "default.json",
                    "tooltip": "Select enhancement profile (JSON files in /profiles folder)"
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
    DESCRIPTION = "Deterministically enhances prompts using position-is-seed methodology with custom JSON profiles. Same inputs = same output, always."
    
    def enhance(self, prompt: str, profile: str, seed: int, intensity: str,
                max_words: int = 150, prefix: str = "", suffix: str = "") -> tuple:
        """
        Enhance a prompt deterministically using selected profile.
        
        Returns:
            Tuple containing the enhanced prompt string
        """
        # Load profile (with caching)
        if profile not in self._profile_cache:
            try:
                self._profile_cache[profile] = load_profile(profile)
            except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
                # Fallback to built-in default
                print(f"[ZeroENH] Warning: Error loading profile '{profile}': {e}")
                print(f"[ZeroENH] Using built-in default profile")
                self._profile_cache[profile] = DEFAULT_PROFILE
        
        profile_data = self._profile_cache[profile]
        
        # Perform enhancement
        enhanced = enhance_prompt(prompt, seed, profile_data, intensity, max_words)
        
        # Apply prefix/suffix if provided
        if prefix:
            enhanced = f"{prefix} {enhanced}"
        if suffix:
            enhanced = f"{enhanced} {suffix}"
        
        return (enhanced,)
    
    @classmethod
    def IS_CHANGED(cls, prompt: str, profile: str, seed: int, intensity: str,
                   max_words: int = 150, prefix: str = "", suffix: str = ""):
        """Ensure node updates when inputs change."""
        input_hash = xxhash.xxh32(prompt.encode()).intdigest()
        profile_hash = xxhash.xxh32(profile.encode()).intdigest()
        intensity_hash = xxhash.xxh32(intensity.encode()).intdigest()
        return enhancement_hash(seed ^ profile_hash ^ intensity_hash, input_hash, 0)


# =============================================================================
# COMFYUI NODE CLASS - PROFILE INFO
# =============================================================================

class DJZZeroENHProfileInfo:
    """
    Utility node to display profile statistics.
    Shows pool sizes and total combinations for selected profile.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        profiles = discover_profiles()
        
        return {
            "required": {
                "profile": (profiles, {
                    "default": profiles[0] if profiles else "default.json",
                }),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("info",)
    FUNCTION = "get_info"
    CATEGORY = "DJZ-Nodes"
    DESCRIPTION = "Display statistics about a ZeroENH enhancement profile"
    
    def get_info(self, profile: str) -> tuple:
        """Get profile information as formatted string."""
        try:
            profile_data = load_profile(profile)
        except Exception as e:
            return (f"Error loading profile: {e}",)
        
        lines = [
            f"Profile: {profile_data.get('name', profile)}",
            f"Description: {profile_data.get('description', 'N/A')}",
            f"Version: {profile_data.get('version', 'N/A')}",
            f"Type: {profile_data.get('type', 'N/A')}",
            "",
            "Pool Sizes:",
        ]
        
        for pool_name in ORDERED_CATEGORIES:
            pool_items = profile_data.get('pools', {}).get(pool_name, [])
            lines.append(f"  {pool_name}: {len(pool_items)} entries")
        
        lines.append(f"  templates: {len(profile_data.get('templates', []))} variations")
        lines.append("")
        
        # Rules
        rules = profile_data.get('rules', {})
        lines.append("Rules:")
        lines.append(f"  mandatory: {rules.get('mandatory', [])}")
        lines.append(f"  optional: {rules.get('optional', [])}")
        lines.append("")
        
        # Anti-pairs count
        anti_pairs = profile_data.get('anti_pairs', {})
        lines.append(f"Anti-pairs: {len(anti_pairs)} trigger rules")
        lines.append("")
        
        total = calculate_combinations(profile_data)
        lines.append(f"Total unique enhancements: {total:,}")
        lines.append(f"Scientific notation: {total:.2e}")
        
        return ("\n".join(lines),)
    
    @classmethod
    def IS_CHANGED(cls, profile: str):
        """Check if profile file has changed."""
        profile_path = get_profiles_dir() / profile
        if profile_path.exists():
            return profile_path.stat().st_mtime
        return 0


# =============================================================================
# COMFYUI REGISTRATION
# =============================================================================

NODE_CLASS_MAPPINGS = {
    "DJZ-ZeroENH-V2": DJZZeroENHV2,
    "DJZ-ZeroENH-ProfileInfo": DJZZeroENHProfileInfo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DJZ-ZeroENH-V2": "DJZ Zero ENH V2",
    "DJZ-ZeroENH-ProfileInfo": "DJZ Zero ENH Profile Info",
}


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DJZ-ZeroENH-V2 - Deterministic Prompt Enhancement with Profiles")
    print("=" * 70)
    
    # Discover profiles
    print("\n[Profile Discovery]")
    print("-" * 70)
    profiles = discover_profiles()
    print(f"Found {len(profiles)} profile(s): {', '.join(profiles)}")
    
    # Test with default profile (built-in)
    print("\n[Testing Built-in Default Profile]")
    print("-" * 70)
    
    test_cases = [
        ("a cat", 42),
        ("a woman in a forest", 42),
        ("cyberpunk samurai, neon lighting", 12345),
    ]
    
    for input_prompt, seed in test_cases:
        print(f"\nInput: \"{input_prompt}\" (seed={seed})")
        
        # Generate multiple times to verify determinism
        results = [enhance_prompt(input_prompt, seed, DEFAULT_PROFILE, "moderate") for _ in range(5)]
        
        if len(set(results)) == 1:
            print(f"✓ DETERMINISTIC - All 5 runs identical")
            print(f"  Output: \"{results[0][:80]}{'...' if len(results[0]) > 80 else ''}\"")
        else:
            print(f"✗ NON-DETERMINISTIC - Multiple outputs detected!")
    
    # Test with JSON profile if available
    if profiles:
        print(f"\n[Testing JSON Profile: {profiles[0]}]")
        print("-" * 70)
        
        try:
            json_profile = load_profile(profiles[0])
            print(f"Loaded: {json_profile.get('name', 'Unknown')}")
            print(f"Description: {json_profile.get('description', 'N/A')}")
            
            # Show stats
            total = calculate_combinations(json_profile)
            print(f"Total combinations: {total:,}")
            
            # Test enhancement
            test_input = "a warrior"
            test_seed = 42
            
            result = enhance_prompt(test_input, test_seed, json_profile, "moderate")
            print(f"\nInput: \"{test_input}\" (seed={test_seed})")
            print(f"Output: \"{result}\"")
            
            # Verify determinism with JSON profile
            results = [enhance_prompt(test_input, test_seed, json_profile, "moderate") for _ in range(5)]
            if len(set(results)) == 1:
                print("✓ JSON profile determinism verified")
            else:
                print("✗ JSON profile NOT deterministic!")
                
        except Exception as e:
            print(f"Error loading JSON profile: {e}")
    
    # V1 vs V2 comparison
    print("\n[V1 vs V2 Compatibility Check]")
    print("-" * 70)
    print("V2 with built-in default should produce same results as V1")
    print("(This assumes V1 and V2 use identical vocabulary)")
    
    test_input = "a knight"
    test_seed = 42
    
    v2_result = enhance_prompt(test_input, test_seed, DEFAULT_PROFILE, "moderate")
    print(f"V2 Output: \"{v2_result}\"")
    
    print("\n" + "=" * 70)
    print("Testing complete!")
    print("=" * 70)
