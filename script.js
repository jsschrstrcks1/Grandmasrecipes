/**
 * Grandma's Recipe Archive - Client-side JavaScript
 * Handles recipe loading, search, filtering, and navigation
 */

// =============================================================================
// Security Utilities - XSS Prevention
// =============================================================================

/**
 * Escape HTML special characters to prevent XSS attacks.
 * Always use this when inserting dynamic content into innerHTML.
 * @param {*} text - The text to escape (will be converted to string)
 * @returns {string} - HTML-escaped string safe for innerHTML
 */
function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

/**
 * Sanitize URLs to prevent javascript: and data: XSS attacks.
 * Only allows relative paths, http://, and https:// URLs.
 * @param {string} url - The URL to sanitize
 * @returns {string} - Sanitized URL or '#' if unsafe
 */
function sanitizeUrl(url) {
  if (!url) return '#';
  const trimmed = String(url).trim();
  // Allow relative paths and http(s) URLs only
  if (trimmed.startsWith('/') ||
      trimmed.startsWith('./') ||
      trimmed.startsWith('../') ||
      trimmed.startsWith('http://') ||
      trimmed.startsWith('https://')) {
    return trimmed;
  }
  // Allow simple filenames and paths (no protocol)
  if (/^[a-zA-Z0-9_\-./]+$/.test(trimmed) && !trimmed.includes(':')) {
    return trimmed;
  }
  return '#';
}

/**
 * Escape a value for use in an HTML attribute.
 * @param {*} value - The value to escape
 * @returns {string} - Escaped string safe for attribute values
 */
function escapeAttr(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// =============================================================================
// Application Code
// =============================================================================

// Global state
let recipes = [];           // Lightweight recipe index for list/search
let fullRecipesCache = {};  // Cache for full recipe details (loaded on demand)
let categories = new Set();
let allTags = new Set();
let currentFilter = { search: '', category: '', tag: '', collections: ['grandma-baker', 'mommom-baker', 'granny-hudson', 'all'], ingredients: [], ingredientMatchInfo: null };

// Recipe grid pagination state
let recipeGridPageSize = 50; // Number of recipes per page
let recipeGridCurrentPage = 0; // Current page (0-indexed)
let recipeGridFilteredRecipes = []; // Store filtered recipes for pagination
let showMetric = false; // Toggle for metric conversions
let recipeScale = 1; // Current recipe scale multiplier
let currentRecipeId = null; // Currently displayed recipe (for re-rendering after substitutions)

// Ingredient search state
let ingredientIndex = null;
let selectedIngredients = [];
let ingredientSearchOptions = {
  matchMode: 'any',      // 'any' or 'all'
  missingThreshold: 0    // 0, 1, 2, or 3
};
let autocompleteHighlightIndex = -1;

// Common pantry staples to exclude from ingredient match display
// These are so common they add noise - most households have them
const COMMON_PANTRY_STAPLES = new Set([
  // Seasonings
  'salt', 'pepper', 'black pepper', 'white pepper', 'kosher salt', 'sea salt',
  'garlic powder', 'onion powder', 'paprika', 'cayenne', 'cayenne pepper',
  // Liquids
  'water', 'cold water', 'warm water', 'hot water', 'boiling water', 'ice water',
  'oil', 'vegetable oil', 'cooking oil', 'canola oil', 'olive oil', 'cooking spray',
  // Baking basics
  'flour', 'all-purpose flour', 'all purpose flour', 'ap flour',
  'sugar', 'granulated sugar', 'white sugar',
  'baking soda', 'baking powder',
  'vanilla', 'vanilla extract', 'pure vanilla extract',
  // Dairy staples
  'butter', 'unsalted butter', 'salted butter', 'margarine',
  'eggs', 'egg', 'large eggs', 'large egg',
  'milk', 'whole milk', '2% milk', 'skim milk',
]);

// Staples system state
let userStaples = [];
let includeStaples = true;
let justStaplesMode = false;

// Substitutions system state
let substitutionsData = null;
let enableSubstitutions = true;

// Recipe-level substitution state (for swapping ingredients on recipe page)
let activeSubstitutions = {}; // Map: ingredientIndex -> { original, substitute, nutritionDelta }
let currentRecipeNutrition = null; // Original nutrition to calculate adjustments

// Kitchen tips state
let kitchenTipsData = null;

// Health considerations state
let healthConsiderationsData = null;

// Pagefind search state
let pagefind = null;
let pagefindLoading = null;
let pagefindSearchResults = null; // Array of recipe IDs from Pagefind, or null if not using Pagefind

// Nutrition and time filter state
let nutritionFilter = {
  timeLimit: null,           // Maximum time in minutes
  calories: { min: null, max: null },
  carbs: { min: null, max: null },
  protein: { min: null, max: null },
  fat: { min: null, max: null },
  onlyWithNutrition: false,
  activeDietPreset: null
};

// Remote collection configuration for client-side fetching
// Supports both monolithic (recipes.json) and sharded (recipes-index.json + recipes-{category}.json)
const REMOTE_COLLECTIONS = {
  'mommom-baker': {
    displayName: 'MomMom Baker',
    baseUrl: 'https://jsschrstrcks1.github.io/MomsRecipes/',
    recipesUrl: 'https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json',
    indexUrl: 'https://jsschrstrcks1.github.io/MomsRecipes/data/recipes-index.json',
    sharded: true  // MomsRecipes uses category-based sharding (30 shards)
  },
  'granny-hudson': {
    displayName: 'Granny Hudson',
    baseUrl: 'https://jsschrstrcks1.github.io/Grannysrecipes/',
    recipesUrl: 'https://jsschrstrcks1.github.io/Grannysrecipes/granny/recipes_master.json',
    indexUrl: 'https://jsschrstrcks1.github.io/Grannysrecipes/granny/recipes-index.json',
    dataPath: 'granny/',  // Custom path (not 'data/')
    sharded: true  // Grannysrecipes uses category-based sharding (10 shards)
  },
  'all': {
    displayName: 'Other Recipes',
    baseUrl: 'https://jsschrstrcks1.github.io/Allrecipes/',
    recipesUrl: 'https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json',
    indexUrl: 'https://jsschrstrcks1.github.io/Allrecipes/data/recipes-index.json',
    sharded: true  // Allrecipes uses category-based sharding
  }
};

// Remote shard cache for on-demand loading
let remoteShardCache = {};      // { 'collection:category': recipes[] }
let remoteIndexCache = {};      // { 'collection': indexData }
let loadingShards = {};         // Track in-progress shard loads

// Diet preset definitions (per serving)
const DIET_PRESETS = {
  'low-carb': {
    name: 'Low Carb',
    carbs: { max: 20 },
    description: 'Max 20g carbs per serving'
  },
  'low-cal': {
    name: 'Low Cal',
    calories: { max: 400 },
    description: 'Max 400 calories per serving'
  },
  'high-protein': {
    name: 'High Protein',
    protein: { min: 25 },
    description: 'Min 25g protein per serving'
  },
  'low-fat': {
    name: 'Low Fat',
    fat: { max: 10 },
    description: 'Max 10g fat per serving'
  },
  'low-sodium': {
    name: 'Low Sodium',
    sodium: { max: 500 },
    description: 'Max 500mg sodium per serving'
  }
};

// Ingredient results pagination state
let ingredientResultsPageSize = 10;
let ingredientResultsShown = 0;
let currentIngredientMatches = [];

// Preset staples bundles
const STAPLES_PRESETS = {
  basics: [
    'salt', 'pepper', 'sugar', 'flour', 'butter', 'oil', 'eggs', 'milk',
    'garlic', 'onion', 'water'
  ],
  baking: [
    'baking powder', 'baking soda', 'vanilla extract', 'brown sugar',
    'powdered sugar', 'vegetable oil', 'shortening', 'cocoa powder'
  ],
  asian: [
    'soy sauce', 'sesame oil', 'rice vinegar', 'ginger', 'green onions',
    'garlic', 'rice', 'cornstarch'
  ],
  mexican: [
    'cumin', 'chili powder', 'cilantro', 'lime', 'jalapeño', 'tortillas',
    'black beans', 'salsa', 'cheese'
  ],
  italian: [
    'olive oil', 'garlic', 'basil', 'oregano', 'parmesan cheese',
    'tomato sauce', 'pasta', 'red pepper flakes'
  ]
};

// Meal pairing rules (category-based)
const MEAL_PAIRINGS = {
  mains: ['sides', 'salads', 'breads', 'beverages'],
  sides: ['mains', 'salads'],
  salads: ['mains', 'breads', 'soups'],
  soups: ['breads', 'salads', 'mains'],
  appetizers: ['mains', 'beverages'],
  breakfast: ['beverages', 'breads'],
  breads: ['soups', 'mains', 'salads'],
  desserts: ['beverages'],
  beverages: ['mains', 'desserts', 'breakfast']
};

// Shopping list state
let shoppingList = [];
let selectedMealRecipes = [];

// DOM Ready
document.addEventListener('DOMContentLoaded', init);

async function init() {
  // Load recipe index and ingredient index in parallel
  await Promise.all([
    loadRecipes(),
    loadIngredientIndex()
  ]);
  // Substitutions and kitchen tips are still lazy loaded on first use
  setupEventListeners();
  setupIngredientSearch();
  setupStaplesSystem();
  setupNutritionFilters();

  // Initialize Milk Substitution Tool (for cheesemaking recipes)
  if (typeof MilkSubstitution !== 'undefined') {
    try {
      await MilkSubstitution.loadData();
      setupMilkSubstitutionListeners();
      console.log('Milk substitution tool initialized');
    } catch (e) {
      console.warn('Milk substitution tool not available:', e.message);
    }
  }

  // Initialize Protein Substitution Tool
  if (typeof ProteinSubstitution !== 'undefined') {
    try {
      await ProteinSubstitution.loadData();
      console.log('Protein substitution tool initialized');
    } catch (e) {
      console.warn('Protein substitution tool not available:', e.message);
    }
  }

  handleRouting();
}

/**
 * Set up listeners for milk substitution changes
 */
function setupMilkSubstitutionListeners() {
  document.addEventListener('milkSubstitutionChanged', (e) => {
    const { adjustedIngredients } = e.detail;
    if (adjustedIngredients && adjustedIngredients.length > 0) {
      updateIngredientsForMilkSubstitution(adjustedIngredients);
    }
  });
}

/**
 * Update the ingredients list when milk substitution changes
 */
function updateIngredientsForMilkSubstitution(adjustedIngredients) {
  const list = document.querySelector('.ingredients-list');
  if (!list) return;

  list.innerHTML = adjustedIngredients.map(ing => {
    const adjusted = ing._adjusted ? ' ingredient-adjusted' : '';
    const omitted = ing._omitted ? ' ingredient-omitted' : '';
    const note = ing._adjustmentNote ? ` <span class="adjustment-note">(${escapeHtml(ing._adjustmentNote)})</span>` : '';

    // Format the ingredient display
    let display = '';
    if (ing.quantity) display += escapeHtml(ing.quantity) + ' ';
    if (ing.unit) display += escapeHtml(ing.unit) + ' ';
    display += escapeHtml(ing.item);

    return `<li class="${adjusted}${omitted}">${display}${note}</li>`;
  }).join('');
}

/**
 * Load lightweight recipe index for list/search views
 */
async function loadRecipes() {
  try {
    const response = await fetch('data/recipes_index.json');
    const data = await response.json();
    recipes = data.recipes || [];

    // Extract categories and tags
    recipes.forEach(recipe => {
      if (recipe.category) categories.add(recipe.category);
      if (recipe.tags) recipe.tags.forEach(tag => allTags.add(tag));
    });

    console.log(`Loaded ${recipes.length} recipes (index)`);
    updateCollectionCounts();
  } catch (error) {
    console.error('Failed to load recipes:', error);
    showError('Unable to load recipes. Please refresh the page.');
  }
}

/**
 * Load full recipe details on demand using two-level sharding
 * - Small collections: Single collection shard (data/recipes-{collection}.json)
 * - Large collections: Category sub-shards (data/recipes-{collection}-{category}.json)
 */
let localShardCache = {};      // { 'shardKey': recipes[] } - shardKey is 'collection' or 'collection:category'
let loadingLocalShards = {};   // Track in-progress local shard loads

// Collections that use category sub-shards (large collections >= 1000 recipes)
const CATEGORY_SHARDED_COLLECTIONS = ['mommom-baker', 'all'];

async function loadFullRecipe(recipeId) {
  // Check recipe cache first
  if (fullRecipesCache[recipeId]) {
    return fullRecipesCache[recipeId];
  }

  // Find recipe in index to get its collection and category
  const indexEntry = recipes.find(r => r.id === recipeId);
  if (!indexEntry) {
    console.warn(`Recipe ${recipeId} not found in index`);
    return null;
  }

  const collection = indexEntry.collection;
  const category = indexEntry.category;

  // Check if this collection uses category sub-shards
  const usesCategoryShards = CATEGORY_SHARDED_COLLECTIONS.includes(collection);

  // Determine shard key and URL
  let shardKey, shardUrl;
  if (usesCategoryShards && category) {
    // Large collection - use category sub-shard
    shardKey = `${collection}:${category}`;
    shardUrl = `data/recipes-${collection}-${category}.json`;
  } else {
    // Small collection - use single collection shard
    shardKey = collection;
    shardUrl = `data/recipes-${collection}.json`;
  }

  // Load shard if not cached
  if (!localShardCache[shardKey]) {
    // Load the shard if not already loading
    if (!loadingLocalShards[shardKey]) {
      loadingLocalShards[shardKey] = (async () => {
        try {
          console.log(`Loading local shard: ${shardUrl}`);
          const response = await fetch(shardUrl);
          if (!response.ok) {
            console.warn(`Failed to load shard ${shardKey}: ${response.status}`);
            return false;
          }
          const data = await response.json();
          const shardRecipes = data.recipes || [];

          // Cache the shard
          localShardCache[shardKey] = shardRecipes;

          // Also cache individual recipes for quick lookup
          shardRecipes.forEach(r => {
            fullRecipesCache[r.id] = r;
          });

          console.log(`Loaded ${shardRecipes.length} recipes from ${shardKey} shard`);
          return true;
        } catch (error) {
          console.error(`Error loading shard ${shardKey}:`, error);
          return false;
        }
      })();
    }

    await loadingLocalShards[shardKey];
  }

  // Return from cache
  if (fullRecipesCache[recipeId]) {
    return fullRecipesCache[recipeId];
  }

  console.warn(`Recipe ${recipeId} not found in ${shardKey} shard`);
  return null;
}

/**
 * Load a recipe from a remote collection (supports sharded repos)
 * @param {string} recipeId - The recipe ID to load
 * @param {Object} indexEntry - The recipe's entry in the local index (has category info)
 * @param {Object} collectionConfig - The remote collection configuration
 * @returns {Object|null} - The full recipe object or null if not found
 */
async function loadRemoteRecipe(recipeId, indexEntry, collectionConfig) {
  const collection = indexEntry.collection;
  const category = indexEntry.category;
  const dataPath = collectionConfig.dataPath || 'data';  // Custom path support (e.g., 'granny' for Grannysrecipes)

  // For sharded repos, load the specific category shard
  if (collectionConfig.sharded && category) {
    const shardKey = `${collection}:${category}`;

    // Check shard cache first
    if (remoteShardCache[shardKey]) {
      const recipe = remoteShardCache[shardKey].find(r => r.id === recipeId);
      if (recipe) return recipe;
    }

    // Load the category shard
    try {
      const shardUrl = `${collectionConfig.baseUrl}${dataPath}/recipes-${category}.json`;
      console.log(`Loading remote shard: ${shardUrl}`);

      const response = await fetch(shardUrl);
      if (!response.ok) {
        console.warn(`Failed to load shard ${category}: ${response.status}`);
        // Fall back to monolithic
      } else {
        const data = await response.json();
        const shardRecipes = data.recipes || [];

        // Cache the shard
        remoteShardCache[shardKey] = shardRecipes;

        // Cache all recipes from the shard
        shardRecipes.forEach(r => {
          fullRecipesCache[r.id] = r;
        });

        console.log(`Loaded remote shard ${category} (${shardRecipes.length} recipes)`);

        // Return the requested recipe
        const recipe = shardRecipes.find(r => r.id === recipeId);
        if (recipe) return recipe;
      }
    } catch (error) {
      console.warn(`Error loading shard ${category}:`, error);
      // Fall back to monolithic
    }
  }

  // Fall back to monolithic load for non-sharded or if shard load failed
  if (collectionConfig.recipesUrl) {
    try {
      console.log(`Loading remote recipes (monolithic): ${collectionConfig.recipesUrl}`);
      const response = await fetch(collectionConfig.recipesUrl);
      if (!response.ok) {
        console.error(`Failed to load remote recipes: ${response.status}`);
        return null;
      }

      const data = await response.json();
      const remoteRecipes = data.recipes || data || [];

      // Cache all recipes from this collection
      remoteRecipes.forEach(r => {
        fullRecipesCache[r.id] = r;
      });

      console.log(`Loaded remote collection (${remoteRecipes.length} recipes)`);
      return remoteRecipes.find(r => r.id === recipeId);
    } catch (error) {
      console.error('Error loading remote recipes:', error);
      return null;
    }
  }

  return null;
}

/**
 * Load the index for a sharded remote collection
 * @param {string} collection - The collection ID
 * @param {Object} collectionConfig - The remote collection configuration
 * @returns {Object|null} - The index data or null if not found/not sharded
 */
async function loadRemoteIndex(collection, collectionConfig) {
  // Check cache first
  if (remoteIndexCache[collection]) {
    return remoteIndexCache[collection];
  }

  if (!collectionConfig.sharded || !collectionConfig.indexUrl) {
    return null;
  }

  try {
    const response = await fetch(collectionConfig.indexUrl);
    if (!response.ok) {
      console.warn(`Failed to load remote index: ${response.status}`);
      return null;
    }

    const indexData = await response.json();
    remoteIndexCache[collection] = indexData;
    console.log(`Loaded remote index for ${collection} (${indexData.shards?.length || 0} shards)`);
    return indexData;
  } catch (error) {
    console.error(`Error loading remote index for ${collection}:`, error);
    return null;
  }
}

/**
 * Preload all shards from a remote sharded collection
 * Useful for offline access or bulk operations
 * @param {string} collection - The collection ID
 * @returns {number} - Number of recipes loaded
 */
async function preloadRemoteCollection(collection) {
  const collectionConfig = REMOTE_COLLECTIONS[collection];
  if (!collectionConfig) {
    console.warn(`Unknown collection: ${collection}`);
    return 0;
  }

  if (!collectionConfig.sharded) {
    // Load monolithic
    try {
      const response = await fetch(collectionConfig.recipesUrl);
      const data = await response.json();
      const recipes = data.recipes || data || [];
      recipes.forEach(r => { fullRecipesCache[r.id] = r; });
      console.log(`Preloaded ${recipes.length} recipes from ${collection} (monolithic)`);
      return recipes.length;
    } catch (error) {
      console.error(`Failed to preload ${collection}:`, error);
      return 0;
    }
  }

  // Load sharded - first get the index
  const indexData = await loadRemoteIndex(collection, collectionConfig);
  if (!indexData || !indexData.shards) {
    return 0;
  }

  const dataPath = collectionConfig.dataPath || 'data';  // Custom path support
  let totalLoaded = 0;
  const shardPromises = indexData.shards.map(async (shard) => {
    const category = shard.category;
    const shardKey = `${collection}:${category}`;

    // Skip if already loaded
    if (remoteShardCache[shardKey]) {
      return remoteShardCache[shardKey].length;
    }

    try {
      const shardFile = shard.file || `recipes-${category}.json`;
      const shardUrl = `${collectionConfig.baseUrl}${dataPath}/${shardFile}`;
      const response = await fetch(shardUrl);

      if (!response.ok) {
        console.warn(`Failed to load shard ${shardFile}: ${response.status}`);
        return 0;
      }

      const data = await response.json();
      const shardRecipes = data.recipes || [];
      remoteShardCache[shardKey] = shardRecipes;
      shardRecipes.forEach(r => { fullRecipesCache[r.id] = r; });
      return shardRecipes.length;
    } catch (error) {
      console.warn(`Error loading shard ${category}:`, error);
      return 0;
    }
  });

  const results = await Promise.all(shardPromises);
  totalLoaded = results.reduce((sum, count) => sum + count, 0);
  console.log(`Preloaded ${totalLoaded} recipes from ${collection} (${indexData.shards.length} shards)`);
  return totalLoaded;
}

// Make preload function available globally for manual use
window.preloadRemoteCollection = preloadRemoteCollection;

/**
 * Load ingredient index from JSON file (lazy loaded on first use)
 */
let ingredientIndexLoading = null;
async function loadIngredientIndex() {
  // Return existing data if already loaded
  if (ingredientIndex) return ingredientIndex;

  // Return existing promise if already loading
  if (ingredientIndexLoading) return ingredientIndexLoading;

  // Start loading
  ingredientIndexLoading = (async () => {
    try {
      const response = await fetch('data/ingredient-index.json');
      ingredientIndex = await response.json();
      console.log(`Loaded ingredient index: ${ingredientIndex.meta.total_ingredients} ingredients from ${Object.keys(ingredientIndex.meta.collections || {}).length} collections`);

      // Display last updated badge
      updateLastUpdatedBadge();

      return ingredientIndex;
    } catch (error) {
      console.error('Failed to load ingredient index:', error);
      ingredientIndexLoading = null; // Allow retry
      return null;
    }
  })();

  return ingredientIndexLoading;
}

/**
 * Format a timestamp as relative time
 */
function formatTimeAgo(isoString) {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffDays > 30) {
      return date.toLocaleDateString();
    } else if (diffDays > 0) {
      return `${diffDays}d ago`;
    } else if (diffHours > 0) {
      return `${diffHours}h ago`;
    } else {
      return 'just now';
    }
  } catch (e) {
    return 'unknown';
  }
}

/**
 * Update the last-updated badge with build timestamp and collection status
 */
function updateLastUpdatedBadge() {
  const badge = document.getElementById('index-last-updated');
  if (!badge || !ingredientIndex || !ingredientIndex.meta.built_at) return;

  try {
    const builtAt = new Date(ingredientIndex.meta.built_at);
    const timeAgo = formatTimeAgo(ingredientIndex.meta.built_at);

    const collectionNames = {
      'grandma-baker': 'Grandma',
      'mommom-baker': 'MomMom',
      'granny-hudson': 'Granny',
      'all': 'Other'
    };

    // Count recipes from local index (not ingredient index metadata)
    const localCounts = {};
    for (const recipe of recipes) {
      const coll = recipe.collection || 'unknown';
      localCounts[coll] = (localCounts[coll] || 0) + 1;
    }

    // Build collection status string from local counts
    const collectionParts = [];
    let totalRecipes = recipes.length;
    for (const [id, count] of Object.entries(localCounts)) {
      const name = collectionNames[id] || id;
      collectionParts.push(`${name}: ${count}`);
    }

    badge.innerHTML = `
      <span class="index-summary">Index updated ${timeAgo} (${totalRecipes} recipes)</span>
      <span class="collection-breakdown">${collectionParts.join(' | ')}</span>
    `;
    badge.title = `Built: ${builtAt.toLocaleString()}\nRecipes loaded: ${totalRecipes}`;
  } catch (e) {
    console.error('Error updating last-updated badge:', e);
  }
}

/**
 * Load substitutions data from JSON file (lazy loaded on first use)
 */
let substitutionsLoading = null;
async function loadSubstitutions() {
  // Return existing data if already loaded
  if (substitutionsData) return substitutionsData;

  // Return existing promise if already loading
  if (substitutionsLoading) return substitutionsLoading;

  // Start loading
  substitutionsLoading = (async () => {
    try {
      const response = await fetch('data/substitutions.json');
      substitutionsData = await response.json();
      console.log(`Loaded ${substitutionsData.substitutions.length} substitution rules`);
      return substitutionsData;
    } catch (error) {
      console.error('Failed to load substitutions:', error);
      substitutionsLoading = null; // Allow retry
      return null;
    }
  })();

  return substitutionsLoading;
}

/**
 * Load kitchen tips data from JSON file (lazy loaded on first use)
 */
let kitchenTipsLoading = null;
async function loadKitchenTips() {
  // Return if already loaded
  if (kitchenTipsData) return kitchenTipsData;

  // Return existing promise if already loading
  if (kitchenTipsLoading) return kitchenTipsLoading;

  // Start loading
  kitchenTipsLoading = (async () => {
    try {
      const response = await fetch('data/kitchen-tips.json');
      kitchenTipsData = await response.json();
      const totalTips = kitchenTipsData.categories.reduce((sum, cat) => sum + cat.tips.length, 0);
      console.log(`Loaded ${totalTips} kitchen tips in ${kitchenTipsData.categories.length} categories`);
      return kitchenTipsData;
    } catch (error) {
      console.error('Failed to load kitchen tips:', error);
      // Non-fatal - tips just won't show
      return null;
    }
  })();

  return kitchenTipsLoading;
}

// Health considerations loading state
let healthConsiderationsLoading = null;

/**
 * Load health considerations data (lazy loaded when viewing a recipe)
 */
async function loadHealthConsiderations() {
  // Return if already loaded
  if (healthConsiderationsData) return healthConsiderationsData;

  // Return existing promise if already loading
  if (healthConsiderationsLoading) return healthConsiderationsLoading;

  // Start loading
  healthConsiderationsLoading = (async () => {
    try {
      const response = await fetch('data/health-considerations.json');
      healthConsiderationsData = await response.json();
      console.log(`Loaded health considerations: ${healthConsiderationsData.meta.total_flagged_ingredients} ingredients, ${healthConsiderationsData.meta.concern_categories} categories`);
      return healthConsiderationsData;
    } catch (error) {
      console.error('Failed to load health considerations:', error);
      // Non-fatal - health panel just won't show
      return null;
    }
  })();

  return healthConsiderationsLoading;
}

/**
 * Analyze recipe ingredients for health concerns
 * @param {Object} recipe - The recipe to analyze
 * @returns {Array} - Array of warnings sorted by severity
 */
async function analyzeRecipeHealth(recipe) {
  const db = await loadHealthConsiderations();
  if (!db || !recipe.ingredients) return [];

  const warnings = new Map(); // concernId -> { concern, ingredients: [] }

  for (const ingredient of recipe.ingredients) {
    // Get the ingredient name (handle both string and object formats)
    let ingText = '';
    if (typeof ingredient === 'string') {
      ingText = ingredient.toLowerCase();
    } else if (ingredient.item) {
      ingText = ingredient.item.toLowerCase();
    } else {
      continue;
    }

    // Check if this ingredient (or parts of it) has any health concerns
    // Try exact match first, then partial match
    let concerns = db.ingredients[ingText];

    if (!concerns) {
      // Try partial match - check if any flagged ingredient is contained in this one
      for (const [flaggedIng, flaggedConcerns] of Object.entries(db.ingredients)) {
        if (ingText.includes(flaggedIng) || flaggedIng.includes(ingText)) {
          concerns = flaggedConcerns;
          break;
        }
      }
    }

    if (concerns) {
      for (const concernId of concerns) {
        if (!warnings.has(concernId)) {
          warnings.set(concernId, {
            concern: db.concerns[concernId],
            concernId: concernId,
            ingredients: []
          });
        }
        // Add the original ingredient name (not lowercased)
        const displayName = typeof ingredient === 'string' ? ingredient : ingredient.item;
        if (!warnings.get(concernId).ingredients.includes(displayName)) {
          warnings.get(concernId).ingredients.push(displayName);
        }
      }
    }
  }

  // Sort by severity: critical > high > allergen > moderate > info
  const severityOrder = { critical: 0, high: 1, allergen: 2, moderate: 3, info: 4 };
  return Array.from(warnings.values())
    .sort((a, b) => severityOrder[a.concern.severity] - severityOrder[b.concern.severity]);
}

/**
 * Render health considerations panel HTML
 * @param {Array} warnings - Array of health warnings
 * @returns {string} - HTML string for the health panel
 */
function renderHealthPanel(warnings) {
  if (!warnings || warnings.length === 0) {
    return '';
  }

  const warningsHtml = warnings.map(warning => {
    const severityClass = warning.concern.severity;
    const title = warning.concern.title;
    const description = escapeHtml(warning.concern.description);
    const ingredients = warning.ingredients.map(i => escapeHtml(i)).join(', ');
    const medications = warning.concern.medications && warning.concern.medications.length > 0
      ? `<p class="health-medications"><em>Medications affected:</em> ${warning.concern.medications.map(m => escapeHtml(m)).join(', ')}</p>`
      : '';

    return `
      <div class="health-warning ${severityClass}">
        <h4>${severityClass === 'critical' ? '⚠️ ' : ''}${escapeHtml(title)}</h4>
        <p><strong>Ingredients:</strong> ${ingredients}</p>
        <p>${description}</p>
        ${medications}
      </div>
    `;
  }).join('');

  return `
    <details class="health-considerations">
      <summary class="health-header">
        <span class="health-icon">⚕️</span>
        <span class="health-title">Health Considerations</span>
        <span class="health-count">(${warnings.length} items)</span>
        <span class="chevron">▶</span>
      </summary>
      <div class="health-content">
        ${warningsHtml}
        <p class="health-disclaimer">
          <strong>Medical Disclaimer:</strong> This information is for general
          awareness only and is NOT medical advice. Always consult your doctor,
          pharmacist, or registered dietitian before making dietary changes,
          especially if you have medical conditions or take medications.
          Food-drug interactions can be serious or life-threatening.
        </p>
      </div>
    </details>
  `;
}

/**
 * Load Pagefind search library (lazy loaded on first search)
 */
async function loadPagefind() {
  // Return if already loaded
  if (pagefind) return pagefind;

  // Return existing promise if already loading
  if (pagefindLoading) return pagefindLoading;

  // Start loading
  pagefindLoading = (async () => {
    try {
      pagefind = await import('/_pagefind/pagefind.js');
      await pagefind.init();
      console.log('Pagefind search loaded');
      return pagefind;
    } catch (error) {
      // Try relative path for local development
      try {
        pagefind = await import('./_pagefind/pagefind.js');
        await pagefind.init();
        console.log('Pagefind search loaded (relative path)');
        return pagefind;
      } catch (e) {
        console.warn('Pagefind not available, using basic search:', e.message);
        return null;
      }
    }
  })();

  return pagefindLoading;
}

/**
 * Search recipes using Pagefind
 * @param {string} query - Search query
 * @returns {Object|null} - Object with localIds (for filtering) and remoteResults (for display), or null if Pagefind unavailable
 */
async function searchWithPagefind(query) {
  if (!query || query.length < 2) {
    return null; // Too short, use basic filter
  }

  const pf = await loadPagefind();
  if (!pf) {
    return null; // Pagefind not available, fall back to basic search
  }

  try {
    const search = await pf.search(query);
    if (!search || !search.results) {
      return { localIds: [], remoteResults: [] };
    }

    const localIds = [];
    const remoteResults = [];

    for (const result of search.results.slice(0, 100)) { // Limit to top 100
      const data = await result.data();
      if (data.url) {
        // Check if it's a remote URL (starts with http)
        if (data.url.startsWith('http')) {
          remoteResults.push({
            title: data.meta?.title || 'Unknown Recipe',
            url: data.url,
            collection: data.meta?.collection || 'External',
            category: data.meta?.category || '',
            description: data.meta?.description || ''
          });
        } else {
          // Local recipe - extract ID from "recipe.html#recipe-id"
          const id = data.url.split('#')[1];
          if (id) localIds.push(id);
        }
      }
    }

    return { localIds, remoteResults };
  } catch (error) {
    console.error('Pagefind search error:', error);
    return null;
  }
}

/**
 * Get relevant kitchen tips for a recipe based on category
 * @param {Object} recipe - The recipe object
 * @returns {Array} - Array of relevant tips
 */
function getKitchenTipsForRecipe(recipe) {
  if (!kitchenTipsData || !recipe) return [];

  const tips = [];
  const recipeCategory = (recipe.category || '').toLowerCase();
  const recipeTitle = (recipe.title || '').toLowerCase();
  const recipeId = recipe.id || '';

  // Map recipe categories to tip categories
  const categoryMapping = {
    'desserts': ['candy-making', 'baking-cakes', 'baking-cookies', 'baking-pies'],
    'breads': ['baking-bread'],
    'mains': ['meat-cooking', 'sauces', 'frying'],
    'sides': ['vegetables', 'sauces'],
    'breakfast': ['eggs', 'baking-bread'],
    'soups': ['soups-stews'],
    'appetizers': ['frying', 'sauces'],
    'salads': ['vegetables'],
    'beverages': []
  };

  // Get tip categories for this recipe category
  const relevantCategories = categoryMapping[recipeCategory] || ['general'];

  // Always include general tips
  if (!relevantCategories.includes('general')) {
    relevantCategories.push('general');
  }

  // Collect tips from relevant categories
  for (const cat of kitchenTipsData.categories) {
    if (relevantCategories.includes(cat.id)) {
      for (const tip of cat.tips) {
        // Check if tip specifically relates to this recipe
        const relatedToRecipe = tip.relatedRecipes?.some(r =>
          recipeId.includes(r) || recipeTitle.includes(r)
        );

        tips.push({
          ...tip,
          category: cat.name,
          categoryIcon: cat.icon,
          isDirectlyRelated: relatedToRecipe
        });
      }
    }
  }

  // Sort: directly related first, then by category
  tips.sort((a, b) => {
    if (a.isDirectlyRelated && !b.isDirectlyRelated) return -1;
    if (!a.isDirectlyRelated && b.isDirectlyRelated) return 1;
    return 0;
  });

  // Return up to 5 tips
  return tips.slice(0, 5);
}

/**
 * Get all kitchen tips organized by category
 * @returns {Array} - Array of tip categories with their tips
 */
function getAllKitchenTips() {
  if (!kitchenTipsData) return [];
  return kitchenTipsData.categories;
}

/**
 * Render kitchen tips HTML for a recipe
 * @param {Object} recipe - The recipe object
 * @returns {string} - HTML string
 */
function renderKitchenTipsForRecipe(recipe) {
  const tips = getKitchenTipsForRecipe(recipe);
  if (tips.length === 0) return '';

  const tipsHtml = tips.map(tip => `
    <div class="kitchen-tip ${tip.isDirectlyRelated ? 'directly-related' : ''}">
      <span class="tip-icon">${escapeHtml(tip.categoryIcon)}</span>
      <div class="tip-content">
        <p class="tip-text">"${escapeHtml(tip.text)}"</p>
        <span class="tip-attribution">— ${escapeHtml(tip.attribution)}</span>
      </div>
    </div>
  `).join('');

  return `
    <div class="kitchen-tips-section">
      <h3 class="kitchen-tips-header">👵 Family Kitchen Wisdom</h3>
      <div class="kitchen-tips-list">
        ${tipsHtml}
      </div>
    </div>
  `;
}

// =============================================================================
// Recipe Scaling Functions
// =============================================================================

/**
 * Common fraction mappings for smart rounding
 */
const FRACTION_MAP = {
  '0.125': '⅛',
  '0.25': '¼',
  '0.333': '⅓',
  '0.375': '⅜',
  '0.5': '½',
  '0.625': '⅝',
  '0.667': '⅔',
  '0.75': '¾',
  '0.875': '⅞'
};

/**
 * Minimum practical measurements for common units
 * Below these, display a warning
 */
const MIN_PRACTICAL_MEASUREMENTS = {
  'teaspoon': 0.125,  // 1/8 tsp
  'tsp': 0.125,
  'tablespoon': 0.25, // 1/4 tbsp
  'tbsp': 0.25,
  'cup': 0.125,       // 1/8 cup
  'cups': 0.125,
  'egg': 0.5,         // Half egg is practical limit
  'eggs': 0.5,
  'ounce': 0.25,
  'oz': 0.25,
  'pound': 0.125,
  'lb': 0.125
};

/**
 * Scale a quantity string by a multiplier
 * @param {string|number} quantity - The quantity to scale (e.g., "1 1/2", "2", "1/4")
 * @param {number} scale - The scale multiplier
 * @returns {Object} - { value: number, display: string, warning: string|null }
 */
function scaleQuantity(quantity, scale) {
  if (!quantity || scale === 1) {
    return { value: parseQuantity(quantity), display: String(quantity || ''), warning: null };
  }

  const numericValue = parseQuantity(quantity);
  if (numericValue === null || isNaN(numericValue)) {
    return { value: null, display: String(quantity || ''), warning: null };
  }

  const scaled = numericValue * scale;
  const display = formatQuantity(scaled);

  return { value: scaled, display, warning: null };
}

/**
 * Parse a quantity string to a number
 * @param {string|number} quantity - The quantity string (e.g., "1 1/2", "1/4", "2")
 * @returns {number|null} - The numeric value or null if unparseable
 */
function parseQuantity(quantity) {
  if (typeof quantity === 'number') return quantity;
  if (!quantity) return null;

  const str = String(quantity).trim();

  // Handle Unicode fractions
  const unicodeFractions = {
    '⅛': 0.125, '¼': 0.25, '⅓': 0.333, '⅜': 0.375,
    '½': 0.5, '⅝': 0.625, '⅔': 0.667, '¾': 0.75, '⅞': 0.875
  };

  // Replace Unicode fractions
  let processed = str;
  for (const [frac, val] of Object.entries(unicodeFractions)) {
    processed = processed.replace(frac, ` ${val}`);
  }

  // Handle mixed numbers like "1 1/2"
  const mixedMatch = processed.match(/^(\d+)\s+(\d+)\/(\d+)$/);
  if (mixedMatch) {
    return parseInt(mixedMatch[1]) + parseInt(mixedMatch[2]) / parseInt(mixedMatch[3]);
  }

  // Handle fractions like "1/2"
  const fractionMatch = processed.match(/^(\d+)\/(\d+)$/);
  if (fractionMatch) {
    return parseInt(fractionMatch[1]) / parseInt(fractionMatch[2]);
  }

  // Handle decimals and whole numbers
  const numMatch = processed.match(/^[\d.]+/);
  if (numMatch) {
    const baseNum = parseFloat(numMatch[0]);
    // Check if there's a fraction after the whole number
    const remainder = processed.slice(numMatch[0].length).trim();
    if (remainder) {
      const remainderVal = parseFloat(remainder);
      if (!isNaN(remainderVal)) {
        return baseNum + remainderVal;
      }
    }
    return baseNum;
  }

  return null;
}

/**
 * Format a number as a nice fraction or decimal
 * @param {number} value - The numeric value
 * @returns {string} - Formatted string (e.g., "1½", "¼", "2.5")
 */
function formatQuantity(value) {
  if (value === null || isNaN(value)) return '';

  // Handle whole numbers
  if (Number.isInteger(value)) {
    return String(value);
  }

  const wholePart = Math.floor(value);
  const fractionalPart = value - wholePart;

  // Round to nearest common fraction
  const roundedFrac = roundToFraction(fractionalPart);

  if (roundedFrac === 0) {
    return String(wholePart || '');
  }
  if (roundedFrac === 1) {
    return String(wholePart + 1);
  }

  // Find the closest fraction symbol
  const fracStr = roundedFrac.toFixed(3);
  const symbol = FRACTION_MAP[fracStr] || roundedFrac.toFixed(2);

  if (wholePart === 0) {
    return symbol;
  }
  return `${wholePart}${symbol}`;
}

/**
 * Round a decimal to the nearest common fraction
 * @param {number} decimal - A decimal between 0 and 1
 * @returns {number} - The nearest common fraction value
 */
function roundToFraction(decimal) {
  const fractions = [0, 0.125, 0.25, 0.333, 0.375, 0.5, 0.625, 0.667, 0.75, 0.875, 1];
  let closest = 0;
  let minDiff = Math.abs(decimal);

  for (const frac of fractions) {
    const diff = Math.abs(decimal - frac);
    if (diff < minDiff) {
      minDiff = diff;
      closest = frac;
    }
  }

  return closest;
}

/**
 * Check if a scaled measurement is below practical minimum
 * @param {number} value - The scaled value
 * @param {string} unit - The unit of measurement
 * @returns {string|null} - Warning message or null
 */
function checkPracticalMinimum(value, unit) {
  if (!unit || !value) return null;

  const normalizedUnit = unit.toLowerCase().replace(/[s.]$/g, '');
  const minimum = MIN_PRACTICAL_MEASUREMENTS[normalizedUnit];

  if (minimum && value < minimum) {
    return `Very small amount - difficult to measure accurately`;
  }

  // Special warning for eggs
  if ((normalizedUnit === 'egg' || unit.toLowerCase().includes('egg')) && value < 1 && value > 0) {
    return `Partial egg - consider whisking a whole egg and using portion`;
  }

  return null;
}

/**
 * Render scaling controls for a recipe
 * @param {Object} recipe - The recipe object
 * @returns {string} - HTML string
 */
function renderScalingControls(recipe) {
  const servings = parseServingsYield(recipe.servings_yield);

  return `
    <div class="scaling-controls">
      <span class="scaling-label">Scale recipe:</span>
      <div class="scaling-buttons">
        <button type="button" class="scale-btn ${recipeScale === 0.25 ? 'active' : ''}" data-scale="0.25">¼×</button>
        <button type="button" class="scale-btn ${recipeScale === 0.5 ? 'active' : ''}" data-scale="0.5">½×</button>
        <button type="button" class="scale-btn ${recipeScale === 1 ? 'active' : ''}" data-scale="1">1×</button>
        <button type="button" class="scale-btn ${recipeScale === 2 ? 'active' : ''}" data-scale="2">2×</button>
        <button type="button" class="scale-btn ${recipeScale === 4 ? 'active' : ''}" data-scale="4">4×</button>
      </div>
      ${servings ? `<span class="scaling-servings">${getScaledServings(servings, recipeScale)}</span>` : ''}
    </div>
  `;
}

/**
 * Parse servings/yield string to extract number
 * @param {string} servingsYield - The servings string (e.g., "Makes 24 cookies", "Serves 6")
 * @returns {Object|null} - { count: number, unit: string } or null
 */
function parseServingsYield(servingsYield) {
  if (!servingsYield) return null;

  const match = servingsYield.match(/(\d+)\s*(servings?|cookies?|pieces?|slices?|cups?|portions?|dozen)?/i);
  if (match) {
    return {
      count: parseInt(match[1]),
      unit: match[2] || 'servings',
      original: servingsYield
    };
  }
  return null;
}

/**
 * Get scaled servings display string
 * @param {Object} servings - Parsed servings object
 * @param {number} scale - Scale multiplier
 * @returns {string} - Display string
 */
function getScaledServings(servings, scale) {
  if (!servings) return '';
  const scaled = Math.round(servings.count * scale);
  return `(${scaled} ${servings.unit})`;
}

/**
 * Set the recipe scale and re-render
 * @param {number} scale - The new scale value
 * @param {string} recipeId - The recipe ID to re-render
 */
function setRecipeScale(scale, recipeId) {
  recipeScale = scale;
  renderRecipeDetail(recipeId);
}

// Make scaling functions available globally
window.setRecipeScale = setRecipeScale;

/**
 * Find substitutes for an ingredient
 * @param {string} ingredient - The ingredient to find substitutes for
 * @returns {Array} - Array of substitute objects with ingredient name, ratio, and notes
 */
function findSubstitutes(ingredient) {
  if (!substitutionsData || !enableSubstitutions) return [];

  const normalized = normalizeIngredientName(ingredient);
  const substitutes = [];

  for (const rule of substitutionsData.substitutions) {
    // Check if this ingredient matches the primary or aliases
    const primaryMatch = normalizeIngredientName(rule.primary) === normalized;
    const aliasMatch = rule.aliases?.some(a => normalizeIngredientName(a) === normalized);

    if (primaryMatch || aliasMatch) {
      // Return all substitutes for this ingredient
      for (const sub of rule.substitutes) {
        substitutes.push({
          original: rule.primary,
          substitute: sub.ingredient,
          ratio: sub.ratio,
          direction: sub.direction,
          notes: sub.notes,
          impact: sub.impact,
          quality: sub.quality
        });
      }
    }

    // Also check if this ingredient IS a substitute for something
    for (const sub of rule.substitutes) {
      if (normalizeIngredientName(sub.ingredient) === normalized) {
        substitutes.push({
          original: sub.ingredient,
          substitute: rule.primary,
          ratio: sub.ratio, // Reverse ratio would need calculation
          direction: sub.direction === 'health' ? 'convenience' : 'health',
          notes: sub.notes,
          quality: sub.quality
        });
      }
    }
  }

  return substitutes;
}

/**
 * Get all ingredients that can substitute for a given ingredient
 * @param {string} ingredient - The ingredient
 * @returns {Array<string>} - Array of ingredient names that can substitute
 */
function getSubstituteIngredients(ingredient) {
  const subs = findSubstitutes(ingredient);
  return subs.map(s => s.substitute);
}

/**
 * Expand staples using substitution rules
 * E.g., if user has "milk", they can also match recipes needing "buttermilk"
 * @param {Array<string>} staples - User's staple ingredients
 * @returns {Array<string>} - Expanded list including substitution matches
 */
function expandStaplesWithSubstitutions(staples) {
  if (!substitutionsData || !enableSubstitutions) return staples;

  const expanded = new Set(staples);

  // Use the stapleExpansions rules from substitutions.json
  if (substitutionsData.stapleExpansions?.expansions) {
    for (const expansion of substitutionsData.stapleExpansions.expansions) {
      const stapleNorm = normalizeIngredientName(expansion.staple);

      // Check if user has this staple
      if (staples.some(s => normalizeIngredientName(s) === stapleNorm)) {
        // Add all the alsoMatches ingredients
        for (const match of expansion.alsoMatches) {
          expanded.add(match.toLowerCase());
        }
      }
    }
  }

  return Array.from(expanded);
}

// =============================================================================
// Recipe Ingredient Substitution Functions
// =============================================================================

/**
 * Find available substitutions for an ingredient on the recipe page
 * @param {string} ingredientName - The ingredient to find substitutes for
 * @returns {Object|null} - Substitution rule with primary and substitutes, or null
 */
function findSubstitutionsForIngredient(ingredientName) {
  if (!substitutionsData || !substitutionsData.substitutions) return null;

  const normalized = normalizeIngredientName(ingredientName);

  for (const rule of substitutionsData.substitutions) {
    // Check primary ingredient
    if (normalizeIngredientName(rule.primary) === normalized) {
      return rule;
    }

    // Check aliases
    if (rule.aliases) {
      for (const alias of rule.aliases) {
        if (normalizeIngredientName(alias) === normalized) {
          return rule;
        }
      }
    }

    // Check if this ingredient IS a substitute (reverse lookup)
    for (const sub of rule.substitutes) {
      if (normalizeIngredientName(sub.ingredient) === normalized) {
        // Return reverse substitution (can swap back to primary)
        return {
          primary: sub.ingredient,
          substitutes: [{
            ingredient: rule.primary,
            ratio: reverseRatio(sub.ratio),
            direction: sub.direction,
            notes: `Original ingredient (reverse of: ${sub.notes || ''})`.trim(),
            quality: sub.quality
          }],
          isReverse: true
        };
      }
    }
  }

  return null;
}

/**
 * Reverse a ratio string (e.g., "1:2" becomes "2:1")
 */
function reverseRatio(ratio) {
  if (!ratio || typeof ratio !== 'string') return '1:1';
  const parts = ratio.split(':');
  if (parts.length === 2) {
    return `${parts[1]}:${parts[0]}`;
  }
  return ratio;
}

/**
 * Reset all active substitutions for the current recipe
 */
function resetSubstitutions() {
  activeSubstitutions = {};
  currentRecipeNutrition = null;
  renderCurrentRecipe();
}

/**
 * Apply a substitution for an ingredient
 * @param {number} ingredientIndex - Index of the ingredient in the recipe
 * @param {Object} originalIng - Original ingredient object
 * @param {Object} substitute - The substitute to apply
 */
function applySubstitution(ingredientIndex, originalIng, substitute) {
  activeSubstitutions[ingredientIndex] = {
    original: originalIng,
    substitute: substitute,
    nutritionDelta: estimateNutritionDelta(originalIng, substitute)
  };

  // Close modal and re-render
  closeSubstitutionModal();
  renderCurrentRecipe();
}

/**
 * Remove a substitution (revert to original)
 * @param {number} ingredientIndex - Index of the ingredient
 */
function revertSubstitution(ingredientIndex) {
  delete activeSubstitutions[ingredientIndex];
  renderCurrentRecipe();
}

/**
 * Estimate nutrition delta for a substitution
 * This is a simplified estimation based on known substitution patterns
 */
function estimateNutritionDelta(original, substitute) {
  // Common nutritional differences per typical serving
  const nutritionEstimates = {
    // Fats
    'butter': { calories: 100, fat: 11, carbs: 0, protein: 0 },
    'margarine': { calories: 100, fat: 11, carbs: 0, protein: 0 },
    'coconut oil': { calories: 120, fat: 14, carbs: 0, protein: 0 },
    'applesauce': { calories: 25, fat: 0, carbs: 7, protein: 0 },
    'olive oil': { calories: 120, fat: 14, carbs: 0, protein: 0 },

    // Dairy
    'milk': { calories: 150, fat: 8, carbs: 12, protein: 8 },
    'almond milk': { calories: 30, fat: 2.5, carbs: 1, protein: 1 },
    'oat milk': { calories: 120, fat: 5, carbs: 16, protein: 3 },
    'heavy cream': { calories: 400, fat: 43, carbs: 3, protein: 3 },
    'half and half': { calories: 150, fat: 14, carbs: 5, protein: 4 },
    'evaporated milk': { calories: 170, fat: 10, carbs: 13, protein: 9 },
    'sour cream': { calories: 230, fat: 23, carbs: 5, protein: 3 },
    'greek yogurt': { calories: 100, fat: 0, carbs: 6, protein: 17 },

    // Eggs
    'eggs': { calories: 70, fat: 5, carbs: 0, protein: 6 },
    'egg substitute': { calories: 25, fat: 0, carbs: 1, protein: 5 },
    'flax egg': { calories: 37, fat: 3, carbs: 2, protein: 1 },

    // Sweeteners
    'sugar': { calories: 48, fat: 0, carbs: 12, protein: 0 },
    'honey': { calories: 64, fat: 0, carbs: 17, protein: 0 },
    'maple syrup': { calories: 52, fat: 0, carbs: 13, protein: 0 },
    'stevia': { calories: 0, fat: 0, carbs: 0, protein: 0 },
    'swerve': { calories: 0, fat: 0, carbs: 0, protein: 0 },
    'monk fruit sweetener': { calories: 0, fat: 0, carbs: 0, protein: 0 },

    // Cheese
    'parmesan cheese': { calories: 110, fat: 7, carbs: 1, protein: 10 },
    'pecorino romano': { calories: 110, fat: 8, carbs: 1, protein: 9 },
    'nutritional yeast': { calories: 20, fat: 0, carbs: 1, protein: 3 },
    'cream cheese': { calories: 100, fat: 10, carbs: 1, protein: 2 },
    'neufchatel cheese': { calories: 70, fat: 6, carbs: 1, protein: 3 },

    // Flour
    'flour': { calories: 110, fat: 0, carbs: 23, protein: 3 },
    'almond flour': { calories: 160, fat: 14, carbs: 6, protein: 6 },
    'coconut flour': { calories: 60, fat: 2, carbs: 8, protein: 2 },
    'whole wheat flour': { calories: 100, fat: 1, carbs: 21, protein: 4 },
  };

  const origName = normalizeIngredientName(original.item || original);
  const subName = normalizeIngredientName(substitute.ingredient);

  const origNutrition = nutritionEstimates[origName] || null;
  const subNutrition = nutritionEstimates[subName] || null;

  if (origNutrition && subNutrition) {
    return {
      calories: subNutrition.calories - origNutrition.calories,
      fat: subNutrition.fat - origNutrition.fat,
      carbs: subNutrition.carbs - origNutrition.carbs,
      protein: subNutrition.protein - origNutrition.protein
    };
  }

  // Check for caloric impact in the substitution notes
  if (substitute.impact) {
    const calorieMatch = substitute.impact.match(/(\d+)\s*calories?/i);
    if (calorieMatch) {
      const cal = parseInt(calorieMatch[1], 10);
      if (substitute.impact.toLowerCase().includes('save')) {
        return { calories: -cal, fat: 0, carbs: 0, protein: 0 };
      }
    }
  }

  return null;
}

/**
 * Calculate adjusted nutrition based on active substitutions
 */
function calculateAdjustedNutrition(baseNutrition) {
  if (!baseNutrition || !baseNutrition.per_serving) return baseNutrition;

  // Start with a copy of the base nutrition
  const adjusted = JSON.parse(JSON.stringify(baseNutrition));

  // Calculate total delta from all substitutions
  let totalDelta = { calories: 0, fat: 0, carbs: 0, protein: 0 };
  let hasDeltas = false;

  for (const sub of Object.values(activeSubstitutions)) {
    if (sub.nutritionDelta) {
      totalDelta.calories += sub.nutritionDelta.calories || 0;
      totalDelta.fat += sub.nutritionDelta.fat || 0;
      totalDelta.carbs += sub.nutritionDelta.carbs || 0;
      totalDelta.protein += sub.nutritionDelta.protein || 0;
      hasDeltas = true;
    }
  }

  if (!hasDeltas) return baseNutrition;

  // Apply deltas (per serving)
  if (adjusted.per_serving.calories !== null) {
    adjusted.per_serving.calories = Math.max(0, Math.round(adjusted.per_serving.calories + totalDelta.calories));
  }
  if (adjusted.per_serving.fat_g !== null) {
    adjusted.per_serving.fat_g = Math.max(0, Math.round((adjusted.per_serving.fat_g + totalDelta.fat) * 10) / 10);
  }
  if (adjusted.per_serving.carbs_g !== null) {
    adjusted.per_serving.carbs_g = Math.max(0, Math.round((adjusted.per_serving.carbs_g + totalDelta.carbs) * 10) / 10);
  }
  if (adjusted.per_serving.protein_g !== null) {
    adjusted.per_serving.protein_g = Math.max(0, Math.round((adjusted.per_serving.protein_g + totalDelta.protein) * 10) / 10);
  }

  // Add note about adjustments
  adjusted.substitutionNote = `Adjusted for ${Object.keys(activeSubstitutions).length} substitution(s)`;

  return adjusted;
}

/**
 * Show the substitution modal for an ingredient
 */
function showSubstitutionModal(ingredientIndex, ingredient, rule) {
  // Create modal if it doesn't exist
  let modal = document.getElementById('substitution-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'substitution-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const isActive = activeSubstitutions[ingredientIndex];

  modal.innerHTML = `
    <div class="modal-content substitution-modal">
      <button class="modal-close" onclick="closeSubstitutionModal()" aria-label="Close">&times;</button>
      <h3>Swap Ingredient</h3>

      <div class="current-ingredient">
        <span class="label">Current:</span>
        <span class="ingredient-name">${escapeHtml(isActive ? isActive.substitute.ingredient : ingredient.item)}</span>
        ${isActive ? '<span class="badge badge-swapped">Swapped</span>' : ''}
      </div>

      ${isActive ? `
        <button class="btn btn-secondary revert-btn" onclick="revertSubstitution(${ingredientIndex})">
          ↩ Revert to ${escapeHtml(isActive.original.item)}
        </button>
        <hr>
      ` : ''}

      <div class="substitution-options">
        <p class="options-label">Available substitutes:</p>
        ${rule.substitutes.map((sub, idx) => `
          <div class="substitution-option" onclick="applySubstitution(${ingredientIndex}, ${escapeAttr(JSON.stringify(ingredient))}, ${escapeAttr(JSON.stringify(sub))})">
            <div class="sub-header">
              <span class="sub-name">${escapeHtml(sub.ingredient)}</span>
              <span class="sub-quality quality-${sub.quality || 'moderate'}">${sub.quality || 'moderate'}</span>
            </div>
            <div class="sub-details">
              <span class="sub-ratio">${escapeHtml(sub.ratio)}</span>
              ${sub.direction ? `<span class="sub-direction">${escapeHtml(sub.direction)}</span>` : ''}
            </div>
            ${sub.notes ? `<p class="sub-notes">${escapeHtml(sub.notes)}</p>` : ''}
            ${sub.impact ? `<p class="sub-impact">${escapeHtml(sub.impact)}</p>` : ''}
          </div>
        `).join('')}
      </div>
    </div>
  `;

  modal.classList.add('active');

  // Close on overlay click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeSubstitutionModal();
  });

  // Close on escape
  document.addEventListener('keydown', handleModalEscape);
}

function handleModalEscape(e) {
  if (e.key === 'Escape') closeSubstitutionModal();
}

function closeSubstitutionModal() {
  const modal = document.getElementById('substitution-modal');
  if (modal) {
    modal.classList.remove('active');
  }
  document.removeEventListener('keydown', handleModalEscape);
}

// Make functions globally available
window.showSubstitutionModal = showSubstitutionModal;
window.closeSubstitutionModal = closeSubstitutionModal;
window.applySubstitution = applySubstitution;
window.revertSubstitution = revertSubstitution;
window.resetSubstitutions = resetSubstitutions;

// =============================================================================
// Nutrition & Time Filter Functions
// =============================================================================

/**
 * Parse time string to minutes
 * @param {string} timeStr - Time string like "30 min", "1 hour 15 min", "45 minutes"
 * @returns {number|null} - Total minutes or null if unparseable
 */
function parseTimeToMinutes(timeStr) {
  if (!timeStr) return null;

  const str = timeStr.toLowerCase().trim();
  let totalMinutes = 0;

  // Match hours
  const hourMatch = str.match(/(\d+\.?\d*)\s*(hour|hr|h)/);
  if (hourMatch) {
    totalMinutes += parseFloat(hourMatch[1]) * 60;
  }

  // Match minutes
  const minMatch = str.match(/(\d+)\s*(minute|min|m)(?!i)/);
  if (minMatch) {
    totalMinutes += parseInt(minMatch[1], 10);
  }

  // If only a number, assume minutes
  if (totalMinutes === 0) {
    const justNumber = str.match(/^(\d+)$/);
    if (justNumber) {
      totalMinutes = parseInt(justNumber[1], 10);
    }
  }

  return totalMinutes > 0 ? totalMinutes : null;
}

/**
 * Check if any nutrition filter is active (excluding onlyWithNutrition)
 * @returns {boolean}
 */
function hasActiveNutritionFilter() {
  return (
    nutritionFilter.calories.min !== null ||
    nutritionFilter.calories.max !== null ||
    nutritionFilter.carbs.min !== null ||
    nutritionFilter.carbs.max !== null ||
    nutritionFilter.protein.min !== null ||
    nutritionFilter.protein.max !== null ||
    nutritionFilter.fat.min !== null ||
    nutritionFilter.fat.max !== null
  );
}

/**
 * Apply a diet preset to the nutrition filter
 * @param {string} presetId - The preset ID like 'low-carb', 'low-cal', etc.
 */
function applyDietPreset(presetId) {
  // Clear all nutrition filters first
  clearNutritionFilters();

  if (presetId === 'clear' || !DIET_PRESETS[presetId]) {
    nutritionFilter.activeDietPreset = null;
    updateDietPresetButtons();
    updateNutritionInputs();
    renderRecipeGrid();
    return;
  }

  const preset = DIET_PRESETS[presetId];
  nutritionFilter.activeDietPreset = presetId;

  // Apply preset values
  if (preset.calories) {
    nutritionFilter.calories.min = preset.calories.min || null;
    nutritionFilter.calories.max = preset.calories.max || null;
  }
  if (preset.carbs) {
    nutritionFilter.carbs.min = preset.carbs.min || null;
    nutritionFilter.carbs.max = preset.carbs.max || null;
  }
  if (preset.protein) {
    nutritionFilter.protein.min = preset.protein.min || null;
    nutritionFilter.protein.max = preset.protein.max || null;
  }
  if (preset.fat) {
    nutritionFilter.fat.min = preset.fat.min || null;
    nutritionFilter.fat.max = preset.fat.max || null;
  }

  updateDietPresetButtons();
  updateNutritionInputs();
  renderRecipeGrid();
}

/**
 * Clear all nutrition filters
 */
function clearNutritionFilters() {
  nutritionFilter.calories = { min: null, max: null };
  nutritionFilter.carbs = { min: null, max: null };
  nutritionFilter.protein = { min: null, max: null };
  nutritionFilter.fat = { min: null, max: null };
  nutritionFilter.activeDietPreset = null;
}

/**
 * Update the diet preset button visual states
 */
function updateDietPresetButtons() {
  document.querySelectorAll('.diet-preset-btn').forEach(btn => {
    const preset = btn.dataset.diet;
    btn.classList.toggle('active', preset === nutritionFilter.activeDietPreset);
  });
}

/**
 * Update the nutrition input fields to reflect current filter state
 */
function updateNutritionInputs() {
  const calMin = document.getElementById('cal-min');
  const calMax = document.getElementById('cal-max');
  const carbsMin = document.getElementById('carbs-min');
  const carbsMax = document.getElementById('carbs-max');
  const proteinMin = document.getElementById('protein-min');
  const proteinMax = document.getElementById('protein-max');
  const fatMin = document.getElementById('fat-min');
  const fatMax = document.getElementById('fat-max');

  if (calMin) calMin.value = nutritionFilter.calories.min ?? '';
  if (calMax) calMax.value = nutritionFilter.calories.max ?? '';
  if (carbsMin) carbsMin.value = nutritionFilter.carbs.min ?? '';
  if (carbsMax) carbsMax.value = nutritionFilter.carbs.max ?? '';
  if (proteinMin) proteinMin.value = nutritionFilter.protein.min ?? '';
  if (proteinMax) proteinMax.value = nutritionFilter.protein.max ?? '';
  if (fatMin) fatMin.value = nutritionFilter.fat.min ?? '';
  if (fatMax) fatMax.value = nutritionFilter.fat.max ?? '';
}

/**
 * Read current values from nutrition input fields and apply to filter
 */
function applyCustomNutritionFilters() {
  const parseInput = (id) => {
    const el = document.getElementById(id);
    if (!el || el.value.trim() === '') return null;
    const val = parseInt(el.value, 10);
    return isNaN(val) ? null : val;
  };

  // Clear preset when custom values are entered
  nutritionFilter.activeDietPreset = null;
  updateDietPresetButtons();

  nutritionFilter.calories.min = parseInput('cal-min');
  nutritionFilter.calories.max = parseInput('cal-max');
  nutritionFilter.carbs.min = parseInput('carbs-min');
  nutritionFilter.carbs.max = parseInput('carbs-max');
  nutritionFilter.protein.min = parseInput('protein-min');
  nutritionFilter.protein.max = parseInput('protein-max');
  nutritionFilter.fat.min = parseInput('fat-min');
  nutritionFilter.fat.max = parseInput('fat-max');

  const onlyWithNutrition = document.getElementById('only-with-nutrition');
  nutritionFilter.onlyWithNutrition = onlyWithNutrition?.checked || false;

  renderRecipeGrid();
}

/**
 * Setup nutrition and time filter event listeners
 */
function setupNutritionFilters() {
  // Time filter
  const timeFilter = document.getElementById('time-filter');
  if (timeFilter) {
    timeFilter.addEventListener('change', (e) => {
      nutritionFilter.timeLimit = e.target.value ? parseInt(e.target.value, 10) : null;
      renderRecipeGrid();
    });
  }

  // Nutrition toggle button
  const nutritionToggle = document.getElementById('nutrition-toggle');
  const nutritionFilters = document.getElementById('nutrition-filters');
  if (nutritionToggle && nutritionFilters) {
    nutritionToggle.addEventListener('click', () => {
      const isExpanded = nutritionToggle.getAttribute('aria-expanded') === 'true';
      nutritionToggle.setAttribute('aria-expanded', !isExpanded);
      nutritionFilters.classList.toggle('hidden', isExpanded);
      nutritionToggle.querySelector('.toggle-icon').textContent = isExpanded ? '▼' : '▲';
    });
  }

  // Diet preset buttons
  document.querySelectorAll('.diet-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      applyDietPreset(btn.dataset.diet);
    });
  });

  // Apply filters button
  const applyBtn = document.getElementById('apply-nutrition-filter');
  if (applyBtn) {
    applyBtn.addEventListener('click', applyCustomNutritionFilters);
  }

  // Only with nutrition checkbox - apply immediately
  const onlyWithNutrition = document.getElementById('only-with-nutrition');
  if (onlyWithNutrition) {
    onlyWithNutrition.addEventListener('change', () => {
      nutritionFilter.onlyWithNutrition = onlyWithNutrition.checked;
      renderRecipeGrid();
    });
  }

  // Shopping panel toggle
  const shoppingToggle = document.getElementById('shopping-toggle');
  const shoppingPanel = document.getElementById('shopping-list-panel');
  if (shoppingToggle && shoppingPanel) {
    shoppingToggle.addEventListener('click', () => {
      const isExpanded = shoppingToggle.getAttribute('aria-expanded') === 'true';
      shoppingToggle.setAttribute('aria-expanded', !isExpanded);
      shoppingPanel.classList.toggle('hidden', isExpanded);
      shoppingToggle.querySelector('.toggle-icon').textContent = isExpanded ? '▼' : '▲';
    });
  }
}

/**
 * Get nutrition status for a recipe based on current filters
 * @param {Object} recipe - The recipe object
 * @returns {Object} - { status: 'good'|'warn'|'over'|null, message: string }
 */
function getNutritionStatus(recipe) {
  if (!hasActiveNutritionFilter() && !nutritionFilter.activeDietPreset) {
    return null;
  }

  if (!recipe.nutrition) {
    return { status: 'warn', message: 'No nutrition data' };
  }

  const n = recipe.nutrition;
  const issues = [];

  // Check each filter
  if (nutritionFilter.calories.max !== null && n.calories > nutritionFilter.calories.max) {
    issues.push(`${n.calories} cal (max ${nutritionFilter.calories.max})`);
  }
  if (nutritionFilter.carbs.max !== null && n.carbohydrates > nutritionFilter.carbs.max) {
    issues.push(`${n.carbohydrates}g carbs (max ${nutritionFilter.carbs.max}g)`);
  }
  if (nutritionFilter.protein.min !== null && n.protein < nutritionFilter.protein.min) {
    issues.push(`${n.protein}g protein (min ${nutritionFilter.protein.min}g)`);
  }
  if (nutritionFilter.fat.max !== null && n.fat > nutritionFilter.fat.max) {
    issues.push(`${n.fat}g fat (max ${nutritionFilter.fat.max}g)`);
  }

  if (issues.length > 0) {
    return { status: 'over', message: issues.join(', ') };
  }

  return { status: 'good', message: 'Meets criteria' };
}

// =============================================================================
// Meal Pairing & Shopping List Functions
// =============================================================================

/**
 * Get meal pairing suggestions for a recipe
 * @param {Object} recipe - The recipe to find pairings for
 * @param {number} limit - Maximum number of suggestions
 * @returns {Array} - Array of suggested recipes
 */
function getMealPairings(recipe, limit = 6) {
  if (!recipe || !recipe.category) return [];

  const pairingCategories = MEAL_PAIRINGS[recipe.category] || [];
  if (pairingCategories.length === 0) return [];

  // Get ingredients from the current recipe for efficiency matching
  const recipeIngredients = new Set(
    (recipe.ingredients || []).map(ing => {
      const name = typeof ing === 'string' ? ing : ing.item || ing.name || '';
      return normalizeIngredientName(name);
    }).filter(Boolean)
  );

  // Find matching recipes
  const candidates = recipes.filter(r => {
    // Must be in a pairing category
    if (!pairingCategories.includes(r.category)) return false;
    // Not the same recipe
    if (r.id === recipe.id) return false;
    // Not a variant
    if (r.variant_of && r.variant_of !== r.id) return false;
    return true;
  });

  // Score candidates by ingredient efficiency (shared ingredients)
  const scored = candidates.map(r => {
    const rIngredients = (r.ingredients || []).map(ing => {
      const name = typeof ing === 'string' ? ing : ing.item || ing.name || '';
      return normalizeIngredientName(name);
    }).filter(Boolean);

    let sharedCount = 0;
    for (const ing of rIngredients) {
      if (recipeIngredients.has(ing)) sharedCount++;
    }

    return {
      recipe: r,
      sharedIngredients: sharedCount,
      // Prefer recipes with nutrition data
      hasNutrition: r.nutrition ? 1 : 0
    };
  });

  // Sort by shared ingredients (desc), then by nutrition data
  scored.sort((a, b) => {
    if (b.sharedIngredients !== a.sharedIngredients) {
      return b.sharedIngredients - a.sharedIngredients;
    }
    return b.hasNutrition - a.hasNutrition;
  });

  return scored.slice(0, limit).map(s => ({
    ...s.recipe,
    sharedIngredients: s.sharedIngredients
  }));
}

/**
 * Add a recipe to the shopping list
 * @param {string} recipeId - The recipe ID to add
 */
function addToShoppingList(recipeId) {
  const recipe = recipes.find(r => r.id === recipeId);
  if (!recipe) return;

  if (!selectedMealRecipes.find(r => r.id === recipeId)) {
    selectedMealRecipes.push(recipe);
    generateShoppingList();
    renderShoppingListPanel();
  }
}

/**
 * Remove a recipe from the shopping list
 * @param {string} recipeId - The recipe ID to remove
 */
function removeFromShoppingList(recipeId) {
  selectedMealRecipes = selectedMealRecipes.filter(r => r.id !== recipeId);
  generateShoppingList();
  renderShoppingListPanel();
}

/**
 * Generate consolidated shopping list from selected recipes
 */
function generateShoppingList() {
  const ingredientMap = new Map();

  for (const recipe of selectedMealRecipes) {
    if (!recipe.ingredients) continue;

    for (const ing of recipe.ingredients) {
      let name, quantity, unit;

      if (typeof ing === 'string') {
        // Parse string format like "1 cup flour"
        const parsed = parseIngredientString(ing);
        name = parsed.name;
        quantity = parsed.quantity;
        unit = parsed.unit;
      } else {
        name = ing.item || ing.name || '';
        quantity = ing.amount || ing.quantity || '';
        unit = ing.unit || '';
      }

      if (!name) continue;

      const normalizedName = normalizeIngredientName(name);
      const key = normalizedName;

      if (ingredientMap.has(key)) {
        const existing = ingredientMap.get(key);
        existing.recipes.push(recipe.title);
        // We can't reliably combine quantities without unit conversion, so just note multiple
        if (quantity) {
          existing.quantities.push({ amount: quantity, unit: unit, recipe: recipe.title });
        }
      } else {
        ingredientMap.set(key, {
          name: name,
          normalizedName: normalizedName,
          recipes: [recipe.title],
          quantities: quantity ? [{ amount: quantity, unit: unit, recipe: recipe.title }] : [],
          checked: false
        });
      }
    }
  }

  shoppingList = Array.from(ingredientMap.values());

  // Sort alphabetically
  shoppingList.sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Parse an ingredient string into components
 * @param {string} str - Ingredient string like "1 cup flour"
 * @returns {Object} - { quantity, unit, name }
 */
function parseIngredientString(str) {
  if (!str) return { quantity: '', unit: '', name: '' };

  // Match patterns like "1 cup", "2 1/2 tbsp", "1/2 tsp"
  const match = str.match(/^([\d\s\/]+)?\s*(cup|cups|tbsp|tsp|tablespoon|tablespoons|teaspoon|teaspoons|oz|ounce|ounces|lb|lbs|pound|pounds|can|cans|package|packages|pkg|jar|jars|bunch|bunches|clove|cloves|head|heads|slice|slices|piece|pieces)?\s*(.+)?$/i);

  if (match) {
    return {
      quantity: (match[1] || '').trim(),
      unit: (match[2] || '').trim(),
      name: (match[3] || str).trim()
    };
  }

  return { quantity: '', unit: '', name: str.trim() };
}

/**
 * Toggle shopping list item checked state
 * @param {string} normalizedName - The normalized ingredient name
 */
function toggleShoppingItem(normalizedName) {
  const item = shoppingList.find(i => i.normalizedName === normalizedName);
  if (item) {
    item.checked = !item.checked;
    renderShoppingListPanel();
  }
}

/**
 * Render the shopping list panel
 */
function renderShoppingListPanel() {
  const panel = document.getElementById('shopping-list-panel');
  if (!panel) return;

  if (selectedMealRecipes.length === 0) {
    panel.innerHTML = `
      <div class="shopping-list-empty">
        <p>No recipes selected. Add recipes to your meal plan to generate a shopping list.</p>
      </div>
    `;
    return;
  }

  const recipesHtml = selectedMealRecipes.map(r => `
    <div class="shopping-recipe">
      <span class="shopping-recipe-title">${escapeHtml(r.title)}</span>
      <button type="button" class="shopping-recipe-remove" onclick="removeFromShoppingList('${escapeAttr(r.id)}')" title="Remove">&times;</button>
    </div>
  `).join('');

  const unchecked = shoppingList.filter(i => !i.checked);
  const checked = shoppingList.filter(i => i.checked);

  const renderItem = (item) => {
    const quantityInfo = item.quantities.length > 0
      ? item.quantities.map(q => `${q.amount} ${q.unit}`.trim()).join(', ')
      : '';
    const recipeInfo = item.recipes.length > 1
      ? ` (${item.recipes.join(', ')})`
      : '';

    return `
      <label class="shopping-item ${item.checked ? 'checked' : ''}">
        <input type="checkbox" ${item.checked ? 'checked' : ''} onchange="toggleShoppingItem('${escapeAttr(item.normalizedName)}')">
        <span class="item-name">${escapeHtml(item.name)}</span>
        ${quantityInfo ? `<span class="item-quantity">${escapeHtml(quantityInfo)}</span>` : ''}
        ${recipeInfo ? `<span class="item-recipes">${escapeHtml(recipeInfo)}</span>` : ''}
      </label>
    `;
  };

  const itemsHtml = `
    ${unchecked.map(renderItem).join('')}
    ${checked.length > 0 ? `
      <div class="shopping-list-checked-header">Checked (${checked.length})</div>
      ${checked.map(renderItem).join('')}
    ` : ''}
  `;

  panel.innerHTML = `
    <div class="shopping-list-header">
      <h3>Meal Plan (${selectedMealRecipes.length} recipes)</h3>
      <button type="button" class="btn btn-small" onclick="copyShoppingList()">Copy List</button>
    </div>
    <div class="shopping-recipes-list">
      ${recipesHtml}
    </div>
    <div class="shopping-list-divider"></div>
    <div class="shopping-items-header">
      <h4>Shopping List (${shoppingList.length} items)</h4>
    </div>
    <div class="shopping-items-list">
      ${itemsHtml}
    </div>
  `;
}

/**
 * Copy shopping list to clipboard
 */
async function copyShoppingList() {
  if (shoppingList.length === 0) return;

  const lines = ['Shopping List', ''];

  // Add recipe titles
  lines.push('Recipes:');
  for (const r of selectedMealRecipes) {
    lines.push(`- ${r.title}`);
  }
  lines.push('');

  // Add ingredients
  lines.push('Ingredients:');
  for (const item of shoppingList) {
    const quantityInfo = item.quantities.length > 0
      ? ` (${item.quantities.map(q => `${q.amount} ${q.unit}`.trim()).join(', ')})`
      : '';
    lines.push(`- ${item.name}${quantityInfo}`);
  }

  const text = lines.join('\n');

  try {
    await navigator.clipboard.writeText(text);
    showToast('Shopping list copied to clipboard!');
  } catch (err) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast('Shopping list copied!');
  }
}

/**
 * Show a toast notification
 * @param {string} message - The message to show
 */
function showToast(message) {
  // Remove existing toast
  const existing = document.querySelector('.toast-notification');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast-notification';
  toast.textContent = message;
  document.body.appendChild(toast);

  // Trigger animation
  setTimeout(() => toast.classList.add('show'), 10);

  // Remove after delay
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

/**
 * Copy shareable link to clipboard
 */
async function copyShareableLink() {
  const url = new URL(window.location.href);

  // Add current filters to URL
  if (currentFilter.search) {
    url.searchParams.set('q', currentFilter.search);
  }
  if (currentFilter.category) {
    url.searchParams.set('cat', currentFilter.category);
  }
  if (selectedIngredients.length > 0) {
    url.searchParams.set('ing', selectedIngredients.join(','));
  }
  if (nutritionFilter.activeDietPreset) {
    url.searchParams.set('diet', nutritionFilter.activeDietPreset);
  }
  if (nutritionFilter.timeLimit) {
    url.searchParams.set('time', nutritionFilter.timeLimit);
  }

  try {
    await navigator.clipboard.writeText(url.toString());
    showToast('Link copied to clipboard!');
  } catch (err) {
    const textarea = document.createElement('textarea');
    textarea.value = url.toString();
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast('Link copied!');
  }
}

/**
 * Clear the shopping list
 */
function clearShoppingList() {
  selectedMealRecipes = [];
  shoppingList = [];
  renderShoppingListPanel();
}

// Make shopping list functions available globally
window.addToShoppingList = addToShoppingList;
window.removeFromShoppingList = removeFromShoppingList;
window.toggleShoppingItem = toggleShoppingItem;
window.copyShoppingList = copyShoppingList;
window.copyShareableLink = copyShareableLink;
window.clearShoppingList = clearShoppingList;

// =============================================================================
// Ingredient Search Functions
// =============================================================================

/**
 * Setup ingredient search event listeners
 */
function setupIngredientSearch() {
  const input = document.getElementById('ingredient-input');
  const searchBtn = document.getElementById('ingredient-search-btn');
  const optionsBtn = document.getElementById('ingredient-options-btn');
  const optionsPanel = document.getElementById('ingredient-options-panel');
  const clearBtn = document.getElementById('clear-ingredient-search');
  const autocomplete = document.getElementById('ingredient-autocomplete');

  if (!input) return; // Not on a page with ingredient search

  // Input events for autocomplete
  input.addEventListener('input', debounce(handleIngredientInput, 150));
  input.addEventListener('keydown', handleIngredientKeydown);
  input.addEventListener('focus', () => {
    if (input.value.length >= 2) {
      showAutocomplete(input.value);
    }
  });

  // Close autocomplete when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.ingredient-input-container')) {
      hideAutocomplete();
    }
  });

  // Search button
  if (searchBtn) {
    searchBtn.addEventListener('click', performIngredientSearch);
  }

  // Options panel toggle
  if (optionsBtn && optionsPanel) {
    optionsBtn.addEventListener('click', () => {
      const isExpanded = optionsBtn.getAttribute('aria-expanded') === 'true';
      optionsBtn.setAttribute('aria-expanded', !isExpanded);
      optionsPanel.classList.toggle('hidden', isExpanded);
    });
  }

  // Option buttons (match mode and missing threshold)
  document.querySelectorAll('.option-btn[data-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.option-btn[data-mode]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      ingredientSearchOptions.matchMode = btn.dataset.mode;
      if (selectedIngredients.length > 0) {
        performIngredientSearch();
      }
    });
  });

  document.querySelectorAll('.option-btn[data-missing]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.option-btn[data-missing]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      ingredientSearchOptions.missingThreshold = parseInt(btn.dataset.missing, 10);
      if (selectedIngredients.length > 0) {
        performIngredientSearch();
      }
    });
  });

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener('click', clearIngredientSearch);
  }

  // Suggestion chips
  document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const ingredient = chip.dataset.ingredient;
      if (!selectedIngredients.includes(ingredient)) {
        addSelectedIngredient(ingredient);
        performIngredientSearch();
      }
    });
  });

  // Page size selector for ingredient results
  const pageSizeSelect = document.getElementById('results-per-page');
  if (pageSizeSelect) {
    pageSizeSelect.addEventListener('change', (e) => {
      const value = e.target.value;
      ingredientResultsPageSize = value === 'all' ? Infinity : parseInt(value, 10);
      ingredientResultsShown = 0;
      renderIngredientRecipeList();
    });
  }

  // Load more button
  const loadMoreBtn = document.getElementById('load-more-recipes');
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', () => {
      loadMoreIngredientResults();
    });
  }
}

/**
 * Handle input in the ingredient search field
 */
function handleIngredientInput(e) {
  const query = e.target.value.trim();

  if (query.length < 2) {
    hideAutocomplete();
    return;
  }

  showAutocomplete(query);
}

/**
 * Handle keyboard navigation in autocomplete
 */
function handleIngredientKeydown(e) {
  const autocomplete = document.getElementById('ingredient-autocomplete');
  const items = autocomplete.querySelectorAll('.autocomplete-item');

  if (autocomplete.classList.contains('hidden') || items.length === 0) {
    if (e.key === 'Enter') {
      e.preventDefault();
      const input = e.target;
      const value = input.value.trim();
      if (value && !selectedIngredients.includes(value.toLowerCase())) {
        addSelectedIngredient(value.toLowerCase());
        input.value = '';
        hideAutocomplete();
        performIngredientSearch();
      }
    }
    return;
  }

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault();
      autocompleteHighlightIndex = Math.min(autocompleteHighlightIndex + 1, items.length - 1);
      updateAutocompleteHighlight(items);
      break;

    case 'ArrowUp':
      e.preventDefault();
      autocompleteHighlightIndex = Math.max(autocompleteHighlightIndex - 1, -1);
      updateAutocompleteHighlight(items);
      break;

    case 'Enter':
      e.preventDefault();
      if (autocompleteHighlightIndex >= 0 && items[autocompleteHighlightIndex]) {
        selectAutocompleteItem(items[autocompleteHighlightIndex]);
      } else if (items.length > 0) {
        selectAutocompleteItem(items[0]);
      }
      break;

    case 'Escape':
      hideAutocomplete();
      break;
  }
}

/**
 * Update autocomplete highlight state
 */
function updateAutocompleteHighlight(items) {
  items.forEach((item, index) => {
    item.classList.toggle('highlighted', index === autocompleteHighlightIndex);
    if (index === autocompleteHighlightIndex) {
      item.scrollIntoView({ block: 'nearest' });
    }
  });
}

/**
 * Show autocomplete dropdown with matches
 */
async function showAutocomplete(query) {
  const autocomplete = document.getElementById('ingredient-autocomplete');
  if (!autocomplete) return;

  // Lazy load ingredient index on first use
  if (!ingredientIndex) {
    autocomplete.innerHTML = `<div class="autocomplete-item" style="color: var(--color-text-light); cursor: default;">Loading ingredients...</div>`;
    autocomplete.classList.remove('hidden');
    await loadIngredientIndex();
    await loadSubstitutions(); // Also load substitutions for search
    if (!ingredientIndex) {
      autocomplete.innerHTML = `<div class="autocomplete-item" style="color: var(--color-text-light); cursor: default;">Failed to load ingredients</div>`;
      return;
    }
  }

  const matches = searchIngredients(query, 10);
  autocompleteHighlightIndex = -1;

  if (matches.length === 0) {
    autocomplete.innerHTML = `
      <div class="autocomplete-item" style="color: var(--color-text-light); cursor: default;">
        No matches found
      </div>
    `;
    autocomplete.classList.remove('hidden');
    return;
  }

  autocomplete.innerHTML = matches.map(match => {
    const highlightedName = highlightMatch(match.name, query);
    const recipeCount = match.recipeCount;
    return `
      <div class="autocomplete-item" data-ingredient="${escapeAttr(match.name)}" role="option">
        <span class="autocomplete-item-name">${highlightedName}</span>
        <span class="autocomplete-item-count">${recipeCount} recipe${recipeCount !== 1 ? 's' : ''}</span>
      </div>
    `;
  }).join('');

  // Add click handlers to items
  autocomplete.querySelectorAll('.autocomplete-item[data-ingredient]').forEach(item => {
    item.addEventListener('click', () => selectAutocompleteItem(item));
  });

  autocomplete.classList.remove('hidden');
}

/**
 * Hide autocomplete dropdown
 */
function hideAutocomplete() {
  const autocomplete = document.getElementById('ingredient-autocomplete');
  if (autocomplete) {
    autocomplete.classList.add('hidden');
    autocompleteHighlightIndex = -1;
  }
}

/**
 * Select an item from the autocomplete
 */
function selectAutocompleteItem(item) {
  const ingredient = item.dataset.ingredient;
  if (!ingredient) return;

  const input = document.getElementById('ingredient-input');
  if (input) {
    input.value = '';
    input.focus();
  }

  if (!selectedIngredients.includes(ingredient)) {
    addSelectedIngredient(ingredient);
    performIngredientSearch();
  }

  hideAutocomplete();
}

/**
 * Get canonical name for an ingredient using synonyms
 */
function getCanonicalName(name) {
  if (!ingredientIndex) return name;
  const lower = name.toLowerCase().trim();
  return ingredientIndex.synonyms[lower] || lower;
}

/**
 * Search ingredients using fuzzy matching
 */
function searchIngredients(query, limit = 10) {
  if (!ingredientIndex || !query) return [];

  const queryLower = query.toLowerCase().trim();
  const results = [];
  const seen = new Set();

  // Search through canonical ingredient names (keys of ingredients object)
  for (const canonical of Object.keys(ingredientIndex.ingredients)) {
    // Skip already selected ingredients
    if (selectedIngredients.some(s => getCanonicalName(s) === canonical)) continue;

    const score = fuzzyMatch(canonical, queryLower);
    if (score > 0 && !seen.has(canonical)) {
      seen.add(canonical);
      const recipeIds = ingredientIndex.ingredients[canonical] || [];

      results.push({
        name: canonical,
        canonical: canonical,
        score: score,
        recipeCount: recipeIds.length
      });
    }
  }

  // Also search through synonyms for better matching
  for (const [variant, canonical] of Object.entries(ingredientIndex.synonyms)) {
    if (seen.has(canonical)) continue;
    if (selectedIngredients.some(s => getCanonicalName(s) === canonical)) continue;

    const score = fuzzyMatch(variant, queryLower);
    if (score > 0) {
      seen.add(canonical);
      const recipeIds = ingredientIndex.ingredients[canonical] || [];

      results.push({
        name: canonical,  // Show canonical name, not variant
        canonical: canonical,
        score: score,
        recipeCount: recipeIds.length
      });
    }
  }

  // Sort by score (descending), then by recipe count (descending)
  results.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return b.recipeCount - a.recipeCount;
  });

  return results.slice(0, limit);
}

/**
 * Fuzzy match scoring function
 * Returns higher score for better matches
 */
function fuzzyMatch(text, query) {
  const textLower = text.toLowerCase();
  const queryLower = query.toLowerCase();

  // Exact match
  if (textLower === queryLower) return 100;

  // Starts with query
  if (textLower.startsWith(queryLower)) return 90;

  // Contains query as word boundary
  const wordBoundaryRegex = new RegExp(`\\b${escapeRegex(queryLower)}`);
  if (wordBoundaryRegex.test(textLower)) return 80;

  // Contains query anywhere
  if (textLower.includes(queryLower)) return 70;

  // Check for word matches (e.g., "chick" matches "chicken")
  const words = textLower.split(/\s+/);
  for (const word of words) {
    if (word.startsWith(queryLower)) return 60;
  }

  // Fuzzy character matching (all query chars present in order)
  let queryIdx = 0;
  for (let i = 0; i < textLower.length && queryIdx < queryLower.length; i++) {
    if (textLower[i] === queryLower[queryIdx]) {
      queryIdx++;
    }
  }
  if (queryIdx === queryLower.length) {
    return 30; // All characters found in order
  }

  return 0; // No match
}

/**
 * Escape special regex characters
 */
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Highlight matching portion of text
 */
function highlightMatch(text, query) {
  if (!query) return escapeHtml(text);

  const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
  const parts = text.split(regex);

  return parts.map(part => {
    if (part.toLowerCase() === query.toLowerCase()) {
      return `<span class="autocomplete-match">${escapeHtml(part)}</span>`;
    }
    return escapeHtml(part);
  }).join('');
}

/**
 * Add an ingredient to the selected list
 */
function addSelectedIngredient(ingredient) {
  if (selectedIngredients.includes(ingredient)) return;

  selectedIngredients.push(ingredient);
  renderSelectedIngredients();
}

/**
 * Remove an ingredient from the selected list
 */
function removeSelectedIngredient(ingredient) {
  selectedIngredients = selectedIngredients.filter(i => i !== ingredient);
  renderSelectedIngredients();
  performIngredientSearch();
}

/**
 * Render the selected ingredients pills
 */
function renderSelectedIngredients() {
  const container = document.getElementById('selected-ingredients');
  if (!container) return;

  if (selectedIngredients.length === 0) {
    container.classList.add('hidden');
    container.innerHTML = '';
    return;
  }

  container.classList.remove('hidden');
  container.innerHTML = selectedIngredients.map(ing => `
    <span class="ingredient-pill">
      ${escapeHtml(ing)}
      <button type="button" class="ingredient-pill-remove" data-ingredient="${escapeAttr(ing)}" aria-label="Remove ${escapeAttr(ing)}">
        &times;
      </button>
    </span>
  `).join('');

  // Add remove handlers
  container.querySelectorAll('.ingredient-pill-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      removeSelectedIngredient(btn.dataset.ingredient);
    });
  });
}

/**
 * Clear the ingredient search
 */
function clearIngredientSearch() {
  selectedIngredients = [];
  searchKeywords = [];
  renderSelectedIngredients();

  const input = document.getElementById('ingredient-input');
  if (input) input.value = '';

  const resultsDiv = document.getElementById('ingredient-search-results');
  if (resultsDiv) resultsDiv.classList.add('hidden');

  // Show regular recipe grid again
  const recipeGrid = document.getElementById('recipe-grid');
  if (recipeGrid) recipeGrid.classList.remove('hidden');

  // Clear ingredient recipe list
  const recipeList = document.getElementById('ingredient-recipe-list');
  if (recipeList) recipeList.innerHTML = '';

  // Reset just staples mode
  justStaplesMode = false;
  const justStaplesBtn = document.getElementById('just-staples-btn');
  if (justStaplesBtn) {
    justStaplesBtn.classList.remove('active');
    justStaplesBtn.textContent = 'Just Staples';
  }

  // Reset current filter's ingredient state
  currentFilter.ingredients = [];
  currentFilter.ingredientMatchInfo = null;
  currentFilter.keywords = [];

  renderRecipeGrid();
}

/**
 * Perform the ingredient-based recipe search
 */
function performIngredientSearch() {
  // Get effective ingredients (selected + staples if enabled, or just staples in that mode)
  const effectiveIngredients = getEffectiveIngredients();

  if (effectiveIngredients.length === 0 && !justStaplesMode) {
    clearIngredientSearch();
    return;
  }

  // Find matching recipes
  const matchInfo = findRecipesByIngredients(
    effectiveIngredients,
    ingredientSearchOptions.matchMode,
    ingredientSearchOptions.missingThreshold
  );

  // Store match info for use in rendering
  currentFilter.ingredients = effectiveIngredients;
  currentFilter.ingredientMatchInfo = matchInfo;

  // Update results summary
  updateIngredientSearchResults(matchInfo);

  // Calculate and display suggestions
  calculateAndDisplaySuggestions(effectiveIngredients, matchInfo);

  // Re-render the recipe grid
  renderRecipeGrid();
}

/**
 * Find recipes that match the selected ingredients
 * Now also considers substitutions - if user has A and recipe needs B (where A can substitute for B),
 * it counts as a match with substitution info tracked
 */
function findRecipesByIngredients(ingredients, matchMode, missingThreshold) {
  if (!ingredientIndex || ingredients.length === 0) {
    return { matches: [], perfectMatches: 0, partialMatches: 0 };
  }

  // Use ingredientIndex to find recipes (works with sharded data)
  // ingredientIndex.ingredients maps ingredient names to recipe IDs
  const ingredientData = ingredientIndex.ingredients || {};

  // Build a map of recipeId -> { matchCount, matchedIngredients, missingIngredients }
  const recipeMatches = new Map();

  // Pre-build a list of all ingredient keys for partial matching (only once)
  const allIngredientKeys = Object.keys(ingredientData);

  for (const selectedIng of ingredients) {
    const normalizedSelected = normalizeIngredientName(selectedIng);
    const canonical = getCanonicalName(normalizedSelected);

    // Find all recipe IDs that contain this ingredient
    const matchingRecipeIds = new Set();

    // 1. Try direct lookup first (O(1))
    if (ingredientData[normalizedSelected]) {
      for (const recipeId of ingredientData[normalizedSelected]) {
        matchingRecipeIds.add(recipeId);
      }
    }

    // 2. Try canonical name lookup
    if (ingredientData[canonical] && canonical !== normalizedSelected) {
      for (const recipeId of ingredientData[canonical]) {
        matchingRecipeIds.add(recipeId);
      }
    }

    // 3. Only do partial matching if no exact matches found and search term is specific enough
    if (matchingRecipeIds.size === 0 && normalizedSelected.length >= 3) {
      // Limit partial matching to avoid performance issues
      for (const ingName of allIngredientKeys) {
        if (ingName.includes(normalizedSelected) || normalizedSelected.includes(ingName)) {
          for (const recipeId of ingredientData[ingName]) {
            matchingRecipeIds.add(recipeId);
          }
        }
        // Stop if we have enough matches to avoid browser crash
        if (matchingRecipeIds.size > 5000) break;
      }
    }

    // Update recipe match info
    for (const recipeId of matchingRecipeIds) {
      if (!recipeMatches.has(recipeId)) {
        recipeMatches.set(recipeId, {
          matchCount: 0,
          matchedIngredients: [],
          missingIngredients: [],
          substitutionMatches: []
        });
      }
      const info = recipeMatches.get(recipeId);
      info.matchCount++;
      info.matchedIngredients.push(selectedIng);
    }
  }

  // Mark missing ingredients for each recipe
  for (const [recipeId, info] of recipeMatches) {
    for (const selectedIng of ingredients) {
      if (!info.matchedIngredients.includes(selectedIng)) {
        info.missingIngredients.push(selectedIng);
      }
    }
  }

  // Filter recipes based on match mode and threshold
  const results = [];

  // Build a Set of valid recipe IDs for fast lookup
  const validRecipeIds = new Set(recipes.map(r => r.id));

  // Get selected collections for filtering
  const selectedCollections = currentFilter.collections || [];

  for (const [recipeId, info] of recipeMatches) {
    // Skip recipes not in local index (ingredient index may have more)
    if (!validRecipeIds.has(recipeId)) continue;

    // Skip variants (check in lightweight index)
    const recipe = recipes.find(r => r.id === recipeId);
    if (recipe && recipe.variant_of && recipe.variant_of !== recipe.id) continue;

    // Filter by selected collections
    if (selectedCollections.length > 0 && recipe) {
      if (!selectedCollections.includes(recipe.collection)) continue;
    }

    let isMatch = false;
    if (matchMode === 'any') {
      // "Any" mode: at least one ingredient matches
      isMatch = info.matchCount > 0;
    } else {
      // "All" mode: all selected ingredients must match (minus threshold)
      const requiredMatches = Math.max(1, ingredients.length - missingThreshold);
      isMatch = info.matchCount >= requiredMatches;
    }

    if (isMatch) {
      results.push({
        recipeId: recipeId,
        matchCount: info.matchCount,
        totalSelected: ingredients.length,
        matchedIngredients: info.matchedIngredients,
        missingIngredients: info.missingIngredients,
        substitutionMatches: info.substitutionMatches,
        hasSubstitutions: info.substitutionMatches.length > 0,
        isPerfectMatch: info.matchCount === ingredients.length
      });
    }
  }

  // Sort by match count (descending), then by recipe title
  results.sort((a, b) => {
    if (b.matchCount !== a.matchCount) return b.matchCount - a.matchCount;
    const recipeA = recipes.find(r => r.id === a.recipeId);
    const recipeB = recipes.find(r => r.id === b.recipeId);
    return (recipeA?.title || '').localeCompare(recipeB?.title || '');
  });

  const perfectMatches = results.filter(r => r.isPerfectMatch).length;
  const partialMatches = results.filter(r => !r.isPerfectMatch).length;

  return {
    matches: results,
    perfectMatches: perfectMatches,
    partialMatches: partialMatches
  };
}

/**
 * Normalize an ingredient name for matching
 */
function normalizeIngredientName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .replace(/[,()]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Update the ingredient search results display
 */
function updateIngredientSearchResults(matchInfo) {
  const resultsDiv = document.getElementById('ingredient-search-results');
  const countSpan = document.getElementById('ingredient-match-count');
  const recipeGrid = document.getElementById('recipe-grid');

  if (!resultsDiv || !countSpan) return;

  const total = matchInfo.matches.length;

  // Store matches for pagination
  currentIngredientMatches = matchInfo.matches;
  ingredientResultsShown = 0;

  // Hide regular recipe grid when showing PWA results
  if (recipeGrid) {
    recipeGrid.classList.add('hidden');
  }

  if (total === 0) {
    countSpan.innerHTML = 'No recipes found with those ingredients';
    // Clear recipe list
    const recipeList = document.getElementById('ingredient-recipe-list');
    if (recipeList) recipeList.innerHTML = '';
    const loadMoreContainer = document.getElementById('load-more-container');
    if (loadMoreContainer) loadMoreContainer.classList.add('hidden');
  } else {
    let text = `Found <span class="match-count-number">${total}</span> recipe${total !== 1 ? 's' : ''}`;

    if (matchInfo.perfectMatches > 0 && matchInfo.partialMatches > 0) {
      text += ` (${matchInfo.perfectMatches} perfect match${matchInfo.perfectMatches !== 1 ? 'es' : ''}, ${matchInfo.partialMatches} partial)`;
    }

    countSpan.innerHTML = text;

    // Render the recipe list
    renderIngredientRecipeList();
  }

  resultsDiv.classList.remove('hidden');
}

/**
 * Render the ingredient recipe list with pagination
 */
function renderIngredientRecipeList() {
  const recipeList = document.getElementById('ingredient-recipe-list');
  const loadMoreContainer = document.getElementById('load-more-container');
  const loadMoreStatus = document.getElementById('load-more-status');

  if (!recipeList) return;

  // Sort matches: perfect matches first, then by match percentage
  const sortedMatches = [...currentIngredientMatches].sort((a, b) => {
    // Perfect matches first
    if (a.isPerfectMatch && !b.isPerfectMatch) return -1;
    if (!a.isPerfectMatch && b.isPerfectMatch) return 1;
    // Then by match percentage
    return b.matchPercent - a.matchPercent;
  });

  // Determine how many to show
  const endIndex = Math.min(ingredientResultsShown + ingredientResultsPageSize, sortedMatches.length);
  const recipesToShow = sortedMatches.slice(ingredientResultsShown, endIndex);

  // If starting fresh, clear the list
  if (ingredientResultsShown === 0) {
    recipeList.innerHTML = '';
  }

  // Render each recipe card
  recipesToShow.forEach(match => {
    const recipe = recipes.find(r => r.id === match.recipeId);
    if (!recipe) return;

    const card = createIngredientResultCard(recipe, match);
    recipeList.appendChild(card);
  });

  // Update shown count
  ingredientResultsShown = endIndex;

  // Update load more button
  if (loadMoreContainer && loadMoreStatus) {
    const remaining = sortedMatches.length - ingredientResultsShown;
    if (remaining > 0) {
      loadMoreContainer.classList.remove('hidden');
      loadMoreStatus.textContent = `Showing ${ingredientResultsShown} of ${sortedMatches.length}`;
    } else {
      loadMoreContainer.classList.add('hidden');
    }
  }
}

/**
 * Load more ingredient search results
 */
function loadMoreIngredientResults() {
  renderIngredientRecipeList();
}

/**
 * Check if an ingredient is a common pantry staple
 */
function isCommonPantryStaple(ingredient) {
  const normalized = ingredient.toLowerCase().trim();
  // Check exact match first
  if (COMMON_PANTRY_STAPLES.has(normalized)) return true;
  // Check if any common staple appears as a word in the ingredient
  for (const staple of COMMON_PANTRY_STAPLES) {
    // Match as whole word (not part of another word like "assault")
    const regex = new RegExp(`\\b${staple}\\b`, 'i');
    if (regex.test(normalized)) return true;
  }
  return false;
}

/**
 * Filter out common pantry staples from an ingredient list
 */
function filterOutCommonStaples(ingredients) {
  return ingredients.filter(ing => !isCommonPantryStaple(ing));
}

/**
 * Create a recipe result card for ingredient search
 */
function createIngredientResultCard(recipe, match) {
  const card = document.createElement('div');
  card.className = 'ingredient-result-card';
  if (match.isPerfectMatch) {
    card.classList.add('perfect-match');
  }

  // Get image path - check if recipe has images
  const hasImage = recipe.image_refs && recipe.image_refs.length > 0;
  const imageSrc = hasImage ? `data/${recipe.image_refs[0]}` : null;

  // Build match info display
  let matchInfo = '';
  if (match.isPerfectMatch) {
    matchInfo = '<span class="match-badge perfect">Perfect Match</span>';
  } else {
    matchInfo = `<span class="match-badge partial">${match.matchedCount}/${match.totalInRecipe} ingredients</span>`;
  }

  // Filter out common pantry staples from display (they add noise)
  const displayMatched = filterOutCommonStaples(match.matchedIngredients);
  const displayMissing = filterOutCommonStaples(match.missingIngredients || []);

  // Show matched ingredients (excluding common staples)
  const matchedList = displayMatched
    .slice(0, 5)
    .map(ing => escapeHtml(ing))
    .join(', ');
  const moreMatched = displayMatched.length > 5
    ? ` +${displayMatched.length - 5} more`
    : '';

  // Show missing ingredients if any (excluding common staples)
  let missingHtml = '';
  if (displayMissing.length > 0) {
    const missingList = displayMissing
      .slice(0, 3)
      .map(ing => escapeHtml(ing))
      .join(', ');
    const moreMissing = displayMissing.length > 3
      ? ` +${displayMissing.length - 3} more`
      : '';
    missingHtml = `<div class="missing-ingredients">Missing: ${missingList}${moreMissing}</div>`;
  }

  // Show substitution info if any
  let substitutionHtml = '';
  if (match.substitutionMatches && match.substitutionMatches.length > 0) {
    const subList = match.substitutionMatches
      .slice(0, 2)
      .map(s => `${escapeHtml(s.userHas)} → ${escapeHtml(s.recipeNeeds)}`)
      .join(', ');
    substitutionHtml = `<div class="substitution-info">Substitutions: ${subList}</div>`;
  }

  card.innerHTML = `
    <div class="result-card-image${hasImage ? '' : ' no-image'}">
      ${hasImage ? `<img src="${escapeAttr(imageSrc)}" alt="${escapeAttr(recipe.title)}" loading="lazy"
           onerror="this.parentElement.classList.add('no-image'); this.style.display='none';">` : ''}
    </div>
    <div class="result-card-content">
      <div class="result-card-header">
        <h4 class="result-card-title">${escapeHtml(recipe.title)}</h4>
        ${matchInfo}
      </div>
      <div class="result-card-category">${escapeHtml(recipe.category || 'Uncategorized')}</div>
      ${displayMatched.length > 0 ? `<div class="matched-ingredients">Have: ${matchedList}${moreMatched}</div>` : ''}
      ${missingHtml}
      ${substitutionHtml}
      <a href="recipe.html?id=${escapeAttr(recipe.id)}" class="result-card-link">View Recipe</a>
    </div>
  `;

  return card;
}

// =============================================================================
// Smart Suggestions Engine
// =============================================================================

/**
 * Calculate and display ingredient suggestions
 */
function calculateAndDisplaySuggestions(currentIngredients, matchInfo) {
  const suggestionsPanel = document.getElementById('ingredient-suggestions');
  const addSuggestionsDiv = document.getElementById('add-suggestions');
  const addSuggestionsList = document.getElementById('add-suggestions-list');
  const removeSuggestionsDiv = document.getElementById('remove-suggestions');
  const removeSuggestionsList = document.getElementById('remove-suggestions-list');

  if (!suggestionsPanel || !addSuggestionsDiv || !removeSuggestionsDiv) return;

  // Only show suggestions if we have at least one ingredient selected
  if (currentIngredients.length === 0) {
    suggestionsPanel.classList.add('hidden');
    return;
  }

  // Calculate add suggestions (ingredients that would unlock more recipes)
  const addSuggestions = calculateAddSuggestions(currentIngredients, matchInfo, 5);

  // Calculate remove suggestions (selected ingredients blocking matches)
  const removeSuggestions = calculateRemoveSuggestions(currentIngredients, 3);

  // Render add suggestions
  if (addSuggestions.length > 0) {
    addSuggestionsList.innerHTML = addSuggestions.map(s => `
      <button type="button" class="suggestion-add-chip" data-ingredient="${escapeAttr(s.ingredient)}">
        +${escapeHtml(s.ingredient)} <span class="chip-count">(${s.newRecipes} more)</span>
      </button>
    `).join('');

    // Add click handlers
    addSuggestionsList.querySelectorAll('.suggestion-add-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const ingredient = chip.dataset.ingredient;
        if (!selectedIngredients.includes(ingredient)) {
          addSelectedIngredient(ingredient);
          performIngredientSearch();
        }
      });
    });

    addSuggestionsDiv.classList.remove('hidden');
  } else {
    addSuggestionsDiv.classList.add('hidden');
  }

  // Render remove suggestions
  if (removeSuggestions.length > 0 && selectedIngredients.length > 1) {
    removeSuggestionsList.innerHTML = removeSuggestions.map(s => `
      <button type="button" class="suggestion-remove-chip" data-ingredient="${escapeAttr(s.ingredient)}">
        -${escapeHtml(s.ingredient)} <span class="chip-count">(${s.newRecipes} more)</span>
      </button>
    `).join('');

    // Add click handlers
    removeSuggestionsList.querySelectorAll('.suggestion-remove-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const ingredient = chip.dataset.ingredient;
        removeSelectedIngredient(ingredient);
      });
    });

    removeSuggestionsDiv.classList.remove('hidden');
  } else {
    removeSuggestionsDiv.classList.add('hidden');
  }

  // Show panel if either has suggestions
  if (addSuggestions.length > 0 || (removeSuggestions.length > 0 && selectedIngredients.length > 1)) {
    suggestionsPanel.classList.remove('hidden');
  } else {
    suggestionsPanel.classList.add('hidden');
  }
}

/**
 * Calculate ingredients that would unlock the most new recipes if added
 */
function calculateAddSuggestions(currentIngredients, matchInfo, limit = 5) {
  if (!ingredientIndex) return [];

  const currentMatches = new Set(matchInfo.matches.map(m => m.recipeId));
  const ingredientGains = {};

  // Look at recipes we're NOT currently matching
  for (const recipe of recipes) {
    if (recipe.variant_of && recipe.variant_of !== recipe.id) continue;
    if (currentMatches.has(recipe.id)) continue; // Already matching

    const recipeIngredients = recipe.ingredients || [];

    // Check what ingredients this recipe needs that we don't have
    for (const ing of recipeIngredients) {
      const normalized = normalizeIngredientName(ing.item);

      // Skip if we already have this ingredient
      if (currentIngredients.some(ci => {
        const ciNorm = normalizeIngredientName(ci);
        return ciNorm === normalized || normalized.includes(ciNorm) || ciNorm.includes(normalized);
      })) continue;

      // Check if adding this ingredient would make a match
      // (simplified: count how many recipes contain this ingredient that we don't match)
      if (!ingredientGains[normalized]) {
        ingredientGains[normalized] = new Set();
      }
      ingredientGains[normalized].add(recipe.id);
    }
  }

  // Convert to array and sort by number of new recipes
  const suggestions = Object.entries(ingredientGains)
    .map(([ingredient, recipeSet]) => ({
      ingredient,
      newRecipes: recipeSet.size
    }))
    .filter(s => s.newRecipes >= 2) // Only suggest if it unlocks at least 2 recipes
    .sort((a, b) => b.newRecipes - a.newRecipes)
    .slice(0, limit);

  return suggestions;
}

/**
 * Calculate selected ingredients that if removed would unlock more recipes
 */
function calculateRemoveSuggestions(currentIngredients, limit = 3) {
  if (currentIngredients.length <= 1) return [];

  const suggestions = [];

  // For each selected ingredient, calculate how many more recipes we'd match without it
  for (const ingredient of currentIngredients) {
    // Skip staples (don't suggest removing them)
    if (userStaples.includes(ingredient)) continue;

    // Only consider user-selected ingredients, not auto-included staples
    if (!selectedIngredients.includes(ingredient)) continue;

    const withoutThis = currentIngredients.filter(i => i !== ingredient);

    if (withoutThis.length === 0) continue;

    // Calculate matches without this ingredient
    const matchInfo = findRecipesByIngredients(
      withoutThis,
      ingredientSearchOptions.matchMode,
      ingredientSearchOptions.missingThreshold
    );

    const currentMatchCount = currentFilter.ingredientMatchInfo?.matches.length || 0;
    const newMatchCount = matchInfo.matches.length;
    const gain = newMatchCount - currentMatchCount;

    if (gain > 0) {
      suggestions.push({
        ingredient,
        newRecipes: gain
      });
    }
  }

  // Sort by gain and limit
  return suggestions
    .sort((a, b) => b.newRecipes - a.newRecipes)
    .slice(0, limit);
}

// =============================================================================
// Staples System Functions
// =============================================================================

/**
 * Setup the staples system UI and event listeners
 */
function setupStaplesSystem() {
  // Load saved staples from localStorage
  loadStaples();

  const includeStaplesCheckbox = document.getElementById('include-staples');
  const justStaplesBtn = document.getElementById('just-staples-btn');
  const editStaplesBtn = document.getElementById('edit-staples-btn');
  const staplesEditor = document.getElementById('staples-editor');
  const staplesInput = document.getElementById('staples-input');
  const addStapleBtn = document.getElementById('add-staple-btn');
  const clearStaplesBtn = document.getElementById('clear-staples-btn');
  const closeStaplesBtn = document.getElementById('close-staples-btn');

  if (!includeStaplesCheckbox) return; // Not on a page with staples

  // Include staples toggle
  includeStaplesCheckbox.checked = includeStaples;
  includeStaplesCheckbox.addEventListener('change', (e) => {
    includeStaples = e.target.checked;
    saveStaplesPreferences();
    if (selectedIngredients.length > 0 || justStaplesMode) {
      performIngredientSearch();
    }
  });

  // Just staples mode button
  if (justStaplesBtn) {
    justStaplesBtn.addEventListener('click', toggleJustStaplesMode);
  }

  // Edit staples button
  if (editStaplesBtn && staplesEditor) {
    editStaplesBtn.addEventListener('click', () => {
      staplesEditor.classList.toggle('hidden');
      editStaplesBtn.textContent = staplesEditor.classList.contains('hidden') ? 'Edit Staples' : 'Hide Editor';
    });
  }

  // Close staples editor
  if (closeStaplesBtn && staplesEditor) {
    closeStaplesBtn.addEventListener('click', () => {
      staplesEditor.classList.add('hidden');
      if (editStaplesBtn) editStaplesBtn.textContent = 'Edit Staples';
    });
  }

  // Add staple input
  if (staplesInput && addStapleBtn) {
    addStapleBtn.addEventListener('click', () => {
      const value = staplesInput.value.trim().toLowerCase();
      if (value && !userStaples.includes(value)) {
        addStaple(value);
        staplesInput.value = '';
      }
    });

    staplesInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const value = staplesInput.value.trim().toLowerCase();
        if (value && !userStaples.includes(value)) {
          addStaple(value);
          staplesInput.value = '';
        }
      }
    });
  }

  // Clear all staples
  if (clearStaplesBtn) {
    clearStaplesBtn.addEventListener('click', () => {
      if (confirm('Clear all staples? This cannot be undone.')) {
        userStaples = [];
        saveStaples();
        renderStaplesList();
        updateStaplesCount();
      }
    });
  }

  // Preset buttons
  document.querySelectorAll('.preset-btn[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.dataset.preset;
      if (STAPLES_PRESETS[preset]) {
        addPresetStaples(preset);
      }
    });
  });

  // Initial render
  renderStaplesList();
  updateStaplesCount();
}

/**
 * Toggle "Just Staples" mode
 */
function toggleJustStaplesMode() {
  const justStaplesBtn = document.getElementById('just-staples-btn');

  justStaplesMode = !justStaplesMode;

  if (justStaplesBtn) {
    justStaplesBtn.classList.toggle('active', justStaplesMode);
    justStaplesBtn.textContent = justStaplesMode ? 'Exit Just Staples' : 'Just Staples';
  }

  if (justStaplesMode) {
    // In "just staples" mode, we search with only staples as ingredients
    performIngredientSearch();
  } else {
    // Exit just staples mode
    if (selectedIngredients.length === 0) {
      clearIngredientSearch();
    } else {
      performIngredientSearch();
    }
  }
}

/**
 * Add a single staple
 */
function addStaple(ingredient) {
  const normalized = ingredient.toLowerCase().trim();
  if (!userStaples.includes(normalized)) {
    userStaples.push(normalized);
    userStaples.sort();
    saveStaples();
    renderStaplesList();
    updateStaplesCount();
  }
}

/**
 * Remove a staple
 */
function removeStaple(ingredient) {
  userStaples = userStaples.filter(s => s !== ingredient);
  saveStaples();
  renderStaplesList();
  updateStaplesCount();
}

/**
 * Add preset staples bundle
 */
function addPresetStaples(presetName) {
  const preset = STAPLES_PRESETS[presetName];
  if (!preset) return;

  let addedCount = 0;
  preset.forEach(ingredient => {
    const normalized = ingredient.toLowerCase().trim();
    if (!userStaples.includes(normalized)) {
      userStaples.push(normalized);
      addedCount++;
    }
  });

  if (addedCount > 0) {
    userStaples.sort();
    saveStaples();
    renderStaplesList();
    updateStaplesCount();
  }
}

/**
 * Render the staples list in the editor
 */
function renderStaplesList() {
  const container = document.getElementById('staples-list');
  if (!container) return;

  if (userStaples.length === 0) {
    container.innerHTML = '<span style="opacity: 0.6; font-size: 0.85rem;">No staples yet. Add some above!</span>';
    return;
  }

  container.innerHTML = userStaples.map(staple => `
    <span class="staple-pill">
      ${escapeHtml(staple)}
      <button type="button" class="staple-pill-remove" data-staple="${escapeAttr(staple)}" aria-label="Remove ${escapeAttr(staple)}">
        &times;
      </button>
    </span>
  `).join('');

  // Add remove handlers
  container.querySelectorAll('.staple-pill-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      removeStaple(btn.dataset.staple);
    });
  });
}

/**
 * Update the staples count display
 */
function updateStaplesCount() {
  const countSpan = document.getElementById('staples-count');
  if (countSpan) {
    countSpan.textContent = `(${userStaples.length} item${userStaples.length !== 1 ? 's' : ''})`;
  }
}

/**
 * Save staples to localStorage
 */
function saveStaples() {
  try {
    localStorage.setItem('grandmas-kitchen-staples', JSON.stringify(userStaples));
  } catch (e) {
    console.warn('Could not save staples:', e);
  }
}

/**
 * Load staples from localStorage
 */
function loadStaples() {
  try {
    const saved = localStorage.getItem('grandmas-kitchen-staples');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        userStaples = parsed;
      }
    }

    // Load staples preferences
    const prefs = localStorage.getItem('grandmas-kitchen-staples-prefs');
    if (prefs) {
      const parsed = JSON.parse(prefs);
      if (typeof parsed.includeStaples === 'boolean') {
        includeStaples = parsed.includeStaples;
      }
    }
  } catch (e) {
    console.warn('Could not load staples:', e);
  }
}

/**
 * Save staples preferences
 */
function saveStaplesPreferences() {
  try {
    localStorage.setItem('grandmas-kitchen-staples-prefs', JSON.stringify({
      includeStaples: includeStaples
    }));
  } catch (e) {
    console.warn('Could not save staples preferences:', e);
  }
}

/**
 * Get effective ingredients for search (selected + staples if enabled)
 * Also expands staples using substitution rules when enabled
 */
function getEffectiveIngredients() {
  let staples = [...userStaples];

  // Expand staples with substitution matches if enabled
  if (enableSubstitutions && staples.length > 0) {
    staples = expandStaplesWithSubstitutions(staples);
  }

  if (justStaplesMode) {
    // In "just staples" mode, use only (expanded) staples
    return staples;
  }

  if (includeStaples && staples.length > 0) {
    // Combine selected ingredients with (expanded) staples (no duplicates)
    const combined = [...selectedIngredients];
    staples.forEach(staple => {
      if (!combined.includes(staple)) {
        combined.push(staple);
      }
    });
    return combined;
  }

  return [...selectedIngredients];
}

/**
 * Update collection filter with recipe counts
 */
function updateCollectionCounts() {
  const collectionFilters = document.getElementById('collection-filters');
  if (!collectionFilters) return;

  // Count recipes by collection
  const counts = {
    'grandma-baker': 0,
    'mommom-baker': 0,
    'granny-hudson': 0,
    'all': 0
  };

  recipes.forEach(recipe => {
    // Skip variants
    if (recipe.variant_of && recipe.variant_of !== recipe.id) return;

    const collection = recipe.collection || '';
    if (counts.hasOwnProperty(collection)) {
      counts[collection]++;
    }
  });

  // Update count labels
  Object.keys(counts).forEach(collection => {
    const countSpan = collectionFilters.querySelector(`.collection-count[data-count="${collection}"]`);
    if (countSpan) {
      countSpan.textContent = `(${counts[collection]})`;
    }
  });
}

/**
 * Update the currentFilter.collections array based on checkbox states
 */
function updateCollectionFilter() {
  const collectionFilters = document.getElementById('collection-filters');
  if (!collectionFilters) return;

  const selectedCollections = [];
  collectionFilters.querySelectorAll('input[type="checkbox"][data-collection]:checked').forEach(checkbox => {
    selectedCollections.push(checkbox.dataset.collection);
  });

  currentFilter.collections = selectedCollections;

  // Update Select All button text
  const selectAllBtn = document.getElementById('collection-select-all');
  if (selectAllBtn) {
    const allCheckboxes = collectionFilters.querySelectorAll('input[type="checkbox"][data-collection]');
    const allChecked = Array.from(allCheckboxes).every(cb => cb.checked);
    selectAllBtn.textContent = allChecked ? 'Clear All' : 'Select All';
  }
}

/**
 * Save collection preferences to localStorage
 */
function saveCollectionPreferences() {
  try {
    localStorage.setItem('grandmas-kitchen-collections', JSON.stringify(currentFilter.collections));
  } catch (e) {
    console.warn('Could not save collection preferences:', e);
  }
}

/**
 * Load collection preferences from localStorage
 */
function loadCollectionPreferences() {
  const collectionFilters = document.getElementById('collection-filters');
  if (!collectionFilters) return;

  try {
    const saved = localStorage.getItem('grandmas-kitchen-collections');
    if (saved) {
      const savedCollections = JSON.parse(saved);
      if (Array.isArray(savedCollections)) {
        // Update checkbox states
        collectionFilters.querySelectorAll('input[type="checkbox"][data-collection]').forEach(checkbox => {
          checkbox.checked = savedCollections.includes(checkbox.dataset.collection);
        });
        currentFilter.collections = savedCollections;
      }
    }
  } catch (e) {
    console.warn('Could not load collection preferences:', e);
  }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Search form
  const searchForm = document.getElementById('search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const query = document.getElementById('search-input').value;
      currentFilter.search = query.toLowerCase();
      // Try Pagefind for better results
      pagefindSearchResults = await searchWithPagefind(query);
      renderRecipeGrid();
    });
  }

  // Search input (live search with Pagefind)
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', debounce(async (e) => {
      const query = e.target.value;
      currentFilter.search = query.toLowerCase();
      // Try Pagefind for better results (searches ingredients too)
      pagefindSearchResults = await searchWithPagefind(query);
      renderRecipeGrid();
    }, 300));
  }

  // Category filter
  const categorySelect = document.getElementById('category-filter');
  if (categorySelect) {
    categorySelect.addEventListener('change', (e) => {
      currentFilter.category = e.target.value;
      renderRecipeGrid();
    });
  }

  // Print button
  const printBtn = document.getElementById('print-btn');
  if (printBtn) {
    printBtn.addEventListener('click', () => window.print());
  }

  // Collection filter checkboxes (multi-select)
  const collectionFilters = document.getElementById('collection-filters');
  if (collectionFilters) {
    // Load saved collection preferences from localStorage
    loadCollectionPreferences();

    // Handle checkbox changes
    collectionFilters.querySelectorAll('input[type="checkbox"][data-collection]').forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        updateCollectionFilter();
        saveCollectionPreferences();
        renderTagFilters();  // Update tags for selected collections
        renderRecipeGrid();
      });
    });

    // Handle "Select All" button
    const selectAllBtn = document.getElementById('collection-select-all');
    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', () => {
        const checkboxes = collectionFilters.querySelectorAll('input[type="checkbox"][data-collection]');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);

        // Toggle: if all checked, uncheck all; otherwise check all
        checkboxes.forEach(cb => {
          cb.checked = !allChecked;
        });

        // Update button text
        selectAllBtn.textContent = allChecked ? 'Select All' : 'Clear All';

        updateCollectionFilter();
        saveCollectionPreferences();
        renderRecipeGrid();
      });
    }

    // Initial update of collection filter
    updateCollectionFilter();
  }

  // Tags toggle (collapsible)
  const tagsToggle = document.getElementById('tags-toggle');
  const tagFilters = document.getElementById('tag-filters');
  if (tagsToggle && tagFilters) {
    tagsToggle.addEventListener('click', () => {
      const isExpanded = tagsToggle.getAttribute('aria-expanded') === 'true';
      tagsToggle.setAttribute('aria-expanded', !isExpanded);
      tagFilters.classList.toggle('collapsed', isExpanded);
    });
  }

  // Keyboard shortcuts
  setupKeyboardShortcuts();

  // Load URL state (filters from URL params)
  loadUrlState();

  // Load favorites and recently viewed
  loadFavorites();
}

// =============================================================================
// Keyboard Shortcuts
// =============================================================================

/**
 * Setup keyboard shortcuts for navigation
 */
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Don't trigger shortcuts when typing in input fields
    if (e.target.matches('input, textarea, select')) return;

    switch (e.key) {
      case '/':
        // Focus search input
        e.preventDefault();
        const searchInput = document.getElementById('search-input') ||
                           document.getElementById('ingredient-input');
        if (searchInput) {
          searchInput.focus();
        }
        break;

      case '?':
        // Show keyboard shortcuts help
        if (!e.shiftKey) break;
        e.preventDefault();
        showKeyboardShortcutsHelp();
        break;

      case 'Escape':
        // Clear search/close modals
        const activeElement = document.activeElement;
        if (activeElement && activeElement.matches('input')) {
          activeElement.blur();
        }
        hideAutocomplete();
        break;

      case 'h':
        // Go to home
        if (!e.ctrlKey && !e.metaKey) {
          window.location.href = 'index.html';
        }
        break;

      case 'r':
        // Random recipe
        if (!e.ctrlKey && !e.metaKey) {
          showRandomRecipe();
        }
        break;
    }
  });
}

/**
 * Show keyboard shortcuts help modal
 */
function showKeyboardShortcutsHelp() {
  const existing = document.querySelector('.shortcuts-modal');
  if (existing) {
    existing.remove();
    return;
  }

  const modal = document.createElement('div');
  modal.className = 'shortcuts-modal';
  modal.innerHTML = `
    <div class="shortcuts-content">
      <h3>Keyboard Shortcuts</h3>
      <ul>
        <li><kbd>/</kbd> Focus search</li>
        <li><kbd>Esc</kbd> Clear focus / close</li>
        <li><kbd>h</kbd> Go to home</li>
        <li><kbd>r</kbd> Random recipe</li>
        <li><kbd>Shift</kbd> + <kbd>?</kbd> Show this help</li>
      </ul>
      <button class="btn btn-small" onclick="this.closest('.shortcuts-modal').remove()">Close</button>
    </div>
  `;
  document.body.appendChild(modal);

  // Close on click outside
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });
}

/**
 * Show a random recipe
 */
function showRandomRecipe() {
  if (recipes.length === 0) return;

  // Filter to canonical recipes only
  const canonical = recipes.filter(r => !r.variant_of || r.variant_of === r.id);
  const random = canonical[Math.floor(Math.random() * canonical.length)];

  if (random) {
    window.location.href = `recipe.html#${random.id}`;
  }
}

// =============================================================================
// Favorites System
// =============================================================================

const FAVORITES_KEY = 'grandmas-kitchen-favorites';
const RECENTLY_VIEWED_KEY = 'grandmas-kitchen-recent';
let favorites = [];
let recentlyViewed = [];

/**
 * Load favorites from localStorage
 */
function loadFavorites() {
  try {
    const saved = localStorage.getItem(FAVORITES_KEY);
    favorites = saved ? JSON.parse(saved) : [];

    const recent = localStorage.getItem(RECENTLY_VIEWED_KEY);
    recentlyViewed = recent ? JSON.parse(recent) : [];
  } catch (e) {
    favorites = [];
    recentlyViewed = [];
  }
}

/**
 * Save favorites to localStorage
 */
function saveFavorites() {
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
  } catch (e) {
    console.error('Failed to save favorites:', e);
  }
}

/**
 * Toggle favorite status for a recipe
 * @param {string} recipeId - The recipe ID
 */
function toggleFavorite(recipeId) {
  const index = favorites.indexOf(recipeId);
  if (index > -1) {
    favorites.splice(index, 1);
  } else {
    favorites.push(recipeId);
  }
  saveFavorites();
  return favorites.includes(recipeId);
}

/**
 * Check if recipe is a favorite
 * @param {string} recipeId - The recipe ID
 * @returns {boolean}
 */
function isFavorite(recipeId) {
  return favorites.includes(recipeId);
}

/**
 * Add recipe to recently viewed
 * @param {string} recipeId - The recipe ID
 */
function addToRecentlyViewed(recipeId) {
  // Remove if already exists
  recentlyViewed = recentlyViewed.filter(id => id !== recipeId);
  // Add to front
  recentlyViewed.unshift(recipeId);
  // Keep only last 10
  recentlyViewed = recentlyViewed.slice(0, 10);

  try {
    localStorage.setItem(RECENTLY_VIEWED_KEY, JSON.stringify(recentlyViewed));
  } catch (e) {
    console.error('Failed to save recently viewed:', e);
  }
}

/**
 * Get recently viewed recipes
 * @returns {Array} - Array of recipe objects
 */
function getRecentlyViewed() {
  return recentlyViewed
    .map(id => recipes.find(r => r.id === id))
    .filter(Boolean);
}

// Make favorites functions available globally
window.toggleFavorite = toggleFavorite;
window.isFavorite = isFavorite;

// =============================================================================
// URL State Management
// =============================================================================

/**
 * Load filter state from URL parameters
 */
function loadUrlState() {
  const params = new URLSearchParams(window.location.search);

  // Search query
  const q = params.get('q');
  if (q) {
    currentFilter.search = q.toLowerCase();
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.value = q;
  }

  // Category
  const cat = params.get('cat');
  if (cat) {
    currentFilter.category = cat;
    const categorySelect = document.getElementById('category-filter');
    if (categorySelect) categorySelect.value = cat;
  }

  // Ingredients
  const ing = params.get('ing');
  if (ing) {
    selectedIngredients = ing.split(',').map(i => i.trim()).filter(Boolean);
    renderSelectedIngredients();
  }

  // Diet preset
  const diet = params.get('diet');
  if (diet && DIET_PRESETS[diet]) {
    applyDietPreset(diet);
  }

  // Time filter
  const time = params.get('time');
  if (time) {
    nutritionFilter.timeLimit = parseInt(time, 10);
    const timeSelect = document.getElementById('time-filter');
    if (timeSelect) timeSelect.value = time;
  }
}

/**
 * Update URL with current filter state (without reloading)
 */
function updateUrlState() {
  const params = new URLSearchParams();

  if (currentFilter.search) params.set('q', currentFilter.search);
  if (currentFilter.category) params.set('cat', currentFilter.category);
  if (selectedIngredients.length > 0) params.set('ing', selectedIngredients.join(','));
  if (nutritionFilter.activeDietPreset) params.set('diet', nutritionFilter.activeDietPreset);
  if (nutritionFilter.timeLimit) params.set('time', nutritionFilter.timeLimit);

  const newUrl = params.toString()
    ? `${window.location.pathname}?${params.toString()}`
    : window.location.pathname;

  window.history.replaceState({}, '', newUrl);
}

/**
 * Handle client-side routing based on URL hash
 */
function handleRouting() {
  const path = window.location.pathname;
  const hash = window.location.hash;

  if (path.includes('recipe.html') && hash) {
    const recipeId = hash.slice(1);
    renderRecipeDetail(recipeId);
  } else if (path.includes('index.html') || path.endsWith('/')) {
    renderHomePage();
  }
}

/**
 * Render home page with recipe grid
 */
function renderHomePage() {
  renderCategoryFilter();
  renderTagFilters();
  renderRecipeGrid();
}

/**
 * Render category filter dropdown
 */
function renderCategoryFilter() {
  const select = document.getElementById('category-filter');
  if (!select) return;

  const sortedCategories = Array.from(categories).sort();
  let html = '<option value="">All Categories</option>';

  sortedCategories.forEach(cat => {
    html += `<option value="${escapeAttr(cat)}">${escapeHtml(capitalizeFirst(cat))}</option>`;
  });

  select.innerHTML = html;
}

/**
 * Get tags for selected collections from ingredient index
 */
function getTagsForSelectedCollections() {
  const selectedCollections = currentFilter.collections || [];
  const tags = new Set();

  // If no ingredient index, fall back to local allTags
  if (!ingredientIndex || !ingredientIndex.meta.collections) {
    return Array.from(allTags).sort();
  }

  // Map UI collection IDs to index collection IDs
  const collectionIdMap = {
    'grandma-baker': 'grandma-baker',
    'mommom': 'mommom-baker',
    'granny': 'granny-hudson',
    'all': 'all'
  };

  // Gather tags from selected collections
  for (const uiId of selectedCollections) {
    const indexId = collectionIdMap[uiId] || uiId;
    const collectionInfo = ingredientIndex.meta.collections[indexId];
    if (collectionInfo && collectionInfo.tags) {
      collectionInfo.tags.forEach(tag => tags.add(tag));
    }
  }

  // If no tags found (perhaps index not loaded), fall back to local
  if (tags.size === 0) {
    return Array.from(allTags).sort();
  }

  return Array.from(tags).sort();
}

/**
 * Render tag filter buttons based on selected collections
 */
function renderTagFilters() {
  const container = document.getElementById('tag-filters');
  if (!container) return;

  const sortedTags = getTagsForSelectedCollections();
  const currentTag = currentFilter.tag;

  // Clear current tag filter if it's no longer in available tags
  if (currentTag && !sortedTags.includes(currentTag.toLowerCase())) {
    currentFilter.tag = '';
  }

  let html = '';
  if (sortedTags.length === 0) {
    html = '<span class="no-tags">No tags available for selected collections</span>';
  } else {
    sortedTags.forEach(tag => {
      const isActive = currentFilter.tag === tag ? ' active' : '';
      html += `<span class="filter-tag${isActive}" data-tag="${escapeAttr(tag)}">${escapeHtml(tag)}</span>`;
    });
  }

  container.innerHTML = html;

  // Add click handlers
  container.querySelectorAll('.filter-tag').forEach(el => {
    el.addEventListener('click', () => {
      const tag = el.dataset.tag;
      if (currentFilter.tag === tag) {
        currentFilter.tag = '';
        el.classList.remove('active');
      } else {
        container.querySelectorAll('.filter-tag').forEach(t => t.classList.remove('active'));
        currentFilter.tag = tag;
        el.classList.add('active');
      }
      renderRecipeGrid();
    });
  });
}

/**
 * Render recipe grid with current filters (with pagination)
 * @param {boolean} appendMore - If true, append to existing results (for "Load More")
 */
function renderRecipeGrid(appendMore = false) {
  const container = document.getElementById('recipe-grid');
  if (!container) return;

  // If not appending, reset pagination and re-filter
  if (!appendMore) {
    recipeGridCurrentPage = 0;

    // Filter recipes
    recipeGridFilteredRecipes = recipes.filter(recipe => {
      // Exclude variants from main grid (show canonical only)
      if (recipe.variant_of && recipe.variant_of !== recipe.id) {
        return false;
      }

      // Search filter (uses Pagefind when available, falls back to basic search)
      if (currentFilter.search) {
        if (pagefindSearchResults !== null && pagefindSearchResults.localIds) {
          // Pagefind returned results - use those IDs for local recipes
          if (!pagefindSearchResults.localIds.includes(recipe.id)) return false;
        } else {
          // Fall back to basic text search
          const searchText = [
            recipe.title,
            recipe.description,
            recipe.attribution,
            ...recipe.tags || []
          ].join(' ').toLowerCase();

          if (!searchText.includes(currentFilter.search)) return false;
        }
      }

      // Category filter
      if (currentFilter.category && recipe.category !== currentFilter.category) {
        return false;
      }

      // Tag filter
      if (currentFilter.tag && (!recipe.tags || !recipe.tags.includes(currentFilter.tag))) {
        return false;
      }

      // Collection filter (multi-select)
      if (currentFilter.collections && currentFilter.collections.length > 0) {
        const recipeCollection = recipe.collection || '';
        if (!currentFilter.collections.includes(recipeCollection)) {
          return false;
        }
      }

      // Ingredient filter
      if (currentFilter.ingredientMatchInfo && currentFilter.ingredientMatchInfo.matches.length > 0) {
        const matchInfo = currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === recipe.id);
        if (!matchInfo) {
          return false;
        }
      }

      // Time filter
      if (nutritionFilter.timeLimit) {
        const recipeTime = parseTimeToMinutes(recipe.total_time || recipe.cook_time);
        if (recipeTime === null || recipeTime > nutritionFilter.timeLimit) {
          return false;
        }
      }

      // Nutrition filters
      if (nutritionFilter.onlyWithNutrition && !recipe.nutrition) {
        return false;
      }

      // Check nutrition ranges if recipe has data
      if (recipe.nutrition) {
        const n = recipe.nutrition;

        // Calories filter
        if (nutritionFilter.calories.min !== null && (n.calories === undefined || n.calories < nutritionFilter.calories.min)) {
          return false;
        }
        if (nutritionFilter.calories.max !== null && n.calories !== undefined && n.calories > nutritionFilter.calories.max) {
          return false;
        }

        // Carbs filter
        if (nutritionFilter.carbs.min !== null && (n.carbohydrates === undefined || n.carbohydrates < nutritionFilter.carbs.min)) {
          return false;
        }
        if (nutritionFilter.carbs.max !== null && n.carbohydrates !== undefined && n.carbohydrates > nutritionFilter.carbs.max) {
          return false;
        }

        // Protein filter
        if (nutritionFilter.protein.min !== null && (n.protein === undefined || n.protein < nutritionFilter.protein.min)) {
          return false;
        }
        if (nutritionFilter.protein.max !== null && n.protein !== undefined && n.protein > nutritionFilter.protein.max) {
          return false;
        }

        // Fat filter
        if (nutritionFilter.fat.min !== null && (n.fat === undefined || n.fat < nutritionFilter.fat.min)) {
          return false;
        }
        if (nutritionFilter.fat.max !== null && n.fat !== undefined && n.fat > nutritionFilter.fat.max) {
          return false;
        }
      } else if (hasActiveNutritionFilter()) {
        // No nutrition data but filters are active - skip unless showing all
        return false;
      }

      return true;
    });

    // If ingredient search is active, sort by match count first
    if (currentFilter.ingredientMatchInfo && currentFilter.ingredientMatchInfo.matches.length > 0) {
      recipeGridFilteredRecipes.sort((a, b) => {
        const matchA = currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === a.id);
        const matchB = currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === b.id);
        const countA = matchA ? matchA.matchCount : 0;
        const countB = matchB ? matchB.matchCount : 0;
        if (countB !== countA) return countB - countA;
        return a.title.localeCompare(b.title);
      });
    } else {
      // Sort by title
      recipeGridFilteredRecipes.sort((a, b) => a.title.localeCompare(b.title));
    }
  }

  // Render empty state
  if (recipeGridFilteredRecipes.length === 0) {
    container.innerHTML = `
      <div class="text-center text-muted" style="grid-column: 1/-1; padding: 2rem;">
        <p>No recipes found matching your criteria.</p>
        <button class="btn btn-secondary" onclick="clearFilters()">Clear Filters</button>
      </div>
    `;
    return;
  }

  // Calculate pagination
  const startIndex = appendMore ? recipeGridCurrentPage * recipeGridPageSize : 0;
  const endIndex = (recipeGridCurrentPage + 1) * recipeGridPageSize;
  const recipesToRender = recipeGridFilteredRecipes.slice(startIndex, endIndex);
  const hasMoreRecipes = endIndex < recipeGridFilteredRecipes.length;
  const totalCount = recipeGridFilteredRecipes.length;
  const showingCount = Math.min(endIndex, totalCount);

  // Build HTML for recipes
  let html = '';

  // If appending, keep existing content but remove the old "Load More" section
  if (appendMore) {
    const existingLoadMore = container.querySelector('.load-more-section');
    if (existingLoadMore) {
      existingLoadMore.remove();
    }
    const existingRemote = container.querySelector('.remote-results-section');
    if (existingRemote) {
      existingRemote.remove();
    }
  }

  recipesToRender.forEach(recipe => {
    // Get ingredient match info if available
    const matchInfo = currentFilter.ingredientMatchInfo
      ? currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === recipe.id)
      : null;
    html += renderRecipeCard(recipe, matchInfo);
  });

  // Add "Load More" button if there are more recipes
  if (hasMoreRecipes) {
    const remaining = totalCount - showingCount;
    html += `
      <div class="load-more-section" style="grid-column: 1/-1; text-align: center; padding: 1.5rem;">
        <p style="color: var(--color-teal-dark); margin-bottom: 0.5rem;">
          Showing ${showingCount} of ${totalCount} recipes
        </p>
        <button class="btn btn-primary" onclick="loadMoreRecipes()" style="padding: 0.75rem 2rem;">
          Load More (${Math.min(remaining, recipeGridPageSize)} more)
        </button>
      </div>
    `;
  } else if (totalCount > recipeGridPageSize) {
    // Show total count when all loaded
    html += `
      <div class="load-more-section" style="grid-column: 1/-1; text-align: center; padding: 1rem;">
        <p style="color: var(--color-teal-dark); font-size: 0.9rem;">
          Showing all ${totalCount} recipes
        </p>
      </div>
    `;
  }

  // Add remote results from Pagefind if searching (only on first render, not append)
  if (!appendMore && pagefindSearchResults && pagefindSearchResults.remoteResults && pagefindSearchResults.remoteResults.length > 0) {
    html += `
      <div class="remote-results-section" style="grid-column: 1/-1; margin-top: 2rem; padding-top: 1rem; border-top: 2px dashed var(--color-teal-light);">
        <h3 style="color: var(--color-teal-dark); margin-bottom: 1rem;">Also found in other collections:</h3>
        <div class="remote-results-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;">
    `;
    pagefindSearchResults.remoteResults.forEach(result => {
      html += `
        <a href="${escapeAttr(result.url)}" class="remote-recipe-card" target="_blank" rel="noopener"
           style="display: block; padding: 1rem; background: var(--color-cream); border: 1px solid var(--color-border); border-radius: 8px; text-decoration: none; color: inherit; transition: transform 0.2s, box-shadow 0.2s;">
          <div style="font-size: 0.75rem; color: var(--color-coral); margin-bottom: 0.25rem;">${escapeHtml(result.collection)}</div>
          <div style="font-weight: 600; color: var(--color-teal-dark);">${escapeHtml(result.title)}</div>
          ${result.category ? `<div style="font-size: 0.8rem; color: #666;">${escapeHtml(result.category)}</div>` : ''}
          <div style="font-size: 0.7rem; color: var(--color-teal); margin-top: 0.5rem;">View on ${escapeHtml(result.collection)} →</div>
        </a>
      `;
    });
    html += `</div></div>`;
  }

  if (appendMore) {
    // Append new recipes to existing grid
    container.insertAdjacentHTML('beforeend', html);
  } else {
    container.innerHTML = html;
  }
}

/**
 * Load more recipes (pagination)
 */
function loadMoreRecipes() {
  recipeGridCurrentPage++;
  renderRecipeGrid(true);
}

/**
 * Render a single recipe card
 * @param {Object} recipe - The recipe data
 * @param {Object|null} ingredientMatchInfo - Optional ingredient match info
 */
function renderRecipeCard(recipe, ingredientMatchInfo = null) {
  const categoryIcon = getCategoryIcon(recipe.category);
  const timeInfo = recipe.total_time || recipe.cook_time || '';

  // Build match badge HTML
  let matchBadgeHtml = '';
  if (ingredientMatchInfo) {
    if (ingredientMatchInfo.isPerfectMatch) {
      matchBadgeHtml = '<span class="match-badge match-badge-perfect">Perfect Match</span>';
    } else {
      matchBadgeHtml = `<span class="match-badge match-badge-partial">${ingredientMatchInfo.matchCount}/${ingredientMatchInfo.totalSelected} matched</span>`;
    }
  }

  // Build missing ingredients HTML
  let missingHtml = '';
  if (ingredientMatchInfo && ingredientMatchInfo.missingIngredients.length > 0) {
    missingHtml = `
      <div class="recipe-missing-ingredients">
        <strong>Need:</strong> ${ingredientMatchInfo.missingIngredients.map(i => escapeHtml(i)).join(', ')}
      </div>
    `;
  }

  // Build substitution info HTML
  let substitutionHtml = '';
  if (ingredientMatchInfo && ingredientMatchInfo.substitutionMatches && ingredientMatchInfo.substitutionMatches.length > 0) {
    const subItems = ingredientMatchInfo.substitutionMatches.map(sub => {
      return `<span class="substitution-item" title="${escapeAttr(sub.substituteInfo.notes || '')}">` +
             `${escapeHtml(sub.userHas)} → ${escapeHtml(sub.recipeNeeds)}</span>`;
    }).join(', ');
    substitutionHtml = `
      <div class="recipe-substitutions">
        <strong>Subs:</strong> ${subItems}
      </div>
    `;
  }

  // Check if recipe is in meal plan
  const isInMealPlan = selectedMealRecipes.some(r => r.id === recipe.id);
  const mealPlanBtnClass = isInMealPlan ? 'meal-plan-btn in-plan' : 'meal-plan-btn';
  const mealPlanBtnText = isInMealPlan ? '✓ In Plan' : '+ Meal Plan';
  const mealPlanAction = isInMealPlan
    ? `removeFromShoppingList('${escapeAttr(recipe.id)}')`
    : `addToShoppingList('${escapeAttr(recipe.id)}')`;

  return `
    <article class="recipe-card category-${escapeAttr(recipe.category)}">
      <div class="recipe-card-image">
        ${matchBadgeHtml ? `<div class="match-badge-container">${matchBadgeHtml}</div>` : ''}
        ${categoryIcon}
      </div>
      <div class="recipe-card-content">
        <span class="category">${escapeHtml(recipe.category) || 'Uncategorized'}</span>
        <h3><a href="recipe.html#${escapeAttr(recipe.id)}">${escapeHtml(recipe.title)}</a></h3>
        <p class="description">${escapeHtml(recipe.description)}</p>
        ${missingHtml}
        ${substitutionHtml}
        <div class="meta">
          ${recipe.servings_yield ? `<span>${escapeHtml(recipe.servings_yield)}</span>` : ''}
          ${timeInfo ? `<span>${escapeHtml(timeInfo)}</span>` : ''}
        </div>
        <button type="button" class="${mealPlanBtnClass}" onclick="${mealPlanAction}; event.stopPropagation();">
          ${mealPlanBtnText}
        </button>
      </div>
    </article>
  `;
}

/**
 * Re-render the current recipe (called after substitution changes)
 */
function renderCurrentRecipe() {
  if (currentRecipeId) {
    renderRecipeDetail(currentRecipeId, true); // true = skip loading message
  }
}

/**
 * Render full recipe detail page
 */
async function renderRecipeDetail(recipeId, skipLoading = false) {
  const container = document.getElementById('recipe-content');

  if (!container) return;

  // Clear substitutions if navigating to a different recipe
  if (currentRecipeId !== recipeId) {
    activeSubstitutions = {};
    currentRecipeId = recipeId;
  }

  // Show loading state (unless this is a re-render)
  if (!skipLoading) {
    container.innerHTML = `
      <div class="text-center" style="padding: 2rem;">
        <p>Loading recipe...</p>
      </div>
    `;
  }

  // Load full recipe details (from cache or fetch)
  const recipe = await loadFullRecipe(recipeId);

  // Load kitchen tips and substitutions lazily when viewing a recipe
  await Promise.all([loadKitchenTips(), loadSubstitutions(), loadHealthConsiderations()]);

  if (!recipe) {
    container.innerHTML = `
      <div class="text-center">
        <h2>Recipe Not Found</h2>
        <p>Sorry, we couldn't find that recipe.</p>
        <a href="index.html" class="btn btn-primary">Back to Recipes</a>
      </div>
    `;
    return;
  }

  // Find variants of this recipe
  const variants = findVariants(recipe);

  // Analyze health considerations
  const healthWarnings = await analyzeRecipeHealth(recipe);

  // Update page title
  document.title = `${recipe.title} - Grandma's Recipe Archive`;

  let html = `
    <article class="recipe-detail">
      <header class="recipe-header">
        <h1>${escapeHtml(recipe.title)}</h1>
        ${recipe.attribution ? `<p class="recipe-attribution">From: ${escapeHtml(recipe.attribution)}</p>` : ''}
        ${recipe.source_note ? `<p class="recipe-source">${escapeHtml(recipe.source_note)}</p>` : ''}
        ${recipe.description ? `<p>${escapeHtml(recipe.description)}</p>` : ''}

        <div class="header-controls">
          <div class="confidence-indicator confidence-${escapeAttr(recipe.confidence?.overall || 'high')}">
            Confidence: ${escapeHtml(capitalizeFirst(recipe.confidence?.overall || 'high'))}
          </div>

          ${variants.length > 0 ? renderVariantsDropdown(recipe, variants) : ''}
        </div>

        <div class="action-buttons" style="margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <button id="print-btn" class="btn btn-secondary btn-print">Print Recipe</button>
          ${recipe.conversions?.has_conversions ? `
            <button id="metric-toggle" class="btn btn-secondary">
              ${showMetric ? 'Show US Units' : 'Show Metric'}
            </button>
          ` : ''}
        </div>
      </header>

      ${renderQuickFacts(recipe)}

      ${renderScalingControls(recipe)}

      <section class="ingredients-section">
        <h2>Ingredients ${showMetric && recipe.conversions?.has_conversions ? '<span class="unit-badge">Metric (approx.)</span>' : ''}${recipeScale !== 1 ? `<span class="scale-badge">${recipeScale}×</span>` : ''}</h2>
        ${renderIngredientsList(recipe)}
      </section>

      <!-- Health Considerations Panel -->
      ${renderHealthPanel(healthWarnings)}

      <!-- Protein & Vegetable Substitution Panel -->
      <div id="protein-substitution-container"></div>

      <!-- Milk Substitution Calculator (for cheesemaking recipes) -->
      <div id="milk-substitution-container"></div>

      <section class="instructions-section">
        <h2>Instructions</h2>
        <ol class="instructions-list">
          ${recipe.instructions.map(inst => {
            const isInferred = inst.text.includes('[INFERRED]');
            const text = inst.text.replace('[INFERRED] ', '');
            return `<li class="${isInferred ? 'inferred' : ''}">${escapeHtml(text)}</li>`;
          }).join('')}
        </ol>
      </section>

      ${recipe.oven_directions ? renderOvenDirections(recipe.oven_directions) : ''}
      ${recipe.frosting ? renderFrosting(recipe.frosting) : ''}
      ${recipe.nutrition ? renderNutrition(recipe.nutrition, recipe.servings_yield) : ''}
      ${recipe.notes && recipe.notes.length > 0 ? renderNotes(recipe.notes) : ''}
      ${recipe.conversions?.conversion_assumptions?.length > 0 && showMetric ? renderConversionNotes(recipe.conversions) : ''}
      ${renderKitchenTipsForRecipe(recipe)}
      ${renderTags(recipe.tags)}
      ${renderConfidenceFlags(recipe.confidence?.flags)}
      ${renderOriginalScan(recipe.image_refs, recipe.collection)}
    </article>
  `;

  container.innerHTML = html;

  // Re-attach event listeners
  const printBtn = document.getElementById('print-btn');
  if (printBtn) {
    printBtn.addEventListener('click', () => window.print());
  }

  const metricToggle = document.getElementById('metric-toggle');
  if (metricToggle) {
    metricToggle.addEventListener('click', () => {
      showMetric = !showMetric;
      renderRecipeDetail(recipeId);
    });
  }

  // Variant dropdown handler
  const variantSelect = document.getElementById('variant-select');
  if (variantSelect) {
    variantSelect.addEventListener('change', (e) => {
      if (e.target.value) {
        window.location.hash = e.target.value;
        renderRecipeDetail(e.target.value);
      }
    });
  }

  // Scale button handlers
  document.querySelectorAll('.scale-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const scale = parseFloat(btn.dataset.scale);
      if (!isNaN(scale)) {
        setRecipeScale(scale, recipeId);
      }
    });
  });

  // Render Milk Substitution Calculator for cheesemaking recipes
  if (typeof MilkSubstitution !== 'undefined') {
    const milkContainer = document.getElementById('milk-substitution-container');
    if (milkContainer && MilkSubstitution.isCheeseRecipe(recipe)) {
      MilkSubstitution.renderMilkSwitcher(recipe, 'milk-substitution-container');
    }
  }

  // Render Protein Substitution Panel
  if (typeof ProteinSubstitution !== 'undefined') {
    const proteinContainer = document.getElementById('protein-substitution-container');
    if (proteinContainer) {
      try {
        const analysis = await ProteinSubstitution.analyzeRecipe(recipe);
        if (analysis.hasSubstitutions) {
          proteinContainer.innerHTML = ProteinSubstitution.renderSubstitutionPanel(analysis);
        }
      } catch (e) {
        console.warn('Protein substitution panel error:', e.message);
      }
    }
  }
}

/**
 * Find all variants of a recipe (or recipes this is a variant of)
 */
function findVariants(recipe) {
  const variants = [];
  const canonicalId = recipe.canonical_id || recipe.id;

  recipes.forEach(r => {
    if (r.id === recipe.id) return; // Skip self

    // Check if this recipe is a variant of the current one
    if (r.variant_of === recipe.id || r.variant_of === canonicalId) {
      variants.push(r);
    }
    // Check if current recipe is a variant and find siblings
    if (recipe.variant_of && (r.id === recipe.variant_of || r.variant_of === recipe.variant_of)) {
      if (r.id !== recipe.id) variants.push(r);
    }
    // Check canonical grouping
    if (r.canonical_id === canonicalId && r.id !== recipe.id) {
      variants.push(r);
    }
  });

  return variants;
}

/**
 * Render variants dropdown
 */
function renderVariantsDropdown(currentRecipe, variants) {
  return `
    <div class="variants-dropdown">
      <label for="variant-select">Variants:</label>
      <select id="variant-select" class="variant-select">
        <option value="${escapeAttr(currentRecipe.id)}" selected>${escapeHtml(currentRecipe.source_note || 'Current version')}</option>
        ${variants.map(v => `
          <option value="${escapeAttr(v.id)}">${escapeHtml(v.source_note || v.title)}${v.variant_notes ? ` - ${escapeHtml(v.variant_notes.substring(0, 50))}...` : ''}</option>
        `).join('')}
      </select>
    </div>
  `;
}

/**
 * Render ingredients list (with metric toggle, scaling support, and substitution swapping)
 */
function renderIngredientsList(recipe) {
  const ingredients = showMetric && recipe.conversions?.ingredients_metric?.length > 0
    ? recipe.conversions.ingredients_metric
    : recipe.ingredients;

  return `
    <ul class="ingredients-list">
      ${ingredients.map((ing, index) => {
        // Check for active substitution
        const activeSub = activeSubstitutions[index];
        const displayItem = activeSub ? activeSub.substitute.ingredient : ing.item;

        // Apply scaling if not 1x
        const scaled = scaleQuantity(ing.quantity, recipeScale);
        const warning = checkPracticalMinimum(scaled.value, ing.unit);

        // Check for available substitutions (use original ingredient for lookup)
        const subRule = findSubstitutionsForIngredient(ing.item);
        const hasSubstitutes = subRule && subRule.substitutes && subRule.substitutes.length > 0;

        const swapClasses = [
          hasSubstitutes ? 'has-substitutes' : '',
          activeSub ? 'is-swapped' : ''
        ].filter(Boolean).join(' ');

        return `
        <li class="${warning ? 'has-warning' : ''} ${swapClasses}">
          <span class="ingredient-quantity ${recipeScale !== 1 ? 'scaled' : ''}">${escapeHtml(scaled.display)} ${escapeHtml(ing.unit || '')}</span>
          <span class="ingredient-item ${hasSubstitutes ? 'swappable' : ''}"
                ${hasSubstitutes ? `onclick="showSubstitutionModal(${index}, ${escapeAttr(JSON.stringify(ing))}, ${escapeAttr(JSON.stringify(subRule))})"` : ''}>
            ${escapeHtml(displayItem)}
            ${ing.prep_note ? `<span class="ingredient-prep">, ${escapeHtml(ing.prep_note)}</span>` : ''}
            ${hasSubstitutes ? '<span class="swap-icon" title="Click to swap ingredient">⇄</span>' : ''}
            ${activeSub ? '<span class="swapped-badge">swapped</span>' : ''}
          </span>
          ${warning ? `<span class="ingredient-warning" title="${escapeAttr(warning)}">⚠️</span>` : ''}
        </li>
      `;
      }).join('')}
    </ul>
    ${Object.keys(activeSubstitutions).length > 0 ? `
      <button class="btn btn-link reset-subs-btn" onclick="resetSubstitutions()">
        ↩ Reset all substitutions
      </button>
    ` : ''}
  `;
}

/**
 * Render nutrition information (with substitution adjustments)
 */
function renderNutrition(nutrition, servings) {
  if (!nutrition || nutrition.status === 'insufficient_data') {
    if (nutrition?.missing_inputs?.length > 0) {
      return `
        <section class="nutrition-section nutrition-incomplete">
          <h3>Nutrition Information</h3>
          <p class="text-muted">Nutrition data incomplete. Missing: ${escapeHtml(nutrition.missing_inputs.join(', '))}</p>
        </section>
      `;
    }
    return '';
  }

  // Apply substitution adjustments if any
  const adjustedNutrition = Object.keys(activeSubstitutions).length > 0
    ? calculateAdjustedNutrition(nutrition)
    : nutrition;

  const n = adjustedNutrition.per_serving;
  if (!n) return '';

  const hasAdjustments = adjustedNutrition.substitutionNote;

  return `
    <section class="nutrition-section ${hasAdjustments ? 'nutrition-adjusted' : ''}">
      <h3>Nutrition Information ${servings ? `<span class="text-muted">(per serving)</span>` : ''}
        ${hasAdjustments ? '<span class="adjusted-badge">adjusted</span>' : ''}
      </h3>
      <div class="nutrition-grid">
        ${n.calories !== null ? `<div class="nutrition-item ${hasAdjustments ? 'adjusted' : ''}"><span class="nutrition-value">${escapeHtml(n.calories)}</span><span class="nutrition-label">Calories</span></div>` : ''}
        ${n.fat_g !== null ? `<div class="nutrition-item ${hasAdjustments ? 'adjusted' : ''}"><span class="nutrition-value">${escapeHtml(n.fat_g)}g</span><span class="nutrition-label">Fat</span></div>` : ''}
        ${n.carbs_g !== null ? `<div class="nutrition-item ${hasAdjustments ? 'adjusted' : ''}"><span class="nutrition-value">${escapeHtml(n.carbs_g)}g</span><span class="nutrition-label">Carbs</span></div>` : ''}
        ${n.protein_g !== null ? `<div class="nutrition-item ${hasAdjustments ? 'adjusted' : ''}"><span class="nutrition-value">${escapeHtml(n.protein_g)}g</span><span class="nutrition-label">Protein</span></div>` : ''}
        ${n.sodium_mg !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.sodium_mg)}mg</span><span class="nutrition-label">Sodium</span></div>` : ''}
        ${n.fiber_g !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.fiber_g)}g</span><span class="nutrition-label">Fiber</span></div>` : ''}
        ${n.sugar_g !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.sugar_g)}g</span><span class="nutrition-label">Sugar</span></div>` : ''}
      </div>
      ${hasAdjustments ? `
        <p class="nutrition-adjusted-note">
          <small>${escapeHtml(adjustedNutrition.substitutionNote)} - estimates may vary</small>
        </p>
      ` : ''}
      ${nutrition.assumptions?.length > 0 ? `
        <p class="nutrition-assumptions text-muted">
          <small>Assumptions: ${escapeHtml(nutrition.assumptions.join('; '))}</small>
        </p>
      ` : ''}
    </section>
  `;
}

/**
 * Render conversion notes
 */
function renderConversionNotes(conversions) {
  if (!conversions?.conversion_assumptions?.length) return '';

  return `
    <section class="notes-section conversion-notes" style="border-left-color: #6c757d;">
      <h3>Conversion Notes</h3>
      <p class="text-muted"><small>Metric conversions are approximate. Assumptions used:</small></p>
      <ul>
        ${conversions.conversion_assumptions.map(a => `<li><small>${escapeHtml(a)}</small></li>`).join('')}
      </ul>
    </section>
  `;
}

/**
 * Render quick facts section
 */
function renderQuickFacts(recipe) {
  const facts = [];

  if (recipe.servings_yield) facts.push({ label: 'Yield', value: recipe.servings_yield });
  if (recipe.prep_time) facts.push({ label: 'Prep', value: recipe.prep_time });
  if (recipe.cook_time) facts.push({ label: 'Cook', value: recipe.cook_time });
  if (recipe.total_time) facts.push({ label: 'Total', value: recipe.total_time });
  if (recipe.temperature) facts.push({ label: 'Temp', value: recipe.temperature });

  if (facts.length === 0) return '';

  return `
    <div class="recipe-quick-facts">
      ${facts.map(f => `
        <div class="quick-fact">
          <span class="quick-fact-label">${escapeHtml(f.label)}</span>
          <span class="quick-fact-value">${escapeHtml(f.value)}</span>
        </div>
      `).join('')}
    </div>
  `;
}

/**
 * Render oven directions (alternative method)
 */
function renderOvenDirections(directions) {
  return `
    <section class="sub-recipe">
      <h3>Oven Directions (Alternative)</h3>
      <ol class="instructions-list">
        ${directions.map(d => `<li>${escapeHtml(d.text)}</li>`).join('')}
      </ol>
    </section>
  `;
}

/**
 * Render frosting/sub-recipe section
 */
function renderFrosting(frosting) {
  return `
    <section class="sub-recipe">
      <h3>${escapeHtml(frosting.name)}</h3>
      <h4>Ingredients:</h4>
      <ul class="ingredients-list">
        ${frosting.ingredients.map(ing => `
          <li>
            <span class="ingredient-quantity">${escapeHtml(ing.quantity)} ${escapeHtml(ing.unit)}</span>
            <span class="ingredient-item">${escapeHtml(ing.item)}</span>
          </li>
        `).join('')}
      </ul>
      <h4>Instructions:</h4>
      <p>${escapeHtml(frosting.instructions)}</p>
    </section>
  `;
}

/**
 * Render notes section
 */
function renderNotes(notes) {
  return `
    <section class="notes-section">
      <h3>Notes</h3>
      <ul>
        ${notes.map(note => `<li>${escapeHtml(note)}</li>`).join('')}
      </ul>
    </section>
  `;
}

/**
 * Render tags
 */
function renderTags(tags) {
  if (!tags || tags.length === 0) return '';

  return `
    <div class="recipe-tags">
      ${tags.map(tag => `<span class="recipe-tag">${escapeHtml(tag)}</span>`).join('')}
    </div>
  `;
}

/**
 * Render confidence flags if any
 */
function renderConfidenceFlags(flags) {
  if (!flags || flags.length === 0) return '';

  return `
    <section class="notes-section" style="border-left-color: #f0ad4e;">
      <h3>Transcription Notes</h3>
      <ul>
        ${flags.map(flag => `
          <li>
            <strong>${escapeHtml(flag.field)}:</strong> ${escapeHtml(flag.issue)}
            ${flag.candidates && flag.candidates.length > 0 ?
              `<br><em>Possible values: ${escapeHtml(flag.candidates.join(', '))}</em>` : ''}
          </li>
        `).join('')}
      </ul>
    </section>
  `;
}

/**
 * Get the folder path for a collection's images
 * @param {string} collection - The collection ID
 * @param {boolean} isRemote - Whether this is a remote collection
 * @param {string} remoteSiteUrl - The base URL for remote collections (e.g., 'https://jsschrstrcks1.github.io/MomsRecipes/')
 * @returns {string} - The base path for images
 */
function getCollectionImagePath(collection, isRemote = false, remoteSiteUrl = null) {
  // Remote collections: use absolute URL to their GitHub Pages site
  if (isRemote && remoteSiteUrl) {
    return remoteSiteUrl + 'data/';
  }
  // Local collection (grandma-baker): images are flat in data/
  return 'data/';
}

/**
 * Render original scan thumbnail
 */
function renderOriginalScan(imageRefs, collection) {
  if (!imageRefs || imageRefs.length === 0) return '';

  const basePath = getCollectionImagePath(collection);

  return `
    <section class="original-scan">
      <h3>Original Scan</h3>
      ${imageRefs.map(ref => {
        const safePath = sanitizeUrl(basePath + ref);
        return `
        <a href="${escapeAttr(safePath)}" target="_blank">
          <img src="${escapeAttr(safePath)}" alt="Original recipe scan" class="scan-thumbnail"
               style="max-width: 200px; max-height: 150px; object-fit: cover;">
        </a>
      `;}).join('')}
    </section>
  `;
}

/**
 * Get category icon (emoji)
 */
function getCategoryIcon(category) {
  const icons = {
    appetizers: '🥗',
    beverages: '🍹',
    breads: '🍞',
    breakfast: '🍳',
    desserts: '🍪',
    mains: '🍽️',
    salads: '🥬',
    sides: '🥕',
    soups: '🍲',
    snacks: '🍿'
  };
  return icons[category] || '📖';
}

/**
 * Clear all filters
 */
function clearFilters() {
  currentFilter = { search: '', category: '', tag: '', collections: ['grandma-baker', 'mommom-baker', 'granny-hudson', 'all'], ingredients: [], ingredientMatchInfo: null };
  pagefindSearchResults = null; // Clear Pagefind results
  recipeGridCurrentPage = 0; // Reset pagination

  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = '';

  const categorySelect = document.getElementById('category-filter');
  if (categorySelect) categorySelect.value = '';

  document.querySelectorAll('.filter-tag').forEach(el => el.classList.remove('active'));

  // Reset collection checkboxes to all checked
  const collectionFilters = document.getElementById('collection-filters');
  if (collectionFilters) {
    collectionFilters.querySelectorAll('input[type="checkbox"][data-collection]').forEach(checkbox => {
      checkbox.checked = true;
    });
    // Update Select All button text
    const selectAllBtn = document.getElementById('collection-select-all');
    if (selectAllBtn) {
      selectAllBtn.textContent = 'Clear All';
    }
  }
  saveCollectionPreferences();

  // Clear ingredient search
  selectedIngredients = [];
  renderSelectedIngredients();
  const ingredientInput = document.getElementById('ingredient-input');
  if (ingredientInput) ingredientInput.value = '';
  const resultsDiv = document.getElementById('ingredient-search-results');
  if (resultsDiv) resultsDiv.classList.add('hidden');

  // Clear time filter
  const timeFilter = document.getElementById('time-filter');
  if (timeFilter) timeFilter.value = '';
  nutritionFilter.timeLimit = null;

  // Clear nutrition filters
  clearNutritionFilters();
  nutritionFilter.onlyWithNutrition = false;
  updateNutritionInputs();
  updateDietPresetButtons();
  const onlyWithNutrition = document.getElementById('only-with-nutrition');
  if (onlyWithNutrition) onlyWithNutrition.checked = false;

  renderRecipeGrid();
}

// Make clearFilters available globally
window.clearFilters = clearFilters;

/**
 * Utility: Capitalize first letter
 */
function capitalizeFirst(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Utility: Debounce function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Show error message
 */
function showError(message) {
  const container = document.getElementById('recipe-grid') || document.getElementById('recipe-content');
  if (container) {
    container.innerHTML = `
      <div class="text-center" style="padding: 2rem; color: #721c24; background: #f8d7da; border-radius: 8px;">
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  }
}
