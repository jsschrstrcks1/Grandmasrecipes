/**
 * Protein & Vegetable Substitution Tool
 *
 * Provides interactive substitution suggestions for proteins and vegetables
 * in recipes, with cooking time adjustments, flavor notes, and safety information.
 * Loads data from data/protein-vegetable-substitutions.json.
 */

const ProteinSubstitution = (function() {
  'use strict';

  // Module state
  let substitutionData = null;
  let isLoaded = false;
  let loadingPromise = null;

  // Protein detection keywords (maps to JSON keys)
  const PROTEIN_KEYWORDS = {
    'chicken_breast': ['chicken breast', 'boneless chicken', 'skinless chicken breast', 'chicken cutlet'],
    'chicken_thighs': ['chicken thigh', 'chicken thighs', 'bone-in chicken', 'dark meat chicken'],
    'ground_beef': ['ground beef', 'minced beef', 'hamburger meat', 'beef mince'],
    'beef_stew_meat': ['beef stew', 'stew meat', 'beef chuck', 'chuck roast', 'beef cubes'],
    'beef_roast': ['beef roast', 'pot roast', 'rib roast', 'prime rib', 'standing rib'],
    'bacon': ['bacon', 'bacon strips', 'bacon slices', 'streaky bacon']
  };

  // Fish category keywords
  const FISH_KEYWORDS = {
    'cod': ['cod', 'codfish', 'atlantic cod', 'pacific cod'],
    'tilapia': ['tilapia'],
    'halibut': ['halibut'],
    'salmon': ['salmon', 'atlantic salmon', 'sockeye', 'chinook', 'coho'],
    'tuna_steak': ['tuna steak', 'ahi tuna', 'yellowfin', 'bigeye tuna']
  };

  // Shellfish keywords
  const SHELLFISH_KEYWORDS = {
    'shrimp': ['shrimp', 'prawns', 'jumbo shrimp', 'large shrimp'],
    'scallops': ['scallop', 'scallops', 'sea scallops', 'bay scallops'],
    'lobster': ['lobster', 'lobster tail', 'lobster meat'],
    'crab': ['crab', 'crab meat', 'lump crab', 'claw meat']
  };

  // High-moisture vegetable keywords (for warnings)
  const HIGH_MOISTURE_VEGETABLES = {
    'zucchini': ['zucchini', 'courgette', 'summer squash'],
    'tomatoes': ['tomato', 'tomatoes', 'cherry tomato', 'roma tomato', 'fresh tomato'],
    'mushrooms': ['mushroom', 'mushrooms', 'cremini', 'shiitake', 'portobello', 'button mushroom'],
    'cucumbers': ['cucumber', 'cucumbers'],
    'eggplant': ['eggplant', 'aubergine']
  };

  /**
   * Load substitution data from JSON file
   */
  async function loadData() {
    if (isLoaded && substitutionData) {
      return substitutionData;
    }

    if (loadingPromise) {
      return loadingPromise;
    }

    loadingPromise = (async () => {
      try {
        const response = await fetch('data/protein-vegetable-substitutions.json');
        if (!response.ok) {
          console.warn('Protein substitution data not available');
          return null;
        }
        substitutionData = await response.json();
        isLoaded = true;
        console.log('Protein substitution data loaded:', substitutionData.meta.version);
        return substitutionData;
      } catch (error) {
        console.error('Failed to load protein substitution data:', error);
        return null;
      }
    })();

    return loadingPromise;
  }

  /**
   * Detect proteins in recipe ingredients
   * @param {Array} ingredients - Array of ingredient objects
   * @returns {Array} - Array of detected proteins with their data
   */
  function detectProteins(ingredients) {
    if (!substitutionData || !ingredients) return [];

    const detected = [];

    for (const ingredient of ingredients) {
      const ingText = (typeof ingredient === 'string' ? ingredient : ingredient.item || '').toLowerCase();

      // Check meat/poultry proteins
      for (const [proteinKey, keywords] of Object.entries(PROTEIN_KEYWORDS)) {
        if (keywords.some(kw => ingText.includes(kw))) {
          const proteinData = substitutionData.protein_substitutions?.[proteinKey];
          if (proteinData) {
            detected.push({
              type: 'protein',
              key: proteinKey,
              ingredient: typeof ingredient === 'string' ? ingredient : ingredient.item,
              data: proteinData
            });
          }
          break;
        }
      }

      // Check fish
      for (const [fishKey, keywords] of Object.entries(FISH_KEYWORDS)) {
        if (keywords.some(kw => ingText.includes(kw))) {
          const fishData = substitutionData.fish_substitutions?.specific_substitutions?.[fishKey];
          if (fishData) {
            detected.push({
              type: 'fish',
              key: fishKey,
              ingredient: typeof ingredient === 'string' ? ingredient : ingredient.item,
              data: fishData,
              category: fishData.category,
              mercuryInfo: getMercuryCategory(fishKey)
            });
          }
          break;
        }
      }

      // Check shellfish
      for (const [shellfishKey, keywords] of Object.entries(SHELLFISH_KEYWORDS)) {
        if (keywords.some(kw => ingText.includes(kw))) {
          const shellfishData = substitutionData.shellfish_substitutions?.[shellfishKey];
          if (shellfishData) {
            detected.push({
              type: 'shellfish',
              key: shellfishKey,
              ingredient: typeof ingredient === 'string' ? ingredient : ingredient.item,
              data: shellfishData
            });
          }
          break;
        }
      }
    }

    return detected;
  }

  /**
   * Detect high-moisture vegetables that need warnings
   * @param {Array} ingredients - Array of ingredient objects
   * @returns {Array} - Array of detected vegetables with moisture warnings
   */
  function detectHighMoistureVegetables(ingredients) {
    if (!substitutionData || !ingredients) return [];

    const detected = [];
    const moistureData = substitutionData.vegetable_substitutions?.high_moisture_warnings?.vegetables;
    if (!moistureData) return [];

    for (const ingredient of ingredients) {
      const ingText = (typeof ingredient === 'string' ? ingredient : ingredient.item || '').toLowerCase();

      for (const [vegKey, keywords] of Object.entries(HIGH_MOISTURE_VEGETABLES)) {
        if (keywords.some(kw => ingText.includes(kw))) {
          const vegData = moistureData[vegKey];
          if (vegData) {
            detected.push({
              type: 'vegetable',
              key: vegKey,
              ingredient: typeof ingredient === 'string' ? ingredient : ingredient.item,
              data: vegData
            });
          }
          break;
        }
      }
    }

    return detected;
  }

  /**
   * Get mercury category for a fish
   * @param {string} fishKey - The fish key
   * @returns {Object|null} - Mercury category info
   */
  function getMercuryCategory(fishKey) {
    if (!substitutionData?.fish_substitutions?.mercury_guide) return null;

    const mercuryGuide = substitutionData.fish_substitutions.mercury_guide;
    const fishLower = fishKey.toLowerCase();

    if (mercuryGuide.best_choices.fish.includes(fishLower)) {
      return { category: 'best', description: mercuryGuide.best_choices.description };
    }
    if (mercuryGuide.good_choices.fish.includes(fishLower)) {
      return { category: 'good', description: mercuryGuide.good_choices.description };
    }
    if (mercuryGuide.avoid.fish.includes(fishLower)) {
      return { category: 'avoid', description: mercuryGuide.avoid.description, warning: mercuryGuide.avoid.warning };
    }
    return null;
  }

  /**
   * Get safe cooking temperature for a protein type
   * @param {string} proteinType - The protein type (beef, pork, poultry, fish)
   * @returns {Object|null} - Temperature info
   */
  function getSafeTemperature(proteinType) {
    if (!substitutionData?.safe_temperatures) return null;

    const temps = substitutionData.safe_temperatures;
    const typeLower = proteinType.toLowerCase();

    if (typeLower.includes('chicken') || typeLower.includes('turkey') || typeLower.includes('poultry')) {
      return temps.poultry?.all;
    }
    if (typeLower.includes('ground')) {
      return temps.beef_pork_lamb_veal?.ground;
    }
    if (typeLower.includes('beef') || typeLower.includes('pork') || typeLower.includes('lamb')) {
      return temps.beef_pork_lamb_veal?.steaks_chops_roasts;
    }
    if (typeLower.includes('fish') || typeLower.includes('seafood')) {
      return temps.fish_shellfish?.fish;
    }
    return null;
  }

  /**
   * Analyze recipe for substitution opportunities
   * @param {Object} recipe - The recipe to analyze
   * @returns {Object} - Analysis results
   */
  async function analyzeRecipe(recipe) {
    await loadData();
    if (!substitutionData || !recipe?.ingredients) {
      return { proteins: [], vegetables: [], hasSubstitutions: false };
    }

    const proteins = detectProteins(recipe.ingredients);
    const vegetables = detectHighMoistureVegetables(recipe.ingredients);

    return {
      proteins,
      vegetables,
      hasSubstitutions: proteins.length > 0 || vegetables.length > 0
    };
  }

  /**
   * Render substitution panel HTML
   * @param {Object} analysis - Analysis results from analyzeRecipe
   * @returns {string} - HTML string
   */
  function renderSubstitutionPanel(analysis) {
    if (!analysis.hasSubstitutions) {
      return '';
    }

    const proteinCards = analysis.proteins.map(p => renderProteinCard(p)).join('');
    const vegetableCards = analysis.vegetables.map(v => renderVegetableCard(v)).join('');

    const totalItems = analysis.proteins.length + analysis.vegetables.length;

    return `
      <details class="substitution-panel">
        <summary class="substitution-header">
          <span class="substitution-icon">🔄</span>
          <span class="substitution-title">Substitution Options</span>
          <span class="substitution-count">(${totalItems} ingredients)</span>
          <span class="chevron">▶</span>
        </summary>
        <div class="substitution-content">
          <p class="substitution-intro">Click any ingredient below to see substitution options with cooking adjustments.</p>

          ${proteinCards ? `
            <div class="substitution-section">
              <h4 class="substitution-section-title">Proteins</h4>
              ${proteinCards}
            </div>
          ` : ''}

          ${vegetableCards ? `
            <div class="substitution-section">
              <h4 class="substitution-section-title">High-Moisture Vegetables</h4>
              <p class="moisture-intro">These vegetables release water during cooking. See tips to prevent soggy dishes.</p>
              ${vegetableCards}
            </div>
          ` : ''}

          <p class="substitution-disclaimer">
            <strong>Note:</strong> Cooking times and temperatures are guidelines.
            Always use a food thermometer to ensure proteins reach safe internal temperatures.
          </p>
        </div>
      </details>
    `;
  }

  /**
   * Render a protein substitution card
   * @param {Object} protein - Detected protein info
   * @returns {string} - HTML string
   */
  function renderProteinCard(protein) {
    const data = protein.data;
    const safeTemp = data.characteristics?.internal_temp_f || getSafeTemperature(protein.key)?.temp_f;

    let substitutesHtml = '';
    if (data.substitutes && data.substitutes.length > 0) {
      substitutesHtml = data.substitutes.map(sub => `
        <div class="substitute-option">
          <div class="substitute-header">
            <span class="substitute-name">${escapeHtml(sub.display_name)}</span>
            <span class="substitute-ratio">${escapeHtml(sub.ratio)}</span>
          </div>
          <div class="substitute-details">
            <p class="substitute-time"><strong>Cook time:</strong> ${escapeHtml(sub.cook_time_adjustment)}</p>
            <p class="substitute-flavor"><strong>Flavor:</strong> ${escapeHtml(sub.flavor_notes)}</p>
            <p class="substitute-tip"><strong>Tip:</strong> ${escapeHtml(sub.tips)}</p>
            <p class="substitute-best-for"><strong>Best for:</strong> ${sub.best_for.map(b => escapeHtml(b)).join(', ')}</p>
          </div>
        </div>
      `).join('');
    }

    // Mercury warning for fish
    let mercuryHtml = '';
    if (protein.type === 'fish' && protein.mercuryInfo) {
      const mercuryClass = protein.mercuryInfo.category === 'avoid' ? 'mercury-warning-high' :
                          protein.mercuryInfo.category === 'good' ? 'mercury-warning-moderate' : 'mercury-warning-low';
      mercuryHtml = `
        <div class="mercury-badge ${mercuryClass}">
          <strong>Mercury:</strong> ${protein.mercuryInfo.description}
          ${protein.mercuryInfo.warning ? `<br><em>${escapeHtml(protein.mercuryInfo.warning)}</em>` : ''}
        </div>
      `;
    }

    return `
      <details class="protein-card">
        <summary class="protein-card-header">
          <span class="protein-name">${escapeHtml(protein.ingredient)}</span>
          ${safeTemp ? `<span class="safe-temp-badge">${safeTemp}°F safe</span>` : ''}
          <span class="chevron-small">▶</span>
        </summary>
        <div class="protein-card-content">
          ${data.characteristics ? `
            <div class="protein-characteristics">
              <span class="char-item"><strong>Fat:</strong> ${escapeHtml(data.characteristics.fat_content)}</span>
              <span class="char-item"><strong>Texture:</strong> ${escapeHtml(data.characteristics.texture)}</span>
              ${data.characteristics.cook_time_per_lb ? `<span class="char-item"><strong>Cook time:</strong> ${escapeHtml(data.characteristics.cook_time_per_lb)}</span>` : ''}
            </div>
          ` : ''}

          ${mercuryHtml}

          ${substitutesHtml ? `
            <div class="substitutes-list">
              <h5>Substitution Options:</h5>
              ${substitutesHtml}
            </div>
          ` : ''}
        </div>
      </details>
    `;
  }

  /**
   * Render a vegetable moisture card
   * @param {Object} vegetable - Detected vegetable info
   * @returns {string} - HTML string
   */
  function renderVegetableCard(vegetable) {
    const data = vegetable.data;

    const mitigationHtml = data.mitigation && data.mitigation.length > 0
      ? `<ul class="mitigation-list">${data.mitigation.map(m => `<li>${escapeHtml(m)}</li>`).join('')}</ul>`
      : '';

    return `
      <details class="vegetable-card">
        <summary class="vegetable-card-header">
          <span class="vegetable-name">${escapeHtml(vegetable.ingredient)}</span>
          <span class="moisture-badge">${data.water_content} water</span>
          <span class="chevron-small">▶</span>
        </summary>
        <div class="vegetable-card-content">
          <p class="vegetable-warning"><strong>Warning:</strong> ${escapeHtml(data.warning)}</p>
          ${mitigationHtml ? `
            <div class="mitigation-section">
              <strong>How to prevent soggy results:</strong>
              ${mitigationHtml}
            </div>
          ` : ''}
        </div>
      </details>
    `;
  }

  /**
   * Escape HTML special characters
   * @param {string} str - String to escape
   * @returns {string} - Escaped string
   */
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Initialize the substitution panel for a recipe
   * @param {Object} recipe - The recipe object
   * @param {string} containerId - ID of the container element
   */
  async function initPanel(recipe, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const analysis = await analyzeRecipe(recipe);
    const html = renderSubstitutionPanel(analysis);
    container.innerHTML = html;
  }

  // Public API
  return {
    loadData,
    analyzeRecipe,
    detectProteins,
    detectHighMoistureVegetables,
    getSafeTemperature,
    getMercuryCategory,
    renderSubstitutionPanel,
    initPanel
  };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ProteinSubstitution;
}
