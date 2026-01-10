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
let recipes = [];
let categories = new Set();
let allTags = new Set();
let currentFilter = { search: '', category: '', tag: '', collection: '', ingredients: [], ingredientMatchInfo: null };
let showMetric = false; // Toggle for metric conversions

// Ingredient search state
let ingredientIndex = null;
let selectedIngredients = [];
let ingredientSearchOptions = {
  matchMode: 'any',      // 'any' or 'all'
  missingThreshold: 0    // 0, 1, 2, or 3
};
let autocompleteHighlightIndex = -1;

// DOM Ready
document.addEventListener('DOMContentLoaded', init);

async function init() {
  await loadRecipes();
  await loadIngredientIndex();
  setupEventListeners();
  setupIngredientSearch();
  handleRouting();
}

/**
 * Load recipes from JSON file
 */
async function loadRecipes() {
  try {
    const response = await fetch('data/recipes_master.json');
    const data = await response.json();
    recipes = data.recipes || [];

    // Extract categories and tags
    recipes.forEach(recipe => {
      if (recipe.category) categories.add(recipe.category);
      if (recipe.tags) recipe.tags.forEach(tag => allTags.add(tag));
    });

    console.log(`Loaded ${recipes.length} recipes`);
    updateCollectionCounts();
  } catch (error) {
    console.error('Failed to load recipes:', error);
    showError('Unable to load recipes. Please refresh the page.');
  }
}

/**
 * Load ingredient index from JSON file
 */
async function loadIngredientIndex() {
  try {
    const response = await fetch('data/ingredient-index.json');
    ingredientIndex = await response.json();
    console.log(`Loaded ingredient index with ${ingredientIndex.meta.total_ingredients} ingredients`);
  } catch (error) {
    console.error('Failed to load ingredient index:', error);
    // Non-fatal - ingredient search just won't work
  }
}

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
function showAutocomplete(query) {
  const autocomplete = document.getElementById('ingredient-autocomplete');
  if (!autocomplete || !ingredientIndex) return;

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
 * Search ingredients using fuzzy matching
 */
function searchIngredients(query, limit = 10) {
  if (!ingredientIndex || !query) return [];

  const queryLower = query.toLowerCase().trim();
  const results = [];

  // Search through all ingredient names
  for (const name of ingredientIndex.all_names) {
    // Skip already selected ingredients
    if (selectedIngredients.includes(name)) continue;

    const score = fuzzyMatch(name, queryLower);
    if (score > 0) {
      // Get canonical name for recipe count
      const canonical = ingredientIndex.name_mapping[name] || name;
      const recipeIds = ingredientIndex.ingredients[canonical] || ingredientIndex.ingredients[name] || [];

      results.push({
        name: name,
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
  renderSelectedIngredients();

  const input = document.getElementById('ingredient-input');
  if (input) input.value = '';

  const resultsDiv = document.getElementById('ingredient-search-results');
  if (resultsDiv) resultsDiv.classList.add('hidden');

  // Reset current filter's ingredient state
  currentFilter.ingredients = [];
  currentFilter.ingredientMatchInfo = null;

  renderRecipeGrid();
}

/**
 * Perform the ingredient-based recipe search
 */
function performIngredientSearch() {
  if (selectedIngredients.length === 0) {
    clearIngredientSearch();
    return;
  }

  // Find matching recipes
  const matchInfo = findRecipesByIngredients(
    selectedIngredients,
    ingredientSearchOptions.matchMode,
    ingredientSearchOptions.missingThreshold
  );

  // Store match info for use in rendering
  currentFilter.ingredients = selectedIngredients;
  currentFilter.ingredientMatchInfo = matchInfo;

  // Update results summary
  updateIngredientSearchResults(matchInfo);

  // Re-render the recipe grid
  renderRecipeGrid();
}

/**
 * Find recipes that match the selected ingredients
 */
function findRecipesByIngredients(ingredients, matchMode, missingThreshold) {
  if (!ingredientIndex || ingredients.length === 0) {
    return { matches: [], perfectMatches: 0, partialMatches: 0 };
  }

  const results = [];

  for (const recipe of recipes) {
    // Skip variants from main grid
    if (recipe.variant_of && recipe.variant_of !== recipe.id) continue;

    const recipeIngredients = recipe.ingredients || [];
    const recipeIngredientNames = recipeIngredients.map(ing =>
      normalizeIngredientName(ing.item)
    );

    // Check how many of the selected ingredients are in this recipe
    let matchCount = 0;
    const matchedIngredients = [];
    const missingIngredients = [];

    for (const selectedIng of ingredients) {
      const normalizedSelected = normalizeIngredientName(selectedIng);
      const canonical = ingredientIndex.name_mapping[normalizedSelected] || normalizedSelected;

      // Check if recipe contains this ingredient (or its synonym)
      const found = recipeIngredientNames.some(recipeName => {
        const recipeCanonical = ingredientIndex.name_mapping[recipeName] || recipeName;
        return recipeName.includes(normalizedSelected) ||
               normalizedSelected.includes(recipeName) ||
               recipeCanonical === canonical ||
               recipeName === normalizedSelected;
      });

      if (found) {
        matchCount++;
        matchedIngredients.push(selectedIng);
      } else {
        missingIngredients.push(selectedIng);
      }
    }

    // Determine if this recipe matches based on mode and threshold
    let isMatch = false;
    if (matchMode === 'any') {
      // "Any" mode: at least one ingredient matches
      isMatch = matchCount > 0;
    } else {
      // "All" mode: all selected ingredients must match (minus threshold)
      const requiredMatches = Math.max(1, ingredients.length - missingThreshold);
      isMatch = matchCount >= requiredMatches;
    }

    if (isMatch) {
      results.push({
        recipeId: recipe.id,
        matchCount: matchCount,
        totalSelected: ingredients.length,
        matchedIngredients: matchedIngredients,
        missingIngredients: missingIngredients,
        isPerfectMatch: matchCount === ingredients.length
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

  if (!resultsDiv || !countSpan) return;

  const total = matchInfo.matches.length;

  if (total === 0) {
    countSpan.innerHTML = 'No recipes found with those ingredients';
  } else {
    let text = `Found <span class="match-count-number">${total}</span> recipe${total !== 1 ? 's' : ''}`;

    if (matchInfo.perfectMatches > 0 && matchInfo.partialMatches > 0) {
      text += ` (${matchInfo.perfectMatches} perfect match${matchInfo.perfectMatches !== 1 ? 'es' : ''}, ${matchInfo.partialMatches} partial)`;
    }

    countSpan.innerHTML = text;
  }

  resultsDiv.classList.remove('hidden');
}

/**
 * Update collection filter buttons with recipe counts
 */
function updateCollectionCounts() {
  const collectionFilters = document.getElementById('collection-filters');
  if (!collectionFilters) return;

  // Count recipes by collection (excluding reference collection from individual counts)
  const counts = {
    '': recipes.length, // All recipes
    'grandma-baker': 0,
    'mommom': 0,
    'granny': 0
  };

  recipes.forEach(recipe => {
    const collection = recipe.collection || '';
    if (counts.hasOwnProperty(collection)) {
      counts[collection]++;
    }
  });

  // Update button labels
  const labels = {
    '': 'All',
    'grandma-baker': 'Grandma',
    'mommom': 'MomMom',
    'granny': 'Granny'
  };

  collectionFilters.querySelectorAll('.collection-btn').forEach(btn => {
    const collection = btn.dataset.collection;
    const label = labels[collection] || collection;
    const count = counts[collection] || 0;
    btn.textContent = `${label} (${count})`;
  });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Search form
  const searchForm = document.getElementById('search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = document.getElementById('search-input').value;
      currentFilter.search = query.toLowerCase();
      renderRecipeGrid();
    });
  }

  // Search input (live search)
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', debounce((e) => {
      currentFilter.search = e.target.value.toLowerCase();
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

  // Collection filter buttons
  const collectionFilters = document.getElementById('collection-filters');
  if (collectionFilters) {
    collectionFilters.querySelectorAll('.collection-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        // Update active state
        collectionFilters.querySelectorAll('.collection-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Update filter
        currentFilter.collection = btn.dataset.collection;
        renderRecipeGrid();
      });
    });
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
 * Render tag filter buttons
 */
function renderTagFilters() {
  const container = document.getElementById('tag-filters');
  if (!container) return;

  const sortedTags = Array.from(allTags).sort();
  let html = '';

  sortedTags.forEach(tag => {
    html += `<span class="filter-tag" data-tag="${escapeAttr(tag)}">${escapeHtml(tag)}</span>`;
  });

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
 * Render recipe grid with current filters
 */
function renderRecipeGrid() {
  const container = document.getElementById('recipe-grid');
  if (!container) return;

  // Filter recipes
  let filtered = recipes.filter(recipe => {
    // Exclude variants from main grid (show canonical only)
    if (recipe.variant_of && recipe.variant_of !== recipe.id) {
      return false;
    }

    // Search filter
    if (currentFilter.search) {
      const searchText = [
        recipe.title,
        recipe.description,
        recipe.attribution,
        ...recipe.tags || []
      ].join(' ').toLowerCase();

      if (!searchText.includes(currentFilter.search)) return false;
    }

    // Category filter
    if (currentFilter.category && recipe.category !== currentFilter.category) {
      return false;
    }

    // Tag filter
    if (currentFilter.tag && (!recipe.tags || !recipe.tags.includes(currentFilter.tag))) {
      return false;
    }

    // Collection filter
    if (currentFilter.collection && recipe.collection !== currentFilter.collection) {
      return false;
    }

    // Ingredient filter
    if (currentFilter.ingredientMatchInfo && currentFilter.ingredientMatchInfo.matches.length > 0) {
      const matchInfo = currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === recipe.id);
      if (!matchInfo) {
        return false;
      }
    }

    return true;
  });

  // If ingredient search is active, sort by match count first
  if (currentFilter.ingredientMatchInfo && currentFilter.ingredientMatchInfo.matches.length > 0) {
    filtered.sort((a, b) => {
      const matchA = currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === a.id);
      const matchB = currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === b.id);
      const countA = matchA ? matchA.matchCount : 0;
      const countB = matchB ? matchB.matchCount : 0;
      if (countB !== countA) return countB - countA;
      return a.title.localeCompare(b.title);
    });
  } else {
    // Sort by title
    filtered.sort((a, b) => a.title.localeCompare(b.title));
  }

  // Render
  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="text-center text-muted" style="grid-column: 1/-1; padding: 2rem;">
        <p>No recipes found matching your criteria.</p>
        <button class="btn btn-secondary" onclick="clearFilters()">Clear Filters</button>
      </div>
    `;
    return;
  }

  let html = '';
  filtered.forEach(recipe => {
    // Get ingredient match info if available
    const matchInfo = currentFilter.ingredientMatchInfo
      ? currentFilter.ingredientMatchInfo.matches.find(m => m.recipeId === recipe.id)
      : null;
    html += renderRecipeCard(recipe, matchInfo);
  });

  container.innerHTML = html;
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
        <div class="meta">
          ${recipe.servings_yield ? `<span>${escapeHtml(recipe.servings_yield)}</span>` : ''}
          ${timeInfo ? `<span>${escapeHtml(timeInfo)}</span>` : ''}
        </div>
      </div>
    </article>
  `;
}

/**
 * Render full recipe detail page
 */
function renderRecipeDetail(recipeId) {
  const recipe = recipes.find(r => r.id === recipeId);
  const container = document.getElementById('recipe-content');

  if (!recipe || !container) {
    if (container) {
      container.innerHTML = `
        <div class="text-center">
          <h2>Recipe Not Found</h2>
          <p>Sorry, we couldn't find that recipe.</p>
          <a href="index.html" class="btn btn-primary">Back to Recipes</a>
        </div>
      `;
    }
    return;
  }

  // Find variants of this recipe
  const variants = findVariants(recipe);

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

      <section class="ingredients-section">
        <h2>Ingredients ${showMetric && recipe.conversions?.has_conversions ? '<span class="unit-badge">Metric (approx.)</span>' : ''}</h2>
        ${renderIngredientsList(recipe)}
      </section>

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
 * Render ingredients list (with metric toggle support)
 */
function renderIngredientsList(recipe) {
  const ingredients = showMetric && recipe.conversions?.ingredients_metric?.length > 0
    ? recipe.conversions.ingredients_metric
    : recipe.ingredients;

  return `
    <ul class="ingredients-list">
      ${ingredients.map(ing => `
        <li>
          <span class="ingredient-quantity">${escapeHtml(ing.quantity)} ${escapeHtml(ing.unit)}</span>
          <span class="ingredient-item">
            ${escapeHtml(ing.item)}
            ${ing.prep_note ? `<span class="ingredient-prep">, ${escapeHtml(ing.prep_note)}</span>` : ''}
          </span>
        </li>
      `).join('')}
    </ul>
  `;
}

/**
 * Render nutrition information
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

  const n = nutrition.per_serving;
  if (!n) return '';

  return `
    <section class="nutrition-section">
      <h3>Nutrition Information ${servings ? `<span class="text-muted">(per serving)</span>` : ''}</h3>
      <div class="nutrition-grid">
        ${n.calories !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.calories)}</span><span class="nutrition-label">Calories</span></div>` : ''}
        ${n.fat_g !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.fat_g)}g</span><span class="nutrition-label">Fat</span></div>` : ''}
        ${n.carbs_g !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.carbs_g)}g</span><span class="nutrition-label">Carbs</span></div>` : ''}
        ${n.protein_g !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.protein_g)}g</span><span class="nutrition-label">Protein</span></div>` : ''}
        ${n.sodium_mg !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.sodium_mg)}mg</span><span class="nutrition-label">Sodium</span></div>` : ''}
        ${n.fiber_g !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.fiber_g)}g</span><span class="nutrition-label">Fiber</span></div>` : ''}
        ${n.sugar_g !== null ? `<div class="nutrition-item"><span class="nutrition-value">${escapeHtml(n.sugar_g)}g</span><span class="nutrition-label">Sugar</span></div>` : ''}
      </div>
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
  currentFilter = { search: '', category: '', tag: '', collection: '', ingredients: [], ingredientMatchInfo: null };

  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = '';

  const categorySelect = document.getElementById('category-filter');
  if (categorySelect) categorySelect.value = '';

  document.querySelectorAll('.filter-tag').forEach(el => el.classList.remove('active'));

  // Reset collection buttons
  const collectionFilters = document.getElementById('collection-filters');
  if (collectionFilters) {
    collectionFilters.querySelectorAll('.collection-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.collection === '');
    });
  }

  // Clear ingredient search
  selectedIngredients = [];
  renderSelectedIngredients();
  const ingredientInput = document.getElementById('ingredient-input');
  if (ingredientInput) ingredientInput.value = '';
  const resultsDiv = document.getElementById('ingredient-search-results');
  if (resultsDiv) resultsDiv.classList.add('hidden');

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
