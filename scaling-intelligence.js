/**
 * Recipe Scaling Intelligence Module
 *
 * Provides intelligent recipe scaling beyond simple multiplication:
 * - Non-linear spice/seasoning scaling
 * - Pan size recommendations
 * - Cooking time adjustments
 * - Warnings for recipes that don't scale well
 *
 * Loads data from: data/scaling-rules.json
 *
 * Sources: America's Test Kitchen, Serious Eats, King Arthur Baking
 */

const ScalingIntelligence = (function() {
  'use strict';

  // Module state
  let scalingRules = null;
  let isLoaded = false;
  let loadingPromise = null;

  /**
   * Load the scaling rules data
   */
  async function loadData() {
    if (isLoaded && scalingRules) {
      return scalingRules;
    }

    if (loadingPromise) {
      return loadingPromise;
    }

    loadingPromise = (async () => {
      try {
        const response = await fetch('data/scaling-rules.json');
        if (!response.ok) {
          console.warn('Scaling intelligence data not available');
          return null;
        }
        scalingRules = await response.json();
        isLoaded = true;
        console.log('Scaling intelligence data loaded:', scalingRules.meta.version);
        return scalingRules;
      } catch (error) {
        console.error('Failed to load scaling intelligence data:', error);
        return null;
      }
    })();

    return loadingPromise;
  }

  /**
   * Check if an ingredient matches any keywords in a category
   * @param {string} ingredientText - Normalized ingredient text
   * @param {string[]} keywords - Keywords to match
   * @returns {boolean}
   */
  function matchesKeywords(ingredientText, keywords) {
    if (!ingredientText || !keywords) return false;
    const lowerText = ingredientText.toLowerCase();
    return keywords.some(kw => lowerText.includes(kw.toLowerCase()));
  }

  /**
   * Normalize ingredient text for matching
   * @param {Object|string} ingredient - Ingredient object or string
   * @returns {string}
   */
  function normalizeIngredient(ingredient) {
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
   * Get the scaling exponent for a specific ingredient
   * @param {Object|string} ingredient - The ingredient to check
   * @returns {Object} - { exponent: number, category: string, notes: string, warning: string|null }
   */
  function getSpiceScalingFactor(ingredient) {
    if (!scalingRules) {
      return { exponent: 1, category: null, notes: null, warning: null };
    }

    const text = normalizeIngredient(ingredient);
    const categories = scalingRules.spice_scaling.categories;

    for (const [catKey, category] of Object.entries(categories)) {
      if (matchesKeywords(text, category.keywords)) {
        return {
          exponent: category.scale_exponent,
          category: catKey,
          notes: category.notes,
          warning: null,
          dangerThreshold: category.danger_threshold || null,
          dangerMessage: category.danger_message || null,
          contextNote: category.context_note || null
        };
      }
    }

    // Default: linear scaling
    return { exponent: 1, category: null, notes: null, warning: null };
  }

  /**
   * Apply intelligent scaling to a quantity
   * @param {number} quantity - Original numeric quantity
   * @param {number} scale - Scale factor (e.g., 2 for doubling)
   * @param {number} exponent - Scaling exponent (1 for linear, <1 for non-linear)
   * @returns {number} - Scaled quantity
   */
  function applyIntelligentScale(quantity, scale, exponent) {
    if (!quantity || scale === 1 || exponent === 1) {
      return quantity * scale;
    }
    // Non-linear scaling: new_qty = old_qty * scale^exponent
    // For exponent 0.7 and scale 2: 2^0.7 = 1.62 (so 2x recipe gets ~1.6x spice)
    return quantity * Math.pow(scale, exponent);
  }

  /**
   * Analyze a recipe for scaling warnings
   * @param {Object} recipe - The recipe to analyze
   * @param {number} scale - The desired scale factor
   * @returns {Object} - { warnings: [], panRecommendations: [], timeAdjustments: [], spiceAdjustments: [] }
   */
  function analyzeRecipeForScaling(recipe, scale) {
    if (!scalingRules || !recipe) {
      return { warnings: [], panRecommendations: [], timeAdjustments: [], spiceAdjustments: [] };
    }

    const result = {
      warnings: [],
      panRecommendations: [],
      timeAdjustments: [],
      spiceAdjustments: []
    };

    // 1. Check for recipes that don't scale well
    const scaleWarnings = checkScalingWarnings(recipe, scale);
    result.warnings = scaleWarnings;

    // 2. Analyze spices for non-linear scaling
    if (recipe.ingredients) {
      result.spiceAdjustments = analyzeSpiceScaling(recipe.ingredients, scale);
    }

    // 3. Get pan recommendations based on recipe category
    result.panRecommendations = getPanRecommendations(recipe, scale);

    // 4. Get cooking time adjustments
    result.timeAdjustments = getTimeAdjustments(recipe, scale);

    return result;
  }

  /**
   * Check recipe for scaling warnings
   * @param {Object} recipe - The recipe
   * @param {number} scale - Scale factor
   * @returns {Array} - Array of warning objects
   */
  function checkScalingWarnings(recipe, scale) {
    if (!scalingRules) return [];

    const warnings = [];
    const recipeText = getRecipeText(recipe);
    const scaleWarnings = scalingRules.scaling_warnings;

    // Check don't-scale categories
    for (const [catKey, category] of Object.entries(scaleWarnings.dont_scale_categories)) {
      if (matchesKeywords(recipeText, category.keywords)) {
        if (scale > category.max_scale) {
          warnings.push({
            type: 'dont_scale',
            category: catKey,
            severity: category.severity,
            message: category.warning,
            tip: category.tip || null,
            maxScale: category.max_scale,
            currentScale: scale
          });
        } else if (scale > 1 && category.tip) {
          // Show tip even within limits
          warnings.push({
            type: 'scaling_tip',
            category: catKey,
            severity: 'info',
            message: category.tip,
            maxScale: category.max_scale
          });
        }
      }
    }

    // Check scaling down warnings
    if (scale < 1) {
      for (const [catKey, category] of Object.entries(scaleWarnings.scaling_down_warnings)) {
        if (matchesKeywords(recipeText, category.keywords)) {
          if (scale < category.min_scale) {
            warnings.push({
              type: 'scale_down',
              category: catKey,
              severity: category.severity,
              message: category.warning,
              tip: category.tip || null,
              minScale: category.min_scale,
              currentScale: scale
            });
          }
        }
      }
    }

    return warnings;
  }

  /**
   * Get all recipe text for pattern matching
   * @param {Object} recipe - The recipe
   * @returns {string}
   */
  function getRecipeText(recipe) {
    const parts = [
      recipe.title || '',
      recipe.category || '',
      recipe.description || ''
    ];

    if (recipe.ingredients) {
      for (const ing of recipe.ingredients) {
        parts.push(normalizeIngredient(ing));
      }
    }

    if (recipe.instructions) {
      for (const inst of recipe.instructions) {
        parts.push(inst.text || inst || '');
      }
    }

    if (recipe.notes) {
      for (const note of recipe.notes) {
        parts.push(note || '');
      }
    }

    return parts.join(' ').toLowerCase();
  }

  /**
   * Analyze spice ingredients for non-linear scaling
   * @param {Array} ingredients - Recipe ingredients
   * @param {number} scale - Scale factor
   * @returns {Array} - Spice adjustment recommendations
   */
  function analyzeSpiceScaling(ingredients, scale) {
    if (!scalingRules || scale === 1) return [];

    const adjustments = [];

    for (let i = 0; i < ingredients.length; i++) {
      const ing = ingredients[i];
      const factor = getSpiceScalingFactor(ing);

      if (factor.exponent < 1) {
        const itemName = typeof ing === 'string' ? ing : ing.item;
        const linearScaled = scale;
        const intelligentScaled = Math.pow(scale, factor.exponent);
        const reductionPercent = Math.round((1 - intelligentScaled / linearScaled) * 100);

        const adjustment = {
          index: i,
          ingredient: itemName,
          category: factor.category,
          linearMultiplier: linearScaled,
          recommendedMultiplier: Math.round(intelligentScaled * 100) / 100,
          reductionPercent: reductionPercent,
          notes: factor.notes
        };

        // Check for danger threshold
        if (factor.dangerThreshold && scale >= factor.dangerThreshold) {
          adjustment.warning = factor.dangerMessage;
          adjustment.severity = 'high';
        }

        adjustments.push(adjustment);
      }
    }

    return adjustments;
  }

  /**
   * Get pan size recommendations
   * @param {Object} recipe - The recipe
   * @param {number} scale - Scale factor
   * @returns {Array} - Pan recommendations
   */
  function getPanRecommendations(recipe, scale) {
    if (!scalingRules || scale === 1) return [];

    const recommendations = [];
    const category = recipe.category || '';
    const recipeText = getRecipeText(recipe);
    const panRecs = scalingRules.pan_sizes.recommendations;

    // Determine recipe type for pan recommendations
    let recipeType = null;

    if (category === 'desserts') {
      if (recipeText.includes('cookie')) {
        recipeType = 'cookies';
      } else if (recipeText.includes('brownie') || recipeText.includes('bar')) {
        recipeType = 'brownies_bars';
      } else if (recipeText.includes('cake') || recipeText.includes('layer')) {
        recipeType = 'cakes_round';
      } else if (recipeText.includes('bread') || recipeText.includes('loaf')) {
        recipeType = 'bread_loaves';
      }
    } else if (category === 'breads') {
      recipeType = 'bread_loaves';
    } else if (category === 'mains' || category === 'sides') {
      if (recipeText.includes('casserole') || recipeText.includes('bake') || recipeText.includes('lasagna')) {
        recipeType = 'casseroles';
      }
    }

    if (recipeType && panRecs[recipeType]) {
      const typeRecs = panRecs[recipeType];
      // Find the closest scale factor that has a recommendation
      const scaleKeys = Object.keys(typeRecs).map(Number).sort((a, b) => a - b);
      let closestKey = scaleKeys[0];

      for (const key of scaleKeys) {
        if (key <= scale) {
          closestKey = key;
        }
      }

      if (scale > scaleKeys[scaleKeys.length - 1]) {
        closestKey = scaleKeys[scaleKeys.length - 1];
      }

      recommendations.push({
        recipeType: recipeType,
        scale: scale,
        recommendation: typeRecs[closestKey],
        note: scale > scaleKeys[scaleKeys.length - 1]
          ? 'Consider baking in multiple batches for best results.'
          : null
      });
    }

    return recommendations;
  }

  /**
   * Get cooking time adjustments
   * @param {Object} recipe - The recipe
   * @param {number} scale - Scale factor
   * @returns {Array} - Time adjustment notes
   */
  function getTimeAdjustments(recipe, scale) {
    if (!scalingRules || scale === 1) return [];

    const adjustments = [];
    const recipeText = getRecipeText(recipe);
    const timeRules = scalingRules.cooking_time_adjustments;

    // Check general cooking method rules
    const generalRules = timeRules.general_rules;

    // Stovetop sauteing
    if (recipeText.includes('saute') || recipeText.includes('sauté') || recipeText.includes('brown') || recipeText.includes('stir-fry')) {
      if (scale > 1) {
        adjustments.push({
          method: 'stovetop_saute',
          message: generalRules.stovetop_saute.scaling_note,
          reason: generalRules.stovetop_saute.reason,
          notes: generalRules.stovetop_saute.notes
        });
      }
    }

    // Deep frying
    if (recipeText.includes('deep fry') || recipeText.includes('fry in oil') || recipeText.includes('deep-fry')) {
      adjustments.push({
        method: 'deep_frying',
        message: generalRules.deep_frying.batch_warning,
        reason: generalRules.deep_frying.reason,
        notes: `${generalRules.deep_frying.max_batch}. ${generalRules.deep_frying.recovery_time}`
      });
    }

    // Oven baking with depth changes
    if (recipeText.includes('bake') || recipeText.includes('oven')) {
      if (scale >= 2) {
        adjustments.push({
          method: 'oven_baking',
          message: 'Baking time may need adjustment',
          notes: generalRules.oven_baking.deep_items,
          temperatureNote: generalRules.oven_baking.temperature_note
        });
      }
    }

    // Slow cooker
    if (recipeText.includes('slow cooker') || recipeText.includes('crockpot') || recipeText.includes('crock pot')) {
      adjustments.push({
        method: 'slow_cooker',
        message: generalRules.slow_cooker.notes,
        notes: scale > 1 ? generalRules.slow_cooker.scaling_up : generalRules.slow_cooker.scaling_down
      });
    }

    // Pressure cooker
    if (recipeText.includes('pressure cooker') || recipeText.includes('instant pot')) {
      adjustments.push({
        method: 'pressure_cooker',
        message: generalRules.pressure_cooker.notes,
        notes: `${generalRules.pressure_cooker.liquid_rule}. ${generalRules.pressure_cooker.max_fill}`
      });
    }

    // Meat roasting - always recommend thermometer
    if ((recipeText.includes('roast') && (recipeText.includes('beef') || recipeText.includes('pork') || recipeText.includes('chicken') || recipeText.includes('turkey'))) ||
        recipeText.includes('roasting')) {
      const meatRule = timeRules.specific_adjustments.meat_roasting;
      adjustments.push({
        method: 'meat_roasting',
        message: meatRule.time_note,
        temps: meatRule.internal_temps
      });
    }

    return adjustments;
  }

  /**
   * Get a summary of all scaling intelligence for display
   * @param {Object} recipe - The recipe
   * @param {number} scale - Scale factor
   * @returns {Object} - Complete scaling analysis
   */
  async function getScalingAnalysis(recipe, scale) {
    await loadData();

    if (scale === 1) {
      return {
        hasIntelligence: false,
        scale: 1,
        warnings: [],
        spiceAdjustments: [],
        panRecommendations: [],
        timeAdjustments: []
      };
    }

    const analysis = analyzeRecipeForScaling(recipe, scale);

    return {
      hasIntelligence: analysis.warnings.length > 0 ||
                       analysis.spiceAdjustments.length > 0 ||
                       analysis.panRecommendations.length > 0 ||
                       analysis.timeAdjustments.length > 0,
      scale: scale,
      ...analysis
    };
  }

  /**
   * Get scaled quantity for an ingredient with intelligent adjustment
   * @param {Object|string} ingredient - The ingredient
   * @param {number} originalQuantity - Original numeric quantity
   * @param {number} scale - Scale factor
   * @returns {Object} - { value: number, isAdjusted: boolean, adjustment: Object|null }
   */
  function getIntelligentScaledQuantity(ingredient, originalQuantity, scale) {
    if (!scalingRules || scale === 1) {
      return {
        value: originalQuantity * scale,
        isAdjusted: false,
        adjustment: null
      };
    }

    const factor = getSpiceScalingFactor(ingredient);

    if (factor.exponent < 1) {
      const intelligentValue = applyIntelligentScale(originalQuantity, scale, factor.exponent);
      return {
        value: intelligentValue,
        isAdjusted: true,
        adjustment: {
          category: factor.category,
          exponent: factor.exponent,
          linearValue: originalQuantity * scale,
          notes: factor.notes
        }
      };
    }

    return {
      value: originalQuantity * scale,
      isAdjusted: false,
      adjustment: null
    };
  }

  /**
   * Format a scaling analysis for HTML display
   * @param {Object} analysis - From getScalingAnalysis
   * @returns {string} - HTML string
   */
  function renderScalingIntelligencePanel(analysis) {
    if (!analysis.hasIntelligence) {
      return '';
    }

    let html = '<div class="scaling-intelligence-panel">';
    html += '<details class="scaling-details">';
    html += '<summary class="scaling-summary">';
    html += '<span class="scaling-icon">&#9881;</span> ';
    html += '<span class="scaling-title">Scaling Tips</span>';

    const totalItems = analysis.warnings.length +
                       analysis.spiceAdjustments.length +
                       analysis.panRecommendations.length +
                       analysis.timeAdjustments.length;
    html += `<span class="scaling-count">(${totalItems} tips)</span>`;
    html += '<span class="scaling-chevron">&#9658;</span>';
    html += '</summary>';

    html += '<div class="scaling-content">';

    // Warnings (most important first)
    if (analysis.warnings.length > 0) {
      html += '<div class="scaling-section scaling-warnings">';
      html += '<h4>&#9888; Scaling Warnings</h4>';
      for (const warning of analysis.warnings) {
        const severityClass = warning.severity === 'high' ? 'warning-high' :
                              warning.severity === 'medium' ? 'warning-medium' : 'warning-low';
        html += `<div class="scaling-warning ${severityClass}">`;
        html += `<p><strong>${formatCategoryName(warning.category)}:</strong> ${escapeHtml(warning.message)}</p>`;
        if (warning.tip) {
          html += `<p class="warning-tip"><em>Tip:</em> ${escapeHtml(warning.tip)}</p>`;
        }
        html += '</div>';
      }
      html += '</div>';
    }

    // Spice adjustments
    if (analysis.spiceAdjustments.length > 0) {
      html += '<div class="scaling-section scaling-spices">';
      html += '<h4>&#127798; Spice & Seasoning Adjustments</h4>';
      html += '<p class="section-intro">These ingredients don\'t scale linearly. Recommended adjustments:</p>';
      html += '<ul class="spice-list">';
      for (const adj of analysis.spiceAdjustments) {
        html += '<li>';
        html += `<strong>${escapeHtml(adj.ingredient)}</strong>: `;
        html += `Use <span class="recommend">${adj.recommendedMultiplier}×</span> instead of ${adj.linearMultiplier}× `;
        html += `<span class="reduction">(${adj.reductionPercent}% less)</span>`;
        if (adj.warning) {
          html += `<br><span class="spice-warning">&#9888; ${escapeHtml(adj.warning)}</span>`;
        }
        html += '</li>';
      }
      html += '</ul>';
      html += '<p class="scaling-note"><em>Always taste and adjust! These are starting recommendations.</em></p>';
      html += '</div>';
    }

    // Pan recommendations
    if (analysis.panRecommendations.length > 0) {
      html += '<div class="scaling-section scaling-pans">';
      html += '<h4>&#127869; Pan Size Recommendations</h4>';
      for (const rec of analysis.panRecommendations) {
        html += `<p><strong>For ${analysis.scale}× batch:</strong> ${escapeHtml(rec.recommendation)}</p>`;
        if (rec.note) {
          html += `<p class="pan-note"><em>${escapeHtml(rec.note)}</em></p>`;
        }
      }
      html += '</div>';
    }

    // Time adjustments
    if (analysis.timeAdjustments.length > 0) {
      html += '<div class="scaling-section scaling-time">';
      html += '<h4>&#9201; Cooking Time Notes</h4>';
      for (const adj of analysis.timeAdjustments) {
        html += '<div class="time-adjustment">';
        html += `<p><strong>${escapeHtml(adj.message)}</strong></p>`;
        if (adj.notes) {
          html += `<p>${escapeHtml(adj.notes)}</p>`;
        }
        if (adj.temperatureNote) {
          html += `<p class="temp-note"><em>${escapeHtml(adj.temperatureNote)}</em></p>`;
        }
        if (adj.temps) {
          html += '<p class="safe-temps"><strong>Safe internal temperatures:</strong><br>';
          for (const [meat, temp] of Object.entries(adj.temps)) {
            const meatName = meat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            html += `${meatName}: ${temp}<br>`;
          }
          html += '</p>';
        }
        html += '</div>';
      }
      html += '</div>';
    }

    html += '</div>'; // scaling-content
    html += '</details>';
    html += '</div>'; // scaling-intelligence-panel

    return html;
  }

  /**
   * Format category name for display
   */
  function formatCategoryName(category) {
    if (!category) return '';
    return category
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  /**
   * Escape HTML special characters
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Public API
  return {
    loadData: loadData,
    getScalingAnalysis: getScalingAnalysis,
    getSpiceScalingFactor: getSpiceScalingFactor,
    getIntelligentScaledQuantity: getIntelligentScaledQuantity,
    renderScalingIntelligencePanel: renderScalingIntelligencePanel,
    applyIntelligentScale: applyIntelligentScale
  };
})();

// Initialize on load
if (typeof window !== 'undefined') {
  window.ScalingIntelligence = ScalingIntelligence;
}
