# Ingredient & Recipe Search Tool - Implementation Plan

*Grandma's Kitchen Family Recipe Archive*
*Planning Document - January 2026*

---

## Vision

A family recipe discovery system that answers: **"What can I make?"**

From simple ingredient search to meal planning, with family wisdom preserved and surfaced. Grandma, Granny, and MomMom can speak through their recipes - their tips, their favorite markers, their love notes live on.

**Design Ethos:**
- Broad compatibility (works everywhere)
- User-friendly without sacrificing depth
- Progressive disclosure (simple default, powerful when needed)
- Family wisdom preserved and surfaced

---

## Feature Architecture

```
                    ┌─────────────────┐
                    │  Ingredient     │
                    │  Search         │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Staples +     │  │ Substitution    │  │ Collection      │
│ Just Staples  │  │ Engine          │  │ Filter          │
└───────┬───────┘  └────────┬────────┘  └────────┬────────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Recipe Matches  │
                   │ (3-tier nutrition)│
                   └────────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌─────────────────┐  ┌───────────────┐
│ Meal Pairings │  │ Smart Scaling   │  │ Leftovers     │
│ Kitchen Tips  │  │ with Limits     │  │ Suggestions   │
└───────┬───────┘  └────────┬────────┘  └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Shopping List   │
                   │ Generator       │
                   └─────────────────┘
```

---

## Complete Feature List

### 1. Ingredient Search (Core)

| Feature | Description |
|---------|-------------|
| Autocomplete input | Type to search, fuzzy matching |
| Multi-ingredient | Add multiple, AND logic |
| Quantity-aware (optional) | "I have 1 lb beef" → matches recipes needing ≤1 lb |
| Normalization | tomato = tomatoes = cherry tomatoes |
| Synonym support | hamburger = ground beef |

### 2. Staples System

| Feature | Description |
|---------|-------------|
| Configurable staples | User builds their list |
| Preset bundles | "Add basics", "Add baking", "Add Asian" |
| Include toggle | ☑ Include my staples (default on) |
| **Just staples mode** | "What can I make right now with only pantry staples?" |
| Persistence | localStorage + export/import |
| Review prompts | Gentle reminder after 30+ days |
| **Substitution expansion** | Canned tomatoes in staples = "have" fresh for matching |

### 3. Collection Filter

| Feature | Description |
|---------|-------------|
| **Multi-select** | Any combination of collections |
| Four sources | Grandma Baker, MomMom Baker, Granny Hudson, Other Recipes |
| Visual counts | Show recipe count per collection |
| Persistent preference | Remember last selection |

### 4. Nutrition Filter

| Feature | Description |
|---------|-------------|
| Preset modes | Low Carb, Keto, Low Cal, Low Fat, High Protein, Heart Healthy |
| Custom ranges | Numeric min/max for any nutrient |
| **Three-tier results** | ✅ Meets criteria / ⚠️ No data / ❌ Exceeds |
| Clear indicators | Badge showing nutrition status |
| "Only with data" toggle | Hide recipes without nutrition |

### 5. Substitution Engine

| Feature | Description |
|---------|-------------|
| **Bidirectional** | Canned↔Fresh (convenience AND health directions) |
| Health alternatives | Lower carb, lower fat, lower sodium options |
| Convenience swaps | Fresh → canned/frozen when in staples |
| Nutrition impact | "+200mg sodium" or "Saves 40g fat" shown |
| Usage notes | "Works in cooked dishes, less ideal for fresh salsa" |
| Staple integration | Expands what staples can match |

### 6. Smart Suggestions

| Feature | Description |
|---------|-------------|
| **Add suggestions** | "+ tomatoes → Tacos, Chili (12 recipes)" |
| **Subtract suggestions** | "- marshmallows → unlocks 4 recipes" |
| Missing ingredients | "Need: beans" per recipe |
| Almost recipes | "Missing 1-2 ingredients" tier |

### 7. Meal Pairings

| Feature | Description |
|---------|-------------|
| "Complete the meal" | Sides, desserts, drinks suggested for main |
| Cuisine matching | Mexican main → Mexican sides |
| Ingredient efficiency | "You already have avocado → make guac too" |
| One-click meal plan | Add all pairings to shopping list |

### 8. Shopping List

| Feature | Description |
|---------|-------------|
| Auto-generate | From selected recipes |
| Consolidate | Combine same ingredients across recipes |
| Show usage | "tomatoes (Tacos, Chili, Salsa)" |
| **Copy link** | For texting/email (private sharing only) |
| Checkboxes | Mark items as bought |
| Leftover warnings | "You'll have ½ can tomatoes left" |

### 9. Leftover Suggestions

| Feature | Description |
|---------|-------------|
| Predict leftovers | Based on recipe vs package sizes |
| Suggest uses | "Use ½ can tomatoes in: Bruschetta, Salsa" |
| Meal chaining | "Make Taco Soup tomorrow - uses all leftovers" |

### 10. Kitchen Tips & Family Wisdom

| Feature | Description |
|---------|-------------|
| **Family tips aggregated** | Tips from all collections shown together |
| **Attributed** | "From Grandma Baker: ..." |
| Contextual | Shown for relevant recipes/techniques |
| Categories | Candy making, bread, altitude, humidity |
| Technique tips | Brief guidance for tricky steps |
| **Family favorites** | "Best recipe" markers, smiley faces, love notes preserved |

### 11. Smart Scaling

| Feature | Description |
|---------|-------------|
| Yield adjustment | "Scale to 6 servings" slider |
| **Practical limits** | Won't scale below practical measurements |
| Smart rounding | 0.333 cup → ⅓ cup |
| Impossible warnings | "Can't halve an egg" with workaround |
| Preset multipliers | ×¼, ×½, ×1, ×2, ×4 buttons |
| **Minimum batch** | Auto-calculated per recipe |

### 12. Recipe Calculator (Separate Tool)

| Feature | Description |
|---------|-------------|
| Editable inputs | Enter any ingredients + quantities |
| Category selection | "Making: Cookies" for comparison context |
| **Database comparison** | Show avg/min/max per ingredient from all similar recipes |
| Visual range bars | Where user's amount falls vs database |
| **Outlier warnings** | "Sugar very low - cookies may not be sweet" |
| **Average suggestions** | "Typical cookie recipe uses 1 cup sugar" |
| **Pattern matching** | "This looks like Meringue Cookies!" → link to recipe |
| One-click adjust | "Match to Grandma's recipe" button |
| Yield estimation | "~24 cookies at 1.5oz each" |
| Nutrition estimation | Per-serving calculated from ingredients |

### 13. UI/UX Features

| Feature | Description |
|---------|-------------|
| **Progressive disclosure** | Simple default, expand for options, expand again for advanced |
| Keyboard shortcuts | /, ?, Enter, Backspace, Esc, 1-4 for collections |
| **Shortcut tip card** | Dismissable hint that shows once |
| Private link sharing | Copy URL for text/email (no social buttons) |
| Favorites | Heart icon, localStorage |
| Recently viewed | Quick access list |
| Print view | Clean recipe cards |
| Dietary profiles | Persistent restrictions (vegetarian, GF, etc.) |
| Allergy warnings | "Contains nuts" flags |

### 14. Data & Persistence

| Feature | Description |
|---------|-------------|
| Pre-compiled index | `data/ingredient-index.json` |
| Service Worker | Cache + background refresh |
| localStorage | Staples, favorites, preferences, dietary profiles |
| Export/Import | Backup all settings |
| URL state | Shareable search URLs with full state |
| Offline support | Core functionality works offline |

---

## Additional Features (All Included)

| Feature | Description |
|---------|-------------|
| Recipe scaling | Serves 4→8 with smart ingredient adjustment |
| Print-friendly view | Clean recipe cards for printing |
| Favorites system | Heart icon, persisted locally |
| Recently viewed | Quick access to recent recipes |
| Dietary restriction filter | Vegetarian, gluten-free from existing tags |
| Technique library | Dedicated page for cooking techniques with family tips |
| Ingredient glossary | "What is cream of tartar?" with family context |
| Family attribution badges | Visual indicator of recipe source |
| Confidence indicators | Show recipe transcription confidence |
| "Surprise me" | Random recipe from what you can make |
| Holiday collections | Quick filter for Thanksgiving, Christmas, etc. |
| Kid-friendly filter | Recipes marked as kid-approved |
| Complexity scoring | Easy/Medium/Hard based on steps + ingredients |
| Active cook time | Separate from total time (active vs waiting) |
| Recipe notes/journal | "I added extra garlic, was great" - personal notes |

---

## Data Schema Additions

### Recipe Schema (new fields)

```json
{
  "tips": [
    "Season the meat while browning for better flavor",
    "Warm tortillas in a dry skillet, not microwave"
  ],
  "pairs_with": ["guacamole", "spanish-rice", "refried-beans"],
  "cuisine": "Mexican",
  "difficulty": "easy",
  "freezer_friendly": true,
  "equipment": ["skillet"],
  "dietary_flags": ["gluten-free-optional"],
  "family_favorite": true,
  "favorite_of": "Grandpa Ed"
}
```

### New Data Files

```
data/
├── ingredient-index.json      # Pre-compiled search index
├── substitutions.json         # Substitution rules (bidirectional)
├── kitchen-tips.json          # Aggregated family wisdom by technique
├── ingredient-categories.json # Groupings (cheese, beans, etc.)
└── nutrition-presets.json     # Diet mode definitions
```

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Build `scripts/build-ingredient-index.py`
- [ ] Create `data/ingredient-index.json`
- [ ] Basic ingredient search UI
- [ ] Autocomplete component
- [ ] Fuzzy matching / normalization

### Phase 2: Core Search
- [ ] Multi-ingredient AND matching
- [ ] Collection multi-select filter
- [ ] Results display (basic grid)
- [ ] "Perfect match" vs "Almost there" tiers
- [ ] Missing ingredient display per recipe

### Phase 3: Staples System
- [ ] Staples configuration UI
- [ ] Preset bundles (basics, baking, Asian, Mexican, Italian)
- [ ] localStorage persistence
- [ ] "Include staples" toggle
- [ ] "Just my staples" mode
- [ ] Review prompts (30+ days)
- [ ] Export/import settings

### Phase 4: Suggestions Engine
- [ ] Add suggestions algorithm
- [ ] Subtract suggestions algorithm
- [ ] Leftover predictions
- [ ] Leftover recipe suggestions

### Phase 5: Substitutions
- [ ] Create `data/substitutions.json`
- [ ] Bidirectional substitution display
- [ ] Health alternatives (lower carb, lower fat, etc.)
- [ ] Convenience swaps
- [ ] Nutrition impact display
- [ ] Staple expansion via substitutions

### Phase 6: Nutrition & Filtering
- [ ] Three-tier results display
- [ ] Preset diet modes (hybrid approach)
- [ ] Custom nutrition ranges (advanced)
- [ ] Time filter
- [ ] "Only with nutrition data" toggle

### Phase 7: Meal Features
- [ ] Meal pairing suggestions
- [ ] Cuisine-based matching
- [ ] Shopping list generator
- [ ] "Plan full meal" flow
- [ ] Copy link for private sharing

### Phase 8: Kitchen Tips
- [ ] Create `data/kitchen-tips.json`
- [ ] Aggregate tips by technique/category
- [ ] Display attributed tips on recipes
- [ ] Link tips to relevant recipes
- [ ] Surface family favorites and love notes

### Phase 9: Smart Scaling
- [ ] Yield adjustment UI
- [ ] Practical measurement limits
- [ ] Smart rounding display
- [ ] Minimum batch calculation
- [ ] Preset multiplier buttons

### Phase 10: Recipe Calculator
- [ ] Separate tool page/section
- [ ] Editable ingredient inputs
- [ ] Category-based comparison
- [ ] Database avg/min/max lookup
- [ ] Visual range indicators
- [ ] Pattern matching to existing recipes
- [ ] "Adjust to match" feature
- [ ] Yield estimation
- [ ] Nutrition estimation

### Phase 11: Polish & Extras
- [ ] Keyboard shortcuts
- [ ] Tip card (dismissable)
- [ ] Favorites system
- [ ] Recently viewed
- [ ] Print view CSS
- [ ] Service Worker caching
- [ ] Offline support
- [ ] URL state encoding
- [ ] Dietary restriction profiles
- [ ] Allergy warning flags
- [ ] All additional features listed above

---

## UI Design: Progressive Disclosure

### Layer 1: Instant Value (Default)
```
┌─────────────────────────────────────────────────────────────┐
│                    🍳 What Can I Make?                      │
│                                                             │
│         [Type ingredients you have...              🔍]      │
│                                                             │
│              Try: chicken, ground beef, pasta               │
│                                                             │
│                                        [More options ▼]     │
└─────────────────────────────────────────────────────────────┘
```

### Layer 2: Common Options (One Click)
```
┌─────────────────────────────────────────────────────────────┐
│  [chicken ×] [rice ×]  [+ Add more...]                     │
│                                                             │
│  MY STAPLES: ☑ Include (salt, pepper, oil +4)  [Just staples] [Edit] │
│                                                             │
│  ▼ OPTIONS                                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Search in: ☑ Grandma  ☑ MomMom  ☐ Granny  ☐ Other      ││
│  │ Diet: [Any ▼]        Ready in: [Any time ▼]            ││
│  │ 💡 Add: [+soy sauce] [+broccoli]  🔄 Remove: [-rice]   ││
│  │                                         [Advanced ▼]    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Layer 3: Advanced (Second Expansion)
- Multi-select collection checkboxes
- Custom nutrition ranges
- Missing ingredient threshold
- Staples management
- Export/import settings
- Copy shareable link

---

## Family Wisdom Preservation

This is a labor of love. The recipes contain more than ingredients and instructions - they contain **family**.

### What We Preserve:
- **Attributions**: "Elsie W.", "Virginia", "Grandpa Ed", "Russ Gust"
- **Favorite markers**: "(Best recipe)", smiley faces, hearts
- **Personal notes**: "Ed :)" means Grandpa loved this one
- **Cross-family references**: "3-minute fudge recipe is in MomMom's collection"
- **Technique wisdom**: "Stir constantly", "Don't rush the roux"
- **Regional context**: "Florida humidity makes candy tricky"
- **Stories**: Written on company letterhead, newspaper clippings, church bulletins

### How Tips Are Surfaced:
```
┌─────────────────────────────────────────────────────────────┐
│  👵 FAMILY KITCHEN WISDOM                                   │
│                                                             │
│  From Grandma Baker:                                        │
│  "Use a candy thermometer - 235°F is the soft ball stage." │
│                                                             │
│  From Granny Hudson:                                        │
│  "At high altitude, reduce temp by 2°F per 1000ft."        │
│                                                             │
│  From MomMom Baker:                                         │
│  "On humid days, cook it 2 degrees higher."                │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Notes

### Broad Compatibility
- Vanilla JavaScript (no heavy frameworks)
- CSS Grid with flexbox fallbacks
- Progressive enhancement
- Touch-friendly tap targets
- Screen reader accessible (ARIA labels)
- Works offline via Service Worker

### Pre-compiled Index
The ingredient index is built at deploy time, not runtime:
```bash
python scripts/build-ingredient-index.py
# Outputs: data/ingredient-index.json (~50KB)
```

Service Worker caches this and refreshes in background when updated.

### Privacy
- No social sharing buttons (site is password-protected)
- Copy link for private sharing via text/email
- All data stays in localStorage
- No analytics or tracking

---

## Questions Resolved

| Question | Decision |
|----------|----------|
| Fuzzy matching? | Yes - normalize plurals, variants, synonyms |
| Show missing ingredients? | Yes - "Need: X" per recipe |
| Pantry staples? | Configurable with preset bundles + "just staples" mode |
| Remote collections? | Pre-compile index, SW refresh optional |
| Substitutions direction? | Bidirectional - health AND convenience |
| Social sharing? | No - private links only |
| Recipe history tracking? | No - removed from plan |

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness."*
— Proverbs 31:27

*Soli Deo Gloria*
