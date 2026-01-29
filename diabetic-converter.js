/**
 * Diabetic-Friendly Recipe Converter
 *
 * Analyzes recipe ingredients for high-carb items and suggests low-carb
 * substitutions with side-by-side comparison. Target: under 50g net carbs
 * per serving (configurable).
 *
 * Loads data from:
 *   data/carb-database.json
 *   data/diabetic-substitutions.json
 *
 * DISCLAIMER: This tool provides general dietary information only.
 * It is NOT medical advice. Always consult your doctor, endocrinologist,
 * or registered dietitian before making significant dietary changes.
 *
 * Sources: ADA Standards of Care 2026, USDA FoodData Central,
 * University of Sydney GI Database, Cleveland Clinic research (2023-2024)
 */

const DiabeticConverter = (function() {
  'use strict';

  // Module state
  let carbDatabase = null;
  let substitutionRules = null;
  let isLoaded = false;
  let loadingPromise = null;

  // Default target: 50g net carbs per serving
  const DEFAULT_TARGET_NET_CARBS = 50;

  /**
   * Load both data files
   */
  async function loadData() {
    if (isLoaded && carbDatabase && substitutionRules) {
      return { carbDatabase, substitutionRules };
    }

    if (loadingPromise) {
      return loadingPromise;
    }

    loadingPromise = (async () => {
      try {
        const [carbResp, subResp] = await Promise.all([
          fetch('data/carb-database.json'),
          fetch('data/diabetic-substitutions.json')
        ]);

        if (!carbResp.ok || !subResp.ok) {
          console.warn('Diabetic converter data not available');
          return null;
        }

        carbDatabase = await carbResp.json();
        substitutionRules = await subResp.json();
        isLoaded = true;
        console.log('Diabetic converter data loaded:', substitutionRules.meta.version);
        return { carbDatabase, substitutionRules };
      } catch (error) {
        console.error('Failed to load diabetic converter data:', error);
        return null;
      }
    })();

    return loadingPromise;
  }

  /**
   * Analyze a recipe for high-carb ingredients and suggest substitutions
   * @param {Object} recipe - The recipe to analyze
   * @param {number} targetNetCarbs - Target net carbs per serving (default 50)
   * @returns {Object} - Analysis results
   */
  function analyzeRecipe(recipe, targetNetCarbs) {
    if (!substitutionRules || !recipe?.ingredients) {
      return { flaggedIngredients: [], hasHighCarb: false, currentCarbs: null };
    }

    const target = targetNetCarbs || DEFAULT_TARGET_NET_CARBS;
    const categories = substitutionRules.categories;
    const flagged = [];

    // Check each ingredient against all substitution categories
    for (let i = 0; i < recipe.ingredients.length; i++) {
      const ingredient = recipe.ingredients[i];
      const ingText = normalizeIngredientText(ingredient);

      for (const [catKey, category] of Object.entries(categories)) {
        if (!category.detection_keywords) continue;

        const matched = category.detection_keywords.some(function(kw) {
          return ingText.includes(kw.toLowerCase());
        });

        if (matched) {
          flagged.push({
            index: i,
            ingredient: typeof ingredient === 'string' ? ingredient : ingredient.item || '',
            ingredientFull: formatIngredientDisplay(ingredient),
            categoryKey: catKey,
            categoryLabel: category.label,
            categoryIcon: category.icon,
            original: category.original,
            substitutes: category.substitutes || []
          });
          break; // One category match per ingredient
        }
      }
    }

    // Get current carbs from existing nutrition data
    const currentCarbs = recipe.nutrition?.per_serving?.carbs_g || null;
    const currentFiber = recipe.nutrition?.per_serving?.fiber_g || null;
    const currentNetCarbs = currentCarbs !== null && currentFiber !== null
      ? Math.max(0, currentCarbs - currentFiber)
      : currentCarbs;

    const isHighCarb = currentNetCarbs !== null ? currentNetCarbs > target : flagged.length > 0;

    return {
      flaggedIngredients: flagged,
      hasHighCarb: isHighCarb,
      hasFlaggedIngredients: flagged.length > 0,
      currentCarbs: currentCarbs,
      currentFiber: currentFiber,
      currentNetCarbs: currentNetCarbs,
      currentProtein: recipe.nutrition?.per_serving?.protein_g || null,
      currentCalories: recipe.nutrition?.per_serving?.calories || null,
      targetNetCarbs: target,
      overTarget: currentNetCarbs !== null ? currentNetCarbs > target : null,
      overAmount: currentNetCarbs !== null && currentNetCarbs > target
        ? currentNetCarbs - target : 0,
      recipeTitle: recipe.title || 'This recipe'
    };
  }

  /**
   * Normalize ingredient text for keyword matching
   */
  function normalizeIngredientText(ingredient) {
    if (typeof ingredient === 'string') {
      return ingredient.toLowerCase();
    }
    // Handle object-format ingredients: combine item, prep_note, etc.
    const parts = [
      ingredient.item || '',
      ingredient.prep_note || ''
    ];
    return parts.join(' ').toLowerCase();
  }

  /**
   * Format ingredient for display
   */
  function formatIngredientDisplay(ingredient) {
    if (typeof ingredient === 'string') return ingredient;
    const parts = [];
    if (ingredient.quantity) parts.push(ingredient.quantity);
    if (ingredient.unit) parts.push(ingredient.unit);
    if (ingredient.item) parts.push(ingredient.item);
    if (ingredient.prep_note) parts.push('(' + ingredient.prep_note + ')');
    return parts.join(' ') || ingredient.item || '';
  }

  /**
   * Estimate carb savings from applying a substitution
   */
  function estimateCarbSavings(flaggedItem, substituteId) {
    const sub = flaggedItem.substitutes.find(function(s) { return s.id === substituteId; });
    if (!sub) return 0;
    return sub.carbs_saved_per_cup || sub.carbs_saved || 0;
  }

  /**
   * Get the GI category label and color
   */
  function getGiInfo(gi) {
    if (!carbDatabase?.gi_categories) return { label: 'Unknown', color: '#999' };
    if (gi <= 55) return { label: 'Low GI', color: '#4caf50' };
    if (gi <= 69) return { label: 'Medium GI', color: '#ff9800' };
    return { label: 'High GI', color: '#f44336' };
  }

  /**
   * Render the full diabetic converter panel HTML
   * @param {Object} analysis - From analyzeRecipe()
   * @returns {string} - HTML string
   */
  function renderPanel(analysis) {
    if (!analysis.hasFlaggedIngredients) {
      return '';
    }

    const carbMeter = renderCarbMeter(analysis);
    const ingredientCards = analysis.flaggedIngredients.map(function(f) {
      return renderFlaggedIngredient(f);
    }).join('');
    const tipsHtml = renderBloodSugarTips();
    const disclaimer = renderDisclaimer();

    return '<details class="diabetic-panel">' +
      '<summary class="diabetic-header">' +
        '<span class="diabetic-icon">' +
          '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">' +
            '<path d="M12 2C8 6 4 10 4 14a8 8 0 0016 0c0-4-4-8-8-12z"/>' +
            '<path d="M12 18v-4m0 0l-2-2m2 2l2-2"/>' +
          '</svg>' +
        '</span>' +
        '<span class="diabetic-title">Diabetic-Friendly Converter</span>' +
        '<span class="diabetic-count">(' + analysis.flaggedIngredients.length + ' high-carb ingredients found)</span>' +
        '<span class="chevron">\u25B6</span>' +
      '</summary>' +
      '<div class="diabetic-content">' +
        carbMeter +
        '<p class="diabetic-intro">' +
          'This recipe contains ingredients that can be substituted with lower-carb alternatives. ' +
          'Click each ingredient below to see options.' +
        '</p>' +
        '<div class="diabetic-flagged-list">' +
          ingredientCards +
        '</div>' +
        tipsHtml +
        disclaimer +
      '</div>' +
    '</details>';
  }

  /**
   * Render the carb meter showing current vs target
   */
  function renderCarbMeter(analysis) {
    if (analysis.currentNetCarbs === null) {
      return '<div class="carb-meter carb-meter-no-data">' +
        '<p class="carb-meter-label">Nutrition data not available for this recipe. ' +
        'Substitutions below are based on ingredient detection.</p>' +
      '</div>';
    }

    var percent = Math.min(100, Math.round((analysis.currentNetCarbs / analysis.targetNetCarbs) * 100));
    var statusClass = analysis.overTarget ? 'carb-over' : 'carb-under';
    var statusLabel = analysis.overTarget
      ? 'Over target by ' + analysis.overAmount + 'g'
      : 'Within target';

    return '<div class="carb-meter ' + statusClass + '">' +
      '<div class="carb-meter-header">' +
        '<span class="carb-meter-label">Net Carbs Per Serving</span>' +
        '<span class="carb-meter-target">Target: &lt;' + analysis.targetNetCarbs + 'g</span>' +
      '</div>' +
      '<div class="carb-meter-bar-container">' +
        '<div class="carb-meter-bar" style="width: ' + Math.min(percent, 100) + '%"></div>' +
        '<div class="carb-meter-threshold" style="left: ' + Math.min(100, Math.round((analysis.targetNetCarbs / Math.max(analysis.currentNetCarbs, analysis.targetNetCarbs)) * 100)) + '%"></div>' +
      '</div>' +
      '<div class="carb-meter-values">' +
        '<div class="carb-value-current">' +
          '<span class="carb-number">' + Math.round(analysis.currentNetCarbs) + 'g</span>' +
          '<span class="carb-label">current net carbs</span>' +
        '</div>' +
        '<div class="carb-value-status ' + statusClass + '-badge">' +
          statusLabel +
        '</div>' +
      '</div>' +
      (analysis.currentCarbs !== null ? '<div class="carb-detail-row">' +
        '<span>Total carbs: ' + analysis.currentCarbs + 'g</span>' +
        (analysis.currentFiber !== null ? ' <span>Fiber: ' + analysis.currentFiber + 'g</span>' : '') +
        (analysis.currentProtein !== null ? ' <span>Protein: ' + analysis.currentProtein + 'g</span>' : '') +
      '</div>' : '') +
    '</div>';
  }

  /**
   * Render a single flagged ingredient with its substitution options
   */
  function renderFlaggedIngredient(flagged) {
    var originalGi = flagged.original?.gi || null;
    var giInfo = originalGi !== null ? getGiInfo(originalGi) : null;

    var subsHtml = flagged.substitutes.map(function(sub) {
      return renderSubstituteOption(sub, flagged);
    }).join('');

    return '<details class="diabetic-ingredient-card">' +
      '<summary class="diabetic-ingredient-header">' +
        '<span class="diabetic-ingredient-name">' + escapeHtml(flagged.ingredientFull) + '</span>' +
        '<span class="diabetic-category-badge">' + escapeHtml(flagged.categoryLabel) + '</span>' +
        (giInfo ? '<span class="gi-badge" style="background-color: ' + giInfo.color + '">' + giInfo.label + '</span>' : '') +
        '<span class="chevron-small">\u25B6</span>' +
      '</summary>' +
      '<div class="diabetic-ingredient-content">' +
        (flagged.original ? '<div class="diabetic-original-info">' +
          '<strong>Original:</strong> ' + escapeHtml(flagged.original.name) +
          ' (' + (flagged.original.net_carbs_per_cup ? flagged.original.net_carbs_per_cup + 'g net carbs/cup' :
                  flagged.original.net_carbs_per_slice ? flagged.original.net_carbs_per_slice + 'g net carbs/slice' :
                  flagged.original.net_carbs_per_tortilla ? flagged.original.net_carbs_per_tortilla + 'g net carbs/tortilla' :
                  flagged.original.net_carbs_per_tbsp ? flagged.original.net_carbs_per_tbsp + 'g net carbs/tbsp' : '') +
          ', GI: ' + (flagged.original.gi || 'N/A') + ')' +
        '</div>' : '') +
        '<div class="diabetic-substitutes">' +
          '<h5 class="diabetic-sub-heading">Lower-Carb Alternatives:</h5>' +
          subsHtml +
        '</div>' +
      '</div>' +
    '</details>';
  }

  /**
   * Render a single substitute option
   */
  function renderSubstituteOption(sub, flagged) {
    var subGi = getGiInfo(sub.gi || 0);
    var carbsSaved = sub.carbs_saved_per_cup || sub.carbs_saved || 0;
    var hasCardioWarning = sub.cardiovascular_warning === true;
    var hasAllergen = !!sub.allergen_warning;

    // Build warnings HTML
    var warningsHtml = '';
    if (hasCardioWarning) {
      warningsHtml += '<div class="diabetic-warning diabetic-warning-cardio">' +
        '<strong>Cardiovascular Concern:</strong> ' + escapeHtml(sub.safety_notes) +
      '</div>';
    }
    if (hasAllergen) {
      warningsHtml += '<div class="diabetic-warning diabetic-warning-allergen">' +
        '<strong>Allergen:</strong> ' + escapeHtml(sub.allergen_warning) +
      '</div>';
    }
    if (sub.moisture_warning) {
      warningsHtml += '<div class="diabetic-warning diabetic-warning-moisture">' +
        '<strong>Moisture:</strong> ' + escapeHtml(sub.moisture_warning) +
      '</div>';
    }
    if (sub.warning) {
      warningsHtml += '<div class="diabetic-warning diabetic-warning-general">' +
        escapeHtml(sub.warning) +
      '</div>';
    }

    return '<div class="diabetic-sub-option' + (sub.recommended_first_choice ? ' diabetic-recommended' : '') + '">' +
      '<div class="diabetic-sub-header">' +
        '<span class="diabetic-sub-name">' + escapeHtml(sub.name) + '</span>' +
        (sub.recommended_first_choice ? '<span class="diabetic-recommended-badge">Recommended</span>' : '') +
        '<span class="gi-badge-small" style="background-color: ' + subGi.color + '">' + subGi.label + '</span>' +
      '</div>' +

      '<div class="diabetic-sub-stats">' +
        (sub.net_carbs_per_cup !== undefined ? '<span class="stat-item"><strong>' + sub.net_carbs_per_cup + 'g</strong> net carbs/cup</span>' :
         sub.net_carbs_per_serving !== undefined ? '<span class="stat-item"><strong>' + sub.net_carbs_per_serving + 'g</strong> net carbs</span>' :
         sub.net_carbs_per_tbsp !== undefined ? '<span class="stat-item"><strong>' + sub.net_carbs_per_tbsp + 'g</strong> net carbs/tbsp</span>' : '') +
        (carbsSaved > 0 ? '<span class="stat-item stat-saved">saves ' + carbsSaved + 'g carbs</span>' : '') +
        (sub.protein_per_cup ? '<span class="stat-item">' + sub.protein_per_cup + 'g protein/cup</span>' : '') +
        (sub.fiber_per_cup ? '<span class="stat-item">' + sub.fiber_per_cup + 'g fiber/cup</span>' : '') +
      '</div>' +

      '<div class="diabetic-sub-details">' +
        (sub.ratio ? '<p><strong>Ratio:</strong> ' + escapeHtml(sub.ratio) + '</p>' : '') +
        (sub.prep_notes ? '<p><strong>Prep:</strong> ' + escapeHtml(sub.prep_notes) + '</p>' : '') +
        (sub.cooking_notes ? '<p><strong>Cooking:</strong> ' + escapeHtml(sub.cooking_notes) + '</p>' : '') +
        (sub.taste_impact ? '<p><strong>Taste:</strong> ' + escapeHtml(sub.taste_impact) + '</p>' : '') +
        (sub.texture_impact ? '<p><strong>Texture:</strong> ' + escapeHtml(sub.texture_impact) + '</p>' : '') +
        (sub.baking_tips ? '<p><strong>Baking tips:</strong> ' + escapeHtml(sub.baking_tips) + '</p>' : '') +
        (sub.best_for ? '<p><strong>Best for:</strong> ' + sub.best_for.map(escapeHtml).join(', ') + '</p>' : '') +
        (sub.avoid_for ? '<p><strong>Avoid for:</strong> ' + sub.avoid_for.map(escapeHtml).join(', ') + '</p>' : '') +
      '</div>' +

      warningsHtml +
    '</div>';
  }

  /**
   * Render blood sugar tips section
   */
  function renderBloodSugarTips() {
    if (!substitutionRules?.blood_sugar_tips) return '';

    var tips = substitutionRules.blood_sugar_tips.general || [];
    if (tips.length === 0) return '';

    return '<details class="diabetic-tips-section">' +
      '<summary class="diabetic-tips-header">' +
        '<span class="diabetic-tips-icon">' +
          '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">' +
            '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/>' +
          '</svg>' +
        '</span>' +
        ' Blood Sugar Management Tips' +
        '<span class="chevron-small">\u25B6</span>' +
      '</summary>' +
      '<ul class="diabetic-tips-list">' +
        tips.map(function(tip) { return '<li>' + escapeHtml(tip) + '</li>'; }).join('') +
      '</ul>' +
    '</details>';
  }

  /**
   * Render medical disclaimer
   */
  function renderDisclaimer() {
    return '<div class="diabetic-disclaimer">' +
      '<strong>Important:</strong> This tool provides general dietary information only. ' +
      'It is NOT medical advice. Always consult your doctor, endocrinologist, or ' +
      'registered dietitian before making significant dietary changes. Individual blood sugar ' +
      'responses to foods vary. Monitor your blood sugar when trying new substitutions.' +
    '</div>';
  }

  /**
   * Escape HTML special characters
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
   * Initialize the converter panel for a recipe
   * @param {Object} recipe - The recipe object
   * @param {string} containerId - ID of the container element
   * @param {number} targetNetCarbs - Optional target (default 50)
   */
  async function initPanel(recipe, containerId, targetNetCarbs) {
    var container = document.getElementById(containerId);
    if (!container) return;

    await loadData();
    if (!substitutionRules) {
      container.innerHTML = '';
      return;
    }

    var analysis = analyzeRecipe(recipe, targetNetCarbs || DEFAULT_TARGET_NET_CARBS);
    var html = renderPanel(analysis);
    container.innerHTML = html;
  }

  // Public API
  return {
    loadData: loadData,
    analyzeRecipe: analyzeRecipe,
    renderPanel: renderPanel,
    initPanel: initPanel,
    getGiInfo: getGiInfo,
    estimateCarbSavings: estimateCarbSavings,
    DEFAULT_TARGET_NET_CARBS: DEFAULT_TARGET_NET_CARBS
  };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = DiabeticConverter;
}
