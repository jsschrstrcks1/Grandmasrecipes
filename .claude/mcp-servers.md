# MCP Servers for Grandma's Recipe Archive

This document describes Model Context Protocol (MCP) servers that can enhance the recipe archive with additional capabilities.

---

## Recommended MCP Servers

### 1. Kitchen MCP Server

**Purpose:** Query ingredients, get nutritional information, and receive recipe recommendations.

**Repository:** [paulabaal12/kitchen-mcp](https://github.com/paulabaal12/kitchen-mcp)

**Capabilities:**
- Query foods and their nutritional information
- Search foods by nutritional criteria (protein, fat, calories)
- Find recipes by ingredients
- Suggest recipes by diet type (vegan, keto, etc.)

**Use Cases for This Project:**
- Look up nutrition data to add to recipes
- Suggest ingredient substitutions
- Verify ingredient names and spellings

**Installation:**
```bash
# Clone and install
git clone https://github.com/paulabaal12/kitchen-mcp
cd kitchen-mcp
npm install
```

**Configuration (add to Claude Desktop config):**
```json
{
  "mcpServers": {
    "kitchen": {
      "command": "node",
      "args": ["/path/to/kitchen-mcp/index.js"]
    }
  }
}
```

---

### 2. OpenNutrition MCP Server

**Purpose:** Access 300,000+ food items with complete nutritional profiles. Runs locally/offline.

**Website:** [scriptbyai.com/opennutrition-mcp](https://www.scriptbyai.com/opennutrition-mcp/)

**Capabilities:**
- Search foods by name
- Get detailed nutritional breakdown
- Works offline after initial setup

**Use Cases for This Project:**
- Add nutrition facts to recipes
- Verify calorie counts in existing calorie-counter entries
- Research ingredient nutritional values

**Data Sources:**
- USDA
- CNF (Canadian Nutrient File)
- FRIDA (Danish Food Database)
- AUSNUT (Australian Food Database)

---

### 3. Spoonacular MCP Server

**Purpose:** Comprehensive food and recipe API access.

**Repository:** [ddsky/spoonacular-mcp](https://github.com/ddsky/spoonacular-mcp)

**Capabilities:**
- Search recipes by ingredients
- Get nutritional information
- Find ingredient substitutions
- Analyze recipes

**Use Cases for This Project:**
- Suggest substitutions for hard-to-find ingredients
- Cross-reference recipe nutritional data
- Verify unusual ingredient combinations

**Note:** Requires Spoonacular API key (free tier available).

---

### 4. MealDB MCP Server

**Purpose:** Access TheMealDB API for recipe and meal information.

**Repository:** Available on LobeHub

**Capabilities:**
- Search recipes by name
- Browse by category
- Get meal details and ingredients

**Use Cases for This Project:**
- Cross-reference classic recipes
- Verify ingredient lists for common dishes
- Research recipe variations

**Note:** No API key required for basic usage.

---

## Integration Patterns

### Pattern 1: Ingredient Substitution Lookup

When a recipe calls for an ingredient that may be hard to find:

```
User: "What can I substitute for buttermilk?"
MCP: Kitchen MCP → search substitutions → "1 cup milk + 1 tbsp lemon juice"
```

### Pattern 2: Nutrition Data Enhancement

To add nutrition information to a recipe:

```
1. Parse ingredients from recipe
2. Query OpenNutrition MCP for each ingredient
3. Calculate totals per serving
4. Add to recipe's "nutrition" field
```

### Pattern 3: Recipe Verification

When transcribing a recipe and something seems unusual:

```
1. Query Spoonacular for similar recipes
2. Compare ingredient ratios
3. Flag if significantly different (may indicate OCR error)
```

---

## MCP Tool Naming Convention

When MCP servers are connected, tools appear with this naming pattern:
```
mcp__<server>__<tool>
```

Examples:
- `mcp__kitchen__search_foods`
- `mcp__kitchen__get_nutrition`
- `mcp__spoonacular__find_substitutes`

---

## Hook Integration

You can create hooks that interact with MCP tools:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__kitchen__.*",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Querying Kitchen MCP...'"
          }
        ]
      }
    ]
  }
}
```

---

## Future Considerations

### Mealie MCP Server
If the family wants to migrate to a self-hosted recipe management system, Mealie MCP could sync recipes between this archive and a Mealie instance.

### OpenFoodFacts MCP
For recipes that reference branded products, OpenFoodFacts could provide product information and nutritional data.

---

## Installation Priority

| Priority | Server | Reason |
|----------|--------|--------|
| 1 | OpenNutrition | Offline, comprehensive, no API key |
| 2 | Kitchen MCP | Good for substitutions |
| 3 | Spoonacular | Most features, but requires API key |
| 4 | MealDB | Nice to have for cross-reference |

---

*Note: MCP servers are optional enhancements. The recipe archive works fully without them.*
