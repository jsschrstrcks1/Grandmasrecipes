/**
 * Heart-Smart Recipe Converter
 *
 * Analyzes recipe ingredients for high-sodium, high-saturated-fat, and
 * high-cholesterol items, and suggests heart-healthy substitutions with
 * flavor enhancement recommendations.
 *
 * Targets (per serving):
 *   - Sodium: <600mg (AHA recommendation)
 *   - Saturated Fat: <5g
 *   - Cholesterol: <100mg
 *
 * Loads data from:
 *   data/heart-smart-database.json
 *
 * DISCLAIMER: This tool provides general dietary information only.
 * It is NOT medical advice. Always consult your doctor, cardiologist,
 * or registered dietitian before making significant dietary changes.
 *
 * Sources: AHA, USDA FoodData Central, Cleveland Clinic, NIH, Mayo Clinic
 */

const HeartSmartConverter = (function() {
  'use strict';

  // Module state
  let heartSmartDatabase = null;
  let isLoaded = false;
  let loadingPromise = null;

  // Default targets per serving
  const DEFAULT_TARGETS = {
    sodium_mg: 600,
    saturated_fat_g: 5,
    cholesterol_mg: 100,
    fiber_g_min: 5
  };

  /**
   * Load the heart-smart database
   */
  async function loadData() {
    if (isLoaded && heartSmartDatabase) {
      return heartSmartDatabase;
    }

    if (loadingPromise) {
      return loadingPromise;
    }

    loadingPromise = (async () => {
      try {
        const response = await fetch('data/heart-smart-database.json');
        if (!response.ok) {
          console.warn('Heart-smart converter data not available');
          return null;
        }

        heartSmartDatabase = await response.json();
        isLoaded = true;
        console.log('Heart-smart converter data loaded:', heartSmartDatabase.meta.version);
        return heartSmartDatabase;
      } catch (error) {
        console.error('Failed to load heart-smart converter data:', error);
        return null;
      }
    })();

    return loadingPromise;
  }

  /**
   * Analyze a recipe for heart-health concerns
   * @param {Object} recipe - The recipe to analyze
   * @param {Object} targets - Custom targets (optional)
   * @returns {Object} - Analysis results
   */
  function analyzeRecipe(recipe, targets) {
    if (!heartSmartDatabase || !recipe?.ingredients) {
      return { flaggedIngredients: [], hasConcerns: false };
    }

    const t = { ...DEFAULT_TARGETS, ...targets };
    const flagged = [];
    const detectedCategories = new Set();

    // Check sodium categories
    for (const [catKey, category] of Object.entries(heartSmartDatabase.sodium_categories || {})) {
      checkCategory(recipe.ingredients, catKey, category, 'sodium', flagged, detectedCategories);
    }

    // Check fat categories
    for (const [catKey, category] of Object.entries(heartSmartDatabase.fat_categories || {})) {
      checkCategory(recipe.ingredients, catKey, category, 'fat', flagged, detectedCategories);
    }

    // Get current nutrition data if available
    const currentSodium = recipe.nutrition?.per_serving?.sodium_mg || null;
    const currentSatFat = recipe.nutrition?.per_serving?.saturated_fat_g || null;
    const currentCholesterol = recipe.nutrition?.per_serving?.cholesterol_mg || null;
    const currentFiber = recipe.nutrition?.per_serving?.fiber_g || null;

    // Determine concerns
    const sodiumOver = currentSodium !== null ? currentSodium > t.sodium_mg : null;
    const satFatOver = currentSatFat !== null ? currentSatFat > t.saturated_fat_g : null;
    const cholesterolOver = currentCholesterol !== null ? currentCholesterol > t.cholesterol_mg : null;
    const fiberLow = currentFiber !== null ? currentFiber < t.fiber_g_min : null;

    return {
      flaggedIngredients: flagged,
      hasConcerns: flagged.length > 0,
      hasNutritionData: currentSodium !== null || currentSatFat !== null,

      // Current values
      currentSodium: currentSodium,
      currentSatFat: currentSatFat,
      currentCholesterol: currentCholesterol,
      currentFiber: currentFiber,

      // Targets
      targets: t,

      // Over/under status
      sodiumOver: sodiumOver,
      satFatOver: satFatOver,
      cholesterolOver: cholesterolOver,
      fiberLow: fiberLow,

      // Calculate amounts over
      sodiumOverAmount: sodiumOver ? currentSodium - t.sodium_mg : 0,
      satFatOverAmount: satFatOver ? currentSatFat - t.saturated_fat_g : 0,

      recipeTitle: recipe.title || 'This recipe'
    };
  }

  /**
   * Check a category for matching ingredients
   */
  function checkCategory(ingredients, catKey, category, concernType, flagged, detectedCategories) {
    if (!category.detection_keywords) return;

    for (let i = 0; i < ingredients.length; i++) {
      const ingredient = ingredients[i];
      const ingText = normalizeIngredientText(ingredient);

      const matched = category.detection_keywords.some(function(kw) {
        return ingText.includes(kw.toLowerCase());
      });

      if (matched && !detectedCategories.has(catKey + '-' + i)) {
        detectedCategories.add(catKey + '-' + i);
        flagged.push({
          index: i,
          ingredient: typeof ingredient === 'string' ? ingredient : ingredient.item || '',
          ingredientFull: formatIngredientDisplay(ingredient),
          categoryKey: catKey,
          categoryLabel: category.label,
          categoryIcon: category.icon,
          concernType: concernType,
          original: category.original,
          substitutes: category.substitutes || [],
          foodSafetyWarning: category.food_safety_warning || null
        });
        break; // One match per category per ingredient
      }
    }
  }

  /**
   * Normalize ingredient text for keyword matching
   */
  function normalizeIngredientText(ingredient) {
    if (typeof ingredient === 'string') {
      return ingredient.toLowerCase();
    }
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
   * Render the full heart-smart converter panel HTML
   * @param {Object} analysis - From analyzeRecipe()
   * @returns {string} - HTML string
   */
  function renderPanel(analysis) {
    if (!analysis.hasConcerns) {
      return '';
    }

    const metersHtml = renderHealthMeters(analysis);
    const ingredientCards = analysis.flaggedIngredients.map(function(f) {
      return renderFlaggedIngredient(f);
    }).join('');
    const flavorTipsHtml = renderFlavorEnhancementTips();
    const safetyWarningsHtml = renderFoodSafetyWarnings(analysis);
    const disclaimer = renderDisclaimer();

    return '<details class="heart-smart-panel">' +
      '<summary class="heart-smart-header">' +
        '<span class="heart-smart-icon">' +
          '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">' +
            '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>' +
          '</svg>' +
        '</span>' +
        '<span class="heart-smart-title">Heart-Smart Converter</span>' +
        '<span class="heart-smart-count">(' + analysis.flaggedIngredients.length + ' items to consider)</span>' +
        '<span class="chevron">\u25B6</span>' +
      '</summary>' +
      '<div class="heart-smart-content">' +
        metersHtml +
        '<p class="heart-smart-intro">' +
          'This recipe contains ingredients that can be substituted with heart-healthier alternatives. ' +
          'Click each ingredient below to see options for reducing sodium, saturated fat, or cholesterol.' +
        '</p>' +
        '<div class="heart-smart-flagged-list">' +
          ingredientCards +
        '</div>' +
        flavorTipsHtml +
        safetyWarningsHtml +
        disclaimer +
      '</div>' +
    '</details>';
  }

  /**
   * Render health meters for sodium, saturated fat, cholesterol
   */
  function renderHealthMeters(analysis) {
    if (!analysis.hasNutritionData) {
      return '<div class="heart-smart-meters heart-smart-no-data">' +
        '<p class="heart-smart-meter-label">Nutrition data not available for this recipe. ' +
        'Substitutions below are based on ingredient detection.</p>' +
      '</div>';
    }

    let metersHtml = '<div class="heart-smart-meters">';

    // Sodium meter
    if (analysis.currentSodium !== null) {
      metersHtml += renderSingleMeter(
        'Sodium',
        analysis.currentSodium,
        analysis.targets.sodium_mg,
        'mg',
        analysis.sodiumOver
      );
    }

    // Saturated fat meter
    if (analysis.currentSatFat !== null) {
      metersHtml += renderSingleMeter(
        'Saturated Fat',
        analysis.currentSatFat,
        analysis.targets.saturated_fat_g,
        'g',
        analysis.satFatOver
      );
    }

    // Cholesterol meter
    if (analysis.currentCholesterol !== null) {
      metersHtml += renderSingleMeter(
        'Cholesterol',
        analysis.currentCholesterol,
        analysis.targets.cholesterol_mg,
        'mg',
        analysis.cholesterolOver
      );
    }

    metersHtml += '</div>';
    return metersHtml;
  }

  /**
   * Render a single health meter
   */
  function renderSingleMeter(label, current, target, unit, isOver) {
    const percent = Math.min(150, Math.round((current / target) * 100));
    const statusClass = isOver ? 'meter-over' : 'meter-ok';
    const statusLabel = isOver ? 'Over target' : 'Within target';

    return '<div class="heart-smart-meter ' + statusClass + '">' +
      '<div class="meter-header">' +
        '<span class="meter-label">' + label + '</span>' +
        '<span class="meter-target">Target: &lt;' + target + unit + '</span>' +
      '</div>' +
      '<div class="meter-bar-container">' +
        '<div class="meter-bar" style="width: ' + Math.min(percent, 100) + '%"></div>' +
        '<div class="meter-threshold"></div>' +
      '</div>' +
      '<div class="meter-values">' +
        '<span class="meter-current"><strong>' + Math.round(current) + unit + '</strong></span>' +
        '<span class="meter-status ' + statusClass + '-badge">' + statusLabel + '</span>' +
      '</div>' +
    '</div>';
  }

  /**
   * Render a single flagged ingredient with its substitution options
   */
  function renderFlaggedIngredient(flagged) {
    const concernBadge = flagged.concernType === 'sodium'
      ? '<span class="concern-badge concern-sodium">High Sodium</span>'
      : '<span class="concern-badge concern-fat">High Sat Fat/Cholesterol</span>';

    const subsHtml = flagged.substitutes.map(function(sub) {
      return renderSubstituteOption(sub, flagged);
    }).join('');

    return '<details class="heart-smart-ingredient-card">' +
      '<summary class="heart-smart-ingredient-header">' +
        '<span class="heart-smart-ingredient-name">' + escapeHtml(flagged.ingredientFull) + '</span>' +
        '<span class="heart-smart-category-badge">' + escapeHtml(flagged.categoryLabel) + '</span>' +
        concernBadge +
        '<span class="chevron-small">\u25B6</span>' +
      '</summary>' +
      '<div class="heart-smart-ingredient-content">' +
        (flagged.original ? '<div class="heart-smart-original-info">' +
          '<strong>Original:</strong> ' + escapeHtml(flagged.original.name) +
          (flagged.original.sodium_per_tsp_mg ? ' (' + flagged.original.sodium_per_tsp_mg + 'mg sodium/tsp)' :
           flagged.original.sodium_per_tbsp_mg ? ' (' + flagged.original.sodium_per_tbsp_mg + 'mg sodium/tbsp)' :
           flagged.original.sodium_per_cup_mg ? ' (' + flagged.original.sodium_per_cup_mg + 'mg sodium/cup)' :
           flagged.original.sodium_per_oz_mg ? ' (' + flagged.original.sodium_per_oz_mg + 'mg sodium/oz)' :
           flagged.original.sodium_per_half_cup_mg ? ' (' + flagged.original.sodium_per_half_cup_mg + 'mg sodium/half cup)' :
           flagged.original.saturated_fat_per_tbsp_g ? ' (' + flagged.original.saturated_fat_per_tbsp_g + 'g sat fat/tbsp)' :
           flagged.original.saturated_fat_per_cup_g ? ' (' + flagged.original.saturated_fat_per_cup_g + 'g sat fat/cup)' :
           flagged.original.saturated_fat_per_3oz_g ? ' (' + flagged.original.saturated_fat_per_3oz_g + 'g sat fat/3oz)' :
           flagged.original.cholesterol_per_unit_mg ? ' (' + flagged.original.cholesterol_per_unit_mg + 'mg cholesterol)' : '') +
        '</div>' : '') +
        (flagged.original?.note ? '<p class="heart-smart-note"><em>' + escapeHtml(flagged.original.note) + '</em></p>' : '') +
        '<div class="heart-smart-substitutes">' +
          '<h5 class="heart-smart-sub-heading">Heart-Healthier Alternatives:</h5>' +
          subsHtml +
        '</div>' +
      '</div>' +
    '</details>';
  }

  /**
   * Render a single substitute option
   */
  function renderSubstituteOption(sub, flagged) {
    // Build stats
    let statsHtml = '<div class="heart-smart-sub-stats">';

    // Sodium savings
    if (sub.sodium_per_tsp_mg !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.sodium_per_tsp_mg + 'mg</strong> sodium/tsp</span>';
    }
    if (sub.sodium_per_tbsp_mg !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.sodium_per_tbsp_mg + 'mg</strong> sodium/tbsp</span>';
    }
    if (sub.sodium_per_cup_mg !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.sodium_per_cup_mg + 'mg</strong> sodium/cup</span>';
    }
    if (sub.sodium_per_oz_mg !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.sodium_per_oz_mg + 'mg</strong> sodium/oz</span>';
    }
    if (sub.sodium_per_half_cup_mg !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.sodium_per_half_cup_mg + 'mg</strong> sodium/half cup</span>';
    }
    if (sub.sodium_saved_mg) {
      statsHtml += '<span class="stat-item stat-saved">saves ' + sub.sodium_saved_mg + 'mg sodium</span>';
    }

    // Fat savings
    if (sub.saturated_fat_per_tbsp_g !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.saturated_fat_per_tbsp_g + 'g</strong> sat fat/tbsp</span>';
    }
    if (sub.saturated_fat_per_cup_g !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.saturated_fat_per_cup_g + 'g</strong> sat fat/cup</span>';
    }
    if (sub.saturated_fat_per_3oz_g !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.saturated_fat_per_3oz_g + 'g</strong> sat fat/3oz</span>';
    }
    if (sub.saturated_fat_saved_g) {
      statsHtml += '<span class="stat-item stat-saved">saves ' + sub.saturated_fat_saved_g + 'g sat fat</span>';
    }

    // Cholesterol
    if (sub.cholesterol_mg !== undefined) {
      statsHtml += '<span class="stat-item"><strong>' + sub.cholesterol_mg + 'mg</strong> cholesterol</span>';
    }
    if (sub.cholesterol_saved_mg) {
      statsHtml += '<span class="stat-item stat-saved">saves ' + sub.cholesterol_saved_mg + 'mg cholesterol</span>';
    }

    // Omega-3 bonus
    if (sub.omega3_bonus_g) {
      statsHtml += '<span class="stat-item stat-bonus">+' + sub.omega3_bonus_g + 'g omega-3</span>';
    }

    statsHtml += '</div>';

    // Build warnings
    let warningsHtml = '';
    if (sub.safety_warning) {
      warningsHtml += '<div class="heart-smart-warning heart-smart-warning-safety">' +
        '<strong>Safety Warning:</strong> ' + escapeHtml(sub.safety_warning) +
      '</div>';
    }
    if (sub.allergen_note) {
      warningsHtml += '<div class="heart-smart-warning heart-smart-warning-allergen">' +
        '<strong>Allergen:</strong> ' + escapeHtml(sub.allergen_note) +
      '</div>';
    }
    if (sub.warning) {
      warningsHtml += '<div class="heart-smart-warning heart-smart-warning-general">' +
        escapeHtml(sub.warning) +
      '</div>';
    }

    return '<div class="heart-smart-sub-option">' +
      '<div class="heart-smart-sub-header">' +
        '<span class="heart-smart-sub-name">' + escapeHtml(sub.name) + '</span>' +
        (sub.heart_benefit ? '<span class="heart-benefit-badge">Heart Benefit</span>' : '') +
      '</div>' +

      statsHtml +

      '<div class="heart-smart-sub-details">' +
        (sub.ratio ? '<p><strong>Ratio:</strong> ' + escapeHtml(sub.ratio) + '</p>' : '') +
        (sub.prep_notes ? '<p><strong>Prep:</strong> ' + escapeHtml(sub.prep_notes) + '</p>' : '') +
        (sub.cooking_notes ? '<p><strong>Cooking:</strong> ' + escapeHtml(sub.cooking_notes) + '</p>' : '') +
        (sub.taste_impact ? '<p><strong>Taste:</strong> ' + escapeHtml(sub.taste_impact) + '</p>' : '') +
        (sub.best_for ? '<p><strong>Best for:</strong> ' + (Array.isArray(sub.best_for) ? sub.best_for.map(escapeHtml).join(', ') : escapeHtml(sub.best_for)) + '</p>' : '') +
        (sub.avoid_for ? '<p><strong>Avoid for:</strong> ' + (Array.isArray(sub.avoid_for) ? sub.avoid_for.map(escapeHtml).join(', ') : escapeHtml(sub.avoid_for)) + '</p>' : '') +
        (sub.bonus ? '<p><strong>Bonus:</strong> ' + escapeHtml(sub.bonus) + '</p>' : '') +
        (sub.note ? '<p><em>' + escapeHtml(sub.note) + '</em></p>' : '') +
      '</div>' +

      warningsHtml +
    '</div>';
  }

  /**
   * Render flavor enhancement tips
   */
  function renderFlavorEnhancementTips() {
    if (!heartSmartDatabase?.tips) return '';

    const tips = heartSmartDatabase.tips.flavor_boosting || [];
    const sodiumTips = heartSmartDatabase.tips.sodium_reduction || [];
    if (tips.length === 0 && sodiumTips.length === 0) return '';

    let herbBlendsHtml = '';
    if (heartSmartDatabase.regional_herb_blends) {
      const blends = Object.values(heartSmartDatabase.regional_herb_blends).slice(0, 4);
      herbBlendsHtml = '<div class="herb-blends-preview">' +
        '<h6>Salt-Free Herb Blends:</h6>' +
        '<div class="herb-blend-chips">' +
        blends.map(function(b) {
          return '<span class="herb-chip" title="' + escapeHtml(b.components.join(', ')) + '">' + escapeHtml(b.name) + '</span>';
        }).join('') +
        '</div>' +
      '</div>';
    }

    return '<details class="heart-smart-tips-section">' +
      '<summary class="heart-smart-tips-header">' +
        '<span class="heart-smart-tips-icon">' +
          '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">' +
            '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>' +
          '</svg>' +
        '</span>' +
        ' Flavor Enhancement Tips' +
        '<span class="chevron-small">\u25B6</span>' +
      '</summary>' +
      '<div class="heart-smart-tips-content">' +
        herbBlendsHtml +
        '<h6>When Reducing Sodium:</h6>' +
        '<ul class="heart-smart-tips-list">' +
          sodiumTips.slice(0, 5).map(function(tip) { return '<li>' + escapeHtml(tip) + '</li>'; }).join('') +
        '</ul>' +
        '<h6>Boost Flavor Without Salt:</h6>' +
        '<ul class="heart-smart-tips-list">' +
          tips.slice(0, 5).map(function(tip) { return '<li>' + escapeHtml(tip) + '</li>'; }).join('') +
        '</ul>' +
      '</div>' +
    '</details>';
  }

  /**
   * Render food safety warnings if applicable
   */
  function renderFoodSafetyWarnings(analysis) {
    if (!heartSmartDatabase?.food_safety_notes) return '';

    // Check if any flagged ingredients have safety warnings
    const hasCuringIngredient = analysis.flaggedIngredients.some(function(f) {
      return f.categoryKey === 'processed_meats';
    });

    const hasPotassiumSubstitute = analysis.flaggedIngredients.some(function(f) {
      return f.substitutes.some(function(s) { return s.id === 'potassium-chloride'; });
    });

    if (!hasCuringIngredient && !hasPotassiumSubstitute) return '';

    let warningsHtml = '<div class="heart-smart-safety-section">';
    warningsHtml += '<h5 class="safety-heading">Important Safety Information</h5>';

    if (hasCuringIngredient && heartSmartDatabase.food_safety_notes.salt_in_curing) {
      const note = heartSmartDatabase.food_safety_notes.salt_in_curing;
      warningsHtml += '<div class="heart-smart-safety-warning">' +
        '<strong>' + escapeHtml(note.title) + ':</strong> ' +
        escapeHtml(note.content) +
      '</div>';
    }

    if (hasPotassiumSubstitute && heartSmartDatabase.food_safety_notes.potassium_chloride_warning) {
      const note = heartSmartDatabase.food_safety_notes.potassium_chloride_warning;
      warningsHtml += '<div class="heart-smart-safety-warning">' +
        '<strong>' + escapeHtml(note.title) + ':</strong> ' +
        escapeHtml(note.content) +
        '<br><strong>At-risk groups:</strong> ' +
        note.at_risk_groups.map(escapeHtml).join(', ') +
      '</div>';
    }

    warningsHtml += '</div>';
    return warningsHtml;
  }

  /**
   * Render medical disclaimer
   */
  function renderDisclaimer() {
    return '<div class="heart-smart-disclaimer">' +
      '<strong>Important:</strong> This tool provides general dietary information only. ' +
      'It is NOT medical advice. Always consult your doctor, cardiologist, or ' +
      'registered dietitian before making significant dietary changes, especially if you ' +
      'have heart disease, high blood pressure, kidney disease, or take medications.' +
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
   * @param {Object} targets - Optional custom targets
   */
  async function initPanel(recipe, containerId, targets) {
    const container = document.getElementById(containerId);
    if (!container) return;

    await loadData();
    if (!heartSmartDatabase) {
      container.innerHTML = '';
      return;
    }

    const analysis = analyzeRecipe(recipe, targets);
    const html = renderPanel(analysis);
    container.innerHTML = html;
  }

  // Public API
  return {
    loadData: loadData,
    analyzeRecipe: analyzeRecipe,
    renderPanel: renderPanel,
    initPanel: initPanel,
    DEFAULT_TARGETS: DEFAULT_TARGETS
  };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HeartSmartConverter;
}
