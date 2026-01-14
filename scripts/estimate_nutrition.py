#!/usr/bin/env python3
"""
Nutrition Estimation Script for Grandma Baker's Recipe Archive

Estimates nutritional information based on ingredient lists and standard
USDA nutritional values. Results are approximations suitable for home cooking.

Usage:
    python scripts/estimate_nutrition.py                    # Estimate all recipes
    python scripts/estimate_nutrition.py --dry-run          # Preview without saving
    python scripts/estimate_nutrition.py --recipe-id ID     # Specific recipe only
    python scripts/estimate_nutrition.py --force            # Re-estimate all (even existing)
    python scripts/estimate_nutrition.py --collection ID    # Specific collection only

Based on the nutrition database from Grannysrecipes, expanded for Grandma Baker's
collection with additional ingredients common to Michigan/Florida family recipes.
"""

import json
import re
import sys
from fractions import Fraction
from pathlib import Path

# =============================================================================
# Nutrition Database (per standard measure)
# Values are approximate and based on USDA data
# Format: {ingredient: {unit: {cal, fat, carb, protein, sodium, fiber, sugar}}}
# =============================================================================

NUTRITION_DB = {
    # =========================================================================
    # PROTEINS
    # =========================================================================
    'chicken breast': {'oz': {'cal': 46, 'fat': 1, 'carb': 0, 'protein': 9, 'sodium': 20, 'fiber': 0, 'sugar': 0}},
    'chicken': {'lb': {'cal': 800, 'fat': 48, 'carb': 0, 'protein': 88, 'sodium': 320, 'fiber': 0, 'sugar': 0}},
    'chicken thighs': {'lb': {'cal': 900, 'fat': 56, 'carb': 0, 'protein': 80, 'sodium': 340, 'fiber': 0, 'sugar': 0}},
    'ground beef': {'lb': {'cal': 1152, 'fat': 88, 'carb': 0, 'protein': 80, 'sodium': 320, 'fiber': 0, 'sugar': 0}},
    'extra-lean ground beef': {'lb': {'cal': 800, 'fat': 48, 'carb': 0, 'protein': 88, 'sodium': 300, 'fiber': 0, 'sugar': 0}},
    'lean ground beef': {'lb': {'cal': 800, 'fat': 48, 'carb': 0, 'protein': 88, 'sodium': 300, 'fiber': 0, 'sugar': 0}},
    'bacon': {'slice': {'cal': 43, 'fat': 3.3, 'carb': 0.1, 'protein': 3, 'sodium': 137, 'fiber': 0, 'sugar': 0}},
    'pork chops': {'oz': {'cal': 52, 'fat': 2.5, 'carb': 0, 'protein': 7, 'sodium': 18, 'fiber': 0, 'sugar': 0}},
    'pork loin': {'lb': {'cal': 800, 'fat': 32, 'carb': 0, 'protein': 120, 'sodium': 280, 'fiber': 0, 'sugar': 0}},
    'pork': {'lb': {'cal': 1000, 'fat': 64, 'carb': 0, 'protein': 100, 'sodium': 280, 'fiber': 0, 'sugar': 0}},
    'spareribs': {'lb': {'cal': 1200, 'fat': 96, 'carb': 0, 'protein': 80, 'sodium': 400, 'fiber': 0, 'sugar': 0}},
    'ham': {'oz': {'cal': 46, 'fat': 2.4, 'carb': 0.4, 'protein': 5.5, 'sodium': 365, 'fiber': 0, 'sugar': 0}},
    'shrimp': {'oz': {'cal': 30, 'fat': 0.5, 'carb': 0.3, 'protein': 6, 'sodium': 55, 'fiber': 0, 'sugar': 0}},
    'crabmeat': {'oz': {'cal': 25, 'fat': 0.4, 'carb': 0, 'protein': 5, 'sodium': 95, 'fiber': 0, 'sugar': 0}},
    'clams': {'oz': {'cal': 21, 'fat': 0.3, 'carb': 1, 'protein': 3.6, 'sodium': 32, 'fiber': 0, 'sugar': 0}},
    'fish': {'oz': {'cal': 35, 'fat': 0.8, 'carb': 0, 'protein': 7, 'sodium': 45, 'fiber': 0, 'sugar': 0}},
    'swordfish': {'oz': {'cal': 41, 'fat': 1.4, 'carb': 0, 'protein': 6.7, 'sodium': 30, 'fiber': 0, 'sugar': 0}},
    'red snapper': {'oz': {'cal': 28, 'fat': 0.4, 'carb': 0, 'protein': 5.8, 'sodium': 18, 'fiber': 0, 'sugar': 0}},
    'cod': {'oz': {'cal': 23, 'fat': 0.2, 'carb': 0, 'protein': 5, 'sodium': 18, 'fiber': 0, 'sugar': 0}},
    'turkey': {'lb': {'cal': 720, 'fat': 32, 'carb': 0, 'protein': 100, 'sodium': 280, 'fiber': 0, 'sugar': 0}},
    'lamb': {'lb': {'cal': 1100, 'fat': 80, 'carb': 0, 'protein': 88, 'sodium': 280, 'fiber': 0, 'sugar': 0}},
    'cornish hen': {'each': {'cal': 500, 'fat': 28, 'carb': 0, 'protein': 60, 'sodium': 200, 'fiber': 0, 'sugar': 0}},
    'corned beef': {'oz': {'cal': 71, 'fat': 5.4, 'carb': 0.4, 'protein': 5, 'sodium': 285, 'fiber': 0, 'sugar': 0}},
    'sausage': {'oz': {'cal': 82, 'fat': 7, 'carb': 0.4, 'protein': 4, 'sodium': 230, 'fiber': 0, 'sugar': 0}},
    'andouille sausage': {'oz': {'cal': 90, 'fat': 8, 'carb': 1, 'protein': 4, 'sodium': 300, 'fiber': 0, 'sugar': 0}},
    'egg': {'large': {'cal': 72, 'fat': 5, 'carb': 0.4, 'protein': 6, 'sodium': 71, 'fiber': 0, 'sugar': 0}},
    'eggs': {'large': {'cal': 72, 'fat': 5, 'carb': 0.4, 'protein': 6, 'sodium': 71, 'fiber': 0, 'sugar': 0}},
    'large eggs': {'each': {'cal': 72, 'fat': 5, 'carb': 0.4, 'protein': 6, 'sodium': 71, 'fiber': 0, 'sugar': 0}},
    'egg whites': {'large': {'cal': 17, 'fat': 0, 'carb': 0.2, 'protein': 3.6, 'sodium': 55, 'fiber': 0, 'sugar': 0}},
    'egg yolks': {'large': {'cal': 55, 'fat': 4.5, 'carb': 0.6, 'protein': 2.7, 'sodium': 8, 'fiber': 0, 'sugar': 0}},
    'tofu': {'oz': {'cal': 22, 'fat': 1.3, 'carb': 0.5, 'protein': 2, 'sodium': 2, 'fiber': 0, 'sugar': 0}},

    # =========================================================================
    # DAIRY
    # =========================================================================
    'butter': {'cup': {'cal': 1628, 'fat': 184, 'carb': 0, 'protein': 2, 'sodium': 1284, 'fiber': 0, 'sugar': 0},
               'tbsp': {'cal': 102, 'fat': 11.5, 'carb': 0, 'protein': 0.1, 'sodium': 80, 'fiber': 0, 'sugar': 0}},
    'unsalted butter': {'cup': {'cal': 1628, 'fat': 184, 'carb': 0, 'protein': 2, 'sodium': 12, 'fiber': 0, 'sugar': 0},
                        'tbsp': {'cal': 102, 'fat': 11.5, 'carb': 0, 'protein': 0.1, 'sodium': 1, 'fiber': 0, 'sugar': 0}},
    'butter or margarine': {'cup': {'cal': 1628, 'fat': 184, 'carb': 0, 'protein': 2, 'sodium': 1284, 'fiber': 0, 'sugar': 0},
                            'tbsp': {'cal': 102, 'fat': 11.5, 'carb': 0, 'protein': 0.1, 'sodium': 80, 'fiber': 0, 'sugar': 0}},
    'margarine': {'cup': {'cal': 1628, 'fat': 184, 'carb': 0, 'protein': 2, 'sodium': 1284, 'fiber': 0, 'sugar': 0},
                  'tbsp': {'cal': 102, 'fat': 11.5, 'carb': 0, 'protein': 0.1, 'sodium': 80, 'fiber': 0, 'sugar': 0}},
    'oleo (margarine)': {'cup': {'cal': 1628, 'fat': 184, 'carb': 0, 'protein': 2, 'sodium': 1284, 'fiber': 0, 'sugar': 0},
                         'tbsp': {'cal': 102, 'fat': 11.5, 'carb': 0, 'protein': 0.1, 'sodium': 80, 'fiber': 0, 'sugar': 0}},
    'milk': {'cup': {'cal': 149, 'fat': 8, 'carb': 12, 'protein': 8, 'sodium': 107, 'fiber': 0, 'sugar': 12}},
    'skim milk': {'cup': {'cal': 83, 'fat': 0.2, 'carb': 12, 'protein': 8, 'sodium': 103, 'fiber': 0, 'sugar': 12}},
    'buttermilk': {'cup': {'cal': 99, 'fat': 2.2, 'carb': 12, 'protein': 8, 'sodium': 257, 'fiber': 0, 'sugar': 12}},
    'heavy cream': {'cup': {'cal': 821, 'fat': 88, 'carb': 7, 'protein': 5, 'sodium': 89, 'fiber': 0, 'sugar': 7}},
    'whipping cream': {'cup': {'cal': 821, 'fat': 88, 'carb': 7, 'protein': 5, 'sodium': 89, 'fiber': 0, 'sugar': 7}},
    'sour cream': {'cup': {'cal': 445, 'fat': 44, 'carb': 8, 'protein': 6, 'sodium': 123, 'fiber': 0, 'sugar': 5}},
    'cream cheese': {'oz': {'cal': 99, 'fat': 10, 'carb': 1, 'protein': 2, 'sodium': 84, 'fiber': 0, 'sugar': 1},
                     'package': {'cal': 792, 'fat': 80, 'carb': 8, 'protein': 16, 'sodium': 672, 'fiber': 0, 'sugar': 8}},
    'cheddar cheese': {'cup': {'cal': 455, 'fat': 37, 'carb': 1.5, 'protein': 28, 'sodium': 700, 'fiber': 0, 'sugar': 0}},
    'shredded cheddar cheese': {'cup': {'cal': 455, 'fat': 37, 'carb': 1.5, 'protein': 28, 'sodium': 700, 'fiber': 0, 'sugar': 0}},
    'mozzarella cheese': {'cup': {'cal': 316, 'fat': 20, 'carb': 4, 'protein': 28, 'sodium': 632, 'fiber': 0, 'sugar': 1}},
    'parmesan cheese': {'tbsp': {'cal': 22, 'fat': 1.4, 'carb': 0.2, 'protein': 2, 'sodium': 76, 'fiber': 0, 'sugar': 0},
                        'cup': {'cal': 352, 'fat': 22.4, 'carb': 3.2, 'protein': 32, 'sodium': 1216, 'fiber': 0, 'sugar': 0}},
    'grated parmesan cheese': {'tbsp': {'cal': 22, 'fat': 1.4, 'carb': 0.2, 'protein': 2, 'sodium': 76, 'fiber': 0, 'sugar': 0}},
    'cheese': {'cup': {'cal': 400, 'fat': 32, 'carb': 2, 'protein': 24, 'sodium': 650, 'fiber': 0, 'sugar': 0}},
    'evaporated milk': {'cup': {'cal': 338, 'fat': 19, 'carb': 25, 'protein': 17, 'sodium': 266, 'fiber': 0, 'sugar': 25}},
    'sweetened condensed milk': {'cup': {'cal': 982, 'fat': 27, 'carb': 166, 'protein': 24, 'sodium': 389, 'fiber': 0, 'sugar': 166},
                                 'can': {'cal': 1300, 'fat': 36, 'carb': 220, 'protein': 32, 'sodium': 516, 'fiber': 0, 'sugar': 220}},
    'cool whip': {'cup': {'cal': 200, 'fat': 14, 'carb': 18, 'protein': 1, 'sodium': 20, 'fiber': 0, 'sugar': 14}},
    'whipped topping': {'cup': {'cal': 200, 'fat': 14, 'carb': 18, 'protein': 1, 'sodium': 20, 'fiber': 0, 'sugar': 14}},
    'cottage cheese': {'cup': {'cal': 220, 'fat': 10, 'carb': 6, 'protein': 26, 'sodium': 820, 'fiber': 0, 'sugar': 6}},
    'yogurt': {'cup': {'cal': 150, 'fat': 8, 'carb': 12, 'protein': 8, 'sodium': 115, 'fiber': 0, 'sugar': 12}},
    'half-and-half': {'cup': {'cal': 315, 'fat': 28, 'carb': 10, 'protein': 7, 'sodium': 98, 'fiber': 0, 'sugar': 10},
                      'tbsp': {'cal': 20, 'fat': 1.7, 'carb': 0.6, 'protein': 0.4, 'sodium': 6, 'fiber': 0, 'sugar': 0.6}},

    # =========================================================================
    # GRAINS & STARCHES
    # =========================================================================
    'flour': {'cup': {'cal': 455, 'fat': 1.2, 'carb': 95, 'protein': 13, 'sodium': 3, 'fiber': 3, 'sugar': 0}},
    'all-purpose flour': {'cup': {'cal': 455, 'fat': 1.2, 'carb': 95, 'protein': 13, 'sodium': 3, 'fiber': 3, 'sugar': 0}},
    'bread flour': {'cup': {'cal': 455, 'fat': 1.5, 'carb': 95, 'protein': 15, 'sodium': 3, 'fiber': 3, 'sugar': 0}},
    'cake flour': {'cup': {'cal': 400, 'fat': 0.8, 'carb': 88, 'protein': 9, 'sodium': 3, 'fiber': 2, 'sugar': 0}},
    'whole wheat flour': {'cup': {'cal': 407, 'fat': 2.2, 'carb': 87, 'protein': 16, 'sodium': 6, 'fiber': 15, 'sugar': 0}},
    'oats': {'cup': {'cal': 307, 'fat': 5, 'carb': 55, 'protein': 11, 'sodium': 5, 'fiber': 8, 'sugar': 1}},
    'quick oats': {'cup': {'cal': 307, 'fat': 5, 'carb': 55, 'protein': 11, 'sodium': 5, 'fiber': 8, 'sugar': 1}},
    'rice': {'cup': {'cal': 206, 'fat': 0.4, 'carb': 45, 'protein': 4, 'sodium': 2, 'fiber': 0.6, 'sugar': 0}},
    'pasta': {'oz': {'cal': 100, 'fat': 0.5, 'carb': 20, 'protein': 3.5, 'sodium': 1, 'fiber': 1, 'sugar': 0}},
    'linguine': {'oz': {'cal': 100, 'fat': 0.5, 'carb': 20, 'protein': 3.5, 'sodium': 1, 'fiber': 1, 'sugar': 0}},
    'noodles': {'cup': {'cal': 220, 'fat': 2, 'carb': 40, 'protein': 8, 'sodium': 10, 'fiber': 2, 'sugar': 0}},
    'fresh chinese noodles': {'oz': {'cal': 100, 'fat': 1, 'carb': 20, 'protein': 3, 'sodium': 150, 'fiber': 1, 'sugar': 0}},
    'bread crumbs': {'cup': {'cal': 427, 'fat': 6, 'carb': 78, 'protein': 14, 'sodium': 930, 'fiber': 3, 'sugar': 6}},
    'hamburger bun': {'each': {'cal': 120, 'fat': 2, 'carb': 21, 'protein': 4, 'sodium': 200, 'fiber': 1, 'sugar': 3}},
    'biscuit mix': {'cup': {'cal': 480, 'fat': 16, 'carb': 72, 'protein': 8, 'sodium': 1360, 'fiber': 2, 'sugar': 8}},
    'cornmeal': {'cup': {'cal': 442, 'fat': 4, 'carb': 94, 'protein': 10, 'sodium': 4, 'fiber': 9, 'sugar': 1}},
    'tortilla': {'each': {'cal': 90, 'fat': 2.5, 'carb': 15, 'protein': 2, 'sodium': 200, 'fiber': 1, 'sugar': 0}},
    'flour tortilla': {'each': {'cal': 140, 'fat': 3.5, 'carb': 24, 'protein': 4, 'sodium': 350, 'fiber': 1, 'sugar': 1}},
    'crescent rolls': {'each': {'cal': 100, 'fat': 5, 'carb': 11, 'protein': 2, 'sodium': 220, 'fiber': 0, 'sugar': 2}},
    'puff pastry': {'sheet': {'cal': 900, 'fat': 60, 'carb': 72, 'protein': 12, 'sodium': 360, 'fiber': 2, 'sugar': 2}},
    'pie crust': {'each': {'cal': 650, 'fat': 40, 'carb': 64, 'protein': 8, 'sodium': 400, 'fiber': 2, 'sugar': 2}},
    'graham cracker crust': {'each': {'cal': 800, 'fat': 36, 'carb': 112, 'protein': 8, 'sodium': 600, 'fiber': 2, 'sugar': 40}},
    'graham crackers': {'cup': {'cal': 440, 'fat': 10, 'carb': 80, 'protein': 6, 'sodium': 520, 'fiber': 2, 'sugar': 24}},
    'potato': {'medium': {'cal': 163, 'fat': 0.2, 'carb': 37, 'protein': 4, 'sodium': 13, 'fiber': 4, 'sugar': 2}},
    'potatoes': {'lb': {'cal': 350, 'fat': 0.4, 'carb': 80, 'protein': 9, 'sodium': 28, 'fiber': 9, 'sugar': 4}},
    'sweet potato': {'medium': {'cal': 103, 'fat': 0.1, 'carb': 24, 'protein': 2, 'sodium': 41, 'fiber': 4, 'sugar': 7}},
    'kashi pilaf': {'cup': {'cal': 170, 'fat': 1, 'carb': 34, 'protein': 6, 'sodium': 0, 'fiber': 6, 'sugar': 0}},
    'barley': {'cup': {'cal': 651, 'fat': 2.3, 'carb': 135, 'protein': 23, 'sodium': 22, 'fiber': 32, 'sugar': 1}},

    # =========================================================================
    # SUGARS & SWEETENERS
    # =========================================================================
    'sugar': {'cup': {'cal': 774, 'fat': 0, 'carb': 200, 'protein': 0, 'sodium': 2, 'fiber': 0, 'sugar': 200},
              'tbsp': {'cal': 48, 'fat': 0, 'carb': 12.5, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 12.5},
              'tsp': {'cal': 16, 'fat': 0, 'carb': 4, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 4}},
    'granulated sugar': {'cup': {'cal': 774, 'fat': 0, 'carb': 200, 'protein': 0, 'sodium': 2, 'fiber': 0, 'sugar': 200},
                         'tbsp': {'cal': 48, 'fat': 0, 'carb': 12.5, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 12.5}},
    'white sugar': {'cup': {'cal': 774, 'fat': 0, 'carb': 200, 'protein': 0, 'sodium': 2, 'fiber': 0, 'sugar': 200}},
    'brown sugar': {'cup': {'cal': 829, 'fat': 0, 'carb': 214, 'protein': 0, 'sodium': 57, 'fiber': 0, 'sugar': 212},
                    'tbsp': {'cal': 52, 'fat': 0, 'carb': 13.4, 'protein': 0, 'sodium': 4, 'fiber': 0, 'sugar': 13.3}},
    'light brown sugar': {'cup': {'cal': 829, 'fat': 0, 'carb': 214, 'protein': 0, 'sodium': 57, 'fiber': 0, 'sugar': 212}},
    'packed brown sugar': {'cup': {'cal': 829, 'fat': 0, 'carb': 214, 'protein': 0, 'sodium': 57, 'fiber': 0, 'sugar': 212}},
    'powdered sugar': {'cup': {'cal': 467, 'fat': 0, 'carb': 119, 'protein': 0, 'sodium': 1, 'fiber': 0, 'sugar': 117},
                       'tbsp': {'cal': 29, 'fat': 0, 'carb': 7.4, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 7.3}},
    "confectioners' sugar": {'cup': {'cal': 467, 'fat': 0, 'carb': 119, 'protein': 0, 'sodium': 1, 'fiber': 0, 'sugar': 117}},
    'honey': {'tbsp': {'cal': 64, 'fat': 0, 'carb': 17, 'protein': 0.1, 'sodium': 1, 'fiber': 0, 'sugar': 17},
              'cup': {'cal': 1031, 'fat': 0, 'carb': 279, 'protein': 1, 'sodium': 14, 'fiber': 0, 'sugar': 278}},
    'maple syrup': {'tbsp': {'cal': 52, 'fat': 0, 'carb': 13, 'protein': 0, 'sodium': 2, 'fiber': 0, 'sugar': 12},
                    'cup': {'cal': 840, 'fat': 0, 'carb': 216, 'protein': 0, 'sodium': 28, 'fiber': 0, 'sugar': 192}},
    'corn syrup': {'cup': {'cal': 925, 'fat': 0, 'carb': 251, 'protein': 0, 'sodium': 395, 'fiber': 0, 'sugar': 153},
                   'tbsp': {'cal': 58, 'fat': 0, 'carb': 16, 'protein': 0, 'sodium': 25, 'fiber': 0, 'sugar': 10}},
    'molasses': {'tbsp': {'cal': 58, 'fat': 0, 'carb': 15, 'protein': 0, 'sodium': 7, 'fiber': 0, 'sugar': 11},
                 'cup': {'cal': 928, 'fat': 0, 'carb': 240, 'protein': 0, 'sodium': 112, 'fiber': 0, 'sugar': 176}},

    # =========================================================================
    # OILS & FATS
    # =========================================================================
    'olive oil': {'tbsp': {'cal': 119, 'fat': 14, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0},
                  'cup': {'cal': 1904, 'fat': 224, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'vegetable oil': {'tbsp': {'cal': 120, 'fat': 14, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0},
                      'cup': {'cal': 1920, 'fat': 224, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'oil': {'tbsp': {'cal': 120, 'fat': 14, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0},
            'cup': {'cal': 1920, 'fat': 224, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'shortening': {'cup': {'cal': 1845, 'fat': 205, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0},
                   'tbsp': {'cal': 115, 'fat': 13, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'mayonnaise': {'tbsp': {'cal': 94, 'fat': 10, 'carb': 0.1, 'protein': 0.1, 'sodium': 88, 'fiber': 0, 'sugar': 0},
                   'cup': {'cal': 1504, 'fat': 160, 'carb': 1.6, 'protein': 1.6, 'sodium': 1408, 'fiber': 0, 'sugar': 0}},
    'sesame oil': {'tbsp': {'cal': 120, 'fat': 14, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},

    # =========================================================================
    # VEGETABLES
    # =========================================================================
    'onion': {'medium': {'cal': 44, 'fat': 0.1, 'carb': 10, 'protein': 1.2, 'sodium': 4, 'fiber': 2, 'sugar': 5},
              'cup': {'cal': 64, 'fat': 0.2, 'carb': 15, 'protein': 1.8, 'sodium': 6, 'fiber': 3, 'sugar': 7}},
    'onions': {'cup': {'cal': 64, 'fat': 0.2, 'carb': 15, 'protein': 1.8, 'sodium': 6, 'fiber': 3, 'sugar': 7}},
    'green onions': {'bunch': {'cal': 32, 'fat': 0.2, 'carb': 7, 'protein': 1.8, 'sodium': 16, 'fiber': 2.6, 'sugar': 2.3},
                     'cup': {'cal': 32, 'fat': 0.2, 'carb': 7, 'protein': 1.8, 'sodium': 16, 'fiber': 2.6, 'sugar': 2.3}},
    'garlic': {'clove': {'cal': 4, 'fat': 0, 'carb': 1, 'protein': 0.2, 'sodium': 1, 'fiber': 0, 'sugar': 0},
               'tsp': {'cal': 4, 'fat': 0, 'carb': 1, 'protein': 0.2, 'sodium': 1, 'fiber': 0, 'sugar': 0}},
    'tomato': {'medium': {'cal': 22, 'fat': 0.2, 'carb': 5, 'protein': 1, 'sodium': 6, 'fiber': 1.5, 'sugar': 3}},
    'tomatoes': {'can': {'cal': 80, 'fat': 0.4, 'carb': 16, 'protein': 4, 'sodium': 600, 'fiber': 4, 'sugar': 10},
                 'cup': {'cal': 32, 'fat': 0.4, 'carb': 7, 'protein': 1.6, 'sodium': 9, 'fiber': 2, 'sugar': 5}},
    'diced tomatoes': {'can': {'cal': 80, 'fat': 0.4, 'carb': 16, 'protein': 4, 'sodium': 600, 'fiber': 4, 'sugar': 10}},
    'tomato sauce': {'cup': {'cal': 59, 'fat': 0.5, 'carb': 13, 'protein': 2.5, 'sodium': 1284, 'fiber': 3, 'sugar': 8}},
    'tomato paste': {'tbsp': {'cal': 13, 'fat': 0.1, 'carb': 3, 'protein': 0.7, 'sodium': 130, 'fiber': 0.7, 'sugar': 2}},
    'mushrooms': {'cup': {'cal': 15, 'fat': 0.2, 'carb': 2, 'protein': 2, 'sodium': 4, 'fiber': 0.7, 'sugar': 1}},
    'green pepper': {'medium': {'cal': 24, 'fat': 0.2, 'carb': 6, 'protein': 1, 'sodium': 4, 'fiber': 2, 'sugar': 3}},
    'bell pepper': {'medium': {'cal': 24, 'fat': 0.2, 'carb': 6, 'protein': 1, 'sodium': 4, 'fiber': 2, 'sugar': 3}},
    'celery': {'stalk': {'cal': 6, 'fat': 0.1, 'carb': 1, 'protein': 0.3, 'sodium': 32, 'fiber': 0.6, 'sugar': 0.5},
               'cup': {'cal': 14, 'fat': 0.2, 'carb': 3, 'protein': 0.7, 'sodium': 80, 'fiber': 1.6, 'sugar': 1.3}},
    'carrot': {'medium': {'cal': 25, 'fat': 0.1, 'carb': 6, 'protein': 0.6, 'sodium': 42, 'fiber': 1.7, 'sugar': 3}},
    'carrots': {'cup': {'cal': 52, 'fat': 0.3, 'carb': 12, 'protein': 1.2, 'sodium': 88, 'fiber': 3.6, 'sugar': 6}},
    'broccoli': {'cup': {'cal': 31, 'fat': 0.3, 'carb': 6, 'protein': 2.5, 'sodium': 30, 'fiber': 2, 'sugar': 1.5}},
    'corn': {'cup': {'cal': 132, 'fat': 1.8, 'carb': 29, 'protein': 5, 'sodium': 23, 'fiber': 3.6, 'sugar': 5}},
    'green beans': {'cup': {'cal': 31, 'fat': 0.1, 'carb': 7, 'protein': 2, 'sodium': 6, 'fiber': 3, 'sugar': 1.5}},
    'peas': {'cup': {'cal': 117, 'fat': 0.6, 'carb': 21, 'protein': 8, 'sodium': 7, 'fiber': 7, 'sugar': 8}},
    'lettuce': {'cup': {'cal': 5, 'fat': 0.1, 'carb': 1, 'protein': 0.5, 'sodium': 5, 'fiber': 0.5, 'sugar': 0.5}},
    'spinach': {'cup': {'cal': 7, 'fat': 0.1, 'carb': 1, 'protein': 0.9, 'sodium': 24, 'fiber': 0.7, 'sugar': 0}},
    'cabbage': {'cup': {'cal': 17, 'fat': 0.1, 'carb': 4, 'protein': 1, 'sodium': 13, 'fiber': 1.8, 'sugar': 2}},
    'zucchini': {'medium': {'cal': 31, 'fat': 0.4, 'carb': 7, 'protein': 2, 'sodium': 16, 'fiber': 2, 'sugar': 5}},
    'avocado': {'each': {'cal': 322, 'fat': 29, 'carb': 17, 'protein': 4, 'sodium': 14, 'fiber': 13, 'sugar': 1}},
    'rhubarb': {'cup': {'cal': 26, 'fat': 0.2, 'carb': 6, 'protein': 1.1, 'sodium': 5, 'fiber': 2, 'sugar': 1.3}},

    # =========================================================================
    # FRUITS
    # =========================================================================
    'banana': {'medium': {'cal': 105, 'fat': 0.4, 'carb': 27, 'protein': 1.3, 'sodium': 1, 'fiber': 3, 'sugar': 14}},
    'apple': {'medium': {'cal': 95, 'fat': 0.3, 'carb': 25, 'protein': 0.5, 'sodium': 2, 'fiber': 4, 'sugar': 19}},
    'lemon juice': {'tbsp': {'cal': 3, 'fat': 0, 'carb': 1, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0.4},
                    'cup': {'cal': 48, 'fat': 0, 'carb': 16, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 6.4}},
    'lime juice': {'tbsp': {'cal': 4, 'fat': 0, 'carb': 1, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0.3}},
    'orange juice': {'cup': {'cal': 112, 'fat': 0.5, 'carb': 26, 'protein': 2, 'sodium': 2, 'fiber': 0.5, 'sugar': 21}},
    'pineapple': {'cup': {'cal': 82, 'fat': 0.2, 'carb': 22, 'protein': 0.9, 'sodium': 2, 'fiber': 2, 'sugar': 16}},
    'crushed pineapple': {'can': {'cal': 280, 'fat': 0.4, 'carb': 68, 'protein': 2, 'sodium': 4, 'fiber': 4, 'sugar': 60}},
    'strawberries': {'cup': {'cal': 49, 'fat': 0.5, 'carb': 12, 'protein': 1, 'sodium': 1, 'fiber': 3, 'sugar': 7}},
    'blueberries': {'cup': {'cal': 84, 'fat': 0.5, 'carb': 21, 'protein': 1, 'sodium': 1, 'fiber': 4, 'sugar': 15}},
    'cranberries': {'cup': {'cal': 46, 'fat': 0.1, 'carb': 12, 'protein': 0.5, 'sodium': 2, 'fiber': 5, 'sugar': 4}},
    'raisins': {'cup': {'cal': 434, 'fat': 0.7, 'carb': 115, 'protein': 5, 'sodium': 17, 'fiber': 5, 'sugar': 86}},
    'coconut': {'cup': {'cal': 283, 'fat': 27, 'carb': 12, 'protein': 3, 'sodium': 16, 'fiber': 7, 'sugar': 5}},
    'dates': {'cup': {'cal': 415, 'fat': 0.6, 'carb': 110, 'protein': 3.6, 'sodium': 3, 'fiber': 12, 'sugar': 93}},
    'peach': {'medium': {'cal': 59, 'fat': 0.4, 'carb': 14, 'protein': 1, 'sodium': 0, 'fiber': 2, 'sugar': 13}},
    'cherries': {'cup': {'cal': 87, 'fat': 0.3, 'carb': 22, 'protein': 1.5, 'sodium': 0, 'fiber': 3, 'sugar': 18}},
    'pumpkin': {'cup': {'cal': 83, 'fat': 0.3, 'carb': 20, 'protein': 3, 'sodium': 12, 'fiber': 3, 'sugar': 8}},
    'calamondin': {'each': {'cal': 12, 'fat': 0.1, 'carb': 3, 'protein': 0.2, 'sodium': 1, 'fiber': 0.5, 'sugar': 1.5}},
    'calamondins': {'cup': {'cal': 60, 'fat': 0.5, 'carb': 15, 'protein': 1, 'sodium': 5, 'fiber': 2.5, 'sugar': 7.5}},

    # =========================================================================
    # NUTS & SEEDS
    # =========================================================================
    'walnuts': {'cup': {'cal': 765, 'fat': 76, 'carb': 16, 'protein': 18, 'sodium': 2, 'fiber': 8, 'sugar': 3}},
    'pecans': {'cup': {'cal': 753, 'fat': 78, 'carb': 15, 'protein': 10, 'sodium': 0, 'fiber': 10, 'sugar': 4}},
    'chopped pecans': {'cup': {'cal': 753, 'fat': 78, 'carb': 15, 'protein': 10, 'sodium': 0, 'fiber': 10, 'sugar': 4}},
    'almonds': {'cup': {'cal': 828, 'fat': 72, 'carb': 28, 'protein': 30, 'sodium': 1, 'fiber': 16, 'sugar': 6}},
    'peanuts': {'cup': {'cal': 854, 'fat': 72, 'carb': 24, 'protein': 35, 'sodium': 26, 'fiber': 12, 'sugar': 6}},
    'peanut butter': {'tbsp': {'cal': 94, 'fat': 8, 'carb': 3, 'protein': 4, 'sodium': 73, 'fiber': 1, 'sugar': 1},
                      'cup': {'cal': 1504, 'fat': 128, 'carb': 48, 'protein': 64, 'sodium': 1168, 'fiber': 16, 'sugar': 16}},
    'nuts': {'cup': {'cal': 800, 'fat': 72, 'carb': 24, 'protein': 20, 'sodium': 5, 'fiber': 8, 'sugar': 4}},
    'chopped nuts': {'cup': {'cal': 800, 'fat': 72, 'carb': 24, 'protein': 20, 'sodium': 5, 'fiber': 8, 'sugar': 4}},

    # =========================================================================
    # CHOCOLATE & BAKING
    # =========================================================================
    'chocolate chips': {'cup': {'cal': 805, 'fat': 50, 'carb': 92, 'protein': 7, 'sodium': 18, 'fiber': 8, 'sugar': 80}},
    'cocoa powder': {'tbsp': {'cal': 12, 'fat': 0.7, 'carb': 3, 'protein': 1, 'sodium': 1, 'fiber': 2, 'sugar': 0},
                     'cup': {'cal': 192, 'fat': 11.2, 'carb': 48, 'protein': 16, 'sodium': 16, 'fiber': 32, 'sugar': 0}},
    'chocolate': {'oz': {'cal': 155, 'fat': 9, 'carb': 17, 'protein': 1.4, 'sodium': 7, 'fiber': 2, 'sugar': 14}},
    'vanilla': {'tsp': {'cal': 12, 'fat': 0, 'carb': 0.5, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0.5}},
    'vanilla extract': {'tsp': {'cal': 12, 'fat': 0, 'carb': 0.5, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0.5}},
    'baking soda': {'tsp': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 1260, 'fiber': 0, 'sugar': 0}},
    'baking powder': {'tsp': {'cal': 2, 'fat': 0, 'carb': 1, 'protein': 0, 'sodium': 488, 'fiber': 0, 'sugar': 0}},
    'yeast': {'packet': {'cal': 21, 'fat': 0.3, 'carb': 3, 'protein': 3, 'sodium': 4, 'fiber': 1, 'sugar': 0}},
    'active dry yeast': {'packet': {'cal': 21, 'fat': 0.3, 'carb': 3, 'protein': 3, 'sodium': 4, 'fiber': 1, 'sugar': 0}},
    'gelatin': {'packet': {'cal': 23, 'fat': 0, 'carb': 0, 'protein': 6, 'sodium': 14, 'fiber': 0, 'sugar': 0}},
    'cream of tartar': {'tsp': {'cal': 2, 'fat': 0, 'carb': 0.5, 'protein': 0, 'sodium': 2, 'fiber': 0, 'sugar': 0}},
    'jello': {'package': {'cal': 80, 'fat': 0, 'carb': 19, 'protein': 2, 'sodium': 120, 'fiber': 0, 'sugar': 19}},
    'pudding mix': {'package': {'cal': 140, 'fat': 0, 'carb': 35, 'protein': 0, 'sodium': 340, 'fiber': 0, 'sugar': 28}},
    'cake mix': {'package': {'cal': 1600, 'fat': 32, 'carb': 312, 'protein': 16, 'sodium': 2800, 'fiber': 4, 'sugar': 168}},
    'yellow cake mix': {'package': {'cal': 1600, 'fat': 32, 'carb': 312, 'protein': 16, 'sodium': 2800, 'fiber': 4, 'sugar': 168}},

    # =========================================================================
    # CANNED GOODS & SOUPS
    # =========================================================================
    'cream of mushroom soup': {'can': {'cal': 225, 'fat': 15, 'carb': 18, 'protein': 4, 'sodium': 2175, 'fiber': 1, 'sugar': 2}},
    'cream of chicken soup': {'can': {'cal': 225, 'fat': 15, 'carb': 18, 'protein': 5, 'sodium': 2175, 'fiber': 1, 'sugar': 2}},
    'chicken broth': {'cup': {'cal': 15, 'fat': 0.5, 'carb': 1, 'protein': 2, 'sodium': 860, 'fiber': 0, 'sugar': 0}},
    'beef broth': {'cup': {'cal': 17, 'fat': 0.5, 'carb': 0.1, 'protein': 3, 'sodium': 893, 'fiber': 0, 'sugar': 0}},
    'vegetable broth': {'cup': {'cal': 12, 'fat': 0.2, 'carb': 2, 'protein': 0.5, 'sodium': 940, 'fiber': 0, 'sugar': 1}},
    'beans': {'cup': {'cal': 225, 'fat': 1, 'carb': 40, 'protein': 15, 'sodium': 400, 'fiber': 12, 'sugar': 1}},
    'pie filling': {'can': {'cal': 840, 'fat': 0, 'carb': 210, 'protein': 0, 'sodium': 100, 'fiber': 4, 'sugar': 180}},

    # =========================================================================
    # CONDIMENTS & SEASONINGS
    # =========================================================================
    'salt': {'tsp': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 2325, 'fiber': 0, 'sugar': 0}},
    'pepper': {'tsp': {'cal': 6, 'fat': 0.1, 'carb': 1.5, 'protein': 0.2, 'sodium': 1, 'fiber': 0.6, 'sugar': 0}},
    'black pepper': {'tsp': {'cal': 6, 'fat': 0.1, 'carb': 1.5, 'protein': 0.2, 'sodium': 1, 'fiber': 0.6, 'sugar': 0}},
    'white pepper': {'tsp': {'cal': 7, 'fat': 0.1, 'carb': 1.6, 'protein': 0.3, 'sodium': 0, 'fiber': 0.6, 'sugar': 0}},
    'salt and pepper': {'tsp': {'cal': 3, 'fat': 0, 'carb': 0.7, 'protein': 0.1, 'sodium': 1163, 'fiber': 0.3, 'sugar': 0}},
    'ketchup': {'tbsp': {'cal': 19, 'fat': 0, 'carb': 5, 'protein': 0.2, 'sodium': 154, 'fiber': 0, 'sugar': 4}},
    'mustard': {'tsp': {'cal': 3, 'fat': 0.2, 'carb': 0.3, 'protein': 0.2, 'sodium': 57, 'fiber': 0, 'sugar': 0}},
    'dry mustard': {'tsp': {'cal': 9, 'fat': 0.6, 'carb': 0.5, 'protein': 0.5, 'sodium': 1, 'fiber': 0.2, 'sugar': 0}},
    'soy sauce': {'tbsp': {'cal': 9, 'fat': 0, 'carb': 0.8, 'protein': 1.3, 'sodium': 879, 'fiber': 0, 'sugar': 0}},
    'oyster sauce': {'tbsp': {'cal': 9, 'fat': 0, 'carb': 2, 'protein': 0.2, 'sodium': 437, 'fiber': 0, 'sugar': 1}},
    'worcestershire sauce': {'tbsp': {'cal': 13, 'fat': 0, 'carb': 3, 'protein': 0, 'sodium': 167, 'fiber': 0, 'sugar': 2}},
    'vinegar': {'tbsp': {'cal': 3, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'white vinegar': {'tbsp': {'cal': 3, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'hot sauce': {'tsp': {'cal': 1, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 124, 'fiber': 0, 'sugar': 0}},
    'chili powder': {'tsp': {'cal': 8, 'fat': 0.4, 'carb': 1.4, 'protein': 0.3, 'sodium': 26, 'fiber': 0.9, 'sugar': 0.2}},
    'garlic powder': {'tsp': {'cal': 10, 'fat': 0, 'carb': 2, 'protein': 0.5, 'sodium': 2, 'fiber': 0.3, 'sugar': 0}},
    'onion powder': {'tsp': {'cal': 8, 'fat': 0, 'carb': 2, 'protein': 0.2, 'sodium': 1, 'fiber': 0.1, 'sugar': 0.4}},
    'garlic salt': {'tsp': {'cal': 3, 'fat': 0, 'carb': 0.7, 'protein': 0.1, 'sodium': 1480, 'fiber': 0, 'sugar': 0}},
    'seasoned salt': {'tsp': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 1360, 'fiber': 0, 'sugar': 0}},

    # =========================================================================
    # HERBS & SPICES
    # =========================================================================
    'cinnamon': {'tsp': {'cal': 6, 'fat': 0, 'carb': 2, 'protein': 0.1, 'sodium': 0, 'fiber': 1, 'sugar': 0}},
    'ground cinnamon': {'tsp': {'cal': 6, 'fat': 0, 'carb': 2, 'protein': 0.1, 'sodium': 0, 'fiber': 1, 'sugar': 0}},
    'nutmeg': {'tsp': {'cal': 12, 'fat': 0.8, 'carb': 1.1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.5, 'sugar': 0}},
    'ground nutmeg': {'tsp': {'cal': 12, 'fat': 0.8, 'carb': 1.1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.5, 'sugar': 0}},
    'ginger': {'tsp': {'cal': 6, 'fat': 0.1, 'carb': 1.3, 'protein': 0.2, 'sodium': 1, 'fiber': 0.2, 'sugar': 0.1}},
    'ground ginger': {'tsp': {'cal': 6, 'fat': 0.1, 'carb': 1.3, 'protein': 0.2, 'sodium': 1, 'fiber': 0.2, 'sugar': 0.1}},
    'fresh ginger': {'tbsp': {'cal': 5, 'fat': 0, 'carb': 1, 'protein': 0.1, 'sodium': 1, 'fiber': 0.1, 'sugar': 0.1}},
    'paprika': {'tsp': {'cal': 6, 'fat': 0.3, 'carb': 1.2, 'protein': 0.3, 'sodium': 2, 'fiber': 0.7, 'sugar': 0.3}},
    'cayenne pepper': {'tsp': {'cal': 6, 'fat': 0.3, 'carb': 1, 'protein': 0.2, 'sodium': 1, 'fiber': 0.5, 'sugar': 0.2}},
    'basil': {'tsp': {'cal': 1, 'fat': 0, 'carb': 0.1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.1, 'sugar': 0}},
    'fresh parsley': {'tbsp': {'cal': 1, 'fat': 0, 'carb': 0.2, 'protein': 0.1, 'sodium': 2, 'fiber': 0.1, 'sugar': 0}},
    'cilantro': {'tbsp': {'cal': 1, 'fat': 0, 'carb': 0.1, 'protein': 0.1, 'sodium': 1, 'fiber': 0, 'sugar': 0}},
    'italian seasoning': {'tsp': {'cal': 3, 'fat': 0.1, 'carb': 0.6, 'protein': 0.1, 'sodium': 1, 'fiber': 0.3, 'sugar': 0}},
    'allspice': {'tsp': {'cal': 5, 'fat': 0.2, 'carb': 1.4, 'protein': 0.1, 'sodium': 1, 'fiber': 0.4, 'sugar': 0}},
    'cloves': {'tsp': {'cal': 7, 'fat': 0.4, 'carb': 1.3, 'protein': 0.1, 'sodium': 5, 'fiber': 0.7, 'sugar': 0.5}},
    'oregano': {'tsp': {'cal': 3, 'fat': 0.1, 'carb': 0.7, 'protein': 0.1, 'sodium': 0, 'fiber': 0.4, 'sugar': 0}},
    'dried oregano': {'tsp': {'cal': 3, 'fat': 0.1, 'carb': 0.7, 'protein': 0.1, 'sodium': 0, 'fiber': 0.4, 'sugar': 0}},
    'thyme': {'tsp': {'cal': 3, 'fat': 0.1, 'carb': 0.6, 'protein': 0.1, 'sodium': 1, 'fiber': 0.3, 'sugar': 0}},
    'dried thyme': {'tsp': {'cal': 3, 'fat': 0.1, 'carb': 0.6, 'protein': 0.1, 'sodium': 1, 'fiber': 0.3, 'sugar': 0}},
    'turmeric': {'tsp': {'cal': 8, 'fat': 0.2, 'carb': 1.4, 'protein': 0.3, 'sodium': 1, 'fiber': 0.5, 'sugar': 0.1}},
    'curry powder': {'tsp': {'cal': 7, 'fat': 0.3, 'carb': 1.2, 'protein': 0.3, 'sodium': 1, 'fiber': 0.7, 'sugar': 0.1}},
    'dill': {'tsp': {'cal': 3, 'fat': 0.1, 'carb': 0.5, 'protein': 0.2, 'sodium': 2, 'fiber': 0.1, 'sugar': 0}},
    'dried dill': {'tsp': {'cal': 3, 'fat': 0.1, 'carb': 0.5, 'protein': 0.2, 'sodium': 2, 'fiber': 0.1, 'sugar': 0}},
    'fresh dill': {'tbsp': {'cal': 1, 'fat': 0, 'carb': 0.1, 'protein': 0.1, 'sodium': 2, 'fiber': 0, 'sugar': 0}},
    'bay leaves': {'each': {'cal': 2, 'fat': 0.1, 'carb': 0.5, 'protein': 0, 'sodium': 0, 'fiber': 0.2, 'sugar': 0}},
    'bay leaf': {'each': {'cal': 2, 'fat': 0.1, 'carb': 0.5, 'protein': 0, 'sodium': 0, 'fiber': 0.2, 'sugar': 0}},

    # =========================================================================
    # ADDITIONAL COMMON INGREDIENTS
    # =========================================================================
    'oatmeal': {'cup': {'cal': 307, 'fat': 5, 'carb': 55, 'protein': 11, 'sodium': 5, 'fiber': 8, 'sugar': 1}},
    'sesame seeds': {'tbsp': {'cal': 52, 'fat': 4.5, 'carb': 2, 'protein': 1.6, 'sodium': 1, 'fiber': 1, 'sugar': 0}},
    'wheat germ': {'tbsp': {'cal': 26, 'fat': 0.7, 'carb': 3.7, 'protein': 2, 'sodium': 0, 'fiber': 1, 'sugar': 0}},
    'sunflower seeds': {'cup': {'cal': 818, 'fat': 72, 'carb': 28, 'protein': 29, 'sodium': 4, 'fiber': 12, 'sugar': 3}},
    'marshmallows': {'cup': {'cal': 159, 'fat': 0.1, 'carb': 41, 'protein': 1.4, 'sodium': 22, 'fiber': 0, 'sugar': 29}},
    'miniature marshmallows': {'cup': {'cal': 159, 'fat': 0.1, 'carb': 41, 'protein': 1.4, 'sodium': 22, 'fiber': 0, 'sugar': 29}},
    'elbow macaroni': {'cup': {'cal': 200, 'fat': 1, 'carb': 41, 'protein': 7, 'sodium': 2, 'fiber': 2, 'sugar': 1}},
    'rotini': {'cup': {'cal': 200, 'fat': 1, 'carb': 41, 'protein': 7, 'sodium': 2, 'fiber': 2, 'sugar': 1}},
    'lemon rind': {'tbsp': {'cal': 3, 'fat': 0, 'carb': 1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.4, 'sugar': 0.4}},
    'grated lemon rind': {'tbsp': {'cal': 3, 'fat': 0, 'carb': 1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.4, 'sugar': 0.4}},
    'lemon zest': {'tbsp': {'cal': 3, 'fat': 0, 'carb': 1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.4, 'sugar': 0.4}},
    'orange peel': {'tbsp': {'cal': 6, 'fat': 0, 'carb': 2, 'protein': 0.1, 'sodium': 0, 'fiber': 0.6, 'sugar': 1}},
    'grated orange peel': {'tbsp': {'cal': 6, 'fat': 0, 'carb': 2, 'protein': 0.1, 'sodium': 0, 'fiber': 0.6, 'sugar': 1}},
    'orange zest': {'tbsp': {'cal': 6, 'fat': 0, 'carb': 2, 'protein': 0.1, 'sodium': 0, 'fiber': 0.6, 'sugar': 1}},
    'almond extract': {'tsp': {'cal': 10, 'fat': 0, 'carb': 0.3, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0.3}},
    'lemon extract': {'tsp': {'cal': 10, 'fat': 0, 'carb': 0.3, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0.3}},
    'vodka': {'oz': {'cal': 64, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'rum': {'oz': {'cal': 64, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'brandy': {'oz': {'cal': 64, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'frozen mixed vegetables': {'cup': {'cal': 82, 'fat': 0.5, 'carb': 16, 'protein': 4, 'sodium': 64, 'fiber': 5, 'sugar': 4}},
    'mixed vegetables': {'cup': {'cal': 82, 'fat': 0.5, 'carb': 16, 'protein': 4, 'sodium': 64, 'fiber': 5, 'sugar': 4}},
    'okra': {'cup': {'cal': 33, 'fat': 0.2, 'carb': 7, 'protein': 2, 'sodium': 7, 'fiber': 3, 'sugar': 1}},
    'cranberry juice': {'cup': {'cal': 116, 'fat': 0.3, 'carb': 31, 'protein': 0, 'sodium': 5, 'fiber': 0.3, 'sugar': 31}},
    'pretzels': {'cup': {'cal': 229, 'fat': 2, 'carb': 48, 'protein': 5, 'sodium': 814, 'fiber': 2, 'sugar': 1}},
    'chex cereal': {'cup': {'cal': 110, 'fat': 0.5, 'carb': 25, 'protein': 2, 'sodium': 220, 'fiber': 1, 'sugar': 2}},
    'bread slices': {'each': {'cal': 79, 'fat': 1, 'carb': 15, 'protein': 3, 'sodium': 147, 'fiber': 1, 'sugar': 1}},
    'bread': {'slice': {'cal': 79, 'fat': 1, 'carb': 15, 'protein': 3, 'sodium': 147, 'fiber': 1, 'sugar': 1}},
    'brownie mix': {'package': {'cal': 1600, 'fat': 32, 'carb': 280, 'protein': 16, 'sodium': 800, 'fiber': 4, 'sugar': 160}},
    'marinara sauce': {'cup': {'cal': 80, 'fat': 2, 'carb': 12, 'protein': 2, 'sodium': 560, 'fiber': 2, 'sugar': 8}},
    'liquid pectin': {'pouch': {'cal': 10, 'fat': 0, 'carb': 3, 'protein': 0, 'sodium': 5, 'fiber': 1, 'sugar': 0}},
    'vegetable cooking spray': {'each': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'cooking spray': {'each': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'nonstick cooking spray': {'each': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'cumin': {'tsp': {'cal': 8, 'fat': 0.5, 'carb': 0.9, 'protein': 0.4, 'sodium': 4, 'fiber': 0.2, 'sugar': 0}},
    'ground cumin': {'tsp': {'cal': 8, 'fat': 0.5, 'carb': 0.9, 'protein': 0.4, 'sodium': 4, 'fiber': 0.2, 'sugar': 0}},
    'pecan halves': {'cup': {'cal': 753, 'fat': 78, 'carb': 15, 'protein': 10, 'sodium': 0, 'fiber': 10, 'sugar': 4}},
    'unsweetened cocoa': {'tbsp': {'cal': 12, 'fat': 0.7, 'carb': 3, 'protein': 1, 'sodium': 1, 'fiber': 2, 'sugar': 0}},
    'pie shell': {'each': {'cal': 650, 'fat': 40, 'carb': 64, 'protein': 8, 'sodium': 400, 'fiber': 2, 'sugar': 2}},
    'baked pie shell': {'each': {'cal': 650, 'fat': 40, 'carb': 64, 'protein': 8, 'sodium': 400, 'fiber': 2, 'sugar': 2}},
    'unbaked pie shell': {'each': {'cal': 650, 'fat': 40, 'carb': 64, 'protein': 8, 'sodium': 400, 'fiber': 2, 'sugar': 2}},
    'tabasco sauce': {'tsp': {'cal': 1, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 124, 'fiber': 0, 'sugar': 0}},
    'whipped cream': {'cup': {'cal': 400, 'fat': 43, 'carb': 3, 'protein': 2, 'sodium': 44, 'fiber': 0, 'sugar': 3}},
    'food coloring': {'drop': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'green food coloring': {'drop': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'red food coloring': {'drop': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'dried apricots': {'cup': {'cal': 313, 'fat': 0.7, 'carb': 81, 'protein': 4.4, 'sodium': 13, 'fiber': 9.5, 'sugar': 69}},
    'apricots': {'cup': {'cal': 79, 'fat': 0.6, 'carb': 18, 'protein': 2.3, 'sodium': 2, 'fiber': 3, 'sugar': 15}},
    'green chilies': {'can': {'cal': 30, 'fat': 0, 'carb': 6, 'protein': 1, 'sodium': 550, 'fiber': 2, 'sugar': 3}},
    'chopped green chilies': {'can': {'cal': 30, 'fat': 0, 'carb': 6, 'protein': 1, 'sodium': 550, 'fiber': 2, 'sugar': 3}},
    'poultry seasoning': {'tsp': {'cal': 5, 'fat': 0.2, 'carb': 1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.2, 'sugar': 0}},
    'lemons': {'each': {'cal': 17, 'fat': 0.2, 'carb': 5, 'protein': 0.6, 'sodium': 1, 'fiber': 1.6, 'sugar': 1.5}},
    'lemon': {'each': {'cal': 17, 'fat': 0.2, 'carb': 5, 'protein': 0.6, 'sodium': 1, 'fiber': 1.6, 'sugar': 1.5}},
    'grated lemon peel': {'tbsp': {'cal': 3, 'fat': 0, 'carb': 1, 'protein': 0.1, 'sodium': 0, 'fiber': 0.4, 'sugar': 0.4}},
    'bisquick': {'cup': {'cal': 480, 'fat': 16, 'carb': 72, 'protein': 8, 'sodium': 1360, 'fiber': 2, 'sugar': 8}},
    'sauerkraut': {'cup': {'cal': 27, 'fat': 0.2, 'carb': 6, 'protein': 1.3, 'sodium': 939, 'fiber': 4, 'sugar': 3}},
    'lard': {'tbsp': {'cal': 115, 'fat': 13, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'dried parsley': {'tbsp': {'cal': 4, 'fat': 0.1, 'carb': 0.6, 'protein': 0.3, 'sodium': 6, 'fiber': 0.2, 'sugar': 0.1}},
    'dried parsley flakes': {'tbsp': {'cal': 4, 'fat': 0.1, 'carb': 0.6, 'protein': 0.3, 'sodium': 6, 'fiber': 0.2, 'sugar': 0.1}},
    'parsley flakes': {'tbsp': {'cal': 4, 'fat': 0.1, 'carb': 0.6, 'protein': 0.3, 'sodium': 6, 'fiber': 0.2, 'sugar': 0.1}},

    # =========================================================================
    # BEVERAGES & ALCOHOL
    # =========================================================================
    'wine': {'cup': {'cal': 200, 'fat': 0, 'carb': 5, 'protein': 0.2, 'sodium': 12, 'fiber': 0, 'sugar': 2}},
    'chinese cooking wine': {'tbsp': {'cal': 15, 'fat': 0, 'carb': 2, 'protein': 0, 'sodium': 180, 'fiber': 0, 'sugar': 1}},
    'sherry': {'oz': {'cal': 45, 'fat': 0, 'carb': 2, 'protein': 0.1, 'sodium': 3, 'fiber': 0, 'sugar': 1}},
    'coffee': {'cup': {'cal': 2, 'fat': 0, 'carb': 0, 'protein': 0.3, 'sodium': 5, 'fiber': 0, 'sugar': 0}},
    'water': {'cup': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'warm water': {'cup': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'hot water': {'cup': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'cold water': {'cup': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
    'boiling water': {'cup': {'cal': 0, 'fat': 0, 'carb': 0, 'protein': 0, 'sodium': 0, 'fiber': 0, 'sugar': 0}},
}

# Ingredient aliases for fuzzy matching
INGREDIENT_ALIASES = {
    'butter or margarine': 'butter',
    'oleo (margarine)': 'margarine',
    'oleo': 'margarine',
    'large eggs': 'eggs',
    'large egg': 'egg',
    'white sugar': 'sugar',
    'vegetable oil': 'oil',
    'cooking oil': 'oil',
    'canola oil': 'oil',
    'boneless chicken': 'chicken breast',
    'chicken breast halves': 'chicken breast',
    'green onion': 'green onions',
    'scallions': 'green onions',
}

# Unit conversions
UNIT_CONVERSIONS = {
    'tbsp': {'tsp': 3, 'cup': 0.0625, 'ml': 15},
    'tsp': {'tbsp': 0.333, 'cup': 0.0208, 'ml': 5},
    'cup': {'tbsp': 16, 'tsp': 48, 'oz': 8, 'ml': 240},
    'oz': {'cup': 0.125, 'lb': 0.0625, 'g': 28.35},
    'lb': {'oz': 16, 'g': 454, 'cup': 2},
    'quart': {'cup': 4, 'pint': 2},
    'pint': {'cup': 2, 'quart': 0.5},
    'gallon': {'quart': 4, 'cup': 16},
}


def parse_quantity(qty_str):
    """Parse quantity string to float, handling fractions and ranges."""
    if not qty_str:
        return 1.0

    qty_str = str(qty_str).strip()

    # Handle ranges (e.g., "1-2") - take average
    if '-' in qty_str and not qty_str.startswith('-'):
        parts = qty_str.split('-')
        if len(parts) == 2:
            try:
                return (parse_quantity(parts[0]) + parse_quantity(parts[1])) / 2
            except:
                pass

    # Handle mixed numbers (e.g., "1 1/2")
    qty_str = qty_str.replace('-', ' ')
    parts = qty_str.split()

    total = 0.0
    for part in parts:
        try:
            if '/' in part:
                total += float(Fraction(part))
            else:
                total += float(part)
        except:
            pass

    return total if total > 0 else 1.0


def find_ingredient_match(item_name):
    """Find best matching ingredient in database."""
    item_lower = item_name.lower().strip()

    # Direct match
    if item_lower in NUTRITION_DB:
        return item_lower

    # Check aliases
    if item_lower in INGREDIENT_ALIASES:
        alias = INGREDIENT_ALIASES[item_lower]
        if alias in NUTRITION_DB:
            return alias

    # Partial matches - ingredient contains DB entry
    for db_item in NUTRITION_DB:
        if db_item in item_lower:
            return db_item

    # Partial matches - DB entry contains ingredient
    for db_item in NUTRITION_DB:
        if item_lower in db_item:
            return db_item

    # Check aliases with partial matching
    for alias, target in INGREDIENT_ALIASES.items():
        if alias in item_lower and target in NUTRITION_DB:
            return target

    return None


def get_nutrition_for_ingredient(match, unit, qty):
    """Get nutrition values for a matched ingredient with unit conversion."""
    if match not in NUTRITION_DB:
        return None

    db_entry = NUTRITION_DB[match]
    unit_lower = unit.lower().strip() if unit else ''

    # Direct unit match
    if unit_lower in db_entry:
        nutrition = db_entry[unit_lower]
    # Common default units
    elif unit_lower in ['', 'each', 'medium', 'large', 'small', 'whole']:
        for default_unit in ['each', 'medium', 'large', 'cup', 'oz', 'tbsp', 'tsp']:
            if default_unit in db_entry:
                nutrition = db_entry[default_unit]
                break
        else:
            nutrition = list(db_entry.values())[0]
    # Try unit conversion
    elif unit_lower in UNIT_CONVERSIONS:
        converted = False
        for target_unit, factor in UNIT_CONVERSIONS.get(unit_lower, {}).items():
            if target_unit in db_entry:
                nutrition = db_entry[target_unit]
                qty = qty * (1 / factor)  # Convert quantity
                converted = True
                break
        if not converted:
            nutrition = list(db_entry.values())[0]
    else:
        # Use first available unit
        nutrition = list(db_entry.values())[0]

    # Calculate totals
    return {
        'cal': nutrition.get('cal', 0) * qty,
        'fat': nutrition.get('fat', 0) * qty,
        'carb': nutrition.get('carb', 0) * qty,
        'protein': nutrition.get('protein', 0) * qty,
        'sodium': nutrition.get('sodium', 0) * qty,
        'fiber': nutrition.get('fiber', 0) * qty,
        'sugar': nutrition.get('sugar', 0) * qty,
    }


def estimate_nutrition(recipe):
    """Estimate nutrition for a recipe based on ingredients."""
    ingredients = recipe.get('ingredients', [])
    servings = recipe.get('servings', 4)

    totals = {
        'calories': 0,
        'fat_g': 0,
        'carbs_g': 0,
        'protein_g': 0,
        'sodium_mg': 0,
        'fiber_g': 0,
        'sugar_g': 0
    }

    missing_ingredients = []
    matched_count = 0

    for ing in ingredients:
        item = ing.get('item', '')
        qty = parse_quantity(ing.get('quantity', '1'))
        unit = ing.get('unit', '')

        # Find matching ingredient
        match = find_ingredient_match(item)

        if not match:
            missing_ingredients.append(item)
            continue

        # Get nutrition values
        nutrition = get_nutrition_for_ingredient(match, unit, qty)
        if nutrition:
            totals['calories'] += nutrition['cal']
            totals['fat_g'] += nutrition['fat']
            totals['carbs_g'] += nutrition['carb']
            totals['protein_g'] += nutrition['protein']
            totals['sodium_mg'] += nutrition['sodium']
            totals['fiber_g'] += nutrition['fiber']
            totals['sugar_g'] += nutrition['sugar']
            matched_count += 1

    # Calculate per serving
    per_serving = {
        'calories': round(totals['calories'] / servings),
        'total_fat': round(totals['fat_g'] / servings, 1),
        'saturated_fat': None,  # Would need more detailed DB
        'cholesterol': None,
        'sodium': round(totals['sodium_mg'] / servings),
        'total_carbohydrates': round(totals['carbs_g'] / servings, 1),
        'dietary_fiber': round(totals['fiber_g'] / servings, 1),
        'sugars': round(totals['sugar_g'] / servings, 1),
        'protein': round(totals['protein_g'] / servings, 1)
    }

    # Determine estimation status
    total_ingredients = len(ingredients)
    if total_ingredients == 0:
        status = 'no_ingredients'
    elif matched_count == total_ingredients:
        status = 'complete'
    elif matched_count >= total_ingredients * 0.7:
        status = 'good'
    elif matched_count >= total_ingredients * 0.5:
        status = 'partial'
    else:
        status = 'insufficient'

    return {
        'status': status,
        'servings': servings,
        'per_serving': per_serving,
        'matched': matched_count,
        'total': total_ingredients,
        'missing': missing_ingredients
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Estimate nutrition for recipes')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview without saving')
    parser.add_argument('--recipe-id', type=str, help='Process specific recipe only')
    parser.add_argument('--collection', type=str, default='grandma-baker', help='Collection to process')
    parser.add_argument('--force', action='store_true', help='Re-estimate all recipes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    # Load recipes
    master_path = Path(__file__).parent.parent / 'data' / 'recipes_master.json'
    with open(master_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = data.get('recipes', [])

    # Filter recipes
    target_recipes = []
    for recipe in recipes:
        if args.collection and recipe.get('collection') != args.collection:
            continue
        if args.recipe_id and recipe.get('id') != args.recipe_id:
            continue
        if recipe.get('category') == 'tips':
            continue
        if not recipe.get('servings'):
            continue
        if not args.force and recipe.get('nutrition', {}).get('calories'):
            continue
        target_recipes.append(recipe)

    print(f"Processing {len(target_recipes)} recipes...")
    print()

    # Process recipes
    stats = {'complete': 0, 'good': 0, 'partial': 0, 'insufficient': 0}
    all_missing = []

    for recipe in target_recipes:
        result = estimate_nutrition(recipe)

        if args.verbose:
            print(f"{recipe['title'][:40]:<40} | {result['status']:<12} | "
                  f"{result['matched']}/{result['total']} ingredients | "
                  f"{result['per_serving']['calories']} cal/serving")
            if result['missing']:
                print(f"  Missing: {', '.join(result['missing'][:5])}")

        stats[result['status']] = stats.get(result['status'], 0) + 1
        all_missing.extend(result['missing'])

        # Update recipe nutrition
        if result['status'] in ['complete', 'good', 'partial']:
            recipe['nutrition'] = {
                'per_serving': True,
                'estimation_status': result['status'],
                'servings_used': result['servings'],
                **result['per_serving']
            }

    # Summary
    print()
    print("=" * 60)
    print("NUTRITION ESTIMATION SUMMARY")
    print("=" * 60)
    print(f"Complete (100% matched):    {stats.get('complete', 0)}")
    print(f"Good (70-99% matched):      {stats.get('good', 0)}")
    print(f"Partial (50-69% matched):   {stats.get('partial', 0)}")
    print(f"Insufficient (<50%):        {stats.get('insufficient', 0)}")
    print()

    # Most common missing ingredients
    from collections import Counter
    missing_counts = Counter(all_missing)
    print("Top 20 missing ingredients (add to NUTRITION_DB):")
    for item, count in missing_counts.most_common(20):
        print(f"  {count:>3}x  {item}")

    # Save if not dry run
    if not args.dry_run:
        with open(master_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print()
        print(f"Saved to {master_path}")
    else:
        print()
        print("DRY RUN - no changes saved")

    return 0


if __name__ == '__main__':
    sys.exit(main())
