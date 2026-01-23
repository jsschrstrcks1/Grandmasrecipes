#!/usr/bin/env python3
"""
Elite Nutrition Estimation Script for Family Recipe Archive

Combines comprehensive ingredient databases and OCR handling from all family
recipe repositories (Allrecipes, MomsRecipes, Grannysrecipes, Grandmasrecipes).

Features:
- 1,909 ingredients with USDA nutritional values
- 5,240+ synonym mappings for ingredient normalization
- 30+ OCR artifact patterns for scanned recipe cards
- Smart serving inference by recipe category
- Equipment detection (skips non-food items)

Usage:
    python scripts/estimate_nutrition_elite.py [options]

Options:
    --dry-run        Preview without saving
    --verbose        Show detailed output
    --recipe-id ID   Process single recipe
    --force          Re-estimate existing nutrition
    --collection ID  Filter by collection

Nutrients tracked: calories, fat, carbs, protein, sodium, fiber, sugar
"""

import json
import re
import glob
import os
import sys
import argparse
from fractions import Fraction
from pathlib import Path
from collections import Counter

# =============================================================================
# COMPREHENSIVE NUTRITION DATABASE (USDA values)
# Format: {ingredient: {unit: {cal, fat, carbs, protein, sodium, fiber, sugar}}}
# =============================================================================

NUTRITION_DB = {
    # =========================================================================
    # WATER & LIQUIDS (0 or minimal calories)
    # =========================================================================
    "water": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
              "tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
              "can": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
              "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "ice": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # FLOURS & STARCHES
    # =========================================================================
    "all-purpose flour": {"cup": {"cal": 455, "fat": 1.2, "carbs": 95, "protein": 13, "sodium": 2, "fiber": 3.4, "sugar": 0.3},
                         "tbsp": {"cal": 28, "fat": 0.1, "carbs": 6, "protein": 0.8, "sodium": 0, "fiber": 0.2, "sugar": 0},
                         "oz": {"cal": 103, "fat": 0.3, "carbs": 22, "protein": 3, "sodium": 0, "fiber": 0.8, "sugar": 0.1},
                         "g": {"cal": 3.6, "fat": 0.01, "carbs": 0.76, "protein": 0.1, "sodium": 0, "fiber": 0.03, "sugar": 0}},
    "flour": {"cup": {"cal": 455, "fat": 1.2, "carbs": 95, "protein": 13, "sodium": 2, "fiber": 3.4, "sugar": 0.3},
             "tbsp": {"cal": 28, "fat": 0.1, "carbs": 6, "protein": 0.8, "sodium": 0, "fiber": 0.2, "sugar": 0},
             "oz": {"cal": 103, "fat": 0.3, "carbs": 22, "protein": 3, "sodium": 0, "fiber": 0.8, "sugar": 0.1},
             "g": {"cal": 3.6, "fat": 0.01, "carbs": 0.76, "protein": 0.1, "sodium": 0, "fiber": 0.03, "sugar": 0}},
    "whole wheat flour": {"cup": {"cal": 408, "fat": 2.2, "carbs": 87, "protein": 16, "sodium": 6, "fiber": 15, "sugar": 0.4},
                         "oz": {"cal": 97, "fat": 0.5, "carbs": 21, "protein": 4, "sodium": 1, "fiber": 3.6, "sugar": 0.1},
                         "g": {"cal": 3.4, "fat": 0.02, "carbs": 0.73, "protein": 0.13, "sodium": 0.05, "fiber": 0.13, "sugar": 0}},
    "bread flour": {"cup": {"cal": 495, "fat": 1.5, "carbs": 99, "protein": 16, "sodium": 2, "fiber": 3.4, "sugar": 0.3},
                   "oz": {"cal": 110, "fat": 0.3, "carbs": 22, "protein": 3.6, "sodium": 0, "fiber": 0.8, "sugar": 0.1},
                   "g": {"cal": 3.9, "fat": 0.01, "carbs": 0.78, "protein": 0.13, "sodium": 0, "fiber": 0.03, "sugar": 0}},
    "cake flour": {"cup": {"cal": 400, "fat": 1, "carbs": 88, "protein": 9, "sodium": 2, "fiber": 2, "sugar": 0.3}},
    "self-rising flour": {"cup": {"cal": 443, "fat": 1.2, "carbs": 93, "protein": 12, "sodium": 1520, "fiber": 3, "sugar": 0.3}},
    "almond flour": {"cup": {"cal": 640, "fat": 56, "carbs": 24, "protein": 24, "sodium": 0, "fiber": 12, "sugar": 4}},
    "coconut flour": {"cup": {"cal": 480, "fat": 16, "carbs": 64, "protein": 16, "sodium": 64, "fiber": 40, "sugar": 8}},
    "cornstarch": {"cup": {"cal": 488, "fat": 0.1, "carbs": 117, "protein": 0.3, "sodium": 12, "fiber": 1, "sugar": 0},
                  "tbsp": {"cal": 30, "fat": 0, "carbs": 7, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0}},
    "tapioca": {"cup": {"cal": 544, "fat": 0, "carbs": 135, "protein": 0, "sodium": 2, "fiber": 1, "sugar": 5},
               "tbsp": {"cal": 34, "fat": 0, "carbs": 8, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "cornmeal": {"cup": {"cal": 442, "fat": 4, "carbs": 94, "protein": 10, "sodium": 43, "fiber": 9, "sugar": 1},
                 "package": {"cal": 850, "fat": 7, "carbs": 180, "protein": 18, "sodium": 1400, "fiber": 6, "sugar": 24},
                 "packet": {"cal": 850, "fat": 7, "carbs": 180, "protein": 18, "sodium": 1400, "fiber": 6, "sugar": 24},
                 "oz": {"cal": 104, "fat": 1, "carbs": 22, "protein": 2.5, "sodium": 10, "fiber": 2, "sugar": 0.2}},
    "masa harina": {"cup": {"cal": 416, "fat": 4, "carbs": 87, "protein": 11, "sodium": 6, "fiber": 7, "sugar": 1}},
    "chickpea flour": {"cup": {"cal": 356, "fat": 6, "carbs": 53, "protein": 21, "sodium": 59, "fiber": 10, "sugar": 10},
                      "oz": {"cal": 100, "fat": 1.7, "carbs": 15, "protein": 6, "sodium": 17, "fiber": 3, "sugar": 3}},
    "garbanzo bean flour": {"cup": {"cal": 356, "fat": 6, "carbs": 53, "protein": 21, "sodium": 59, "fiber": 10, "sugar": 10}},
    "semolina": {"cup": {"cal": 601, "fat": 1.8, "carbs": 122, "protein": 21, "sodium": 2, "fiber": 6.5, "sugar": 0},
                "oz": {"cal": 106, "fat": 0.3, "carbs": 22, "protein": 4, "sodium": 0, "fiber": 1, "sugar": 0}},
    "semolina flour": {"cup": {"cal": 601, "fat": 1.8, "carbs": 122, "protein": 21, "sodium": 2, "fiber": 6.5, "sugar": 0}},
    "rye flour": {"cup": {"cal": 361, "fat": 2, "carbs": 75, "protein": 11, "sodium": 2, "fiber": 15, "sugar": 1}},
    "whole wheat flour": {"cup": {"cal": 408, "fat": 2.2, "carbs": 87, "protein": 16, "sodium": 6, "fiber": 15, "sugar": 0.4},
                         "oz": {"cal": 96, "fat": 0.5, "carbs": 20, "protein": 4, "sodium": 1, "fiber": 3.5, "sugar": 0.1}},

    # =========================================================================
    # SUGARS & SWEETENERS
    # =========================================================================
    "sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200},
             "tbsp": {"cal": 48, "fat": 0, "carbs": 12.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 12.5},
             "tsp": {"cal": 16, "fat": 0, "carbs": 4, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 4}},
    "brown sugar": {"cup": {"cal": 836, "fat": 0, "carbs": 216, "protein": 0, "sodium": 57, "fiber": 0, "sugar": 213},
                   "tbsp": {"cal": 52, "fat": 0, "carbs": 13.5, "protein": 0, "sodium": 4, "fiber": 0, "sugar": 13}},
    "powdered sugar": {"cup": {"cal": 467, "fat": 0, "carbs": 120, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 117},
                       "tbsp": {"cal": 29, "fat": 0, "carbs": 7.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 7.3},
                       "": {"cal": 29, "fat": 0, "carbs": 7.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 7.3}},
    "honey": {"cup": {"cal": 1031, "fat": 0, "carbs": 279, "protein": 1, "sodium": 14, "fiber": 0, "sugar": 278},
             "tbsp": {"cal": 64, "fat": 0, "carbs": 17, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 17}},
    "maple syrup": {"cup": {"cal": 840, "fat": 0.2, "carbs": 216, "protein": 0, "sodium": 27, "fiber": 0, "sugar": 192},
                   "tbsp": {"cal": 52, "fat": 0, "carbs": 13, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 12}},
    "molasses": {"cup": {"cal": 977, "fat": 0, "carbs": 252, "protein": 0, "sodium": 121, "fiber": 0, "sugar": 183},
                "tbsp": {"cal": 58, "fat": 0, "carbs": 15, "protein": 0, "sodium": 7, "fiber": 0, "sugar": 11}},
    "corn syrup": {"cup": {"cal": 925, "fat": 0, "carbs": 251, "protein": 0, "sodium": 395, "fiber": 0, "sugar": 155},
                  "tbsp": {"cal": 57, "fat": 0, "carbs": 15.5, "protein": 0, "sodium": 24, "fiber": 0, "sugar": 9.5}},
    "agave": {"tbsp": {"cal": 60, "fat": 0, "carbs": 16, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 15}},
    "stevia": {"tsp": {"cal": 0, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "splenda": {"tsp": {"cal": 0, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "caramels": {"": {"cal": 39, "fat": 0.8, "carbs": 8, "protein": 0.5, "sodium": 25, "fiber": 0, "sugar": 6},
                "cup": {"cal": 624, "fat": 13, "carbs": 128, "protein": 8, "sodium": 400, "fiber": 0, "sugar": 96}},
    "caramel": {"": {"cal": 39, "fat": 0.8, "carbs": 8, "protein": 0.5, "sodium": 25, "fiber": 0, "sugar": 6}},

    # =========================================================================
    # DAIRY
    # =========================================================================
    "milk": {"cup": {"cal": 149, "fat": 8, "carbs": 12, "protein": 8, "sodium": 105, "fiber": 0, "sugar": 12},
            "tbsp": {"cal": 9, "fat": 0.5, "carbs": 0.75, "protein": 0.5, "sodium": 7, "fiber": 0, "sugar": 0.75},
            "pint": {"cal": 298, "fat": 16, "carbs": 24, "protein": 16, "sodium": 210, "fiber": 0, "sugar": 24},
            "quart": {"cal": 596, "fat": 32, "carbs": 48, "protein": 32, "sodium": 420, "fiber": 0, "sugar": 48},
            "ml": {"cal": 0.63, "fat": 0.03, "carbs": 0.05, "protein": 0.03, "sodium": 0.44, "fiber": 0, "sugar": 0.05}},
    "skim milk": {"cup": {"cal": 83, "fat": 0.2, "carbs": 12, "protein": 8, "sodium": 103, "fiber": 0, "sugar": 12}},
    "evaporated milk": {"cup": {"cal": 338, "fat": 19, "carbs": 25, "protein": 17, "sodium": 267, "fiber": 0, "sugar": 25}},
    "sweetened condensed milk": {"cup": {"cal": 982, "fat": 27, "carbs": 166, "protein": 24, "sodium": 389, "fiber": 0, "sugar": 166}},
    "buttermilk": {"cup": {"cal": 99, "fat": 2.2, "carbs": 12, "protein": 8, "sodium": 257, "fiber": 0, "sugar": 12}},
    "heavy cream": {"cup": {"cal": 821, "fat": 88, "carbs": 7, "protein": 5, "sodium": 89, "fiber": 0, "sugar": 7},
                   "tbsp": {"cal": 51, "fat": 5.5, "carbs": 0.4, "protein": 0.3, "sodium": 6, "fiber": 0, "sugar": 0.4}},
    "half and half": {"cup": {"cal": 315, "fat": 28, "carbs": 10, "protein": 7, "sodium": 98, "fiber": 0, "sugar": 10},
                     "tbsp": {"cal": 20, "fat": 1.7, "carbs": 0.6, "protein": 0.4, "sodium": 6, "fiber": 0, "sugar": 0.6}},
    "sour cream": {"cup": {"cal": 444, "fat": 45, "carbs": 8, "protein": 5, "sodium": 108, "fiber": 0, "sugar": 5},
                  "tbsp": {"cal": 28, "fat": 2.8, "carbs": 0.5, "protein": 0.3, "sodium": 7, "fiber": 0, "sugar": 0.3},
                  "carton": {"cal": 444, "fat": 45, "carbs": 8, "protein": 5, "sodium": 108, "fiber": 0, "sugar": 5},
                  "": {"cal": 28, "fat": 2.8, "carbs": 0.5, "protein": 0.3, "sodium": 7, "fiber": 0, "sugar": 0.3}},
    "cream cheese": {"cup": {"cal": 793, "fat": 79, "carbs": 8, "protein": 14, "sodium": 691, "fiber": 0, "sugar": 6},
                    "oz": {"cal": 99, "fat": 10, "carbs": 1, "protein": 2, "sodium": 86, "fiber": 0, "sugar": 0.8},
                    "tbsp": {"cal": 50, "fat": 5, "carbs": 0.5, "protein": 1, "sodium": 43, "fiber": 0, "sugar": 0.4},
                    "package": {"cal": 792, "fat": 80, "carbs": 8, "protein": 16, "sodium": 688, "fiber": 0, "sugar": 6.4}},
    "yogurt": {"cup": {"cal": 149, "fat": 8, "carbs": 11, "protein": 9, "sodium": 113, "fiber": 0, "sugar": 11}},
    "greek yogurt": {"cup": {"cal": 190, "fat": 10, "carbs": 8, "protein": 18, "sodium": 65, "fiber": 0, "sugar": 7}},
    "cottage cheese": {"cup": {"cal": 220, "fat": 10, "carbs": 8, "protein": 25, "sodium": 819, "fiber": 0, "sugar": 5}},
    "ricotta cheese": {"cup": {"cal": 428, "fat": 32, "carbs": 7, "protein": 28, "sodium": 307, "fiber": 0, "sugar": 0.5}},
    "cheddar cheese": {"cup": {"cal": 455, "fat": 37, "carbs": 1, "protein": 28, "sodium": 702, "fiber": 0, "sugar": 0.5},
                      "oz": {"cal": 113, "fat": 9, "carbs": 0.3, "protein": 7, "sodium": 175, "fiber": 0, "sugar": 0.1},
                      "g": {"cal": 4.0, "fat": 0.33, "carbs": 0.01, "protein": 0.25, "sodium": 6.2, "fiber": 0, "sugar": 0}},
    "parmesan cheese": {"cup": {"cal": 431, "fat": 29, "carbs": 4, "protein": 38, "sodium": 1529, "fiber": 0, "sugar": 1},
                       "tbsp": {"cal": 22, "fat": 1.4, "carbs": 0.2, "protein": 2, "sodium": 76, "fiber": 0, "sugar": 0},
                       "g": {"cal": 3.9, "fat": 0.26, "carbs": 0.03, "protein": 0.34, "sodium": 13.9, "fiber": 0, "sugar": 0}},
    "mozzarella cheese": {"cup": {"cal": 336, "fat": 25, "carbs": 2, "protein": 25, "sodium": 627, "fiber": 0, "sugar": 1},
                         "oz": {"cal": 84, "fat": 6, "carbs": 0.6, "protein": 6, "sodium": 157, "fiber": 0, "sugar": 0.2}},
    "swiss cheese": {"cup": {"cal": 420, "fat": 31, "carbs": 6, "protein": 30, "sodium": 228, "fiber": 0, "sugar": 2},
                    "oz": {"cal": 106, "fat": 8, "carbs": 1.5, "protein": 8, "sodium": 54, "fiber": 0, "sugar": 0.4},
                    "slice": {"cal": 106, "fat": 8, "carbs": 1.5, "protein": 8, "sodium": 54, "fiber": 0, "sugar": 0.4},
                    "": {"cal": 106, "fat": 8, "carbs": 1.5, "protein": 8, "sodium": 54, "fiber": 0, "sugar": 0.4}},
    "american cheese": {"slice": {"cal": 94, "fat": 7, "carbs": 2, "protein": 5, "sodium": 274, "fiber": 0, "sugar": 1}},
    "provolone cheese": {"slice": {"cal": 98, "fat": 7, "carbs": 0.6, "protein": 7, "sodium": 248, "fiber": 0, "sugar": 0.2},
                        "oz": {"cal": 98, "fat": 7, "carbs": 0.6, "protein": 7, "sodium": 248, "fiber": 0, "sugar": 0.2}},
    "velveeta": {"oz": {"cal": 80, "fat": 6, "carbs": 3, "protein": 4, "sodium": 410, "fiber": 0, "sugar": 2}},
    "whipped cream": {"cup": {"cal": 240, "fat": 22, "carbs": 7, "protein": 3, "sodium": 60, "fiber": 0, "sugar": 7},
                     "tbsp": {"cal": 15, "fat": 1.4, "carbs": 0.4, "protein": 0.2, "sodium": 4, "fiber": 0, "sugar": 0.4}},

    # =========================================================================
    # FATS & OILS
    # =========================================================================
    "butter": {"cup": {"cal": 1628, "fat": 184, "carbs": 0, "protein": 2, "sodium": 1246, "fiber": 0, "sugar": 0},
              "tbsp": {"cal": 102, "fat": 11.5, "carbs": 0, "protein": 0.1, "sodium": 78, "fiber": 0, "sugar": 0},
              "tsp": {"cal": 34, "fat": 4, "carbs": 0, "protein": 0, "sodium": 26, "fiber": 0, "sugar": 0},
              "": {"cal": 102, "fat": 11.5, "carbs": 0, "protein": 0.1, "sodium": 78, "fiber": 0, "sugar": 0}},
    "margarine": {"tbsp": {"cal": 100, "fat": 11, "carbs": 0, "protein": 0, "sodium": 90, "fiber": 0, "sugar": 0},
                  "stick": {"cal": 810, "fat": 91, "carbs": 1, "protein": 1, "sodium": 800, "fiber": 0, "sugar": 0},
                  "": {"cal": 100, "fat": 11, "carbs": 0, "protein": 0, "sodium": 90, "fiber": 0, "sugar": 0}},
    "oleo": {"tbsp": {"cal": 100, "fat": 11, "carbs": 0, "protein": 0, "sodium": 90, "fiber": 0, "sugar": 0},
             "stick": {"cal": 810, "fat": 91, "carbs": 1, "protein": 1, "sodium": 800, "fiber": 0, "sugar": 0},
             "": {"cal": 100, "fat": 11, "carbs": 0, "protein": 0, "sodium": 90, "fiber": 0, "sugar": 0}},
    "vegetable oil": {"cup": {"cal": 1927, "fat": 218, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                     "tbsp": {"cal": 120, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                     "": {"cal": 120, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "olive oil": {"cup": {"cal": 1909, "fat": 216, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                 "tbsp": {"cal": 119, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                 "": {"cal": 119, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "coconut oil": {"tbsp": {"cal": 117, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "shortening": {"cup": {"cal": 1812, "fat": 205, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                  "tbsp": {"cal": 113, "fat": 13, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "lard": {"cup": {"cal": 1849, "fat": 205, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
            "tbsp": {"cal": 115, "fat": 13, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "mayonnaise": {"cup": {"cal": 1440, "fat": 160, "carbs": 0, "protein": 2, "sodium": 1250, "fiber": 0, "sugar": 0},
                  "tbsp": {"cal": 90, "fat": 10, "carbs": 0, "protein": 0.1, "sodium": 78, "fiber": 0, "sugar": 0}},
    "bacon grease": {"tbsp": {"cal": 116, "fat": 13, "carbs": 0, "protein": 0, "sodium": 19, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # EGGS
    # =========================================================================
    "egg": {"": {"cal": 72, "fat": 5, "carbs": 0.4, "protein": 6, "sodium": 71, "fiber": 0, "sugar": 0.4}},
    "large egg": {"": {"cal": 72, "fat": 5, "carbs": 0.4, "protein": 6, "sodium": 71, "fiber": 0, "sugar": 0.4}},
    "eggs": {"": {"cal": 72, "fat": 5, "carbs": 0.4, "protein": 6, "sodium": 71, "fiber": 0, "sugar": 0.4}},
    "egg white": {"": {"cal": 17, "fat": 0, "carbs": 0.2, "protein": 4, "sodium": 55, "fiber": 0, "sugar": 0.2}},
    "egg yolk": {"": {"cal": 55, "fat": 5, "carbs": 0.6, "protein": 3, "sodium": 8, "fiber": 0, "sugar": 0.1}},

    # =========================================================================
    # MEATS - POULTRY
    # =========================================================================
    "chicken breast": {"lb": {"cal": 748, "fat": 16, "carbs": 0, "protein": 140, "sodium": 340, "fiber": 0, "sugar": 0},
                      "": {"cal": 187, "fat": 4, "carbs": 0, "protein": 35, "sodium": 85, "fiber": 0, "sugar": 0}},
    "chicken thigh": {"lb": {"cal": 980, "fat": 54, "carbs": 0, "protein": 115, "sodium": 422, "fiber": 0, "sugar": 0},
                     "": {"cal": 206, "fat": 11, "carbs": 0, "protein": 24, "sodium": 88, "fiber": 0, "sugar": 0}},
    "chicken": {"lb": {"cal": 880, "fat": 40, "carbs": 0, "protein": 120, "sodium": 380, "fiber": 0, "sugar": 0},
               "cup": {"cal": 231, "fat": 10, "carbs": 0, "protein": 32, "sodium": 100, "fiber": 0, "sugar": 0},
               "": {"cal": 231, "fat": 10, "carbs": 0, "protein": 32, "sodium": 100, "fiber": 0, "sugar": 0}},
    "ground chicken": {"lb": {"cal": 748, "fat": 36, "carbs": 0, "protein": 100, "sodium": 340, "fiber": 0, "sugar": 0}},
    "turkey": {"lb": {"cal": 720, "fat": 32, "carbs": 0, "protein": 104, "sodium": 300, "fiber": 0, "sugar": 0},
              "cup": {"cal": 190, "fat": 8, "carbs": 0, "protein": 27, "sodium": 79, "fiber": 0, "sugar": 0}},
    "ground turkey": {"lb": {"cal": 752, "fat": 36, "carbs": 0, "protein": 100, "sodium": 340, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # MEATS - BEEF
    # =========================================================================
    "ground beef": {"lb": {"cal": 1152, "fat": 88, "carbs": 0, "protein": 80, "sodium": 304, "fiber": 0, "sugar": 0}},
    "lean ground beef": {"lb": {"cal": 816, "fat": 48, "carbs": 0, "protein": 92, "sodium": 320, "fiber": 0, "sugar": 0}},
    "beef": {"lb": {"cal": 1000, "fat": 68, "carbs": 0, "protein": 92, "sodium": 280, "fiber": 0, "sugar": 0},
            "cup": {"cal": 263, "fat": 18, "carbs": 0, "protein": 24, "sodium": 74, "fiber": 0, "sugar": 0}},
    "steak": {"lb": {"cal": 880, "fat": 52, "carbs": 0, "protein": 100, "sodium": 260, "fiber": 0, "sugar": 0},
             "oz": {"cal": 55, "fat": 3.3, "carbs": 0, "protein": 6, "sodium": 16, "fiber": 0, "sugar": 0}},
    "roast beef": {"lb": {"cal": 800, "fat": 40, "carbs": 0, "protein": 108, "sodium": 272, "fiber": 0, "sugar": 0}},
    "beef stew meat": {"lb": {"cal": 720, "fat": 32, "carbs": 0, "protein": 108, "sodium": 280, "fiber": 0, "sugar": 0}},
    "corned beef": {"lb": {"cal": 880, "fat": 56, "carbs": 2, "protein": 88, "sodium": 3840, "fiber": 0, "sugar": 0}},
    "beef jerky": {"oz": {"cal": 116, "fat": 7, "carbs": 3, "protein": 9, "sodium": 590, "fiber": 0.4, "sugar": 3},
                  "lb": {"cal": 1856, "fat": 112, "carbs": 48, "protein": 144, "sodium": 9440, "fiber": 6.4, "sugar": 48},
                  "cup": {"cal": 232, "fat": 14, "carbs": 6, "protein": 18, "sodium": 1180, "fiber": 0.8, "sugar": 6},
                  "": {"cal": 116, "fat": 7, "carbs": 3, "protein": 9, "sodium": 590, "fiber": 0.4, "sugar": 3}},
    "dried beef": {"oz": {"cal": 116, "fat": 7, "carbs": 3, "protein": 9, "sodium": 590, "fiber": 0.4, "sugar": 3},
                  "lb": {"cal": 1856, "fat": 112, "carbs": 48, "protein": 144, "sodium": 9440, "fiber": 6.4, "sugar": 48},
                  "cup": {"cal": 232, "fat": 14, "carbs": 6, "protein": 18, "sodium": 1180, "fiber": 0.8, "sugar": 6},
                  "slice": {"cal": 10, "fat": 0.6, "carbs": 0.3, "protein": 0.8, "sodium": 50, "fiber": 0, "sugar": 0.3},
                  "": {"cal": 116, "fat": 7, "carbs": 3, "protein": 9, "sodium": 590, "fiber": 0.4, "sugar": 3}},

    # =========================================================================
    # MEATS - PORK
    # =========================================================================
    "pork": {"lb": {"cal": 1016, "fat": 60, "carbs": 0, "protein": 112, "sodium": 260, "fiber": 0, "sugar": 0},
            "oz": {"cal": 64, "fat": 3.8, "carbs": 0, "protein": 7, "sodium": 16, "fiber": 0, "sugar": 0}},
    "pork chop": {"": {"cal": 231, "fat": 13, "carbs": 0, "protein": 26, "sodium": 62, "fiber": 0, "sugar": 0}},
    "pork loin": {"lb": {"cal": 680, "fat": 24, "carbs": 0, "protein": 116, "sodium": 280, "fiber": 0, "sugar": 0}},
    "pork tenderloin": {"lb": {"cal": 544, "fat": 12, "carbs": 0, "protein": 104, "sodium": 240, "fiber": 0, "sugar": 0}},
    "bacon": {"slice": {"cal": 43, "fat": 3, "carbs": 0, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0},
             "strip": {"cal": 43, "fat": 3, "carbs": 0, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0},
             "strips": {"cal": 43, "fat": 3, "carbs": 0, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0},
             "lb": {"cal": 2420, "fat": 232, "carbs": 0, "protein": 60, "sodium": 3040, "fiber": 0, "sugar": 0}},
    "ham": {"cup": {"cal": 207, "fat": 11, "carbs": 2, "protein": 24, "sodium": 1684, "fiber": 0, "sugar": 0},
           "lb": {"cal": 620, "fat": 32, "carbs": 4, "protein": 80, "sodium": 5050, "fiber": 0, "sugar": 0}},
    "sausage": {"link": {"cal": 82, "fat": 7, "carbs": 0.5, "protein": 4, "sodium": 192, "fiber": 0, "sugar": 0},
               "lb": {"cal": 1148, "fat": 100, "carbs": 4, "protein": 56, "sodium": 2840, "fiber": 0, "sugar": 0},
               "oz": {"cal": 72, "fat": 6, "carbs": 0.3, "protein": 3.5, "sodium": 178, "fiber": 0, "sugar": 0},
               "pkg": {"cal": 1148, "fat": 100, "carbs": 4, "protein": 56, "sodium": 2840, "fiber": 0, "sugar": 0},
               "": {"cal": 82, "fat": 7, "carbs": 0.5, "protein": 4, "sodium": 192, "fiber": 0, "sugar": 0}},
    "italian sausage": {"link": {"cal": 125, "fat": 10, "carbs": 1, "protein": 8, "sodium": 380, "fiber": 0, "sugar": 0}},
    "ground pork": {"lb": {"cal": 1200, "fat": 92, "carbs": 0, "protein": 80, "sodium": 280, "fiber": 0, "sugar": 0}},
    "pork ribs": {"lb": {"cal": 1156, "fat": 88, "carbs": 0, "protein": 84, "sodium": 280, "fiber": 0, "sugar": 0},
                 "oz": {"cal": 72, "fat": 5.5, "carbs": 0, "protein": 5, "sodium": 18, "fiber": 0, "sugar": 0},
                 "rack": {"cal": 2312, "fat": 176, "carbs": 0, "protein": 168, "sodium": 560, "fiber": 0, "sugar": 0},
                 "": {"cal": 72, "fat": 5.5, "carbs": 0, "protein": 5, "sodium": 18, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # SEAFOOD
    # =========================================================================
    "shrimp": {"lb": {"cal": 480, "fat": 8, "carbs": 4, "protein": 92, "sodium": 800, "fiber": 0, "sugar": 0},
              "cup": {"cal": 120, "fat": 2, "carbs": 1, "protein": 23, "sodium": 200, "fiber": 0, "sugar": 0},
              "": {"cal": 7, "fat": 0.1, "carbs": 0, "protein": 1.5, "sodium": 13, "fiber": 0, "sugar": 0}},
    "chipotle pepper": {"": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 100, "fiber": 0.3, "sugar": 0.5},
                       "tbsp": {"cal": 17, "fat": 0.5, "carbs": 3, "protein": 0.5, "sodium": 400, "fiber": 1, "sugar": 2}},
    "salmon": {"lb": {"cal": 936, "fat": 56, "carbs": 0, "protein": 104, "sodium": 260, "fiber": 0, "sugar": 0},
              "oz": {"cal": 59, "fat": 3.5, "carbs": 0, "protein": 6.5, "sodium": 16, "fiber": 0, "sugar": 0},
              "": {"cal": 59, "fat": 3.5, "carbs": 0, "protein": 6.5, "sodium": 16, "fiber": 0, "sugar": 0},
              "slice": {"cal": 30, "fat": 1.8, "carbs": 0, "protein": 3.3, "sodium": 8, "fiber": 0, "sugar": 0},
              "slices": {"cal": 30, "fat": 1.8, "carbs": 0, "protein": 3.3, "sodium": 8, "fiber": 0, "sugar": 0},
              "fillet": {"cal": 177, "fat": 10.5, "carbs": 0, "protein": 19.5, "sodium": 48, "fiber": 0, "sugar": 0}},
    "trout": {"lb": {"cal": 680, "fat": 28, "carbs": 0, "protein": 104, "sodium": 260, "fiber": 0, "sugar": 0},
              "oz": {"cal": 43, "fat": 1.8, "carbs": 0, "protein": 6.5, "sodium": 16, "fiber": 0, "sugar": 0},
              "fillet": {"cal": 215, "fat": 9, "carbs": 0, "protein": 33, "sodium": 81, "fiber": 0, "sugar": 0},
              "fillets": {"cal": 215, "fat": 9, "carbs": 0, "protein": 33, "sodium": 81, "fiber": 0, "sugar": 0}},
    "tuna": {"can": {"cal": 179, "fat": 1, "carbs": 0, "protein": 40, "sodium": 558, "fiber": 0, "sugar": 0},
            "cup": {"cal": 179, "fat": 1, "carbs": 0, "protein": 40, "sodium": 558, "fiber": 0, "sugar": 0}},
    "cod": {"lb": {"cal": 372, "fat": 4, "carbs": 0, "protein": 80, "sodium": 280, "fiber": 0, "sugar": 0}},
    "tilapia": {"lb": {"cal": 436, "fat": 8, "carbs": 0, "protein": 92, "sodium": 232, "fiber": 0, "sugar": 0}},
    "crab": {"cup": {"cal": 97, "fat": 2, "carbs": 0, "protein": 19, "sodium": 911, "fiber": 0, "sugar": 0}},
    "crabmeat": {"oz": {"cal": 25, "fat": 0.4, "carbs": 0, "protein": 5, "sodium": 95, "fiber": 0, "sugar": 0}},
    "clams": {"cup": {"cal": 168, "fat": 2, "carbs": 6, "protein": 29, "sodium": 127, "fiber": 0, "sugar": 0},
             "can": {"cal": 120, "fat": 1.5, "carbs": 4, "protein": 20, "sodium": 350, "fiber": 0, "sugar": 0},
             "oz": {"cal": 21, "fat": 0.3, "carbs": 0.8, "protein": 4, "sodium": 16, "fiber": 0, "sugar": 0}},
    "lobster": {"cup": {"cal": 142, "fat": 1, "carbs": 2, "protein": 30, "sodium": 705, "fiber": 0, "sugar": 0}},
    "anchovies": {"can": {"cal": 94, "fat": 4, "carbs": 0, "protein": 13, "sodium": 1651, "fiber": 0, "sugar": 0}},
    "swordfish": {"oz": {"cal": 41, "fat": 1.4, "carbs": 0, "protein": 6.7, "sodium": 30, "fiber": 0, "sugar": 0}},
    "red snapper": {"oz": {"cal": 28, "fat": 0.4, "carbs": 0, "protein": 5.8, "sodium": 18, "fiber": 0, "sugar": 0}},
    "cornish hen": {"": {"cal": 500, "fat": 28, "carbs": 0, "protein": 60, "sodium": 200, "fiber": 0, "sugar": 0}},
    "corned beef": {"oz": {"cal": 71, "fat": 5.4, "carbs": 0.4, "protein": 5, "sodium": 285, "fiber": 0, "sugar": 0}},
    "sirloin": {"lb": {"cal": 880, "fat": 48, "carbs": 0, "protein": 104, "sodium": 280, "fiber": 0, "sugar": 0}},
    "round steak": {"lb": {"cal": 720, "fat": 24, "carbs": 0, "protein": 120, "sodium": 240, "fiber": 0, "sugar": 0}},
    "pot roast": {"lb": {"cal": 880, "fat": 52, "carbs": 0, "protein": 100, "sodium": 280, "fiber": 0, "sugar": 0}},
    "stew meat": {"lb": {"cal": 880, "fat": 52, "carbs": 0, "protein": 100, "sodium": 280, "fiber": 0, "sugar": 0}},
    "salami": {"oz": {"cal": 119, "fat": 10, "carbs": 0.5, "protein": 6, "sodium": 529, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # CANNED GOODS & PREPARED FOODS
    # =========================================================================
    "cream of chicken soup": {"can": {"cal": 225, "fat": 14, "carbs": 18, "protein": 6, "sodium": 1800, "fiber": 0, "sugar": 2}},
    "cream of mushroom soup": {"can": {"cal": 200, "fat": 13, "carbs": 15, "protein": 4, "sodium": 1700, "fiber": 1, "sugar": 2}},
    "cream of celery soup": {"can": {"cal": 180, "fat": 11, "carbs": 17, "protein": 3, "sodium": 1650, "fiber": 1, "sugar": 2}},
    "tomato soup": {"can": {"cal": 161, "fat": 4, "carbs": 28, "protein": 4, "sodium": 1410, "fiber": 3, "sugar": 19}},
    "chicken broth": {"cup": {"cal": 15, "fat": 0.5, "carbs": 1, "protein": 2, "sodium": 860, "fiber": 0, "sugar": 0},
                     "can": {"cal": 30, "fat": 1, "carbs": 2, "protein": 4, "sodium": 1720, "fiber": 0, "sugar": 0}},
    "beef broth": {"cup": {"cal": 17, "fat": 0.5, "carbs": 1, "protein": 3, "sodium": 890, "fiber": 0, "sugar": 0},
                  "can": {"cal": 34, "fat": 1, "carbs": 2, "protein": 6, "sodium": 1780, "fiber": 0, "sugar": 0}},
    "vegetable broth": {"cup": {"cal": 12, "fat": 0, "carbs": 3, "protein": 0, "sodium": 700, "fiber": 0, "sugar": 1}},
    "vegetable juice": {"cup": {"cal": 46, "fat": 0, "carbs": 10, "protein": 2, "sodium": 650, "fiber": 2, "sugar": 6},
                       "can": {"cal": 92, "fat": 0, "carbs": 20, "protein": 4, "sodium": 1300, "fiber": 4, "sugar": 12}},
    "chili seasoning": {"packet": {"cal": 25, "fat": 0.5, "carbs": 5, "protein": 1, "sodium": 1200, "fiber": 1, "sugar": 1},
                       "tbsp": {"cal": 10, "fat": 0.2, "carbs": 2, "protein": 0.4, "sodium": 480, "fiber": 0.4, "sugar": 0.4},
                       "": {"cal": 25, "fat": 0.5, "carbs": 5, "protein": 1, "sodium": 1200, "fiber": 1, "sugar": 1}},
    "beef bouillon": {"cube": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0},
                     "": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0}},
    "chicken bouillon": {"cube": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0},
                        "": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0}},
    "bouillon cube": {"": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0}},
    "chicken bouillon cube": {"": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0}},
    "beef bouillon cube": {"": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0}},
    "bouillon": {"cube": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0},
                 "tbsp": {"cal": 15, "fat": 0, "carbs": 3, "protein": 1.5, "sodium": 2700, "fiber": 0, "sugar": 0},
                 "tsp": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0}},
    "tomato paste": {"can": {"cal": 139, "fat": 1, "carbs": 32, "protein": 7, "sodium": 170, "fiber": 7, "sugar": 21},
                    "tbsp": {"cal": 13, "fat": 0.1, "carbs": 3, "protein": 0.7, "sodium": 16, "fiber": 0.7, "sugar": 2}},
    "tomato sauce": {"cup": {"cal": 59, "fat": 0.4, "carbs": 13, "protein": 3, "sodium": 1116, "fiber": 4, "sugar": 8},
                    "can": {"cal": 89, "fat": 0.6, "carbs": 20, "protein": 4, "sodium": 1674, "fiber": 6, "sugar": 12}},
    "marinara sauce": {"cup": {"cal": 128, "fat": 4, "carbs": 20, "protein": 3, "sodium": 940, "fiber": 4, "sugar": 11},
                      "can": {"cal": 192, "fat": 6, "carbs": 30, "protein": 4.5, "sodium": 1410, "fiber": 6, "sugar": 16}},
    "spaghetti sauce": {"cup": {"cal": 128, "fat": 4, "carbs": 20, "protein": 3, "sodium": 940, "fiber": 4, "sugar": 11},
                       "can": {"cal": 192, "fat": 6, "carbs": 30, "protein": 4.5, "sodium": 1410, "fiber": 6, "sugar": 16}},
    "soup": {"can": {"cal": 225, "fat": 8, "carbs": 20, "protein": 8, "sodium": 1780, "fiber": 1, "sugar": 4},
             "cup": {"cal": 112, "fat": 4, "carbs": 10, "protein": 4, "sodium": 890, "fiber": 0.5, "sugar": 2},
             "": {"cal": 112, "fat": 4, "carbs": 10, "protein": 4, "sodium": 890, "fiber": 0.5, "sugar": 2}},
    "stewed tomatoes": {"can": {"cal": 66, "fat": 0.4, "carbs": 16, "protein": 3, "sodium": 564, "fiber": 4, "sugar": 9}},
    "diced tomatoes": {"can": {"cal": 66, "fat": 0.4, "carbs": 16, "protein": 3, "sodium": 564, "fiber": 4, "sugar": 9}},
    "crushed tomatoes": {"can": {"cal": 70, "fat": 0.5, "carbs": 16, "protein": 3, "sodium": 600, "fiber": 4, "sugar": 10}},
    "canned tomatoes": {"can": {"cal": 66, "fat": 0.4, "carbs": 16, "protein": 3, "sodium": 564, "fiber": 4, "sugar": 9}},
    "salsa": {"cup": {"cal": 70, "fat": 0.3, "carbs": 15, "protein": 3, "sodium": 1990, "fiber": 4, "sugar": 8},
             "can": {"cal": 140, "fat": 0.6, "carbs": 30, "protein": 6, "sodium": 3980, "fiber": 8, "sugar": 16},
             "jar": {"cal": 140, "fat": 0.6, "carbs": 30, "protein": 6, "sodium": 3980, "fiber": 8, "sugar": 16},
             "oz": {"cal": 9, "fat": 0, "carbs": 2, "protein": 0.4, "sodium": 249, "fiber": 0.5, "sugar": 1},
             "": {"cal": 70, "fat": 0.3, "carbs": 15, "protein": 3, "sodium": 1990, "fiber": 4, "sugar": 8}},
    "enchilada sauce": {"cup": {"cal": 60, "fat": 1, "carbs": 11, "protein": 2, "sodium": 1160, "fiber": 2, "sugar": 4}},
    "black beans": {"can": {"cal": 339, "fat": 1, "carbs": 61, "protein": 22, "sodium": 660, "fiber": 15, "sugar": 1},
                   "cup": {"cal": 227, "fat": 0.9, "carbs": 41, "protein": 15, "sodium": 440, "fiber": 10, "sugar": 0.5}},
    "kidney beans": {"can": {"cal": 330, "fat": 1, "carbs": 58, "protein": 23, "sodium": 880, "fiber": 16, "sugar": 3},
                    "cup": {"cal": 225, "fat": 1, "carbs": 40, "protein": 15, "sodium": 607, "fiber": 11, "sugar": 2},
                    "": {"cal": 225, "fat": 1, "carbs": 40, "protein": 15, "sodium": 607, "fiber": 11, "sugar": 2}},
    "pinto beans": {"can": {"cal": 320, "fat": 1, "carbs": 56, "protein": 20, "sodium": 620, "fiber": 15, "sugar": 1},
                   "cup": {"cal": 245, "fat": 1, "carbs": 45, "protein": 15, "sodium": 2, "fiber": 15, "sugar": 0.6},
                   "": {"cal": 245, "fat": 1, "carbs": 45, "protein": 15, "sodium": 2, "fiber": 15, "sugar": 0.6}},
    "refried beans": {"cup": {"cal": 237, "fat": 3, "carbs": 39, "protein": 14, "sodium": 1069, "fiber": 11, "sugar": 1}},
    "baked beans": {"cup": {"cal": 266, "fat": 1, "carbs": 52, "protein": 12, "sodium": 928, "fiber": 10, "sugar": 22}},
    "green beans": {"can": {"cal": 44, "fat": 0.3, "carbs": 10, "protein": 2, "sodium": 620, "fiber": 4, "sugar": 2},
                   "cup": {"cal": 31, "fat": 0.2, "carbs": 7, "protein": 2, "sodium": 6, "fiber": 3, "sugar": 3},
                   "quart": {"cal": 124, "fat": 0.8, "carbs": 28, "protein": 8, "sodium": 24, "fiber": 12, "sugar": 12},
                   "lb": {"cal": 141, "fat": 0.9, "carbs": 32, "protein": 9, "sodium": 27, "fiber": 13, "sugar": 14},
                   "oz": {"cal": 9, "fat": 0.1, "carbs": 2, "protein": 0.6, "sodium": 2, "fiber": 0.9, "sugar": 0.9},
                   "": {"cal": 31, "fat": 0.2, "carbs": 7, "protein": 2, "sodium": 6, "fiber": 3, "sugar": 3}},
    "corn": {"can": {"cal": 210, "fat": 2, "carbs": 50, "protein": 6, "sodium": 600, "fiber": 4, "sugar": 12},
            "cup": {"cal": 132, "fat": 2, "carbs": 29, "protein": 5, "sodium": 1, "fiber": 4, "sugar": 5},
            "ear": {"cal": 77, "fat": 1, "carbs": 17, "protein": 3, "sodium": 1, "fiber": 2, "sugar": 3},
            "": {"cal": 77, "fat": 1, "carbs": 17, "protein": 3, "sodium": 1, "fiber": 2, "sugar": 3}},
    "cream-style corn": {"can": {"cal": 184, "fat": 1, "carbs": 46, "protein": 4, "sodium": 730, "fiber": 3, "sugar": 11}},
    "peas": {"cup": {"cal": 117, "fat": 0.6, "carbs": 21, "protein": 8, "sodium": 7, "fiber": 7, "sugar": 8},
            "can": {"cal": 175, "fat": 0.9, "carbs": 31, "protein": 12, "sodium": 800, "fiber": 10, "sugar": 12}},
    "mushrooms": {"can": {"cal": 39, "fat": 0.5, "carbs": 8, "protein": 3, "sodium": 660, "fiber": 4, "sugar": 2},
                 "cup": {"cal": 15, "fat": 0.2, "carbs": 2, "protein": 2, "sodium": 4, "fiber": 0.7, "sugar": 1},
                 "oz": {"cal": 6, "fat": 0.1, "carbs": 0.9, "protein": 0.9, "sodium": 1, "fiber": 0.3, "sugar": 0.6},
                 "small": {"cal": 20, "fat": 0.3, "carbs": 4, "protein": 1.5, "sodium": 330, "fiber": 2, "sugar": 1},
                 "": {"cal": 15, "fat": 0.2, "carbs": 2, "protein": 2, "sodium": 4, "fiber": 0.7, "sugar": 1}},
    "olives": {"cup": {"cal": 155, "fat": 14, "carbs": 8, "protein": 1, "sodium": 1556, "fiber": 3, "sugar": 0},
               "can": {"cal": 155, "fat": 14, "carbs": 8, "protein": 1, "sodium": 1556, "fiber": 3, "sugar": 0},
               "tbsp": {"cal": 10, "fat": 1, "carbs": 0.5, "protein": 0.1, "sodium": 97, "fiber": 0.2, "sugar": 0},
               "": {"cal": 10, "fat": 1, "carbs": 0.5, "protein": 0.1, "sodium": 97, "fiber": 0.2, "sugar": 0}},
    "coconut milk": {"cup": {"cal": 445, "fat": 48, "carbs": 6, "protein": 5, "sodium": 29, "fiber": 0, "sugar": 6}},
    "pumpkin puree": {"cup": {"cal": 83, "fat": 0.7, "carbs": 20, "protein": 3, "sodium": 12, "fiber": 7, "sugar": 8}},
    "green chiles": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 400, "fiber": 2, "sugar": 3},
                    "cup": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 400, "fiber": 2, "sugar": 3}},
    "diced green chiles": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 400, "fiber": 2, "sugar": 3}},
    "chopped green chiles": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 400, "fiber": 2, "sugar": 3}},

    # =========================================================================
    # VEGETABLES
    # =========================================================================
    "onion": {"cup": {"cal": 64, "fat": 0.2, "carbs": 15, "protein": 2, "sodium": 6, "fiber": 3, "sugar": 7},
             "medium": {"cal": 44, "fat": 0.1, "carbs": 10, "protein": 1, "sodium": 4, "fiber": 2, "sugar": 5},
             "small": {"cal": 28, "fat": 0.1, "carbs": 7, "protein": 0.8, "sodium": 3, "fiber": 1, "sugar": 3},
             "large": {"cal": 60, "fat": 0.2, "carbs": 14, "protein": 1.5, "sodium": 5, "fiber": 2.5, "sugar": 6},
             "": {"cal": 44, "fat": 0.1, "carbs": 10, "protein": 1, "sodium": 4, "fiber": 2, "sugar": 5}},
    "green onion": {"cup": {"cal": 32, "fat": 0.2, "carbs": 7, "protein": 2, "sodium": 16, "fiber": 3, "sugar": 2},
                   "": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.3, "sodium": 2, "fiber": 0.4, "sugar": 0.4}},
    "garlic": {"clove": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.1, "sugar": 0},
              "cloves": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.1, "sugar": 0},
              "tbsp": {"cal": 13, "fat": 0, "carbs": 3, "protein": 0.6, "sodium": 2, "fiber": 0.2, "sugar": 0},
              "tsp": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.1, "sugar": 0},
              "": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.1, "sugar": 0}},
    "celery": {"cup": {"cal": 16, "fat": 0.2, "carbs": 3, "protein": 0.7, "sodium": 80, "fiber": 2, "sugar": 1},
              "stalk": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.3, "sodium": 32, "fiber": 0.6, "sugar": 0.5},
              "stick": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.3, "sodium": 32, "fiber": 0.6, "sugar": 0.5},
              "inch": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0.1, "sodium": 5, "fiber": 0.1, "sugar": 0.1},
              "": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.3, "sodium": 32, "fiber": 0.6, "sugar": 0.5}},
    "carrot": {"cup": {"cal": 52, "fat": 0.3, "carbs": 12, "protein": 1, "sodium": 88, "fiber": 4, "sugar": 6},
              "medium": {"cal": 25, "fat": 0.1, "carbs": 6, "protein": 0.6, "sodium": 42, "fiber": 2, "sugar": 3},
              "": {"cal": 25, "fat": 0.1, "carbs": 6, "protein": 0.6, "sodium": 42, "fiber": 2, "sugar": 3}},
    "bell pepper": {"cup": {"cal": 30, "fat": 0.3, "carbs": 6, "protein": 1, "sodium": 4, "fiber": 2, "sugar": 4},
                   "medium": {"cal": 24, "fat": 0.2, "carbs": 5, "protein": 0.8, "sodium": 3, "fiber": 1.5, "sugar": 3},
                   "": {"cal": 24, "fat": 0.2, "carbs": 5, "protein": 0.8, "sodium": 3, "fiber": 1.5, "sugar": 3}},
    "green pepper": {"cup": {"cal": 30, "fat": 0.3, "carbs": 6, "protein": 1, "sodium": 4, "fiber": 2, "sugar": 4},
                    "": {"cal": 24, "fat": 0.2, "carbs": 5, "protein": 0.8, "sodium": 3, "fiber": 1.5, "sugar": 3}},
    "red pepper": {"cup": {"cal": 39, "fat": 0.4, "carbs": 9, "protein": 1, "sodium": 5, "fiber": 3, "sugar": 6}},
    "jalapeno": {"": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0.5}},
    "green chiles": {"cup": {"cal": 30, "fat": 0.2, "carbs": 7, "protein": 1, "sodium": 552, "fiber": 1.5, "sugar": 4},
                    "can": {"cal": 15, "fat": 0.1, "carbs": 3, "protein": 0.5, "sodium": 276, "fiber": 0.8, "sugar": 2},
                    "oz": {"cal": 4, "fat": 0, "carbs": 0.9, "protein": 0.1, "sodium": 69, "fiber": 0.2, "sugar": 0.5}},
    "poblano pepper": {"": {"cal": 48, "fat": 0.4, "carbs": 9, "protein": 2, "sodium": 7, "fiber": 4, "sugar": 5}},
    "anaheim pepper": {"": {"cal": 10, "fat": 0.1, "carbs": 2, "protein": 0.4, "sodium": 2, "fiber": 0.8, "sugar": 1}},
    "chili peppers": {"tbsp": {"cal": 3, "fat": 0.1, "carbs": 0.6, "protein": 0.1, "sodium": 1, "fiber": 0.2, "sugar": 0.3},
                     "cup": {"cal": 40, "fat": 0.4, "carbs": 9, "protein": 2, "sodium": 7, "fiber": 1.5, "sugar": 5},
                     "": {"cal": 18, "fat": 0.1, "carbs": 4, "protein": 0.9, "sodium": 3, "fiber": 0.7, "sugar": 2}},
    "tomato": {"cup": {"cal": 32, "fat": 0.4, "carbs": 7, "protein": 2, "sodium": 9, "fiber": 2, "sugar": 5},
              "medium": {"cal": 22, "fat": 0.2, "carbs": 5, "protein": 1, "sodium": 6, "fiber": 1.5, "sugar": 3},
              "": {"cal": 22, "fat": 0.2, "carbs": 5, "protein": 1, "sodium": 6, "fiber": 1.5, "sugar": 3}},
    "potato": {"medium": {"cal": 163, "fat": 0.2, "carbs": 37, "protein": 4, "sodium": 13, "fiber": 4, "sugar": 2},
              "cup": {"cal": 116, "fat": 0.1, "carbs": 26, "protein": 3, "sodium": 9, "fiber": 3, "sugar": 1},
              "lb": {"cal": 354, "fat": 0.4, "carbs": 80, "protein": 9, "sodium": 28, "fiber": 9, "sugar": 4},
              "": {"cal": 163, "fat": 0.2, "carbs": 37, "protein": 4, "sodium": 13, "fiber": 4, "sugar": 2}},
    "sweet potato": {"cup": {"cal": 114, "fat": 0.1, "carbs": 27, "protein": 2, "sodium": 73, "fiber": 4, "sugar": 6},
                    "medium": {"cal": 103, "fat": 0.1, "carbs": 24, "protein": 2, "sodium": 41, "fiber": 4, "sugar": 7},
                    "": {"cal": 103, "fat": 0.1, "carbs": 24, "protein": 2, "sodium": 41, "fiber": 4, "sugar": 7}},
    "broccoli": {"cup": {"cal": 31, "fat": 0.3, "carbs": 6, "protein": 3, "sodium": 30, "fiber": 2, "sugar": 2},
                "inch": {"cal": 5, "fat": 0.05, "carbs": 1, "protein": 0.5, "sodium": 5, "fiber": 0.3, "sugar": 0.3},
                "packet": {"cal": 62, "fat": 0.6, "carbs": 12, "protein": 6, "sodium": 60, "fiber": 4, "sugar": 4},
                "package": {"cal": 62, "fat": 0.6, "carbs": 12, "protein": 6, "sodium": 60, "fiber": 4, "sugar": 4},
                "lb": {"cal": 154, "fat": 1.7, "carbs": 30, "protein": 13, "sodium": 150, "fiber": 12, "sugar": 7.5},
                "oz": {"cal": 10, "fat": 0.1, "carbs": 2, "protein": 0.8, "sodium": 10, "fiber": 0.8, "sugar": 0.5},
                "": {"cal": 31, "fat": 0.3, "carbs": 6, "protein": 3, "sodium": 30, "fiber": 2, "sugar": 2}},
    "cauliflower": {"cup": {"cal": 27, "fat": 0.3, "carbs": 5, "protein": 2, "sodium": 32, "fiber": 2, "sugar": 2},
                   "medium": {"cal": 146, "fat": 1.6, "carbs": 29, "protein": 11, "sodium": 176, "fiber": 12, "sugar": 11},
                   "head": {"cal": 146, "fat": 1.6, "carbs": 29, "protein": 11, "sodium": 176, "fiber": 12, "sugar": 11},
                   "lb": {"cal": 113, "fat": 1.2, "carbs": 22, "protein": 9, "sodium": 136, "fiber": 9, "sugar": 9},
                   "": {"cal": 27, "fat": 0.3, "carbs": 5, "protein": 2, "sodium": 32, "fiber": 2, "sugar": 2}},
    "spinach": {"cup": {"cal": 7, "fat": 0.1, "carbs": 1, "protein": 1, "sodium": 24, "fiber": 0.7, "sugar": 0.1},
                "oz": {"cal": 7, "fat": 0.1, "carbs": 1, "protein": 0.9, "sodium": 22, "fiber": 0.6, "sugar": 0.1},
                "packet": {"cal": 65, "fat": 1, "carbs": 10, "protein": 8, "sodium": 220, "fiber": 6, "sugar": 1},
                "package": {"cal": 65, "fat": 1, "carbs": 10, "protein": 8, "sodium": 220, "fiber": 6, "sugar": 1},
                "bunch": {"cal": 78, "fat": 1.2, "carbs": 12, "protein": 10, "sodium": 268, "fiber": 8, "sugar": 1.4},
                "bag": {"cal": 65, "fat": 1, "carbs": 10, "protein": 8, "sodium": 220, "fiber": 6, "sugar": 1},
                "": {"cal": 7, "fat": 0.1, "carbs": 1, "protein": 1, "sodium": 24, "fiber": 0.7, "sugar": 0.1}},
    "lettuce": {"cup": {"cal": 5, "fat": 0.1, "carbs": 1, "protein": 0.5, "sodium": 5, "fiber": 0.5, "sugar": 0.5}},
    "cabbage": {"cup": {"cal": 22, "fat": 0.1, "carbs": 5, "protein": 1, "sodium": 16, "fiber": 2, "sugar": 3},
               "head": {"cal": 218, "fat": 1, "carbs": 52, "protein": 11, "sodium": 164, "fiber": 22, "sugar": 28},
               "medium": {"cal": 218, "fat": 1, "carbs": 52, "protein": 11, "sodium": 164, "fiber": 22, "sugar": 28}},
    "zucchini": {"cup": {"cal": 19, "fat": 0.2, "carbs": 4, "protein": 1, "sodium": 12, "fiber": 1, "sugar": 3},
                "medium": {"cal": 33, "fat": 0.4, "carbs": 6, "protein": 2, "sodium": 20, "fiber": 2, "sugar": 5}},
    "squash": {"cup": {"cal": 21, "fat": 0.2, "carbs": 5, "protein": 1, "sodium": 2, "fiber": 1, "sugar": 3},
               "medium": {"cal": 50, "fat": 0.4, "carbs": 12, "protein": 2, "sodium": 4, "fiber": 3, "sugar": 7},
               "lb": {"cal": 73, "fat": 0.6, "carbs": 17, "protein": 3, "sodium": 7, "fiber": 4, "sugar": 10},
               "oz": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.3, "sugar": 0.6},
               "": {"cal": 21, "fat": 0.2, "carbs": 5, "protein": 1, "sodium": 2, "fiber": 1, "sugar": 3}},
    "eggplant": {"cup": {"cal": 20, "fat": 0.2, "carbs": 5, "protein": 0.8, "sodium": 2, "fiber": 3, "sugar": 3}},
    "cucumber": {"cup": {"cal": 16, "fat": 0.1, "carbs": 4, "protein": 0.7, "sodium": 2, "fiber": 0.5, "sugar": 2},
                "inch": {"cal": 3, "fat": 0, "carbs": 0.8, "protein": 0.1, "sodium": 0.4, "fiber": 0.1, "sugar": 0.4},
                "medium": {"cal": 45, "fat": 0.3, "carbs": 11, "protein": 2, "sodium": 6, "fiber": 1.5, "sugar": 5},
                "": {"cal": 45, "fat": 0.3, "carbs": 11, "protein": 2, "sodium": 6, "fiber": 1.5, "sugar": 5}},
    "asparagus": {"cup": {"cal": 27, "fat": 0.2, "carbs": 5, "protein": 3, "sodium": 3, "fiber": 3, "sugar": 2},
                  "bunch": {"cal": 60, "fat": 0.4, "carbs": 11, "protein": 7, "sodium": 6, "fiber": 6, "sugar": 4},
                  "": {"cal": 4, "fat": 0, "carbs": 0.7, "protein": 0.4, "sodium": 0, "fiber": 0.4, "sugar": 0.3}},
    "brussels sprouts": {"cup": {"cal": 56, "fat": 0.4, "carbs": 12, "protein": 4, "sodium": 28, "fiber": 4, "sugar": 3}},
    "kale": {"cup": {"cal": 33, "fat": 0.5, "carbs": 6, "protein": 2, "sodium": 25, "fiber": 1, "sugar": 1},
            "bunch": {"cal": 165, "fat": 2.5, "carbs": 30, "protein": 10, "sodium": 125, "fiber": 5, "sugar": 5},
            "leaves": {"cal": 8, "fat": 0.1, "carbs": 1.5, "protein": 0.5, "sodium": 6, "fiber": 0.3, "sugar": 0.3},
            "": {"cal": 33, "fat": 0.5, "carbs": 6, "protein": 2, "sodium": 25, "fiber": 1, "sugar": 1}},
    "avocado": {"": {"cal": 234, "fat": 21, "carbs": 12, "protein": 3, "sodium": 10, "fiber": 10, "sugar": 1},
               "cup": {"cal": 234, "fat": 21, "carbs": 12, "protein": 3, "sodium": 10, "fiber": 10, "sugar": 1}},
    "artichoke": {"": {"cal": 60, "fat": 0.2, "carbs": 13, "protein": 4, "sodium": 120, "fiber": 7, "sugar": 1}},
    "leek": {"cup": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1, "sodium": 18, "fiber": 2, "sugar": 3},
             "": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1, "sodium": 18, "fiber": 2, "sugar": 3}},
    "leeks": {"cup": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1, "sodium": 18, "fiber": 2, "sugar": 3},
              "": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1, "sodium": 18, "fiber": 2, "sugar": 3}},
    "parsley": {"cup": {"cal": 22, "fat": 0.5, "carbs": 4, "protein": 2, "sodium": 34, "fiber": 2, "sugar": 0.5},
                "tbsp": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0.1, "sodium": 2, "fiber": 0.1, "sugar": 0}},
    "cilantro": {"cup": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 3, "fiber": 0.2, "sugar": 0},
                 "tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                 "bunch": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.5, "sodium": 18, "fiber": 1, "sugar": 0},
                 "sprig": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                 "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "basil": {"cup": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.2, "sodium": 0, "fiber": 0.1, "sugar": 0},
              "tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
              "tsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 0, "fiber": 0.1, "sugar": 0},
              "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "chives": {"tbsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 0, "fiber": 0.1, "sugar": 0},
               "cup": {"cal": 6, "fat": 0.1, "carbs": 0.6, "protein": 0.5, "sodium": 1, "fiber": 0.4, "sugar": 0.2},
               "": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "dill": {"tbsp": {"cal": 0, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0},
             "bunch": {"cal": 4, "fat": 0.1, "carbs": 0.7, "protein": 0.3, "sodium": 6, "fiber": 0.2, "sugar": 0},
             "cup": {"cal": 4, "fat": 0.1, "carbs": 0.7, "protein": 0.3, "sodium": 6, "fiber": 0.2, "sugar": 0},
             "": {"cal": 0, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0}},
    "mint": {"tbsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0},
             "cup": {"cal": 10, "fat": 0.1, "carbs": 1.5, "protein": 0.5, "sodium": 5, "fiber": 1, "sugar": 0},
             "": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "rosemary": {"tbsp": {"cal": 2, "fat": 0.1, "carbs": 0.4, "protein": 0, "sodium": 1, "fiber": 0.2, "sugar": 0},
                 "tsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0},
                 "cup": {"cal": 32, "fat": 1.6, "carbs": 6.4, "protein": 0.5, "sodium": 8, "fiber": 3.2, "sugar": 0},
                 "sprig": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0},
                 "": {"cal": 2, "fat": 0.1, "carbs": 0.4, "protein": 0, "sodium": 1, "fiber": 0.2, "sugar": 0}},
    "thyme": {"tbsp": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0},
              "": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "sage": {"tbsp": {"cal": 2, "fat": 0.1, "carbs": 0.4, "protein": 0.1, "sodium": 0, "fiber": 0.3, "sugar": 0},
             "": {"cal": 2, "fat": 0.1, "carbs": 0.4, "protein": 0.1, "sodium": 0, "fiber": 0.3, "sugar": 0}},

    # =========================================================================
    # FRUITS
    # =========================================================================
    "apple": {"cup": {"cal": 65, "fat": 0.2, "carbs": 17, "protein": 0.3, "sodium": 1, "fiber": 3, "sugar": 13},
             "medium": {"cal": 95, "fat": 0.3, "carbs": 25, "protein": 0.5, "sodium": 2, "fiber": 4, "sugar": 19},
             "large": {"cal": 116, "fat": 0.4, "carbs": 31, "protein": 0.6, "sodium": 2, "fiber": 5.4, "sugar": 23},
             "small": {"cal": 77, "fat": 0.2, "carbs": 20, "protein": 0.4, "sodium": 1, "fiber": 3.6, "sugar": 15},
             "each": {"cal": 95, "fat": 0.3, "carbs": 25, "protein": 0.5, "sodium": 2, "fiber": 4.4, "sugar": 19},
             "": {"cal": 95, "fat": 0.3, "carbs": 25, "protein": 0.5, "sodium": 2, "fiber": 4, "sugar": 19}},
    "banana": {"": {"cal": 105, "fat": 0.4, "carbs": 27, "protein": 1, "sodium": 1, "fiber": 3, "sugar": 14},
              "cup": {"cal": 134, "fat": 0.5, "carbs": 34, "protein": 1.6, "sodium": 2, "fiber": 4, "sugar": 18}},
    "orange": {"": {"cal": 62, "fat": 0.2, "carbs": 15, "protein": 1, "sodium": 0, "fiber": 3, "sugar": 12},
              "cup": {"cal": 85, "fat": 0.2, "carbs": 21, "protein": 2, "sodium": 0, "fiber": 4, "sugar": 17}},
    "lemon": {"": {"cal": 17, "fat": 0.2, "carbs": 5, "protein": 0.6, "sodium": 1, "fiber": 2, "sugar": 1.5}},
    "lime": {"": {"cal": 20, "fat": 0.1, "carbs": 7, "protein": 0.5, "sodium": 1, "fiber": 2, "sugar": 1}},
    "lemon juice": {"cup": {"cal": 54, "fat": 0.6, "carbs": 17, "protein": 1, "sodium": 4, "fiber": 1, "sugar": 6},
                   "tbsp": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.4}},
    "lime juice": {"cup": {"cal": 60, "fat": 0.2, "carbs": 20, "protein": 1, "sodium": 4, "fiber": 1, "sugar": 4},
                  "tbsp": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.3},
                  "": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.3}},
    "orange juice": {"cup": {"cal": 112, "fat": 0.5, "carbs": 26, "protein": 2, "sodium": 2, "fiber": 0.5, "sugar": 21}},
    "blueberries": {"cup": {"cal": 84, "fat": 0.5, "carbs": 21, "protein": 1, "sodium": 1, "fiber": 4, "sugar": 15}},
    "strawberries": {"cup": {"cal": 49, "fat": 0.5, "carbs": 12, "protein": 1, "sodium": 2, "fiber": 3, "sugar": 7},
                     "dozen": {"cal": 48, "fat": 0.5, "carbs": 11, "protein": 1, "sodium": 2, "fiber": 3, "sugar": 7},
                     "oz": {"cal": 9, "fat": 0.1, "carbs": 2.2, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 1.4},
                     "": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.3, "sugar": 0.6}},
    "raspberries": {"cup": {"cal": 64, "fat": 0.8, "carbs": 15, "protein": 1.5, "sodium": 1, "fiber": 8, "sugar": 5}},
    "blackberries": {"cup": {"cal": 62, "fat": 0.7, "carbs": 14, "protein": 2, "sodium": 1, "fiber": 8, "sugar": 7}},
    "berries": {"cup": {"cal": 65, "fat": 0.6, "carbs": 16, "protein": 1, "sodium": 1, "fiber": 6, "sugar": 9},
                "piece": {"cal": 3, "fat": 0, "carbs": 0.8, "protein": 0, "sodium": 0, "fiber": 0.3, "sugar": 0.5}},
    "mixed berries": {"cup": {"cal": 65, "fat": 0.6, "carbs": 16, "protein": 1, "sodium": 1, "fiber": 6, "sugar": 9},
                      "piece": {"cal": 3, "fat": 0, "carbs": 0.8, "protein": 0, "sodium": 0, "fiber": 0.3, "sugar": 0.5}},
    "cranberries": {"cup": {"cal": 46, "fat": 0.1, "carbs": 12, "protein": 0.4, "sodium": 2, "fiber": 5, "sugar": 4}},
    "grapes": {"cup": {"cal": 104, "fat": 0.2, "carbs": 27, "protein": 1, "sodium": 3, "fiber": 1, "sugar": 23}},
    "peach": {"cup": {"cal": 60, "fat": 0.4, "carbs": 14, "protein": 1, "sodium": 0, "fiber": 2, "sugar": 12},
             "": {"cal": 59, "fat": 0.4, "carbs": 14, "protein": 1, "sodium": 0, "fiber": 2, "sugar": 13}},
    "pear": {"": {"cal": 102, "fat": 0.2, "carbs": 27, "protein": 0.6, "sodium": 2, "fiber": 6, "sugar": 17}},
    "plum": {"": {"cal": 30, "fat": 0.2, "carbs": 8, "protein": 0.5, "sodium": 0, "fiber": 1, "sugar": 7}},
    "mango": {"cup": {"cal": 99, "fat": 0.6, "carbs": 25, "protein": 1, "sodium": 2, "fiber": 3, "sugar": 23}},
    "pineapple": {"cup": {"cal": 82, "fat": 0.2, "carbs": 22, "protein": 1, "sodium": 2, "fiber": 2, "sugar": 16},
                  "slice": {"cal": 27, "fat": 0.1, "carbs": 7, "protein": 0.3, "sodium": 1, "fiber": 0.7, "sugar": 5},
                  "ring": {"cal": 27, "fat": 0.1, "carbs": 7, "protein": 0.3, "sodium": 1, "fiber": 0.7, "sugar": 5},
                  "can": {"cal": 264, "fat": 0.5, "carbs": 68, "protein": 2, "sodium": 6, "fiber": 4, "sugar": 56},
                  "": {"cal": 27, "fat": 0.1, "carbs": 7, "protein": 0.3, "sodium": 1, "fiber": 0.7, "sugar": 5}},
    "watermelon": {"cup": {"cal": 46, "fat": 0.2, "carbs": 12, "protein": 1, "sodium": 2, "fiber": 0.6, "sugar": 9}},
    "cantaloupe": {"cup": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1, "sodium": 26, "fiber": 1, "sugar": 12}},
    "cherries": {"cup": {"cal": 97, "fat": 0.3, "carbs": 25, "protein": 2, "sodium": 0, "fiber": 3, "sugar": 20}},
    "raisins": {"cup": {"cal": 434, "fat": 0.5, "carbs": 115, "protein": 5, "sodium": 18, "fiber": 5, "sugar": 86}},
    "dates": {"cup": {"cal": 415, "fat": 0.4, "carbs": 110, "protein": 4, "sodium": 3, "fiber": 12, "sugar": 93}},
    "dried cranberries": {"cup": {"cal": 308, "fat": 1, "carbs": 82, "protein": 0.2, "sodium": 3, "fiber": 6, "sugar": 65}},
    "dried apricots": {"cup": {"cal": 313, "fat": 0.7, "carbs": 81, "protein": 4, "sodium": 13, "fiber": 9, "sugar": 69},
                      "lb": {"cal": 1063, "fat": 2.3, "carbs": 275, "protein": 14, "sodium": 45, "fiber": 31, "sugar": 235}},
    "dried apples": {"cup": {"cal": 209, "fat": 0.3, "carbs": 57, "protein": 1, "sodium": 75, "fiber": 7, "sugar": 49},
                    "lb": {"cal": 1090, "fat": 1.4, "carbs": 296, "protein": 4, "sodium": 390, "fiber": 36, "sugar": 255}},
    "applesauce": {"cup": {"cal": 167, "fat": 0.4, "carbs": 43, "protein": 0.4, "sodium": 5, "fiber": 3, "sugar": 36}},
    "mixed fruit": {"cup": {"cal": 76, "fat": 0.2, "carbs": 20, "protein": 0.5, "sodium": 5, "fiber": 1.5, "sugar": 17},
                   "can": {"cal": 152, "fat": 0.4, "carbs": 40, "protein": 1, "sodium": 10, "fiber": 3, "sugar": 34}},
    "fruit cocktail": {"cup": {"cal": 76, "fat": 0.2, "carbs": 20, "protein": 0.5, "sodium": 5, "fiber": 1.5, "sugar": 17},
                      "can": {"cal": 152, "fat": 0.4, "carbs": 40, "protein": 1, "sodium": 10, "fiber": 3, "sugar": 34}},

    # =========================================================================
    # NUTS & SEEDS
    # =========================================================================
    "almonds": {"cup": {"cal": 828, "fat": 72, "carbs": 28, "protein": 30, "sodium": 1, "fiber": 17, "sugar": 6},
               "oz": {"cal": 164, "fat": 14, "carbs": 6, "protein": 6, "sodium": 0, "fiber": 3.5, "sugar": 1}},
    "walnuts": {"cup": {"cal": 765, "fat": 76, "carbs": 16, "protein": 18, "sodium": 2, "fiber": 8, "sugar": 3}},
    "pecans": {"cup": {"cal": 753, "fat": 78, "carbs": 15, "protein": 10, "sodium": 0, "fiber": 10, "sugar": 4}},
    "peanuts": {"cup": {"cal": 828, "fat": 72, "carbs": 24, "protein": 38, "sodium": 26, "fiber": 12, "sugar": 6}},
    "peanut butter": {"cup": {"cal": 1517, "fat": 130, "carbs": 50, "protein": 64, "sodium": 1010, "fiber": 12, "sugar": 24},
                     "tbsp": {"cal": 95, "fat": 8, "carbs": 3, "protein": 4, "sodium": 63, "fiber": 0.8, "sugar": 1.5}},
    "cashews": {"cup": {"cal": 786, "fat": 64, "carbs": 44, "protein": 25, "sodium": 22, "fiber": 4, "sugar": 8}},
    "sunflower seeds": {"cup": {"cal": 818, "fat": 71, "carbs": 28, "protein": 29, "sodium": 4, "fiber": 12, "sugar": 4}},
    "pumpkin seeds": {"cup": {"cal": 677, "fat": 55, "carbs": 25, "protein": 34, "sodium": 25, "fiber": 12, "sugar": 2}},
    "sesame seeds": {"cup": {"cal": 825, "fat": 72, "carbs": 34, "protein": 25, "sodium": 16, "fiber": 17, "sugar": 0},
                    "tbsp": {"cal": 52, "fat": 4.5, "carbs": 2, "protein": 1.6, "sodium": 1, "fiber": 1, "sugar": 0}},
    "flax seeds": {"tbsp": {"cal": 37, "fat": 3, "carbs": 2, "protein": 1.3, "sodium": 2, "fiber": 2, "sugar": 0}},
    "flaxseed": {"tbsp": {"cal": 37, "fat": 3, "carbs": 2, "protein": 1.3, "sodium": 2, "fiber": 2, "sugar": 0},
                "cup": {"cal": 592, "fat": 48, "carbs": 32, "protein": 21, "sodium": 32, "fiber": 32, "sugar": 0}},
    "ground flaxseed": {"tbsp": {"cal": 37, "fat": 3, "carbs": 2, "protein": 1.3, "sodium": 2, "fiber": 2, "sugar": 0}},
    "chia seeds": {"tbsp": {"cal": 58, "fat": 4, "carbs": 5, "protein": 2, "sodium": 2, "fiber": 4, "sugar": 0}},
    "coconut": {"cup": {"cal": 283, "fat": 27, "carbs": 12, "protein": 3, "sodium": 16, "fiber": 7, "sugar": 5},
                "oz": {"cal": 100, "fat": 9.5, "carbs": 4.2, "protein": 1, "sodium": 6, "fiber": 2.5, "sugar": 1.8},
                "package": {"cal": 1400, "fat": 133, "carbs": 59, "protein": 14, "sodium": 84, "fiber": 35, "sugar": 25},
                "packet": {"cal": 283, "fat": 27, "carbs": 12, "protein": 3, "sodium": 16, "fiber": 7, "sugar": 5},
                "": {"cal": 283, "fat": 27, "carbs": 12, "protein": 3, "sodium": 16, "fiber": 7, "sugar": 5}},

    # =========================================================================
    # GRAINS & PASTA
    # =========================================================================
    "rice": {"cup": {"cal": 206, "fat": 0.4, "carbs": 45, "protein": 4, "sodium": 2, "fiber": 0.6, "sugar": 0}},
    "brown rice": {"cup": {"cal": 216, "fat": 1.8, "carbs": 45, "protein": 5, "sodium": 10, "fiber": 4, "sugar": 0}},
    "pasta": {"cup": {"cal": 220, "fat": 1.3, "carbs": 43, "protein": 8, "sodium": 1, "fiber": 3, "sugar": 0.8},
             "lb": {"cal": 756, "fat": 4.5, "carbs": 148, "protein": 27, "sodium": 3, "fiber": 10, "sugar": 3},
             "oz": {"cal": 100, "fat": 0.5, "carbs": 20, "protein": 3.5, "sodium": 0, "fiber": 1, "sugar": 0.2},
             "packet": {"cal": 756, "fat": 4.5, "carbs": 148, "protein": 27, "sodium": 3, "fiber": 10, "sugar": 3},
             "package": {"cal": 756, "fat": 4.5, "carbs": 148, "protein": 27, "sodium": 3, "fiber": 10, "sugar": 3}},
    "egg noodles": {"cup": {"cal": 221, "fat": 3.3, "carbs": 40, "protein": 7, "sodium": 8, "fiber": 2, "sugar": 0.5}},
    "oats": {"cup": {"cal": 307, "fat": 5, "carbs": 55, "protein": 11, "sodium": 5, "fiber": 8, "sugar": 1}},
    "cream of wheat": {"cup": {"cal": 130, "fat": 0.5, "carbs": 28, "protein": 4, "sodium": 140, "fiber": 1, "sugar": 0},
                       "tbsp": {"cal": 20, "fat": 0.1, "carbs": 4, "protein": 0.6, "sodium": 22, "fiber": 0.2, "sugar": 0}},
    "juice": {"cup": {"cal": 112, "fat": 0.3, "carbs": 26, "protein": 0.9, "sodium": 10, "fiber": 0.2, "sugar": 24},
              "tbsp": {"cal": 7, "fat": 0, "carbs": 1.6, "protein": 0.1, "sodium": 1, "fiber": 0, "sugar": 1.5}},
    "instant oatmeal": {"packet": {"cal": 100, "fat": 2, "carbs": 19, "protein": 4, "sodium": 75, "fiber": 3, "sugar": 1},
                        "packets": {"cal": 100, "fat": 2, "carbs": 19, "protein": 4, "sodium": 75, "fiber": 3, "sugar": 1},
                        "oz": {"cal": 100, "fat": 2, "carbs": 19, "protein": 4, "sodium": 75, "fiber": 3, "sugar": 1},
                        "1-oz": {"cal": 100, "fat": 2, "carbs": 19, "protein": 4, "sodium": 75, "fiber": 3, "sugar": 1},
                        "cup": {"cal": 150, "fat": 3, "carbs": 28, "protein": 6, "sodium": 113, "fiber": 4, "sugar": 1}},
    "quinoa": {"cup": {"cal": 222, "fat": 3.6, "carbs": 39, "protein": 8, "sodium": 13, "fiber": 5, "sugar": 2}},
    "couscous": {"cup": {"cal": 176, "fat": 0.3, "carbs": 36, "protein": 6, "sodium": 8, "fiber": 2, "sugar": 0}},
    "breadcrumbs": {"cup": {"cal": 427, "fat": 6, "carbs": 78, "protein": 14, "sodium": 791, "fiber": 5, "sugar": 6}},
    "croutons": {"cup": {"cal": 122, "fat": 2, "carbs": 22, "protein": 4, "sodium": 209, "fiber": 2, "sugar": 2}},
    "stuffing": {"cup": {"cal": 355, "fat": 17, "carbs": 43, "protein": 6, "sodium": 1100, "fiber": 3, "sugar": 4},
                "pkg": {"cal": 710, "fat": 34, "carbs": 86, "protein": 12, "sodium": 2200, "fiber": 6, "sugar": 8},
                "": {"cal": 355, "fat": 17, "carbs": 43, "protein": 6, "sodium": 1100, "fiber": 3, "sugar": 4}},
    "dumplings": {"": {"cal": 80, "fat": 3, "carbs": 10, "protein": 3, "sodium": 180, "fiber": 0.5, "sugar": 1},
                 "cup": {"cal": 320, "fat": 12, "carbs": 40, "protein": 12, "sodium": 720, "fiber": 2, "sugar": 4}},

    # =========================================================================
    # BREADS & TORTILLAS
    # =========================================================================
    "bread": {"slice": {"cal": 79, "fat": 1, "carbs": 15, "protein": 3, "sodium": 147, "fiber": 0.6, "sugar": 1.5},
             "": {"cal": 79, "fat": 1, "carbs": 15, "protein": 3, "sodium": 147, "fiber": 0.6, "sugar": 1.5},
             "loaf": {"cal": 1100, "fat": 14, "carbs": 216, "protein": 42, "sodium": 2100, "fiber": 9, "sugar": 21},
             "cup": {"cal": 122, "fat": 1.5, "carbs": 23, "protein": 4.2, "sodium": 227, "fiber": 0.9, "sugar": 2.3},
             "oz": {"cal": 75, "fat": 1, "carbs": 14, "protein": 2.6, "sodium": 140, "fiber": 0.6, "sugar": 1.4},
             "can": {"cal": 500, "fat": 6, "carbs": 98, "protein": 19, "sodium": 950, "fiber": 4, "sugar": 9},
             "packet": {"cal": 500, "fat": 6, "carbs": 98, "protein": 19, "sodium": 950, "fiber": 4, "sugar": 9},
             "package": {"cal": 500, "fat": 6, "carbs": 98, "protein": 19, "sodium": 950, "fiber": 4, "sugar": 9}},
    "white bread": {"slice": {"cal": 79, "fat": 1, "carbs": 15, "protein": 3, "sodium": 147, "fiber": 0.6, "sugar": 1.5}},
    "whole wheat bread": {"slice": {"cal": 81, "fat": 1, "carbs": 14, "protein": 4, "sodium": 146, "fiber": 2, "sugar": 1.4}},
    "tortilla": {"": {"cal": 94, "fat": 2, "carbs": 16, "protein": 2, "sodium": 191, "fiber": 1, "sugar": 0.4},
                "large": {"cal": 140, "fat": 3.5, "carbs": 24, "protein": 4, "sodium": 290, "fiber": 1.5, "sugar": 0.6}},
    "flour tortilla": {"": {"cal": 94, "fat": 2, "carbs": 16, "protein": 2, "sodium": 191, "fiber": 1, "sugar": 0.4},
                      "large": {"cal": 140, "fat": 3.5, "carbs": 24, "protein": 4, "sodium": 290, "fiber": 1.5, "sugar": 0.6}},
    "corn tortilla": {"": {"cal": 52, "fat": 0.7, "carbs": 11, "protein": 1, "sodium": 11, "fiber": 1.5, "sugar": 0.2}},
    "pita bread": {"": {"cal": 165, "fat": 0.7, "carbs": 34, "protein": 5, "sodium": 322, "fiber": 1, "sugar": 0.5}},
    "hamburger bun": {"": {"cal": 120, "fat": 2, "carbs": 21, "protein": 4, "sodium": 206, "fiber": 0.9, "sugar": 3}},
    "hot dog bun": {"": {"cal": 100, "fat": 1.5, "carbs": 18, "protein": 3, "sodium": 180, "fiber": 0.7, "sugar": 2}},
    "hoagie roll": {"": {"cal": 190, "fat": 3, "carbs": 35, "protein": 7, "sodium": 340, "fiber": 1.5, "sugar": 3}},
    "sub roll": {"": {"cal": 190, "fat": 3, "carbs": 35, "protein": 7, "sodium": 340, "fiber": 1.5, "sugar": 3}},
    "italian roll": {"": {"cal": 175, "fat": 2, "carbs": 33, "protein": 6, "sodium": 310, "fiber": 1.5, "sugar": 2}},
    "pie crust": {"": {"cal": 648, "fat": 40, "carbs": 63, "protein": 7, "sodium": 520, "fiber": 2, "sugar": 2}},
    "pastry": {"": {"cal": 648, "fat": 40, "carbs": 63, "protein": 7, "sodium": 520, "fiber": 2, "sugar": 2},
               "9-inch": {"cal": 648, "fat": 40, "carbs": 63, "protein": 7, "sodium": 520, "fiber": 2, "sugar": 2}},
    "pizza dough": {"lb": {"cal": 680, "fat": 8, "carbs": 130, "protein": 22, "sodium": 1200, "fiber": 5, "sugar": 4}},
    "biscuit": {"": {"cal": 127, "fat": 6, "carbs": 17, "protein": 2, "sodium": 368, "fiber": 0.5, "sugar": 2}},
    "biscuits": {"": {"cal": 127, "fat": 6, "carbs": 17, "protein": 2, "sodium": 368, "fiber": 0.5, "sugar": 2},
                "can": {"cal": 800, "fat": 38, "carbs": 102, "protein": 12, "sodium": 2200, "fiber": 3, "sugar": 12}},
    "refrigerated biscuits": {"can": {"cal": 800, "fat": 38, "carbs": 102, "protein": 12, "sodium": 2200, "fiber": 3, "sugar": 12}},
    "crescent rolls": {"can": {"cal": 880, "fat": 48, "carbs": 96, "protein": 12, "sodium": 1920, "fiber": 0, "sugar": 12}},
    "croissant": {"": {"cal": 231, "fat": 12, "carbs": 26, "protein": 5, "sodium": 319, "fiber": 1.5, "sugar": 5}},
    "french bread": {"slice": {"cal": 92, "fat": 1, "carbs": 18, "protein": 4, "sodium": 202, "fiber": 0.8, "sugar": 1},
                    "loaf": {"cal": 1100, "fat": 12, "carbs": 216, "protein": 48, "sodium": 2424, "fiber": 10, "sugar": 12}},
    "rye bread": {"slice": {"cal": 83, "fat": 1, "carbs": 15, "protein": 3, "sodium": 211, "fiber": 1.9, "sugar": 1}},
    "sourdough": {"slice": {"cal": 93, "fat": 0.6, "carbs": 18, "protein": 4, "sodium": 206, "fiber": 0.6, "sugar": 0.5}},
    "ciabatta": {"": {"cal": 150, "fat": 2, "carbs": 28, "protein": 6, "sodium": 310, "fiber": 1, "sugar": 1},
                "loaf": {"cal": 600, "fat": 8, "carbs": 112, "protein": 24, "sodium": 1240, "fiber": 4, "sugar": 4}},

    # =========================================================================
    # CHOCOLATE & BAKING
    # =========================================================================
    "chocolate chips": {"cup": {"cal": 805, "fat": 50, "carbs": 100, "protein": 7, "sodium": 23, "fiber": 10, "sugar": 81},
                       "pkg": {"cal": 1210, "fat": 75, "carbs": 150, "protein": 10, "sodium": 35, "fiber": 15, "sugar": 122},
                       "bag": {"cal": 1210, "fat": 75, "carbs": 150, "protein": 10, "sodium": 35, "fiber": 15, "sugar": 122},
                       "oz": {"cal": 134, "fat": 8, "carbs": 17, "protein": 1, "sodium": 4, "fiber": 2, "sugar": 13},
                       "": {"cal": 805, "fat": 50, "carbs": 100, "protein": 7, "sodium": 23, "fiber": 10, "sugar": 81}},
    "cocoa powder": {"cup": {"cal": 196, "fat": 12, "carbs": 47, "protein": 17, "sodium": 18, "fiber": 29, "sugar": 1},
                    "tbsp": {"cal": 12, "fat": 0.7, "carbs": 3, "protein": 1, "sodium": 1, "fiber": 2, "sugar": 0}},
    "malted milk": {"cup": {"cal": 480, "fat": 10, "carbs": 84, "protein": 16, "sodium": 580, "fiber": 0, "sugar": 64},
                   "tbsp": {"cal": 30, "fat": 0.6, "carbs": 5, "protein": 1, "sodium": 36, "fiber": 0, "sugar": 4}},
    "baking chocolate": {"oz": {"cal": 145, "fat": 15, "carbs": 8, "protein": 3, "sodium": 4, "fiber": 4, "sugar": 0}},
    "white chocolate": {"cup": {"cal": 916, "fat": 55, "carbs": 101, "protein": 10, "sodium": 153, "fiber": 0, "sugar": 101}},
    "nutella": {"tbsp": {"cal": 100, "fat": 6, "carbs": 11, "protein": 1, "sodium": 15, "fiber": 0.5, "sugar": 10}},
    "candy": {"cup": {"cal": 360, "fat": 0, "carbs": 90, "protein": 0, "sodium": 40, "fiber": 0, "sugar": 80},
             "oz": {"cal": 95, "fat": 0, "carbs": 24, "protein": 0, "sodium": 10, "fiber": 0, "sugar": 21}},
    "gumdrops": {"cup": {"cal": 360, "fat": 0, "carbs": 90, "protein": 0, "sodium": 40, "fiber": 0, "sugar": 80}},
    "gelatin": {"tbsp": {"cal": 23, "fat": 0, "carbs": 0, "protein": 6, "sodium": 14, "fiber": 0, "sugar": 0},
               "packet": {"cal": 23, "fat": 0, "carbs": 0, "protein": 6, "sodium": 14, "fiber": 0, "sugar": 0},
               "envelope": {"cal": 23, "fat": 0, "carbs": 0, "protein": 6, "sodium": 14, "fiber": 0, "sugar": 0}},
    "vanilla extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.5}},
    "almond extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # LEAVENING & BAKING STAPLES
    # =========================================================================
    "baking powder": {"tsp": {"cal": 2, "fat": 0, "carbs": 0.7, "protein": 0, "sodium": 133, "fiber": 0, "sugar": 0},
                     "tbsp": {"cal": 5, "fat": 0, "carbs": 2, "protein": 0, "sodium": 400, "fiber": 0, "sugar": 0}},
    "baking soda": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 1260, "fiber": 0, "sugar": 0}},
    "yeast": {"packet": {"cal": 21, "fat": 0.3, "carbs": 3, "protein": 3, "sodium": 4, "fiber": 2, "sugar": 0},
             "sachet": {"cal": 21, "fat": 0.3, "carbs": 3, "protein": 3, "sodium": 4, "fiber": 2, "sugar": 0},
             "tbsp": {"cal": 23, "fat": 0.4, "carbs": 3, "protein": 3, "sodium": 4, "fiber": 2, "sugar": 0},
             "tsp": {"cal": 8, "fat": 0.1, "carbs": 1, "protein": 1, "sodium": 1, "fiber": 0.6, "sugar": 0}},
    "cream of tartar": {"tsp": {"cal": 8, "fat": 0, "carbs": 2, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 0}},
    "marshmallow": {"cup": {"cal": 159, "fat": 0.2, "carbs": 41, "protein": 1, "sodium": 23, "fiber": 0, "sugar": 29},
                   "jar": {"cal": 635, "fat": 0.8, "carbs": 164, "protein": 4, "sodium": 92, "fiber": 0, "sugar": 116},
                   "": {"cal": 25, "fat": 0, "carbs": 6, "protein": 0.2, "sodium": 4, "fiber": 0, "sugar": 5}},
    "marshmallow cream": {"cup": {"cal": 635, "fat": 0.8, "carbs": 164, "protein": 4, "sodium": 92, "fiber": 0, "sugar": 116},
                         "jar": {"cal": 635, "fat": 0.8, "carbs": 164, "protein": 4, "sodium": 92, "fiber": 0, "sugar": 116},
                         "": {"cal": 40, "fat": 0.1, "carbs": 10, "protein": 0.2, "sodium": 6, "fiber": 0, "sugar": 7}},

    # =========================================================================
    # SPICES & SEASONINGS
    # =========================================================================
    "salt": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 2325, "fiber": 0, "sugar": 0},
            "tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 6975, "fiber": 0, "sugar": 0},
            "pinch": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 150, "fiber": 0, "sugar": 0},
            "to taste": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 300, "fiber": 0, "sugar": 0},
            "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 300, "fiber": 0, "sugar": 0}},
    "pepper": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.5, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0},
              "to taste": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0},
              "": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "black pepper": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.5, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "garlic powder": {"tsp": {"cal": 10, "fat": 0, "carbs": 2, "protein": 0.5, "sodium": 2, "fiber": 0.3, "sugar": 0}},
    "onion powder": {"tsp": {"cal": 8, "fat": 0, "carbs": 2, "protein": 0.2, "sodium": 2, "fiber": 0.2, "sugar": 0.4}},
    "cumin": {"tsp": {"cal": 8, "fat": 0.5, "carbs": 1, "protein": 0.4, "sodium": 4, "fiber": 0.2, "sugar": 0},
             "tbsp": {"cal": 22, "fat": 1.3, "carbs": 3, "protein": 1, "sodium": 10, "fiber": 0.6, "sugar": 0.1}},
    "paprika": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1.2, "protein": 0.3, "sodium": 2, "fiber": 0.8, "sugar": 0.5},
               "": {"cal": 6, "fat": 0.3, "carbs": 1.2, "protein": 0.3, "sodium": 2, "fiber": 0.8, "sugar": 0.5}},
    "chili powder": {"tsp": {"cal": 8, "fat": 0.4, "carbs": 1.4, "protein": 0.3, "sodium": 26, "fiber": 0.9, "sugar": 0.3},
                    "tbsp": {"cal": 24, "fat": 1.3, "carbs": 4, "protein": 1, "sodium": 77, "fiber": 2.7, "sugar": 0.9},
                    "packet": {"cal": 100, "fat": 2, "carbs": 18, "protein": 4, "sodium": 1100, "fiber": 4, "sugar": 3},
                    "": {"cal": 8, "fat": 0.4, "carbs": 1.4, "protein": 0.3, "sodium": 26, "fiber": 0.9, "sugar": 0.3}},
    "cayenne pepper": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.5, "sugar": 0.2}},
    "oregano": {"tsp": {"cal": 5, "fat": 0.2, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.4, "sugar": 0}},
    "thyme": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.6, "protein": 0.1, "sodium": 1, "fiber": 0.4, "sugar": 0}},
    "sage": {"tsp": {"cal": 2, "fat": 0.1, "carbs": 0.4, "protein": 0.1, "sodium": 0, "fiber": 0.3, "sugar": 0}},
    "marjoram": {"tsp": {"cal": 2, "fat": 0.1, "carbs": 0.4, "protein": 0.1, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "tarragon": {"tsp": {"cal": 2, "fat": 0, "carbs": 0.4, "protein": 0.1, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "bay leaf": {"": {"cal": 2, "fat": 0.1, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "bay leaves": {"": {"cal": 2, "fat": 0.1, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "parsley": {"tsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 2, "fiber": 0.1, "sugar": 0},
               "cup": {"cal": 22, "fat": 0.5, "carbs": 4, "protein": 2, "sodium": 34, "fiber": 2, "sugar": 0.5},
               "tbsp": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0.1, "sodium": 2, "fiber": 0.1, "sugar": 0},
               "bunch": {"cal": 22, "fat": 0.5, "carbs": 4, "protein": 2, "sodium": 34, "fiber": 2, "sugar": 0.5},
               "branches": {"cal": 5, "fat": 0.1, "carbs": 1, "protein": 0.5, "sodium": 8, "fiber": 0.5, "sugar": 0.1},
               "": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 2, "fiber": 0.1, "sugar": 0}},
    "dill": {"tsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0},
            "tbsp": {"cal": 3, "fat": 0.1, "carbs": 0.6, "protein": 0.2, "sodium": 5, "fiber": 0.2, "sugar": 0}},
    "cinnamon": {"tsp": {"cal": 6, "fat": 0, "carbs": 2, "protein": 0, "sodium": 0, "fiber": 1, "sugar": 0},
                "pinch": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0},
                "": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "pumpkin spice": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.5, "protein": 0.1, "sodium": 1, "fiber": 0.5, "sugar": 0.1},
                     "cup": {"cal": 288, "fat": 4.8, "carbs": 72, "protein": 4.8, "sodium": 48, "fiber": 24, "sugar": 4.8}},
    "cereal": {"cup": {"cal": 110, "fat": 1, "carbs": 24, "protein": 2, "sodium": 200, "fiber": 1, "sugar": 3},
               "": {"cal": 110, "fat": 1, "carbs": 24, "protein": 2, "sodium": 200, "fiber": 1, "sugar": 3}},
    "nutmeg": {"tsp": {"cal": 12, "fat": 0.8, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.5, "sugar": 0},
              "pinch": {"cal": 1.5, "fat": 0.1, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0},
              "": {"cal": 1.5, "fat": 0.1, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "ginger": {"tsp": {"cal": 6, "fat": 0, "carbs": 1.3, "protein": 0.2, "sodium": 1, "fiber": 0.2, "sugar": 0},
              "tbsp": {"cal": 18, "fat": 0, "carbs": 4, "protein": 0.5, "sodium": 3, "fiber": 0.6, "sugar": 0.5},
              "dash": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
              "pinch": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
              "": {"cal": 6, "fat": 0, "carbs": 1.3, "protein": 0.2, "sodium": 1, "fiber": 0.2, "sugar": 0}},
    "allspice": {"tsp": {"cal": 5, "fat": 0.2, "carbs": 1.4, "protein": 0.1, "sodium": 1, "fiber": 0.4, "sugar": 0}},
    "star anise": {"": {"cal": 7, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.3, "sugar": 0},
                  "tsp": {"cal": 7, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.3, "sugar": 0}},
    "sichuan peppercorns": {"tsp": {"cal": 6, "fat": 0.2, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.3, "sugar": 0}},
    "long pepper": {"tsp": {"cal": 6, "fat": 0.2, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.3, "sugar": 0}},
    "cloves": {"tsp": {"cal": 7, "fat": 0.4, "carbs": 1.3, "protein": 0.1, "sodium": 5, "fiber": 0.7, "sugar": 0}},
    "mustard": {"tsp": {"cal": 3, "fat": 0.2, "carbs": 0.3, "protein": 0.2, "sodium": 57, "fiber": 0.1, "sugar": 0.1},
               "tbsp": {"cal": 10, "fat": 0.7, "carbs": 0.8, "protein": 0.7, "sodium": 171, "fiber": 0.4, "sugar": 0.3},
               "cup": {"cal": 160, "fat": 11.2, "carbs": 12.8, "protein": 11.2, "sodium": 2736, "fiber": 6.4, "sugar": 4.8}},
    "dry mustard": {"tsp": {"cal": 9, "fat": 0.5, "carbs": 0.5, "protein": 0.5, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "curry powder": {"tsp": {"cal": 7, "fat": 0.3, "carbs": 1.2, "protein": 0.3, "sodium": 1, "fiber": 0.7, "sugar": 0.1},
                    "tbsp": {"cal": 20, "fat": 0.9, "carbs": 3.7, "protein": 0.8, "sodium": 3, "fiber": 2, "sugar": 0.2}},
    "bay leaf": {"": {"cal": 2, "fat": 0.1, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "bay leaves": {"": {"cal": 2, "fat": 0.1, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "italian seasoning": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.6, "protein": 0.1, "sodium": 1, "fiber": 0.3, "sugar": 0}},
    "taco seasoning": {"packet": {"cal": 30, "fat": 0.5, "carbs": 6, "protein": 1, "sodium": 1400, "fiber": 1, "sugar": 1},
                      "tbsp": {"cal": 15, "fat": 0.3, "carbs": 3, "protein": 0.5, "sodium": 700, "fiber": 0.5, "sugar": 0.5}},
    "ranch seasoning": {"packet": {"cal": 45, "fat": 0, "carbs": 10, "protein": 1, "sodium": 1200, "fiber": 0, "sugar": 2}},
    "worcestershire sauce": {"tbsp": {"cal": 13, "fat": 0, "carbs": 3, "protein": 0, "sodium": 167, "fiber": 0, "sugar": 2}},
    "browning sauce": {"tsp": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0, "sodium": 100, "fiber": 0, "sugar": 0},
                      "tbsp": {"cal": 15, "fat": 0, "carbs": 3, "protein": 0, "sodium": 300, "fiber": 0, "sugar": 0}},
    "soy sauce": {"tbsp": {"cal": 9, "fat": 0, "carbs": 1, "protein": 1, "sodium": 879, "fiber": 0, "sugar": 0},
                 "cup": {"cal": 135, "fat": 0, "carbs": 15, "protein": 15, "sodium": 14000, "fiber": 0, "sugar": 1}},
    "hot sauce": {"tsp": {"cal": 1, "fat": 0, "carbs": 0, "protein": 0, "sodium": 124, "fiber": 0, "sugar": 0}},
    "bbq sauce": {"tbsp": {"cal": 29, "fat": 0.1, "carbs": 7, "protein": 0.1, "sodium": 175, "fiber": 0.2, "sugar": 5}},
    "ketchup": {"tbsp": {"cal": 19, "fat": 0, "carbs": 5, "protein": 0.2, "sodium": 154, "fiber": 0, "sugar": 4}},

    # =========================================================================
    # VINEGARS & ACIDS
    # =========================================================================
    "vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
               "cup": {"cal": 43, "fat": 0, "carbs": 0.9, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 0.4},
               "quart": {"cal": 172, "fat": 0, "carbs": 3.6, "protein": 0, "sodium": 8, "fiber": 0, "sugar": 1.6},
               "pint": {"cal": 86, "fat": 0, "carbs": 1.8, "protein": 0, "sodium": 4, "fiber": 0, "sugar": 0.8}},
    "apple cider vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0}},
    "balsamic vinegar": {"tbsp": {"cal": 14, "fat": 0, "carbs": 3, "protein": 0, "sodium": 4, "fiber": 0, "sugar": 2}},
    "red wine vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0},
                         "cup": {"cal": 45, "fat": 0, "carbs": 0, "protein": 0, "sodium": 12, "fiber": 0, "sugar": 0}},
    "white wine vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0}},
    "rice vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                    "cup": {"cal": 45, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # WINES & ALCOHOL (for cooking)
    # =========================================================================
    "white wine": {"cup": {"cal": 194, "fat": 0, "carbs": 5, "protein": 0.3, "sodium": 10, "fiber": 0, "sugar": 1.4}},
    "red wine": {"cup": {"cal": 199, "fat": 0, "carbs": 5, "protein": 0.3, "sodium": 10, "fiber": 0, "sugar": 0.9}},
    "cooking wine": {"cup": {"cal": 190, "fat": 0, "carbs": 8, "protein": 0, "sodium": 1000, "fiber": 0, "sugar": 4}},
    "beer": {"cup": {"cal": 103, "fat": 0, "carbs": 6, "protein": 1, "sodium": 14, "fiber": 0, "sugar": 0}},
    "rum": {"tbsp": {"cal": 32, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "bourbon": {"tbsp": {"cal": 32, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "vodka": {"tbsp": {"cal": 32, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "champagne": {"cup": {"cal": 168, "fat": 0, "carbs": 3, "protein": 0.5, "sodium": 10, "fiber": 0, "sugar": 1.5},
                 "oz": {"cal": 21, "fat": 0, "carbs": 0.4, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0.2}},
    "sparkling wine": {"cup": {"cal": 168, "fat": 0, "carbs": 3, "protein": 0.5, "sodium": 10, "fiber": 0, "sugar": 1.5}},
    "prosecco": {"cup": {"cal": 160, "fat": 0, "carbs": 2, "protein": 0.4, "sodium": 10, "fiber": 0, "sugar": 1}},
    "dry vermouth": {"oz": {"cal": 35, "fat": 0, "carbs": 3.5, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 1.5}},
    "sweet vermouth": {"oz": {"cal": 45, "fat": 0, "carbs": 5, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 4}},
    "vermouth": {"oz": {"cal": 40, "fat": 0, "carbs": 4, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 2}},
    "sherry": {"cup": {"cal": 258, "fat": 0, "carbs": 8, "protein": 0.5, "sodium": 20, "fiber": 0, "sugar": 2}},
    "port": {"cup": {"cal": 352, "fat": 0, "carbs": 20, "protein": 0.5, "sodium": 20, "fiber": 0, "sugar": 18}},
    "brandy": {"oz": {"cal": 65, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "cognac": {"oz": {"cal": 65, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "whiskey": {"oz": {"cal": 70, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "scotch": {"oz": {"cal": 70, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "tequila": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "triple sec": {"oz": {"cal": 103, "fat": 0, "carbs": 11, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 11}},
    "kahlua": {"oz": {"cal": 91, "fat": 0.1, "carbs": 14, "protein": 0, "sodium": 3, "fiber": 0, "sugar": 14}},
    "amaretto": {"oz": {"cal": 110, "fat": 0, "carbs": 17, "protein": 0, "sodium": 3, "fiber": 0, "sugar": 17}},
    "grand marnier": {"oz": {"cal": 76, "fat": 0, "carbs": 7, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 7}},
    "simple syrup": {"oz": {"cal": 52, "fat": 0, "carbs": 13, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 13}},

    # =========================================================================
    # MISCELLANEOUS
    # =========================================================================
    "coffee": {"cup": {"cal": 2, "fat": 0, "carbs": 0, "protein": 0.3, "sodium": 5, "fiber": 0, "sugar": 0}},
    "tea": {"cup": {"cal": 2, "fat": 0, "carbs": 1, "protein": 0, "sodium": 7, "fiber": 0, "sugar": 0}},
    "cocoa": {"cup": {"cal": 196, "fat": 12, "carbs": 47, "protein": 17, "sodium": 18, "fiber": 29, "sugar": 1}},
    "jam": {"tbsp": {"cal": 56, "fat": 0, "carbs": 14, "protein": 0, "sodium": 6, "fiber": 0.2, "sugar": 10}},
    "jelly": {"tbsp": {"cal": 56, "fat": 0, "carbs": 14, "protein": 0, "sodium": 6, "fiber": 0, "sugar": 10}},
    "pudding": {"cup": {"cal": 150, "fat": 3, "carbs": 28, "protein": 3, "sodium": 150, "fiber": 0, "sugar": 20},
                "box": {"cal": 400, "fat": 8, "carbs": 75, "protein": 8, "sodium": 400, "fiber": 0, "sugar": 53},
                "pkg": {"cal": 400, "fat": 8, "carbs": 75, "protein": 8, "sodium": 400, "fiber": 0, "sugar": 53},
                "": {"cal": 150, "fat": 3, "carbs": 28, "protein": 3, "sodium": 150, "fiber": 0, "sugar": 20}},
    "marshmallows": {"cup": {"cal": 159, "fat": 0, "carbs": 41, "protein": 1, "sodium": 22, "fiber": 0, "sugar": 29}},
    "graham cracker": {"sheet": {"cal": 59, "fat": 1.4, "carbs": 11, "protein": 1, "sodium": 67, "fiber": 0.4, "sugar": 4}},
    "crackers": {"cup": {"cal": 484, "fat": 15, "carbs": 78, "protein": 10, "sodium": 1080, "fiber": 3, "sugar": 6}},
    "ladyfingers": {"": {"cal": 40, "fat": 1, "carbs": 7, "protein": 1, "sodium": 16, "fiber": 0, "sugar": 4},
                   "doz": {"cal": 480, "fat": 12, "carbs": 84, "protein": 12, "sodium": 192, "fiber": 0, "sugar": 48}},
    "corn chips": {"cup": {"cal": 267, "fat": 14, "carbs": 33, "protein": 3, "sodium": 179, "fiber": 2, "sugar": 0}},
    "tortilla chips": {"cup": {"cal": 267, "fat": 14, "carbs": 33, "protein": 3, "sodium": 179, "fiber": 2, "sugar": 0}},
    "potato chips": {"cup": {"cal": 274, "fat": 19, "carbs": 25, "protein": 3, "sodium": 303, "fiber": 2, "sugar": 1},
                    "bag": {"cal": 800, "fat": 55, "carbs": 73, "protein": 9, "sodium": 900, "fiber": 6, "sugar": 3}},
    "french fried onions": {"cup": {"cal": 320, "fat": 24, "carbs": 24, "protein": 4, "sodium": 520, "fiber": 2, "sugar": 4}},
    "popcorn": {"cup": {"cal": 31, "fat": 0.4, "carbs": 6, "protein": 1, "sodium": 1, "fiber": 1, "sugar": 0.1},
               "quart": {"cal": 124, "fat": 1.6, "carbs": 24, "protein": 4, "sodium": 4, "fiber": 4, "sugar": 0.4},
               "bag": {"cal": 500, "fat": 32, "carbs": 50, "protein": 6, "sodium": 520, "fiber": 8, "sugar": 2}},
    "chocolate syrup": {"tbsp": {"cal": 52, "fat": 0.4, "carbs": 12, "protein": 0.5, "sodium": 27, "fiber": 0.4, "sugar": 10},
                       "cup": {"cal": 832, "fat": 6.4, "carbs": 192, "protein": 8, "sodium": 432, "fiber": 6.4, "sugar": 160}},

    # Cooking sprays & zests
    "cooking spray": {"": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "nonstick spray": {"": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "lemon zest": {"tsp": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0.1},
                   "tbsp": {"cal": 3, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0.2},
                   "": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0.1}},
    "orange zest": {"tsp": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0.2, "sugar": 0.2},
                    "tbsp": {"cal": 6, "fat": 0, "carbs": 1.5, "protein": 0.1, "sodium": 0, "fiber": 0.6, "sugar": 0.4}},
    "lime zest": {"tsp": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0.1, "sugar": 0.1},
                  "tbsp": {"cal": 3, "fat": 0, "carbs": 0.9, "protein": 0, "sodium": 0, "fiber": 0.3, "sugar": 0.2}},
    "onion juice": {"tbsp": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 1, "fiber": 0, "sugar": 0.4},
                    "tsp": {"cal": 1, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.1}},
    "grated onion": {"tbsp": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 1, "fiber": 0.1, "sugar": 0.4}},

    # Cream and creamed soups
    "cream": {"cup": {"cal": 821, "fat": 88, "carbs": 7, "protein": 5, "sodium": 89, "fiber": 0, "sugar": 7}},
    "whipped topping": {"cup": {"cal": 239, "fat": 19, "carbs": 17, "protein": 1, "sodium": 5, "fiber": 0, "sugar": 14}},
    "cool whip": {"cup": {"cal": 239, "fat": 19, "carbs": 17, "protein": 1, "sodium": 5, "fiber": 0, "sugar": 14}},
    "cream of chicken soup": {"can": {"cal": 226, "fat": 14, "carbs": 18, "protein": 6, "sodium": 1764, "fiber": 1, "sugar": 2}},
    "cream of mushroom soup": {"can": {"cal": 260, "fat": 18, "carbs": 18, "protein": 4, "sodium": 1740, "fiber": 2, "sugar": 4}},
    "cream of celery soup": {"can": {"cal": 180, "fat": 10, "carbs": 18, "protein": 2, "sodium": 1760, "fiber": 2, "sugar": 4}},
    "tomato soup": {"can": {"cal": 160, "fat": 2, "carbs": 34, "protein": 4, "sodium": 1400, "fiber": 2, "sugar": 20}},

    # Pinch/dash for minimal seasonings
    "pinch": {"": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 75, "fiber": 0, "sugar": 0}},
    "dash": {"": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 75, "fiber": 0, "sugar": 0}},

    # Baked goods & prepared items (from GrannysRecipes)
    "croissant": {"": {"cal": 230, "fat": 12, "carbs": 26, "protein": 5, "sodium": 310, "fiber": 1, "sugar": 6}},
    "crescent rolls": {"": {"cal": 100, "fat": 5, "carbs": 11, "protein": 2, "sodium": 220, "fiber": 0, "sugar": 2}},
    "puff pastry": {"sheet": {"cal": 900, "fat": 60, "carbs": 72, "protein": 12, "sodium": 360, "fiber": 2, "sugar": 2}},
    "english muffin": {"": {"cal": 134, "fat": 1, "carbs": 26, "protein": 4, "sodium": 264, "fiber": 2, "sugar": 2}},
    "angel food cake": {"slice": {"cal": 72, "fat": 0.2, "carbs": 16, "protein": 2, "sodium": 210, "fiber": 0, "sugar": 12}},
    "crepe": {"": {"cal": 90, "fat": 4, "carbs": 11, "protein": 3, "sodium": 100, "fiber": 0, "sugar": 2}},
    "crepes": {"": {"cal": 90, "fat": 4, "carbs": 11, "protein": 3, "sodium": 100, "fiber": 0, "sugar": 2}},
    "pound cake": {"slice": {"cal": 220, "fat": 10, "carbs": 28, "protein": 3, "sodium": 180, "fiber": 0.5, "sugar": 18}},

    # Convenience foods
    "cake mix": {"package": {"cal": 1600, "fat": 32, "carbs": 312, "protein": 16, "sodium": 2800, "fiber": 4, "sugar": 168}},
    "pudding mix": {"package": {"cal": 140, "fat": 0, "carbs": 35, "protein": 0, "sodium": 340, "fiber": 0, "sugar": 28}},
    "jello": {"package": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "pie filling": {"can": {"cal": 840, "fat": 0, "carbs": 210, "protein": 0, "sodium": 100, "fiber": 4, "sugar": 180}},
    "tater tots": {"cup": {"cal": 200, "fat": 10, "carbs": 24, "protein": 2, "sodium": 400, "fiber": 2, "sugar": 0}},
    "bouillon cube": {"": {"cal": 5, "fat": 0.1, "carbs": 0.6, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0}},

    # Additional vegetables/fruits
    "beets": {"cup": {"cal": 58, "fat": 0.2, "carbs": 13, "protein": 2, "sodium": 106, "fiber": 4, "sugar": 9}},
    "cherry": {"cup": {"cal": 87, "fat": 0.3, "carbs": 22, "protein": 1.5, "sodium": 0, "fiber": 3, "sugar": 18}},
    "cherries": {"cup": {"cal": 87, "fat": 0.3, "carbs": 22, "protein": 1.5, "sodium": 0, "fiber": 3, "sugar": 18}},
    "mandarin oranges": {"cup": {"cal": 72, "fat": 0.2, "carbs": 18, "protein": 1, "sodium": 10, "fiber": 2, "sugar": 14}},
    "prunes": {"cup": {"cal": 418, "fat": 0.7, "carbs": 111, "protein": 4, "sodium": 4, "fiber": 12, "sugar": 66}},
    "barley": {"cup": {"cal": 651, "fat": 2.3, "carbs": 135, "protein": 23, "sodium": 22, "fiber": 32, "sugar": 1}},

    # Condiments & misc
    "horseradish": {"tbsp": {"cal": 7, "fat": 0.1, "carbs": 2, "protein": 0.2, "sodium": 47, "fiber": 0.5, "sugar": 1}},
    "chili sauce": {"tbsp": {"cal": 20, "fat": 0.1, "carbs": 5, "protein": 0.3, "sodium": 200, "fiber": 0.2, "sugar": 3},
                   "cup": {"cal": 320, "fat": 1.6, "carbs": 80, "protein": 4.8, "sodium": 3200, "fiber": 3.2, "sugar": 48}},
    "pickles": {"cup": {"cal": 17, "fat": 0.2, "carbs": 3.7, "protein": 0.4, "sodium": 1208, "fiber": 1, "sugar": 2}},
    "pickle": {"": {"cal": 12, "fat": 0.1, "carbs": 2.7, "protein": 0.3, "sodium": 870, "fiber": 0.8, "sugar": 1}},

    # =========================================================================
    # ADDITIONAL FROM MomsRecipes DATABASE
    # =========================================================================

    # Meat variants & poultry
    "chicken thighs": {"lb": {"cal": 900, "fat": 56, "carbs": 0, "protein": 80, "sodium": 340, "fiber": 0, "sugar": 0}},
    "extra-lean ground beef": {"lb": {"cal": 800, "fat": 48, "carbs": 0, "protein": 88, "sodium": 300, "fiber": 0, "sugar": 0}},
    "pork chops": {"oz": {"cal": 52, "fat": 2.5, "carbs": 0, "protein": 7, "sodium": 18, "fiber": 0, "sugar": 0},
                   "": {"cal": 231, "fat": 13, "carbs": 0, "protein": 26, "sodium": 62, "fiber": 0, "sugar": 0}},
    "spareribs": {"lb": {"cal": 1200, "fat": 96, "carbs": 0, "protein": 80, "sodium": 400, "fiber": 0, "sugar": 0}},
    "lamb": {"lb": {"cal": 1100, "fat": 80, "carbs": 0, "protein": 88, "sodium": 280, "fiber": 0, "sugar": 0}},
    "ground lamb": {"lb": {"cal": 1100, "fat": 80, "carbs": 0, "protein": 88, "sodium": 280, "fiber": 0, "sugar": 0}},
    "lamb chops": {"lb": {"cal": 880, "fat": 60, "carbs": 0, "protein": 84, "sodium": 260, "fiber": 0, "sugar": 0}},
    "guanciale": {"oz": {"cal": 155, "fat": 14, "carbs": 0, "protein": 6, "sodium": 480, "fiber": 0, "sugar": 0}},
    "pancetta": {"oz": {"cal": 145, "fat": 13, "carbs": 0, "protein": 7, "sodium": 500, "fiber": 0, "sugar": 0}},
    "andouille sausage": {"oz": {"cal": 90, "fat": 8, "carbs": 1, "protein": 4, "sodium": 300, "fiber": 0, "sugar": 0}},
    "tofu": {"oz": {"cal": 22, "fat": 1.3, "carbs": 0.5, "protein": 2, "sodium": 2, "fiber": 0, "sugar": 0},
             "cup": {"cal": 176, "fat": 10, "carbs": 4, "protein": 16, "sodium": 16, "fiber": 0, "sugar": 0}},
    "fish": {"oz": {"cal": 35, "fat": 0.8, "carbs": 0, "protein": 7, "sodium": 45, "fiber": 0, "sugar": 0},
             "lb": {"cal": 560, "fat": 13, "carbs": 0, "protein": 112, "sodium": 720, "fiber": 0, "sugar": 0},
             "cup": {"cal": 140, "fat": 3.2, "carbs": 0, "protein": 28, "sodium": 180, "fiber": 0, "sugar": 0}},

    # Dairy aliases & variants
    "unsalted butter": {"cup": {"cal": 1628, "fat": 184, "carbs": 0, "protein": 2, "sodium": 12, "fiber": 0, "sugar": 0},
                        "tbsp": {"cal": 102, "fat": 11.5, "carbs": 0, "protein": 0.1, "sodium": 1, "fiber": 0, "sugar": 0}},
    "butter or margarine": {"cup": {"cal": 1628, "fat": 184, "carbs": 0, "protein": 2, "sodium": 1284, "fiber": 0, "sugar": 0},
                            "tbsp": {"cal": 102, "fat": 11.5, "carbs": 0, "protein": 0.1, "sodium": 80, "fiber": 0, "sugar": 0}},
    "oleo (margarine)": {"tbsp": {"cal": 100, "fat": 11, "carbs": 0, "protein": 0, "sodium": 90, "fiber": 0, "sugar": 0}},
    "whipping cream": {"cup": {"cal": 821, "fat": 88, "carbs": 7, "protein": 5, "sodium": 89, "fiber": 0, "sugar": 7}},
    "half-and-half": {"cup": {"cal": 315, "fat": 28, "carbs": 10, "protein": 7, "sodium": 98, "fiber": 0, "sugar": 10},
                      "tbsp": {"cal": 20, "fat": 1.7, "carbs": 0.6, "protein": 0.4, "sodium": 6, "fiber": 0, "sugar": 0.6}},
    "shredded cheddar cheese": {"cup": {"cal": 455, "fat": 37, "carbs": 1.5, "protein": 28, "sodium": 700, "fiber": 0, "sugar": 0}},
    "grated parmesan cheese": {"tbsp": {"cal": 22, "fat": 1.4, "carbs": 0.2, "protein": 2, "sodium": 76, "fiber": 0, "sugar": 0},
                               "cup": {"cal": 352, "fat": 22, "carbs": 3, "protein": 32, "sodium": 1216, "fiber": 0, "sugar": 0}},
    "cheese": {"cup": {"cal": 400, "fat": 32, "carbs": 2, "protein": 24, "sodium": 650, "fiber": 0, "sugar": 0},
               "oz": {"cal": 100, "fat": 8, "carbs": 0.5, "protein": 6, "sodium": 162, "fiber": 0, "sugar": 0},
               "slice": {"cal": 100, "fat": 8, "carbs": 0.5, "protein": 6, "sodium": 162, "fiber": 0, "sugar": 0},
               "": {"cal": 100, "fat": 8, "carbs": 0.5, "protein": 6, "sodium": 162, "fiber": 0, "sugar": 0}},
    "large eggs": {"": {"cal": 72, "fat": 5, "carbs": 0.4, "protein": 6, "sodium": 71, "fiber": 0, "sugar": 0.4}},
    "egg whites": {"": {"cal": 17, "fat": 0, "carbs": 0.2, "protein": 3.6, "sodium": 55, "fiber": 0, "sugar": 0}},
    "egg yolks": {"": {"cal": 55, "fat": 4.5, "carbs": 0.6, "protein": 2.7, "sodium": 8, "fiber": 0, "sugar": 0}},

    # Grains & starches
    "quick oats": {"cup": {"cal": 307, "fat": 5, "carbs": 55, "protein": 11, "sodium": 5, "fiber": 8, "sugar": 1}},
    "oatmeal": {"cup": {"cal": 307, "fat": 5, "carbs": 55, "protein": 11, "sodium": 5, "fiber": 8, "sugar": 1},
                "": {"cal": 150, "fat": 2.5, "carbs": 27, "protein": 5, "sodium": 3, "fiber": 4, "sugar": 0.5}},
    "noodles": {"cup": {"cal": 220, "fat": 2, "carbs": 40, "protein": 8, "sodium": 10, "fiber": 2, "sugar": 0}},
    "linguine": {"oz": {"cal": 100, "fat": 0.5, "carbs": 20, "protein": 3.5, "sodium": 1, "fiber": 1, "sugar": 0}},
    "elbow macaroni": {"cup": {"cal": 200, "fat": 1, "carbs": 41, "protein": 7, "sodium": 2, "fiber": 2, "sugar": 1}},
    "rotini": {"cup": {"cal": 200, "fat": 1, "carbs": 41, "protein": 7, "sodium": 2, "fiber": 2, "sugar": 1}},
    "fresh chinese noodles": {"oz": {"cal": 100, "fat": 1, "carbs": 20, "protein": 3, "sodium": 150, "fiber": 1, "sugar": 0}},
    "bread crumbs": {"cup": {"cal": 427, "fat": 6, "carbs": 78, "protein": 14, "sodium": 930, "fiber": 3, "sugar": 6}},
    "bread slices": {"": {"cal": 79, "fat": 1, "carbs": 15, "protein": 3, "sodium": 147, "fiber": 1, "sugar": 1}},
    "kashi pilaf": {"cup": {"cal": 170, "fat": 1, "carbs": 34, "protein": 6, "sodium": 0, "fiber": 6, "sugar": 0}},
    "biscuit mix": {"cup": {"cal": 480, "fat": 16, "carbs": 72, "protein": 8, "sodium": 1360, "fiber": 2, "sugar": 8}},
    "bisquick": {"cup": {"cal": 480, "fat": 16, "carbs": 72, "protein": 8, "sodium": 1360, "fiber": 2, "sugar": 8}},
    "graham crackers": {"cup": {"cal": 440, "fat": 10, "carbs": 80, "protein": 6, "sodium": 520, "fiber": 2, "sugar": 24}},
    "graham cracker crust": {"": {"cal": 800, "fat": 36, "carbs": 112, "protein": 8, "sodium": 600, "fiber": 2, "sugar": 40}},

    # Sugar aliases
    "granulated sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200},
                         "tbsp": {"cal": 48, "fat": 0, "carbs": 12.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 12.5}},
    "white sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200}},
    "light brown sugar": {"cup": {"cal": 829, "fat": 0, "carbs": 214, "protein": 0, "sodium": 57, "fiber": 0, "sugar": 212}},
    "packed brown sugar": {"cup": {"cal": 829, "fat": 0, "carbs": 214, "protein": 0, "sodium": 57, "fiber": 0, "sugar": 212}},
    "confectioners' sugar": {"cup": {"cal": 467, "fat": 0, "carbs": 119, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 117}},

    # Oils
    "oil": {"tbsp": {"cal": 120, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
            "cup": {"cal": 1920, "fat": 224, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "sesame oil": {"tbsp": {"cal": 120, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Vegetables
    "onions": {"cup": {"cal": 64, "fat": 0.2, "carbs": 15, "protein": 1.8, "sodium": 6, "fiber": 3, "sugar": 7}},
    "green onions": {"cup": {"cal": 32, "fat": 0.2, "carbs": 7, "protein": 1.8, "sodium": 16, "fiber": 2.6, "sugar": 2.3},
                     "bunch": {"cal": 32, "fat": 0.2, "carbs": 7, "protein": 1.8, "sodium": 16, "fiber": 2.6, "sugar": 2.3}},
    "carrots": {"cup": {"cal": 52, "fat": 0.3, "carbs": 12, "protein": 1.2, "sodium": 88, "fiber": 3.6, "sugar": 6}},
    "tomatoes": {"can": {"cal": 80, "fat": 0.4, "carbs": 16, "protein": 4, "sodium": 600, "fiber": 4, "sugar": 10},
                 "cup": {"cal": 32, "fat": 0.4, "carbs": 7, "protein": 1.6, "sodium": 9, "fiber": 2, "sugar": 5}},
    "potatoes": {"lb": {"cal": 350, "fat": 0.4, "carbs": 80, "protein": 9, "sodium": 28, "fiber": 9, "sugar": 4}},
    "rhubarb": {"cup": {"cal": 26, "fat": 0.2, "carbs": 6, "protein": 1.1, "sodium": 5, "fiber": 2, "sugar": 1.3}},
    "pumpkin": {"cup": {"cal": 83, "fat": 0.3, "carbs": 20, "protein": 3, "sodium": 12, "fiber": 3, "sugar": 8}},
    "okra": {"cup": {"cal": 33, "fat": 0.2, "carbs": 7, "protein": 2, "sodium": 7, "fiber": 3, "sugar": 1},
            "pkg": {"cal": 66, "fat": 0.4, "carbs": 14, "protein": 4, "sodium": 14, "fiber": 6, "sugar": 2},
            "": {"cal": 33, "fat": 0.2, "carbs": 7, "protein": 2, "sodium": 7, "fiber": 3, "sugar": 1}},
    "sauerkraut": {"cup": {"cal": 27, "fat": 0.2, "carbs": 6, "protein": 1.3, "sodium": 939, "fiber": 4, "sugar": 3}},
    "green chilies": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 550, "fiber": 2, "sugar": 3},
                     "cup": {"cal": 30, "fat": 0.2, "carbs": 7, "protein": 1, "sodium": 552, "fiber": 1.5, "sugar": 4},
                     "": {"cal": 8, "fat": 0, "carbs": 1.5, "protein": 0.3, "sodium": 140, "fiber": 0.4, "sugar": 1}},
    "chopped green chilies": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 550, "fiber": 2, "sugar": 3},
                             "cup": {"cal": 30, "fat": 0.2, "carbs": 7, "protein": 1, "sodium": 552, "fiber": 1.5, "sugar": 4},
                             "": {"cal": 8, "fat": 0, "carbs": 1.5, "protein": 0.3, "sodium": 140, "fiber": 0.4, "sugar": 1}},
    "frozen mixed vegetables": {"cup": {"cal": 82, "fat": 0.5, "carbs": 16, "protein": 4, "sodium": 64, "fiber": 5, "sugar": 4}},
    "mixed vegetables": {"cup": {"cal": 82, "fat": 0.5, "carbs": 16, "protein": 4, "sodium": 64, "fiber": 5, "sugar": 4}},
    "beans": {"cup": {"cal": 225, "fat": 1, "carbs": 40, "protein": 15, "sodium": 400, "fiber": 12, "sugar": 1}},

    # Fruits
    "calamondin": {"": {"cal": 12, "fat": 0.1, "carbs": 3, "protein": 0.2, "sodium": 1, "fiber": 0.5, "sugar": 1.5}},
    "calamondins": {"cup": {"cal": 60, "fat": 0.5, "carbs": 15, "protein": 1, "sodium": 5, "fiber": 2.5, "sugar": 7.5}},
    "crushed pineapple": {"can": {"cal": 280, "fat": 0.4, "carbs": 68, "protein": 2, "sodium": 4, "fiber": 4, "sugar": 60}},
    "apricots": {"cup": {"cal": 79, "fat": 0.6, "carbs": 18, "protein": 2.3, "sodium": 2, "fiber": 3, "sugar": 15}},
    "dried apricots": {"cup": {"cal": 313, "fat": 0.7, "carbs": 81, "protein": 4.4, "sodium": 13, "fiber": 9.5, "sugar": 69}},
    "lemons": {"": {"cal": 17, "fat": 0.2, "carbs": 5, "protein": 0.6, "sodium": 1, "fiber": 1.6, "sugar": 1.5}},
    "lemon": {"": {"cal": 17, "fat": 0.2, "carbs": 5, "protein": 0.6, "sodium": 1, "fiber": 1.6, "sugar": 1.5}},
    "cranberry juice": {"cup": {"cal": 116, "fat": 0.3, "carbs": 31, "protein": 0, "sodium": 5, "fiber": 0.3, "sugar": 31}},

    # Nuts
    "chopped pecans": {"cup": {"cal": 753, "fat": 78, "carbs": 15, "protein": 10, "sodium": 0, "fiber": 10, "sugar": 4}},
    "pecan halves": {"cup": {"cal": 753, "fat": 78, "carbs": 15, "protein": 10, "sodium": 0, "fiber": 10, "sugar": 4}},
    "chopped nuts": {"cup": {"cal": 800, "fat": 72, "carbs": 24, "protein": 20, "sodium": 5, "fiber": 8, "sugar": 4}},
    "nuts": {"cup": {"cal": 800, "fat": 72, "carbs": 24, "protein": 20, "sodium": 5, "fiber": 8, "sugar": 4}},
    "wheat germ": {"tbsp": {"cal": 26, "fat": 0.7, "carbs": 3.7, "protein": 2, "sodium": 0, "fiber": 1, "sugar": 0},
                   "cup": {"cal": 414, "fat": 11, "carbs": 60, "protein": 27, "sodium": 4, "fiber": 15, "sugar": 0}},

    # Baking & chocolate
    "chocolate": {"oz": {"cal": 155, "fat": 9, "carbs": 17, "protein": 1.4, "sodium": 7, "fiber": 2, "sugar": 14},
                  "cup": {"cal": 840, "fat": 48, "carbs": 92, "protein": 8, "sodium": 38, "fiber": 11, "sugar": 76},
                  "tbsp": {"cal": 50, "fat": 3, "carbs": 6, "protein": 0.5, "sodium": 2, "fiber": 0.7, "sugar": 4.5},
                  "": {"cal": 155, "fat": 9, "carbs": 17, "protein": 1.4, "sodium": 7, "fiber": 2, "sugar": 14}},
    "unsweetened cocoa": {"tbsp": {"cal": 12, "fat": 0.7, "carbs": 3, "protein": 1, "sodium": 1, "fiber": 2, "sugar": 0}},
    "vanilla": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.5}},
    "lemon extract": {"tsp": {"cal": 10, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.3}},
    "active dry yeast": {"packet": {"cal": 21, "fat": 0.3, "carbs": 3, "protein": 3, "sodium": 4, "fiber": 1, "sugar": 0}},
    "yellow cake mix": {"package": {"cal": 1600, "fat": 32, "carbs": 312, "protein": 16, "sodium": 2800, "fiber": 4, "sugar": 168}},
    "brownie mix": {"package": {"cal": 1600, "fat": 32, "carbs": 280, "protein": 16, "sodium": 800, "fiber": 4, "sugar": 160}},
    "liquid pectin": {"pouch": {"cal": 10, "fat": 0, "carbs": 3, "protein": 0, "sodium": 5, "fiber": 1, "sugar": 0}},

    # Pie shells
    "pie shell": {"": {"cal": 650, "fat": 40, "carbs": 64, "protein": 8, "sodium": 400, "fiber": 2, "sugar": 2}},
    "baked pie shell": {"": {"cal": 650, "fat": 40, "carbs": 64, "protein": 8, "sodium": 400, "fiber": 2, "sugar": 2}},
    "unbaked pie shell": {"": {"cal": 650, "fat": 40, "carbs": 64, "protein": 8, "sodium": 400, "fiber": 2, "sugar": 2}},

    # Herbs & spices - dried variants
    "ground cinnamon": {"tsp": {"cal": 6, "fat": 0, "carbs": 2, "protein": 0.1, "sodium": 0, "fiber": 1, "sugar": 0}},
    "ground nutmeg": {"tsp": {"cal": 12, "fat": 0.8, "carbs": 1.1, "protein": 0.1, "sodium": 0, "fiber": 0.5, "sugar": 0}},
    "ground ginger": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.3, "protein": 0.2, "sodium": 1, "fiber": 0.2, "sugar": 0.1}},
    "ground cumin": {"tsp": {"cal": 8, "fat": 0.5, "carbs": 0.9, "protein": 0.4, "sodium": 4, "fiber": 0.2, "sugar": 0}},
    "fresh ginger": {"tbsp": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 1, "fiber": 0.1, "sugar": 0.1},
                    "slice": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                    "inch": {"cal": 8, "fat": 0, "carbs": 2, "protein": 0.2, "sodium": 1, "fiber": 0.2, "sugar": 0.2},
                    "": {"cal": 8, "fat": 0, "carbs": 2, "protein": 0.2, "sodium": 1, "fiber": 0.2, "sugar": 0.2}},
    "fresh parsley": {"tbsp": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0.1, "sodium": 2, "fiber": 0.1, "sugar": 0}},
    "fresh dill": {"tbsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 2, "fiber": 0, "sugar": 0}},
    "dried dill": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.5, "protein": 0.2, "sodium": 2, "fiber": 0.1, "sugar": 0}},
    "dried oregano": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.7, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0}},
    "dried thyme": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.6, "protein": 0.1, "sodium": 1, "fiber": 0.3, "sugar": 0}},
    "dried parsley": {"tbsp": {"cal": 4, "fat": 0.1, "carbs": 0.6, "protein": 0.3, "sodium": 6, "fiber": 0.2, "sugar": 0.1}},
    "dried parsley flakes": {"tbsp": {"cal": 4, "fat": 0.1, "carbs": 0.6, "protein": 0.3, "sodium": 6, "fiber": 0.2, "sugar": 0.1}},
    "parsley flakes": {"tbsp": {"cal": 4, "fat": 0.1, "carbs": 0.6, "protein": 0.3, "sodium": 6, "fiber": 0.2, "sugar": 0.1}},
    "turmeric": {"tsp": {"cal": 8, "fat": 0.2, "carbs": 1.4, "protein": 0.3, "sodium": 1, "fiber": 0.5, "sugar": 0.1}},
    "poultry seasoning": {"tsp": {"cal": 5, "fat": 0.2, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "white pepper": {"tsp": {"cal": 7, "fat": 0.1, "carbs": 1.6, "protein": 0.3, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "salt and pepper": {"tsp": {"cal": 3, "fat": 0, "carbs": 0.7, "protein": 0.1, "sodium": 1163, "fiber": 0.3, "sugar": 0}},
    "seasoned salt": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 1360, "fiber": 0, "sugar": 0}},
    "garlic salt": {"tsp": {"cal": 3, "fat": 0, "carbs": 0.7, "protein": 0.1, "sodium": 1480, "fiber": 0, "sugar": 0}},
    "onion salt": {"tsp": {"cal": 3, "fat": 0, "carbs": 0.8, "protein": 0.1, "sodium": 1500, "fiber": 0.1, "sugar": 0.1}},
    "celery salt": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.5, "protein": 0.1, "sodium": 1470, "fiber": 0.1, "sugar": 0}},

    # Condiments & sauces
    "oyster sauce": {"tbsp": {"cal": 9, "fat": 0, "carbs": 2, "protein": 0.2, "sodium": 437, "fiber": 0, "sugar": 1}},
    "white vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "tabasco sauce": {"tsp": {"cal": 1, "fat": 0, "carbs": 0, "protein": 0, "sodium": 124, "fiber": 0, "sugar": 0}},
    "marinara sauce": {"cup": {"cal": 80, "fat": 2, "carbs": 12, "protein": 2, "sodium": 560, "fiber": 2, "sugar": 8}},

    # Alcohol
    "wine": {"cup": {"cal": 200, "fat": 0, "carbs": 5, "protein": 0.2, "sodium": 12, "fiber": 0, "sugar": 2}},
    "chinese cooking wine": {"tbsp": {"cal": 15, "fat": 0, "carbs": 2, "protein": 0, "sodium": 180, "fiber": 0, "sugar": 1}},
    "sherry": {"oz": {"cal": 45, "fat": 0, "carbs": 2, "protein": 0.1, "sodium": 3, "fiber": 0, "sugar": 1},
               "tbsp": {"cal": 22, "fat": 0, "carbs": 1, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 0.5}},
    "brandy": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
               "tbsp": {"cal": 32, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Water variants
    "warm water": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "hot water": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "cold water": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "boiling water": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Miscellaneous
    "miniature marshmallows": {"cup": {"cal": 159, "fat": 0.1, "carbs": 41, "protein": 1.4, "sodium": 22, "fiber": 0, "sugar": 29}},
    "pretzels": {"cup": {"cal": 229, "fat": 2, "carbs": 48, "protein": 5, "sodium": 814, "fiber": 2, "sugar": 1}},
    "chex cereal": {"cup": {"cal": 110, "fat": 0.5, "carbs": 25, "protein": 2, "sodium": 220, "fiber": 1, "sugar": 2}},
    "lemon rind": {"tbsp": {"cal": 3, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0.4}},
    "grated lemon rind": {"tbsp": {"cal": 3, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0.4}},
    "grated lemon peel": {"tbsp": {"cal": 3, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0.4}},
    "orange peel": {"tbsp": {"cal": 6, "fat": 0, "carbs": 2, "protein": 0.1, "sodium": 0, "fiber": 0.6, "sugar": 1}},
    "grated orange peel": {"tbsp": {"cal": 6, "fat": 0, "carbs": 2, "protein": 0.1, "sodium": 0, "fiber": 0.6, "sugar": 1}},
    "food coloring": {"drop": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "green food coloring": {"drop": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "red food coloring": {"drop": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "vegetable cooking spray": {"": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "nonstick cooking spray": {"": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # ADDITIONAL FROM MomsRecipes DATABASE - ROUND 2
    # =========================================================================

    # Beverages
    "cola": {"cup": {"cal": 97, "fat": 0, "carbs": 26, "protein": 0, "sodium": 7, "fiber": 0, "sugar": 26}},
    "soda": {"cup": {"cal": 97, "fat": 0, "carbs": 26, "protein": 0, "sodium": 7, "fiber": 0, "sugar": 26}},
    "ginger ale": {"cup": {"cal": 83, "fat": 0, "carbs": 21, "protein": 0, "sodium": 26, "fiber": 0, "sugar": 21}},
    "apple juice": {"cup": {"cal": 114, "fat": 0.3, "carbs": 28, "protein": 0.2, "sodium": 10, "fiber": 0.2, "sugar": 24},
                    "bottle": {"cal": 456, "fat": 1.2, "carbs": 112, "protein": 0.8, "sodium": 40, "fiber": 0.8, "sugar": 96}},
    "grape juice": {"cup": {"cal": 152, "fat": 0.2, "carbs": 37, "protein": 1, "sodium": 13, "fiber": 0.3, "sugar": 36}},
    "limeade": {"cup": {"cal": 104, "fat": 0, "carbs": 27, "protein": 0.1, "sodium": 5, "fiber": 0, "sugar": 26}},
    "lemonade": {"cup": {"cal": 99, "fat": 0.1, "carbs": 26, "protein": 0.2, "sodium": 7, "fiber": 0.2, "sugar": 25}},
    "cranberry juice": {"cup": {"cal": 116, "fat": 0.3, "carbs": 31, "protein": 0, "sodium": 5, "fiber": 0.3, "sugar": 31}},
    "tomato juice": {"cup": {"cal": 41, "fat": 0.1, "carbs": 10, "protein": 1.8, "sodium": 654, "fiber": 1, "sugar": 8}},
    "v8 juice": {"cup": {"cal": 46, "fat": 0.1, "carbs": 10, "protein": 1.5, "sodium": 480, "fiber": 1.5, "sugar": 7}},
    "prune juice": {"cup": {"cal": 182, "fat": 0.1, "carbs": 45, "protein": 1.6, "sodium": 10, "fiber": 2.6, "sugar": 42}},

    # Proteins - meats & poultry
    "veal": {"lb": {"cal": 800, "fat": 32, "carbs": 0, "protein": 120, "sodium": 340, "fiber": 0, "sugar": 0}},
    "duck": {"lb": {"cal": 1300, "fat": 100, "carbs": 0, "protein": 88, "sodium": 280, "fiber": 0, "sugar": 0}},
    "liver": {"lb": {"cal": 600, "fat": 16, "carbs": 16, "protein": 92, "sodium": 300, "fiber": 0, "sugar": 0},
              "": {"cal": 150, "fat": 4, "carbs": 4, "protein": 23, "sodium": 75, "fiber": 0, "sugar": 0}},
    "sweetbreads": {"lb": {"cal": 680, "fat": 32, "carbs": 0, "protein": 92, "sodium": 400, "fiber": 0, "sugar": 0},
                   "": {"cal": 170, "fat": 8, "carbs": 0, "protein": 23, "sodium": 100, "fiber": 0, "sugar": 0}},
    "chicken liver": {"lb": {"cal": 600, "fat": 16, "carbs": 3, "protein": 84, "sodium": 320, "fiber": 0, "sugar": 0},
                      "": {"cal": 35, "fat": 1, "carbs": 0.2, "protein": 5, "sodium": 20, "fiber": 0, "sugar": 0}},
    "hot dog": {"each": {"cal": 151, "fat": 13, "carbs": 2, "protein": 5, "sodium": 567, "fiber": 0, "sugar": 1},
                "": {"cal": 151, "fat": 13, "carbs": 2, "protein": 5, "sodium": 567, "fiber": 0, "sugar": 1}},
    "hot dogs": {"each": {"cal": 151, "fat": 13, "carbs": 2, "protein": 5, "sodium": 567, "fiber": 0, "sugar": 1},
                 "": {"cal": 151, "fat": 13, "carbs": 2, "protein": 5, "sodium": 567, "fiber": 0, "sugar": 1}},
    "frankfurter": {"each": {"cal": 151, "fat": 13, "carbs": 2, "protein": 5, "sodium": 567, "fiber": 0, "sugar": 1},
                    "": {"cal": 151, "fat": 13, "carbs": 2, "protein": 5, "sodium": 567, "fiber": 0, "sugar": 1}},
    "pepperoni": {"oz": {"cal": 138, "fat": 12, "carbs": 0.9, "protein": 6, "sodium": 463, "fiber": 0, "sugar": 0},
                  "package": {"cal": 828, "fat": 72, "carbs": 5.4, "protein": 36, "sodium": 2778, "fiber": 0, "sugar": 0},
                  "slice": {"cal": 14, "fat": 1.2, "carbs": 0.1, "protein": 0.6, "sodium": 46, "fiber": 0, "sugar": 0},
                  "": {"cal": 14, "fat": 1.2, "carbs": 0.1, "protein": 0.6, "sodium": 46, "fiber": 0, "sugar": 0}},
    "salami": {"oz": {"cal": 119, "fat": 10, "carbs": 0.5, "protein": 6, "sodium": 529, "fiber": 0, "sugar": 0}},
    "prosciutto": {"oz": {"cal": 55, "fat": 3, "carbs": 0.3, "protein": 7, "sodium": 520, "fiber": 0, "sugar": 0}},
    "corned beef": {"lb": {"cal": 800, "fat": 48, "carbs": 2, "protein": 88, "sodium": 3200, "fiber": 0, "sugar": 0}},

    # Proteins - seafood
    "halibut": {"lb": {"cal": 500, "fat": 10, "carbs": 0, "protein": 96, "sodium": 260, "fiber": 0, "sugar": 0}},
    "catfish": {"lb": {"cal": 544, "fat": 24, "carbs": 0, "protein": 80, "sodium": 200, "fiber": 0, "sugar": 0}},
    "scallops": {"lb": {"cal": 400, "fat": 4, "carbs": 8, "protein": 76, "sodium": 700, "fiber": 0, "sugar": 0}},
    "sea scallops": {"lb": {"cal": 400, "fat": 4, "carbs": 8, "protein": 76, "sodium": 700, "fiber": 0, "sugar": 0}},
    "oysters": {"cup": {"cal": 169, "fat": 6, "carbs": 10, "protein": 17, "sodium": 521, "fiber": 0, "sugar": 0}},
    "mussels": {"lb": {"cal": 350, "fat": 8, "carbs": 16, "protein": 48, "sodium": 1200, "fiber": 0, "sugar": 0}},
    "sardines": {"can": {"cal": 191, "fat": 11, "carbs": 0, "protein": 23, "sodium": 465, "fiber": 0, "sugar": 0}},
    "anchovies": {"can": {"cal": 95, "fat": 4, "carbs": 0, "protein": 13, "sodium": 1650, "fiber": 0, "sugar": 0}},
    "anchovy fillets": {"each": {"cal": 8, "fat": 0.4, "carbs": 0, "protein": 1, "sodium": 147, "fiber": 0, "sugar": 0}},
    "cod": {"lb": {"cal": 372, "fat": 3, "carbs": 0, "protein": 80, "sodium": 220, "fiber": 0, "sugar": 0}},
    "sole": {"lb": {"cal": 360, "fat": 4, "carbs": 0, "protein": 76, "sodium": 360, "fiber": 0, "sugar": 0}},
    "flounder": {"lb": {"cal": 360, "fat": 4, "carbs": 0, "protein": 76, "sodium": 360, "fiber": 0, "sugar": 0}},
    "perch": {"lb": {"cal": 420, "fat": 4, "carbs": 0, "protein": 88, "sodium": 300, "fiber": 0, "sugar": 0}},
    "trout": {"lb": {"cal": 600, "fat": 24, "carbs": 0, "protein": 92, "sodium": 220, "fiber": 0, "sugar": 0}},
    "swordfish": {"lb": {"cal": 548, "fat": 16, "carbs": 0, "protein": 92, "sodium": 420, "fiber": 0, "sugar": 0}},
    "mahi mahi": {"lb": {"cal": 384, "fat": 4, "carbs": 0, "protein": 84, "sodium": 400, "fiber": 0, "sugar": 0}},

    # Legumes
    "navy beans": {"cup": {"cal": 255, "fat": 1, "carbs": 47, "protein": 15, "sodium": 0, "fiber": 19, "sugar": 0}},
    "lima beans": {"cup": {"cal": 216, "fat": 0.7, "carbs": 39, "protein": 15, "sodium": 29, "fiber": 13, "sugar": 6}},
    "chickpeas": {"cup": {"cal": 269, "fat": 4, "carbs": 45, "protein": 15, "sodium": 11, "fiber": 12.5, "sugar": 8}},
    "garbanzo beans": {"cup": {"cal": 269, "fat": 4, "carbs": 45, "protein": 15, "sodium": 11, "fiber": 12.5, "sugar": 8}},
    "lentils": {"cup": {"cal": 230, "fat": 0.8, "carbs": 40, "protein": 18, "sodium": 4, "fiber": 16, "sugar": 4}},
    "split peas": {"cup": {"cal": 231, "fat": 0.8, "carbs": 41, "protein": 16, "sodium": 4, "fiber": 16, "sugar": 6}},
    "hummus": {"cup": {"cal": 435, "fat": 21, "carbs": 50, "protein": 20, "sodium": 960, "fiber": 15, "sugar": 0}},

    # Dairy
    "ricotta cheese": {"cup": {"cal": 428, "fat": 32, "carbs": 7.5, "protein": 28, "sodium": 307, "fiber": 0, "sugar": 0.6}},
    "ricotta": {"cup": {"cal": 428, "fat": 32, "carbs": 7.5, "protein": 28, "sodium": 307, "fiber": 0, "sugar": 0.6}},
    "blue cheese": {"oz": {"cal": 100, "fat": 8, "carbs": 0.7, "protein": 6, "sodium": 325, "fiber": 0, "sugar": 0.1},
                   "cup": {"cal": 475, "fat": 39, "carbs": 3, "protein": 29, "sodium": 1508, "fiber": 0, "sugar": 0.5},
                   "lb": {"cal": 1600, "fat": 128, "carbs": 11, "protein": 96, "sodium": 5200, "fiber": 0, "sugar": 1.6},
                   "tbsp": {"cal": 30, "fat": 2.4, "carbs": 0.2, "protein": 1.8, "sodium": 94, "fiber": 0, "sugar": 0}},
    "feta cheese": {"oz": {"cal": 75, "fat": 6, "carbs": 1, "protein": 4, "sodium": 316, "fiber": 0, "sugar": 1}},
    "feta": {"oz": {"cal": 75, "fat": 6, "carbs": 1, "protein": 4, "sodium": 316, "fiber": 0, "sugar": 1}},
    "goat cheese": {"oz": {"cal": 76, "fat": 6, "carbs": 0, "protein": 5, "sodium": 104, "fiber": 0, "sugar": 0}},
    "gorgonzola": {"oz": {"cal": 100, "fat": 9, "carbs": 1, "protein": 6, "sodium": 375, "fiber": 0, "sugar": 0}},
    "gorgonzola cheese": {"oz": {"cal": 100, "fat": 9, "carbs": 1, "protein": 6, "sodium": 375, "fiber": 0, "sugar": 0}},
    "string cheese": {"each": {"cal": 80, "fat": 6, "carbs": 1, "protein": 7, "sodium": 200, "fiber": 0, "sugar": 0},
                      "piece": {"cal": 80, "fat": 6, "carbs": 1, "protein": 7, "sodium": 200, "fiber": 0, "sugar": 0}},
    "mozzarella string cheese": {"each": {"cal": 80, "fat": 6, "carbs": 1, "protein": 7, "sodium": 200, "fiber": 0, "sugar": 0},
                                 "piece": {"cal": 80, "fat": 6, "carbs": 1, "protein": 7, "sodium": 200, "fiber": 0, "sugar": 0}},
    "crème fraîche": {"cup": {"cal": 450, "fat": 45, "carbs": 3, "protein": 3, "sodium": 40, "fiber": 0, "sugar": 3},
                     "tbsp": {"cal": 28, "fat": 2.8, "carbs": 0.2, "protein": 0.2, "sodium": 2, "fiber": 0, "sugar": 0.2}},
    "creme fraiche": {"cup": {"cal": 450, "fat": 45, "carbs": 3, "protein": 3, "sodium": 40, "fiber": 0, "sugar": 3},
                     "tbsp": {"cal": 28, "fat": 2.8, "carbs": 0.2, "protein": 0.2, "sodium": 2, "fiber": 0, "sugar": 0.2}},
    "ice cream": {"cup": {"cal": 273, "fat": 15, "carbs": 31, "protein": 5, "sodium": 100, "fiber": 0.7, "sugar": 28}},
    "vanilla ice cream": {"cup": {"cal": 273, "fat": 15, "carbs": 31, "protein": 5, "sodium": 100, "fiber": 0.7, "sugar": 28}},
    "sweetened condensed milk": {"can": {"cal": 982, "fat": 27, "carbs": 166, "protein": 24, "sodium": 389, "fiber": 0, "sugar": 166}},
    "mascarpone": {"cup": {"cal": 920, "fat": 96, "carbs": 4, "protein": 8, "sodium": 80, "fiber": 0, "sugar": 4}},
    "queso fresco": {"oz": {"cal": 80, "fat": 6, "carbs": 1, "protein": 5, "sodium": 180, "fiber": 0, "sugar": 0}},

    # Produce - vegetables
    "artichoke": {"each": {"cal": 60, "fat": 0.2, "carbs": 13, "protein": 4, "sodium": 120, "fiber": 6.5, "sugar": 1}},
    "artichoke hearts": {"cup": {"cal": 90, "fat": 0.3, "carbs": 20, "protein": 6, "sodium": 180, "fiber": 9, "sugar": 2}},
    "parsnips": {"cup": {"cal": 100, "fat": 0.4, "carbs": 24, "protein": 1.6, "sodium": 13, "fiber": 6.5, "sugar": 6}},
    "parsnip": {"cup": {"cal": 100, "fat": 0.4, "carbs": 24, "protein": 1.6, "sodium": 13, "fiber": 6.5, "sugar": 6},
                "": {"cal": 75, "fat": 0.3, "carbs": 18, "protein": 1.2, "sodium": 10, "fiber": 5, "sugar": 4.5}},
    "radish": {"cup": {"cal": 19, "fat": 0.1, "carbs": 4, "protein": 0.8, "sodium": 45, "fiber": 1.9, "sugar": 2}},
    "radishes": {"cup": {"cal": 19, "fat": 0.1, "carbs": 4, "protein": 0.8, "sodium": 45, "fiber": 1.9, "sugar": 2}},
    "turnip": {"cup": {"cal": 36, "fat": 0.1, "carbs": 8, "protein": 1, "sodium": 87, "fiber": 2.3, "sugar": 5}},
    "turnips": {"cup": {"cal": 36, "fat": 0.1, "carbs": 8, "protein": 1, "sodium": 87, "fiber": 2.3, "sugar": 5}},
    "watercress": {"cup": {"cal": 4, "fat": 0, "carbs": 0.4, "protein": 0.8, "sodium": 14, "fiber": 0.2, "sugar": 0.1}},
    "shallot": {"tbsp": {"cal": 7, "fat": 0, "carbs": 2, "protein": 0.3, "sodium": 1, "fiber": 0, "sugar": 0.8},
               "": {"cal": 28, "fat": 0, "carbs": 7, "protein": 1, "sodium": 5, "fiber": 0, "sugar": 3}},
    "shallots": {"tbsp": {"cal": 7, "fat": 0, "carbs": 2, "protein": 0.3, "sodium": 1, "fiber": 0, "sugar": 0.8},
                "": {"cal": 28, "fat": 0, "carbs": 7, "protein": 1, "sodium": 5, "fiber": 0, "sugar": 3}},
    "leek": {"cup": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1.3, "sodium": 18, "fiber": 1.6, "sugar": 3.5}},
    "leeks": {"cup": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1.3, "sodium": 18, "fiber": 1.6, "sugar": 3.5}},
    "fennel": {"cup": {"cal": 27, "fat": 0.2, "carbs": 6, "protein": 1, "sodium": 45, "fiber": 3, "sugar": 3},
               "bulb": {"cal": 73, "fat": 0.5, "carbs": 17, "protein": 3, "sodium": 122, "fiber": 7, "sugar": 8},
               "": {"cal": 73, "fat": 0.5, "carbs": 17, "protein": 3, "sodium": 122, "fiber": 7, "sugar": 8}},
    "fennel bulb": {"cup": {"cal": 27, "fat": 0.2, "carbs": 6, "protein": 1, "sodium": 45, "fiber": 3, "sugar": 3},
                   "": {"cal": 73, "fat": 0.5, "carbs": 17, "protein": 3, "sodium": 122, "fiber": 7, "sugar": 8}},
    "rutabaga": {"cup": {"cal": 52, "fat": 0.3, "carbs": 12, "protein": 1.5, "sodium": 28, "fiber": 3, "sugar": 7}},
    "kohlrabi": {"cup": {"cal": 36, "fat": 0.1, "carbs": 8, "protein": 2, "sodium": 27, "fiber": 5, "sugar": 4}},
    "jicama": {"cup": {"cal": 46, "fat": 0.1, "carbs": 11, "protein": 0.9, "sodium": 5, "fiber": 6, "sugar": 2}},
    "bok choy": {"cup": {"cal": 9, "fat": 0.1, "carbs": 1.5, "protein": 1, "sodium": 46, "fiber": 0.7, "sugar": 0.8}},
    "swiss chard": {"cup": {"cal": 7, "fat": 0.1, "carbs": 1.4, "protein": 0.6, "sodium": 77, "fiber": 0.6, "sugar": 0.4}},
    "collard greens": {"cup": {"cal": 11, "fat": 0.2, "carbs": 2, "protein": 1, "sodium": 6, "fiber": 1.4, "sugar": 0.2}},
    "mustard greens": {"cup": {"cal": 15, "fat": 0.2, "carbs": 3, "protein": 1.5, "sodium": 14, "fiber": 2, "sugar": 0.8}},

    # Produce - fruits
    "blackberries": {"cup": {"cal": 62, "fat": 0.7, "carbs": 14, "protein": 2, "sodium": 1, "fiber": 7.6, "sugar": 7}},
    "cantaloupe": {"cup": {"cal": 53, "fat": 0.3, "carbs": 13, "protein": 1.3, "sodium": 25, "fiber": 1.4, "sugar": 12}},
    "figs": {"each": {"cal": 37, "fat": 0.2, "carbs": 10, "protein": 0.4, "sodium": 1, "fiber": 1.5, "sugar": 8}},
    "dried figs": {"cup": {"cal": 371, "fat": 1.4, "carbs": 95, "protein": 5, "sodium": 14, "fiber": 14.6, "sugar": 71}},
    "honeydew": {"cup": {"cal": 61, "fat": 0.2, "carbs": 15, "protein": 0.9, "sodium": 30, "fiber": 1.4, "sugar": 14}},
    "honeydew melon": {"cup": {"cal": 61, "fat": 0.2, "carbs": 15, "protein": 0.9, "sodium": 30, "fiber": 1.4, "sugar": 14}},
    "kiwi": {"each": {"cal": 42, "fat": 0.4, "carbs": 10, "protein": 0.8, "sodium": 2, "fiber": 2.1, "sugar": 6}},
    "kiwi fruit": {"each": {"cal": 42, "fat": 0.4, "carbs": 10, "protein": 0.8, "sodium": 2, "fiber": 2.1, "sugar": 6}},
    "mango": {"each": {"cal": 202, "fat": 1.3, "carbs": 50, "protein": 2.8, "sodium": 3, "fiber": 5.4, "sugar": 45}},
    "papaya": {"cup": {"cal": 55, "fat": 0.2, "carbs": 14, "protein": 0.8, "sodium": 4, "fiber": 2.5, "sugar": 8}},
    "passion fruit": {"each": {"cal": 17, "fat": 0.1, "carbs": 4, "protein": 0.4, "sodium": 5, "fiber": 1.9, "sugar": 2}},
    "pomegranate": {"each": {"cal": 234, "fat": 3.3, "carbs": 53, "protein": 4.7, "sodium": 8, "fiber": 11, "sugar": 39}},
    "pomegranate seeds": {"cup": {"cal": 144, "fat": 2, "carbs": 33, "protein": 3, "sodium": 5, "fiber": 7, "sugar": 24}},
    "persimmon": {"each": {"cal": 118, "fat": 0.3, "carbs": 31, "protein": 1, "sodium": 2, "fiber": 6, "sugar": 21}},
    "guava": {"each": {"cal": 37, "fat": 0.5, "carbs": 8, "protein": 1.4, "sodium": 1, "fiber": 3, "sugar": 5}},
    "star fruit": {"each": {"cal": 28, "fat": 0.3, "carbs": 6, "protein": 1, "sodium": 2, "fiber": 2.5, "sugar": 4}},
    "tangerine": {"each": {"cal": 47, "fat": 0.3, "carbs": 12, "protein": 0.7, "sodium": 2, "fiber": 1.6, "sugar": 9}},
    "clementine": {"each": {"cal": 35, "fat": 0.1, "carbs": 9, "protein": 0.6, "sodium": 1, "fiber": 1.3, "sugar": 7}},
    "nectarine": {"each": {"cal": 63, "fat": 0.5, "carbs": 15, "protein": 1.5, "sodium": 0, "fiber": 2.4, "sugar": 11}},
    "plantain": {"each": {"cal": 218, "fat": 0.5, "carbs": 57, "protein": 2, "sodium": 6, "fiber": 4, "sugar": 27}},

    # Grains
    "stuffing mix": {"cup": {"cal": 356, "fat": 17, "carbs": 44, "protein": 6, "sodium": 1086, "fiber": 3, "sugar": 4}},
    "corn flakes": {"cup": {"cal": 101, "fat": 0.2, "carbs": 24, "protein": 2, "sodium": 203, "fiber": 0.7, "sugar": 3}},
    "bran": {"cup": {"cal": 125, "fat": 2.5, "carbs": 37, "protein": 9, "sodium": 1, "fiber": 25, "sugar": 0}},
    "wheat bran": {"cup": {"cal": 125, "fat": 2.5, "carbs": 37, "protein": 9, "sodium": 1, "fiber": 25, "sugar": 0}},
    "oat bran": {"cup": {"cal": 231, "fat": 6.5, "carbs": 62, "protein": 16, "sodium": 4, "fiber": 14.5, "sugar": 1}},
    "wild rice": {"cup": {"cal": 166, "fat": 0.6, "carbs": 35, "protein": 6.5, "sodium": 5, "fiber": 3, "sugar": 1}},
    "grits": {"cup": {"cal": 143, "fat": 0.5, "carbs": 31, "protein": 3, "sodium": 5, "fiber": 1, "sugar": 0}},
    "polenta": {"cup": {"cal": 143, "fat": 0.5, "carbs": 31, "protein": 3, "sodium": 5, "fiber": 1, "sugar": 0}},
    "couscous": {"cup": {"cal": 176, "fat": 0.3, "carbs": 36, "protein": 6, "sodium": 8, "fiber": 2.2, "sugar": 0}},
    "quinoa": {"cup": {"cal": 222, "fat": 4, "carbs": 39, "protein": 8, "sodium": 13, "fiber": 5, "sugar": 0}},
    "bulgur": {"cup": {"cal": 151, "fat": 0.4, "carbs": 34, "protein": 6, "sodium": 9, "fiber": 8, "sugar": 0}},
    "farro": {"cup": {"cal": 200, "fat": 1.5, "carbs": 40, "protein": 8, "sodium": 0, "fiber": 5, "sugar": 0}},
    "barley": {"cup": {"cal": 193, "fat": 0.7, "carbs": 44, "protein": 4, "sodium": 5, "fiber": 6, "sugar": 0.4}},
    "pearl barley": {"cup": {"cal": 193, "fat": 0.7, "carbs": 44, "protein": 4, "sodium": 5, "fiber": 6, "sugar": 0.4}},
    "millet": {"cup": {"cal": 207, "fat": 1.7, "carbs": 41, "protein": 6, "sodium": 3, "fiber": 2.3, "sugar": 0}},
    "buckwheat": {"cup": {"cal": 155, "fat": 1, "carbs": 34, "protein": 6, "sodium": 7, "fiber": 4.5, "sugar": 0}},
    "orzo": {"cup": {"cal": 200, "fat": 0.9, "carbs": 42, "protein": 7, "sodium": 0, "fiber": 2, "sugar": 0}},

    # Nuts & seeds
    "macadamia nuts": {"cup": {"cal": 962, "fat": 102, "carbs": 18, "protein": 10, "sodium": 6, "fiber": 11, "sugar": 6}},
    "macadamias": {"cup": {"cal": 962, "fat": 102, "carbs": 18, "protein": 10, "sodium": 6, "fiber": 11, "sugar": 6}},
    "pine nuts": {"cup": {"cal": 909, "fat": 92, "carbs": 18, "protein": 18, "sodium": 3, "fiber": 5, "sugar": 5}},
    "pignoli": {"cup": {"cal": 909, "fat": 92, "carbs": 18, "protein": 18, "sodium": 3, "fiber": 5, "sugar": 5}},
    "hazelnuts": {"cup": {"cal": 848, "fat": 82, "carbs": 23, "protein": 20, "sodium": 0, "fiber": 13, "sugar": 6}},
    "filberts": {"cup": {"cal": 848, "fat": 82, "carbs": 23, "protein": 20, "sodium": 0, "fiber": 13, "sugar": 6}},
    "pistachios": {"cup": {"cal": 685, "fat": 55, "carbs": 34, "protein": 25, "sodium": 1, "fiber": 13, "sugar": 9}},
    "poppy seeds": {"tbsp": {"cal": 46, "fat": 4, "carbs": 2, "protein": 1.6, "sodium": 2, "fiber": 0.5, "sugar": 0.3}},
    "tahini": {"tbsp": {"cal": 89, "fat": 8, "carbs": 3, "protein": 2.6, "sodium": 17, "fiber": 0.7, "sugar": 0}},
    "sesame paste": {"tbsp": {"cal": 89, "fat": 8, "carbs": 3, "protein": 2.6, "sodium": 17, "fiber": 0.7, "sugar": 0}},
    "pumpkin seeds": {"cup": {"cal": 285, "fat": 12, "carbs": 34, "protein": 12, "sodium": 12, "fiber": 12, "sugar": 0}},
    "pepitas": {"cup": {"cal": 285, "fat": 12, "carbs": 34, "protein": 12, "sodium": 12, "fiber": 12, "sugar": 0}},
    "chia seeds": {"tbsp": {"cal": 58, "fat": 4, "carbs": 5, "protein": 2, "sodium": 2, "fiber": 4, "sugar": 0}},
    "hemp seeds": {"tbsp": {"cal": 57, "fat": 4, "carbs": 1, "protein": 3, "sodium": 0, "fiber": 0.3, "sugar": 0}},

    # Canned goods
    "rotel": {"can": {"cal": 50, "fat": 0, "carbs": 10, "protein": 2, "sodium": 890, "fiber": 2, "sugar": 6}},
    "bamboo shoots": {"cup": {"cal": 25, "fat": 0.5, "carbs": 4, "protein": 2.5, "sodium": 9, "fiber": 2, "sugar": 3}},
    "water chestnuts": {"cup": {"cal": 60, "fat": 0.1, "carbs": 15, "protein": 1, "sodium": 9, "fiber": 2, "sugar": 3}},
    "fruit cocktail": {"cup": {"cal": 110, "fat": 0, "carbs": 28, "protein": 0.5, "sodium": 10, "fiber": 2.5, "sugar": 26}},
    "mandarin oranges": {"cup": {"cal": 72, "fat": 0.1, "carbs": 19, "protein": 1, "sodium": 12, "fiber": 1.8, "sugar": 16}},
    "crushed pineapple": {"cup": {"cal": 109, "fat": 0.2, "carbs": 28, "protein": 0.8, "sodium": 2, "fiber": 2, "sugar": 25}},
    "pineapple chunks": {"cup": {"cal": 109, "fat": 0.2, "carbs": 28, "protein": 0.8, "sodium": 2, "fiber": 2, "sugar": 25}},
    "pineapple tidbits": {"cup": {"cal": 109, "fat": 0.2, "carbs": 28, "protein": 0.8, "sodium": 2, "fiber": 2, "sugar": 25}},
    "sliced pineapple": {"cup": {"cal": 109, "fat": 0.2, "carbs": 28, "protein": 0.8, "sodium": 2, "fiber": 2, "sugar": 25}},
    "hearts of palm": {"cup": {"cal": 41, "fat": 0.9, "carbs": 7, "protein": 4, "sodium": 622, "fiber": 3.5, "sugar": 0}},
    "palm hearts": {"cup": {"cal": 41, "fat": 0.9, "carbs": 7, "protein": 4, "sodium": 622, "fiber": 3.5, "sugar": 0}},

    # Sauces & condiments
    "pesto": {"tbsp": {"cal": 80, "fat": 8, "carbs": 1, "protein": 2, "sodium": 125, "fiber": 0, "sugar": 0}},
    "basil pesto": {"tbsp": {"cal": 80, "fat": 8, "carbs": 1, "protein": 2, "sodium": 125, "fiber": 0, "sugar": 0}},
    "sun-dried tomato pesto": {"tbsp": {"cal": 70, "fat": 6, "carbs": 3, "protein": 1, "sodium": 160, "fiber": 0.5, "sugar": 2}},
    "aioli": {"tbsp": {"cal": 100, "fat": 11, "carbs": 0.5, "protein": 0.3, "sodium": 110, "fiber": 0, "sugar": 0}},
    "chipotle mayo": {"tbsp": {"cal": 100, "fat": 11, "carbs": 0.5, "protein": 0.1, "sodium": 140, "fiber": 0, "sugar": 0}},
    "sriracha mayo": {"tbsp": {"cal": 100, "fat": 11, "carbs": 1, "protein": 0.1, "sodium": 160, "fiber": 0, "sugar": 0.5}},
    "tartar sauce": {"tbsp": {"cal": 74, "fat": 8, "carbs": 1, "protein": 0.2, "sodium": 107, "fiber": 0, "sugar": 1}},
    "cocktail sauce": {"tbsp": {"cal": 20, "fat": 0, "carbs": 5, "protein": 0.3, "sodium": 270, "fiber": 0, "sugar": 4}},
    "hoisin sauce": {"tbsp": {"cal": 35, "fat": 0.5, "carbs": 7, "protein": 0.5, "sodium": 258, "fiber": 0.4, "sugar": 5}},
    "fish sauce": {"tbsp": {"cal": 6, "fat": 0, "carbs": 0.7, "protein": 0.9, "sodium": 1413, "fiber": 0, "sugar": 0}},
    "oyster sauce": {"tbsp": {"cal": 9, "fat": 0, "carbs": 2, "protein": 0.2, "sodium": 492, "fiber": 0, "sugar": 1}},
    "miso paste": {"tbsp": {"cal": 34, "fat": 1, "carbs": 4.5, "protein": 2, "sodium": 634, "fiber": 0.9, "sugar": 1}},
    "white miso": {"tbsp": {"cal": 34, "fat": 1, "carbs": 4.5, "protein": 2, "sodium": 634, "fiber": 0.9, "sugar": 1}},
    "red miso": {"tbsp": {"cal": 35, "fat": 1, "carbs": 5, "protein": 2, "sodium": 750, "fiber": 1, "sugar": 1}},
    "sambal oelek": {"tbsp": {"cal": 15, "fat": 0, "carbs": 3, "protein": 0.5, "sodium": 600, "fiber": 1, "sugar": 1}},
    "gochujang": {"tbsp": {"cal": 40, "fat": 1, "carbs": 8, "protein": 1, "sodium": 410, "fiber": 1, "sugar": 4}},
    "harissa": {"tbsp": {"cal": 15, "fat": 0.5, "carbs": 2.5, "protein": 0.5, "sodium": 95, "fiber": 0.5, "sugar": 1}},
    "chili garlic sauce": {"tbsp": {"cal": 20, "fat": 0.5, "carbs": 4, "protein": 0.5, "sodium": 450, "fiber": 0.5, "sugar": 2}},
    "duck sauce": {"tbsp": {"cal": 60, "fat": 0, "carbs": 15, "protein": 0, "sodium": 75, "fiber": 0, "sugar": 13}},
    "plum sauce": {"tbsp": {"cal": 35, "fat": 0, "carbs": 8, "protein": 0.2, "sodium": 180, "fiber": 0.2, "sugar": 6}},
    "sweet chili sauce": {"tbsp": {"cal": 40, "fat": 0, "carbs": 10, "protein": 0.1, "sodium": 220, "fiber": 0, "sugar": 9}},
    "ponzu": {"tbsp": {"cal": 10, "fat": 0, "carbs": 2, "protein": 0.5, "sodium": 600, "fiber": 0, "sugar": 1}},

    # Prepared foods
    "pizza dough": {"lb": {"cal": 1100, "fat": 6, "carbs": 220, "protein": 32, "sodium": 1600, "fiber": 8, "sugar": 4}},
    "pie crust": {"each": {"cal": 620, "fat": 39, "carbs": 60, "protein": 7, "sodium": 420, "fiber": 2, "sugar": 2}},
    "puff pastry": {"sheet": {"cal": 850, "fat": 56, "carbs": 72, "protein": 11, "sodium": 420, "fiber": 2, "sugar": 1}},
    "phyllo dough": {"sheet": {"cal": 57, "fat": 1, "carbs": 10, "protein": 1.4, "sodium": 92, "fiber": 0.4, "sugar": 0}},
    "wonton wrappers": {"each": {"cal": 23, "fat": 0.4, "carbs": 4.6, "protein": 0.8, "sodium": 46, "fiber": 0.2, "sugar": 0}},
    "egg roll wrappers": {"each": {"cal": 93, "fat": 1.6, "carbs": 18, "protein": 3, "sodium": 183, "fiber": 0.6, "sugar": 0}},
    "tortilla chips": {"cup": {"cal": 200, "fat": 10, "carbs": 24, "protein": 2.5, "sodium": 170, "fiber": 2, "sugar": 0.5}},
    "croutons": {"cup": {"cal": 122, "fat": 2, "carbs": 22, "protein": 4, "sodium": 210, "fiber": 1.5, "sugar": 1}},

    # =========================================================================
    # GAP ANALYSIS - ROUND 3 (most common missing ingredients)
    # =========================================================================

    # Syrups & sweeteners
    "light corn syrup": {"cup": {"cal": 925, "fat": 0, "carbs": 251, "protein": 0, "sodium": 395, "fiber": 0, "sugar": 251}},
    "dark corn syrup": {"cup": {"cal": 925, "fat": 0, "carbs": 251, "protein": 0, "sodium": 210, "fiber": 0, "sugar": 251}},
    "superfine sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200}},
    "caster sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200}},
    "raw sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200}},
    "turbinado sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200}},
    "demerara sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200}},
    "muscovado sugar": {"cup": {"cal": 760, "fat": 0, "carbs": 196, "protein": 0, "sodium": 6, "fiber": 0, "sugar": 196}},

    # Dried fruits
    "currants": {"cup": {"cal": 408, "fat": 0.4, "carbs": 107, "protein": 6, "sodium": 12, "fiber": 10, "sugar": 93}},
    "dried currants": {"cup": {"cal": 408, "fat": 0.4, "carbs": 107, "protein": 6, "sodium": 12, "fiber": 10, "sugar": 93}},
    "citron": {"cup": {"cal": 320, "fat": 0.3, "carbs": 82, "protein": 0.5, "sodium": 290, "fiber": 5, "sugar": 73}},
    "candied citron": {"cup": {"cal": 320, "fat": 0.3, "carbs": 82, "protein": 0.5, "sodium": 290, "fiber": 5, "sugar": 73}},
    "maraschino cherries": {"each": {"cal": 8, "fat": 0, "carbs": 2, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 2}},
    "candied cherries": {"cup": {"cal": 160, "fat": 0, "carbs": 40, "protein": 0, "sodium": 30, "fiber": 0, "sugar": 36}},

    # Condiments & sauces
    "catsup": {"tbsp": {"cal": 17, "fat": 0, "carbs": 4.5, "protein": 0.2, "sodium": 154, "fiber": 0, "sugar": 3.5}},
    "ketchup": {"tbsp": {"cal": 17, "fat": 0, "carbs": 4.5, "protein": 0.2, "sodium": 154, "fiber": 0, "sugar": 3.5}},
    "dijon mustard": {"tbsp": {"cal": 15, "fat": 1, "carbs": 1, "protein": 1, "sodium": 360, "fiber": 0.5, "sugar": 0}},
    "prepared mustard": {"tbsp": {"cal": 10, "fat": 0.6, "carbs": 0.8, "protein": 0.6, "sodium": 168, "fiber": 0.4, "sugar": 0.3}},
    "yellow mustard": {"tbsp": {"cal": 10, "fat": 0.6, "carbs": 0.8, "protein": 0.6, "sodium": 168, "fiber": 0.4, "sugar": 0.3}},
    "stone ground mustard": {"tbsp": {"cal": 15, "fat": 1, "carbs": 1, "protein": 1, "sodium": 200, "fiber": 0.5, "sugar": 0}},
    "salad dressing": {"tbsp": {"cal": 60, "fat": 5, "carbs": 3, "protein": 0, "sodium": 160, "fiber": 0, "sugar": 2}},
    "thousand island dressing": {"tbsp": {"cal": 59, "fat": 5.6, "carbs": 2.4, "protein": 0.1, "sodium": 138, "fiber": 0, "sugar": 2}},
    "ranch dressing": {"tbsp": {"cal": 73, "fat": 7.7, "carbs": 0.5, "protein": 0.1, "sodium": 122, "fiber": 0, "sugar": 0.4}},
    "blue cheese dressing": {"tbsp": {"cal": 77, "fat": 8, "carbs": 0.6, "protein": 0.4, "sodium": 167, "fiber": 0, "sugar": 0.5}},
    "italian dressing": {"tbsp": {"cal": 35, "fat": 3, "carbs": 1.5, "protein": 0, "sodium": 146, "fiber": 0, "sugar": 1}},
    "sweet pickle": {"each": {"cal": 32, "fat": 0, "carbs": 9, "protein": 0.1, "sodium": 160, "fiber": 0.3, "sugar": 7}},
    "sweet pickle relish": {"tbsp": {"cal": 20, "fat": 0.1, "carbs": 5, "protein": 0.1, "sodium": 122, "fiber": 0.2, "sugar": 4}},
    "dill pickle relish": {"tbsp": {"cal": 4, "fat": 0.1, "carbs": 1, "protein": 0, "sodium": 210, "fiber": 0.2, "sugar": 0.5}},

    # Vegetables
    "pimiento": {"oz": {"cal": 6, "fat": 0.1, "carbs": 1.3, "protein": 0.2, "sodium": 4, "fiber": 0.4, "sugar": 0.8},
                "tbsp": {"cal": 3, "fat": 0, "carbs": 0.6, "protein": 0.1, "sodium": 2, "fiber": 0.2, "sugar": 0.4},
                "": {"cal": 6, "fat": 0.1, "carbs": 1.3, "protein": 0.2, "sodium": 4, "fiber": 0.4, "sugar": 0.8}},
    "pimentos": {"oz": {"cal": 6, "fat": 0.1, "carbs": 1.3, "protein": 0.2, "sodium": 4, "fiber": 0.4, "sugar": 0.8},
                "": {"cal": 6, "fat": 0.1, "carbs": 1.3, "protein": 0.2, "sodium": 4, "fiber": 0.4, "sugar": 0.8}},
    "water chestnuts": {"can": {"cal": 66, "fat": 0.1, "carbs": 15, "protein": 1, "sodium": 11, "fiber": 2, "sugar": 3},
                       "cup": {"cal": 60, "fat": 0.1, "carbs": 13, "protein": 1, "sodium": 10, "fiber": 2, "sugar": 3}},
    "jicama": {"cup": {"cal": 46, "fat": 0.1, "carbs": 11, "protein": 0.9, "sodium": 5, "fiber": 6, "sugar": 2}},
    "mango": {"cup": {"cal": 99, "fat": 0.6, "carbs": 25, "protein": 1.4, "sodium": 2, "fiber": 2.6, "sugar": 23},
             "": {"cal": 135, "fat": 0.8, "carbs": 35, "protein": 1.9, "sodium": 3, "fiber": 3.7, "sugar": 31}},
    "green peppers": {"cup": {"cal": 30, "fat": 0.3, "carbs": 7, "protein": 1.3, "sodium": 4, "fiber": 2.5, "sugar": 4}},
    "red peppers": {"cup": {"cal": 39, "fat": 0.4, "carbs": 9, "protein": 1.5, "sodium": 6, "fiber": 3, "sugar": 6}},
    "apples": {"each": {"cal": 95, "fat": 0.3, "carbs": 25, "protein": 0.5, "sodium": 2, "fiber": 4.4, "sugar": 19},
               "cup": {"cal": 65, "fat": 0.2, "carbs": 17, "protein": 0.3, "sodium": 1, "fiber": 3, "sugar": 13}},
    "apple": {"each": {"cal": 95, "fat": 0.3, "carbs": 25, "protein": 0.5, "sodium": 2, "fiber": 4.4, "sugar": 19},
              "cup": {"cal": 65, "fat": 0.2, "carbs": 17, "protein": 0.3, "sodium": 1, "fiber": 3, "sugar": 13},
              "large": {"cal": 116, "fat": 0.4, "carbs": 31, "protein": 0.6, "sodium": 2, "fiber": 5.4, "sugar": 23},
              "medium": {"cal": 95, "fat": 0.3, "carbs": 25, "protein": 0.5, "sodium": 2, "fiber": 4.4, "sugar": 19},
              "small": {"cal": 77, "fat": 0.2, "carbs": 20, "protein": 0.4, "sodium": 1, "fiber": 3.6, "sugar": 15},
              "": {"cal": 95, "fat": 0.3, "carbs": 25, "protein": 0.5, "sodium": 2, "fiber": 4.4, "sugar": 19}},
    "bananas": {"each": {"cal": 105, "fat": 0.4, "carbs": 27, "protein": 1.3, "sodium": 1, "fiber": 3.1, "sugar": 14},
                "large": {"cal": 121, "fat": 0.5, "carbs": 31, "protein": 1.5, "sodium": 1, "fiber": 3.5, "sugar": 17},
                "medium": {"cal": 105, "fat": 0.4, "carbs": 27, "protein": 1.3, "sodium": 1, "fiber": 3.1, "sugar": 14},
                "small": {"cal": 90, "fat": 0.3, "carbs": 23, "protein": 1.1, "sodium": 1, "fiber": 2.6, "sugar": 12}},
    "banana": {"each": {"cal": 105, "fat": 0.4, "carbs": 27, "protein": 1.3, "sodium": 1, "fiber": 3.1, "sugar": 14},
               "large": {"cal": 121, "fat": 0.5, "carbs": 31, "protein": 1.5, "sodium": 1, "fiber": 3.5, "sugar": 17},
               "medium": {"cal": 105, "fat": 0.4, "carbs": 27, "protein": 1.3, "sodium": 1, "fiber": 3.1, "sugar": 14},
               "small": {"cal": 90, "fat": 0.3, "carbs": 23, "protein": 1.1, "sodium": 1, "fiber": 2.6, "sugar": 12},
               "cup": {"cal": 134, "fat": 0.5, "carbs": 34, "protein": 1.6, "sodium": 2, "fiber": 3.9, "sugar": 18}},
    "peaches": {"each": {"cal": 59, "fat": 0.4, "carbs": 14, "protein": 1.4, "sodium": 0, "fiber": 2.3, "sugar": 13},
                "large": {"cal": 68, "fat": 0.4, "carbs": 17, "protein": 1.6, "sodium": 0, "fiber": 2.6, "sugar": 15},
                "medium": {"cal": 59, "fat": 0.4, "carbs": 14, "protein": 1.4, "sodium": 0, "fiber": 2.3, "sugar": 13},
                "cup": {"cal": 60, "fat": 0.4, "carbs": 15, "protein": 1.4, "sodium": 0, "fiber": 2.3, "sugar": 13},
                "": {"cal": 59, "fat": 0.4, "carbs": 14, "protein": 1.4, "sodium": 0, "fiber": 2.3, "sugar": 13}},
    "peach": {"each": {"cal": 59, "fat": 0.4, "carbs": 14, "protein": 1.4, "sodium": 0, "fiber": 2.3, "sugar": 13},
              "large": {"cal": 68, "fat": 0.4, "carbs": 17, "protein": 1.6, "sodium": 0, "fiber": 2.6, "sugar": 15},
              "medium": {"cal": 59, "fat": 0.4, "carbs": 14, "protein": 1.4, "sodium": 0, "fiber": 2.3, "sugar": 13}},

    # Dairy & cream
    "light cream": {"cup": {"cal": 468, "fat": 46, "carbs": 9, "protein": 6, "sodium": 95, "fiber": 0, "sugar": 9}},
    "coffee cream": {"cup": {"cal": 468, "fat": 46, "carbs": 9, "protein": 6, "sodium": 95, "fiber": 0, "sugar": 9}},
    "table cream": {"cup": {"cal": 468, "fat": 46, "carbs": 9, "protein": 6, "sodium": 95, "fiber": 0, "sugar": 9}},
    "sour milk": {"cup": {"cal": 98, "fat": 2.4, "carbs": 12, "protein": 8, "sodium": 257, "fiber": 0, "sugar": 12}},
    "buttermilk powder": {"tbsp": {"cal": 25, "fat": 0.4, "carbs": 3, "protein": 2, "sodium": 34, "fiber": 0, "sugar": 3}},
    "rich milk": {"cup": {"cal": 150, "fat": 8, "carbs": 12, "protein": 8, "sodium": 105, "fiber": 0, "sugar": 12}},
    "plain yogurt": {"cup": {"cal": 149, "fat": 8, "carbs": 11, "protein": 9, "sodium": 113, "fiber": 0, "sugar": 11}},
    "greek yogurt": {"cup": {"cal": 190, "fat": 10, "carbs": 8, "protein": 18, "sodium": 65, "fiber": 0, "sugar": 7}},

    # Cheese variations
    "sharp cheddar cheese": {"cup": {"cal": 455, "fat": 37, "carbs": 1.4, "protein": 28, "sodium": 701, "fiber": 0, "sugar": 0.5}},
    "mild cheddar cheese": {"cup": {"cal": 455, "fat": 37, "carbs": 1.4, "protein": 28, "sodium": 621, "fiber": 0, "sugar": 0.5}},
    "monterey jack cheese": {"cup": {"cal": 421, "fat": 34, "carbs": 0.7, "protein": 28, "sodium": 603, "fiber": 0, "sugar": 0.5}},
    "pepper jack cheese": {"cup": {"cal": 421, "fat": 34, "carbs": 0.7, "protein": 28, "sodium": 650, "fiber": 0, "sugar": 0.5}},
    "colby cheese": {"cup": {"cal": 445, "fat": 36, "carbs": 2.9, "protein": 27, "sodium": 684, "fiber": 0, "sugar": 0.5}},
    "american cheese": {"slice": {"cal": 104, "fat": 9, "carbs": 0.5, "protein": 5, "sodium": 406, "fiber": 0, "sugar": 0.3}},
    "velveeta": {"oz": {"cal": 80, "fat": 6, "carbs": 3, "protein": 4, "sodium": 410, "fiber": 0, "sugar": 2}},

    # Spices & seasonings
    "cayenne": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.5, "sugar": 0.2}},
    "cayenne pepper": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.5, "sugar": 0.2}},
    "mace": {"tsp": {"cal": 8, "fat": 0.6, "carbs": 0.9, "protein": 0.1, "sodium": 1, "fiber": 0.3, "sugar": 0}},
    "ground mace": {"tsp": {"cal": 8, "fat": 0.6, "carbs": 0.9, "protein": 0.1, "sodium": 1, "fiber": 0.3, "sugar": 0}},
    "whole cloves": {"tsp": {"cal": 7, "fat": 0.4, "carbs": 1.3, "protein": 0.1, "sodium": 5, "fiber": 0.7, "sugar": 0.5}},
    "celery seed": {"tsp": {"cal": 8, "fat": 0.5, "carbs": 0.8, "protein": 0.4, "sodium": 3, "fiber": 0.2, "sugar": 0}},
    "celery salt": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 0.6, "protein": 0.3, "sodium": 1280, "fiber": 0.2, "sugar": 0}},
    "cinnamon stick": {"each": {"cal": 6, "fat": 0, "carbs": 2, "protein": 0.1, "sodium": 0, "fiber": 1.4, "sugar": 0}},
    "cinnamon sticks": {"each": {"cal": 6, "fat": 0, "carbs": 2, "protein": 0.1, "sodium": 0, "fiber": 1.4, "sugar": 0}},
    "red pepper flakes": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.5, "sugar": 0.2}},
    "crushed red pepper": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0.5, "sugar": 0.2}},
    "ground coriander": {"tsp": {"cal": 5, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.8, "sugar": 0}},
    "freshly grated nutmeg": {"tsp": {"cal": 12, "fat": 0.8, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.5, "sugar": 0.1}},
    "cream tartar": {"tsp": {"cal": 8, "fat": 0, "carbs": 1.8, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 0}},
    "cream of tartar": {"tsp": {"cal": 8, "fat": 0, "carbs": 1.8, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 0}},

    # Flavorings
    "rose water": {"tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "rose-water": {"tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "orange extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "lemon extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "almond extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "peppermint extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "rum extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "maple extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "coconut extract": {"tsp": {"cal": 12, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Flours & starches
    "pastry flour": {"cup": {"cal": 400, "fat": 1, "carbs": 84, "protein": 9, "sodium": 2, "fiber": 2, "sugar": 0}},
    "whole wheat pastry flour": {"cup": {"cal": 400, "fat": 2, "carbs": 80, "protein": 12, "sodium": 2, "fiber": 12, "sugar": 0}},
    "cake flour": {"cup": {"cal": 400, "fat": 1, "carbs": 85, "protein": 8, "sodium": 2, "fiber": 2, "sugar": 0}},
    "bread flour": {"cup": {"cal": 495, "fat": 1.5, "carbs": 99, "protein": 16, "sodium": 2, "fiber": 3.4, "sugar": 0.3},
                   "oz": {"cal": 110, "fat": 0.3, "carbs": 22, "protein": 3.6, "sodium": 0, "fiber": 0.8, "sugar": 0.1},
                   "g": {"cal": 3.9, "fat": 0.01, "carbs": 0.78, "protein": 0.13, "sodium": 0, "fiber": 0.03, "sugar": 0}},
    "self-rising flour": {"cup": {"cal": 443, "fat": 1.2, "carbs": 93, "protein": 12, "sodium": 1588, "fiber": 3, "sugar": 0}},
    "yellow cornmeal": {"cup": {"cal": 442, "fat": 4, "carbs": 94, "protein": 10, "sodium": 4, "fiber": 9, "sugar": 1}},
    "white cornmeal": {"cup": {"cal": 442, "fat": 4, "carbs": 94, "protein": 10, "sodium": 4, "fiber": 9, "sugar": 1}},
    "corn meal": {"cup": {"cal": 442, "fat": 4, "carbs": 94, "protein": 10, "sodium": 4, "fiber": 9, "sugar": 1}},
    "indian meal": {"cup": {"cal": 442, "fat": 4, "carbs": 94, "protein": 10, "sodium": 4, "fiber": 9, "sugar": 1}},
    "corn starch": {"tbsp": {"cal": 30, "fat": 0, "carbs": 7, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "tapioca starch": {"tbsp": {"cal": 30, "fat": 0, "carbs": 7, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "arrowroot": {"tbsp": {"cal": 29, "fat": 0, "carbs": 7, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0}},
    "dry bread crumbs": {"cup": {"cal": 427, "fat": 6, "carbs": 78, "protein": 14, "sodium": 791, "fiber": 5, "sugar": 6}},
    "panko": {"cup": {"cal": 220, "fat": 2, "carbs": 44, "protein": 6, "sodium": 300, "fiber": 2, "sugar": 2}},
    "panko bread crumbs": {"cup": {"cal": 220, "fat": 2, "carbs": 44, "protein": 6, "sodium": 300, "fiber": 2, "sugar": 2}},

    # Fats & oils
    "salad oil": {"tbsp": {"cal": 120, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "drippings": {"tbsp": {"cal": 115, "fat": 13, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "bacon drippings": {"tbsp": {"cal": 115, "fat": 13, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "bacon grease": {"tbsp": {"cal": 115, "fat": 13, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "fat": {"tbsp": {"cal": 115, "fat": 13, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "salt pork": {"oz": {"cal": 212, "fat": 23, "carbs": 0, "protein": 1.4, "sodium": 404, "fiber": 0, "sugar": 0}},
    "fatback": {"oz": {"cal": 212, "fat": 23, "carbs": 0, "protein": 1.4, "sodium": 404, "fiber": 0, "sugar": 0}},
    "suet": {"oz": {"cal": 242, "fat": 27, "carbs": 0, "protein": 0.4, "sodium": 2, "fiber": 0, "sugar": 0}},

    # Meats
    "chicken wings": {"lb": {"cal": 960, "fat": 68, "carbs": 0, "protein": 80, "sodium": 360, "fiber": 0, "sugar": 0}},
    "chicken wing": {"each": {"cal": 43, "fat": 3, "carbs": 0, "protein": 4, "sodium": 16, "fiber": 0, "sugar": 0}},
    "ground italian sausage": {"lb": {"cal": 1360, "fat": 112, "carbs": 4, "protein": 68, "sodium": 1500, "fiber": 0, "sugar": 0}},
    "italian sausage links": {"each": {"cal": 286, "fat": 23, "carbs": 1, "protein": 16, "sodium": 756, "fiber": 0, "sugar": 0}},
    "breakfast sausage": {"lb": {"cal": 1360, "fat": 112, "carbs": 0, "protein": 64, "sodium": 1400, "fiber": 0, "sugar": 0}},
    "polish sausage": {"lb": {"cal": 1280, "fat": 104, "carbs": 8, "protein": 68, "sodium": 2800, "fiber": 0, "sugar": 0}},
    "kielbasa": {"lb": {"cal": 1280, "fat": 104, "carbs": 8, "protein": 68, "sodium": 2800, "fiber": 0, "sugar": 0}},
    "andouille sausage": {"lb": {"cal": 1200, "fat": 96, "carbs": 8, "protein": 68, "sodium": 3200, "fiber": 0, "sugar": 0}},
    "chorizo": {"lb": {"cal": 1550, "fat": 132, "carbs": 8, "protein": 72, "sodium": 2700, "fiber": 0, "sugar": 0},
                "oz": {"cal": 97, "fat": 8, "carbs": 0.5, "protein": 4.5, "sodium": 169, "fiber": 0, "sugar": 0},
                "cup": {"cal": 387, "fat": 33, "carbs": 2, "protein": 18, "sodium": 675, "fiber": 0, "sugar": 0},
                "": {"cal": 97, "fat": 8, "carbs": 0.5, "protein": 4.5, "sodium": 169, "fiber": 0, "sugar": 0}},

    # Rice & grains
    "instant rice": {"cup": {"cal": 190, "fat": 0.4, "carbs": 42, "protein": 4, "sodium": 5, "fiber": 1, "sugar": 0}},
    "minute rice": {"cup": {"cal": 190, "fat": 0.4, "carbs": 42, "protein": 4, "sodium": 5, "fiber": 1, "sugar": 0}},
    "converted rice": {"cup": {"cal": 200, "fat": 0.5, "carbs": 44, "protein": 4, "sodium": 5, "fiber": 1, "sugar": 0}},
    "arborio rice": {"cup": {"cal": 200, "fat": 0.4, "carbs": 45, "protein": 4, "sodium": 0, "fiber": 1, "sugar": 0}},
    "jasmine rice": {"cup": {"cal": 205, "fat": 0.4, "carbs": 45, "protein": 4, "sodium": 2, "fiber": 0.6, "sugar": 0}},
    "basmati rice": {"cup": {"cal": 205, "fat": 0.4, "carbs": 45, "protein": 4, "sodium": 2, "fiber": 0.6, "sugar": 0}},
    "sushi rice": {"cup": {"cal": 200, "fat": 0.4, "carbs": 44, "protein": 4, "sodium": 0, "fiber": 0.6, "sugar": 0}},

    # Canned goods
    "tomato sauce": {"cup": {"cal": 59, "fat": 0.5, "carbs": 13, "protein": 2.6, "sodium": 1116, "fiber": 3, "sugar": 9}},
    "canned mushrooms": {"cup": {"cal": 33, "fat": 0.3, "carbs": 6, "protein": 2.5, "sodium": 561, "fiber": 2, "sugar": 2}},

    # Wine & alcohol
    "dry white wine": {"cup": {"cal": 194, "fat": 0, "carbs": 5, "protein": 0, "sodium": 10, "fiber": 0, "sugar": 1}},
    "dry sherry": {"cup": {"cal": 255, "fat": 0, "carbs": 10, "protein": 0, "sodium": 20, "fiber": 0, "sugar": 2}},
    "cooking sherry": {"cup": {"cal": 225, "fat": 0, "carbs": 8, "protein": 0, "sodium": 1100, "fiber": 0, "sugar": 4}},
    "marsala wine": {"cup": {"cal": 320, "fat": 0, "carbs": 28, "protein": 0, "sodium": 20, "fiber": 0, "sugar": 18}},
    "port wine": {"cup": {"cal": 370, "fat": 0, "carbs": 36, "protein": 0, "sodium": 20, "fiber": 0, "sugar": 30}},
    "madeira wine": {"cup": {"cal": 330, "fat": 0, "carbs": 32, "protein": 0, "sodium": 20, "fiber": 0, "sugar": 20}},
    "sake": {"cup": {"cal": 195, "fat": 0, "carbs": 7.5, "protein": 0.7, "sodium": 3, "fiber": 0, "sugar": 0}},

    # Chocolate & cocoa
    "semisweet chocolate": {"oz": {"cal": 136, "fat": 9, "carbs": 15, "protein": 1.2, "sodium": 2, "fiber": 1.8, "sugar": 13}},
    "bittersweet chocolate": {"oz": {"cal": 136, "fat": 9, "carbs": 13, "protein": 1.4, "sodium": 4, "fiber": 2, "sugar": 10}},
    "unsweetened chocolate": {"oz": {"cal": 145, "fat": 15, "carbs": 8, "protein": 3, "sodium": 4, "fiber": 5, "sugar": 0}},
    "baking chocolate": {"oz": {"cal": 145, "fat": 15, "carbs": 8, "protein": 3, "sodium": 4, "fiber": 5, "sugar": 0}},
    "white chocolate": {"oz": {"cal": 153, "fat": 9, "carbs": 17, "protein": 1.5, "sodium": 25, "fiber": 0, "sugar": 17}},
    "german chocolate": {"oz": {"cal": 140, "fat": 8, "carbs": 16, "protein": 1, "sodium": 5, "fiber": 1.5, "sugar": 14}},
    "dutch-process cocoa powder": {"tbsp": {"cal": 12, "fat": 0.7, "carbs": 3, "protein": 1, "sodium": 0, "fiber": 2, "sugar": 0}},
    "natural cocoa powder": {"tbsp": {"cal": 12, "fat": 0.7, "carbs": 3, "protein": 1, "sodium": 0, "fiber": 2, "sugar": 0}},

    # Miscellaneous
    "pistachio nuts": {"cup": {"cal": 685, "fat": 55, "carbs": 34, "protein": 25, "sodium": 1, "fiber": 13, "sugar": 9}},
    "slivered almonds": {"cup": {"cal": 624, "fat": 54, "carbs": 22, "protein": 23, "sodium": 1, "fiber": 12, "sugar": 5}},
    "sliced almonds": {"cup": {"cal": 530, "fat": 46, "carbs": 18, "protein": 20, "sodium": 1, "fiber": 10, "sugar": 4}},
    "almond meal": {"cup": {"cal": 640, "fat": 56, "carbs": 24, "protein": 24, "sodium": 0, "fiber": 14, "sugar": 5}},
    "lukewarm water": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "warm water": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "cider vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0.1}},
    "apple cider vinegar": {"tbsp": {"cal": 3, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 0.1}},
    "kitchen bouquet": {"tsp": {"cal": 15, "fat": 0, "carbs": 4, "protein": 0, "sodium": 10, "fiber": 0, "sugar": 3}},
    "truvia": {"packet": {"cal": 0, "fat": 0, "carbs": 3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "truvia natural sweetener": {"packet": {"cal": 0, "fat": 0, "carbs": 3, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "truvia natural sweetener spoonable": {"tsp": {"cal": 0, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "splenda": {"packet": {"cal": 0, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "stevia": {"packet": {"cal": 0, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # GAP ANALYSIS - ROUND 4 (remaining missing ingredients)
    # =========================================================================

    # Vegetables
    "sweet potatoes": {"lb": {"cal": 390, "fat": 0.4, "carbs": 90, "protein": 7, "sodium": 250, "fiber": 14, "sugar": 18}},
    "sweet potato": {"each": {"cal": 112, "fat": 0.1, "carbs": 26, "protein": 2, "sodium": 72, "fiber": 4, "sugar": 5}},
    "acorn squash": {"cup": {"cal": 56, "fat": 0.1, "carbs": 15, "protein": 1, "sodium": 4, "fiber": 2, "sugar": 0}},
    "butternut squash": {"cup": {"cal": 63, "fat": 0.1, "carbs": 16, "protein": 1.4, "sodium": 6, "fiber": 2.8, "sugar": 3}},
    "spaghetti squash": {"cup": {"cal": 31, "fat": 0.6, "carbs": 7, "protein": 0.6, "sodium": 17, "fiber": 1.5, "sugar": 2.5}},
    "button mushrooms": {"cup": {"cal": 15, "fat": 0.2, "carbs": 2.3, "protein": 2.2, "sodium": 4, "fiber": 0.7, "sugar": 1}},
    "black olives": {"cup": {"cal": 142, "fat": 13, "carbs": 8, "protein": 1, "sodium": 735, "fiber": 3, "sugar": 0}},
    "green olives": {"cup": {"cal": 145, "fat": 15, "carbs": 4, "protein": 1, "sodium": 1556, "fiber": 3, "sugar": 0}},
    "kalamata olives": {"cup": {"cal": 196, "fat": 17, "carbs": 10, "protein": 2, "sodium": 1840, "fiber": 3, "sugar": 0}},
    "plum tomato": {"each": {"cal": 11, "fat": 0.1, "carbs": 2.4, "protein": 0.5, "sodium": 3, "fiber": 0.7, "sugar": 1.6}},
    "stalk celery": {"each": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.3, "sodium": 32, "fiber": 0.6, "sugar": 0.6}},
    "celery stalks": {"each": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.3, "sodium": 32, "fiber": 0.6, "sugar": 0.6}},

    # Nuts & seeds
    "blanched almonds": {"cup": {"cal": 624, "fat": 54, "carbs": 22, "protein": 23, "sodium": 1, "fiber": 12, "sugar": 5}},
    "nut meats": {"cup": {"cal": 785, "fat": 79, "carbs": 16, "protein": 18, "sodium": 1, "fiber": 8, "sugar": 3}},
    "walnut meats": {"cup": {"cal": 785, "fat": 79, "carbs": 16, "protein": 18, "sodium": 1, "fiber": 8, "sugar": 3}},
    "fennel seeds": {"tsp": {"cal": 7, "fat": 0.3, "carbs": 1, "protein": 0.3, "sodium": 2, "fiber": 0.8, "sugar": 0}},
    "mustard seeds": {"tsp": {"cal": 15, "fat": 1, "carbs": 1, "protein": 0.8, "sodium": 0, "fiber": 0.4, "sugar": 0}},

    # Proteins
    "cooked chicken": {"cup": {"cal": 231, "fat": 5, "carbs": 0, "protein": 43, "sodium": 104, "fiber": 0, "sugar": 0}},
    "frying chicken": {"lb": {"cal": 960, "fat": 68, "carbs": 0, "protein": 80, "sodium": 360, "fiber": 0, "sugar": 0}},
    "smoked salmon": {"oz": {"cal": 33, "fat": 1.2, "carbs": 0, "protein": 5, "sodium": 222, "fiber": 0, "sugar": 0}},

    # Juices
    "pineapple juice": {"cup": {"cal": 132, "fat": 0.3, "carbs": 32, "protein": 0.9, "sodium": 5, "fiber": 0.5, "sugar": 25}},

    # Sauces
    "white sauce": {"cup": {"cal": 368, "fat": 27, "carbs": 23, "protein": 10, "sodium": 797, "fiber": 0.5, "sugar": 12}},
    "cream sauce": {"cup": {"cal": 368, "fat": 27, "carbs": 23, "protein": 10, "sodium": 797, "fiber": 0.5, "sugar": 12}},
    "cheese sauce": {"cup": {"cal": 470, "fat": 36, "carbs": 14, "protein": 24, "sodium": 1360, "fiber": 0.5, "sugar": 6}},
    "mushroom soup": {"cup": {"cal": 129, "fat": 9, "carbs": 9, "protein": 2.3, "sodium": 871, "fiber": 0.5, "sugar": 1.6}},

    # Breads & doughs
    "whole ciabatta": {"each": {"cal": 600, "fat": 4, "carbs": 120, "protein": 20, "sodium": 1200, "fiber": 4, "sugar": 4}},
    "pancake mix": {"cup": {"cal": 420, "fat": 4, "carbs": 84, "protein": 12, "sodium": 1400, "fiber": 3, "sugar": 12}},
    "macaroons": {"each": {"cal": 97, "fat": 4, "carbs": 14, "protein": 1, "sodium": 30, "fiber": 0.5, "sugar": 13}},

    # Flours
    "whole-wheat flour": {"cup": {"cal": 407, "fat": 2, "carbs": 87, "protein": 16, "sodium": 6, "fiber": 15, "sugar": 0}},
    "unsifted whole-wheat flour": {"cup": {"cal": 407, "fat": 2, "carbs": 87, "protein": 16, "sodium": 6, "fiber": 15, "sugar": 0}},

    # Dairy
    "sweet cream": {"cup": {"cal": 821, "fat": 88, "carbs": 7, "protein": 5, "sodium": 89, "fiber": 0, "sugar": 7}},
    "sweet milk": {"cup": {"cal": 149, "fat": 8, "carbs": 12, "protein": 8, "sodium": 105, "fiber": 0, "sugar": 12}},
    "sharp cheese": {"cup": {"cal": 455, "fat": 37, "carbs": 1.4, "protein": 28, "sodium": 701, "fiber": 0, "sugar": 0.5}},

    # Wine
    "dry red wine": {"cup": {"cal": 199, "fat": 0, "carbs": 6, "protein": 0, "sodium": 8, "fiber": 0, "sugar": 1}},
    "red wine": {"cup": {"cal": 199, "fat": 0, "carbs": 6, "protein": 0, "sodium": 8, "fiber": 0, "sugar": 1}},

    # Miscellaneous
    "basil leaves": {"cup": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.2, "sodium": 0, "fiber": 0.1, "sugar": 0}},
    "tortillas": {"each": {"cal": 150, "fat": 4, "carbs": 26, "protein": 4, "sodium": 340, "fiber": 2, "sugar": 1}},
    "unsweetened applesauce": {"cup": {"cal": 102, "fat": 0.2, "carbs": 28, "protein": 0.4, "sodium": 5, "fiber": 2.7, "sugar": 23}},
    "applesauce": {"cup": {"cal": 167, "fat": 0.4, "carbs": 43, "protein": 0.4, "sodium": 5, "fiber": 2.7, "sugar": 37}},
    "creamy peanut butter": {"tbsp": {"cal": 94, "fat": 8, "carbs": 3, "protein": 4, "sodium": 73, "fiber": 1, "sugar": 1.5}},
    "chunky peanut butter": {"tbsp": {"cal": 94, "fat": 8, "carbs": 3.5, "protein": 4, "sodium": 78, "fiber": 1, "sugar": 1}},
    "mustard powder": {"tsp": {"cal": 9, "fat": 0.6, "carbs": 0.6, "protein": 0.5, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "dry mustard": {"tsp": {"cal": 9, "fat": 0.6, "carbs": 0.6, "protein": 0.5, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "golden raisins": {"cup": {"cal": 434, "fat": 0.7, "carbs": 115, "protein": 5, "sodium": 17, "fiber": 5, "sugar": 86}},
    "apricot preserves": {"tbsp": {"cal": 50, "fat": 0, "carbs": 13, "protein": 0, "sodium": 8, "fiber": 0.2, "sugar": 11}},
    "apricot jam": {"tbsp": {"cal": 50, "fat": 0, "carbs": 13, "protein": 0, "sodium": 8, "fiber": 0.2, "sugar": 11}},
    "malted milk powder": {"tbsp": {"cal": 40, "fat": 0.5, "carbs": 7, "protein": 1.5, "sodium": 40, "fiber": 0, "sugar": 5}},
    "grated nutmeg": {"tsp": {"cal": 12, "fat": 0.8, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.5, "sugar": 0.1}},
    "tomato catsup": {"tbsp": {"cal": 17, "fat": 0, "carbs": 4.5, "protein": 0.2, "sodium": 154, "fiber": 0, "sugar": 3.5}},
    "gelatine": {"envelope": {"cal": 23, "fat": 0, "carbs": 0, "protein": 6, "sodium": 14, "fiber": 0, "sugar": 0}},

    # =========================================================================
    # GAP ANALYSIS - ROUND 5 (remaining missing ingredients)
    # =========================================================================

    # Vegetables
    "avocados": {"each": {"cal": 322, "fat": 29, "carbs": 17, "protein": 4, "sodium": 14, "fiber": 13, "sugar": 1}},
    "avocado": {"each": {"cal": 322, "fat": 29, "carbs": 17, "protein": 4, "sodium": 14, "fiber": 13, "sugar": 1},
               "": {"cal": 322, "fat": 29, "carbs": 17, "protein": 4, "sodium": 14, "fiber": 13, "sugar": 1},
               "cup": {"cal": 234, "fat": 21, "carbs": 12, "protein": 3, "sodium": 10, "fiber": 10, "sugar": 1}},
    "broccoli florets": {"cup": {"cal": 31, "fat": 0.3, "carbs": 6, "protein": 2.5, "sodium": 30, "fiber": 2.4, "sugar": 1.5}},
    "cucumbers": {"each": {"cal": 45, "fat": 0.3, "carbs": 11, "protein": 2, "sodium": 6, "fiber": 1.5, "sugar": 5}},
    "cucumber": {"each": {"cal": 45, "fat": 0.3, "carbs": 11, "protein": 2, "sodium": 6, "fiber": 1.5, "sugar": 5}},
    "baby spinach": {"cup": {"cal": 7, "fat": 0.1, "carbs": 1.1, "protein": 0.9, "sodium": 24, "fiber": 0.7, "sugar": 0.1}},
    "spring onions": {"each": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.3, "sodium": 2, "fiber": 0.4, "sugar": 0.4}},
    "rocket": {"cup": {"cal": 5, "fat": 0.1, "carbs": 0.7, "protein": 0.5, "sodium": 5, "fiber": 0.3, "sugar": 0.4},
               "": {"cal": 3, "fat": 0.05, "carbs": 0.4, "protein": 0.3, "sodium": 3, "fiber": 0.2, "sugar": 0.2}},
    "arugula": {"cup": {"cal": 5, "fat": 0.1, "carbs": 0.7, "protein": 0.5, "sodium": 5, "fiber": 0.3, "sugar": 0.4},
               "": {"cal": 3, "fat": 0.05, "carbs": 0.4, "protein": 0.3, "sodium": 3, "fiber": 0.2, "sugar": 0.2}},
    "mashed potatoes": {"cup": {"cal": 237, "fat": 9, "carbs": 35, "protein": 4, "sodium": 699, "fiber": 3, "sugar": 3}},
    "new potatoes": {"lb": {"cal": 350, "fat": 0.4, "carbs": 80, "protein": 9, "sodium": 25, "fiber": 8, "sugar": 4}},
    "small potatoes": {"each": {"cal": 130, "fat": 0.1, "carbs": 30, "protein": 3.5, "sodium": 8, "fiber": 3, "sugar": 1}},

    # Beans & legumes
    "cannellini beans": {"cup": {"cal": 225, "fat": 0.9, "carbs": 40, "protein": 15, "sodium": 4, "fiber": 11, "sugar": 0.6}},
    "white beans": {"cup": {"cal": 225, "fat": 0.9, "carbs": 40, "protein": 15, "sodium": 4, "fiber": 11, "sugar": 0.6}},
    "great northern beans": {"cup": {"cal": 209, "fat": 0.8, "carbs": 37, "protein": 15, "sodium": 4, "fiber": 12, "sugar": 0.6}},
    "pork & beans": {"cup": {"cal": 268, "fat": 4, "carbs": 51, "protein": 13, "sodium": 1047, "fiber": 14, "sugar": 16}},
    "soybeans": {"cup": {"cal": 298, "fat": 15, "carbs": 17, "protein": 29, "sodium": 1, "fiber": 10, "sugar": 6}},
    "edamame": {"cup": {"cal": 188, "fat": 8, "carbs": 14, "protein": 18, "sodium": 9, "fiber": 8, "sugar": 3}},

    # Meats
    "flank steak": {"lb": {"cal": 720, "fat": 32, "carbs": 0, "protein": 104, "sodium": 280, "fiber": 0, "sugar": 0}},
    "round beef": {"lb": {"cal": 680, "fat": 28, "carbs": 0, "protein": 100, "sodium": 260, "fiber": 0, "sugar": 0}},
    "streaky bacon": {"slice": {"cal": 43, "fat": 3.3, "carbs": 0.1, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0}},
    "bacon strips": {"slice": {"cal": 43, "fat": 3.3, "carbs": 0.1, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0}},
    "slices bacon": {"slice": {"cal": 43, "fat": 3.3, "carbs": 0.1, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0}},
    "strips bacon": {"slice": {"cal": 43, "fat": 3.3, "carbs": 0.1, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0}},
    "chopped cooked ham": {"cup": {"cal": 203, "fat": 8, "carbs": 2, "protein": 30, "sodium": 1684, "fiber": 0, "sugar": 0}},
    "chicken breast halves": {"each": {"cal": 284, "fat": 6, "carbs": 0, "protein": 53, "sodium": 104, "fiber": 0, "sugar": 0}},

    # Grains & pasta
    "white rice": {"cup": {"cal": 205, "fat": 0.4, "carbs": 45, "protein": 4, "sodium": 2, "fiber": 0.6, "sugar": 0}},
    "macaroni": {"cup": {"cal": 221, "fat": 1.3, "carbs": 43, "protein": 8, "sodium": 1, "fiber": 2.5, "sugar": 1}},
    "elbow macaroni": {"cup": {"cal": 221, "fat": 1.3, "carbs": 43, "protein": 8, "sodium": 1, "fiber": 2.5, "sugar": 1}},
    "soft bread crumbs": {"cup": {"cal": 120, "fat": 2, "carbs": 22, "protein": 4, "sodium": 200, "fiber": 1, "sugar": 2}},
    "wheat bread": {"slice": {"cal": 81, "fat": 1, "carbs": 15, "protein": 4, "sodium": 146, "fiber": 2, "sugar": 1}},
    "slices wheat bread": {"slice": {"cal": 81, "fat": 1, "carbs": 15, "protein": 4, "sodium": 146, "fiber": 2, "sugar": 1}},
    "ciabatta": {"each": {"cal": 200, "fat": 1.3, "carbs": 40, "protein": 7, "sodium": 400, "fiber": 1.5, "sugar": 1}},
    "muesli": {"cup": {"cal": 289, "fat": 4, "carbs": 66, "protein": 8, "sodium": 14, "fiber": 6, "sugar": 26}},
    "cornflakes": {"cup": {"cal": 101, "fat": 0.2, "carbs": 24, "protein": 2, "sodium": 203, "fiber": 0.7, "sugar": 3}},

    # Cheese
    "longhorn cheese": {"cup": {"cal": 455, "fat": 37, "carbs": 1.4, "protein": 28, "sodium": 701, "fiber": 0, "sugar": 0.5}},
    "muenster cheese": {"oz": {"cal": 104, "fat": 8.5, "carbs": 0.3, "protein": 7, "sodium": 178, "fiber": 0, "sugar": 0.3}},
    "sieved cottage cheese": {"cup": {"cal": 163, "fat": 2.3, "carbs": 6, "protein": 28, "sodium": 918, "fiber": 0, "sugar": 5}},

    # Condiments & sauces
    "chunky salsa": {"cup": {"cal": 70, "fat": 0.4, "carbs": 14, "protein": 3, "sodium": 1200, "fiber": 4, "sugar": 8},
                    "can": {"cal": 140, "fat": 0.8, "carbs": 28, "protein": 6, "sodium": 2400, "fiber": 8, "sugar": 16},
                    "oz": {"cal": 9, "fat": 0.1, "carbs": 2, "protein": 0.4, "sodium": 150, "fiber": 0.5, "sugar": 1}},
    "seasoning salt": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 1600, "fiber": 0, "sugar": 0}},
    "low-sodium soy sauce": {"tbsp": {"cal": 10, "fat": 0, "carbs": 1, "protein": 1, "sodium": 533, "fiber": 0, "sugar": 0}},
    "bottled minced garlic": {"tsp": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Spices
    "whole allspice": {"tsp": {"cal": 5, "fat": 0.2, "carbs": 1.4, "protein": 0.1, "sodium": 1, "fiber": 0.4, "sugar": 0}},
    "pumpkin pie spice": {"tsp": {"cal": 6, "fat": 0.2, "carbs": 1.2, "protein": 0.1, "sodium": 1, "fiber": 0.4, "sugar": 0}},
    "greek seasoning": {"tsp": {"cal": 5, "fat": 0.2, "carbs": 1, "protein": 0.2, "sodium": 5, "fiber": 0.3, "sugar": 0}},
    "sage leaves": {"each": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Alcohol
    "gin": {"oz": {"cal": 73, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "vodka": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "tequila": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "whiskey": {"oz": {"cal": 70, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "bourbon": {"oz": {"cal": 70, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "scotch": {"oz": {"cal": 70, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "cognac": {"oz": {"cal": 69, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "brandy": {"oz": {"cal": 69, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "triple sec": {"oz": {"cal": 103, "fat": 0, "carbs": 11, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 11}},
    "kahlua": {"oz": {"cal": 91, "fat": 0, "carbs": 14, "protein": 0, "sodium": 3, "fiber": 0, "sugar": 14}},
    "amaretto": {"oz": {"cal": 110, "fat": 0, "carbs": 17, "protein": 0, "sodium": 3, "fiber": 0, "sugar": 17}},
    "grand marnier": {"oz": {"cal": 76, "fat": 0, "carbs": 7, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 7}},

    # Gelatin flavors
    "lemon-flavored gelatin": {"package": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "strawberry gelatin": {"package": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "lime gelatin": {"package": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "orange gelatin": {"package": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "cherry gelatin": {"package": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},

    # Fruits
    "grapefruits": {"each": {"cal": 103, "fat": 0.3, "carbs": 26, "protein": 2, "sodium": 0, "fiber": 4, "sugar": 17}},
    "grapefruit": {"each": {"cal": 103, "fat": 0.3, "carbs": 26, "protein": 2, "sodium": 0, "fiber": 4, "sugar": 17}},
    "large apple": {"each": {"cal": 116, "fat": 0.4, "carbs": 31, "protein": 0.6, "sodium": 2, "fiber": 5.4, "sugar": 23}},
    "large bananas": {"each": {"cal": 121, "fat": 0.4, "carbs": 31, "protein": 1.5, "sodium": 1, "fiber": 3.5, "sugar": 17}},
    "large mangos": {"each": {"cal": 202, "fat": 1.3, "carbs": 50, "protein": 2.8, "sodium": 3, "fiber": 5.4, "sugar": 45}},

    # Yogurt flavors
    "plain nonfat yoghurt": {"cup": {"cal": 137, "fat": 0.4, "carbs": 19, "protein": 14, "sodium": 189, "fiber": 0, "sugar": 19}},
    "banana-flavored yogurt": {"cup": {"cal": 193, "fat": 2.8, "carbs": 36, "protein": 11, "sodium": 148, "fiber": 0, "sugar": 33}},
    "mango flavored yogurt": {"cup": {"cal": 193, "fat": 2.8, "carbs": 36, "protein": 11, "sodium": 148, "fiber": 0, "sugar": 33}},

    # Chiles & peppers
    "whole green chiles": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 680, "fiber": 2, "sugar": 3}},
    "green chiles": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 680, "fiber": 2, "sugar": 3}},
    "diced green chiles": {"can": {"cal": 30, "fat": 0, "carbs": 6, "protein": 1, "sodium": 680, "fiber": 2, "sugar": 3}},

    # Seeds
    "linseeds": {"tbsp": {"cal": 55, "fat": 4.3, "carbs": 3, "protein": 2, "sodium": 3, "fiber": 2.8, "sugar": 0.2}},
    "flaxseeds": {"tbsp": {"cal": 55, "fat": 4.3, "carbs": 3, "protein": 2, "sodium": 3, "fiber": 2.8, "sugar": 0.2}},
    "flax seeds": {"tbsp": {"cal": 55, "fat": 4.3, "carbs": 3, "protein": 2, "sodium": 3, "fiber": 2.8, "sugar": 0.2}},

    # Historical/vintage ingredients (for old cookbooks)
    "pearl ash": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "saleratus": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 629, "fiber": 0, "sugar": 0}},
    "emptins": {"cup": {"cal": 30, "fat": 1, "carbs": 4, "protein": 2, "sodium": 10, "fiber": 1, "sugar": 0}},

    # Misc
    "thick cream": {"cup": {"cal": 821, "fat": 88, "carbs": 7, "protein": 5, "sodium": 89, "fiber": 0, "sugar": 7}},
    "truffles": {"oz": {"cal": 84, "fat": 9, "carbs": 2, "protein": 1, "sodium": 15, "fiber": 0, "sugar": 0}},
    "minced parsley": {"tbsp": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0.1, "sodium": 2, "fiber": 0.1, "sugar": 0}},

    # =========================================================================
    # GAP ANALYSIS - ROUND 6 (final pass)
    # =========================================================================

    # Meats & sausages
    "pork sausage": {"lb": {"cal": 1360, "fat": 112, "carbs": 0, "protein": 64, "sodium": 1400, "fiber": 0, "sugar": 0}},
    "pork sausage links": {"each": {"cal": 80, "fat": 7, "carbs": 0, "protein": 4, "sodium": 200, "fiber": 0, "sugar": 0}},
    "stewing beef": {"lb": {"cal": 800, "fat": 48, "carbs": 0, "protein": 88, "sodium": 280, "fiber": 0, "sugar": 0}},

    # Chocolate & chips
    "milk chocolate": {"oz": {"cal": 153, "fat": 8, "carbs": 17, "protein": 2, "sodium": 23, "fiber": 0.8, "sugar": 15}},
    "milk chocolate chips": {"cup": {"cal": 840, "fat": 48, "carbs": 92, "protein": 10, "sodium": 128, "fiber": 4, "sugar": 84}},
    "peanut butter chips": {"cup": {"cal": 800, "fat": 48, "carbs": 80, "protein": 16, "sodium": 320, "fiber": 2, "sugar": 72}},
    "butterscotch chips": {"cup": {"cal": 800, "fat": 40, "carbs": 100, "protein": 2, "sodium": 300, "fiber": 0, "sugar": 92}},
    "squares unsweetened chocolate": {"each": {"cal": 145, "fat": 15, "carbs": 8, "protein": 3, "sodium": 4, "fiber": 5, "sugar": 0}},

    # Nuts
    "black walnuts": {"cup": {"cal": 760, "fat": 71, "carbs": 12, "protein": 30, "sodium": 2, "fiber": 6, "sugar": 1}},
    "chopped walnuts": {"cup": {"cal": 785, "fat": 79, "carbs": 16, "protein": 18, "sodium": 1, "fiber": 8, "sugar": 3}},
    "broken pecans": {"cup": {"cal": 753, "fat": 78, "carbs": 15, "protein": 10, "sodium": 0, "fiber": 10, "sugar": 4}},
    "cut-up nuts": {"cup": {"cal": 785, "fat": 79, "carbs": 16, "protein": 18, "sodium": 1, "fiber": 8, "sugar": 3}},

    # Dried fruits
    "cut-up raisins": {"cup": {"cal": 434, "fat": 0.5, "carbs": 115, "protein": 5, "sodium": 18, "fiber": 6, "sugar": 86}},
    "cut-up dates": {"cup": {"cal": 415, "fat": 0.6, "carbs": 110, "protein": 4, "sodium": 3, "fiber": 12, "sugar": 93}},
    "eeded raisins": {"cup": {"cal": 434, "fat": 0.5, "carbs": 115, "protein": 5, "sodium": 18, "fiber": 6, "sugar": 86}},

    # Coconut variants
    "sweetened shredded coconut": {"cup": {"cal": 466, "fat": 33, "carbs": 44, "protein": 3, "sodium": 244, "fiber": 4, "sugar": 40}},
    "cocoanut": {"cup": {"cal": 283, "fat": 27, "carbs": 12, "protein": 3, "sodium": 16, "fiber": 7, "sugar": 5}},

    # Spreads & condiments
    "apple butter": {"tbsp": {"cal": 29, "fat": 0.1, "carbs": 7, "protein": 0.1, "sodium": 1, "fiber": 0.3, "sugar": 6}},
    "spicy salsa": {"cup": {"cal": 70, "fat": 0.4, "carbs": 14, "protein": 3, "sodium": 1400, "fiber": 4, "sugar": 8}},

    # Seeds & spices
    "mustard seed": {"tsp": {"cal": 15, "fat": 1, "carbs": 1, "protein": 0.8, "sodium": 0, "fiber": 0.4, "sugar": 0}},
    "caraway seeds": {"tsp": {"cal": 7, "fat": 0.3, "carbs": 1, "protein": 0.4, "sodium": 0, "fiber": 0.8, "sugar": 0}},
    "caraway seed": {"tsp": {"cal": 7, "fat": 0.3, "carbs": 1, "protein": 0.4, "sodium": 0, "fiber": 0.8, "sugar": 0}},
    "coriander seed": {"tsp": {"cal": 5, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.8, "sugar": 0}},
    "spice": {"tsp": {"cal": 6, "fat": 0.2, "carbs": 1, "protein": 0.1, "sodium": 1, "fiber": 0.5, "sugar": 0}},
    "mild chili powder": {"tsp": {"cal": 8, "fat": 0.4, "carbs": 1.4, "protein": 0.3, "sodium": 26, "fiber": 0.9, "sugar": 0.2}},

    # Dairy
    "eggnog": {"cup": {"cal": 343, "fat": 19, "carbs": 34, "protein": 10, "sodium": 137, "fiber": 0, "sugar": 34}},
    "coconut custard": {"cup": {"cal": 280, "fat": 14, "carbs": 32, "protein": 8, "sodium": 180, "fiber": 1, "sugar": 28}},
    "milk or cream": {"cup": {"cal": 150, "fat": 8, "carbs": 12, "protein": 8, "sodium": 105, "fiber": 0, "sugar": 12}},
    "lukewarm milk": {"cup": {"cal": 149, "fat": 8, "carbs": 12, "protein": 8, "sodium": 105, "fiber": 0, "sugar": 12}},

    # Flour variants
    "buckwheat flour": {"cup": {"cal": 402, "fat": 4, "carbs": 85, "protein": 15, "sodium": 13, "fiber": 12, "sugar": 3}},

    # Apples
    "tart apples": {"each": {"cal": 80, "fat": 0.3, "carbs": 21, "protein": 0.4, "sodium": 1, "fiber": 4, "sugar": 15}},
    "tart cooking apples": {"each": {"cal": 80, "fat": 0.3, "carbs": 21, "protein": 0.4, "sodium": 1, "fiber": 4, "sugar": 15}},

    # Yeast variants
    "yeast cake": {"each": {"cal": 10, "fat": 0.1, "carbs": 1.5, "protein": 1.3, "sodium": 4, "fiber": 0.8, "sugar": 0}},
    "cake yeast": {"each": {"cal": 10, "fat": 0.1, "carbs": 1.5, "protein": 1.3, "sodium": 4, "fiber": 0.8, "sugar": 0}},
    "granulated yeast": {"tsp": {"cal": 8, "fat": 0.1, "carbs": 1, "protein": 1, "sodium": 2, "fiber": 0.5, "sugar": 0}},

    # Canned goods
    "can tomato soup": {"can": {"cal": 161, "fat": 2.4, "carbs": 33, "protein": 4, "sodium": 1710, "fiber": 1.6, "sugar": 20}},
    "strained tomato": {"cup": {"cal": 41, "fat": 0.3, "carbs": 9, "protein": 2, "sodium": 800, "fiber": 2, "sugar": 7}},

    # Cereals
    "kellogg's rice krispies cereal": {"cup": {"cal": 96, "fat": 0.3, "carbs": 23, "protein": 2, "sodium": 190, "fiber": 0.3, "sugar": 3}},
    "rice krispies": {"cup": {"cal": 96, "fat": 0.3, "carbs": 23, "protein": 2, "sodium": 190, "fiber": 0.3, "sugar": 3}},

    # Vegetables
    "shelled peas": {"cup": {"cal": 117, "fat": 0.6, "carbs": 21, "protein": 8, "sodium": 7, "fiber": 7, "sugar": 8}},
    "one carrot": {"each": {"cal": 25, "fat": 0.1, "carbs": 6, "protein": 0.6, "sodium": 42, "fiber": 1.7, "sugar": 3}},

    # Misc prepared
    "stove top stuffing": {"cup": {"cal": 177, "fat": 9, "carbs": 21, "protein": 4, "sodium": 522, "fiber": 1, "sugar": 3}},
    "fine sugar": {"cup": {"cal": 774, "fat": 0, "carbs": 200, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 200}},

    # =========================================================================
    # GAP ANALYSIS - ROUND 7 (final cleanup)
    # =========================================================================

    # Herbs & leaves
    "mint leaves": {"tbsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0.1, "sodium": 1, "fiber": 0, "sugar": 0}},
    "oregano leaves": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.7, "protein": 0.1, "sodium": 0, "fiber": 0.4, "sugar": 0}},
    "thyme sprigs": {"each": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "fresh oregano": {"tbsp": {"cal": 3, "fat": 0.1, "carbs": 0.5, "protein": 0.1, "sodium": 0, "fiber": 0.3, "sugar": 0}},

    # Spices & seasonings
    "ground red pepper": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.5, "sugar": 0.2}},
    "garam masala": {"tsp": {"cal": 7, "fat": 0.3, "carbs": 1.3, "protein": 0.2, "sodium": 2, "fiber": 0.5, "sugar": 0.1}},
    "turmeric powder": {"tsp": {"cal": 8, "fat": 0.2, "carbs": 1.4, "protein": 0.3, "sodium": 1, "fiber": 0.5, "sugar": 0.1}},
    "turmeric": {"tsp": {"cal": 8, "fat": 0.2, "carbs": 1.4, "protein": 0.3, "sodium": 1, "fiber": 0.5, "sugar": 0.1}},
    "powdered thyme": {"tsp": {"cal": 4, "fat": 0.1, "carbs": 0.9, "protein": 0.1, "sodium": 1, "fiber": 0.5, "sugar": 0}},
    "black peppercorns": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.4, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "peppercorns": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.4, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "alum": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 0}},

    # Nuts & seeds
    "pecan meats": {"cup": {"cal": 753, "fat": 78, "carbs": 15, "protein": 10, "sodium": 0, "fiber": 10, "sugar": 4}},
    "cashew nuts": {"cup": {"cal": 786, "fat": 63, "carbs": 45, "protein": 21, "sodium": 16, "fiber": 4, "sugar": 6}},
    "cashews": {"cup": {"cal": 786, "fat": 63, "carbs": 45, "protein": 21, "sodium": 16, "fiber": 4, "sugar": 6}},

    # Peppers
    "serrano chile": {"each": {"cal": 2, "fat": 0, "carbs": 0.4, "protein": 0.1, "sodium": 1, "fiber": 0.2, "sugar": 0.2}},
    "poblano pepper": {"each": {"cal": 48, "fat": 0.5, "carbs": 9, "protein": 2, "sodium": 6, "fiber": 4, "sugar": 5}},
    "poblano": {"each": {"cal": 48, "fat": 0.5, "carbs": 9, "protein": 2, "sodium": 6, "fiber": 4, "sugar": 5}},

    # Vegetables
    "yellow squash": {"cup": {"cal": 18, "fat": 0.2, "carbs": 4, "protein": 1, "sodium": 2, "fiber": 1, "sugar": 2}},
    "sliced cucumber": {"cup": {"cal": 14, "fat": 0.1, "carbs": 3, "protein": 0.6, "sodium": 2, "fiber": 0.5, "sugar": 1.5}},
    "corn kernels": {"cup": {"cal": 132, "fat": 1.8, "carbs": 29, "protein": 5, "sodium": 23, "fiber": 4, "sugar": 5}},
    "one leek": {"each": {"cal": 54, "fat": 0.3, "carbs": 13, "protein": 1.3, "sodium": 18, "fiber": 1.6, "sugar": 3.5}},
    "celery stalk": {"each": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.3, "sodium": 32, "fiber": 0.6, "sugar": 0.6}},
    "stalks celery": {"each": {"cal": 6, "fat": 0.1, "carbs": 1, "protein": 0.3, "sodium": 32, "fiber": 0.6, "sugar": 0.6}},
    "capers": {"tbsp": {"cal": 2, "fat": 0, "carbs": 0.4, "protein": 0.2, "sodium": 255, "fiber": 0.3, "sugar": 0}},
    "guacamole": {"cup": {"cal": 368, "fat": 32, "carbs": 20, "protein": 4, "sodium": 700, "fiber": 14, "sugar": 2}},

    # Beans
    "red kidney beans": {"cup": {"cal": 225, "fat": 0.9, "carbs": 40, "protein": 15, "sodium": 2, "fiber": 11, "sugar": 0.6}},
    "chili beans": {"cup": {"cal": 286, "fat": 2.6, "carbs": 52, "protein": 17, "sodium": 920, "fiber": 18, "sugar": 6}},

    # Cheese
    "asiago cheese": {"oz": {"cal": 111, "fat": 9, "carbs": 1, "protein": 7, "sodium": 340, "fiber": 0, "sugar": 0.5}},
    "parmigiano-reggiano cheese": {"oz": {"cal": 111, "fat": 7, "carbs": 1, "protein": 10, "sodium": 330, "fiber": 0, "sugar": 0}},
    "mozzarella": {"cup": {"cal": 318, "fat": 22, "carbs": 3, "protein": 26, "sodium": 627, "fiber": 0, "sugar": 1},
                   "slice": {"cal": 78, "fat": 6, "carbs": 0.6, "protein": 6, "sodium": 178, "fiber": 0, "sugar": 0.2},
                   "piece": {"cal": 80, "fat": 6, "carbs": 1, "protein": 7, "sodium": 200, "fiber": 0, "sugar": 0},
                   "oz": {"cal": 85, "fat": 6, "carbs": 0.6, "protein": 6, "sodium": 176, "fiber": 0, "sugar": 0.3}},
    "cheese slices": {"slice": {"cal": 104, "fat": 9, "carbs": 0.5, "protein": 5, "sodium": 406, "fiber": 0, "sugar": 0.3}},

    # Dairy
    "crème fraîche": {"cup": {"cal": 440, "fat": 46, "carbs": 3, "protein": 4, "sodium": 40, "fiber": 0, "sugar": 3}},
    "creme fraiche": {"cup": {"cal": 440, "fat": 46, "carbs": 3, "protein": 4, "sodium": 40, "fiber": 0, "sugar": 3}},
    "full cream milk": {"cup": {"cal": 149, "fat": 8, "carbs": 12, "protein": 8, "sodium": 105, "fiber": 0, "sugar": 12}},
    "ice cubes": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Meats
    "ground turkey breast": {"lb": {"cal": 544, "fat": 8, "carbs": 0, "protein": 112, "sodium": 320, "fiber": 0, "sugar": 0}},
    "lean beef": {"lb": {"cal": 680, "fat": 28, "carbs": 0, "protein": 100, "sodium": 260, "fiber": 0, "sugar": 0}},
    "ham fat": {"oz": {"cal": 170, "fat": 18, "carbs": 0, "protein": 1.5, "sodium": 320, "fiber": 0, "sugar": 0}},

    # Juices & beverages
    "grapefruit juice": {"cup": {"cal": 96, "fat": 0.3, "carbs": 23, "protein": 1.2, "sodium": 2, "fiber": 0.2, "sugar": 20}},
    "strong hot coffee": {"cup": {"cal": 2, "fat": 0, "carbs": 0, "protein": 0.3, "sodium": 5, "fiber": 0, "sugar": 0}},
    "apricot nectar": {"cup": {"cal": 140, "fat": 0.2, "carbs": 36, "protein": 0.9, "sodium": 8, "fiber": 1.5, "sugar": 33}},
    "apple juice or cider": {"cup": {"cal": 114, "fat": 0.3, "carbs": 28, "protein": 0.2, "sodium": 10, "fiber": 0.2, "sugar": 24}},

    # Breads
    "baguette": {"each": {"cal": 680, "fat": 2, "carbs": 140, "protein": 24, "sodium": 1400, "fiber": 6, "sugar": 2}},

    # Oils
    "peanut oil": {"tbsp": {"cal": 119, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Condiments & canned
    "jellied cranberry sauce": {"cup": {"cal": 418, "fat": 0.4, "carbs": 108, "protein": 0.5, "sodium": 80, "fiber": 3, "sugar": 87}},
    "cranberry sauce": {"cup": {"cal": 418, "fat": 0.4, "carbs": 108, "protein": 0.5, "sodium": 80, "fiber": 3, "sugar": 87},
                       "can": {"cal": 418, "fat": 0.4, "carbs": 108, "protein": 0.5, "sodium": 80, "fiber": 3, "sugar": 87}},
    "tzatziki": {"cup": {"cal": 150, "fat": 10, "carbs": 10, "protein": 6, "sodium": 400, "fiber": 0.5, "sugar": 6}},
    "tzatziki sauce": {"cup": {"cal": 150, "fat": 10, "carbs": 10, "protein": 6, "sodium": 400, "fiber": 0.5, "sugar": 6}},
    "onion soup": {"can": {"cal": 140, "fat": 4, "carbs": 18, "protein": 5, "sodium": 2440, "fiber": 2, "sugar": 5}},
    "condensed french onion soup": {"can": {"cal": 140, "fat": 4, "carbs": 18, "protein": 5, "sodium": 2440, "fiber": 2, "sugar": 5}},
    "mushrooms canned": {"cup": {"cal": 33, "fat": 0.3, "carbs": 6, "protein": 2.5, "sodium": 561, "fiber": 2, "sugar": 2}},

    # Sweeteners
    "swerve sweetener": {"cup": {"cal": 0, "fat": 0, "carbs": 96, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},

    # Misc
    "large banana": {"each": {"cal": 121, "fat": 0.4, "carbs": 31, "protein": 1.5, "sodium": 1, "fiber": 3.5, "sugar": 17}},
    "frozen strawberries": {"cup": {"cal": 77, "fat": 0.2, "carbs": 20, "protein": 1, "sodium": 3, "fiber": 3.3, "sugar": 13}},

    # =========================================================================
    # BATCH 13: Additional missing ingredients
    # =========================================================================

    # Dips & spreads
    "hummus": {"cup": {"cal": 435, "fat": 21, "carbs": 50, "protein": 20, "sodium": 960, "fiber": 15, "sugar": 0},
              "oz": {"cal": 54, "fat": 2.6, "carbs": 6, "protein": 2.5, "sodium": 120, "fiber": 2, "sugar": 0},
              "tbsp": {"cal": 27, "fat": 1.3, "carbs": 3, "protein": 1.3, "sodium": 60, "fiber": 1, "sugar": 0},
              "container": {"cal": 864, "fat": 42, "carbs": 96, "protein": 40, "sodium": 1920, "fiber": 24, "sugar": 0}},
    "pita chips": {"cup": {"cal": 260, "fat": 10, "carbs": 36, "protein": 6, "sodium": 380, "fiber": 2, "sugar": 1},
                  "bag": {"cal": 780, "fat": 30, "carbs": 108, "protein": 18, "sodium": 1140, "fiber": 6, "sugar": 3},
                  "oz": {"cal": 130, "fat": 5, "carbs": 18, "protein": 3, "sodium": 190, "fiber": 1, "sugar": 0.5}},
    "tzatziki": {"cup": {"cal": 150, "fat": 10, "carbs": 10, "protein": 6, "sodium": 400, "fiber": 0.5, "sugar": 6}},

    # Meats
    "ground veal": {"lb": {"cal": 840, "fat": 40, "carbs": 0, "protein": 112, "sodium": 320, "fiber": 0, "sugar": 0},
                   "oz": {"cal": 53, "fat": 2.5, "carbs": 0, "protein": 7, "sodium": 20, "fiber": 0, "sugar": 0}},
    "veal": {"lb": {"cal": 840, "fat": 40, "carbs": 0, "protein": 112, "sodium": 320, "fiber": 0, "sugar": 0},
             "oz": {"cal": 53, "fat": 2.5, "carbs": 0, "protein": 7, "sodium": 20, "fiber": 0, "sugar": 0}},
    "skirt steak": {"lb": {"cal": 800, "fat": 48, "carbs": 0, "protein": 92, "sodium": 280, "fiber": 0, "sugar": 0},
                   "oz": {"cal": 50, "fat": 3, "carbs": 0, "protein": 5.8, "sodium": 18, "fiber": 0, "sugar": 0}},
    "beef heart": {"lb": {"cal": 560, "fat": 16, "carbs": 0, "protein": 96, "sodium": 400, "fiber": 0, "sugar": 0},
                  "oz": {"cal": 35, "fat": 1, "carbs": 0, "protein": 6, "sodium": 25, "fiber": 0, "sugar": 0}},
    "tripe": {"lb": {"cal": 400, "fat": 16, "carbs": 0, "protein": 60, "sodium": 180, "fiber": 0, "sugar": 0}},
    "honeycomb tripe": {"lb": {"cal": 400, "fat": 16, "carbs": 0, "protein": 60, "sodium": 180, "fiber": 0, "sugar": 0}},
    "veal knuckle": {"each": {"cal": 350, "fat": 12, "carbs": 0, "protein": 56, "sodium": 200, "fiber": 0, "sugar": 0}},

    # Cheese varieties
    "roquefort cheese": {"oz": {"cal": 105, "fat": 9, "carbs": 0.6, "protein": 6, "sodium": 513, "fiber": 0, "sugar": 0},
                        "cup": {"cal": 420, "fat": 36, "carbs": 2.4, "protein": 24, "sodium": 2052, "fiber": 0, "sugar": 0}},
    "cotija cheese": {"oz": {"cal": 106, "fat": 8, "carbs": 2, "protein": 7, "sodium": 350, "fiber": 0, "sugar": 0},
                     "cup": {"cal": 424, "fat": 32, "carbs": 8, "protein": 28, "sodium": 1400, "fiber": 0, "sugar": 0}},
    "queso cheese": {"cup": {"cal": 480, "fat": 36, "carbs": 8, "protein": 28, "sodium": 1200, "fiber": 0, "sugar": 2},
                    "oz": {"cal": 60, "fat": 4.5, "carbs": 1, "protein": 3.5, "sodium": 150, "fiber": 0, "sugar": 0.3}},
    "queso fresco": {"oz": {"cal": 80, "fat": 6, "carbs": 1, "protein": 5, "sodium": 180, "fiber": 0, "sugar": 0}},
    "daiya cheese": {"cup": {"cal": 240, "fat": 16, "carbs": 16, "protein": 0, "sodium": 640, "fiber": 0, "sugar": 0},
                    "oz": {"cal": 60, "fat": 4, "carbs": 4, "protein": 0, "sodium": 160, "fiber": 0, "sugar": 0}},
    "muenster cheese": {"slice": {"cal": 104, "fat": 8.5, "carbs": 0.3, "protein": 6.6, "sodium": 178, "fiber": 0, "sugar": 0.1},
                       "oz": {"cal": 104, "fat": 8.5, "carbs": 0.3, "protein": 6.6, "sodium": 178, "fiber": 0, "sugar": 0.1}},
    "gouda cheese": {"slice": {"cal": 101, "fat": 8, "carbs": 0.6, "protein": 7, "sodium": 232, "fiber": 0, "sugar": 0.6},
                    "oz": {"cal": 101, "fat": 8, "carbs": 0.6, "protein": 7, "sodium": 232, "fiber": 0, "sugar": 0.6}},

    # Spices & seasonings
    "saffron": {"tsp": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0.1, "sodium": 1, "fiber": 0, "sugar": 0},
               "threads": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0.1, "sodium": 1, "fiber": 0, "sugar": 0}},
    "saffron threads": {"tsp": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0.1, "sodium": 1, "fiber": 0, "sugar": 0}},
    "garam masala": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.4, "sugar": 0},
                    "tbsp": {"cal": 18, "fat": 0.9, "carbs": 3, "protein": 0.6, "sodium": 3, "fiber": 1.2, "sugar": 0}},
    "cardamom": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.4, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "green cardamom": {"pod": {"cal": 6, "fat": 0.1, "carbs": 1.4, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0},
                       "": {"cal": 6, "fat": 0.1, "carbs": 1.4, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "black cardamom": {"pod": {"cal": 6, "fat": 0.2, "carbs": 1.2, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0},
                       "": {"cal": 6, "fat": 0.2, "carbs": 1.2, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "peppercorns": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.5, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "lavender": {"tsp": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0.1, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "dried lavender": {"tsp": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0.1, "sodium": 0, "fiber": 0.2, "sugar": 0}},

    # Sauces
    "green chile sauce": {"cup": {"cal": 60, "fat": 1, "carbs": 11, "protein": 2, "sodium": 1200, "fiber": 2, "sugar": 4},
                         "can": {"cal": 90, "fat": 1.5, "carbs": 16, "protein": 3, "sodium": 1800, "fiber": 3, "sugar": 6},
                         "oz": {"cal": 8, "fat": 0.1, "carbs": 1.4, "protein": 0.3, "sodium": 150, "fiber": 0.3, "sugar": 0.5}},
    "picante sauce": {"cup": {"cal": 70, "fat": 0.3, "carbs": 16, "protein": 3, "sodium": 2400, "fiber": 4, "sugar": 8},
                     "jar": {"cal": 140, "fat": 0.6, "carbs": 32, "protein": 6, "sodium": 4800, "fiber": 8, "sugar": 16}},
    "russian dressing": {"tbsp": {"cal": 57, "fat": 5, "carbs": 3, "protein": 0.2, "sodium": 133, "fiber": 0, "sugar": 2},
                        "bottle": {"cal": 912, "fat": 80, "carbs": 48, "protein": 3, "sodium": 2128, "fiber": 0, "sugar": 32}},
    "creamy french dressing": {"tbsp": {"cal": 70, "fat": 6, "carbs": 4, "protein": 0, "sodium": 140, "fiber": 0, "sugar": 3},
                              "bottle": {"cal": 1120, "fat": 96, "carbs": 64, "protein": 0, "sodium": 2240, "fiber": 0, "sugar": 48}},
    "stove top stuffing": {"pkg": {"cal": 440, "fat": 8, "carbs": 84, "protein": 12, "sodium": 1800, "fiber": 4, "sugar": 6}},

    # Preserves & sweets
    "jam": {"tbsp": {"cal": 56, "fat": 0, "carbs": 14, "protein": 0, "sodium": 6, "fiber": 0.2, "sugar": 10},
            "cup": {"cal": 896, "fat": 0, "carbs": 224, "protein": 0, "sodium": 96, "fiber": 3.2, "sugar": 160},
            "jar": {"cal": 1008, "fat": 0, "carbs": 252, "protein": 0, "sodium": 108, "fiber": 3.6, "sugar": 180}},
    "preserves": {"tbsp": {"cal": 56, "fat": 0, "carbs": 14, "protein": 0, "sodium": 6, "fiber": 0.2, "sugar": 10},
                 "jar": {"cal": 1008, "fat": 0, "carbs": 252, "protein": 0, "sodium": 108, "fiber": 3.6, "sugar": 180}},
    "apricot preserves": {"tbsp": {"cal": 50, "fat": 0, "carbs": 13, "protein": 0, "sodium": 8, "fiber": 0.2, "sugar": 11},
                         "jar": {"cal": 800, "fat": 0, "carbs": 208, "protein": 0, "sodium": 128, "fiber": 3.2, "sugar": 176}},
    "preserved ginger": {"tbsp": {"cal": 20, "fat": 0, "carbs": 5, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 4}},
    "crystallized ginger": {"oz": {"cal": 96, "fat": 0.1, "carbs": 24, "protein": 0.2, "sodium": 4, "fiber": 0.4, "sugar": 19}},
    "lady fingers": {"each": {"cal": 40, "fat": 1, "carbs": 7, "protein": 1, "sodium": 16, "fiber": 0, "sugar": 4},
                    "doz": {"cal": 480, "fat": 12, "carbs": 84, "protein": 12, "sodium": 192, "fiber": 0, "sugar": 48}},

    # Condiments
    "pickle relish": {"tbsp": {"cal": 14, "fat": 0.1, "carbs": 3.5, "protein": 0.1, "sodium": 164, "fiber": 0.2, "sugar": 2.5}},
    "pickle juice": {"cup": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 1800, "fiber": 0, "sugar": 0},
                    "tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 113, "fiber": 0, "sugar": 0}},
    "horseradish": {"tbsp": {"cal": 7, "fat": 0.1, "carbs": 2, "protein": 0.2, "sodium": 47, "fiber": 0.5, "sugar": 1}},
    "prepared horseradish": {"tbsp": {"cal": 7, "fat": 0.1, "carbs": 2, "protein": 0.2, "sodium": 47, "fiber": 0.5, "sugar": 1}},

    # Fruits
    "gooseberries": {"cup": {"cal": 66, "fat": 0.9, "carbs": 15, "protein": 1.3, "sodium": 2, "fiber": 6.5, "sugar": 0},
                    "lb": {"cal": 134, "fat": 1.8, "carbs": 30, "protein": 2.6, "sodium": 4, "fiber": 13, "sugar": 0}},
    "ripe gooseberries": {"lb": {"cal": 134, "fat": 1.8, "carbs": 30, "protein": 2.6, "sodium": 4, "fiber": 13, "sugar": 0}},
    "roma tomatoes": {"each": {"cal": 11, "fat": 0.1, "carbs": 2.4, "protein": 0.5, "sodium": 3, "fiber": 0.7, "sugar": 1.6},
                     "cup": {"cal": 32, "fat": 0.4, "carbs": 7, "protein": 1.6, "sodium": 9, "fiber": 2, "sugar": 5}},

    # Meat alternatives
    "tvp": {"cup": {"cal": 222, "fat": 0.5, "carbs": 21, "protein": 35, "sodium": 4, "fiber": 12, "sugar": 9}},
    "textured vegetable protein": {"cup": {"cal": 222, "fat": 0.5, "carbs": 21, "protein": 35, "sodium": 4, "fiber": 12, "sugar": 9}},

    # Canned goods
    "clam juice": {"cup": {"cal": 6, "fat": 0, "carbs": 0, "protein": 1, "sodium": 640, "fiber": 0, "sugar": 0},
                  "bottle": {"cal": 12, "fat": 0, "carbs": 0, "protein": 2, "sodium": 1280, "fiber": 0, "sugar": 0}},
    "crabmeat": {"cup": {"cal": 134, "fat": 2, "carbs": 0, "protein": 28, "sodium": 600, "fiber": 0, "sugar": 0},
                "can": {"cal": 100, "fat": 1.5, "carbs": 0, "protein": 21, "sodium": 450, "fiber": 0, "sugar": 0},
                "oz": {"cal": 25, "fat": 0.4, "carbs": 0, "protein": 5, "sodium": 95, "fiber": 0, "sugar": 0}},
    "peach syrup": {"cup": {"cal": 240, "fat": 0, "carbs": 60, "protein": 0, "sodium": 10, "fiber": 0, "sugar": 55}},

    # Baked goods
    "saltine crackers": {"each": {"cal": 13, "fat": 0.3, "carbs": 2.2, "protein": 0.3, "sodium": 38, "fiber": 0.1, "sugar": 0},
                        "cup": {"cal": 195, "fat": 4.5, "carbs": 33, "protein": 4.5, "sodium": 570, "fiber": 1.5, "sugar": 0}},
    "ritz crackers": {"tube": {"cal": 1600, "fat": 80, "carbs": 200, "protein": 16, "sodium": 3200, "fiber": 8, "sugar": 24},
                     "each": {"cal": 16, "fat": 0.8, "carbs": 2, "protein": 0.2, "sodium": 32, "fiber": 0.1, "sugar": 0.2}},

    # Flavored gelatin
    "lemon-flavored gelatin": {"pkg": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "orange-flavored gelatin": {"pkg": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "strawberry gelatin": {"pkg": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "lime gelatin": {"pkg": {"cal": 80, "fat": 0, "carbs": 19, "protein": 2, "sodium": 120, "fiber": 0, "sugar": 19}},
    "unflavored gelatin": {"envelope": {"cal": 23, "fat": 0, "carbs": 0, "protein": 6, "sodium": 14, "fiber": 0, "sugar": 0},
                          "pkg": {"cal": 23, "fat": 0, "carbs": 0, "protein": 6, "sodium": 14, "fiber": 0, "sugar": 0}},

    # Beverages
    "gingerale": {"cup": {"cal": 83, "fat": 0, "carbs": 21, "protein": 0, "sodium": 26, "fiber": 0, "sugar": 21}},
    "apple cider": {"cup": {"cal": 117, "fat": 0.3, "carbs": 29, "protein": 0.2, "sodium": 5, "fiber": 0.2, "sugar": 24},
                   "quart": {"cal": 468, "fat": 1.2, "carbs": 116, "protein": 0.8, "sodium": 20, "fiber": 0.8, "sugar": 96},
                   "gallon": {"cal": 1872, "fat": 4.8, "carbs": 464, "protein": 3.2, "sodium": 80, "fiber": 3.2, "sugar": 384}},

    # Misc
    "spanish rice": {"cup": {"cal": 130, "fat": 1, "carbs": 28, "protein": 3, "sodium": 510, "fiber": 1, "sugar": 2}},
    "savory pie crust": {"each": {"cal": 620, "fat": 39, "carbs": 60, "protein": 7, "sodium": 560, "fiber": 2, "sugar": 2}},
    "deep dish pie crust": {"each": {"cal": 720, "fat": 45, "carbs": 70, "protein": 8, "sodium": 650, "fiber": 2, "sugar": 3}},
    "enchilada sauce": {"cup": {"cal": 60, "fat": 1, "carbs": 11, "protein": 2, "sodium": 1160, "fiber": 2, "sugar": 4},
                       "can": {"cal": 90, "fat": 1.5, "carbs": 16, "protein": 3, "sodium": 1740, "fiber": 3, "sugar": 6}},
    "red enchilada sauce": {"cup": {"cal": 60, "fat": 1, "carbs": 11, "protein": 2, "sodium": 1160, "fiber": 2, "sugar": 4}},

    # BATCH 14: Additional missing ingredients and units
    # New entries for missing items
    "red onion": {"cup": {"cal": 64, "fat": 0.2, "carbs": 15, "protein": 2, "sodium": 6, "fiber": 2, "sugar": 7},
                 "medium": {"cal": 44, "fat": 0.1, "carbs": 10, "protein": 1.3, "sodium": 4, "fiber": 1.5, "sugar": 5},
                 "tbsp": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.1, "sugar": 0.4}},
    "light mayonnaise": {"tbsp": {"cal": 35, "fat": 3.5, "carbs": 1, "protein": 0, "sodium": 100, "fiber": 0, "sugar": 1},
                        "cup": {"cal": 560, "fat": 56, "carbs": 16, "protein": 0, "sodium": 1600, "fiber": 0, "sugar": 16}},
    "hemp seeds": {"tbsp": {"cal": 55, "fat": 4.5, "carbs": 1, "protein": 3, "sodium": 0, "fiber": 0.5, "sugar": 0},
                  "cup": {"cal": 880, "fat": 72, "carbs": 16, "protein": 48, "sodium": 0, "fiber": 8, "sugar": 0}},
    "pumpkin seeds": {"cup": {"cal": 721, "fat": 63, "carbs": 25, "protein": 34, "sodium": 25, "fiber": 12, "sugar": 2},
                     "oz": {"cal": 126, "fat": 11, "carbs": 4.4, "protein": 6, "sodium": 4, "fiber": 2, "sugar": 0.4},
                     "tbsp": {"cal": 45, "fat": 4, "carbs": 1.5, "protein": 2, "sodium": 2, "fiber": 0.7, "sugar": 0.1}},
    "sunflower seeds": {"cup": {"cal": 818, "fat": 72, "carbs": 28, "protein": 29, "sodium": 5, "fiber": 12, "sugar": 3},
                       "oz": {"cal": 165, "fat": 14, "carbs": 5.6, "protein": 5.8, "sodium": 1, "fiber": 2.4, "sugar": 0.6},
                       "tbsp": {"cal": 51, "fat": 4.5, "carbs": 1.8, "protein": 1.8, "sodium": 0, "fiber": 0.7, "sugar": 0.2}},
    "poppy seeds": {"tbsp": {"cal": 46, "fat": 4, "carbs": 2, "protein": 1.5, "sodium": 2, "fiber": 1, "sugar": 0.3},
                   "tsp": {"cal": 15, "fat": 1.3, "carbs": 0.7, "protein": 0.5, "sodium": 0.5, "fiber": 0.3, "sugar": 0.1}},
    "caraway seeds": {"tsp": {"cal": 7, "fat": 0.3, "carbs": 1, "protein": 0.4, "sodium": 0.4, "fiber": 0.8, "sugar": 0},
                     "tbsp": {"cal": 21, "fat": 0.9, "carbs": 3, "protein": 1.2, "sodium": 1, "fiber": 2.4, "sugar": 0}},
    "dark sesame oil": {"tbsp": {"cal": 120, "fat": 14, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                       "tsp": {"cal": 40, "fat": 4.5, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "ground chipotle pepper": {"tsp": {"cal": 8, "fat": 0.4, "carbs": 1.5, "protein": 0.3, "sodium": 26, "fiber": 0.9, "sugar": 0.5}},
    "chipotle chile pepper": {"tsp": {"cal": 8, "fat": 0.4, "carbs": 1.5, "protein": 0.3, "sodium": 26, "fiber": 0.9, "sugar": 0.5}},
    "asian chili sauce": {"tsp": {"cal": 6, "fat": 0, "carbs": 1.2, "protein": 0.2, "sodium": 100, "fiber": 0.2, "sugar": 0.8},
                         "tbsp": {"cal": 18, "fat": 0, "carbs": 3.6, "protein": 0.6, "sodium": 300, "fiber": 0.6, "sugar": 2.4}},
    "turkey italian sausage": {"link": {"cal": 140, "fat": 8, "carbs": 2, "protein": 14, "sodium": 480, "fiber": 0, "sugar": 1},
                              "oz": {"cal": 44, "fat": 2.5, "carbs": 0.6, "protein": 4.4, "sodium": 150, "fiber": 0, "sugar": 0.3},
                              "lb": {"cal": 704, "fat": 40, "carbs": 10, "protein": 70, "sodium": 2400, "fiber": 0, "sugar": 5}},
    "clam juice": {"cup": {"cal": 5, "fat": 0, "carbs": 0, "protein": 1, "sodium": 516, "fiber": 0, "sugar": 0},
                  "oz": {"cal": 0.6, "fat": 0, "carbs": 0, "protein": 0.1, "sodium": 64, "fiber": 0, "sugar": 0},
                  "bottle": {"cal": 5, "fat": 0, "carbs": 0, "protein": 1, "sodium": 516, "fiber": 0, "sugar": 0}},
    "beef roast": {"lb": {"cal": 816, "fat": 48, "carbs": 0, "protein": 88, "sodium": 280, "fiber": 0, "sugar": 0},
                  "oz": {"cal": 51, "fat": 3, "carbs": 0, "protein": 5.5, "sodium": 18, "fiber": 0, "sugar": 0}},
    "chuck roast": {"lb": {"cal": 1080, "fat": 72, "carbs": 0, "protein": 96, "sodium": 320, "fiber": 0, "sugar": 0},
                   "oz": {"cal": 67, "fat": 4.5, "carbs": 0, "protein": 6, "sodium": 20, "fiber": 0, "sugar": 0}},
    "canned tomatoes": {"can": {"cal": 72, "fat": 0.4, "carbs": 16, "protein": 3.2, "sodium": 640, "fiber": 4, "sugar": 10},
                       "cup": {"cal": 41, "fat": 0.2, "carbs": 9, "protein": 1.8, "sodium": 360, "fiber": 2.2, "sugar": 5.5}},
    # Additional units for existing items
    "cucumber": {"cup": {"cal": 16, "fat": 0.1, "carbs": 4, "protein": 0.7, "sodium": 2, "fiber": 0.5, "sugar": 2},
                "medium": {"cal": 24, "fat": 0.2, "carbs": 6, "protein": 1, "sodium": 3, "fiber": 0.7, "sugar": 3},
                "each": {"cal": 45, "fat": 0.3, "carbs": 11, "protein": 2, "sodium": 6, "fiber": 1.5, "sugar": 5}},
    "lettuce": {"cup": {"cal": 5, "fat": 0.1, "carbs": 1, "protein": 0.5, "sodium": 5, "fiber": 0.5, "sugar": 0.4},
               "leaf": {"cal": 1, "fat": 0, "carbs": 0.2, "protein": 0.1, "sodium": 1, "fiber": 0.1, "sugar": 0.1},
               "head": {"cal": 54, "fat": 0.5, "carbs": 10, "protein": 5, "sodium": 50, "fiber": 5, "sugar": 4}},

    # BATCH 15: More missing ingredients and expanded units
    # Spices & seasonings
    "italian herbs": {"tsp": {"cal": 3, "fat": 0.1, "carbs": 0.6, "protein": 0.1, "sodium": 1, "fiber": 0.3, "sugar": 0},
                     "tbsp": {"cal": 9, "fat": 0.3, "carbs": 1.8, "protein": 0.3, "sodium": 3, "fiber": 0.9, "sugar": 0}},
    "ground pepper": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.4, "protein": 0.2, "sodium": 1, "fiber": 0.6, "sugar": 0},
                     "tbsp": {"cal": 18, "fat": 0.3, "carbs": 4.2, "protein": 0.6, "sodium": 3, "fiber": 1.8, "sugar": 0}},
    "lemon-pepper seasoning": {"tsp": {"cal": 7, "fat": 0.1, "carbs": 1.5, "protein": 0.2, "sodium": 340, "fiber": 0.3, "sugar": 0.2}},
    "ground mustard": {"tsp": {"cal": 9, "fat": 0.5, "carbs": 0.6, "protein": 0.5, "sodium": 0, "fiber": 0.2, "sugar": 0}},
    "rubbed sage": {"tsp": {"cal": 2, "fat": 0.1, "carbs": 0.4, "protein": 0.1, "sodium": 0, "fiber": 0.3, "sugar": 0}},
    "cajun seasoning": {"tsp": {"cal": 8, "fat": 0.3, "carbs": 1.5, "protein": 0.3, "sodium": 200, "fiber": 0.5, "sugar": 0.2},
                       "tbsp": {"cal": 24, "fat": 0.9, "carbs": 4.5, "protein": 0.9, "sodium": 600, "fiber": 1.5, "sugar": 0.6}},
    "ground cardamom": {"tsp": {"cal": 6, "fat": 0.1, "carbs": 1.4, "protein": 0.2, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    "ground turmeric": {"tsp": {"cal": 8, "fat": 0.2, "carbs": 1.4, "protein": 0.3, "sodium": 1, "fiber": 0.5, "sugar": 0.1}},
    "chipotle": {"tsp": {"cal": 8, "fat": 0.4, "carbs": 1.5, "protein": 0.3, "sodium": 26, "fiber": 0.9, "sugar": 0.5},
                "each": {"cal": 15, "fat": 0.8, "carbs": 3, "protein": 0.6, "sodium": 52, "fiber": 1.8, "sugar": 1}},
    "pepper sauce": {"tsp": {"cal": 1, "fat": 0, "carbs": 0.1, "protein": 0, "sodium": 124, "fiber": 0, "sugar": 0},
                    "tbsp": {"cal": 3, "fat": 0, "carbs": 0.3, "protein": 0, "sodium": 372, "fiber": 0, "sugar": 0}},
    # Cheese
    "part-skim mozzarella cheese": {"cup": {"cal": 336, "fat": 20, "carbs": 4, "protein": 32, "sodium": 704, "fiber": 0, "sugar": 2},
                                    "oz": {"cal": 72, "fat": 4.5, "carbs": 0.8, "protein": 7, "sodium": 150, "fiber": 0, "sugar": 0.4}},
    "jack cheese": {"cup": {"cal": 422, "fat": 34, "carbs": 2, "protein": 28, "sodium": 660, "fiber": 0, "sugar": 0.5},
                   "oz": {"cal": 106, "fat": 8.5, "carbs": 0.5, "protein": 7, "sodium": 165, "fiber": 0, "sugar": 0.1}},
    "blue cheese crumbles": {"cup": {"cal": 476, "fat": 39, "carbs": 3, "protein": 29, "sodium": 1395, "fiber": 0, "sugar": 0.5},
                            "oz": {"cal": 100, "fat": 8, "carbs": 0.7, "protein": 6, "sodium": 325, "fiber": 0, "sugar": 0.1},
                            "tbsp": {"cal": 30, "fat": 2.5, "carbs": 0.2, "protein": 1.8, "sodium": 87, "fiber": 0, "sugar": 0}},
    # Vegetables
    "fresh mushrooms": {"cup": {"cal": 15, "fat": 0.2, "carbs": 2.3, "protein": 2.2, "sodium": 4, "fiber": 0.7, "sugar": 1.4},
                       "oz": {"cal": 6, "fat": 0.1, "carbs": 0.9, "protein": 0.9, "sodium": 1.5, "fiber": 0.3, "sugar": 0.5}},
    "fresh gingerroot": {"tbsp": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.1, "sodium": 1, "fiber": 0.1, "sugar": 0.1},
                        "tsp": {"cal": 2, "fat": 0, "carbs": 0.4, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                        "inch": {"cal": 8, "fat": 0.1, "carbs": 1.8, "protein": 0.2, "sodium": 1, "fiber": 0.2, "sugar": 0.2}},
    "medium green pepper": {"": {"cal": 24, "fat": 0.2, "carbs": 5.5, "protein": 1, "sodium": 4, "fiber": 2, "sugar": 3}},
    "medium zucchini": {"": {"cal": 33, "fat": 0.4, "carbs": 6, "protein": 2.4, "sodium": 16, "fiber": 2, "sugar": 5}},
    "medium ripe avocado": {"": {"cal": 240, "fat": 22, "carbs": 13, "protein": 3, "sodium": 11, "fiber": 10, "sugar": 1}},
    "medium carrot": {"": {"cal": 25, "fat": 0.1, "carbs": 6, "protein": 0.6, "sodium": 42, "fiber": 1.7, "sugar": 3}},
    "medium cucumber": {"": {"cal": 24, "fat": 0.2, "carbs": 6, "protein": 1, "sodium": 3, "fiber": 0.7, "sugar": 3}},
    "coleslaw mix": {"cup": {"cal": 17, "fat": 0.1, "carbs": 4, "protein": 1, "sodium": 13, "fiber": 1.4, "sugar": 2},
                    "bag": {"cal": 85, "fat": 0.5, "carbs": 20, "protein": 5, "sodium": 65, "fiber": 7, "sugar": 10}},
    # Meat
    "pork loin chops": {"lb": {"cal": 680, "fat": 28, "carbs": 0, "protein": 100, "sodium": 260, "fiber": 0, "sugar": 0},
                       "oz": {"cal": 43, "fat": 1.8, "carbs": 0, "protein": 6.3, "sodium": 16, "fiber": 0, "sugar": 0},
                       "each": {"cal": 170, "fat": 7, "carbs": 0, "protein": 25, "sodium": 65, "fiber": 0, "sugar": 0}},
    "lean ground turkey": {"lb": {"cal": 720, "fat": 36, "carbs": 0, "protein": 92, "sodium": 400, "fiber": 0, "sugar": 0},
                          "oz": {"cal": 45, "fat": 2.3, "carbs": 0, "protein": 5.8, "sodium": 25, "fiber": 0, "sugar": 0}},
    "beef steak": {"lb": {"cal": 880, "fat": 56, "carbs": 0, "protein": 88, "sodium": 280, "fiber": 0, "sugar": 0},
                  "oz": {"cal": 55, "fat": 3.5, "carbs": 0, "protein": 5.5, "sodium": 18, "fiber": 0, "sugar": 0}},
    "white fish": {"lb": {"cal": 400, "fat": 4, "carbs": 0, "protein": 84, "sodium": 300, "fiber": 0, "sugar": 0},
                  "oz": {"cal": 25, "fat": 0.3, "carbs": 0, "protein": 5.3, "sodium": 19, "fiber": 0, "sugar": 0},
                  "fillet": {"cal": 100, "fat": 1, "carbs": 0, "protein": 21, "sodium": 75, "fiber": 0, "sugar": 0}},
    # Broths
    "reduced-sodium chicken broth": {"cup": {"cal": 15, "fat": 0.5, "carbs": 1, "protein": 2, "sodium": 450, "fiber": 0, "sugar": 0},
                                    "can": {"cal": 22, "fat": 0.8, "carbs": 1.5, "protein": 3, "sodium": 675, "fiber": 0, "sugar": 0}},
    "reduced-sodium beef broth": {"cup": {"cal": 17, "fat": 0.5, "carbs": 1, "protein": 3, "sodium": 440, "fiber": 0, "sugar": 0},
                                 "can": {"cal": 25, "fat": 0.8, "carbs": 1.5, "protein": 4.5, "sodium": 660, "fiber": 0, "sugar": 0}},
    "beef bouillon granules": {"tsp": {"cal": 5, "fat": 0.2, "carbs": 0.5, "protein": 0.5, "sodium": 900, "fiber": 0, "sugar": 0},
                              "tbsp": {"cal": 15, "fat": 0.6, "carbs": 1.5, "protein": 1.5, "sodium": 2700, "fiber": 0, "sugar": 0}},
    # Sauces
    "barbecue sauce": {"tbsp": {"cal": 29, "fat": 0.1, "carbs": 7, "protein": 0.2, "sodium": 175, "fiber": 0.2, "sugar": 5},
                      "cup": {"cal": 464, "fat": 1.6, "carbs": 112, "protein": 3.2, "sodium": 2800, "fiber": 3.2, "sugar": 80}},
    "bechamel sauce": {"cup": {"cal": 308, "fat": 22, "carbs": 18, "protein": 9, "sodium": 680, "fiber": 0.5, "sugar": 8},
                      "tbsp": {"cal": 19, "fat": 1.4, "carbs": 1.1, "protein": 0.6, "sodium": 42, "fiber": 0, "sugar": 0.5}},
    # Miscellaneous
    "chips": {"cup": {"cal": 274, "fat": 18, "carbs": 25, "protein": 3, "sodium": 268, "fiber": 2, "sugar": 0.5},
             "oz": {"cal": 152, "fat": 10, "carbs": 14, "protein": 1.7, "sodium": 149, "fiber": 1.1, "sugar": 0.3}},
    "pita": {"each": {"cal": 165, "fat": 0.7, "carbs": 34, "protein": 5.5, "sodium": 322, "fiber": 1.3, "sugar": 0.7},
            "half": {"cal": 82, "fat": 0.4, "carbs": 17, "protein": 2.8, "sodium": 161, "fiber": 0.7, "sugar": 0.4}},

    # BATCH 16: Remaining missing ingredients and expanded units
    # Alcohol/beverages
    "silver tequila": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                      "shot": {"cal": 97, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "tequila": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
               "shot": {"cal": 97, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "ginger beer": {"cup": {"cal": 124, "fat": 0, "carbs": 32, "protein": 0, "sodium": 13, "fiber": 0, "sugar": 31},
                   "oz": {"cal": 15, "fat": 0, "carbs": 4, "protein": 0, "sodium": 2, "fiber": 0, "sugar": 4}},
    "light rum": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                 "shot": {"cal": 97, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "dark rum": {"oz": {"cal": 64, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                "shot": {"cal": 97, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "orange liqueur": {"oz": {"cal": 103, "fat": 0, "carbs": 11, "protein": 0, "sodium": 1, "fiber": 0, "sugar": 11},
                      "tbsp": {"cal": 32, "fat": 0, "carbs": 3.4, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 3.4}},
    # Specialty ingredients
    "black sesame seeds": {"tbsp": {"cal": 52, "fat": 4.5, "carbs": 2, "protein": 1.6, "sodium": 1, "fiber": 1, "sugar": 0},
                          "tsp": {"cal": 17, "fat": 1.5, "carbs": 0.7, "protein": 0.5, "sodium": 0, "fiber": 0.3, "sugar": 0}},
    "ghee": {"tbsp": {"cal": 112, "fat": 13, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
            "cup": {"cal": 1792, "fat": 208, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
            "tsp": {"cal": 37, "fat": 4.3, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "white miso paste": {"tbsp": {"cal": 33, "fat": 1, "carbs": 4, "protein": 2, "sodium": 634, "fiber": 0.5, "sugar": 1},
                        "tsp": {"cal": 11, "fat": 0.3, "carbs": 1.3, "protein": 0.7, "sodium": 211, "fiber": 0.2, "sugar": 0.3}},
    "miso paste": {"tbsp": {"cal": 33, "fat": 1, "carbs": 4, "protein": 2, "sodium": 634, "fiber": 0.5, "sugar": 1},
                  "tsp": {"cal": 11, "fat": 0.3, "carbs": 1.3, "protein": 0.7, "sodium": 211, "fiber": 0.2, "sugar": 0.3}},
    "ground sumac": {"tsp": {"cal": 5, "fat": 0.1, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.3, "sugar": 0.2}},
    "tajin": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 190, "fiber": 0, "sugar": 0}},
    "char siu sauce": {"tbsp": {"cal": 45, "fat": 0, "carbs": 10, "protein": 1, "sodium": 520, "fiber": 0, "sugar": 8}},
    "chipotle paste": {"tbsp": {"cal": 15, "fat": 0.5, "carbs": 3, "protein": 0.5, "sodium": 180, "fiber": 1, "sugar": 1},
                      "tsp": {"cal": 5, "fat": 0.2, "carbs": 1, "protein": 0.2, "sodium": 60, "fiber": 0.3, "sugar": 0.3}},
    "fine salt": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 2325, "fiber": 0, "sugar": 0}},
    "chai masala": {"tsp": {"cal": 6, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.4, "sugar": 0}},
    "summer savory": {"tsp": {"cal": 4, "fat": 0.1, "carbs": 1, "protein": 0.1, "sodium": 0, "fiber": 0.6, "sugar": 0}},
    # Meat
    "beef ribs": {"lb": {"cal": 1060, "fat": 84, "carbs": 0, "protein": 72, "sodium": 280, "fiber": 0, "sugar": 0},
                 "each": {"cal": 265, "fat": 21, "carbs": 0, "protein": 18, "sodium": 70, "fiber": 0, "sugar": 0}},
    "ground lamb": {"lb": {"cal": 1120, "fat": 88, "carbs": 0, "protein": 76, "sodium": 320, "fiber": 0, "sugar": 0},
                   "oz": {"cal": 70, "fat": 5.5, "carbs": 0, "protein": 4.8, "sodium": 20, "fiber": 0, "sugar": 0}},
    "imitation crabmeat": {"oz": {"cal": 25, "fat": 0.3, "carbs": 3, "protein": 2.5, "sodium": 180, "fiber": 0, "sugar": 0.5},
                          "cup": {"cal": 81, "fat": 1, "carbs": 10, "protein": 8, "sodium": 580, "fiber": 0, "sugar": 1.5}},
    # Vegetables
    "large carrot": {"": {"cal": 30, "fat": 0.2, "carbs": 7, "protein": 0.7, "sodium": 50, "fiber": 2, "sugar": 3.5}},
    "medium beets": {"": {"cal": 35, "fat": 0.1, "carbs": 8, "protein": 1.3, "sodium": 64, "fiber": 2.3, "sugar": 6}},
    "nori sheets": {"each": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 5, "fiber": 0.3, "sugar": 0}},
    "nori": {"sheet": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.5, "sodium": 5, "fiber": 0.3, "sugar": 0}},
    # Pickles
    "dill pickles": {"each": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 283, "fiber": 0.3, "sugar": 0.4},
                    "cup": {"cal": 17, "fat": 0.2, "carbs": 4, "protein": 0.8, "sodium": 1208, "fiber": 1.2, "sugar": 1.5}},
    "dill pickle spears": {"each": {"cal": 4, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 283, "fiber": 0.3, "sugar": 0.4}},
    "dill pickle juice": {"tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 210, "fiber": 0, "sugar": 0},
                         "cup": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0, "sodium": 3360, "fiber": 0, "sugar": 0}},
    # Cheese
    "provolone": {"slice": {"cal": 75, "fat": 5.7, "carbs": 0.6, "protein": 5.5, "sodium": 190, "fiber": 0, "sugar": 0.2},
                 "oz": {"cal": 100, "fat": 7.5, "carbs": 0.8, "protein": 7.3, "sodium": 250, "fiber": 0, "sugar": 0.3},
                 "cup": {"cal": 463, "fat": 35, "carbs": 4, "protein": 34, "sodium": 1157, "fiber": 0, "sugar": 1}},
    # Pudding/dessert
    "vanilla pudding": {"cup": {"cal": 150, "fat": 2.5, "carbs": 28, "protein": 4, "sodium": 380, "fiber": 0, "sugar": 21},
                       "pkg": {"cal": 100, "fat": 0, "carbs": 24, "protein": 0, "sodium": 350, "fiber": 0, "sugar": 20}},
    # Rice
    "quick-cooking rice": {"cup": {"cal": 165, "fat": 0.4, "carbs": 36, "protein": 3.4, "sodium": 1, "fiber": 0.6, "sugar": 0}},
    # Expanded units for existing items with unit mismatches
    "ground beef": {"lb": {"cal": 1152, "fat": 80, "carbs": 0, "protein": 96, "sodium": 320, "fiber": 0, "sugar": 0},
                   "oz": {"cal": 72, "fat": 5, "carbs": 0, "protein": 6, "sodium": 20, "fiber": 0, "sugar": 0},
                   "cup": {"cal": 339, "fat": 24, "carbs": 0, "protein": 28, "sodium": 94, "fiber": 0, "sugar": 0}},
    "tomato sauce": {"cup": {"cal": 59, "fat": 0.5, "carbs": 13, "protein": 2.5, "sodium": 1284, "fiber": 3.4, "sugar": 8},
                    "can": {"cal": 89, "fat": 0.8, "carbs": 20, "protein": 3.8, "sodium": 1926, "fiber": 5, "sugar": 12},
                    "oz": {"cal": 7, "fat": 0.1, "carbs": 1.6, "protein": 0.3, "sodium": 160, "fiber": 0.4, "sugar": 1},
                    "": {"cal": 89, "fat": 0.8, "carbs": 20, "protein": 3.8, "sodium": 1926, "fiber": 5, "sugar": 12}},
    "bacon": {"slice": {"cal": 43, "fat": 3.3, "carbs": 0.1, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0},
             "strip": {"cal": 43, "fat": 3.3, "carbs": 0.1, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0},
             "strips": {"cal": 43, "fat": 3.3, "carbs": 0.1, "protein": 3, "sodium": 137, "fiber": 0, "sugar": 0},
             "lb": {"cal": 2400, "fat": 184, "carbs": 5, "protein": 168, "sodium": 7600, "fiber": 0, "sugar": 0},
             "oz": {"cal": 150, "fat": 11.5, "carbs": 0.3, "protein": 10.5, "sodium": 475, "fiber": 0, "sugar": 0},
             "cup": {"cal": 573, "fat": 44, "carbs": 1, "protein": 40, "sodium": 1820, "fiber": 0, "sugar": 0}},
    "ketchup": {"tbsp": {"cal": 17, "fat": 0, "carbs": 4.5, "protein": 0.2, "sodium": 154, "fiber": 0, "sugar": 3.6},
               "cup": {"cal": 272, "fat": 0, "carbs": 72, "protein": 3.2, "sodium": 2464, "fiber": 0, "sugar": 58},
               "bottle": {"cal": 400, "fat": 0, "carbs": 100, "protein": 4, "sodium": 3600, "fiber": 0, "sugar": 80},
               "jar": {"cal": 400, "fat": 0, "carbs": 100, "protein": 4, "sodium": 3600, "fiber": 0, "sugar": 80},
               "": {"cal": 17, "fat": 0, "carbs": 4.5, "protein": 0.2, "sodium": 154, "fiber": 0, "sugar": 3.6}},

    # BATCH 17: Remaining missing ingredients and expanded units
    # Spices/herbs
    "coriander": {"tsp": {"cal": 5, "fat": 0.3, "carbs": 1, "protein": 0.2, "sodium": 1, "fiber": 0.8, "sugar": 0},
                 "tbsp": {"cal": 15, "fat": 0.9, "carbs": 3, "protein": 0.6, "sodium": 3, "fiber": 2.4, "sugar": 0}},
    "angostura bitters": {"dash": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0.5},
                         "tsp": {"cal": 10, "fat": 0, "carbs": 2.5, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 2.5}},
    # Vegetables
    "beetroot": {"cup": {"cal": 58, "fat": 0.2, "carbs": 13, "protein": 2.2, "sodium": 106, "fiber": 3.8, "sugar": 9},
                "medium": {"cal": 35, "fat": 0.1, "carbs": 8, "protein": 1.3, "sodium": 64, "fiber": 2.3, "sugar": 6}},
    "persian cucumbers": {"cup": {"cal": 16, "fat": 0.1, "carbs": 4, "protein": 0.7, "sodium": 2, "fiber": 0.5, "sugar": 2},
                         "each": {"cal": 8, "fat": 0.1, "carbs": 2, "protein": 0.3, "sodium": 1, "fiber": 0.3, "sugar": 1}},
    "medium sweet yellow pepper": {"": {"cal": 50, "fat": 0.4, "carbs": 12, "protein": 1.9, "sodium": 4, "fiber": 2, "sugar": 8}},
    "medium red grapefruit": {"": {"cal": 82, "fat": 0.3, "carbs": 21, "protein": 1.5, "sodium": 0, "fiber": 2.8, "sugar": 17}},
    # Beans
    "refried pinto beans": {"cup": {"cal": 234, "fat": 3, "carbs": 36, "protein": 14, "sodium": 753, "fiber": 12, "sugar": 1},
                           "can": {"cal": 351, "fat": 4.5, "carbs": 54, "protein": 21, "sodium": 1130, "fiber": 18, "sugar": 1.5}},
    # Asian ingredients
    "rice papers": {"each": {"cal": 30, "fat": 0, "carbs": 7, "protein": 0.3, "sodium": 10, "fiber": 0, "sugar": 0}},
    "chow mein noodles": {"cup": {"cal": 237, "fat": 14, "carbs": 26, "protein": 4, "sodium": 198, "fiber": 1.8, "sugar": 0},
                         "oz": {"cal": 148, "fat": 8.7, "carbs": 16, "protein": 2.5, "sodium": 124, "fiber": 1.1, "sugar": 0}},
    "broccoli coleslaw mix": {"cup": {"cal": 20, "fat": 0.1, "carbs": 4, "protein": 1.5, "sodium": 15, "fiber": 2, "sugar": 2}},
    # Alcohol
    "whiskey": {"oz": {"cal": 70, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
               "shot": {"cal": 105, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "german beer": {"cup": {"cal": 103, "fat": 0, "carbs": 9, "protein": 1, "sodium": 12, "fiber": 0, "sugar": 0},
                   "oz": {"cal": 13, "fat": 0, "carbs": 1.1, "protein": 0.1, "sodium": 1.5, "fiber": 0, "sugar": 0}},
    # Specialty
    "ube extract": {"tsp": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 1}},
    "pretzel salt": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 1800, "fiber": 0, "sugar": 0}},
    "blackberry jam": {"tbsp": {"cal": 50, "fat": 0, "carbs": 13, "protein": 0, "sodium": 6, "fiber": 0.3, "sugar": 10}},
    # Batch 1 - Missing ingredients
    "soy flour": {"cup": {"cal": 366, "fat": 17, "carbs": 30, "protein": 47, "sodium": 11, "fiber": 8, "sugar": 8},
                 "tbsp": {"cal": 23, "fat": 1.1, "carbs": 1.9, "protein": 2.9, "sodium": 1, "fiber": 0.5, "sugar": 0.5}},
    "flax seed": {"cup": {"cal": 897, "fat": 71, "carbs": 49, "protein": 31, "sodium": 51, "fiber": 46, "sugar": 3},
                 "tbsp": {"cal": 55, "fat": 4.3, "carbs": 3, "protein": 1.9, "sodium": 3, "fiber": 2.8, "sugar": 0.2}},
    "flaxseed": {"cup": {"cal": 897, "fat": 71, "carbs": 49, "protein": 31, "sodium": 51, "fiber": 46, "sugar": 3},
                "tbsp": {"cal": 55, "fat": 4.3, "carbs": 3, "protein": 1.9, "sodium": 3, "fiber": 2.8, "sugar": 0.2}},
    "macaroons": {"each": {"cal": 97, "fat": 3, "carbs": 17, "protein": 1, "sodium": 59, "fiber": 0.5, "sugar": 14},
                 "cup": {"cal": 485, "fat": 15, "carbs": 85, "protein": 5, "sodium": 295, "fiber": 2.5, "sugar": 70}},
    "watermelon rind": {"cup": {"cal": 30, "fat": 0.2, "carbs": 7, "protein": 1, "sodium": 2, "fiber": 0.4, "sugar": 4}},
    # Batch 2 - Missing ingredients
    "garnish": {"": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
               "garnish": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "pizza sauce": {"cup": {"cal": 80, "fat": 2, "carbs": 12, "protein": 3, "sodium": 800, "fiber": 3, "sugar": 8},
                   "tbsp": {"cal": 5, "fat": 0.1, "carbs": 0.8, "protein": 0.2, "sodium": 50, "fiber": 0.2, "sugar": 0.5},
                   "can": {"cal": 160, "fat": 4, "carbs": 24, "protein": 6, "sodium": 1600, "fiber": 6, "sugar": 16},
                   "jar": {"cal": 160, "fat": 4, "carbs": 24, "protein": 6, "sodium": 1600, "fiber": 6, "sugar": 16},
                   "": {"cal": 80, "fat": 2, "carbs": 12, "protein": 3, "sodium": 800, "fiber": 3, "sugar": 8}},
    "onion soup mix": {"packet": {"cal": 60, "fat": 1, "carbs": 10, "protein": 2, "sodium": 2400, "fiber": 1, "sugar": 3},
                      "tbsp": {"cal": 10, "fat": 0.2, "carbs": 1.7, "protein": 0.3, "sodium": 400, "fiber": 0.2, "sugar": 0.5}},
    "spice cake": {"slice": {"cal": 180, "fat": 6, "carbs": 32, "protein": 2, "sodium": 220, "fiber": 0.5, "sugar": 20}},
    "chipotle in adobo": {"each": {"cal": 15, "fat": 0.5, "carbs": 2.5, "protein": 0.5, "sodium": 130, "fiber": 0.8, "sugar": 1},
                         "tbsp": {"cal": 15, "fat": 0.5, "carbs": 3, "protein": 0.5, "sodium": 180, "fiber": 1, "sugar": 1}},
    "guacamole": {"cup": {"cal": 184, "fat": 15, "carbs": 12, "protein": 2.3, "sodium": 372, "fiber": 7, "sugar": 1},
                 "tbsp": {"cal": 12, "fat": 1, "carbs": 0.8, "protein": 0.1, "sodium": 23, "fiber": 0.4, "sugar": 0.1}},
    # Expanded units for items with mismatches
    "green chiles": {"can": {"cal": 30, "fat": 0.2, "carbs": 6, "protein": 1.5, "sodium": 550, "fiber": 2, "sugar": 3},
                    "oz": {"cal": 5, "fat": 0, "carbs": 1, "protein": 0.2, "sodium": 90, "fiber": 0.3, "sugar": 0.5},
                    "cup": {"cal": 40, "fat": 0.3, "carbs": 8, "protein": 2, "sodium": 733, "fiber": 2.7, "sugar": 4},
                    "tbsp": {"cal": 2, "fat": 0, "carbs": 0.5, "protein": 0.1, "sodium": 46, "fiber": 0.2, "sugar": 0.2}},
    "ham": {"cup": {"cal": 249, "fat": 13, "carbs": 3, "protein": 29, "sodium": 1684, "fiber": 0, "sugar": 0},
           "lb": {"cal": 680, "fat": 36, "carbs": 8, "protein": 80, "sodium": 4600, "fiber": 0, "sugar": 0},
           "oz": {"cal": 43, "fat": 2.3, "carbs": 0.5, "protein": 5, "sodium": 290, "fiber": 0, "sugar": 0},
           "slice": {"cal": 46, "fat": 2.4, "carbs": 0.6, "protein": 5.3, "sodium": 310, "fiber": 0, "sugar": 0}},
    "feta": {"oz": {"cal": 75, "fat": 6, "carbs": 1, "protein": 4, "sodium": 316, "fiber": 0, "sugar": 1},
            "cup": {"cal": 396, "fat": 32, "carbs": 6, "protein": 21, "sodium": 1668, "fiber": 0, "sugar": 5},
            "tbsp": {"cal": 25, "fat": 2, "carbs": 0.3, "protein": 1.3, "sodium": 105, "fiber": 0, "sugar": 0.3}},
    "carrots": {"cup": {"cal": 52, "fat": 0.3, "carbs": 12, "protein": 1.2, "sodium": 88, "fiber": 3.6, "sugar": 6},
               "medium": {"cal": 25, "fat": 0.1, "carbs": 6, "protein": 0.6, "sodium": 42, "fiber": 1.7, "sugar": 3},
               "lb": {"cal": 186, "fat": 1, "carbs": 43, "protein": 4.3, "sodium": 314, "fiber": 13, "sugar": 21}},
    "tortillas": {"each": {"cal": 94, "fat": 2.4, "carbs": 15, "protein": 2.5, "sodium": 191, "fiber": 1, "sugar": 0.4},
                 "cup": {"cal": 188, "fat": 4.8, "carbs": 30, "protein": 5, "sodium": 382, "fiber": 2, "sugar": 0.8},
                 "": {"cal": 94, "fat": 2.4, "carbs": 15, "protein": 2.5, "sodium": 191, "fiber": 1, "sugar": 0.4}},
    "beans": {"cup": {"cal": 239, "fat": 0.9, "carbs": 43, "protein": 16, "sodium": 1, "fiber": 16, "sugar": 0.6},
             "can": {"cal": 358, "fat": 1.4, "carbs": 64, "protein": 24, "sodium": 880, "fiber": 24, "sugar": 1}},

    # =========================================================================
    # CHEESEMAKING INGREDIENTS (added for family cheese recipes)
    # =========================================================================
    "liquid rennet": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                      "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "rennet": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
               "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "calcium chloride": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                         "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "cheese salt": {"tbsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 6976, "fiber": 0, "sugar": 0},
                    "tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 2325, "fiber": 0, "sugar": 0}},
    "starter culture": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                        "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "mesophilic starter culture": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                                   "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "thermophilic starter culture": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0},
                                     "": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "mesophilic starter": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "appropriate starter": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "appropriate starter culture": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "cow's milk": {"gallon": {"cal": 2384, "fat": 128, "carbs": 192, "protein": 128, "sodium": 1712, "fiber": 0, "sugar": 192},
                   "cup": {"cal": 149, "fat": 8, "carbs": 12, "protein": 8, "sodium": 107, "fiber": 0, "sugar": 12}},
    "raw cow's milk": {"gallon": {"cal": 2384, "fat": 128, "carbs": 192, "protein": 128, "sodium": 1712, "fiber": 0, "sugar": 192}},
    "goat's milk": {"gallon": {"cal": 2752, "fat": 160, "carbs": 176, "protein": 144, "sodium": 800, "fiber": 0, "sugar": 176},
                    "cup": {"cal": 172, "fat": 10, "carbs": 11, "protein": 9, "sodium": 50, "fiber": 0, "sugar": 11}},
    "sheep's milk": {"gallon": {"cal": 4224, "fat": 272, "carbs": 208, "protein": 240, "sodium": 720, "fiber": 0, "sugar": 208},
                     "cup": {"cal": 264, "fat": 17, "carbs": 13, "protein": 15, "sodium": 45, "fiber": 0, "sugar": 13}},
    "citric acid": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "annatto": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
    "lipase powder": {"tsp": {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}},
}

# =============================================================================
# STANDARD CAN & JAR SIZES
# =============================================================================

STANDARD_CAN_SIZES = {
    # Size name: ounces
    "small": 8,
    "regular": 14.5,
    "standard": 14.5,
    "large": 28,
    "family": 28,
    "#10": 106,  # Restaurant size
    "#300": 14,
    "#303": 16,
    "#2": 20,
    "#2.5": 28,
    "#3": 46,
}

STANDARD_JAR_SIZES = {
    # Size name: ounces
    "small": 8,
    "regular": 16,
    "standard": 16,
    "large": 24,
    "family": 32,
}

# =============================================================================
# INGREDIENT NORMALIZATION
# =============================================================================

def parse_quantity(qty_str):
    """Parse quantity string to float, handling fractions and ranges."""
    if not qty_str or qty_str.strip() == "":
        return 1.0

    qty_str = str(qty_str).strip().lower()

    # Handle word numbers (historical recipes)
    word_numbers = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "a": 1, "an": 1,
        "half": 0.5, "quarter": 0.25
    }
    if qty_str in word_numbers:
        return float(word_numbers[qty_str])

    # Handle ranges like "1-2" or "6-8" - take midpoint
    if '-' in qty_str and not qty_str.startswith('-'):
        parts = qty_str.split('-')
        if len(parts) == 2:
            try:
                low = parse_quantity(parts[0])
                high = parse_quantity(parts[1])
                return (low + high) / 2
            except:
                pass

    # Handle "to" ranges like "6 to 8"
    if ' to ' in qty_str:
        parts = qty_str.split(' to ')
        if len(parts) == 2:
            try:
                low = parse_quantity(parts[0])
                high = parse_quantity(parts[1])
                return (low + high) / 2
            except:
                pass

    # Handle mixed numbers like "1 1/2"
    parts = qty_str.split()
    total = 0
    for part in parts:
        try:
            if '/' in part:
                total += float(Fraction(part))
            else:
                # Remove any trailing punctuation
                part = part.rstrip('.,;:')
                total += float(part)
        except (ValueError, ZeroDivisionError):
            continue

    return total if total > 0 else 1.0


def normalize_unit(unit):
    """Normalize unit names to standard forms."""
    unit = str(unit).lower().strip().rstrip('.')

    unit_map = {
        # Volume
        "cups": "cup", "c": "cup", "c.": "cup",
        "tablespoons": "tbsp", "tablespoon": "tbsp", "tbsps": "tbsp", "t": "tbsp", "tbs": "tbsp", "tbl": "tbsp",
        "tblsp": "tbsp", "tblsps": "tbsp", "tblsp.": "tbsp", "tblsps.": "tbsp", "spoons": "tbsp", "spoon": "tbsp",
        "teaspoons": "tsp", "teaspoon": "tsp", "tsps": "tsp", "t.": "tsp",
        "ounces": "oz", "ounce": "oz", "ozs": "oz",
        "pounds": "lb", "pound": "lb", "lbs": "lb",
        "pints": "pint", "pt": "pint",
        "quarts": "quart", "qt": "quart",
        "gallons": "gallon", "gal": "gallon",
        # Historical measurements (Batch 14)
        "gill": "gill", "gills": "gill",  # 4 fl oz = 0.5 cup
        "drachm": "drachm", "drachms": "drachm", "dram": "drachm", "drams": "drachm",  # 1/8 oz
        "dessertspoon": "dessertspoon", "dessertspoons": "dessertspoon", "dssp": "dessertspoon",  # 2 tsp
        "saltspoon": "saltspoon", "saltspoons": "saltspoon", "saltspoonful": "saltspoon", "saltspoonfuls": "saltspoon",  # 1/4 tsp
        "wineglass": "wineglass", "wineglasses": "wineglass", "wine glass": "wineglass", "wine glasses": "wineglass",  # ~4 fl oz = 0.5 cup
        "teacup": "teacup", "teacups": "teacup", "tea cup": "teacup", "tea cups": "teacup",  # ~6 fl oz = 0.75 cup
        "coffeecup": "coffeecup", "coffeecups": "coffeecup", "coffee cup": "coffeecup", "coffee cups": "coffeecup",  # ~1 cup
        "jigger": "jigger", "jiggers": "jigger",  # 1.5 oz = 3 tbsp
        "peck": "peck", "pecks": "peck", "pk": "peck",  # 8 quarts (dry)
        "bushel": "bushel", "bushels": "bushel", "bu": "bushel",  # 4 pecks = 32 quarts
        "firkin": "firkin", "firkins": "firkin",  # 9 gallons
        "hogshead": "hogshead", "hogsheads": "hogshead",  # 63 gallons
        # Count
        "slices": "slice", "thin slices": "slice", "thick slices": "slice",
        "links": "link",
        "cloves": "clove",
        "cans": "can",
        "loaves": "loaf", "large loaf": "loaf", "small loaf": "loaf", "medium loaf": "loaf",
        "packages": "package", "pkg": "package", "pkgs": "package", "packets": "package", "pkg.": "package",
        "packet": "package", "oz package": "package",
        "containers": "container", "oz container": "container",
        # Handful/portions
        "handful": "", "handfuls": "",
        "sachet (7g)": "sachet", "sachets": "sachet",
        "envelopes": "envelope",
        "stalks": "stalk",
        "sprigs": "sprig",
        "ears": "ear",
        "bunches": "bunch",
        "heads": "head",
        "loaves": "loaf",
        "pieces": "piece", "pc": "piece", "pcs": "piece",
        # Size-based
        "small": "small", "sm": "small",
        "medium": "medium", "med": "medium",
        "large": "large", "lg": "large",
    }

    # Handle embedded sizes like "can (17 oz)" or "cup (4 oz)" or "cans (15.5 oz each)" → strip the size
    import re
    embedded_size = re.match(r'^(\w+)s?\s*\([\d\s.]+\s*oz(?:\s+each)?\)$', unit)
    if embedded_size:
        unit = embedded_size.group(1)

    # Handle "cup (3-inch)" or "cups (1-inch)" → "cup" (strip dimension descriptor)
    dimension_size = re.match(r'^(\w+)s?\s*\([\d\s./-]+-inch\)$', unit)
    if dimension_size:
        unit = dimension_size.group(1)

    # Handle "3-oz packages" or "2-oz pkgs" → "package" (strip size prefix)
    oz_packages = re.match(r'^[\d\s./-]+\s*oz\.?\s*(?:packages?|pkgs?)$', unit)
    if oz_packages:
        unit = "package"

    # Handle "15 1/2 oz cans" or "14.5-oz cans" or plain "oz can" → "can"
    oz_cans = re.match(r'^(?:[\d\s./½¼¾-]+\s*)?oz\.?\s*cans?$', unit)
    if oz_cans:
        unit = "can"

    # Handle "oz jar" or "16 oz jar" → "jar" (treat as can equivalent)
    oz_jar = re.match(r'^(?:[\d\s./]+\s*)?oz\.?\s*jars?$', unit)
    if oz_jar:
        unit = "can"  # jars are roughly equivalent to cans

    # Handle "oz carton" or "32-oz carton" → "can" (treat as can equivalent)
    oz_carton = re.match(r'^(?:[\d\s./-]+\s*)?oz\.?\s*cartons?$', unit)
    if oz_carton:
        unit = "can"  # cartons are roughly equivalent to cans

    # Handle "oz box" or "10 oz box" → "package"
    oz_box = re.match(r'^(?:[\d\s./-]+\s*)?oz\.?\s*box(?:es)?$', unit)
    if oz_box:
        unit = "package"

    # Handle "oz pkgs" or "1 1/4 oz pkgs" → "packet"
    oz_pkgs = re.match(r'^(?:[\d\s./½¼¾-]+\s*)?oz\.?\s*pkgs?$', unit)
    if oz_pkgs:
        unit = "packet"

    # Handle OCR artifacts where "lbs" becomes "lb s." or "lb s"
    # Also "tsp s.", "tbsp s.", "oz s.", "qts.", "pts."
    ocr_unit_fix = re.match(r'^(lb|tsp|tbsp|oz|qt|pt)\s*s\.?$', unit)
    if ocr_unit_fix:
        unit = ocr_unit_fix.group(1)

    # Handle "qts." and "pts." → "quart" and "pint"
    if unit in ["qts", "qts.", "qt.", "qt"]:
        unit = "quart"
    if unit in ["pts", "pts.", "pt.", "pt"]:
        unit = "pint"

    # Handle "for garnish" units - treat as optional (return empty for no caloric contribution)
    if "for garnish" in unit or "for serving" in unit or "for topping" in unit:
        unit = "garnish"

    # Descriptive units that should be treated as empty (each)
    descriptive_units = ["ripe", "fresh", "extra", "additional"]
    if unit in descriptive_units:
        unit = ""

    return unit_map.get(unit, unit)


def normalize_ingredient(item):
    """Normalize ingredient name for database lookup."""
    if not item:
        return ""

    item = str(item).lower().strip()

    # Fix unicode fractions
    unicode_fractions = {
        '½': '1/2', '¼': '1/4', '¾': '3/4', '⅓': '1/3', '⅔': '2/3',
        '⅛': '1/8', '⅜': '3/8', '⅝': '5/8', '⅞': '7/8'
    }
    for uf, replacement in unicode_fractions.items():
        item = item.replace(uf, replacement)

    # Normalize curly quotes and special characters
    item = item.replace('\u2019', "'")   # Right single curly quote '
    item = item.replace('\u2018', "'")   # Left single curly quote '
    item = item.replace('\u201c', '"')   # Left double curly quote "
    item = item.replace('\u201d', '"')   # Right double curly quote "
    item = item.replace('ﬂ', 'fl')  # fi/fl ligature
    item = item.replace('ﬁ', 'fi')  # fi ligature

    # Remove leading numbers/quantities EARLY so unit patterns can match (Batch 14 fix)
    import re
    item = re.sub(r'^\d+[\s/\d.-]*\s*', '', item)

    # Remove OCR artifacts where "lbs." got split to unit="lb", item="s. ..."
    # e.g., "s. raw spinach" -> "raw spinach", "s. rhubarb" -> "rhubarb"
    item = re.sub(r'^s\.\s+', '', item)

    # Remove leading "ful of" from OCR'd "tablespoonful of" / "teaspoonful of"
    item = re.sub(r'^ful\s+of\s+', '', item)

    # Remove footnote references like "[2]", "[1]", etc.
    item = re.sub(r'\[\d+\]', '', item)

    # Remove trailing non-breaking spaces
    item = item.replace('\xa0', ' ').strip()

    # Batch 29: Handle fully unparsed ingredient strings that still have units at start
    # e.g., "cups beef broth" -> "beef broth", "oz can cream of chicken soup" -> "cream of chicken soup"
    leading_unit_patterns = [
        r'^cups?\s+', r'^cup\s+', r'^tbsp\.?\s+', r'^tsp\.?\s+', r'^oz\.?\s+',
        r'^ounces?\s+', r'^lb\.?\s+', r'^lbs?\s+', r'^pounds?\s+', r'^can[s]?\s+',
        r'^package[s]?\s+', r'^pkg\.?\s+', r'^bag[s]?\s+', r'^box(es)?\s+',
        r'^bottle[s]?\s+', r'^jar[s]?\s+', r'^carton[s]?\s+', r'^container[s]?\s+',
        r'^bunch(es)?\s+', r'^head[s]?\s+', r'^clove[s]?\s+', r'^slice[s]?\s+',
        r'^piece[s]?\s+', r'^small\s+', r'^medium\s+', r'^large\s+', r'^extra\s+',
        r'^each\s+', r'^dozen\s+', r'^pinch(es)?\s+', r'^dash(es)?\s+',
    ]
    for pattern in leading_unit_patterns:
        item = re.sub(pattern, '', item, flags=re.IGNORECASE)

    # Remove leading WORD numbers (historical recipes)
    word_numbers = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
                    'nine', 'ten', 'eleven', 'twelve', 'a', 'an', 'half', 'quarter']
    for word in word_numbers:
        if item.startswith(word + ' '):
            item = item[len(word)+1:]
            break

    # Fix common OCR quirks in ingredient text
    ocr_fixes = [
        (r'^ful[s]?\s+of\s*', ''),           # item starts with "ful of" (OCR artifact)
        (r'^ful[s]?\s+', ''),                # item starts with "ful " (OCR artifact)
        (r'\btsp\s*ful\s*of\b', ''),         # "tsp ful of" -> ""
        (r'\btbsp\s*ful[s]?\s*of\b', ''),    # "tbsp fuls of" -> ""
        (r'\btsp\s*ful\b', ''),              # "tsp ful" -> ""
        (r'\btbsp\s*ful[s]?\b', ''),         # "tbsp fuls" -> ""
        (r'\btblsp\.?\b', ''),               # "tblsp" -> ""
        (r'\blevel\s+tablespoonful[s]?\s+of\b', ''),  # "level tablespoonfuls of"
        (r'\blevel\s+teaspoonful[s]?\s+of\b', ''),    # "level teaspoonfuls of"
        (r'\bsaltspoonful\s+of\b', ''),      # "saltspoonful of" -> ""
        (r'\bfew\s+grains\b', ''),           # "few grains" -> ""
        (r'\bdash\s+of\b', ''),              # "dash of" -> ""
        (r'\bdash\s+', ''),                  # "dash " embedded in item
        (r'\bpinch\s+', ''),                 # "pinch " embedded in item
        (r'\btsp\.?\s+', ''),                # "tsp " or "tsp. " embedded in item
        (r'\btbsp\.?\s+', ''),               # "tbsp " embedded in item
        (r'^t\s+', ''),                      # "t " at start (abbreviation for tsp)
        (r'^c\s+', ''),                      # "c " at start (abbreviation for cup)
        (r'^T\s+', ''),                      # "T " at start (abbreviation for tbsp)
        # Full-word units embedded in item (Batch 14)
        (r'^teaspoons?\s+', ''),             # "teaspoon " or "teaspoons " at start
        (r'^tablespoons?\s+', ''),           # "tablespoon " or "tablespoons " at start
        (r'^teaspoonful[s]?\s+of\s*', ''),   # "teaspoonfuls of" at start
        (r'^tablespoonful[s]?\s+of\s*', ''), # "tablespoonfuls of" at start
        (r'^teaspoonful[s]?\s+', ''),        # "teaspoonfuls " at start
        (r'^tablespoonful[s]?\s+', ''),      # "tablespoonfuls " at start
        (r'^ounces?\s+', ''),                # "ounce " or "ounces " at start
        (r'^pounds?\s+', ''),                # "pound " or "pounds " at start
        (r'\b1/2\s+cups?\s+', ''),           # "1/2 cup(s) " embedded
        (r'\b1/4\s+cups?\s+', ''),           # "1/4 cup(s) " embedded
        (r'\b3/4\s+cups?\s+', ''),           # "3/4 cup(s) " embedded
        (r'\b1/2\s+tsp\.?\s+', ''),          # "1/2 tsp " embedded
        (r'\b1/4\s+tsp\.?\s+', ''),          # "1/4 tsp " embedded
        (r'\b1/2\s+tbsp\.?\s+', ''),         # "1/2 tbsp " embedded
        (r'\bcup[s]?\s+', ''),               # "cup " embedded in item
        (r'\bpint[s]?\s+', ''),              # "pint " embedded in item
        (r'\bquart[s]?\s+', ''),             # "quart " embedded in item
        (r'\bpound[s]?\s+', ''),             # "pound " embedded in item
        (r'\s+of\s+', ' '),                  # " of " -> " "
        (r'\s*\.\s*$', ''),                  # trailing period
        (r'\s*\.\s+', ' '),                  # period in middle
        (r'-\s+', ' '),                      # hyphen with trailing space (OCR line-break)
        (r'\s+-', ' '),                      # space before hyphen
        (r',\s*$', ''),                      # trailing comma
        (r'\s{2,}', ' '),                    # multiple spaces
    ]
    for pattern, replacement in ocr_fixes:
        item = re.sub(pattern, replacement, item)

    # Remove prep notes after comma, but preserve compound terms that include commas
    # e.g., "fat-free, less-sodium chicken broth" should NOT be split
    compound_comma_terms = ["less-sodium", "reduced-sodium", "low-sodium", "deveined", "peeled shrimp"]
    should_split_comma = True
    for term in compound_comma_terms:
        if term in item:
            should_split_comma = False
            break
    if "," in item and should_split_comma:
        item = item.split(",")[0].strip()

    # Remove parenthetical notes (including leading ones like "(4 oz)")
    item = re.sub(r'^\([^)]*\)\s*', '', item)  # Leading parenthetical
    item = re.sub(r'\s*\([^)]*\)', '', item)   # Embedded parenthetical

    # Second pass: Remove any new leading numbers exposed after parenthetical removal
    item = re.sub(r'^\d+[\s/\d.-]*\s*', '', item)

    # Protect specific items from prefix stripping
    protected_items = {
        "hot dog", "hot dogs", "hot dog bun", "hot dog buns",
        "hot sauce", "hot pepper", "hot peppers", "hot chili",
        "hot roll mix",
        "dried beef", "dried apples", "dried apricots", "dried cranberries",
        "dried cherries", "dried fruit", "dried fish",
    }
    if item not in protected_items:
        # Common prefixes to remove (skip for protected items)
        prefixes = [
            "fresh ", "frozen ", "dried ", "canned ", "cooked ", "raw ",
            "chopped ", "diced ", "minced ", "sliced ", "cubed ",
            "grated ", "shredded ", "mashed ", "crushed ", "crumbled ",
            "melted ", "softened ", "room temperature ", "cold ", "warm ", "hot ",
            "ripe ", "peeled ", "pitted ", "seeded ", "cored ",
            "toasted ", "roasted ", "sauteed ",
            "sifted ", "packed ", "firmly packed ", "lightly packed ",
            "finely ", "coarsely ", "roughly ", "thinly ",
            "boneless ", "skinless ",
            "low-fat ", "lowfat ", "low fat ", "nonfat ", "non-fat ", "fat-free ",
            "unsalted ", "salted ",
            "pure ", "organic ", "natural ",
            "about ", "approximately ", "approx ",
        ]

        for prefix in prefixes:
            if item.startswith(prefix):
                item = item[len(prefix):]

    # Brand name normalization (use straight quotes since curly quotes are normalized earlier)
    brand_map = {
        "grandma's molasses": "molasses",
        "grandmas molasses": "molasses",
        "carnation milk": "evaporated milk",
        "gold medal flour": "flour",
        "pillsbury flour": "flour",
        "crisco": "shortening",
        "pam": "cooking spray",
        "kraft": "",
        "heinz": "",
        "hellmann's": "mayonnaise",
        "best foods": "mayonnaise",
        "philadelphia": "cream cheese",
        "jell-o": "gelatin",
        "knox": "gelatin",
        "bisquick": "biscuit mix",
        "jiffy": "corn muffin mix",
        "shedd's spread country crock calcium plus vitamin d": "margarine",
        "shedd's spread country crock": "margarine",
        "shedd's spread": "margarine",
        "country crock": "margarine",
        "i can't believe it's not butter": "margarine",
        "campbell's": "",
        "swanson": "",
        "progresso": "",
        "lipton": "",
        "mccormick": "",
    }

    for brand, replacement in brand_map.items():
        if brand in item:
            if replacement:
                item = replacement
            else:
                item = item.replace(brand, "").strip()

    # Common ingredient synonyms
    synonyms = {
        # Flour
        "all purpose flour": "flour",
        "all-purpose flour": "flour",
        "ap flour": "flour",
        "plain flour": "flour",
        "unbleached flour": "flour",
        "enriched flour": "flour",
        "strong white bread flour": "bread flour",

        # Sugar
        "granulated sugar": "sugar",
        "white sugar": "sugar",
        "cane sugar": "sugar",
        "light brown sugar": "brown sugar",
        "dark brown sugar": "brown sugar",
        "confectioners sugar": "powdered sugar",
        "confectioner's sugar": "powdered sugar",
        "icing sugar": "powdered sugar",
        "10x sugar": "powdered sugar",

        # Eggs
        "large eggs": "egg",
        "eggs": "egg",
        "whole egg": "egg",
        "beaten egg": "egg",
        "egg whites": "egg white",
        "egg yolks": "egg yolk",

        # Dairy
        "whole milk": "milk",
        "2% milk": "milk",
        "1% milk": "skim milk",
        "fat free milk": "skim milk",
        "heavy whipping cream": "heavy cream",
        "whipping cream": "heavy cream",

        # Butter
        "unsalted butter": "butter",
        "salted butter": "butter",
        "stick butter": "butter",
        "butter or margarine": "butter",

        # Oil
        "canola oil": "vegetable oil",
        "corn oil": "vegetable oil",
        "safflower oil": "vegetable oil",
        "cooking oil": "vegetable oil",
        "extra virgin olive oil": "olive oil",
        "extra-virgin olive oil": "olive oil",
        "evoo": "olive oil",

        # Chicken
        "chicken breasts": "chicken breast",
        "boneless skinless chicken breasts": "chicken breast",
        "boneless skinless chicken breast": "chicken breast",
        "whole chicken breasts": "chicken breast",
        "chicken thighs": "chicken thigh",
        "boneless skinless chicken thighs": "chicken thigh",

        # Ground meats
        "lean ground beef": "ground beef",
        "ground chuck": "ground beef",
        "hamburger": "ground beef",
        "hamburger meat": "ground beef",

        # Onion/garlic
        "yellow onion": "onion",
        "white onion": "onion",
        "red onion": "onion",
        "sweet onion": "onion",
        "vidalia onion": "onion",
        "garlic cloves": "garlic",
        "cloves garlic": "garlic",
        "garlic clove": "garlic",
        "green onions": "green onion",
        "scallions": "green onion",

        # Peppers
        "green bell pepper": "green pepper",
        "red bell pepper": "red pepper",
        "bell pepper": "bell pepper",
        "jalapeno pepper": "jalapeno",
        "jalapeño": "jalapeno",
        "serrano pepper": "jalapeno",

        # Tomatoes
        "roma tomatoes": "tomato",
        "plum tomatoes": "tomato",
        "cherry tomatoes": "tomato",
        "grape tomatoes": "tomato",
        "tomatoes": "tomato",

        # Potatoes
        "russet potato": "potato",
        "russet potatoes": "potato",
        "yukon gold potato": "potato",
        "red potato": "potato",
        "baking potato": "potato",
        "idaho potato": "potato",

        # Spices
        "ground cumin": "cumin",
        "ground cinnamon": "cinnamon",
        "ground ginger": "ginger",
        "ground nutmeg": "nutmeg",
        "ground cloves": "cloves",
        "ground allspice": "allspice",
        "ground black pepper": "black pepper",
        "freshly ground black pepper": "black pepper",
        "freshly ground pepper": "pepper",
        "kosher salt": "salt",
        "sea salt": "salt",
        "table salt": "salt",
        "salt and pepper": "salt",
        "salt & pepper": "salt",

        # Vanilla
        "pure vanilla extract": "vanilla extract",
        "vanilla": "vanilla extract",
        "pure vanilla": "vanilla extract",

        # Oatmeal
        "instant oatmeal packets": "instant oatmeal",
        "instant oatmeal packets plain": "instant oatmeal",
        "oatmeal packets": "instant oatmeal",
        "quaker instant oatmeal": "instant oatmeal",
        "quaker oats instant oatmeal": "instant oatmeal",
        "quick oats": "oats",
        "rolled oats": "oats",
        "old fashioned oats": "oats",

        # Baking
        "baking cocoa": "cocoa powder",
        "unsweetened cocoa": "cocoa powder",
        "unsweetened cocoa powder": "cocoa powder",
        "dutch process cocoa": "cocoa powder",
        "semisweet chocolate chips": "chocolate chips",
        "semi-sweet chocolate chips": "chocolate chips",
        "dark chocolate chips": "chocolate chips",
        "milk chocolate chips": "chocolate chips",
        "active dry yeast": "yeast",
        "instant yeast": "yeast",
        "rapid rise yeast": "yeast",
        "unflavored gelatin": "gelatin",

        # Broth
        "low sodium chicken broth": "chicken broth",
        "reduced sodium chicken broth": "chicken broth",
        "low sodium beef broth": "beef broth",
        "stock": "chicken broth",
        "chicken stock": "chicken broth",
        "beef stock": "beef broth",

        # Canned goods
        "condensed cream of chicken soup": "cream of chicken soup",
        "condensed cream of mushroom soup": "cream of mushroom soup",
        "condensed cream of celery soup": "cream of celery soup",
        "condensed tomato soup": "tomato soup",
        "petite diced tomatoes": "diced tomatoes",
        "fire roasted diced tomatoes": "diced tomatoes",
        "stewed tomatoes": "canned tomatoes",
        "whole tomatoes": "canned tomatoes",

        # Herbs
        "fresh parsley": "parsley",
        "flat-leaf parsley": "parsley",
        "italian parsley": "parsley",
        "fresh cilantro": "cilantro",
        "fresh basil": "basil",
        "fresh dill": "dill",
        "fresh thyme": "thyme",
        "fresh rosemary": "rosemary",
        "fresh mint": "mint",
        "fresh sage": "sage",

        # Fish
        "trout fillets": "trout",
        "trout fillet": "trout",
        "salmon fillets": "salmon",
        "salmon fillet": "salmon",
        "skinless trout": "trout",
        "skinless salmon": "salmon",

        # Leavening
        "soda": "baking soda",
        "bicarbonate of soda": "baking soda",
        "bicarb": "baking soda",
        "dry active yeast": "yeast",
        "dry yeast": "yeast",
        "fast-action dried yeast": "yeast",
        "fast action dried yeast": "yeast",
        "quick rise yeast": "yeast",

        # Milk variants
        "lukewarm milk": "milk",
        "warm milk": "milk",
        "cold milk": "milk",
        "whole milk": "milk",
        "2% milk": "milk",

        # Mustard variants
        "english mustard powder": "mustard powder",
        "dry mustard powder": "mustard powder",
        "coleman's mustard": "mustard powder",

        # Cheese variants
        "extra mature cheddar cheese": "cheddar cheese",
        "extra sharp cheddar cheese": "cheddar cheese",
        "sharp cheddar cheese": "cheddar cheese",
        "mild cheddar cheese": "cheddar cheese",
        "mature cheddar cheese": "cheddar cheese",

        # Citrus zest
        "lemon rind": "lemon zest",
        "grated lemon rind": "lemon zest",
        "lemon peel": "lemon zest",
        "orange rind": "orange zest",
        "grated orange rind": "orange zest",
        "orange peel": "orange zest",
        "lime rind": "lime zest",
        "grated lime rind": "lime zest",

        # Salt & pepper
        "salt and pepper": "salt",
        "salt & pepper": "salt",
        "kosher salt and pepper": "salt",
        "kosher salt and freshly ground pepper": "salt",
        "salt and freshly ground pepper": "salt",
        "salt and freshly ground black pepper": "salt",
        "salt to taste": "salt",
        "pepper to taste": "pepper",
        "paprika": "paprika",

        # Misc
        "fresh lemon juice": "lemon juice",
        "fresh lime juice": "lime juice",
        "worcestershire": "worcestershire sauce",
        "sour cream": "sour cream",
        "plain greek yogurt": "greek yogurt",
        "non-fat greek yogurt": "greek yogurt",
        "thick-cut bacon": "bacon",
        "thick cut bacon": "bacon",
        "turkey bacon": "bacon",
        "center-cut bacon": "bacon",

        # Cooking spray
        "cooking spray": "cooking spray",
        "nonstick cooking spray": "cooking spray",
        "non-stick cooking spray": "cooking spray",
        "vegetable cooking spray": "cooking spray",
        "butter flavored cooking spray": "cooking spray",

        # Pie crust
        "savory deep dish pie crust": "pie crust",
        "deep dish pie crust": "pie crust",
        "9-inch pie crust": "pie crust",
        "unbaked pie crust": "pie crust",
        "prepared pie crust": "pie crust",
        "refrigerated pie crust": "pie crust",

        # Creamed soups
        "cream chicken soup": "cream of chicken soup",
        "cream mushroom soup": "cream of mushroom soup",
        "cream celery soup": "cream of celery soup",

        # Tortillas
        "large flour tortillas": "flour tortilla",
        "flour tortillas": "flour tortilla",
        "corn tortillas": "corn tortilla",
        "10-inch flour tortillas": "flour tortilla",
        "8-inch flour tortillas": "flour tortilla",

        # Lemons/citrus
        "lemons": "lemon",
        "limes": "lime",
        "oranges": "orange",

        # Gelatin
        "envelope unflavored gelatin": "gelatin",
        "packet unflavored gelatin": "gelatin",
        "unflavored gelatine": "gelatin",

        # Additional gap analysis mappings
        "soft shortening": "shortening",
        "soft butter": "butter",
        "creamed butter": "butter",
        "sweet butter": "butter",
        "butter substitute": "butter",
        "chilled butter": "butter",
        "clove garlic": "garlic",
        "small onion": "onion",
        "medium onion": "onion",
        "large onion": "onion",
        "chopped onion": "onion",
        "one onion": "onion",
        "two onions": "onion",
        "cut onion": "onion",
        "cutonion": "onion",
        "one egg": "egg",
        "eggwhites": "egg white",

        # OCR artifact fixes - space-corrupted words
        "mayonnais e": "mayonnaise",
        "eg g yolks": "egg yolk",
        "eg g": "egg",
        "unsalt ed butter": "butter",
        "lemo n peel": "lemon zest",
        "lemo n": "lemon",
        "m iniature marshmallows": "miniature marshmallows",
        "bouillon c ube": "bouillon cube",
        "unsweet ened pineapple juice": "pineapple juice",
        "s. hard pears": "pear",
        "s. sugar": "sugar",
        "all-purpose ﬂour": "flour",
        "ﬂour": "flour",  # Wrong fl character
        "confectioners' sugar": "powdered sugar",
        "cutparsley": "parsley",
        "teaspoon salt": "salt",
        "teaspoons salt": "salt",
        "t salt": "salt",
        "of salt": "salt",
        "two teaspoons ofsalt": "salt",
        "two teaspoons ofbaking powder": "baking powder",
        "three offlour": "flour",
        "four tablespoons ofshortening": "shortening",

        # Unit embedded in item cleanup
        "c sugar": "sugar",
        "c flour": "flour",
        "c butter": "butter",
        "c water": "water",
        "c milk": "milk",
        "qts water": "water",

        # Additional cheese
        "sharp cheddar": "sharp cheddar cheese",
        "mild cheddar": "mild cheddar cheese",
        "monterey jack": "monterey jack cheese",
        "pepper jack": "pepper jack cheese",
        "extra sharp cheddar": "sharp cheddar cheese",

        # Additional common mappings
        "boneless": "chicken breast",
        "skinless": "chicken breast",
        "low-sodium chicken broth": "chicken broth",
        "reduced sodium chicken broth": "chicken broth",
        # Protect broths from fat-free partial match
        "fat-free chicken broth": "chicken broth",
        "fat-free less-sodium chicken broth": "chicken broth",
        "fat-free, less-sodium chicken broth": "chicken broth",
        "fat-free beef broth": "beef broth",
        "fat-free less-sodium beef broth": "beef broth",
        "fat-free": "skim milk",

        # Corn syrup
        "corn syrup": "light corn syrup",
        "karo syrup": "light corn syrup",
        "karo": "light corn syrup",

        # More synonyms from gap analysis
        "large ripe banana": "banana",
        "ripe banana": "banana",
        "ripe mango": "mango",
        "t water": "water",
        "t milk": "milk",
        "t sugar": "sugar",
        "t cornstarch": "cornstarch",
        "c celery": "celery",
        "c powdered sugar": "powdered sugar",
        "c powdere d sugar": "powdered sugar",
        "lb butter": "butter",
        "teaspoon nutmeg": "nutmeg",
        "teaspoon cinnamon": "cinnamon",
        "teaspoons cinnamon": "cinnamon",
        "can tomato sauce": "tomato sauce",
        "can mushrooms": "mushrooms",
        "jar apricot preserves": "apricot preserves",
        "mel ted butter": "butter",
        "parsl ey": "parsley",
        "chili flakes": "red pepper flakes",
        "% milk": "milk",
        "spices": "allspice",
        "flavoring": "vanilla extract",

        # Round 5 gap analysis synonyms
        "c walnuts": "walnuts",
        "c salad oil": "salad oil",
        "c lemo n juice": "lemon juice",
        "tbs flour": "flour",
        "mozzarella chees e": "mozzarella cheese",
        "d onion": "onion",
        "cutgreen peppers": "green pepper",
        "pulverized sugar": "powdered sugar",
        "teaspoon pepper": "pepper",
        "of pepper": "pepper",
        "t cold water": "water",
        "glass white wine": "dry white wine",
        "olive or vegetable oil": "olive oil",
        "margarine or butter": "butter",
        "cereals or muesli": "muesli",
        "two tablespoons ofbutter": "butter",
        "two tablespoonfuls ofsugar": "sugar",
        "four branches ofparsley": "parsley",
        "three tablespoons offinely minced parsley": "parsley",
        "two teaspoonfuls ofsalt": "salt",
        "one teaspoonful ofsalt": "salt",
        "two level tablespoons ofbaking powder": "baking powder",
        "three cupsofflour": "flour",
        "ofmilk": "milk",

        # Historical cookbook OCR artifacts
        "double-acting or 11/2 teaspoons cream tartar baking powder": "baking powder",
        "double-acting or 11/4 teaspoons cream tartar baking powder": "baking powder",
        "double-acting or 3 teaspoons cream tartar baking powder": "baking powder",
        "pastry for 2-crust": "pie crust",
        "cooked": "chicken",
        "meal": "cornmeal",

        # Round 6 synonyms
        "confectioners' sugar": "powdered sugar",
        "ugar": "sugar",
        "ugar;": "sugar",
        "cheddar": "cheddar cheese",
        "tablespoons butter": "butter",
        "vinegar or lemon juice": "vinegar",
        "c brown sugar": "brown sugar",
        "two ofsugar": "sugar",
        "and a half sugar": "sugar",
        "butter with two sugar": "butter",
        "three teaspoonfuls baking powder": "baking powder",
        "three tablespoons ofbaking powder": "baking powder",
        "four cupsofsifted flour": "flour",
        "two tablespoons ofshortening": "shortening",
        "to 4 flour": "flour",
        "juice 1 lemon": "lemon juice",
        "black molasses": "molasses",
        "no 2 can crushed pineapple": "crushed pineapple",
        "one 9-inch pie shell": "pie crust",
        "pastry for 9\" shell": "pie crust",
        "s stewing beef": "stewing beef",
        "miniature marshmallows or 20 regular marshmallows": "miniature marshmallows",
        "orange zest strips": "orange zest",
        "stove top stuffi ng": "stove top stuffing",

        # Round 8 synonyms - OCR artifacts
        "tblsp. flour": "flour",
        "tblsp. sugar": "sugar",
        "tblsp. vinegar": "vinegar",
        "tblsp flour": "flour",
        "tblsp sugar": "sugar",
        "t vanilla": "vanilla extract",
        "t. vanilla": "vanilla extract",
        "tsp. vanilla": "vanilla extract",
        "level tablespoonfuls of flour": "flour",
        "level tablespoons of flour": "flour",
        "level tablespoonfuls flour": "flour",
        "tablespoonfuls of flour": "flour",
        "tablespoons of flour": "flour",
        "tablespoons flour": "flour",
        "½ cups sugar": "sugar",
        "½ cups flour": "flour",
        "½ cup sugar": "sugar",
        "½ cup shortening": "shortening",
        "½ cup milk": "milk",
        "½ tsp. baking powder": "baking powder",
        "½ tsp. cloves": "cloves",
        "½ tsp baking powder": "baking powder",
        "¾ cup sugar": "sugar",

        # Rose water variants
        "rose-water": "rose water",
        "rosewater": "rose water",

        # Catsup/ketchup
        "catsup": "ketchup",

        # Corn variants
        "kernel corn": "corn",
        "corn kernels": "corn",
        "whole kernel corn": "corn",

        # Pimiento/pimento
        "pimento": "pimiento",
        "chopped pimiento": "pimiento",
        "chopped pimento": "pimiento",

        # Green items
        "green peppers": "green pepper",
        "green chiles, chopped": "green chiles",
        "(4 oz) green chiles, chopped": "green chiles",
        "green chiles chopped": "green chiles",
        "chopped green chiles": "green chiles",

        # Whole spices
        "whole cloves": "cloves",
        "whole allspice": "allspice",

        # Common plurals and variants
        "potatoes": "potato",
        "onions": "onion",
        "carrots": "carrot",
        "apples": "apple",
        "avocados": "avocado",
        "raisins": "raisins",
        "bread crumbs": "breadcrumbs",

        # Gelatin
        "envelope unflavored gelatin": "gelatin",
        "envelopes unflavored gelatin": "gelatin",
        "packet gelatin": "gelatin",

        # Wine
        "wine": "dry white wine",
        "white wine": "dry white wine",
        "red wine": "dry red wine",

        # Soy sauce
        "soy sauce": "soy sauce",

        # Mace
        "mace": "nutmeg",  # Similar flavor profile

        # Sliced variants
        "slices bacon": "bacon",
        "bacon slices": "bacon",

        # Water variants
        "boiling water": "water",
        "cold water": "water",
        "qts. water": "water",

        # Spice synonyms
        "white peppercorns": "peppercorns",
        "black peppercorns": "peppercorns",
        "coriander seeds": "coriander seed",
        "ground fennel seeds": "fennel seeds",
        "fennel seeds, crushed": "fennel seeds",
        "ground cayenne pepper": "cayenne",
        "ground cayenne": "cayenne",
        "pinch cayenne": "cayenne",
        "red pepper flakes": "crushed red pepper",
        "seasoning salt": "salt",

        # Panko/breadcrumbs
        "panko crumbs": "panko",
        "panko breadcrumbs": "panko",

        # Cheese synonyms
        "crumbled feta cheese": "feta cheese",
        "crumbled gorgonzola cheese": "gorgonzola",
        "crumbled feta": "feta cheese",
        "crumbled gorgonzola": "gorgonzola",
        "romano cheese": "parmesan cheese",
        "parmigiano-reggiano cheese": "parmesan cheese",
        "parmigiano-reggiano": "parmesan cheese",

        # Pasta synonyms
        "penne pasta": "pasta",
        "bucatini": "pasta",
        "uncooked penne pasta": "pasta",
        "uncooked bucatini": "pasta",

        # Brand name cleanup
        "campbell's condensed french onion soup": "onion soup",
        "pepperidge farm classic sandwich buns": "hamburger bun",
        "ocean spray jellied cranberry sauce": "cranberry sauce",
        "heinz chili sauce": "chili sauce",
        "bird's eye": "",

        # Ingredient with prep embedded (from insufficient recipes analysis)
        "large potato": "potato",
        "large potato, diced": "potato",
        "medium potato": "potato",
        "small potato": "potato",
        "top sirloin steak": "sirloin",
        "top sirloin": "sirloin",
        "ribeye steaks": "steak",
        "ribeye steak": "steak",
        "beef ribeye steaks": "steak",
        "hoagie rolls": "hoagie roll",
        "italian rolls": "italian roll",
        "sub rolls": "sub roll",
        "crusty italian rolls": "italian roll",

        # Cottage cheese variants
        "½ cups cottage cheese": "cottage cheese",
        "cups cottage cheese": "cottage cheese",

        # Cooked rice/noodles
        "cooked rice": "rice",
        "cooked noodles": "noodles",
        "fine noodles": "noodles",
        "½ cups cooked rice": "rice",
        "½ cups cooked rice or fine noodles": "rice",

        # Tomato variants
        "¼ cups tomato juice": "tomato juice",
        "cups tomato juice": "tomato juice",

        # Green chile variants
        "green chiles, chopped": "green chiles",
        "chopped green chiles": "green chiles",
        "diced green chiles": "green chiles",

        # Cherry variants
        "sour cherries": "cherries",
        "pitted sour cherries": "cherries",
        "pitted cherries": "cherries",
        "concord grapes": "grapes",

        # Pepper variants
        "poblano peppers": "poblano pepper",
        "anaheim peppers": "anaheim pepper",

        # OCR space-corruption patterns
        "c raspb erries": "raspberries",
        "raspb erries": "raspberries",
        "c sugar": "sugar",
        "c water": "water",
        "t cornstarch": "cornstarch",
        "t vanilla": "vanilla",
        "t baking powder": "baking powder",
        "t bakin g powder": "baking powder",
        "t lemon extrac t": "lemon extract",
        "lemon extrac t": "lemon extract",
        "c flour": "flour",
        "c peca ns": "pecans",
        "peca ns": "pecans",
        "t lem on peel": "lemon zest",
        "lem on peel": "lemon zest",
        "c brown sugar": "brown sugar",
        "m iniature marshmallows": "marshmallows",
        "mini ature marsh mallows": "marshmallows",
        "miniature marshmallows": "marshmallows",
        "chop ped walnuts": "walnuts",
        "all-purpos e flour": "flour",
        "all purpos e flour": "flour",
        "shorte ning": "shortening",
        "semi- sweet real chocolate": "chocolate chips",
        "semi-sweet real chocolate": "chocolate chips",

        # Ingredient with unit embedded (from Corn Relish analysis)
        "ears corn": "corn",
        "ears ofcorn": "corn",
        "ears of corn": "corn",
        "head cabbage": "cabbage",
        "medium head cabbage": "cabbage",
        "dry mustard": "mustard powder",
        "red peppers": "red pepper",
        "green peppers": "green pepper",

        # Gelatin variants
        "lime gelatin": "gelatin",
        "lemon gelatin": "gelatin",
        "orange gelatin": "gelatin",
        "strawberry gelatin": "gelatin",
        "unflavored gelatin": "gelatin",
        "plain gelatin": "gelatin",

        # More OCR patterns
        "ofvinegar": "vinegar",
        "pint ofvinegar": "vinegar",

        # Embedded size units (strip the descriptor)
        "oz mushrooms": "mushrooms",
        "mushrooms, sliced": "mushrooms",
        "sliced mushrooms": "mushrooms",

        # Shrimp variants (from batch 2 analysis)
        "large shrimp": "shrimp",
        "medium shrimp": "shrimp",
        "small shrimp": "shrimp",
        "jumbo shrimp": "shrimp",

        # Chipotle variants
        "chipotle pepper in adobo": "chipotle pepper",
        "chipotle peppers in adobo": "chipotle pepper",
        "chipotle in adobo": "chipotle pepper",
        "chipotles in adobo": "chipotle pepper",

        # Salsa variants
        "chunky salsa": "salsa",
        "mild salsa": "salsa",
        "hot salsa": "salsa",
        "medium salsa": "salsa",

        # Pimiento variants
        "diced pimiento": "pimiento",
        "chopped pimiento": "pimiento",
        "jarred pimiento": "pimiento",

        # Walnut variants
        "black walnuts": "walnuts",
        "chopped black walnuts": "walnuts",
        "english walnuts": "walnuts",

        # Corn syrup variants
        "dark corn syrup": "corn syrup",
        "light corn syrup": "corn syrup",

        # Cold/cooked variants
        "cold chicken": "chicken",
        "cooked chicken": "chicken",
        "cooked cubed chicken": "chicken",

        # Wild rice variants
        "uncle ben's wild rice": "wild rice",
        "wild rice mix": "wild rice",

        # Water chestnuts variants
        "sliced water chestnuts": "water chestnuts",
        "canned water chestnuts": "water chestnuts",

        # Peeled/sliced variants
        "peeled jicama": "jicama",
        "julienne-cut peeled jicama": "jicama",
        "sliced peeled ripe mango": "mango",
        "peeled ripe mango": "mango",

        # Celery soup
        "cream of celery soup": "cream of chicken soup",
        "celery soup": "cream of chicken soup",

        # French green beans
        "french green beans": "green beans",
        "french cut green beans": "green beans",

        # Rhubarb
        "stewed rhubarb": "rhubarb",

        # Brand names
        "carnation milk": "evaporated milk",

        # Batch 3 analysis - OCR space-corrupted patterns
        "garl ic powder": "garlic powder",
        "garl ic": "garlic",
        "papri ka": "paprika",
        "alls pice": "allspice",
        "cocktai l": "cocktail",
        "conv erted": "converted",

        # Batch 3 analysis - historical ingredient names
        "calf's liver": "liver",
        "calfs liver": "liver",
        "beef liver": "liver",
        "fryer": "chicken",
        "fryer in pieces": "chicken",
        "frying chicken": "chicken",

        # Hard-cooked eggs
        "hard-cooked egg": "egg",
        "hard-cooked large egg": "egg",
        "hard boiled egg": "egg",
        "hard-boiled egg": "egg",

        # Crispy rice cereal
        "crispy rice cereal": "rice krispies",
        "cups crispy rice cereal": "rice krispies",
        "cups cups crispy rice cereal": "rice krispies",

        # Barley variants
        "pearled barley": "barley",
        "pearl barley": "barley",

        # Biscuit dough
        "biscuit dough": "biscuit",

        # Cakes yeast (historical format)
        "cakes yeast": "yeast",
        "cake yeast": "yeast",

        # Sauce variants
        "spaghetti sauce with mushrooms": "spaghetti sauce",
        "spaghetti sauce": "marinara sauce",
        "stewed tomato bits": "stewed tomatoes",

        # Cheese variants
        "ricotta salata cheese": "ricotta cheese",
        "ricotta salata": "ricotta cheese",
        "freshly crumbled ricotta salata cheese": "ricotta cheese",

        # Plum tomato
        "plum tomato": "tomato",
        "sliced plum tomato": "tomato",

        # Dutch-process cocoa
        "dutch-process cocoa powder": "cocoa powder",

        # Malted milk
        "malted milk powder": "malted milk",

        # Half-and-half variants
        "half-and-half": "half and half",

        # Olives
        "niçoise olives": "olives",
        "nicoise olives": "olives",
        "pitted niçoise olives": "olives",
        "pitted nicoise olives": "olives",
        "chopped pitted niçoise olives": "olives",
        "chopped pitted nicoise olives": "olives",

        # Basil variants
        "sliced fresh basil": "basil",
        "thinly sliced fresh basil": "basil",
        "torn basil leaves": "basil",
        "fresh basil leaves": "basil",

        # Mint variants
        "mint leaves": "mint",
        "torn mint leaves": "mint",
        "mint sprigs": "mint",

        # Sardinian bread (specialty, use crackers equiv)
        "pane carasau": "crackers",
        "sardinian music bread": "crackers",
        "sheets pane carasau": "crackers",

        # Browning sauce (negligible calories)
        "bottled browning sauce": "browning sauce",
        "kitchen bouquet": "browning sauce",

        # Whole wheat baguette
        "whole-wheat french bread baguette": "french bread",
        "whole wheat french bread baguette": "french bread",

        # Rice vinegar
        "rice wine vinegar": "rice vinegar",

        # Ginger slices
        "slice ginger": "fresh ginger",
        "inch slice ginger": "fresh ginger",
        "slices ginger": "fresh ginger",

        # Batch 4 analysis - OCR space-corrupted patterns
        "chick en": "chicken",
        "chick en breast": "chicken breast",
        "slice d": "sliced",
        "slice d mushrooms": "mushrooms",
        "pounded chick en breast": "chicken breast",

        # Batch 4 - historical/archaic ingredient names
        "yellow corn meal": "cornmeal",
        "sour milk": "buttermilk",
        "sweet milk or buttermilk": "buttermilk",
        "sour milk or buttermilk": "buttermilk",
        "naples biscuit": "ladyfinger",
        "naples biscuits": "ladyfinger",
        "fine loaf crumbs": "breadcrumbs",
        "seville oranges": "orange",
        "seville orange": "orange",
        "orange water": "orange extract",
        "rose water": "rose water",
        "races of ginger": "ginger",
        "saltpork": "salt pork",
        "salt pork": "salt pork",
        "beef tips": "beef stew meat",

        # Batch 4 - spice variants
        "sichuan peppercorns": "sichuan peppercorns",
        "szechuan peppercorns": "sichuan peppercorns",
        "regular peppercorns": "peppercorns",
        "white pepper corns": "peppercorns",

        # Batch 4 - cheese variants
        "slices swiss cheese": "swiss cheese",
        "swiss cheese slices": "swiss cheese",

        # Batch 4 - cherry variants
        "bing cherries": "cherries",
        "no. 2½ can bing cherries": "cherries",
        "cherry-flavored gelatin": "gelatin",

        # Batch 4 - stuffed olives
        "stuffed olives": "olives",
        "bottle stuffed olives": "olives",

        # Batch 4 - mixed herbs
        "mixed fresh herbs": "fresh herbs",
        "fresh herbs": "parsley",

        # Batch 4 - brand names
        "carnation": "evaporated milk",
        "carnation milk": "evaporated milk",
        "wesson oil": "vegetable oil",
        "grandma's molasses": "molasses",

        # Batch 4 - package/envelope normalization
        "unflavored gelatin": "gelatin",
        "envelopes unflavored gelatin": "gelatin",
        "1-oz instant oatmeal packet": "instant oatmeal",
        "instant oatmeal packet plain": "instant oatmeal",
        "instant oatmeal packets plain": "instant oatmeal",

        # Batch 4 - frozen vegetables
        "frozen pepper stir-fry": "mixed vegetables",
        "pepper stir-fry": "mixed vegetables",

        # Batch 4 - baby food (negligible calories for marinades)
        "baby juice": "apple juice",
        "baby food peaches": "peaches",
        "jars baby juice": "apple juice",
        "jars baby food peaches": "peaches",

        # Batch 4 manual repairs - additional patterns found
        "chopped red skinned apples": "apple",
        "red skinned apples": "apple",
        "green onion tops": "green onion",
        "finely chopped green onion tops": "green onion",
        "broken pecans": "pecans",
        "broken pecan meats": "pecans",
        "pecan meats": "pecans",
        "mixed stuffing": "stuffing mix",
        "savory deep dish pie crust": "pie crust",
        "deep dish pie crust": "pie crust",
        "half and half cream": "half and half",
        "cumin seeds": "cumin",
        "fine sugar": "sugar",
        "moist shredded coconut": "coconut",
        "moist": "coconut",
        "shredded coconut": "coconut",
        "one clove": "garlic",

        # Batch 5 manual repairs
        "stewing hen": "chicken",
        "rivels": "egg noodles",
        "zwieback": "crackers",
        "broccoli rabe": "broccoli",
        "chili flakes": "red pepper flakes",
        "anchovies": "fish",
        "tuna steaks": "tuna",
        "yellowfin tuna steaks": "tuna",
        "yellowfin tuna": "tuna",
        "napa cabbage": "cabbage",
        "chinese cabbage": "cabbage",
        "fish broth": "chicken broth",
        "crisp rice cereal": "rice krispies",
        "rice krispies": "puffed rice",
        "rose water": "vanilla extract",
        "rose-water": "vanilla extract",
        "granulated gelatin": "unflavored gelatin",
        "fruit juice": "orange juice",
        "fruit pulp": "applesauce",
        "salsa verde": "salsa",
        "fire-roasted salsa verde": "salsa",
        "fire-roasted salsa": "salsa",
        "pizza dough": "bread dough",
        "matchstick-cut carrots": "carrots",
        "presliced red onion": "red onion",
        "chili seasoning mix": "chili powder",
        "bouillon cubes": "bouillon",
        "beef bouillon cubes": "bouillon",
        "chicken bouillon cubes": "bouillon",
        "ground turkey breast": "ground turkey",

        # Batch 6 manual repairs
        "venison": "beef",
        "condensed mushroom soup": "cream of mushroom soup",
        "french onion soup": "onion soup",
        "salad dressing": "mayonnaise",
        "chopped sweet pickle": "sweet pickle relish",
        "dark molasses": "molasses",
        "mel ted margari ne": "margarine",
        "melted margarine": "margarine",
        "double crust": "pie crust",
        "lard": "shortening",
        "alum": "cream of tartar",
        "corned beef brisket": "corned beef",
        "dijon mustard": "mustard",
        "orange marmalade": "orange jam",
        "mashed potatoes": "potatoes",
        "bread dough": "yeast dough",
        "sherry": "white wine",
        "chinese rice wine": "white wine",
        "dry sherry": "white wine",
        "orange zest strips": "orange zest",
        "pearled barley": "barley",
        "anaheim chile peppers": "green chiles",
        "anaheim chiles": "green chiles",
        "melba toast crumbs": "bread crumbs",
        "apple butter": "applesauce",
        "peach syrup": "simple syrup",
        "white sauce": "bechamel sauce",
        "petite diced tomatoes": "diced tomatoes",
        "mild chili beans": "chili beans",
        "mild chili seasoning mix": "chili powder",
        "canned peaches": "peaches",

        # Batch 7 manual repairs
        "strawberry syrup": "simple syrup",
        "maraschino cherries": "cherries",
        "reserved chicken cooking liquid": "chicken broth",
        "chicken cooking liquid": "chicken broth",
        "slivered almonds": "almonds",
        "franks": "hot dogs",
        "cooked franks": "hot dogs",
        "corn tortillas": "tortillas",
        "grated pineapple": "pineapple",
        "roquefort cheese": "blue cheese",
        "roquefort": "blue cheese",
        "firm tofu": "tofu",
        "gai lan": "broccoli",
        "chinese broccoli": "broccoli",
        "uncle ben's": "",
        "converted brand rice": "rice",
        "caramel ice cream topping": "caramel sauce",
        "baker's semi-sweet chocolate": "semi-sweet chocolate",
        "cool whip whipped topping": "whipped cream",
        "cool whip": "whipped cream",
        "nilla wafer pie crust": "pie crust",
        "philadelphia cream cheese": "cream cheese",
        "sweet milk": "milk",
        "custard": "vanilla pudding",
        "thin custard": "vanilla pudding",
        "muenster": "cheese",
        "gouda cheese": "cheese",
        "muenster cheese": "cheese",
        "wild mushrooms": "mushrooms",
        "fregula": "couscous",
        "abbamele": "honey",
        "pastry flour": "flour",
        "cold fat": "shortening",
        "lavender": "vanilla extract",
        "dried lavender": "vanilla extract",
        "culinary lavender": "vanilla extract",
        "dandelion greens": "spinach",
        "young dandelion greens": "spinach",
        "oysters": "clams",
        "green tomatoes": "tomatoes",
        "celery seed": "celery salt",
        "mustard seed": "dry mustard",

        # Batch 8 manual repairs
        "anasazi beans": "pinto beans",
        "black forest ham": "ham",
        "smoked mozzarella": "mozzarella",
        "chicken cutlets": "chicken breast",
        "pearl ash": "baking soda",
        "double refined sugar": "sugar",
        "sweetest cream": "heavy cream",
        "cakes yeast": "yeast",
        "pot pie dough": "pie crust",
        "almond paste": "marzipan",
        "marzipan": "almonds",
        "apricot nectar": "apricot juice",
        "sriracha": "hot sauce",
        "sweet marjoram": "marjoram",
        "mace": "nutmeg",
        "mutton": "lamb",
        "jicama": "water chestnuts",
        "instant spanish rice": "rice",
        "picante sauce": "salsa",
        "colliflowers": "cauliflower",
        "fresh chives": "chives",
        "whole wheat pastry flour": "whole wheat flour",
        "wheat bran": "bran",
        "fat": "butter",
        "breakfast sausage": "sausage",
        "frozen pizza dough": "pizza dough",
        "biscuit mix": "bisquick",
        "bisquick": "flour",
        "pancake mix": "flour",
        "instant rice": "rice",

        # Batch 9: Synonyms from GrandmasRecipes script
        # Poultry variants
        "boneless chicken": "chicken breast",
        "boneless skinless chicken": "chicken breast",
        "chicken breast halves": "chicken breast",
        "boneless skinless chicken breast halves": "chicken breast",
        "chicken breast half": "chicken breast",
        "bone-in chicken": "chicken thighs",
        "chicken pieces": "chicken thighs",
        "cornish hen": "chicken",
        "cornish game hen": "chicken",
        "game hen": "chicken",
        "rock cornish hen": "chicken",
        "capon": "chicken",
        "rotisserie chicken": "chicken",
        "cooked chicken": "chicken breast",
        "leftover chicken": "chicken breast",
        "shredded chicken": "chicken breast",
        "diced chicken": "chicken breast",
        "cubed chicken": "chicken breast",

        # Sausage variants
        "andouille sausage": "sausage",
        "andouille": "sausage",
        "kielbasa": "sausage",
        "polish sausage": "sausage",
        "italian sausage links": "italian sausage",
        "hot italian sausage": "italian sausage",
        "mild italian sausage": "italian sausage",
        "sweet italian sausage": "italian sausage",
        "breakfast sausage links": "sausage",
        "sausage patties": "sausage",
        "pork sausage": "sausage",
        "turkey sausage": "sausage",
        "chicken sausage": "sausage",
        "smoked sausage": "sausage",
        "chorizo sausage": "chorizo",

        # Other meats
        "chuck roast": "beef roast",
        "pot roast": "beef roast",
        "eye of round": "beef roast",
        "rump roast": "beef roast",
        "sirloin roast": "beef roast",
        "top round": "beef roast",
        "bottom round": "beef roast",
        "brisket": "beef roast",
        "beef brisket": "beef roast",
        "corned beef brisket": "corned beef",
        "short ribs": "beef ribs",
        "beef short ribs": "beef ribs",
        "beef stew meat": "beef",
        "stew meat": "beef",
        "cubed beef": "beef",
        "london broil": "flank steak",
        "skirt steak": "flank steak",
        "hanger steak": "flank steak",
        "flat iron steak": "beef steak",
        "ribeye": "beef steak",
        "rib eye": "beef steak",
        "new york strip": "beef steak",
        "strip steak": "beef steak",
        "filet mignon": "beef tenderloin",
        "beef filet": "beef tenderloin",
        "tenderloin steak": "beef tenderloin",
        "tri-tip": "beef roast",
        "tri tip": "beef roast",

        # Pork variants
        "pork tenderloin": "pork loin",
        "pork roast": "pork loin",
        "pork shoulder": "pork",
        "pork butt": "pork",
        "boston butt": "pork",
        "pulled pork": "pork",
        "pork cutlets": "pork chops",
        "boneless pork chops": "pork chops",
        "bone-in pork chops": "pork chops",
        "thick-cut pork chops": "pork chops",
        "center-cut pork chops": "pork chops",
        "pork ribs": "pork",
        "baby back ribs": "pork",
        "spare ribs": "pork",
        "st louis ribs": "pork",
        "country-style ribs": "pork",

        # Seafood variants
        "cod fillets": "cod",
        "cod fillet": "cod",
        "haddock": "cod",
        "pollock": "cod",
        "halibut": "cod",
        "halibut fillet": "cod",
        "tilapia": "white fish",
        "tilapia fillets": "white fish",
        "swai": "white fish",
        "catfish fillets": "catfish",
        "salmon fillets": "salmon",
        "salmon fillet": "salmon",
        "sockeye salmon": "salmon",
        "atlantic salmon": "salmon",
        "wild salmon": "salmon",
        "smoked salmon": "salmon",
        "lox": "salmon",
        "trout": "salmon",
        "rainbow trout": "salmon",
        "steelhead": "salmon",
        "tuna steaks": "tuna",
        "ahi tuna": "tuna",
        "yellowfin tuna": "tuna",
        "swordfish": "tuna",
        "mahi mahi": "white fish",
        "mahi-mahi": "white fish",
        "sea bass": "white fish",
        "grouper": "white fish",
        "snapper": "white fish",
        "red snapper": "white fish",
        "flounder": "white fish",
        "sole": "white fish",

        # Shellfish
        "jumbo shrimp": "shrimp",
        "large shrimp": "shrimp",
        "medium shrimp": "shrimp",
        "small shrimp": "shrimp",
        "tiger shrimp": "shrimp",
        "gulf shrimp": "shrimp",
        "bay shrimp": "shrimp",
        "rock shrimp": "shrimp",
        "prawns": "shrimp",
        "langostino": "shrimp",
        "crawfish": "shrimp",
        "crayfish": "shrimp",
        "lobster tail": "lobster",
        "lobster tails": "lobster",
        "sea scallops": "scallops",
        "bay scallops": "scallops",
        "littleneck clams": "clams",
        "cherrystone clams": "clams",
        "manila clams": "clams",
        "razor clams": "clams",
        "mussels": "clams",
        "oysters": "clams",

        # Grain variants
        "polenta": "cornmeal",
        "instant polenta": "cornmeal",
        "coarse cornmeal": "cornmeal",
        "fine cornmeal": "cornmeal",
        "corn grits": "grits",
        "hominy grits": "grits",
        "instant grits": "grits",
        "stone-ground grits": "grits",
        "quinoa": "rice",
        "red quinoa": "rice",
        "white quinoa": "rice",
        "tri-color quinoa": "rice",
        "bulgur": "barley",
        "bulgur wheat": "barley",
        "cracked wheat": "barley",
        "farro": "barley",
        "freekeh": "barley",
        "wheat berries": "barley",
        "spelt": "barley",
        "kamut": "barley",
        "millet": "rice",
        "amaranth": "rice",
        "teff": "rice",
        "sorghum": "rice",
        "buckwheat": "oats",
        "buckwheat groats": "oats",
        "kasha": "oats",
        "steel-cut oats": "oats",
        "rolled oats": "oats",
        "old-fashioned oats": "oats",
        "quick oats": "oats",
        "instant oatmeal": "oats",
        "oat bran": "oats",

        # Bean variants
        "navy beans": "beans",
        "great northern beans": "beans",
        "cannellini beans": "beans",
        "white beans": "beans",
        "small white beans": "beans",
        "butter beans": "lima beans",
        "baby lima beans": "lima beans",
        "large lima beans": "lima beans",
        "flageolet beans": "beans",
        "cranberry beans": "pinto beans",
        "roman beans": "pinto beans",
        "borlotti beans": "pinto beans",
        "red beans": "kidney beans",
        "small red beans": "kidney beans",
        "dark red kidney beans": "kidney beans",
        "light red kidney beans": "kidney beans",
        "pink beans": "pinto beans",
        "black turtle beans": "black beans",
        "frijoles negros": "black beans",
        "black-eyed peas": "black eyed peas",
        "cowpeas": "black eyed peas",
        "field peas": "black eyed peas",
        "crowder peas": "black eyed peas",
        "split peas": "lentils",
        "green split peas": "lentils",
        "yellow split peas": "lentils",
        "red lentils": "lentils",
        "green lentils": "lentils",
        "brown lentils": "lentils",
        "french lentils": "lentils",
        "du puy lentils": "lentils",
        "beluga lentils": "lentils",

        # Pasta variants
        "rotini": "pasta",
        "fusilli": "pasta",
        "penne": "pasta",
        "penne rigate": "pasta",
        "rigatoni": "pasta",
        "ziti": "pasta",
        "mostaccioli": "pasta",
        "farfalle": "pasta",
        "bow tie pasta": "pasta",
        "bowtie pasta": "pasta",
        "bow ties": "pasta",
        "orecchiette": "pasta",
        "cavatappi": "pasta",
        "gemelli": "pasta",
        "campanelle": "pasta",
        "radiatore": "pasta",
        "wagon wheels": "pasta",
        "rotelle": "pasta",
        "shells": "pasta",
        "medium shells": "pasta",
        "large shells": "pasta",
        "jumbo shells": "pasta",
        "conchiglie": "pasta",
        "elbows": "macaroni",
        "elbow pasta": "macaroni",
        "elbow macaroni": "macaroni",
        "ditalini": "macaroni",
        "tubetti": "macaroni",
        "orzo": "pasta",
        "acini di pepe": "pasta",
        "pastina": "pasta",
        "stelline": "pasta",
        "alphabets": "pasta",
        "couscous": "pasta",
        "israeli couscous": "pasta",
        "pearl couscous": "pasta",
        "spaghetti": "pasta",
        "thin spaghetti": "pasta",
        "spaghettini": "pasta",
        "angel hair": "pasta",
        "capellini": "pasta",
        "linguine": "pasta",
        "fettuccine": "pasta",
        "tagliatelle": "pasta",
        "pappardelle": "pasta",
        "bucatini": "pasta",
        "perciatelli": "pasta",
        "vermicelli": "pasta",
        "lasagna noodles": "pasta",
        "lasagne": "pasta",
        "manicotti": "pasta",
        "cannelloni": "pasta",
        "egg noodles": "pasta",
        "wide egg noodles": "pasta",
        "extra wide egg noodles": "pasta",
        "kluski noodles": "pasta",
        "no-boil lasagna": "pasta",
        "oven-ready lasagna": "pasta",
        "rice noodles": "pasta",
        "pad thai noodles": "pasta",
        "lo mein noodles": "pasta",
        "ramen noodles": "pasta",
        "udon noodles": "pasta",
        "soba noodles": "pasta",
        "rice vermicelli": "pasta",
        "cellophane noodles": "pasta",
        "glass noodles": "pasta",
        "bean thread noodles": "pasta",

        # Vegetable variants
        "scallions": "green onions",
        "green onion": "green onions",
        "spring onions": "green onions",
        "collard greens": "spinach",
        "collards": "spinach",
        "mustard greens": "spinach",
        "turnip greens": "spinach",
        "beet greens": "spinach",
        "swiss chard": "spinach",
        "chard": "spinach",
        "rainbow chard": "spinach",
        "escarole": "spinach",
        "endive": "spinach",
        "belgian endive": "lettuce",
        "radicchio": "lettuce",
        "frisee": "lettuce",
        "arugula": "spinach",
        "rocket": "spinach",
        "watercress": "spinach",
        "baby spinach": "spinach",
        "baby kale": "kale",
        "lacinato kale": "kale",
        "tuscan kale": "kale",
        "curly kale": "kale",
        "dinosaur kale": "kale",
        "artichoke hearts": "asparagus",
        "artichokes": "asparagus",
        "hearts of palm": "asparagus",
        "palm hearts": "asparagus",
        "jicama": "water chestnuts",
        "daikon": "radishes",
        "daikon radish": "radishes",
        "turnips": "potatoes",
        "rutabaga": "potatoes",
        "parsnips": "carrots",
        "celeriac": "celery",
        "celery root": "celery",
        "fennel bulb": "celery",
        "fennel": "celery",
        "kohlrabi": "cabbage",
        "bok choy": "cabbage",
        "baby bok choy": "cabbage",
        "napa cabbage": "cabbage",
        "chinese cabbage": "cabbage",
        "savoy cabbage": "cabbage",
        "red cabbage": "cabbage",
        "green cabbage": "cabbage",
        "brussels sprouts": "broccoli",
        "broccolini": "broccoli",
        "broccoli rabe": "broccoli",
        "rapini": "broccoli",
        "broccoli florets": "broccoli",
        "cauliflower florets": "cauliflower",
        "romanesco": "cauliflower",

        # Squash variants
        "butternut squash": "squash",
        "acorn squash": "squash",
        "spaghetti squash": "squash",
        "delicata squash": "squash",
        "kabocha squash": "squash",
        "hubbard squash": "squash",
        "winter squash": "squash",
        "summer squash": "zucchini",
        "yellow squash": "zucchini",
        "crookneck squash": "zucchini",
        "pattypan squash": "zucchini",
        "chayote": "zucchini",

        # Pepper variants
        "bell pepper": "green pepper",
        "bell peppers": "green pepper",
        "red bell pepper": "red pepper",
        "yellow bell pepper": "green pepper",
        "orange bell pepper": "green pepper",
        "sweet pepper": "green pepper",
        "sweet peppers": "green pepper",
        "cubanelle pepper": "green pepper",
        "banana pepper": "green pepper",
        "pepperoncini": "green pepper",
        "pimento": "red pepper",
        "pimientos": "red pepper",
        "roasted red peppers": "red pepper",
        "jarred roasted peppers": "red pepper",
        "jalapeno pepper": "jalapeno",
        "jalapeno peppers": "jalapeno",
        "serrano pepper": "jalapeno",
        "serrano peppers": "jalapeno",
        "fresno pepper": "jalapeno",
        "poblano pepper": "green chilies",
        "poblano peppers": "green chilies",
        "anaheim pepper": "green chilies",
        "anaheim peppers": "green chilies",
        "hatch chiles": "green chilies",
        "pasilla pepper": "green chilies",
        "ancho chile": "green chilies",
        "guajillo chile": "green chilies",
        "chipotle pepper": "chipotle",
        "habanero": "jalapeno",
        "habanero pepper": "jalapeno",
        "scotch bonnet": "jalapeno",
        "thai chili": "jalapeno",
        "thai chilies": "jalapeno",
        "bird's eye chili": "jalapeno",

        # Mushroom variants
        "cremini mushrooms": "mushrooms",
        "cremini": "mushrooms",
        "baby bella mushrooms": "mushrooms",
        "baby bellas": "mushrooms",
        "button mushrooms": "mushrooms",
        "white mushrooms": "mushrooms",
        "portobello mushrooms": "mushrooms",
        "portobello": "mushrooms",
        "portabella": "mushrooms",
        "portobella": "mushrooms",
        "shiitake mushrooms": "mushrooms",
        "shiitake": "mushrooms",
        "oyster mushrooms": "mushrooms",
        "chanterelle mushrooms": "mushrooms",
        "chanterelles": "mushrooms",
        "porcini mushrooms": "mushrooms",
        "porcini": "mushrooms",
        "morel mushrooms": "mushrooms",
        "morels": "mushrooms",
        "enoki mushrooms": "mushrooms",
        "king trumpet mushrooms": "mushrooms",
        "maitake mushrooms": "mushrooms",
        "hen of the woods": "mushrooms",
        "dried mushrooms": "mushrooms",
        "dried porcini": "mushrooms",
        "dried shiitake": "mushrooms",
        "mushroom caps": "mushrooms",
        "sliced mushrooms": "mushrooms",

        # Tomato variants
        "roma tomatoes": "tomatoes",
        "plum tomatoes": "tomatoes",
        "grape tomatoes": "tomatoes",
        "cherry tomatoes": "tomatoes",
        "beefsteak tomatoes": "tomatoes",
        "heirloom tomatoes": "tomatoes",
        "vine-ripened tomatoes": "tomatoes",
        "campari tomatoes": "tomatoes",
        "san marzano tomatoes": "canned tomatoes",
        "fire-roasted tomatoes": "canned tomatoes",
        "fire roasted tomatoes": "canned tomatoes",
        "petite diced tomatoes": "canned tomatoes",
        "stewed tomatoes": "canned tomatoes",
        "crushed tomatoes": "canned tomatoes",
        "tomato puree": "tomato sauce",
        "tomato passata": "tomato sauce",
        "marinara sauce": "tomato sauce",
        "pizza sauce": "tomato sauce",
        "sun-dried tomato paste": "tomato paste",
        "double-concentrated tomato paste": "tomato paste",

        # Onion variants
        "yellow onion": "onion",
        "white onion": "onion",
        "red onion": "onion",
        "sweet onion": "onion",
        "vidalia onion": "onion",
        "walla walla onion": "onion",
        "maui onion": "onion",
        "spanish onion": "onion",
        "bermuda onion": "onion",
        "pearl onions": "onion",
        "cipollini onions": "onion",
        "boiling onions": "onion",
        "shallots": "onion",
        "shallot": "onion",
        "leeks": "onion",
        "leek": "onion",
        "ramps": "onion",
        "chives": "green onions",

        # Cheese variants
        "sharp cheddar": "cheddar cheese",
        "mild cheddar": "cheddar cheese",
        "medium cheddar": "cheddar cheese",
        "extra sharp cheddar": "cheddar cheese",
        "white cheddar": "cheddar cheese",
        "aged cheddar": "cheddar cheese",
        "colby cheese": "cheddar cheese",
        "colby jack": "cheddar cheese",
        "monterey jack cheese": "jack cheese",
        "pepper jack cheese": "jack cheese",
        "pepper jack": "jack cheese",
        "queso fresco": "feta cheese",
        "cotija cheese": "parmesan cheese",
        "cotija": "parmesan cheese",
        "pecorino romano": "parmesan cheese",
        "pecorino": "parmesan cheese",
        "asiago cheese": "parmesan cheese",
        "asiago": "parmesan cheese",
        "grana padano": "parmesan cheese",
        "parmigiano-reggiano": "parmesan cheese",
        "parmigiano reggiano": "parmesan cheese",
        "gruyere cheese": "swiss cheese",
        "gruyere": "swiss cheese",
        "emmental": "swiss cheese",
        "emmentaler": "swiss cheese",
        "jarlsberg": "swiss cheese",
        "fontina cheese": "swiss cheese",
        "fontina": "swiss cheese",
        "provolone cheese": "provolone",
        "smoked provolone": "provolone",
        "havarti cheese": "swiss cheese",
        "havarti": "swiss cheese",
        "gouda cheese": "swiss cheese",
        "gouda": "swiss cheese",
        "smoked gouda": "swiss cheese",
        "edam": "swiss cheese",
        "manchego": "swiss cheese",
        "muenster cheese": "swiss cheese",
        "muenster": "swiss cheese",
        "brie cheese": "brie",
        "camembert": "brie",
        "boursin": "cream cheese",
        "neufchatel": "cream cheese",
        "mascarpone cheese": "cream cheese",
        "mascarpone": "cream cheese",
        "ricotta cheese": "ricotta",
        "part-skim ricotta": "ricotta",
        "whole milk ricotta": "ricotta",
        "fresh mozzarella": "mozzarella",
        "buffalo mozzarella": "mozzarella",
        "mozzarella pearls": "mozzarella",
        "bocconcini": "mozzarella",
        "burrata": "mozzarella",
        "string cheese": "mozzarella",
        "crumbled feta": "feta cheese",
        "crumbled blue cheese": "blue cheese",
        "crumbled gorgonzola": "blue cheese",
        "gorgonzola": "blue cheese",
        "roquefort": "blue cheese",
        "stilton": "blue cheese",
        "danish blue": "blue cheese",
        "maytag blue": "blue cheese",

        # Batch 10: Specialty and prepared ingredients
        # Indian ingredients
        "indian puffed rice": "rice",
        "puffed rice": "rice",
        "sev": "noodles",
        "fine indian noodles": "noodles",
        "tamarind-date chutney": "jam",
        "tamarind chutney": "jam",
        "date chutney": "jam",
        "mint chutney": "jam",
        "cilantro chutney": "jam",
        "mango chutney": "jam",
        "serrano chile": "jalapeno",
        "serrano chiles": "jalapeno",
        "semolina": "flour",
        "pasta flour": "flour",
        "semolina flour": "flour",
        "durum flour": "flour",
        "00 flour": "flour",

        # Prepared/packaged items
        "container prepared hummus": "hummus",
        "prepared hummus": "hummus",
        "store-bought hummus": "hummus",
        "iceberg lettuce": "lettuce",
        "romaine lettuce": "lettuce",
        "boston lettuce": "lettuce",
        "bibb lettuce": "lettuce",
        "butter lettuce": "lettuce",
        "red leaf lettuce": "lettuce",
        "green leaf lettuce": "lettuce",
        "mixed greens": "lettuce",
        "spring mix": "lettuce",
        "salad mix": "lettuce",
        "container crumbled feta cheese": "feta cheese",
        "container feta": "feta cheese",
        "packages sliced smoked salmon": "salmon",
        "sliced smoked salmon": "salmon",
        "smoked salmon slices": "salmon",
        "packages pie dough mix": "pie crust",
        "pie dough mix": "pie crust",
        "refrigerated pie crust": "pie crust",
        "frozen pie crust": "pie crust",
        "pie dough": "pie crust",
        "puff pastry sheets": "pie crust",
        "puff pastry": "pie crust",
        "phyllo dough": "pie crust",
        "filo dough": "pie crust",
        "can white chicken meat": "chicken breast",
        "canned chicken": "chicken breast",
        "canned chicken breast": "chicken breast",
        "shredded rotisserie chicken": "chicken breast",
        "can sliced ripe olives": "olives",
        "sliced ripe olives": "olives",
        "sliced black olives": "olives",
        "pitted olives": "olives",
        "kalamata olives": "olives",
        "green olives": "olives",
        "stuffed olives": "olives",
        "shredded mexican cheese blend": "cheddar cheese",
        "mexican cheese blend": "cheddar cheese",
        "mexican blend cheese": "cheddar cheese",
        "taco cheese": "cheddar cheese",
        "fiesta blend cheese": "cheddar cheese",

        # Bread varieties
        "baguette": "french bread",
        "french baguette": "french bread",
        "italian bread": "french bread",
        "ciabatta": "french bread",
        "focaccia": "french bread",
        "pumpernickel bread": "rye bread",
        "pumpernickel": "rye bread",
        "dark rye": "rye bread",
        "marble rye": "rye bread",
        "sourdough bread": "bread",
        "sourdough": "bread",
        "brioche": "bread",
        "challah": "bread",
        "english muffins": "bread",
        "english muffin": "bread",
        "bagels": "bread",
        "bagel": "bread",
        "croissants": "bread",
        "croissant": "bread",
        "pita bread": "bread",
        "naan": "bread",
        "naan bread": "bread",
        "flatbread": "bread",
        "tortilla chips": "chips",
        "corn chips": "chips",
        "pita chips": "chips",

        # Nuts and dried fruit
        "candied pecans": "pecans",
        "glazed pecans": "pecans",
        "praline pecans": "pecans",
        "candied walnuts": "walnuts",
        "glazed walnuts": "walnuts",
        "candied almonds": "almonds",
        "sliced almonds": "almonds",
        "slivered almonds": "almonds",
        "blanched almonds": "almonds",
        "marcona almonds": "almonds",
        "roasted almonds": "almonds",
        "dry-roasted peanuts": "peanuts",
        "roasted peanuts": "peanuts",
        "honey roasted peanuts": "peanuts",
        "cocktail peanuts": "peanuts",
        "chopped peanuts": "peanuts",
        "pine nuts": "almonds",
        "pignoli": "almonds",
        "pistachios": "almonds",
        "pistachio": "almonds",
        "macadamia nuts": "almonds",
        "macadamias": "almonds",
        "hazelnuts": "almonds",
        "filberts": "almonds",
        "chestnuts": "almonds",
        "cashews": "almonds",
        "cashew pieces": "almonds",
        "mixed nuts": "almonds",

        # Canned fruits
        "cans sliced pears": "pears",
        "canned pears": "pears",
        "sliced pears": "pears",
        "canned peaches": "peaches",
        "sliced peaches": "peaches",
        "canned fruit cocktail": "mixed fruit",
        "fruit cocktail": "mixed fruit",
        "canned mandarin oranges": "oranges",
        "mandarin oranges": "oranges",
        "canned pineapple": "pineapple",
        "crushed pineapple": "pineapple",
        "pineapple chunks": "pineapple",
        "pineapple tidbits": "pineapple",
        "pineapple rings": "pineapple",
        "maraschino cherries": "cherries",

        # Deli meats
        "pepperoni slices": "pepperoni",
        "sliced pepperoni": "pepperoni",
        "turkey pepperoni": "pepperoni",
        "salami": "pepperoni",
        "hard salami": "pepperoni",
        "genoa salami": "pepperoni",
        "sopressata": "pepperoni",
        "capicola": "ham",
        "capocollo": "ham",
        "prosciutto": "ham",
        "pancetta": "bacon",
        "guanciale": "bacon",
        "canadian bacon": "ham",
        "black forest ham": "ham",
        "honey ham": "ham",
        "deli ham": "ham",
        "deli turkey": "turkey",
        "sliced turkey": "turkey",
        "turkey breast": "turkey",
        "roast beef": "beef",
        "deli roast beef": "beef",
        "corned beef": "beef",
        "pastrami": "beef",

        # Hot dogs and sausages
        "cooked franks": "hot dogs",
        "franks": "hot dogs",
        "frankfurters": "hot dogs",
        "wieners": "hot dogs",
        "beef franks": "hot dogs",
        "turkey dogs": "hot dogs",
        "cocktail franks": "hot dogs",
        "cocktail weiners": "hot dogs",
        "little smokies": "sausage",
        "lit'l smokies": "sausage",

        # Condiments and sauces
        "soy sauce": "soy sauce",
        "tamari": "soy sauce",
        "coconut aminos": "soy sauce",
        "teriyaki sauce": "soy sauce",
        "hoisin sauce": "soy sauce",
        "oyster sauce": "soy sauce",
        "fish sauce": "soy sauce",
        "worcestershire sauce": "soy sauce",
        "hot sauce": "salsa",
        "sriracha": "salsa",
        "tabasco": "salsa",
        "buffalo sauce": "salsa",
        "wing sauce": "salsa",
        "enchilada sauce": "salsa",
        "taco sauce": "salsa",
        "picante sauce": "salsa",
        "verde salsa": "salsa",
        "salsa verde": "salsa",
        "pico de gallo": "salsa",
        "for serving marinara sauce": "tomato sauce",
        "for dipping": "soy sauce",

        # Dairy and cream
        "plain yogurt": "yogurt",
        "vanilla yogurt": "yogurt",
        "greek yogurt": "yogurt",
        "nonfat yogurt": "yogurt",
        "non fat yogurt": "yogurt",
        "low-fat yogurt": "yogurt",
        "whole milk yogurt": "yogurt",
        "26% greek yogurt": "yogurt",
        "creme fraiche": "sour cream",
        "clotted cream": "heavy cream",
        "sweetened condensed milk": "milk",
        "condensed milk": "milk",
        "evaporated milk": "milk",
        "coconut milk": "milk",
        "coconut cream": "cream",
        "heavy whipping cream": "cream",
        "whipping cream": "cream",
        "half and half": "cream",
        "half-and-half": "cream",
        "light cream": "cream",
        "whipped cream": "cream",
        "cool whip": "cream",
        "whipped topping": "cream",

        # Baking items
        "caramel squares": "caramels",
        "caramel candies": "caramels",
        "kraft caramels": "caramels",
        "dulce de leche": "caramels",
        "caster sugar": "sugar",
        "castor sugar": "sugar",
        "superfine sugar": "sugar",
        "confectioners sugar": "powdered sugar",
        "icing sugar": "powdered sugar",
        "turbinado sugar": "brown sugar",
        "demerara sugar": "brown sugar",
        "muscovado sugar": "brown sugar",
        "raw sugar": "sugar",
        "cane sugar": "sugar",
        "coconut sugar": "brown sugar",
        "instant coffee": "coffee",
        "espresso powder": "coffee",
        "instant espresso": "coffee",
        "coffee granules": "coffee",
        "grated chocolate": "chocolate",
        "chocolate shavings": "chocolate",
        "chocolate curls": "chocolate",
        "mini chocolate chips": "chocolate chips",
        "white chocolate chips": "chocolate chips",
        "dark chocolate chips": "chocolate chips",
        "bittersweet chocolate": "chocolate",
        "semisweet chocolate": "chocolate",
        "unsweetened chocolate": "chocolate",
        "milk chocolate": "chocolate",
        "german chocolate": "chocolate",
        "cocoa nibs": "cocoa",
        "cacao powder": "cocoa",
        "dutch process cocoa": "cocoa",
        "natural cocoa": "cocoa",

        # Yeast and leavening
        "dry yeast": "yeast",
        "active dry yeast": "yeast",
        "instant yeast": "yeast",
        "rapid rise yeast": "yeast",
        "bread machine yeast": "yeast",
        "granulated yeast": "yeast",
        "package dry yeast": "yeast",
        "pkg yeast": "yeast",
        "packet yeast": "yeast",

        # Fruit items
        "large banana": "banana",
        "ripe banana": "banana",
        "mashed banana": "banana",
        "mashed ripe banana": "banana",
        "banana essence": "vanilla extract",
        "granny smith apples": "apples",
        "granny smith apple": "apples",
        "green apples": "apples",
        "gala apples": "apples",
        "fuji apples": "apples",
        "honeycrisp apples": "apples",
        "pink lady apples": "apples",
        "mcintosh apples": "apples",
        "red delicious apples": "apples",
        "golden delicious apples": "apples",
        "baked apples": "apples",
        "apple slices": "apples",

        # Alcohol
        "cognac": "brandy",
        "armagnac": "brandy",
        "calvados": "brandy",
        "grand marnier": "brandy",
        "cointreau": "brandy",
        "triple sec": "brandy",
        "orange liqueur": "brandy",
        "kahlua": "brandy",
        "coffee liqueur": "brandy",
        "amaretto": "brandy",
        "frangelico": "brandy",
        "bailey's": "cream",
        "irish cream": "cream",
        "champagne": "wine",
        "demi-sec champagne": "wine",
        "sparkling wine": "wine",
        "prosecco": "wine",
        "cava": "wine",
        "dry vermouth": "wine",
        "sweet vermouth": "wine",
        "sherry": "wine",
        "marsala": "wine",
        "port": "wine",
        "madeira": "wine",
        "sake": "wine",
        "mirin": "wine",
        "rice wine": "wine",
        "seltzer": "water",
        "club soda": "water",
        "sparkling water": "water",
        "tonic water": "water",
        "sparkling apple juice": "apple juice",

        # Juice and nectar
        "apricot nectar": "orange juice",
        "peach nectar": "orange juice",
        "mango nectar": "orange juice",
        "guava nectar": "orange juice",
        "cranberry juice": "orange juice",
        "grape juice": "orange juice",
        "pomegranate juice": "orange juice",
        "grapefruit juice": "orange juice",
        "pineapple juice": "orange juice",
        "tomato juice": "tomato sauce",
        "v8 juice": "tomato sauce",
        "clamato": "tomato sauce",
        "frozen orange juice": "orange juice",
        "can frozen orange juice": "orange juice",
        "bottle cranberry juice": "orange juice",

        # Canned items
        "cans biscuits": "biscuits",
        "can biscuits": "biscuits",
        "refrigerated biscuits": "biscuits",
        "pillsbury biscuits": "biscuits",
        "grands biscuits": "biscuits",
        "crescent rolls": "biscuits",
        "crescent roll dough": "biscuits",
        "can green chile strips": "green chilies",
        "green chile strips": "green chilies",
        "can green chile sauce": "green chilies",
        "can tomato sauce": "tomato sauce",
        "cans tomato sauce": "tomato sauce",
        "can mushroom soup": "cream of mushroom soup",
        "cans mushroom soup": "cream of mushroom soup",
        "condensed mushroom soup": "cream of mushroom soup",
        "cream of mushroom": "cream of mushroom soup",
        "condensed beef": "beef broth",
        "cans mushrooms": "mushrooms",
        "can mushrooms": "mushrooms",
        "canned mushrooms": "mushrooms",

        # Flax and seeds
        "ground flaxseed": "flaxseed",
        "ground flax seed": "flaxseed",
        "flax meal": "flaxseed",
        "flaxseed meal": "flaxseed",
        "chia seeds": "flaxseed",
        "hemp seeds": "flaxseed",
        "hemp hearts": "hemp seeds",
        "sunflower kernels": "sunflower seeds",
        "pepitas": "pumpkin seeds",
        # Note: sesame seeds, poppy seeds, caraway seeds are in database - no mapping needed

        # Herbs (fresh)
        "bunch dill": "dill",
        "fresh dill": "dill",
        "dill weed": "dill",
        "dill fronds": "dill",
        "grapefruit zest": "lemon zest",
        "orange zest": "lemon zest",
        "lime zest": "lemon zest",
        "citrus zest": "lemon zest",
        "loosely packed cilantro leaves": "cilantro",
        "cilantro leaves": "cilantro",
        "fresh cilantro": "cilantro",
        "coriander leaves": "cilantro",
        "mint leaves": "mint",
        "fresh mint": "mint",
        "spearmint": "mint",
        "peppermint": "mint",

        # Miscellaneous prepared items
        "salt-free all-purpose seasoning": "salt",
        "all-purpose seasoning": "salt",
        "seasoning blend": "salt",
        "mrs dash": "salt",
        "creamy peanut butter": "peanut butter",
        "smooth peanut butter": "peanut butter",
        "crunchy peanut butter": "peanut butter",
        "chunky peanut butter": "peanut butter",
        "natural peanut butter": "peanut butter",
        "almond butter": "peanut butter",
        "cashew butter": "peanut butter",
        "sunflower butter": "peanut butter",
        "pecan meats": "pecans",
        "walnut pieces": "walnuts",
        "walnut halves": "walnuts",
        "pecan pieces": "pecans",
        "pecan halves": "pecans",

        # Batch 11: More ingredient synonyms
        # Cereals and bran
        "bran cereal": "bran",
        "all-bran": "bran",
        "raisin bran": "bran",
        "bran flakes": "bran",
        "wheat bran": "bran",
        "oat bran": "oats",
        "bran flour": "bran",
        "grape nuts": "bran",
        "corn flakes": "cornmeal",
        "rice krispies": "rice",
        "cheerios": "oats",
        "granola": "oats",

        # Applesauce and fruit purees (applesauce is in DB)
        "applesauce": "applesauce",  # Exact match to prevent "apples" pattern matching
        "unsweetened applesauce": "applesauce",
        "apple sauce": "applesauce",
        "pumpkin puree": "pumpkin",
        "canned pumpkin": "pumpkin",
        "pumpkin pie filling": "pumpkin",
        "mashed sweet potato": "sweet potatoes",
        "mashed potatoes": "potatoes",

        # Berries
        "frozen berries": "berries",
        "fresh berries": "berries",
        "berry mix": "berries",
        "frozen strawberries": "strawberries",
        "frozen blueberries": "blueberries",
        "frozen raspberries": "raspberries",
        "frozen blackberries": "blackberries",
        "fresh strawberries": "strawberries",
        "fresh blueberries": "blueberries",
        "fresh raspberries": "raspberries",

        # Syrups
        "strawberry syrup": "sugar",
        "raspberry syrup": "sugar",
        "blueberry syrup": "sugar",
        "fruit syrup": "sugar",
        "simple syrup": "sugar",
        "malt syrup": "honey",
        "barley malt syrup": "honey",
        "rice syrup": "honey",
        "brown rice syrup": "honey",
        "golden syrup": "honey",
        "agave syrup": "honey",
        "agave nectar": "honey",
        "date syrup": "honey",
        "pomegranate molasses": "molasses",

        # Beef cuts
        "round steak": "beef steak",
        "cube steak": "beef steak",
        "minute steak": "beef steak",
        "swiss steak": "beef steak",
        "chicken fried steak": "beef steak",
        "salisbury steak": "ground beef",

        # Tortillas
        "corn tortillas": "tortillas",
        "flour tortillas": "tortillas",
        "whole wheat tortillas": "tortillas",
        "soft taco shells": "tortillas",
        "hard taco shells": "tortillas",
        "taco shells": "tortillas",
        "tostada shells": "tortillas",
        "burrito shells": "tortillas",
        "burrito tortillas": "tortillas",
        "fajita tortillas": "tortillas",

        # Coconut products
        "coconut flakes": "coconut",
        "shredded coconut": "coconut",
        "sweetened coconut": "coconut",
        "unsweetened coconut": "coconut",
        "toasted coconut": "coconut",
        "coconut chips": "coconut",
        "desiccated coconut": "coconut",

        # More bread items
        "ciabatta rolls": "french bread",
        "ciabatta roll": "french bread",
        "whole ciabatta": "french bread",
        "kaiser rolls": "bread",
        "hoagie rolls": "bread",
        "sub rolls": "bread",
        "hamburger buns": "bread",
        "hot dog buns": "bread",
        "slider buns": "bread",
        "dinner rolls": "bread",
        "parker house rolls": "bread",
        "crescent rolls": "biscuits",
        "hawaiian rolls": "bread",
        "kings hawaiian": "bread",
        "texas toast": "bread",
        "garlic bread": "bread",

        # Ham varieties
        "spiced ham": "ham",
        "baked ham": "ham",
        "glazed ham": "ham",
        "spiral ham": "ham",
        "bone-in ham": "ham",
        "boneless ham": "ham",
        "ham steak": "ham",
        "country ham": "ham",
        "city ham": "ham",
        "smoked ham": "ham",
        "virginia ham": "ham",

        # Bacon
        "bacon strips": "bacon",
        "bacon slices": "bacon",
        "thick-cut bacon": "bacon",
        "thin-cut bacon": "bacon",
        "center-cut bacon": "bacon",
        "applewood bacon": "bacon",
        "hickory bacon": "bacon",
        "maple bacon": "bacon",
        "turkey bacon": "bacon",
        "beef bacon": "bacon",

        # Greens (arugula/rocket)
        "fresh rocket": "spinach",
        "rocket leaves": "spinach",
        "baby rocket": "spinach",
        "wild arugula": "spinach",
        "baby arugula": "spinach",

        # Citrus
        "grapefruits": "grapefruit",
        "pink grapefruit": "grapefruit",
        "ruby red grapefruit": "grapefruit",
        "white grapefruit": "grapefruit",
        "grapefruit segments": "grapefruit",
        "grapefruit sections": "grapefruit",
        "blood orange": "oranges",
        "navel orange": "oranges",
        "cara cara orange": "oranges",
        "clementines": "oranges",
        "tangerines": "oranges",
        "satsumas": "oranges",
        "meyer lemon": "lemon",
        "meyer lemons": "lemon",
        "key limes": "lime",
        "persian limes": "lime",

        # Vegetables
        "eggplant": "squash",
        "egg plant": "squash",
        "aubergine": "squash",
        "japanese eggplant": "squash",
        "chinese eggplant": "squash",
        "baby eggplant": "squash",
        "pimiento": "red pepper",
        "pimientos": "red pepper",
        "whole pimiento": "red pepper",
        "diced pimientos": "red pepper",

        # Vinegars
        "cider vinegar": "vinegar",
        "apple cider vinegar": "vinegar",
        "white vinegar": "vinegar",
        "distilled vinegar": "vinegar",
        "red wine vinegar": "vinegar",
        "white wine vinegar": "vinegar",
        "sherry vinegar": "vinegar",
        "champagne vinegar": "vinegar",
        "balsamic vinegar": "vinegar",
        "rice vinegar": "vinegar",
        "seasoned rice vinegar": "vinegar",
        "malt vinegar": "vinegar",

        # Spices (whole vs ground)
        "whole cloves": "cloves",
        "ground cloves": "cloves",
        "whole allspice": "allspice",
        "ground allspice": "allspice",
        "whole nutmeg": "nutmeg",
        "freshly grated nutmeg": "nutmeg",
        "celery seed": "celery",
        "celery seeds": "celery",
        "mustard seed": "mustard",
        "mustard seeds": "mustard",
        "cumin seed": "cumin",
        "cumin seeds": "cumin",
        "coriander seed": "coriander",
        "coriander seeds": "coriander",
        "fennel seed": "fennel",
        "fennel seeds": "fennel",
        "dill seed": "dill",
        "dill seeds": "dill",
        "anise seed": "fennel",
        "anise seeds": "fennel",
        "star anise": "fennel",

        # Chili and pepper powders
        "mild chili powder": "chili powder",
        "hot chili powder": "chili powder",
        "ancho chili powder": "chili powder",
        "chipotle chili powder": "chili powder",
        "cayenne pepper": "chili powder",
        "ground cayenne": "chili powder",
        "red pepper flakes": "chili powder",
        "crushed red pepper": "chili powder",
        "aleppo pepper": "chili powder",
        "gochugaru": "chili powder",
        "korean chili flakes": "chili powder",

        # Breakfast meats
        "breakfast sausage": "sausage",
        "pork sausage": "sausage",
        "turkey sausage": "sausage",
        "chicken sausage": "sausage",
        "veggie sausage": "sausage",
        "sausage links": "sausage",
        "sausage patties": "sausage",
        "chorizo sausage": "chorizo",
        "mexican chorizo": "chorizo",
        "spanish chorizo": "chorizo",

        # Pizza dough
        "frozen pizza dough": "pizza dough",
        "refrigerated pizza dough": "pizza dough",
        "store-bought pizza dough": "pizza dough",
        "pizza crust": "pizza dough",
        "prebaked pizza crust": "pizza dough",
        "boboli": "pizza dough",
        "naan pizza crust": "pizza dough",
        "flatbread pizza crust": "pizza dough",

        # Measurement/equipment words to filter
        "pkg": "",
        "package": "",
        "packages": "",
        "can": "",
        "cans": "",
        "jar": "",
        "jars": "",
        "bag": "",
        "bags": "",
        "box": "",
        "boxes": "",
        "bunch": "",
        "bunches": "",
        "handful": "",
        "handfuls": "",
        "slice": "",
        "slices": "",
        "strip": "",
        "strips": "",
        "piece": "",
        "pieces": "",
        "whole": "",
        "inch": "",
        "inches": "",

        # Juice concentrate
        "apple juice concentrate": "apple juice",
        "frozen apple juice concentrate": "apple juice",
        "orange juice concentrate": "orange juice",
        "frozen orange juice concentrate": "orange juice",
        "grape juice concentrate": "grape juice",
        "lemon juice concentrate": "lemon juice",
        "lime juice concentrate": "lime juice",
        "pineapple juice concentrate": "pineapple juice",

        # More misc items
        "boiling water": "water",
        "cold water": "water",
        "warm water": "water",
        "hot water": "water",
        "ice water": "water",
        "room temperature water": "water",
        "honey": "honey",
        "warmed honey": "honey",
        "raw honey": "honey",
        "local honey": "honey",
        "clover honey": "honey",
        "wildflower honey": "honey",
        "manuka honey": "honey",
        "for serving": "",
        "for topping": "",
        "for garnish": "",
        "for dipping": "",
        "optional": "",

        # Batch 13: More ingredient synonyms
        # Vegetables & Produce
        "roma tomato": "roma tomatoes",
        "plum tomato": "roma tomatoes",
        "medium roma tomatoes": "roma tomatoes",
        "medium tomatoes": "tomatoes",
        "medium tomato": "tomatoes",
        "diced tomatoes": "canned tomatoes",
        "sliced cucumber": "cucumber",
        "diced cucumber": "cucumber",
        "chopped cucumber": "cucumber",
        "english cucumber": "cucumber",
        "seedless cucumber": "cucumber",
        "peeled jicama": "jicama",
        "julienne-cut peeled jicama": "jicama",
        "julienne jicama": "jicama",
        "yellow squash": "zucchini",

        # Seafood
        "yellowfin tuna steaks": "tuna",
        "yellowfin tuna": "tuna",
        "ahi tuna steaks": "tuna",
        "tuna steak": "tuna",
        "cod fillet": "cod",
        "scrubbed mussels": "mussels",
        "debearded mussels": "mussels",

        # Meats
        "ground veal or turkey": "ground veal",
        "top sirloin beef": "beef steak",
        "top sirloin": "beef steak",
        "boneless pork steak": "pork chops",
        "pork steak": "pork chops",
        "beef round steak": "beef steak",
        "boneless beef chuck roast": "beef roast",
        "guanciale": "pancetta",
        "finely chopped pancetta": "pancetta",

        # Cheese
        "smoked mozzarella": "mozzarella",
        "fresh mozzarella": "mozzarella",
        "shredded mozzarella": "mozzarella",
        "grated mozzarella": "mozzarella",
        "grated fresh parmigiano-reggiano cheese": "parmesan cheese",
        "fresh parmigiano-reggiano": "parmesan cheese",
        "parmigiano-reggiano": "parmesan cheese",
        "grated parmesan": "parmesan cheese",
        "freshly grated parmesan": "parmesan cheese",
        "shredded cheddar cheese": "cheddar cheese",
        "shredded monterey jack cheese": "monterey jack cheese",
        "shredded mexican-blend cheese": "cheddar cheese",
        "mexican blend cheese": "cheddar cheese",
        "sharp cheddar": "cheddar cheese",
        "longhorn cheese": "cheddar cheese",
        "long horn cheese": "cheddar cheese",
        "feta cheese": "feta",
        "crumbled feta": "feta",
        "crumbled cotija cheese": "cotija cheese",
        "soft goat cheese": "goat cheese",

        # Sauces & condiments
        "shoyu": "soy sauce",
        "tamari": "soy sauce",
        "red russian dressing": "russian dressing",
        "kraft creamy french dressing": "creamy french dressing",
        "old world style pasta sauce": "tomato sauce",
        "ragu pasta sauce": "tomato sauce",
        "jar taco sauce": "taco sauce",
        "bottle tomato catsup": "ketchup",
        "tomato catsup": "ketchup",
        "bottle russian dressing": "russian dressing",

        # Bread & dough
        "savory deep dish pie crust": "deep dish pie crust",
        "frozen puff pastry": "puff pastry",
        "thawed puff pastry": "puff pastry",
        "pita bread": "pita",
        "sandwich bread": "bread",
        "white sandwich bread": "bread",
        "whole wheat bread": "bread",

        # Alcohol & beverages
        "apricot brandy": "brandy",
        "cooking wine": "white wine",
        "unsweetened pineapple juice": "pineapple juice",

        # Spices & seasonings
        "tarragon leaves": "tarragon",
        "fresh tarragon": "tarragon",
        "dried tarragon": "tarragon",
        "dried oregano leaves": "oregano",
        "dried thyme leaves": "thyme",
        "crushed oregano": "oregano",
        "coriander powder": "coriander",
        "garam masala powder": "garam masala",
        "taco seasoning": "chili powder",
        "chili seasoning mix": "chili powder",
        "taco seasoning mix": "chili powder",
        "mild chili seasoning": "chili powder",
        "onion soup mix": "onion soup",
        "dry onion soup": "onion soup",
        "lipton onion soup": "onion soup",

        # Canned goods
        "can black olives": "black olives",
        "ripe black olives": "black olives",
        "sliced black olives": "black olives",
        "pitted black olives": "black olives",
        "can kidney beans": "kidney beans",
        "can black beans": "black beans",
        "can pinto beans": "pinto beans",
        "can chili beans": "chili beans",
        "can cannellini beans": "cannellini beans",
        "can great northern beans": "great northern beans",
        "can refried beans": "refried beans",
        "can tomato sauce": "tomato sauce",
        "can stewed tomatoes": "canned tomatoes",
        "can diced tomatoes": "canned tomatoes",
        "can tomato juice": "tomato juice",
        "can tomato puree": "tomato puree",
        "can green chiles": "green chilies",
        "can diced green chiles": "green chilies",
        "can cream of mushroom soup": "mushroom soup",
        "can cream of chicken soup": "cream of chicken soup",
        "can chicken broth": "chicken broth",
        "can beef broth": "beef broth",
        "can mixed vegetables": "mixed vegetables",
        "can corn": "corn",
        "canned pineapple chunk": "pineapple chunks",

        # Preserves & sweets
        "jar apricot preserves": "apricot preserves",
        "apricot jam": "apricot preserves",
        "strawberry preserves": "jam",
        "fruit preserves": "jam",
        "grape jelly": "jam",

        # Misc
        "hot dogs": "hot dog",
        "frankfurters": "hot dog",
        "franks": "hot dog",
        "lesueur peas": "peas",
        "petit pois": "peas",
        "instant yeast": "yeast",
        "active dry yeast": "yeast",
        "dry yeast": "yeast",
        "rapid rise yeast": "yeast",
        "yeast cake": "yeast",
        "cake yeast": "yeast",
        "biscuit baking mix": "bisquick",
        "baking mix": "bisquick",
        "watercress": "arugula",
        "tough stems removed": "",
        "cooked rice": "rice",
        "leftover rice": "rice",
        "steamed rice": "rice",
        "chopped walnuts": "walnuts",
        "chopped pecans": "pecans",
        "chopped almonds": "almonds",

        # Batch 14: Additional synonyms for common variations
        # Onion variants
        "purple onion": "red onion",
        "spanish onion": "onion",
        "yellow onion": "onion",
        "sweet onion": "onion",
        "vidalia onion": "onion",
        "walla walla onion": "onion",
        # Lettuce types -> lettuce (base mapping)
        "bibb lettuce": "lettuce",
        "boston lettuce": "lettuce",
        "butterhead lettuce": "lettuce",
        "romaine lettuce": "lettuce",
        "iceberg lettuce": "lettuce",
        "leaf lettuce": "lettuce",
        "mixed greens": "lettuce",
        "salad greens": "lettuce",
        "spring mix": "lettuce",
        # Celery variants
        "chopped celery": "celery",
        "celery stalk": "celery",
        "celery stalks": "celery",
        "celery ribs": "celery",
        "celery rib": "celery",
        # Carrot variants
        "chopped carrot": "carrots",
        "shredded carrot": "carrots",
        "carrot sticks": "carrots",
        # Pepper variants
        "sweet red pepper": "red pepper",
        "red bell pepper": "red pepper",
        "green bell pepper": "green pepper",
        "yellow bell pepper": "yellow pepper",
        "orange bell pepper": "orange pepper",
        "bell pepper": "green pepper",
        # Herbs with sprigs/leaves
        "thyme sprigs": "thyme",
        "thyme sprig": "thyme",
        "parsley sprigs": "parsley",
        "parsley sprig": "parsley",
        "dill sprigs": "dill",
        "rosemary sprigs": "rosemary",
        "oregano leaves": "oregano",
        "thyme leaves": "thyme",
        "basil leaves": "basil",
        "sage leaves": "sage",
        "mint leaves": "mint",
        # Mayonnaise variants
        "reduced-fat mayonnaise": "light mayonnaise",
        "low-fat mayonnaise": "light mayonnaise",
        "fat free mayonnaise": "light mayonnaise",
        "mayo": "mayonnaise",
        # Sesame oil
        "toasted sesame oil": "dark sesame oil",
        "asian sesame oil": "dark sesame oil",
        # Large/medium/small fruit
        "large lemon": "lemon",
        "medium lemon": "lemon",
        "small lemon": "lemon",
        "large lime": "lime",
        "medium lime": "lime",
        "large orange": "oranges",
        "medium orange": "oranges",
        "navel orange": "oranges",
        "valencia orange": "oranges",
        # Cheese variants
        "parmigiano-reggiano cheese": "parmesan cheese",
        "parmigiano-reggiano": "parmesan cheese",
        "pecorino romano": "parmesan cheese",
        "grated parmesan": "parmesan cheese",
        "shaved parmesan": "parmesan cheese",
        "blue cheese": "blue cheese crumbles",
        "gorgonzola": "blue cheese crumbles",
        # Pepper/spices
        "coarsely ground pepper": "black pepper",
        "freshly ground pepper": "black pepper",
        "ground black pepper": "black pepper",
        "cracked pepper": "black pepper",
        "crushed red pepper": "red pepper flakes",
        "red pepper flakes": "red pepper flakes",
        "italian seasoning": "italian herbs",
        # Meat variants
        "boneless skinless chicken": "chicken breast",
        "chicken cutlets": "chicken breast",
        "chicken tenders": "chicken breast",
        "skinless chicken thighs": "chicken thighs",
        "bone-in chicken": "chicken",
        # Pasta
        "penne pasta": "pasta",
        "spaghetti": "pasta",
        "linguine": "pasta",
        "fettuccine": "pasta",
        "rigatoni": "pasta",
        "farfalle": "pasta",
        "rotini": "pasta",
        "angel hair": "pasta",
        "egg noodles": "pasta",

        # Batch 15: More synonyms for remaining variations
        # Ginger variants
        "gingerroot": "fresh gingerroot",
        "fresh ginger": "fresh gingerroot",
        "ginger root": "fresh gingerroot",
        "minced ginger": "fresh gingerroot",
        "grated ginger": "fresh gingerroot",
        # Mushroom variants
        "sliced mushrooms": "fresh mushrooms",
        "white mushrooms": "fresh mushrooms",
        "cremini mushrooms": "fresh mushrooms",
        "button mushrooms": "fresh mushrooms",
        "baby bella mushrooms": "fresh mushrooms",
        # Cheese variants
        "mozzarella cheese": "part-skim mozzarella cheese",
        "shredded mozzarella": "part-skim mozzarella cheese",
        "fresh mozzarella": "part-skim mozzarella cheese",
        "monterey jack cheese": "jack cheese",
        "pepper jack cheese": "jack cheese",
        "colby jack cheese": "jack cheese",
        "crumbled blue cheese": "blue cheese crumbles",
        # Pepper variants
        "green pepper": "medium green pepper",
        "large green pepper": "medium green pepper",
        "small green pepper": "medium green pepper",
        "diced green pepper": "medium green pepper",
        # Avocado
        "ripe avocado": "medium ripe avocado",
        "large avocado": "medium ripe avocado",
        "haas avocado": "medium ripe avocado",
        "hass avocado": "medium ripe avocado",
        # Zucchini
        "small zucchini": "medium zucchini",
        "large zucchini": "medium zucchini",
        "diced zucchini": "zucchini",
        "sliced zucchini": "zucchini",
        # Broth variants
        "low-sodium chicken broth": "reduced-sodium chicken broth",
        "low sodium chicken broth": "reduced-sodium chicken broth",
        "less sodium chicken broth": "reduced-sodium chicken broth",
        "low-sodium beef broth": "reduced-sodium beef broth",
        "low sodium beef broth": "reduced-sodium beef broth",
        # Sauce variants
        "hot sauce": "pepper sauce",
        "hot pepper sauce": "pepper sauce",
        "tabasco": "pepper sauce",
        "franks hot sauce": "pepper sauce",
        "louisiana hot sauce": "pepper sauce",
        "sriracha": "pepper sauce",
        "bbq sauce": "barbecue sauce",
        "white sauce": "bechamel sauce",
        # Section headers (to ignore)
        "sauce:": "",
        "filling:": "",
        "topping:": "",
        "dressing:": "",
        "salad:": "",
        "for the sauce:": "",
        "for the filling:": "",
        "for the topping:": "",
        # Meat variants
        "pork chops": "pork loin chops",
        "boneless pork chops": "pork loin chops",
        "thick-cut pork chops": "pork loin chops",
        "ground turkey": "lean ground turkey",
        "extra lean ground turkey": "lean ground turkey",
        "flank steak": "beef steak",
        "sirloin steak": "beef steak",
        "strip steak": "beef steak",
        "ribeye steak": "beef steak",
        "tilapia": "white fish",
        "halibut": "white fish",
        "mahi mahi": "white fish",
        "snapper": "white fish",
        "sea bass": "white fish",
        # Seasoning variants
        "lemon pepper": "lemon-pepper seasoning",
        "creole seasoning": "cajun seasoning",
        "blackening seasoning": "cajun seasoning",
        "dry mustard": "ground mustard",
        "mustard powder": "ground mustard",
        # Protect sausage from partial match on "sage"
        "sausage": "sausage",
        "lb sausage": "sausage",
        "pkg sausage": "sausage",
        "package sausage": "sausage",
        "sage": "rubbed sage",
        "dried sage": "rubbed sage",
        "ground sage": "rubbed sage",
        # Garnishes (minimal calories)
        "lemon wedges": "lemon",
        "lime wedges": "lime",
        "lime wedge": "lime",
        "orange wedges": "oranges",

        # Batch 16: More synonyms for remaining variations
        # Alcohol
        "blanco tequila": "silver tequila",
        "white tequila": "silver tequila",
        "reposado tequila": "tequila",
        "gold tequila": "tequila",
        "triple sec": "orange liqueur",
        "cointreau": "orange liqueur",
        "grand marnier": "orange liqueur",
        "orange liquor": "orange liqueur",
        "white rum": "light rum",
        "spiced rum": "dark rum",
        "coconut rum": "light rum",
        # Asian ingredients
        "red miso": "miso paste",
        "yellow miso": "miso paste",
        "awase miso": "miso paste",
        "hoisin": "hoisin sauce",
        "chinese bbq sauce": "char siu sauce",
        "seaweed sheets": "nori sheets",
        "sushi nori": "nori sheets",
        "roasted seaweed": "nori sheets",
        # Pickles
        "kosher dill pickles": "dill pickles",
        "pickle spears": "dill pickle spears",
        "pickle juice": "dill pickle juice",
        # Cheese
        "sliced provolone": "provolone",
        "provolone cheese": "provolone",
        "sharp provolone": "provolone",
        # Carrot sizes
        "carrots": "carrots",
        "baby carrots": "carrots",
        # Beets
        "beets": "medium beets",
        "red beets": "medium beets",
        "golden beets": "medium beets",
        # Chiles
        "green chilli": "green chiles",
        "green chillies": "green chiles",
        "diced green chiles": "green chiles",
        "chopped green chiles": "green chiles",
        "green chilies": "green chiles",
        # Rice
        "minute rice": "quick-cooking rice",
        "instant rice": "quick-cooking rice",
        # Salt
        "sea salt": "fine salt",
        "kosher salt": "salt",
        "table salt": "salt",
        "flaky salt": "salt",
        # Vegetables
        "string beans": "green beans",
        "snap beans": "green beans",
        "french beans": "green beans",
        "haricots verts": "green beans",
        # Bacon variants
        "broiled bacon": "bacon",
        "crispy bacon": "bacon",
        "cooked bacon": "bacon",
        "crumbled bacon": "bacon",
        "fried bacon": "bacon",
        # Cottage cheese variants
        "dry cottage cheese": "cottage cheese",
        "creamed cottage cheese": "cottage cheese",
        "small curd cottage cheese": "cottage cheese",
        "large curd cottage cheese": "cottage cheese",
        "low-fat cottage cheese": "cottage cheese",
        "lowfat cottage cheese": "cottage cheese",
        "chive cottage cheese": "cottage cheese",
        # Tuna variants
        "tuna fish": "tuna",
        "canned tuna": "tuna",
        "tuna salad": "tuna",
        "albacore tuna": "tuna",
        "chunk light tuna": "tuna",
        # Dried beef
        "chipped beef": "dried beef",
        # Nuts
        "hickory nuts": "pecans",
        "butternuts": "walnuts",
        # Fruit cocktail
        "fruit cocktail": "mixed fruit",
        "canned fruit cocktail": "mixed fruit",
        # Blue cheese
        "roquefort": "blue cheese",
        "roquefort cheese": "blue cheese",
        "gorgonzola cheese": "blue cheese",
        "stilton": "blue cheese",
        # Bread variants
        "bread cubes": "bread",
        "day-old bread": "bread",
        "stale bread": "bread",
        "french bread cubes": "bread",
        "italian bread cubes": "bread",
        "bread crumbs": "breadcrumbs",
        # Bacon variants
        "apple smoked bacon": "bacon",
        "applewood bacon": "bacon",
        "apple-smoked bacon": "bacon",
        "hickory smoked bacon": "bacon",
        "thick-cut bacon": "bacon",
        "center-cut bacon": "bacon",
        "turkey bacon": "bacon",
        # Ground beef
        "hamburg": "ground beef",
        "hamburger": "ground beef",
        "hamburger meat": "ground beef",
        "ground chuck": "ground beef",
        "ground round": "ground beef",
        "ground sirloin": "ground beef",
        # Boiled/cooked meats
        "boiled beef": "beef",
        "cooked beef": "beef",
        "leftover beef": "beef",
        "leftover meat": "beef",
        # Lima beans
        "dried limas": "lima beans",
        "limas": "lima beans",
        "butter beans": "lima beans",
        "large lima beans": "lima beans",
        "baby lima beans": "lima beans",
        # Rice variants
        "long-cooking rice": "rice",
        "long grain rice": "rice",
        "short grain rice": "rice",
        "converted rice": "rice",
        "parboiled rice": "rice",
        "minute rice": "rice",
        "instant rice": "rice",
        "basmati rice": "rice",
        "jasmine rice": "rice",
        # Meat
        "lamb": "ground lamb",
        "ground lamb or beef": "ground lamb",
        "beef or lamb": "ground beef",
        "short ribs": "beef ribs",
        "beef short ribs": "beef ribs",
        "spare ribs": "beef ribs",
        "crab sticks": "imitation crabmeat",
        "imitation crabmeat sticks": "imitation crabmeat",
        "surimi": "imitation crabmeat",
        "krab": "imitation crabmeat",
        # OCR artifacts to ignore
        "specialist kit": "",
        "congress st": "",
        "tbutter": "butter",
        "tflour": "flour",
        "pn salt": "salt",
        "^peck": "",
        # Juice parsing issues
        "juice from 1/2 lime juice": "lime juice",
        "juice 1 lime": "lime juice",
        "squeeze lime juice": "lime juice",
        "lime juice)": "lime juice",
        "fresh lime juice": "lime juice",
        "fresh lemon juice": "lemon juice",
        # Misc
        "raisin": "raisins",
        "tomato liquid": "tomato juice",
        "torn romaine": "lettuce",
        "g feta": "feta",
        "g coriander": "coriander",
        # Of choice patterns - ignore
        "seasonings of choice": "",
        "of choice": "",
        "fillings of choice": "",
        "omelet fillings of choice": "",
        # Steaks
        "skirt steak": "beef steak",
        "flank steak": "beef steak",
        "sirloin steak": "beef steak",
        "strip steak": "beef steak",
        "ribeye steak": "beef steak",
        "rib eye steak": "beef steak",
        # Apples variants
        "granny smith apples": "apple",
        "granny smith apple": "apple",
        "gala apples": "apple",
        "honeycrisp apples": "apple",
        "fuji apples": "apple",
        "mcintosh apples": "apple",
        # Oils
        "avocado oil": "olive oil",
        "vegetable oil": "oil",
        "canola oil": "oil",
        "corn oil": "oil",
        "peanut oil": "oil",
        "coconut oil": "oil",
        # Brownie mix (uses specific brownie mix entry)
        "cake mix": "chocolate cake mix",
        # Spare ribs
        "spareribs": "pork ribs",
        "spare ribs": "pork ribs",
        "baby back ribs": "pork ribs",
        "st louis ribs": "pork ribs",
        # Schnitz (PA Dutch dried apples)
        "schnitz": "dried apples",
        # Pimento
        "pimento": "red pepper",
        "pimientos": "red pepper",
        # Chicken livers
        "chicken livers": "chicken liver",

        # Batch 17: More synonyms for parsing issues
        # Parsing artifacts (extra words)
        "plus olive oil": "olive oil",
        "to 4 tablespoons lemon juice": "lemon juice",
        "assorted fresh vegetables": "mixed vegetables",
        "guacamole)": "guacamole",
        # Removed: "mixed" → "mixed vegetables" - too broad, matches "mixed berries" incorrectly
        "ml tequila blanco": "tequila",
        "dashes angostura bitters": "angostura bitters",
        "x 75ml ice lolly moulds": "",
        "round rice papers": "rice papers",
        "crispy chow mein noodles": "chow mein noodles",
        "grams bread flour": "flour",
        "grams quick-rise yeast": "yeast",
        "dry long grain rice": "rice",
        "avocado and yogurt": "avocado",
        "powdered saltpeter": "salt",
        "to the gallon fruit": "",
        "at a time": "",
        "to the pound": "",
        "tart dark jelly": "grape jelly",
        "rich stale cake": "cake",
        "tajín seasoning to sprinkle": "tajin",
        # Citrus/zest
        "orange or tangerine zest": "orange zest",
        "tangerine zest": "orange zest",
        "rind of 1 lemon": "lemon zest",
        "grated rind of 1 lemon": "lemon zest",
        "grated peel of 1 lemon": "lemon zest",
        "rind of ¾ lemon": "lemon zest",
        "grated rind of ¾ lemon": "lemon zest",
        "juice of a lemon": "lemon juice",
        "juice of 1 lemon": "lemon juice",
        "juice of ½ lemon": "lemon juice",
        # Egg parts
        "yolk of 1 egg": "egg yolk",
        "egg yolks": "egg yolk",
        "white of 1 egg": "egg white",
        "egg whites": "egg white",
        # Milk variants
        "thick milk": "milk",
        "sweet milk": "milk",
        "sour milk": "buttermilk",
        # Butter variants
        "butter or substitute": "butter",
        "butter or margarine": "butter",
        "margarine or butter": "butter",
        "shortening or butter": "butter",
        # Fruit
        "fruit salad": "mixed fruit",
        "fruit": "mixed fruit",
        "fresh fruit": "mixed fruit",
        # Cinnamon
        "stick cinnamon": "cinnamon stick",
        "cinnamon sticks": "cinnamon stick",
        # Syrup
        "peach syrup": "syrup",
        "canned peach syrup": "syrup",
        "hot canned peach syrup": "syrup",
        # Broth alternatives
        "rum or chicken broth": "chicken broth",
        "wine or chicken broth": "chicken broth",
        "wine or broth": "chicken broth",
        # Vegetables
        "sweet yellow pepper": "medium sweet yellow pepper",
        "yellow pepper": "medium sweet yellow pepper",
        "red grapefruit": "medium red grapefruit",
        "pink grapefruit": "medium red grapefruit",
        "beet": "beetroot",
        "raw beet": "beetroot",
        "cooked beet": "beetroot",
        # Asian
        "spring roll wrappers": "rice papers",
        "egg roll wrappers": "rice papers",
        "vietnamese rice papers": "rice papers",
        "fried chow mein noodles": "chow mein noodles",
        "crunchy chow mein noodles": "chow mein noodles",
        "la choy chow mein noodles": "chow mein noodles",
        # Bitters
        "bitters": "angostura bitters",
        "aromatic bitters": "angostura bitters",
        # Beans
        "refried beans": "refried pinto beans",
        # Chiles
        "canned green chiles": "green chiles",
        "mild green chiles": "green chiles",
        "diced green chilies": "green chiles",
        # Whiskey
        "good whiskey": "whiskey",
        "bourbon whiskey": "whiskey",
        "rye whiskey": "whiskey",
        "irish whiskey": "whiskey",
        # Chipotle
        "chipotle chili in adobo": "chipotle in adobo",
        "chipotle peppers in adobo": "chipotle in adobo",
        "chipotles in adobo": "chipotle in adobo",
        "adobo sauce": "chipotle in adobo",
        # Coriander
        "ground coriander": "coriander",
        "coriander seeds": "coriander",
        "coriander powder": "coriander",
        # Minimal ingredients - treat as zero calorie
        "little pepper": "",
        "a little pepper": "",
        "little salt": "",
        "a little salt": "",
        "little nutmeg": "",
        "a little nutmeg": "",
        "dash of allspice": "allspice",
        "dash of cinnamon": "cinnamon",
        "dash of allspice and cinnamon": "",
        "dash of steak sauce": "",
        "spinach liquid": "",
        "rennet tablet": "",
        "dumpling recipe": "",
        # Pumpkin variants
        "steamed pumpkin": "pumpkin",
        "mashed pumpkin": "pumpkin",
        "mashed pumpkin or squash": "pumpkin",
        "canned pumpkin": "pumpkin",
        # Chocolate variants
        "sq. chocolate": "unsweetened chocolate",
        "squares chocolate": "unsweetened chocolate",
        "square chocolate": "unsweetened chocolate",
        # Stale bread/cake
        "stale cake or bread": "bread",
        "stale cake": "cake",
        "stale bread": "bread",
        # Rich variants - just use base item
        "rich baking powder": "baking powder",
        "rich milk": "milk",

        # Batch 1 fixes - OCR artifacts with missing spaces
        "coldmilk": "milk",
        "coldmilk.": "milk",
        "oroleomargarine": "margarine",
        "oroleomargarine.": "margarine",
        "ofbuttermilk": "buttermilk",
        "ofbuttermilk.": "buttermilk",
        "calded m^k": "milk",
        "cupdates": "dates",
        "ofbran": "bran",
        "ofbran.": "bran",
        "sourmilk": "buttermilk",
        "sour milk": "buttermilk",
        "eggyolks": "egg yolk",
        "softed flour": "flour",
        "sifted flour": "flour",
        "andcutrind": "watermelon rind",
        "andcutrind.": "watermelon rind",
        "coldmashed potato": "mashed potatoes",
        "thebutter": "butter",
        "c.suet": "suet",
        "c.molasses": "molasses",
        "c.sourmilk": "buttermilk",

        # Batch 1 - Historical measurement words
        "a pint rum": "rum",
        "a pint good whiskey": "whiskey",
        "one cup tart dark jelly": "grape jelly",
        "one cup blackberry jam": "blackberry jam",
        "one cup crumbled rich stale cake": "pound cake",
        "one pint raw grated sweet potato": "sweet potato",
        "half a cup very rich milk": "heavy cream",
        "one cup nuts rolled small": "walnuts",
        "one cup crumbled macaroons": "macaroons",
        "tablespoonfuls": "tbsp",
        "tablespoonful": "tbsp",
        "teaspoonfuls": "tsp",
        "teaspoonful": "tsp",
        "cupful": "cup",
        "cupfuls": "cups",

        # Batch 1 - Compound OCR artifacts
        "three cups ofbuttermilk": "buttermilk",
        "three cups ofbran": "bran",
        "two teaspoons of,baking powder": "baking powder",
        "two level tablespoons baking powder": "baking powder",
        "two tablespoons shortening": "shortening",
        "four tablespoons syrup": "maple syrup",
        "broken cinnamon stick": "cinnamon stick",
        "level teaspoons cloves": "cloves",

        # Batch 1 - Specific ingredients
        "plum tomato": "tomato",
        "large plum tomato": "tomato",
        "fresh basil": "basil",
        "large french baguette": "french bread",
        "french baguette": "french bread",
        "stewing chicken": "chicken",
        "a little flour": "flour",
        "pastry crust": "pie crust",
        "poblano peppers": "green pepper",
        "poblano pepper": "green pepper",
        "anaheim peppers": "green chiles",
        "anaheim pepper": "green chiles",
        "pkg family size chicken": "chicken",
        "pkg stove top stuffi ng": "stuffing mix",
        "pkg stove top stuffing": "stuffing mix",
        "can cream of mushroom soup": "cream of mushroom soup",
        "grams goat cheese": "goat cheese",
        "soured milk": "buttermilk",
        "nutme g": "nutmeg",
        "inch cucumber": "cucumber",
        "inch stem broccoli": "broccoli",
        "inch slice beetroot": "beets",
        "beetroot": "beets",
        "package yeast": "yeast",
        # Deep frying
        "for deep frying oil": "oil",
        "deep frying oil": "oil",
        # Mushrooms
        "nice mushrooms": "mushrooms",
        "button mushrooms": "mushrooms",
        "sliced mushrooms": "mushrooms",
        "cremini mushrooms": "mushrooms",
        # Gratings
        "few gratings of nutmeg": "",
        "gratings of nutmeg": "",
        "gratings nutmeg": "",
        # Popcorn
        "popped corn": "popcorn",
        "popped popcorn": "popcorn",
        # Gelatin
        "envelope gelatin": "gelatin",
        "envelopes gelatin": "gelatin",
        "pkg gelatin": "gelatin",
        # Mashed variants
        "mashed bananas": "banana",
        "mashed banana": "banana",
        "mashed potatoes": "potato",
        "mashed potato": "potato",
        # Typos and OCR artifacts
        "baking power": "baking powder",
        "sug ar": "sugar",
        "carro ts": "carrots",
        "she rry": "sherry",
        "cats up": "ketchup",
        "catsup": "ketchup",
        "cat sup": "ketchup",
        # Cereals
        "wheaties": "cereal",
        "cheerios": "cereal",
        "corn flakes": "cereal",
        "rice krispies": "cereal",
        # Nuts
        "broken nuts": "mixed nuts",
        "chopped nuts": "mixed nuts",
        # Citron
        "cut-up citron": "candied citron",
        "citron": "candied citron",
        # Spice variants
        "ginger powder": "ground ginger",
        "dillweed": "dill",
        "dried dillweed": "dill",
        "celery flakes": "celery",
        "ground thyme": "thyme",
        "dried thyme": "thyme",
        # Noodle variants
        "fine noodles": "pasta",
        "wide noodles": "pasta",
        "egg noodles": "pasta",
        # Broth
        "beef consommé": "beef broth",
        "beef consomme": "beef broth",
        "chicken consommé": "chicken broth",
        "chicken consomme": "chicken broth",
        # Cut-up variants
        "cut-up broccoli": "broccoli",
        "cut-up celery": "celery",
        "cut-up chicken": "chicken",
        # Chocolate
        "chocolate sauce": "chocolate syrup",
        # Cream of tartar typos
        "cream of tarter": "cream of tartar",
        "cream of tatar": "cream of tartar",
        # Half and half
        "half & half": "half and half",
        "half&half": "half and half",
        "top milk": "half and half",
        # Chicken variants
        "fryer chickens": "chicken",
        "fryer chicken": "chicken",
        "frying chicken": "chicken",
        "roasting chicken": "chicken",
        "chicken parts": "chicken",
        # Pepper variants
        "coarse pepper": "black pepper",
        "coarse black pepper": "black pepper",
        "cracked pepper": "black pepper",
        "cracked black pepper": "black pepper",
        # Onion soup
        "lipton onion soup": "onion soup mix",
        "lipton onion s oup": "onion soup mix",
        "pkg onion soup": "onion soup mix",
        "dry onion soup": "onion soup mix",
        "pkg dry onion soup": "onion soup mix",
        # Juice variants - more specific patterns
        "apricot juice": "orange juice",
        "the apricot juice": "orange juice",
        # Pimento
        "small can pimientos": "red pepper",
        "small can pimento": "red pepper",
        "can pimientos": "red pepper",

        # Batch 2 fixes - Can/package patterns
        "packet taco seasoning": "taco seasoning",
        "package pepperonis": "pepperoni",
        "pkg shredded": "cheese",
        "lb ground beef or turkey": "ground beef",
        "lb ground pork": "ground pork",
        "lb italian sausage": "italian sausage",
        "lb dried pinto beans": "pinto beans",
        "oz can black beans": "black beans",
        "oz can kidney beans": "kidney beans",
        "oz can red kidney beans": "kidney beans",
        "oz can chili beans": "chili beans",
        "oz can chicken broth": "chicken broth",
        "oz can corn": "corn",
        "oz can tomato sauce": "tomato sauce",
        "oz jar pizza sauce": "pizza sauce",
        "small can tomato paste": "tomato paste",
        "oz pkgs onion soup mix": "onion soup mix",
        "slices smoked mozzarella": "mozzarella",
        "slices muenster or gouda cheese": "cheese",
        "slices oven-roasted turkey": "turkey",
        "bunch watercress": "watercress",
        "bunch arugula": "arugula",

        # Batch 2 - Measurement patterns
        "dash black pepper": "pepper",
        "pinch cinnamon": "cinnamon",
        "pinch nutmeg": "nutmeg",
        "generous pinch": "nutmeg",
        "ground chipotle chile pepper": "chipotle",
        "chili powder": "chili powder",
        "inch corn tortillas": "corn tortilla",
        "inch flour tortillas": "flour tortilla",
        "large flour tortillas": "flour tortilla",
        "julienne-cut peeled jicama": "jicama",
        "large shredded carrots": "carrots",

        # Batch 2 - Garnish (should become zero cal)
        "for garnish shredded cheddar cheese": "garnish",
        "for garnish sour cream": "garnish",
        "for garnish crushed tortilla chips": "garnish",
        "for serving saltine crackers": "garnish",
        "for serving corn chips": "garnish",
        "optional shredded cheddar cheese": "garnish",
        "optional sour cream": "garnish",
        "toppings of your choice": "garnish",

        # Batch 2 - Specific items
        "whole smoked ham": "ham",
        "apple butter": "apple butter",
        "dijon mustard": "mustard",
        "baguette": "french bread",
        "watercress": "watercress",
        "arugula": "arugula",
        "jicama": "jicama",
        "rusk": "crackers",
        "spiced cake": "spice cake",
        "syllabub": "whipped cream",
        "flowers": "garnish",

        # Batch 2 - OCR artifacts with equipment
        "cups flour wooden cake-apoon": "flour",
        "baking-powder small saucepan": "baking powder",
        "butter cake-pan": "butter",
        "egg small bowl": "egg",
        "flour bread-boardmteaspoon": "flour",
        "salt cookie-cutter": "salt",
        "beat theegg": "egg",
        "four ounces ofbutter": "butter",
        "cupf ulsofflour": "flour",
        "teaspoonfuls ofbaking powder": "baking powder",

        # Batch 2 - Scripture cake Bible references (map to actual ingredients)
        "butter judges": "butter",
        "flour i-kings": "flour",
        "salt leviticus": "salt",
        "figs i-samuel": "figs",
        "cups sugar jeremiah": "sugar",
        "baking powder luke": "baking powder",
        "honey proverbs": "honey",
        "almonds genesis": "almonds",
        "cup ofjudge": "sugar",
        "cup jeremiah": "sugar",
        "cup nehum": "raisins",
        "cup numbers": "almonds",
        "cup ikings": "flour",

        # Batch 3 - Patterns AFTER number stripping (numbers removed at line 2231)
        "packet taco seasoning": "taco seasoning",
        "can mushroom soup": "cream of mushroom soup",
        "oz can kidney beans": "kidney beans",
        "oz can tomato sauce": "tomato sauce",
        "oz can corn": "corn",
        "oz can chicken broth": "chicken broth",
        "oz pkg shredded": "cheese",
        "oz cans chili beans": "chili beans",
        "oz pkgs onion soup mix": "onion soup mix",
        "oz jar pizza sauce": "pizza sauce",
        "-inch corn tortillas": "corn tortilla",
        "large flour tortillas": "flour tortilla",
        "(8 oz) can cream of mushroom soup": "cream of mushroom soup",
        "oz) can cream of mushroom soup": "cream of mushroom soup",
        "-to-15-pound whole smoked ham": "ham",
        "-pound whole smoked ham": "ham",
        "cup apple butter": "apple butter",
        "cup dijon mustard": "mustard",

        # Batch 3 - Garnish patterns (case variations)
        "for garnish shredded cheddar cheese": "garnish",
        "shredded cheddar cheese": "cheddar cheese",
        "optional shredded cheddar cheese": "garnish",
        "for serving saltine crackers or corn chips": "garnish",

        # Batch 3 - More OCR artifacts
        "one cup stale cake crumbs": "bread crumbs",
        "c + 2 tbs flour": "flour",
        "tsp baking powder pinch of salt": "baking powder",
        "tbs crisco(solid)": "shortening",
        "c buttermilk": "buttermilk",
        "140 pound cake": "pound cake",
        "crisco(solid)": "shortening",

        # Batch 3 - Armed Forces Recipe Service garbage
        "index to armed forces recipe service (tm 10-412)": "garnish",
        "appetizers.": "garnish",
        "general principles of coffee brewing": "garnish",
        "standard recipes for hot tea": "garnish",
        "standard recipe for cocoa": "garnish",
        "standard recipe for hot rolls": "garnish",
        "guide for hot-roll makeup": "garnish",
        "standard recipe for sweet dough": "garnish",
        "recipe conversion from armed forces": "garnish",

        # Batch 4 - More can/package patterns (AFTER number stripping)
        "oz can petite diced tomatoes": "diced tomatoes",
        "oz can mild chili beans": "chili beans",
        "oz can stewed tomatoes": "stewed tomatoes",
        "oz can diced green chiles": "green chiles",
        "oz can chopped green chiles": "green chiles",
        "oz can great northern beans": "great northern beans",
        "oz can cannellini beans": "cannellini beans",
        "oz can black beans": "black beans",
        "oz can tomato paste": "tomato paste",
        "oz can tomato juice": "tomato juice",
        "oz can english peas": "peas",
        "oz can whole kernel corn": "corn",
        "beef bouillon cubes": "beef bouillon",
        "chicken bouillon cubes": "chicken bouillon",
        "oz pkgs chili seasoning mix": "chili seasoning",
        "pkg chili seasoning mix": "chili seasoning",
        "oz cans green chiles": "green chiles",
        "oz each) green chiles": "green chiles",
        "oz jar stuffed green": "olives",
        "oz) pimento": "pimento",
        "oz jar pimento": "pimento",

        # Batch 4 - Informal measurements (casual cooking)
        "big squeeze lime juice": "lime juice",
        "squeeze lime juice": "lime juice",
        "splash olive oil": "olive oil",
        "splash oil": "vegetable oil",
        "pinch cumin powder": "cumin",
        "pinch cumin": "cumin",
        "dash cayenne": "cayenne pepper",
        "dash sea salt": "salt",
        "dash chili powder": "chili powder",
        "generous pinch freshly grated nutmeg": "nutmeg",
        "freshly grated nutmeg": "nutmeg",

        # Batch 4 - Product patterns
        "pkg (10 oz) frozen cut okra": "okra",
        "pkg frozen cut okra": "okra",
        "frozen cut okra": "okra",
        "cup vegetable juice cocktail": "vegetable juice",
        "vegetable juice cocktail": "vegetable juice",
        "cups fritos": "corn chips",
        "fritos": "corn chips",
        "c tvp® granules or flakes": "tvp",
        "tvp® granules or flakes": "tvp",
        "tvp granules": "tvp",
        "lb coarsely ground lean beef": "ground beef",
        "coarsely ground lean beef": "ground beef",
        "lb ground beef or turkey": "ground beef",
        "ground beef or turkey": "ground beef",
        "slices smoked mozzarella": "mozzarella cheese",
        "smoked mozzarella": "mozzarella cheese",
        "baguette": "french bread",
        "bunch watercress": "watercress",
        "bunch kale": "kale",
        "slices muenster": "cheese",
        "muenster": "cheese",
        "gouda cheese": "cheese",
        "slices oven-roasted turkey": "turkey",
        "oven-roasted turkey": "turkey",
        "deli-sliced": "turkey",
        "toppings of your choice": "garnish",
        "toppings": "garnish",
        "for garnish taco-blend cheese": "garnish",
        "for garnish guacamole": "garnish",
        "for garnish sour cream": "garnish",
        "optional sour cream": "garnish",
        "optional guacamole": "garnish",
        "for garnish crushed tortilla chips": "garnish",
        "for serving": "garnish",
        "for dipping": "garnish",

        # Batch 4 - Historical OCR with combined columns
        "cup offlour equal": "flour",
        "cup ofbutter packed": "butter",
        "cup ofbutter equals": "butter",
        "cups ofpowdered sugar": "powdered sugar",
        "cup ofshelled nutmeats": "nuts",
        "gills = 1 pint": "garnish",
        "pints = 1 quart": "garnish",
        "quarts = 1 gallon": "garnish",
        "oz = 1 pound": "garnish",
        "kitchen cupful": "garnish",
        "tablespoonfuls ofliquid": "garnish",
        "wine glasses equal": "garnish",
        "gills equal": "garnish",
        "coffeecupfuls equal": "garnish",
        "pints equal": "garnish",
        "gillb=1 pint": "garnish",
        "quarts =1 gallon": "garnish",

        # Batch 4 - Equipment and non-food items
        "wooden spoon": "garnish",
        "frying pan": "garnish",
        "saucepans": "garnish",
        "bread pans": "garnish",
        "setsmuffin pans": "garnish",
        "dish-towels": "garnish",
        "roller-towels": "garnish",
        "dish-clotha": "garnish",
        "dish-pans": "garnish",
        "asbestos holders": "garnish",
        "chopping-bowl": "garnish",
        "doughnut-cutter": "garnish",
        "mixing-spoons": "garnish",
        "forks": "garnish",

        # Batch 4 - Index entries, table of contents (non-food)
        "head,": "garnish",
        "face,": "garnish",
        "ears,": "garnish",
        "nose": "garnish",
        "tongue,": "garnish",
        "eyes,": "garnish",
        "general methods": "garnish",
        "almond crescents": "garnish",
        "almond macaroons": "garnish",
        "almond paste": "garnish",
        "factors that contribute": "garnish",
        "meat thermometers": "garnish",
        "weighing ingredients": "garnish",
        "definitions of terms": "garnish",
        "guidelines for": "garnish",
        "three types of salad": "garnish",
        "relish trays": "garnish",
        "sandwich variations": "garnish",
        "sandwich preparation": "garnish",
        "sandwich-spread variations": "garnish",
        "charles street": "garnish",
        "berkeley street": "garnish",
        "broadway": "garnish",
        "thin white sauce": "garnish",
        "medium white sauce": "garnish",
        "thick white sauce": "garnish",
        "bulb—onion": "garnish",
        "stems—celery": "garnish",
        "leaves—lettuce": "garnish",
        "flower—cauliflower": "garnish",
        "fruit—squash": "garnish",
        "tbs = 1 oz": "garnish",
        "c = 8 tbs": "garnish",
        "c = 5 1/3 tbs": "garnish",
        "c = 8 oz": "garnish",
        "qt = 4 c": "garnish",
        "lb loaf = about": "garnish",
        "quarts 1 peck": "garnish",
        "^peck": "garnish",
        "cups brown sugar": "garnish",
        "cups cornstarch": "garnish",

        # Batch 4 - More scripture cake references
        "cup butter judges": "butter",
        "cup flour i-kings": "flour",
        "tsp. salt leviticus": "salt",
        "cup figs i-samuel": "figs",
        "cups sugar jeremiah": "sugar",

        # Batch 5 - Additional normalizations
        "scallion": "green onion",
        "scallions": "green onion",
        "bay-leaf": "bay leaf",
        "bay-leaves": "bay leaf",
        "sprigs parsley": "parsley",
        "sprig parsley": "parsley",
        "sprigs of parsley": "parsley",
        "ts olive oil": "olive oil",
        "ts oil": "vegetable oil",
        "ts butter": "butter",
        "t butter": "butter",
        "c mushrooms": "mushrooms",
        "t. baking powder": "baking powder",
        "t. salt": "salt",
        "t. cinnamon": "cinnamon",
        "ea egg": "egg",
        "ea eggs": "egg",
        "marga rine": "margarine",
        "c marga rine": "margarine",
        "c sugar": "sugar",
        "c flour": "flour",
        "salmon fillets": "salmon",
        "salmon fillet": "salmon",
        "skin-on salmon": "salmon",
        "center-cut skin-on salmon": "salmon",
        "fresh dill": "dill",
        "bunch fresh dill": "dill",
        "bunch dill": "dill",
        "pumpernickel": "bread",
        "pumpernickel bread": "bread",
        "good squash": "squash",
        "winter squash": "butternut squash",
        "spoons dry bread": "bread crumbs",
        "dry bread": "bread crumbs",
        "chopped parsley tablespoon": "parsley",
        "onion juice saucepan": "onion",
        "flour bowl": "flour",
        "baking-powder tablespoon": "baking powder",
        "salt small saucepan": "salt",

        # Batch 6 - More product/brand patterns
        "ciabatta": "bread",
        "whole ciabatta": "bread",
        "smoked salmon": "salmon",
        "slices smoked salmon": "salmon",
        "pita bread": "bread",
        "package pita bread": "bread",
        "oz package pita bread": "bread",
        "container prepared hummus": "hummus",
        "prepared hummus": "hummus",
        "oz container": "garnish",  # Generic container reference
        "to top champagne": "champagne",
        "champagne": "wine",
        "pepper stir-fry": "bell pepper",
        "frozen pepper stir-fry": "bell pepper",
        "-oz bag) frozen pepper": "bell pepper",
        "non fat vanilla yogurt": "yogurt",
        "nonfat vanilla yogurt": "yogurt",
        "vanilla yogurt": "yogurt",
        "cup applesauce": "applesauce",
        "butter at room temperature": "butter",
        "room temperature butter": "butter",
        "slices of cooked ham": "ham",
        "cooked ham": "ham",
        "slices of ham": "ham",
        "pie dough mix": "pie crust",
        "-oz packages pie dough": "pie crust",
        "packages pie dough mix": "pie crust",
        "white chicken meat": "chicken",
        "oz can white chicken": "chicken",
        "-oz can white chicken meat": "chicken",
        "shredded rotisserie chicken": "chicken",
        "rotisserie chicken": "chicken",
        "cream cheese": "cream cheese",
        "oz package cream cheese": "cream cheese",
        "package cream cheese": "cream cheese",
        "philadelphia cream cheese": "cream cheese",
        "baker's semi-sweet chocolate": "chocolate chips",
        "semi-sweet chocolate squares": "chocolate chips",
        "chocolate squares": "chocolate chips",
        "crème fraîche": "sour cream",
        "creme fraiche": "sour cream",
        "for topping crème fraîche": "garnish",
        "for topping chopped chives": "garnish",
        "chopped chives": "chives",
        "french 75 (bubbly)": "garnish",  # cocktail section header
        "gibson (dry)": "garnish",  # cocktail section header
        "gin martini (classic)": "garnish",  # cocktail section header
        "ground lean beef": "ground beef",
        "coarsely ground lean beef": "ground beef",
        "lb coarsely ground lean beef": "ground beef",
        "goya black beans": "black beans",
        "cans goya black beans": "black beans",
        "goya minced garlic": "garlic",
        "tsp goya minced garlic": "garlic",
        "-inch piece ginger": "ginger",
        "piece ginger": "ginger",
        "-inch orange zest strips": "orange zest",
        "orange zest strips": "orange zest",
        "canned solid pumpkin": "pumpkin",
        "oz can canned solid pumpkin": "pumpkin",
        "pumpkin pie spice": "pumpkin spice",
        "cup pumpkin pie spice": "pumpkin spice",
        "muenster or gouda cheese": "cheese",
        "slices muenster or gouda": "cheese",
        "oven-roasted turkey": "turkey",
        "slices oven-roasted turkey": "turkey",
        "corn chex cereal": "cereal",
        "rice chex cereal": "cereal",
        "wheat chex cereal": "cereal",
        "cups corn chex": "cereal",
        "cups rice chex": "cereal",
        "cups wheat chex": "cereal",
        "package pepperonis": "pepperoni",
        "pepperonis": "pepperoni",
        "lb italian sausage": "italian sausage",
        "italian sausage": "sausage",

        # Batch 7 - More cleanup patterns
        "of a 16-oz can": "garnish",  # Partial quantity (1/2 of a can)
        "of a can": "garnish",
        "white corn": "corn",
        "can white corn": "corn",
        "coffee-flavored liqueur": "coffee liqueur",
        "espresso beans": "coffee",
        "finely ground espresso beans": "coffee",
        "pompeian extra light tasting olive oil": "olive oil",
        "extra light tasting olive oil": "olive oil",
        "gorgonzola": "blue cheese",
        "gorgonzola cheese": "blue cheese",
        "rocket": "arugula",
        "arugula": "lettuce",

        # Batch 8 - Historical OCR patterns
        # Space-in-word OCR artifacts
        "cinna mon": "cinnamon",
        "ap ples": "apples",
        "appl e": "apple",
        "almo nds": "almonds",
        "all-purp ose flour": "flour",
        "quick-cooki ng oats": "oats",
        "semi- sweet": "semi-sweet",
        "semi-sweet real chocolate": "chocolate chips",
        "choco late": "chocolate",
        "marga rine": "margarine",

        # "fuls" suffix patterns (historical measurement)
        "cup ful": "cup",
        "cupful": "cup",
        "cupsful": "cups",
        "cup fuls": "cups",
        "tbsp ful": "tbsp",
        "tablespoonful": "tbsp",
        "tablespoonfuls": "tbsp",
        "teaspoonful": "tsp",
        "teaspoonfuls": "tsp",
        "^teaspoonful": "tsp",
        "^cupsful": "cups",

        # Measurement abbreviations with periods/spaces
        "lb s.": "lb",
        "tsp s.": "tsp",

        # Brand names
        "land o lakes ® butter": "butter",
        "land o lakes ® margarine": "margarine",
        "land o lakes": "butter",

        # Frozen/packaged items
        "pkg frozen green shrimp": "shrimp",
        "frozen green shrimp": "shrimp",
        "pkg frozen rhubarb": "rhubarb",
        "frozen rhubarb": "rhubarb",
        "pkg frozen strawberries": "strawberries",
        "frozen strawberries": "strawberries",
        "red vegetable coloring": "garnish",
        "vegetable coloring": "garnish",

        # Descriptors that should map to base ingredient
        "finely diced celery": "celery",
        "finely chopped": "garnish",
        "chopped sweet pickle": "pickle",
        "rounds of toast": "bread",
        "round of toast": "bread",
        "cut up": "garnish",
        "chicken cut up": "chicken",
        "butter for frying": "butter",
        "for frying": "garnish",
        "boiled rice": "rice",
        "beaten lightly": "garnish",
        "egg beaten lightly": "egg",
        "level cups flour": "flour",
        "level teaspoons": "tsp",
        "level tablespoons": "tbsp",
        "small pinch each of thyme": "thyme",
        "small pinch": "garnish",
        "chopped olive": "olives",
        "chopped spanish pepper": "bell pepper",
        "spanish pepper": "bell pepper",

        # OCR garbage to filter
        "^^^^": "garnish",
        "pure food recipes": "garnish",
        "dark leaves outside": "garnish",
        "incenter": "garnish",
        "asifhalf": "garnish",

        # Combined columns (treat as first item or garnish)
        "pkg crescent rolls": "biscuit",
        "crescent rolls": "biscuit",
        "can crescent rolls": "biscuit",
        "jar pizza sauce": "pizza sauce",
        "shredded cheddar cheese": "cheddar cheese",
        "shredded mozzarella cheese": "mozzarella cheese",
        "ground beef": "ground beef",
        "diced ham": "ham",
        "c diced ham": "ham",
        "jar pimento": "pimento",
        "oz) pimento": "pimento",
        "jar stuffed green": "olives",
        "stuffed green": "olives",
        "white pepper": "pepper",
        "tsp white pepper": "pepper",
        "light molasses": "molasses",
        "c light molasses": "molasses",
        "tsp salt": "salt",
        "tsp pepper": "pepper",
        "frier chicken": "chicken",
        "lb frier chicken": "chicken",
        "prepared mustard": "mustard",
        "tbs prepared mustard": "mustard",
        "tsp vanilla": "vanilla",
        "unbaked pie shell": "pie crust",
        "rains": "raisins",
        "c rains": "raisins",
        "dressing ofchoice": "garnish",
        "sliced banana": "banana",
        "cup sliced banana": "banana",
        "strawberry gelatin": "gelatin",
        "cup strawberry gelatin": "gelatin",
        "finely cutapple": "apple",
        "cutapple": "apple",

        # Missing spaces OCR
        "ofveal": "veal",
        "ofchopped": "garnish",
        "ofsalt": "salt",
        "offlour": "flour",
        "ofsugar": "sugar",
        "ofbutter": "butter",
        "ofmilk": "milk",

        # Gooseberries and other fruits
        "ripe gooseberries": "gooseberries",
        "gooseberries": "grapes",

        # Fraction artifacts from number stripping
        "/4 stick celery": "celery",
        "/2 stick celery": "celery",
        "stick celery": "celery",
        "/4 stick": "garnish",
        "/2 stick": "garnish",

        # Batch 9 - Packaged/branded items
        "package pita bread": "pita bread",
        "pita bread": "bread",
        "container hummus": "hummus",
        "prepared hummus": "hummus",
        "pkg pie dough mix": "pie crust",
        "pie dough mix": "pie crust",
        "pie dough": "pie crust",
        "can white chicken meat": "chicken",
        "white chicken meat": "chicken",
        "squares baker's": "chocolate",
        "baker's semi-sweet": "chocolate",
        "baker's chocolate": "chocolate",
        "package philadelphia": "cream cheese",
        "philadelphia cream cheese": "cream cheese",
        "can eagle brand": "sweetened condensed milk",
        "eagle brand": "sweetened condensed milk",
        "pkg lemon flavored gelatin": "gelatin",
        "pkg lemon-flavored gelatin": "gelatin",
        "lemon flavored gelatin": "gelatin",
        "lemon-flavored gelatin": "gelatin",
        "flavored gelatin": "gelatin",
        "pkg zwieback": "crackers",
        "zwieback": "crackers",
        "packet taco seasoning": "taco seasoning",
        "taco seasoning": "chili powder",
        "pkg thin spaghetti": "spaghetti",
        "thin spaghetti": "spaghetti",
        "pkg stove top": "stuffing",
        "stove top stuffi ng": "stuffing",
        "stove top stuffing": "stuffing",
        "pkg tortillas": "tortillas",
        "flour tortillas": "tortillas",
        "large flour tortillas": "tortillas",
        "large tortilla wraps": "tortillas",
        "tortilla wraps": "tortillas",

        # Can/jar patterns with contents
        "can chili beans": "kidney beans",
        "cans chili beans": "kidney beans",
        "chili beans": "kidney beans",
        "pkgs onion soup mix": "onion soup mix",
        "pkg onion soup mix": "onion soup mix",
        "onion soup mix": "onion powder",
        "pkg chili seasoning mix": "chili powder",
        "chili seasoning mix": "chili powder",
        "can red kidney beans": "kidney beans",
        "can kidney beans": "kidney beans",
        "can condensed cream of chicken soup": "cream of chicken soup",
        "can cream of chicken soup": "cream of chicken soup",
        "cream of chicken soup": "cream of mushroom soup",
        "bottle prepared horseradish": "horseradish",
        "prepared horseradish": "horseradish",
        "bottle tomato catsup": "ketchup",
        "tomato catsup": "ketchup",
        "catsup": "ketchup",
        "can mushroom soup": "cream of mushroom soup",
        "mushroom soup": "cream of mushroom soup",

        # Produce patterns
        "whole ciabatta": "bread",
        "ciabatta": "bread",
        "baguette": "bread",
        "roma tomatoes": "tomatoes",
        "medium roma tomatoes": "tomatoes",
        "container crumbled feta": "feta cheese",
        "crumbled feta": "feta cheese",
        "cans sliced pears": "pears",
        "sliced pears in juice": "pears",
        "center-cut skin-on salmon": "salmon",
        "skin-on salmon": "salmon",
        "smoked salmon": "salmon",
        "slices smoked salmon": "salmon",
        "thin slices bacon": "bacon",
        "slices bacon": "bacon",
        "fresh rocket": "arugula",
        "bunch fresh dill": "dill",
        "fresh dill": "dill",
        "bunch radishes": "radishes",
        "thinly sliced": "garnish",
        "smoked mozzarella": "mozzarella cheese",
        "slices smoked mozzarella": "mozzarella cheese",
        "bunch watercress": "lettuce",
        "watercress": "lettuce",
        "tough stems removed": "garnish",
        "piece ginger": "ginger",
        "orange zest strips": "orange zest",
        "zest strips": "garnish",
        "frozen chicken": "chicken",
        "frozen vegetable dumplings": "dumplings",
        "vegetable dumplings": "dumplings",
        "pot stickers": "dumplings",
        "slices muenster": "cheese",
        "muenster": "cheese",
        "slices gouda": "cheese",
        "gouda cheese": "cheese",
        "slices oven-roasted turkey": "turkey",
        "oven-roasted turkey": "turkey",
        "deli-sliced": "garnish",
        "pinch freshly grated nutmeg": "nutmeg",
        "freshly grated nutmeg": "nutmeg",
        "grated nutmeg": "nutmeg",
        "package pepperonis": "pepperoni",
        "pepperonis": "pepperoni",
        "jar pizza sauce": "pizza sauce",
        "small can tomato paste": "tomato paste",

        # Measurement patterns
        "inch cucumber": "cucumber",
        "inch stem broccoli": "broccoli",
        "inch slice beetroot": "beets",
        "slice beetroot": "beets",
        "beetroot": "beets",
        "handful fresh": "garnish",
        "handful": "garnish",
        "generous pinch": "garnish",

        # Shredded items
        "large shredded carrots": "carrots",
        "shredded carrots": "carrots",
        "pinch cinnamon": "cinnamon",
        "pinch nutmeg": "nutmeg",

        # Meat items
        "whole smoked ham": "ham",
        "smoked ham": "ham",
        "lb. chicken": "chicken",
        "lbs. chicken": "chicken",
        "l bs. chicken": "chicken",
        "lbs pork belly": "pork",
        "pork belly": "pork",
        "turkey polish kielbasa": "sausage",
        "polish kielbasa": "sausage",
        "kielbasa": "sausage",
        "large celery stalk": "celery",
        "celery stalk": "celery",
        "large carrots": "carrots",
        "chicken wings": "chicken",

        # Fresh herbs/spices
        "bunch kale": "kale",
        "leaves kale": "kale",
        "dash cayenne": "cayenne pepper",
        "medium butternut squash": "squash",
        "butternut squash": "squash",
        "short grain brown rice": "brown rice",
        "grain brown rice": "brown rice",
        "pinch cumin powder": "cumin",
        "cumin powder": "cumin",
        "dash chili powder": "chili powder",
        "dash sea salt": "salt",
        "sea salt": "salt",
        "cup fritos": "corn chips",
        "fritos": "corn chips",
        "cups fritos": "corn chips",
        "cup sriracha": "hot sauce",
        "sriracha": "hot sauce",

        # Batch 10 - More OCR space artifacts from remaining recipes
        "g rated ginger": "ginger",
        "g rated": "grated",
        "grated ginger": "ginger",
        "tarragon leav es": "tarragon",
        "leav es": "leaves",
        "tarragon leaves": "tarragon",
        "w orcestershire sauce": "worcestershire sauce",
        "w orcestershire": "worcestershire sauce",
        "orcestershire": "worcestershire sauce",
        "hot pepper sauc e": "hot sauce",
        "pepper sauc e": "hot sauce",
        "sauc e": "sauce",
        "longhorn chees e": "cheddar cheese",
        "longhorn cheese": "cheddar cheese",
        "chees e": "cheese",
        "cry stals": "crystals",
        "chicken bouillon cry stals": "chicken bouillon",
        "bouillon cry stals": "bouillon",
        "chi cken": "chicken",
        "fl orida": "garnish",
        "enchi lada": "enchilada",
        "enchilada": "garnish",
        "deli ght": "garnish",
        "pineappl e": "pineapple",
        "pineapple cubes": "pineapple",
        "ourmilk": "buttermilk",
        "zatek cocoa": "cocoa",
        "stuffi ng": "stuffing",
        "boned & skinned chicken": "chicken",
        "boned chicken or": "chicken",
        "boned chicken": "chicken",
        "can boned chicken": "chicken",
        "frying size chicken": "chicken",
        "cut up chicken": "chicken",
        "can chicken": "chicken",
        "cup chicken": "chicken",
        "family size chicken": "chicken",
        "chopped fresh coriander": "cilantro",
        "fresh coriander": "cilantro",
        "coriander": "cilantro",
        "oriental sesame oil": "sesame oil",
        "boiled egg": "egg",
        "chopped meat": "ground beef",
        "chopped suet": "shortening",
        "suet": "shortening",
        "apricot brandy": "brandy",
        "condensed cream of chicken": "cream of mushroom soup",
        "green olives": "olives",
        "bunches green olives": "olives",
        "sliced raw celery": "celery",
        "raw celery": "celery",
        "bottle tomato": "ketchup",
        "green chili": "green chilies",
        "inch piece ginger": "ginger",
        "inch ginger": "ginger",
        "stick celery": "celery",

        # Historical cooking terms
        "bitter chocolate": "unsweetened chocolate",
        "square bitter chocolate": "unsweetened chocolate",
        "lady fingers": "ladyfingers",
        "doz. lady fingers": "ladyfingers",
        "doz lady fingers": "ladyfingers",
        "half doz": "garnish",
        "broken walnut meats": "walnuts",
        "walnut meats": "walnuts",
        "creamy cottage cheese": "cottage cheese",
        "fine noodles": "egg noodles",
        "half pkg": "garnish",
        "half cup": "garnish",
        "gelatine": "gelatin",
        "tbsp. gelatine": "gelatin",

        # For topping/garnish patterns
        "for topping crème fraîche": "garnish",
        "crème fraîche": "sour cream",
        "for topping chopped chives": "garnish",
        "for topping chopped": "garnish",
        "for topping fresh dill": "garnish",
        "for topping fresh": "garnish",
        "to top champagne": "garnish",
        "for garnish orange twist": "garnish",
        "orange twist": "garnish",
        "for serving saltine crackers": "garnish",
        "saltine crackers": "crackers",
        "corn chips": "corn chips",
        "red or yel low pepper": "bell pepper",
        "yel low pepper": "bell pepper",
        "yellow pepper": "bell pepper",

        # Section headers and labels (OCR artifacts)
        "french 75 (bubbly):": "garnish",
        "gibson (dry):": "garnish",
        "bronx (sweet):": "garnish",
        "lemon, juice": "lemon juice",
        "juice of": "garnish",
        "juice and rind of": "garnish",
        "rind of": "garnish",

        # Batch 11 - More OCR missing-space artifacts
        "coldboiled": "cold boiled",
        "cold boiled chicken": "chicken",
        "cutcelery": "celery",
        "cut celery": "celery",
        "finely cut celery": "celery",
        "orlettuce": "lettuce",
        "lettuce leaves": "lettuce",
        "shredded lettuce": "lettuce",
        "orgrated": "garnish",
        "or grated": "garnish",
        "chopped parley": "parsley",
        "parley": "parsley",
        "tea^oon": "tsp",
        "teaspoon ground": "garnish",
        "tablespoonfuls mo-": "garnish",
        "large tablespoonfuls": "garnish",
        "rounded tablespoon": "tbsp",
        "rounded teaspoon": "tsp",
        "tablespoonful flour": "flour",
        "tablespoonful butter": "butter",
        "tablespoonful of salt": "salt",
        "½ tablespoonful": "garnish",
        "½ cup of milk": "milk",
        "½ cup of cream": "cream",
        "poTinds": "pounds",
        "Mbdng-bowl": "garnish",
        "andpaper": "garnish",
        "frying-kettle": "garnish",
        "colander": "garnish",
        "andcutinhalf": "garnish",
        "thechicken": "chicken",
        "singe the": "garnish",
        "dressed": "garnish",
        "levelteaspoon": "tsp",
        "%cups": "cups",
        ">4 cup": "garnish",
        "dissolved in": "garnish",
        "chopped orcocoa": "cocoa",
        "orcocoa": "cocoa",
        "automatic fi.our": "flour",
        "fi.our": "flour",
        "-sized cauliflower": "cauliflower",
        "medium cauliflower": "cauliflower",
        "medium-sized": "garnish",
        "withstrawberry": "garnish",
        "sliced banana.": "banana",
        "strawberry gelatin.": "gelatin",
        "finely cutapple.": "apple",
        "cutapple": "apple",

        # Equipment words to filter
        "strainer": "garnish",
        "grater": "garnish",
        "sauce-": "garnish",
        "covered sauce-": "garnish",
        "pan strainer": "garnish",
        "directions": "garnish",
        "have the": "garnish",
        "wash the": "garnish",
        "inside andout": "garnish",
        "along the": "garnish",

        # More combined-word OCR
        "redpepper": "red pepper",
        "red pepper": "cayenne pepper",
        "tomato pulp": "tomato sauce",
        "onion juice": "onion",
        "long grain rice": "rice",
        "long grain brown rice": "brown rice",
        "mild chili beans": "kidney beans",
        "mild chili seasoning": "chili powder",
        "saltpork": "salt pork",
        "salt pork": "bacon",
        "cooked meat (veal": "veal",
        "cooked meat": "beef",
        "veal": "beef",

        # More produce patterns
        "spinach tortillas": "tortillas",
        "flour or spinach": "garnish",
        "inch flour": "garnish",
        "8 inch flour": "garnish",
        "leaves kale": "kale",
        "pinch cumin": "cumin",
        "dash cayenne": "cayenne pepper",

        # Sizes/ranges in items
        "to-12-oz": "garnish",
        "to-15-pound": "garnish",
        "11-to-": "garnish",
        "10-to-": "garnish",
        "oz packages": "package",
        "oz package": "package",
        "oz container": "container",

        # Apple butter and mustard
        "apple butter": "apple butter",
        "dijon mustard": "mustard",

        # Capers
        "cup capers": "capers",

        # Batch 12 - More ingredient patterns
        "ears of corn": "corn",
        "ear of corn": "corn",
        "ears corn": "corn",
        "can creamed corn": "creamed corn",
        "creamed corn": "corn",
        "can chicken broth": "chicken broth",
        "cups chicken broth": "chicken broth",
        "cup chicken broth": "chicken broth",
        "optional shredded": "garnish",
        "optional sour cream": "garnish",
        "optional": "garnish",
        "loaf white bread": "bread",
        "white bread cubed": "bread",
        "cup cracker crumbs": "crackers",
        "cracker crumbs": "crackers",
        "pkg corn tortillas": "tortillas",
        "corn tortillas": "tortillas",
        "ol eo": "margarine",
        "oleo": "margarine",
        "can mixed vegetables": "mixed vegetables",
        "mixed vegetables": "peas",
        "cup diced": "garnish",
        "cups diced": "garnish",
        "pin bones removed": "garnish",
        "bones removed": "garnish",
        "drained (or": "garnish",
        "(or": "garnish",
        "shredded rotisserie": "chicken",
        "rotisserie chicken": "chicken",
        "sliced ripe olives": "olives",
        "ripe olives": "olives",
        "can sliced": "garnish",
        "inch slice ginger": "ginger",
        "slice ginger": "ginger",
        "for serving cooked rice": "garnish",
        "cooked rice": "rice",
        "serving cooked": "garnish",
        "oz jar": "jar",
        "oz pkg": "package",
        "oz pkgs": "packages",
        "oz can": "can",
        "oz cans": "can",
        "1/2 oz pkgs": "garnish",
        "1/4 oz pkgs": "garnish",
        "1/4 oz pkg": "garnish",
        "breast of chicken": "chicken",
        "boneless breast": "chicken",
        "pieces boneless": "garnish",
        "slices mozzarella": "mozzarella cheese",
        "mozzarella cheese": "mozzarella cheese",
        "chi cken": "chicken",
        "finely diced celery": "celery",
        "diced celery": "celery",
        "green shrimp": "shrimp",
        "chopped sweet pickle": "pickle",
        "sweet pickle": "pickle",
        "l bs.": "lb",
        "l bs": "lb",
        "oz) can condensed": "garnish",
        "condensed cream of chicken": "cream of mushroom soup",
        "instant chicken bouillon": "chicken bouillon",
        "chicken bouillon cube": "chicken bouillon",
        "bouillon cube": "bouillon",
        "family size chicken": "chicken",
        "pkg family size": "garnish",
        "can cream of mushroom": "cream of mushroom soup",
        "oz can cream": "garnish",
        "pot pi e": "pie",
        "pkg zwieback": "crackers",
        "lb. cottage cheese": "cottage cheese",
        "½ lb. cottage cheese": "cottage cheese",
        "½ lb cottage cheese": "cottage cheese",
        "pkg stove top": "stuffing",
        "stove top": "stuffing",
        "pkg (12)": "garnish",
        "for garnish shredded cheddar": "garnish",
        "for serving saltine": "garnish",
        "saltine crackers": "crackers",
        "1/2 cup apple butter": "apple butter",
        "1/2 cup dijon": "mustard",
        "dijon": "mustard",
        "muenster or gouda": "cheese",
        "oven-roasted turkey": "turkey",
        "leftover or deli": "garnish",
        "deli-sliced": "garnish",
        "½ cup of milk": "milk",
        "½ cup of cream": "cream",
        "½ tablespoonful of salt": "salt",
        "cup ½ cup": "garnish",
        "tsp ½ tablespoonful": "garnish",
        "and/or parsley": "garnish",
        "fresh dill and/or": "dill",
        "chopped chives": "chives",
        "crème fraîche": "sour cream",
        "to top champagne": "garnish",
        "champagne": "wine",
        "lb.": "lb",

        # Batch 13 - More OCR and ingredient patterns
        "whole ciabatta": "bread",
        "handful fresh": "garnish",
        "handful": "garnish",
        "small can": "can",
        "large shredded": "garnish",
        "shredded carrots": "carrots",
        "pinch cinnamon": "cinnamon",
        "pinch nutmeg": "nutmeg",

        # OCR combined words
        "drymustard": "mustard",
        "dry mustard": "mustard",
        "thickcream": "cream",
        "thick cream": "cream",
        "stem theberries": "garnish",
        "theberries": "garnish",
        "divide thedough": "garnish",
        "thedough": "garnish",
        "^teaspoon": "tsp",
        "trong hotcoffee": "coffee",
        "hot coffee": "coffee",
        "hotcoffee": "coffee",
        "ugax": "sugar",
        "aslow fire": "garnish",
        "slow fire": "garnish",
        "fishbroth": "fish stock",
        "fish broth": "fish stock",
        "ormilk": "milk",
        "fine-chopped": "chopped",
        "teaspooufuls": "tsp",
        "bak-": "garnish",
        "cupful chicken gravy": "gravy",
        "chicken gravy": "gravy",
        "orcream sauce": "cream",
        "cream sauce": "cream",
        "wingold flour": "flour",
        "wingold": "garnish",
        "tspcream tartar": "cream of tartar",
        "tspcream": "garnish",
        "cream tartar": "cream of tartar",
        "large tspcream": "cream of tartar",
        "tblsp.": "tbsp",
        "tblsp": "tbsp",
        "allspice kernels": "allspice",
        "kernels": "garnish",
        "pepper kernels": "peppercorns",
        "black pepper kernels": "peppercorns",
        "peppercorns": "pepper",
        "ofgirated": "grated",
        "oflemon": "lemon",
        "ofgrated": "grated",
        "of&iely": "finely",
        "&iely": "finely",
        "offinely": "finely",
        "ofmelted": "melted",
        "ofsalt": "salt",
        "of grated horseradish": "horseradish",
        "grated horseradish": "horseradish",
        "of lemon juice": "lemon juice",
        "of grated cheese": "cheese",
        "of finely minced parsley": "parsley",
        "finely minced": "minced",
        "of finely minced celery": "celery",
        "level teaspoons": "garnish",
        "of melted butter": "butter",

        # Equipment mixed with ingredients (filter out)
        "bowl": "garnish",
        "fork": "garnish",
        "pie-pan": "garnish",
        "saucepan": "garnish",
        "covered saucepan": "garnish",
        "mixing-spoon": "garnish",
        "sifter": "garnish",
        "bread orcakepan": "garnish",
        "orcakepan": "garnish",
        "cakepan": "garnish",
        "2 bowls": "garnish",
        "plate": "garnish",

        # Instruction text mixed in
        "putthefruit": "garnish",
        "rsetthesaucepan": "garnish",
        "over aslow fire": "garnish",
        "inasaucepan": "garnish",
        "beaten light flour": "flour",
        "asneeded": "garnish",
        "flour asneeded": "flour",
        "egg;": "egg",
        "butter;": "butter",
        "%cupsautomatic": "garnish",
        "automatic": "garnish",

        # Complex fraction patterns
        "¼ cups": "cups",
        "½ cup": "cup",
        "¾ cup": "cup",
        "½ lb": "lb",
        "¼ lb": "lb",
        "¾ lb": "lb",

        # More OCR patterns
        "good sized pike": "fish",
        "pike": "fish",
        "bayleaves": "bay leaves",
        "bay leaves": "bay leaf",
        "ggg": "egg",
        "ggg.": "egg",
        "ggg.beaten": "egg",
        "c.butter": "butter",
        "c.milk": "milk",
        "c.flour": "flour",
        "c.diced": "garnish",
        "c.malaga": "garnish",
        "malaga grapes": "grapes",
        "grape fruit": "grapefruit",
        "salmon fillets": "salmon",
        "skin-on salmon": "salmon",
        "center-cut": "garnish",
        "oz packages pie dough": "pie crust",
        "packages pie dough": "pie crust",
        "oz can white chicken": "chicken",
        "can white chicken": "chicken",
        "oz can sliced ripe": "olives",
        "can sliced ripe": "olives",
        "oz package pita": "bread",
        "package pita": "bread",
        "oz container prepared": "hummus",
        "container prepared": "garnish",
        "medium roma": "tomatoes",
        "oz container crumbled": "feta cheese",
        "container crumbled": "garnish",
        "pkg) baker's": "chocolate",
        "squares (1 pkg)": "garnish",
        "oz package philadelphia": "cream cheese",
        "package philadelphia": "cream cheese",
        "oz can eagle brand": "sweetened condensed milk",
        "can eagle brand": "sweetened condensed milk",
        "to-15-pound whole": "garnish",
        "to-12-oz center": "garnish",
        "slice ginger": "ginger",
        "oz jar pizza sauce": "pizza sauce",
        "jar pizza sauce": "pizza sauce",
        "oz can chicken broth": "chicken broth",
        "can chicken broth": "chicken broth",
        "oz can kidney beans": "kidney beans",
        "can kidney beans": "kidney beans",
        "oz pkgs onion soup": "onion powder",
        "pkgs onion soup": "onion powder",
        "oz pkgs chili seasoning": "chili powder",
        "pkgs chili seasoning": "chili powder",
        "oz can mild chili": "kidney beans",
        "can mild chili": "kidney beans",
        "oz pkg mild chili": "chili powder",
        "pkg mild chili": "chili powder",
        "oz pkg thin": "spaghetti",
        "pkg thin": "garnish",
        "inch flour or spinach": "tortillas",
        "flour or spinach": "garnish",
        "pkg zwieback (6 oz.)": "crackers",
        "zwieback (6 oz.)": "crackers",
        "oz turkey polish": "sausage",
        "turkey polish": "sausage",
        "pkg stove top stuffi": "stuffing",
        "oz) can cream": "cream of mushroom soup",
        "oz can cream": "cream of mushroom soup",
        "sliced banana.": "banana",
        "cup strawberry gelatin.": "gelatin",
        "strawberry gelatin.": "gelatin",
        "finely cutapple.": "apple",
        "-sized cauliflower.": "cauliflower",
        "rounded tablespoon flour.": "flour",
        "tablespoon flour.": "flour",
        "rounded tablespoon butter.": "butter",
        "tablespoon butter.": "butter",

        # Batch 14 - More ingredient patterns
        "tbsp soy": "soy sauce",
        "cup soy": "soy sauce",
        "soy": "soy sauce",
        "veg oil": "vegetable oil",
        "cup veg oil": "vegetable oil",
        "sesame seed": "sesame seeds",
        "cup sesame seed": "sesame seeds",
        "lundberg": "garnish",
        "[unclear]": "garnish",
        "good squash": "squash",
        "spoons dry bread": "bread",
        "dry bread": "bread",
        "spoons rose-water": "rose water",
        "rose-water": "rose water",
        "rose water": "garnish",
        "do. wine": "wine",
        "do wine": "wine",
        "spoon flour": "flour",
        "pork or beef": "beef",
        "cups pork or beef": "beef",
        "zucchini squash": "zucchini",
        "medium zucchini": "zucchini",
        "large green chiles": "green chilies",
        "green chiles": "green chilies",
        "green chile": "green chilies",
        "chiles": "green chilies",
        "chile": "green chilies",
        "triscuit": "crackers",
        "refrigerator biscuits": "biscuits",
        "can refrigerator": "garnish",
        "spanish-style tomato sauce": "tomato sauce",
        "spanish-style": "garnish",
        "frozen cut okra": "okra",
        "cut okra": "okra",
        "chile powder flakes": "chili powder",
        "chile powder": "chili powder",
        "file powder": "garnish",
        "cream-style cottage cheese": "cottage cheese",
        "cream-style": "garnish",
        "fish steaks": "fish",
        "lb fish steaks": "fish",
        "fish fillets": "fish",
        "cleaned, small whole fish": "fish",
        "small whole fish": "fish",
        "whole fish": "fish",
        "such as trout or salmon": "garnish",
        "trout or salmon": "fish",
        "trout": "fish",
        "fennel bulb": "fennel",
        "small chunk of parmesan": "parmesan cheese",
        "chunk of parmesan": "parmesan cheese",
        "parmesan, shaved": "parmesan cheese",
        "shaved": "garnish",
        "cup of parsley": "parsley",
        "of parsley": "parsley",
        "basil, dill": "garnish",
        "dill or other": "dill",
        "or other": "garnish",
        "sauerkraut": "cabbage",
        "rinsed and drained": "garnish",
        "beef soup bones": "beef",
        "soup bones": "beef",
        "stew beef": "beef",
        "lb stew beef": "beef",
        "english peas": "peas",
        "can english peas": "peas",
        "carton": "container",
        "oz carton": "container",
        "can (4 oz)": "can",
        "can (8 oz)": "can",
        "can (10 oz)": "can",
        "can (14 oz)": "can",
        "cans (4 oz each)": "can",
        "each)": "garnish",
        "diced": "garnish",
        "chopped": "garnish",
        "drained": "garnish",
        "cooked and drained": "garnish",
        "black olives": "olives",
        "can black olives": "olives",
        "pkg (8 oz)": "package",
        "pkg (10 oz)": "package",
        "egg noodles, cooked": "egg noodles",
        "apples, peeled": "apples",
        "thinly sliced": "garnish",
        "peeled and": "garnish",
        "cup lemon juice": "lemon juice",
        "dry thyme": "thyme",
        "tsp dry": "garnish",

        # Halibut and complex OCR patterns
        "ful lemon juice": "lemon juice",
        "tbsp ful": "tbsp",
        "tsp ful": "tsp",
        "cupful fishbroth": "fish stock",
        "cupful cream": "cream",
        "ful grated onion": "onion",
        "'3 cupful": "garnish",
        "ful chopped": "garnish",
        "ful fine-chopped": "garnish",
        "fine-chopped parsley": "parsley",
        "fid criseo": "shortening",
        "criseo": "shortening",
        "j2 teaspoonful": "garnish",
        "cup ful milk": "milk",
        "cupfuls chicken broth": "chicken broth",
        "_'cupful chicken gravy": "gravy",
        "'_'cupful": "garnish",
        "bak-'_'cupful": "garnish",
        "teaspooufuls bak-": "garnish",

        # Cream horseradish sauce OCR
        "tablespoons ofgirated horseradish": "horseradish",
        "tablespoons ofgrated cheese": "cheese",
        "tablespoons of&iely minced parsley": "parsley",
        "two tablespoons": "tbsp",

        # More patterns
        "slices smoked salmon": "salmon",
        "thin slices bacon": "bacon",
        "fresh rocket": "arugula",
        "diced,": "garnish",
        "roma tomatoes, diced": "tomatoes",
        "oz packages pie dough mix": "pie crust",
        "9.75-oz can white chicken": "chicken",
        "3-oz can sliced ripe": "olives",
        "baker's semi-sweet chocolate squares": "chocolate",
        "semi-sweet chocolate squares": "chocolate",
        "chocolate squares": "chocolate",
        "can eagle brand sweetened": "sweetened condensed milk",
        "eagle brand sweetened": "sweetened condensed milk",
        "bunch fresh dill": "dill",
        "bunch radishes": "radishes",
        "muenster or gouda cheese": "cheese",
        "slices muenster or gouda": "cheese",
        "oven-roasted turkey (leftover": "turkey",
        "generous pinch freshly": "garnish",
        "package pepperonis": "pepperoni",
        "16-oz jar pizza sauce": "pizza sauce",
        "small can tomato paste": "tomato paste",
        "inch cucumber": "cucumber",
        "inch stem broccoli": "broccoli",
        "inch slice beetroot": "beets",
        "large shredded carrots": "carrots",
        "1/2 oz can chicken broth": "chicken broth",
        "shredded cheddar cheese": "cheddar cheese",
        "optional shredded": "garnish",
        "for garnish shredded": "garnish",
        "for serving saltine crackers": "garnish",
        "or corn chips": "garnish",
        "1.35 oz pkgs": "garnish",
        "1 1/4 oz pkgs": "garnish",
        "oz can red kidney": "kidney beans",
        "can red kidney": "kidney beans",
        "red kidney beans": "kidney beans",
        "pinch cumin powder": "cumin",
        "dash chili powder": "chili powder",
        "leaves kale": "kale",
        "bunch kale": "kale",
        "dash cayenne": "cayenne pepper",
        "8 inch flour": "tortillas",
        "or spinach tortillas": "tortillas",
        "pkg zwieback (6 oz.)": "crackers",
        "½ lb. cottage cheese": "cottage cheese",
        "juice and rind of ½": "lemon juice",
        "juice and rind": "garnish",
        "pieces boneless breast of": "chicken",
        "boneless breast of chicken": "chicken",
        "can chicken broth": "chicken broth",
        "slices mozzarella cheese": "mozzarella cheese",
        "oz turkey polish kielbasa": "sausage",
        "turkey polish kielbasa": "sausage",
        "large celery stalk": "celery",
        "large carrots": "carrots",
        "pkg family size": "garnish",
        "family size chicken": "chicken",
        "pkg stove top stuffi ng": "stuffing",
        "(8 oz) can cream of mushroom": "cream of mushroom soup",
        "can cream of mushroom soup": "cream of mushroom soup",
        "cup ½ cup of milk": "milk",
        "½ cup of cream": "cream",
        "tsp ½ tablespoonful of salt": "salt",
        "medium -sized cauliflower.": "cauliflower",
        "11-to-15-pound whole smoked ham": "ham",
        "to-15-pound whole smoked ham": "ham",
        "1/2 cup apple butter": "apple butter",
        "1/2 cup dijon mustard": "mustard",
        "1/2 inch slice ginger": "ginger",
        "inch slice ginger": "ginger",
        "cup chicken broth": "chicken broth",
        "for serving cooked rice": "garnish",
        "spoons biscuit": "biscuit",

        # Batch 15 - Final cleanup patterns
        "whole ciabatta": "bread",
        "oz package pita bread": "bread",
        "package pita bread": "bread",
        "oz container prepared hummus": "hummus",
        "container prepared hummus": "hummus",
        "roma tomatoes, diced": "tomatoes",
        "oz container crumbled feta": "feta cheese",
        "container crumbled feta": "feta cheese",
        "crumbled feta cheese": "feta cheese",
        "oz packages pie dough": "pie crust",
        "packages pie dough": "pie crust",
        "oz can white chicken meat": "chicken",
        "can white chicken meat": "chicken",
        "white chicken meat, drained": "chicken",
        "cups shredded rotisserie": "chicken",
        "shredded rotisserie chicken": "chicken",
        "oz can sliced ripe olives": "olives",
        "can sliced ripe olives": "olives",
        "sliced ripe olives": "olives",
        "(1 pkg) baker's": "chocolate",
        "baker's semi-sweet chocolate": "chocolate",
        "oz package philadelphia cream": "cream cheese",
        "package philadelphia cream": "cream cheese",
        "oz can eagle brand sweetened": "sweetened condensed milk",
        "can eagle brand sweetened": "sweetened condensed milk",
        "sweetened condensed milk": "sweetened condensed milk",
        "center-cut skin-on salmon": "salmon",
        "skin-on salmon fillets": "salmon",
        "salmon fillets, pin": "salmon",
        "bunch fresh dill, chopped": "dill",
        "fresh dill, chopped": "dill",
        "bunch radishes, thinly": "radishes",
        "to-15-pound whole smoked": "ham",
        "whole smoked ham": "ham",
        "cup apple butter": "apple butter",
        "cup dijon mustard": "mustard",
        "slices muenster or gouda cheese": "cheese",
        "muenster or gouda cheese": "cheese",
        "slices oven-roasted turkey": "turkey",
        "oven-roasted turkey (leftover": "turkey",
        "(leftover or deli-sliced)": "garnish",
        "generous pinch freshly grated": "nutmeg",
        "freshly grated nutmeg": "nutmeg",
        "inch slice ginger": "ginger",
        "package pepperonis": "pepperoni",
        "oz jar pizza sauce": "pizza sauce",
        "small can tomato paste": "tomato paste",
        "oz can chicken broth": "chicken broth",
        "can chicken broth": "chicken broth",
        "optional shredded cheddar": "garnish",
        "optional sour cream": "garnish",
        "oz pkgs onion soup mix": "onion powder",
        "pkgs onion soup mix": "onion powder",
        "onion soup mix": "onion powder",
        "for garnish shredded cheddar": "garnish",
        "for garnish sour cream": "garnish",
        "for serving saltine": "garnish",
        "saltine crackers or corn": "garnish",
        "oz pkgs chili seasoning": "chili powder",
        "pkgs chili seasoning mix": "chili powder",
        "chili seasoning mix": "chili powder",
        "pinch cumin powder": "cumin",
        "dash chili powder": "chili powder",
        "leaves kale": "kale",
        "bunch kale": "kale",
        "dash cayenne": "cayenne pepper",
        "8 inch flour or spinach": "tortillas",
        "pieces boneless breast": "chicken",
        "boneless breast of chicken": "chicken",
        "slices mozzarella cheese": "mozzarella cheese",
        "oz turkey polish kielbasa": "sausage",
        "large celery stalk": "celery",
        "large carrots": "carrots",
        "pkg family size chicken": "chicken",
        "pkg stove top stuffi ng": "stuffing",
        "(8 oz) can cream of mushroom": "cream of mushroom soup",
        "can cream of mushroom soup": "cream of mushroom soup",
        "cup ½ cup of milk": "milk",
        "½ cup of cream": "cream",
        "tsp ½ tablespoonful of salt": "salt",
        "sliced banana.": "banana",
        "cup strawberry gelatin.": "gelatin",
        "finely cutapple.": "apple",
        "medium -sized cauliflower.": "cauliflower",
        "rounded tablespoon flour.": "flour",
        "rounded tablespoon butter.": "butter",
        "ful lemon juice": "lemon juice",
        "cupful fishbroth ormilk": "fish stock",
        "ful grated onion": "onion",
        "'3 cupful cream": "cream",
        "ful chopped 1 egg": "egg",
        "teaspooufuls bak-'_'cupful": "garnish",
        "orcream sauce": "cream",
        "fid criseo j2 teaspoonful": "shortening",
        "j2 teaspoonful salt": "salt",
        "cup ful milk (about)": "milk",
        "cupfuls chicken broth": "chicken broth",
        "tablespoons ofgirated horseradish": "horseradish",
        "tablespoons ofgirated horseradish,": "horseradish",
        "tablespoons ofgrated cheese.": "cheese",
        "tablespoons of&iely minced parsley.": "parsley",
        "good squash": "squash",
        "spoons dry bread or biscuit": "bread",
        "dry bread or biscuit": "bread",
        "spoons rose-water": "rose water",
        "do. wine": "wine",
        "spoon flour": "flour",
        "pkg (10 oz) frozen broccoli": "broccoli",
        "frozen broccoli, chopped": "broccoli",
        "frozen broccoli": "broccoli",
        "jar (8 oz) processed cheese": "cheese",
        "processed cheese spread": "cheese",
        "cheese spread": "cheese",
        "cup green chiles, chopped": "green chilies",
        "green chiles, chopped": "green chilies",
        "pkg (8 oz) egg noodles": "egg noodles",
        "egg noodles, cooked and drained": "egg noodles",
        "carton (8 oz) sour cream": "sour cream",
        "large green chiles, chopped": "green chilies",
        "can (4 oz) black olives": "olives",
        "cups apples, peeled": "apples",
        "apples, peeled and thinly": "apples",
        "can (14 oz) sauerkraut": "cabbage",
        "sauerkraut, rinsed and drained": "cabbage",
        "c + 2 tbs flour": "flour",
        "tbs flour": "flour",
        "tsp baking soda": "baking soda",
        "tsp baking powder pinch": "baking powder",
        "baking powder pinch of salt": "baking powder",
        "pinch of salt": "salt",
        "tbs crisco(solid)": "shortening",
        "crisco(solid)": "shortening",
        "c buttermilk": "buttermilk",
        "fennel bulb": "fennel",
        "cup of parsley, basil": "parsley",
        "parsley, basil, dill": "parsley",
        "basil, dill or other": "garnish",
        "chunk of parmesan, shaved": "parmesan cheese",
        "cup lemon juice": "lemon juice",
        "1/4 stick celery": "celery",

        # Batch 16 - Partial recipes common missing items
        "cup chicken broth": "chicken broth",
        "can chicken broth": "chicken broth",
        "large flour tortillas": "tortillas",
        "cup salad oil": "vegetable oil",
        "salad oil": "vegetable oil",
        "cup applesauce": "applesauce",
        "cup unsweetened applesauce": "applesauce",
        "cup sweetened applesauce": "applesauce",
        "unsweetened applesauce": "applesauce",
        "sweetened applesauce": "applesauce",
        "slices swiss cheese": "swiss cheese",
        "swiss cheese": "cheese",
        "squares chocolate": "chocolate",
        "square chocolate": "chocolate",
        "lb ground italian sausage": "sausage",
        "ground italian sausage": "sausage",
        "italian sausage": "sausage",
        "can water": "garnish",
        "egg-yolks": "egg yolk",
        "egg-yolk": "egg yolk",
        "cup apples": "apples",
        "large apples": "apples",
        "cup green apple": "apples",
        "green apple": "apples",
        "granny smith apples": "apples",
        "small orange": "orange",
        "whip cream": "whipped cream",
        "whipped cream": "cream",
        "cup unsweetened orange juice": "orange juice",
        "unsweetened orange juice": "orange juice",
        "small can tomato sauce": "tomato sauce",
        "packet taco seasoning": "chili powder",
        "cup cut-up walnuts": "walnuts",
        "cut-up walnuts": "walnuts",
        "slices cheddar cheese": "cheddar cheese",
        "cup quick-cooking oats": "oats",
        "quick-cooking oats": "oats",
        "instant-cooking oats": "oats",
        "cup instant-cooking oats": "oats",
        "pure anise extract": "anise extract",
        "anise extract": "vanilla",
        "cup raspberry jam": "jam",
        "raspberry jam": "jam",
        "cup chocolate hazelnut spread": "nutella",
        "chocolate hazelnut spread": "nutella",
        "nutella": "chocolate",
        "tbsp white flour": "flour",
        "white flour": "flour",
        "tbsp tangy salsa": "salsa",
        "tangy salsa": "salsa",
        "jar spicy salsa": "salsa",
        "spicy salsa": "salsa",
        "tbsp virgin olive oil": "olive oil",
        "virgin olive oil": "olive oil",
        "tbsp granulated tapioca": "tapioca",
        "granulated tapioca": "tapioca",
        "granulated tapioca.": "tapioca",

        # Historical OCR patterns
        "teaspoons ofbaking powder.": "baking powder",
        "teaspoons ofbaking powder": "baking powder",
        "ofbaking powder": "baking powder",
        "tablespoonfuls shortening.": "shortening",
        "tablespoonfuls shortening": "shortening",
        "teaspoons ofcinnamon.": "cinnamon",
        "teaspoons ofcinnamon": "cinnamon",
        "ofcinnamon": "cinnamon",
        "tablespoons ofshortening.": "shortening",
        "tablespoons ofshortening": "shortening",
        "tablespoons offinely minced parsley.": "parsley",
        "offinely minced parsley": "parsley",
        "hotmilk,": "milk",
        "hotmilk": "milk",
        "hot milk": "milk",
        "theory andpractice ofcookery": "garnish",
        "andpractice ofcookery": "garnish",
        "finely cutapples.": "apples",
        "finely cutapples": "apples",
        "cutapples": "apples",
        "boiled tripe.": "beef",
        "boiled tripe": "beef",
        "tripe": "beef",
        "steakfish.": "fish",
        "steakfish": "fish",
        "peck spinach.": "spinach",
        "peck spinach": "spinach",
        "tablespoonfuls syrup,": "syrup",
        "tablespoonfuls syrup": "syrup",
        "tablespoons ofbaking powder.": "baking powder",
        "tablespoons ofbaking powder": "baking powder",
        "two cloves.": "cloves",
        "two cloves": "cloves",
        "can milk": "evaporated milk",

        # Batch 17 - More partial recipe patterns
        "vegetable spray": "cooking spray",
        "lump crabmeat": "crab",
        "crabmeat": "crab",
        "loaf of french bread": "bread",
        "french bread": "bread",
        "chopped chilis": "chili peppers",
        "chopped chili": "chili peppers",
        "frozen pizza dough": "pizza dough",
        "pizza dough": "bread",
        "breakfast sausage": "sausage",
        "chorizo sausage": "chorizo",
        "ciabatta rolls": "bread",
        "ciabatta roll": "bread",
        "ciabatta": "bread",
        "pesto sauce": "pesto",
        "cheese sauce": "cheese",
        "plain chocolate chips": "chocolate chips",
        "pineapple marmalade": "jam",
        "pieces flour tortillas": "tortillas",
        "flour tortillas": "tortillas",
        "semi sweet chocolate chips": "chocolate chips",
        "semi-sweet chocolate chips": "chocolate chips",
        "semisweet chocolate chips": "chocolate chips",
        "frozen shredded hash browns": "potato",
        "shredded hash browns": "potato",
        "hash browns": "potato",
        "cook and serve vanilla pudding": "pudding",
        "vanilla pudding": "pudding",
        "instant pudding": "pudding",
        "box pudding": "pudding",
        "lemon lemon zest": "lemon zest",
        "bacon bits": "bacon",
        "semi-sweet baking chocolate": "chocolate",
        "semisweet baking chocolate": "chocolate",
        "baking chocolate": "chocolate",
        "campbell's condensed french onion soup": "onion soup",
        "campbell's condensed": "soup",
        "condensed french onion soup": "onion soup",
        "french onion soup": "onion soup",
        "onion soup": "soup",
        "corn tortillas": "tortillas",
        "-inch corn tortillas": "tortillas",
        "heinz chili sauce": "chili sauce",
        "-oz bottle": "garnish",
        "for garnish sour cream": "garnish",
        "for garnish shredded cheddar cheese": "garnish",
        "for garnish": "garnish",
        "cup apple butter": "jam",
        "apple butter": "jam",
        "peeled and grated": "garnish",
        "tub (": "garnish",
        "level tablespoons ofbaking powder": "baking powder",
        "level tablespoons of baking powder": "baking powder",
        "tsp three level tablespoons": "garnish",

        # Batch 18 - More historical OCR and remaining patterns
        "tablespoonfuls shortening": "shortening",
        "tablespoonfuls ofshortening": "shortening",
        "tablespoons offinely": "garnish",
        "offinely minced parsley": "parsley",
        "tablespoons ofparsley": "parsley",
        "ofparsley": "parsley",
        "tablespoonfuls ofsyrup": "maple syrup",
        "tablespoons ofsyrup": "maple syrup",
        "tablespoonfuls syrup": "maple syrup",
        "syrup.": "maple syrup",
        "syrup": "maple syrup",
        "tablespoonful ofbutter": "butter",
        "tablespoonfuls ofbutter": "butter",
        "tablespoonful offlour": "flour",
        "tablespoonfuls offlour": "flour",
        "%cups flour": "flour",
        "two eggis": "eggs",
        "eggis": "eggs",
        "teaspoonfuls ofbaking powder": "baking powder",
        "teaspoonfuls ofcinnamon": "cinnamon",
        "ofcinnamon": "cinnamon",
        "teaspoon ofpepper": "black pepper",
        "ofpepper": "black pepper",
        "gill rose-water": "rosewater",
        "rose-water": "rosewater",
        "rosewater": "vanilla",
        "slices swiss cheese": "swiss cheese",
        "swiss cheese": "cheese",
        "huckleberries": "blueberries",
        "cup huckleberries": "blueberries",
        "green apple": "apples",
        "small can tomato sauce": "tomato sauce",
        "packet taco seasoning": "chili powder",
        "pkg taco seasoning": "chili powder",
        "taco seasoning": "chili powder",
        "graham flour": "whole wheat flour",
        "cup graham flour": "whole wheat flour",
        "medium papaya": "mango",
        "papaya": "mango",
        "pkg chocolate bits": "chocolate chips",
        "chocolate bits": "chocolate chips",
        "box chocolate pudding": "pudding",
        "large box chocolate pudding": "pudding",
        "chocolate pudding": "pudding",
        "box vanilla pudding": "pudding",
        "heinz chili sauce": "chili sauce",
        "chili sauce": "ketchup",
        "nutella": "chocolate",
        "cup nutella": "chocolate",
        "thin ": "garnish",
        "bit of cinnamon": "cinnamon",
        "small bit of cinnamon": "cinnamon",
        "a lemon's yellow rind": "lemon zest",
        "lemon's yellow rind": "lemon zest",
        "yellow rind": "lemon zest",
        "-oz squares": "garnish",
        "squares semi-sweet baking chocolate": "chocolate",
        "baking chocolate, melted": "chocolate",
        "condensed french onion soup": "soup",
        "campbell's condensed": "soup",
        "for garnish sour cream": "garnish",
        "for garnish shredded": "garnish",

        # Batch 19 - More OCR and missing patterns
        "cutapples": "apples",
        "finely cutapples": "apples",
        "ofshortening": "shortening",
        "tablespoons ofshortening": "shortening",
        "tablespoonful ofshortening": "shortening",
        "cook and serve vanilla pudding": "pudding",
        "cook and serve chocolate pudding": "pudding",
        "cook and serve": "pudding",
        "stove top stuffi ng": "stuffing",
        "stuffi ng": "stuffing",
        "stuffing mix": "stuffing",
        "stove top": "stuffing",
        "picante sauce": "salsa",
        "jar picante sauce": "salsa",
        "maraschino cherry juice": "juice",
        "cherry juice": "juice",
        "can water chestnuts": "water chestnuts",
        "water chestnuts": "water chestnuts",
        "small can mushrooms": "mushrooms",
        "can mushrooms": "mushrooms",
        "leanstewing beef": "beef",
        "stewing beef": "beef",
        "yrup": "maple syrup",
        "almon": "almonds",
        "ornutmeg": "nutmeg",
        "granulated gelatin": "gelatin",
        "ofcelery": "celery",
        "stalks ofcelery": "celery",
        "cutindice": "garnish",
        "carrot cutindice": "carrots",
        "chopped boiled tongue": "beef",
        "boiled tongue": "beef",
        "hrimp": "shrimp",
        "can hrimp": "shrimp",
        "butter or olive oil": "butter",
        " or olive oil": "",
        " or butter": "",
        "t salt currants": "currants",
        "ful of chopped": "garnish",
        "%cups flour": "flour",
        "three level tablespoons baking powder": "baking powder",
        "level tablespoons baking powder": "baking powder",
        "large apples": "apples",
        "cup apples": "apples",

        # Batch 20 - More remaining patterns
        "chocolate hazelnut spread": "chocolate",
        "cup chocolate hazelnut spread": "chocolate",
        "chopped chilis": "chili peppers",
        "tbsp chopped chilis": "chili peppers",
        "chilis": "chili peppers",
        "frozen shredded hash browns": "potato",
        "cups frozen shredded hash browns": "potato",
        "small bit of cinnamon": "cinnamon",
        "bit of cinnamon": "cinnamon",
        "thin": "garnish",
        "squares semi-sweet baking chocolate": "chocolate",
        "semi-sweet baking chocolate": "chocolate",
        "oz squares": "garnish",
        "pkg chocolate bits": "chocolate chips",
        "can campbell's condensed": "soup",
        "campbell's condensed french onion soup": "soup",
        "(10 1/2 oz) can": "garnish",
        "pint milk 1 egg": "garnish",
        "cup of farina": "farina",
        "farina": "cream of wheat",
        "maraschino cherry juice": "juice",
        "cup maraschino cherry juice": "juice",
        "cherry juice": "juice",
        "can water chestnuts": "water chestnuts",
        "water chestnuts": "water chestnuts",
        "small can mushrooms": "mushrooms",
        "can mushrooms": "mushrooms",
        "pkg stove top stuffi ng": "stuffing",
        "stove top stuffi ng": "stuffing",
        "jar picante sauce": "salsa",
        "can water": "garnish",
        "yolk of an egg": "egg yolk",
        "cup stale bread": "bread",
        "stale bread": "bread",
        "beef bones": "beef",
        "lb beef bones": "beef",
        "ham bone": "ham",
        "red food coloring": "garnish",
        "food coloring": "garnish",
        "ful ofcream oftartar": "cream of tartar",
        "ofcream oftartar": "cream of tartar",
        "dijon mustard": "mustard",
        "cup dijon mustard": "mustard",
        "sticks cinnamon": "cinnamon",
        "can cream of chicken soup": "soup",
        "(10 3/4 oz) can cream of chicken soup": "soup",
        "cream of chicken soup": "soup",
        "lb sausage": "sausage",

        # Batch 21 - More comprehensive patterns
        # Egg variations
        "yolk an egg": "egg yolk",
        "yolk of an egg": "egg yolk",
        "egg yolks": "egg yolk",
        "large egg yolk": "egg yolk",
        "large apples": "apple",
        "apples": "apple",
        "carton sour cream": "sour cream",
        "carton (8 oz) sour cream": "sour cream",
        "(8 oz) sour cream": "sour cream",
        "grated cheese": "cheese",
        "tablespoons ofgrated cheese": "cheese",
        "ofgrated cheese": "cheese",
        "chicken drummettes": "chicken",
        "drummettes": "chicken",
        "lingonberry preserves": "jam",
        "cranberry preserves": "jam",
        "sheet puff pastry": "pastry",
        "puff pastry": "pastry",
        "pastry": "pie crust",
        "pinch cayenne": "cayenne pepper",
        "bags spinach": "spinach",
        "oz bags spinach": "spinach",
        "string cheese": "mozzarella cheese",
        "mozzarella string cheese": "mozzarella cheese",
        "toasted sesame seeds": "sesame seeds",
        "sesame seeds": "garnish",
        "bouillon paste": "bouillon",
        "bouillon": "chicken broth",
        "chopped conch": "clams",
        "conch": "clams",
        "yellow bell pepper": "bell pepper",
        "red bell pepper": "bell pepper",
        "green bell pepper": "bell pepper",
        "packages cream cheese": "cream cheese",
        # Removed: "hot dogs": "sausage" - use specific hot dog entry
        # Removed: "hot dog": "sausage" - use specific hot dog entry
        "crisp bacon": "bacon",
        "soft wheat flour": "flour",
        "banana": "bananas",
        "large banana": "bananas",
        "half banana": "bananas",
        "sweetened condensed milk": "evaporated milk",
        "condensed milk": "evaporated milk",
        "cognac": "brandy",
        "brandy": "wine",
        "seltzer": "water",
        "club soda": "water",
        "sparkling apple juice": "apple juice",
        "fresh pears": "pears",
        "pears": "apples",
        "piece ginger": "ginger",
        "small piece ginger": "ginger",
        "inch cucumber": "cucumber",
        "inch stem broccoli": "broccoli",
        "inch slice beetroot": "beets",
        "beetroot": "beets",
        "small red bell pepper": "bell pepper",
        "scalded milk": "milk",
        "cup scalded milk": "milk",
        "chilled ginger ale": "ginger ale",
        "ginger ale": "soda",
        "soda": "water",
        "lime sherbet": "ice cream",
        "sherbet": "ice cream",
        "quarts lime sherbet": "ice cream",
        "ground coffee": "coffee",
        "finely ground coffee": "coffee",
        "tablespoons ground coffee": "coffee",
        "teaspoons finely ground coffee": "coffee",
        "rounding tablespoons ground coffee": "coffee",
        "beverages": "garnish",
        "coffee should beroasted": "garnish",
        "hops": "garnish",
        "essence of spruce": "garnish",
        # Batch 23 - More pattern fixes
        "small bit cinnamon": "cinnamon",
        "small bit of cinnamon": "cinnamon",
        "bit of cinnamon": "cinnamon",
        "bit cinnamon": "cinnamon",
        "kale leaves": "kale",
        "kale": "spinach",
        "chopped basil and thyme": "basil",
        "basil and thyme": "basil",
        "spring onion greens": "green onion",
        "spring onion": "green onion",
        "sweet ham": "ham",
        "white bread": "bread",
        "sliced white bread": "bread",
        "dark chocolate": "chocolate",
        "ciabatta": "bread",
        "whole ciabatta": "bread",
        "cream of coconut": "coconut milk",
        "shredded coconut": "coconut",
        "marshmallow crème": "marshmallow",
        "marshmallow creme": "marshmallow",
        "corn muffin mix": "cornmeal",
        "pizza dough": "bread",
        "clam juice": "chicken broth",
        "cod fillet": "white fish",
        "goat cheese": "cheese",
        "leg of lamb": "lamb",
        "boneless leg of lamb": "lamb",
        "red curry paste": "curry paste",
        "curry paste": "curry powder",
        "beef tenderloin steaks": "beef",
        "beef tenderloin": "beef",
        "grass-fed beef": "beef",
        "tequila": "wine",
        "cognac": "wine",
        "walnut oil": "olive oil",
        "egg substitute": "egg",
        "liquid egg substitute": "egg",
        "lemon zest": "lemon",
        "finely grated lemon zest": "lemon",
        "rosemary leaves": "rosemary",
        "fresh rosemary leaves": "rosemary",
        "rosemary": "thyme",
        "sour cherry preserves": "jam",
        "cherry preserves": "jam",
        "raspberry preserves": "jam",
        "crystallized ginger": "ginger",
        "minced crystallized ginger": "ginger",
        "fleur de sel": "salt",
        "fine fleur de sel": "salt",
        # More complex patterns
        "fresh basil": "basil",
        "chopped finely": "garnish",
        "french baguette": "bread",
        "large french baguette": "bread",
        "baguette": "bread",
        "flaked dried fish": "white fish",
        "dried fish": "white fish",
        "cheddar cheese": "cheese",
        "slices cheddar cheese": "cheese",
        "sharp cheddar cheese": "cheese",
        "cheddar": "cheese",
        "parmigiano-reggiano cheese": "parmesan",
        "parmigiano-reggiano": "parmesan",
        "grated fresh parmigiano-reggiano cheese": "parmesan",
        "ground ginger": "ginger",
        "dash ground ginger": "ginger",
        "ground pork": "pork",
        "fat-free chicken broth": "chicken broth",
        "processed cheese": "cheese",
        "velveeta": "cheese",
        "velveeta light": "cheese",
        "shredded light processed cheese": "cheese",
        "ground turkey breast": "ground turkey",
        "ground turkey": "ground beef",
        "pizza dough": "bread",
        "thin-crust pizza dough": "bread",
        "refrigerated pizza dough": "bread",
        "julienne-cut peeled jicama": "jicama",
        "julienne-cut jicama": "jicama",
        "peeled jicama": "jicama",
        "black pepper": "pepper",
        "dash black pepper": "pepper",
        "cubed peeled apple": "apple",
        "cubed apple": "apple",
        "navel orange": "oranges",
        "sectioned orange": "oranges",
        "baby spinach": "spinach",
        "frozen baby spinach": "spinach",
        "frozen spinach": "spinach",
        "frozen chopped spinach": "spinach",
        "broccoli florets": "broccoli",
        "frozen broccoli florets": "broccoli",
        "frozen broccoli": "broccoli",
        "white mushrooms": "mushrooms",
        "quartered mushrooms": "mushrooms",
        "spreadable cheese": "cream cheese",
        "boursin": "cream cheese",
        "boursin light": "cream cheese",
        "garlic-and-herbs spreadable cheese": "cream cheese",
        "cilantro sprigs": "garnish",
        "sliced zucchini": "zucchini",
        "sliced carrots": "carrots",
        "carrots": "carrot",
        "beef tenderloin steaks": "beef",
        "grass-fed beef tenderloin steaks": "beef",
        "sliced fresh basil": "basil",
        "thinly sliced fresh basil": "basil",
        "whole-wheat french bread": "bread",
        "french bread": "bread",
        "fava beans": "lima beans",
        "shelled fava beans": "lima beans",
        "myrtle leaves": "garnish",
        "fresh myrtle leaves": "garnish",
        "cornbread stuffing": "stuffing",
        "mashed bananas": "bananas",
        "ripe mangoes": "mango",
        "mangoes": "mango",
        "assorted jams": "jam",
        "jams": "jam",
        "silver nonpareils": "garnish",
        "nonpareils": "garnish",
        "piece fresh ginger": "ginger",
        "inch piece fresh ginger": "ginger",
        "pork loin": "pork",
        "pork tenderloin": "pork",
        "boneless pork loin": "pork",
        "heritage pork loin": "pork",
        "italian sausage": "sausage",
        "hot italian sausage": "sausage",
        "turkey italian sausage": "sausage",
        "hot turkey italian sausage": "sausage",
        "extra rolled oats": "oats",
        "rolled oats": "oats",
        "butter and oats": "garnish",
        "vegetable shortening": "shortening",
        "gruyère cheese": "cheese",
        "gruyere cheese": "cheese",
        "ground savory": "thyme",
        "savory": "thyme",
        "corn muffin mix": "cornmeal",
        "jiffy": "cornmeal",
        "very ripe bananas": "bananas",
        "ripe bananas": "bananas",
        "butter or shortening": "butter",
        "rum or apple juice": "rum",
        "rum": "wine",
        "for serving whipped cream": "garnish",
        "for serving": "garnish",
        "mint chocolate chips": "chocolate chips",
        "brewed coffee": "coffee",
        "fresh peaches": "peaches",
        "amaretto liqueur": "liqueur",
        "amaretto": "liqueur",
        "liqueur": "wine",
        "ghee": "butter",
        "ghee or vegetable oil": "butter",
        "pinch ground black pepper": "black pepper",
        "ground black pepper": "black pepper",
        "cardamom seeds": "cardamom",
        "for deep frying oil": "garnish",
        "deep frying oil": "garnish",
        "dark rye flour": "rye flour",
        "rye flour": "whole wheat flour",
        "monkey bread dough": "bread",
        "recipe monkey bread dough": "bread",
        "xanthan gum": "cornstarch",
        "vanilla non-fat yogurt": "yogurt",
        "non-fat yogurt": "yogurt",
        "nonfat yogurt": "yogurt",
        # Protect specific berries from partial match on "berries" -> "blueberries"
        "strawberries": "strawberries",
        # Fix coconut patterns
        "cream coconut": "coconut milk",
        "cream of coconut": "coconut milk",
        "raspberries": "raspberries",
        "blackberries": "blackberries",
        "cranberries": "cranberries",
        # Removed: "berries" → "blueberries" - use specific berries entry
        "package brownie mix": "brownie mix",
        "bits crisp bacon": "bacon",
        # Removed: "dried beef" → "beef" - use specific dried beef entry
        "slices of dried beef": "dried beef",
        "cake fresh yeast": "yeast",
        "fresh yeast": "yeast",
        "slices pineapple": "pineapple",
        "chopped figs": "figs",
        "figs": "raisins",
        "dates": "raisins",
        "c hicken thighs": "chicken thigh",
        "skinned and boned": "garnish",
        "scant halfteaspoonful": "garnish",
        "ofsodamixed inwith milk": "garnish",
        "halfteaspoonful ofsodamixed": "baking soda",
        "capers": "olives",
        "steak seasoning": "seasoned salt",
        "cocktail-size meatballs": "meatballs",
        "pre-cooked": "garnish",
        "frozen": "garnish",
        "lb bag frozen": "garnish",
        # Batch 26 - More patterns
        "dozen strawberries": "strawberries",
        "hulled strawberries": "strawberries",
        "package shredded coconut": "coconut",
        "shredded coconut": "coconut",
        "flaked coconut": "coconut",
        "sweetened flaked coconut": "coconut",
        "sweetened coconut": "coconut",
        "coconut rum": "wine",
        "sparkling apple juice": "apple juice",
        "bottle sparkling apple juice": "apple juice",
        "smoked ham": "ham",
        "whole smoked ham": "ham",
        "puff pastry": "bread",
        "frozen puff pastry": "bread",
        "sheet puff pastry": "bread",
        "pie crust": "bread",
        "unbaked pie crust": "bread",
        "inch unbaked pie crust": "bread",
        "pinch cayenne": "cayenne pepper",
        "cayenne": "cayenne pepper",
        "roasted saigon cinnamon": "cinnamon",
        "saigon cinnamon": "cinnamon",
        "grated parmesan": "parmesan",
        "ramen noodles": "pasta",
        "packages ramen noodles": "pasta",
        "crusty bread": "bread",
        "slices crusty bread": "bread",
        "watercress": "spinach",
        "bunch watercress": "spinach",
        "ragù": "tomato sauce",
        "leftover ragù": "tomato sauce",
        "cups leftover ragù": "tomato sauce",
        "black beans": "black beans",
        "goya black beans": "black beans",
        "small tomato": "tomato",
        "small carrot": "carrot",
        "dijon mustard": "mustard",
        "cup dijon mustard": "mustard",
        "brewed black coffee": "coffee",
        "strong brewed coffee": "coffee",
        "strong brewed black coffee": "coffee",
        "orange juice or orange liqueur": "orange juice",
        "orange liqueur": "wine",
        "sliced zucchini": "zucchini",
        "inch sliced zucchini": "zucchini",
        "whole wheat french bread baguette": "bread",
        "whole-wheat french bread baguette": "bread",
        "oz whole-wheat french bread": "bread",
        "sliced fresh basil": "basil",
        "thinly sliced fresh basil": "basil",
        "cup thinly sliced fresh basil": "basil",
        "fresh rosemary leaves": "rosemary",
        "cups fresh rosemary leaves": "rosemary",
        "minced crystallized ginger": "ginger",
        "cup minced crystallized ginger": "ginger",
        "inch piece fresh ginger": "ginger",
        "piece fresh ginger": "ginger",
        "peeled and coarsely chopped": "garnish",
        "coarsely chopped": "garnish",
        "very ripe bananas": "bananas",
        "mashed about medium": "bananas",
        "frozen baby spinach": "spinach",
        "oz package frozen baby spinach": "spinach",
        "package frozen baby spinach": "spinach",
        "frozen broccoli florets": "broccoli",
        "package frozen broccoli florets": "broccoli",
        "oz frozen broccoli florets": "broccoli",
        "boneless leg of lamb": "lamb",
        "lb boneless leg of lamb": "lamb",
        "ground turkey breast": "ground turkey",
        "oz ground turkey breast": "ground turkey",
        "fat-free less-sodium chicken broth": "chicken broth",
        "oz can fat-free chicken broth": "chicken broth",
        "can fat-free chicken broth": "chicken broth",
        "ground pork": "pork",
        "oz ground pork": "pork",
        "dash ground ginger": "ginger",
        "oz grated fresh parmigiano-reggiano cheese": "parmesan",
        "ounce grated fresh parmigiano-reggiano cheese": "parmesan",
        "cup grated fresh parmigiano-reggiano cheese": "parmesan",
        "lb pork tenderloin": "pork",
        "pound pork tenderloin": "pork",
        "(1-pound) pork tenderloin": "pork",
        "boneless heritage pork loin": "pork",
        "(1-pound) boneless heritage pork loin": "pork",
        "oz package corn muffin mix": "cornmeal",
        "package corn muffin mix": "cornmeal",
        "corn muffin mix (such as jiffy)": "cornmeal",
        "oz box frozen chopped spinach": "spinach",
        "box frozen chopped spinach": "spinach",
        "oz jars marshmallow crème": "marshmallow",
        "jars marshmallow crème": "marshmallow",
        "marshmallow crème": "marshmallow",
        "marshmallow creme": "marshmallow",
        "oz can refrigerated thin-crust pizza dough": "bread",
        "can refrigerated thin-crust pizza dough": "bread",
        "refrigerated thin-crust pizza dough": "bread",
        "julienne-cut peeled jicama": "jicama",
        "inch julienne-cut peeled jicama": "jicama",
        "(3-inch) julienne-cut peeled jicama": "jicama",
        "navel orange": "oranges",
        "sectioned and chopped": "garnish",
        "can cream of chicken soup": "soup",
        "(10 3/4 oz) can cream of chicken soup": "soup",
        "oz can cream of chicken soup": "soup",
        "tsp ful ofcream oftartar": "cream of tartar",
        "ful ofcream oftartar": "cream of tartar",
        "ofcream oftartar": "cream of tartar",
        "can water": "garnish",
        "%cups flour": "flour",
        "t salt currants": "garnish",
        "small lettuce meat stock": "garnish",
        "flaked dried fish": "white fish",
        "cup flaked dried fish": "white fish",
        "sliced white bread": "bread",
        "pieces sliced white bread": "bread",
        "melted butter to grease ramekins": "garnish",
        "butter to grease ramekins": "garnish",
        "to grease ramekins": "garnish",
        "fresh basil chopped finely": "basil",
        "cup fresh basil chopped finely": "basil",
        "whole ciabatta": "bread",
        "ciabatta": "bread",
        "extra rolled oats": "oats",
        # Batch 28 - More DB mapping fixes
        "parmesan": "cheese",
        "grated parmesan": "cheese",
        "freshly grated parmesan": "cheese",
        "freshly grated parmesan cheese": "cheese",
        "for serving": "garnish",
        "liqueur": "wine",
        "amaretto liqueur": "wine",
        "amaretto": "wine",
        "waffles": "bread",
        "eggo waffles": "bread",
        "homestyle waffles": "bread",
        "kellogg's eggo": "bread",
        "butterscotch morsels": "chocolate chips",
        "butterscotch chips": "chocolate chips",
        "pitas": "bread",
        "small pitas": "bread",
        "pita bread": "bread",
        "chili crisp": "chili oil",
        "chili oil": "olive oil",
        "tbsp chili crisp": "olive oil",
        "tortellini": "pasta",
        "package tortellini": "pasta",
        "refrigerated tortellini": "pasta",
        "liquid smoke": "garnish",
        "tsp liquid smoke": "garnish",
        "long-grain rice": "rice",
        "cup long-grain rice": "rice",
        "fettucine noodles": "pasta",
        "fettucine": "pasta",
        "fettuccine": "pasta",
        "angel hair pasta": "pasta",
        "package angel hair pasta": "pasta",
        "package lasagna noodles": "pasta",
        "oven-ready lasagna noodles": "pasta",
        "lasagna noodles": "pasta",
        "package pepperonis": "pepperoni",
        "pepperonis": "pepperoni",
        "tomato paste": "tomato sauce",
        "small can tomato paste": "tomato sauce",
        "can tomato paste": "tomato sauce",
        "loaf french bread": "bread",
        "large loaf french bread": "bread",
        "converted rice": "rice",
        "parboiled rice": "rice",
        "instant white rice": "rice",
        "frozen okra": "okra",
        "whole baby okra": "okra",
        "frozen whole baby okra": "okra",
        "oven-roasted turkey": "turkey",
        "leftover turkey": "turkey",
        "deli turkey": "turkey",
        "slices turkey": "turkey",
        "dried cherries": "cherries",
        "chopped dried cherries": "cherries",
        "bite-size pretzels": "pretzels",
        "mozzarella string cheese": "mozzarella",
        "string cheese": "mozzarella",
        "pieces mozzarella string cheese": "mozzarella",
        "ears corn": "corn",
        "ears of corn": "corn",
        "shrimp": "shrimp",
        "deveined peeled shrimp": "shrimp",
        "peeled shrimp": "shrimp",
        "lb deveined peeled shrimp": "shrimp",
        "goya black beans": "black beans",
        "cans goya black beans": "black beans",
        "each goya black beans": "black beans",
        # Batch 29 - More ingredient patterns from analysis
        "fresh basil": "basil",
        "chopped fresh basil": "basil",
        "sliced fresh basil": "basil",
        "thinly sliced fresh basil": "basil",
        "shredded coconut": "coconut",
        "flaked coconut": "coconut",
        "package shredded coconut": "coconut",
        "frozen spinach": "spinach",
        "frozen chopped spinach": "spinach",
        "baby spinach": "spinach",
        "frozen baby spinach": "spinach",
        "package frozen spinach": "spinach",
        "corn muffin mix": "cornmeal",
        "package corn muffin mix": "cornmeal",
        "pork tenderloin": "pork",
        "lb pork tenderloin": "pork",
        "pound pork tenderloin": "pork",
        "pork loin": "pork",
        "lb pork loin": "pork",
        "boneless pork loin": "pork",
        "heritage pork loin": "pork",
        "parmigiano-reggiano": "cheese",
        "grated parmigiano-reggiano": "cheese",
        "fresh parmigiano-reggiano": "cheese",
        "ground ginger": "ginger",
        "dash ground ginger": "ginger",
        "crystallized ginger": "ginger",
        "minced crystallized ginger": "ginger",
        "piece fresh ginger": "ginger",
        "inch piece ginger": "ginger",
        "piece ginger": "ginger",
        "ground pork": "pork",
        "oz ground pork": "pork",
        "lb ground pork": "pork",
        "ground turkey": "turkey",
        "ground turkey breast": "turkey",
        "oz ground turkey": "turkey",
        "lb ground turkey": "turkey",
        "less-sodium beef broth": "beef broth",
        "carton beef broth": "beef broth",
        "oz carton beef broth": "beef broth",
        "less-sodium chicken broth": "chicken broth",
        "fat-free chicken broth": "chicken broth",
        "fat-free less-sodium chicken broth": "chicken broth",
        "oz can chicken broth": "chicken broth",
        "pizza dough": "bread",
        "refrigerated pizza dough": "bread",
        "thin-crust pizza dough": "bread",
        "red curry paste": "curry powder",
        "tbsp red curry paste": "curry powder",
        "dijon mustard": "mustard",
        "cup dijon mustard": "mustard",
        "tbsp dijon mustard": "mustard",
        "ramen noodles": "pasta",
        "packages ramen noodles": "pasta",
        "package ramen noodles": "pasta",
        "smoked mozzarella": "mozzarella",
        "slices smoked mozzarella": "mozzarella",
        "sliced mozzarella": "mozzarella",
        "white rice": "rice",
        "converted white rice": "rice",
        "parboiled white rice": "rice",
        "instant white rice": "rice",
        "sparkling apple juice": "apple juice",
        "bottle sparkling apple juice": "apple juice",
        "smoked ham": "ham",
        "whole smoked ham": "ham",
        "lb smoked ham": "ham",
        "pound smoked ham": "ham",
        "leg of lamb": "lamb",
        "boneless leg of lamb": "lamb",
        "lb leg of lamb": "lamb",
        "navel orange": "orange",
        "sectioned navel orange": "orange",
        "chopped navel orange": "orange",
        "fresh rosemary": "rosemary",
        "fresh rosemary leaves": "rosemary",
        "cups fresh rosemary": "rosemary",
        "broccoli florets": "broccoli",
        "frozen broccoli florets": "broccoli",
        "package frozen broccoli": "broccoli",
        "sliced zucchini": "zucchini",
        "inch sliced zucchini": "zucchini",
        "cups sliced zucchini": "zucchini",
        "mashed bananas": "banana",
        "ripe bananas": "banana",
        "very ripe bananas": "banana",
        "medium bananas": "banana",
        "unbaked pie crust": "flour",
        "inch unbaked pie crust": "flour",
        "prepared pie crust": "flour",
        "pinch cayenne": "cayenne pepper",
        "watercress": "spinach",
        "bunch watercress": "spinach",
        "trimmed watercress": "spinach",
        "arugula": "spinach",
        "bunch arugula": "spinach",
        "orange zest strips": "orange",
        "inch orange zest": "orange",
        "orange zest": "orange",
        "jicama": "turnip",
        "julienne jicama": "turnip",
        "peeled jicama": "turnip",
        "cup jicama": "turnip",
        "sliced bread": "bread",
        "sliced white bread": "bread",
        "pieces sliced bread": "bread",
        "white bread": "bread",
        "ciabatta": "bread",
        "whole ciabatta": "bread",
        "ciabatta bread": "bread",
        "hulled strawberries": "strawberries",
        "dozen strawberries": "strawberries",
        "rolled oats": "oatmeal",
        "extra rolled oats": "oatmeal",
        "old-fashioned oats": "oatmeal",
        "quick oats": "oatmeal",
        "daing": "fish",
        "dried fish": "fish",
        "flaked dried fish": "fish",
        "deboned fish": "fish",
        "cream of chicken soup": "cream of mushroom soup",
        "can cream of chicken soup": "cream of mushroom soup",
        "oz can cream of chicken soup": "cream of mushroom soup",
        "can water": "water",
        # Batch 30 - More ingredient mappings
        "carton less-sodium beef broth": "beef broth",
        "oz carton less-sodium beef broth": "beef broth",
        "can fat-free less-sodium chicken broth": "chicken broth",
        "oz can fat-free chicken broth": "chicken broth",
        "oz can refrigerated pizza dough": "bread",
        "can refrigerated pizza dough": "bread",
        "oz package frozen spinach": "spinach",
        "package frozen spinach": "spinach",
        "bags spinach": "spinach",
        "oz bags spinach": "spinach",
        "oz package frozen broccoli": "broccoli",
        "package frozen broccoli": "broccoli",
        "oven-roasted turkey": "turkey",
        "slices oven-roasted turkey": "turkey",
        "deli-sliced turkey": "turkey",
        "green cardamom pod": "green cardamom",
        "black cardamom pod": "black cardamom",
        "kasoori methi": "oregano",
        "tbsp kasoori methi": "oregano",
        "chili crisp": "chili sauce",
        "tbsp chili crisp": "chili sauce",
        "refrigerated tortellini": "pasta",
        "oz package refrigerated tortellini": "pasta",
        "package refrigerated tortellini": "pasta",
        "deveined peeled shrimp": "shrimp",
        "lb deveined peeled shrimp": "shrimp",
        "oz package frozen okra": "okra",
        "package frozen okra": "okra",
        "frozen whole okra": "okra",
        "baby okra": "okra",
        "fresh peaches": "peach",
        "cup fresh peaches": "peach",
        "peeled peaches": "peach",
        "rum or apple juice": "apple juice",
        "cup rum": "wine",
        "inch piece ginger": "ginger",
        "inch slice ginger": "ginger",
        "inch ginger": "ginger",
        "premium tuna": "tuna",
        "oz can premium tuna": "tuna",
        "can premium tuna": "tuna",
        "canned tuna": "tuna",
        "lb boneless leg of lamb": "lamb",
        "boneless leg lamb": "lamb",
        "lb-boneless leg of lamb": "lamb",
        "pound whole ham": "ham",
        "lb whole ham": "ham",
        "to-pound whole ham": "ham",
        # Batch 31 - More OCR artifact fixes and pattern matching
        "granny smith apples": "apple",
        "large granny smith apples": "apple",
        "medium granny smith apples": "apple",
        "cottage cheese with chive": "cottage cheese",
        "cottage cheese with chives": "cottage cheese",
        "cream of tarter": "cream of tartar",
        "cream of tater": "cream of tartar",
        "sq chocolate": "chocolate",
        "sq. chocolate": "chocolate",
        "squares chocolate": "chocolate",
        "coarsely chopped nuts": "nuts",
        "finely chopped nuts": "nuts",
        "chopped nuts": "nuts",
        "egg separated": "egg",
        "eggs separated": "egg",
        "separated egg": "egg",
        "large eggs separated": "egg",
        "egg yolk beaten": "egg yolk",
        "large egg separated": "egg",
        "mashed pumpkin": "pumpkin",
        "mashed pumpkin or squash": "pumpkin",
        "prepared pancake batter": "pancake mix",
        "cups prepared pancake batter": "pancake mix",
        "large teaspoons": "tsp",
        "large teaspoons of": "tsp",
        "heaping teaspoons": "tsp",
        "heaping teaspoonsful": "tsp",
        "store-bought piecrust": "pastry",
        "inch store-bought piecrust": "pastry",
        "bottle sparkling apple juice": "apple juice",
        "bottles sparkling apple juice": "apple juice",
        "sparkling apple juice": "apple juice",
        "package brownie mix": "brownie mix",
        "packages cream cheese": "cream cheese",
        "package cream cheese": "cream cheese",
        "packages of cream cheese": "cream cheese",
        "slices dried beef": "dried beef",
        "inch cucumber": "cucumber",
        "inch slice beetroot": "beets",
        "tbsp bouillon paste": "bouillon",
        "bouillon paste": "bouillon",
        "chicken bouillon paste": "chicken bouillon",
        "beef bouillon paste": "beef bouillon",
        "flaked dried fish": "fish",
        "dried fish": "fish",
        "seasonings of choice": "salt",
        "omelet fillings of choice": "egg",
        "fillings of choice": "egg",
        "squares of toast": "bread",
        "slices of toast": "bread",
        "toast": "bread",
        "tureen of pate-de-foie-gras": "liver",
        "pate-de-foie-gras": "liver",
        "tbsp ful of tarragon vinegar": "vinegar",
        "tarragon vinegar": "vinegar",
        "tsp ful of anchovy sauce": "anchovy paste",
        "anchovy sauce": "anchovy paste",
        "tbsp ful of chopped gherkin": "pickle",
        "chopped gherkin": "pickle",
        "gherkin": "pickle",
        "lemon juice or vinegar": "lemon juice",
        "juice or vinegar": "lemon juice",
        "milk or cider": "milk",
        "cup milk or cider": "milk",
        "additional oil and butter": "butter",
        "oil and butter": "butter",
        "for deep frying oil": "vegetable oil",
        "deep frying oil": "vegetable oil",
        "for frying oil": "vegetable oil",
        "frying oil": "vegetable oil",
        "hot roll mix": "bread",
        "pkg hot roll mix": "bread",
        "package hot roll mix": "bread",
        "large pkg hot roll mix": "bread",
        "crisp molasses cookies": "cookies",
        "molasses cookies": "cookies",
        "grated rind of lemon": "lemon zest",
        "grated peel of lemon": "lemon zest",
        "grated rind of 1 lemon": "lemon zest",
        "grated peel of 1 lemon": "lemon zest",
        "juice of a lemon": "lemon juice",
        "juice of lemon": "lemon juice",
        "juice of 1 lemon": "lemon juice",
        # Batch 32 - More OCR and historical patterns
        "entire wheat flour": "whole wheat flour",
        "entire-wheat flour": "whole wheat flour",
        "whole-wheat flour": "whole wheat flour",
        "graham flour": "whole wheat flour",
        "boiling milk": "milk",
        "boiling water": "water",
        "scalded milk": "milk",
        "warm milk": "milk",
        "cold milk": "milk",
        "cold water": "water",
        "warm water": "water",
        "lukewarm water": "water",
        "cold boiled ham": "ham",
        "boiled ham": "ham",
        "very ripe bananas": "banana",
        "ripe bananas": "banana",
        "overripe bananas": "banana",
        "spoons flour": "flour",
        "compressed yeast": "yeast",
        "cake yeast": "yeast",
        "can biscuits": "biscuit mix",
        "refrigerated biscuits": "biscuit mix",
        "slices of bread": "bread",
        "crusts of bread": "bread",
        # Batch 33 - More fixes for remaining patterns
        "chicken leg thighs": "chicken thigh",
        "leg thighs": "chicken thigh",
        "cream of mushroom soup": "cream of mushroom soup",
        "cream of chicken soup": "cream of chicken soup",
        "can cream of mushroom soup": "cream of mushroom soup",
        "can cream of chicken soup": "cream of chicken soup",
        "oz can cream of mushroom soup": "cream of mushroom soup",
        "oz can cream of chicken soup": "cream of chicken soup",
        "arrowroot": "cornstarch",
        "arrowroot or cornstarch": "cornstarch",
        "cornstarch or arrowroot": "cornstarch",
        "broken nuts": "nuts",
        "cut nuts": "nuts",
        "mashed squash": "squash",
        "mashed pumpkin or squash": "pumpkin",
        "pumpkin or squash": "pumpkin",
        "gumdrops": "candy",
        "cut-up gumdrops": "candy",
        "coldboiled ham": "ham",
        "cold boiled ham": "ham",
        "baking-powder": "baking powder",
        "baiking-powder": "baking powder",
        "cloves or allspice": "cloves",
        "nutmeg and cloves": "nutmeg",
        "nutmeg or cloves": "nutmeg",
        "flour to make": "flour",
        "flour to make a": "flour",
        "soft batter": "flour",
        "store-bought piecrust": "pastry",
        "flaked dried fish": "fish",
        "dried fish (daing)": "fish",
        "pate-de-foie-gras": "liver",
        "rye flour": "flour",
        "tsp ful": "tsp",
        "tbsp ful": "tbsp",
        "cup ful": "cup",
        # Batch 34 - More OCR artifacts
        "ofbread": "bread",
        "offlour": "flour",
        "ofsugar": "sugar",
        "ofmilk": "milk",
        "ofwater": "water",
        "ofbutter": "butter",
        "ofsalt": "salt",
        "ofegg": "egg",
        "coldboiled": "boiled",
        "finely chopped coldboiled ham": "ham",
        "coldboiled ham": "ham",
        "cup cold boiled": "ham",
        "cold boiled": "ham",
        "inch store-bought": "pastry",
        "9-inch store-bought": "pastry",
        "seasonings choice": "salt",
        "seasoning of choice": "salt",
        "tureen of": "liver",
        # Batch 35 - More fixes
        "prepared hummus": "hummus",
        "container prepared hummus": "hummus",
        "roma tomatoes": "tomatoes",
        "medium roma tomatoes": "tomatoes",
        "crumbled feta cheese": "feta cheese",
        "container crumbled feta cheese": "feta cheese",
        "oz container": "oz",
        "chunk of parmesan": "parmesan",
        "parmesan, shaved": "parmesan",
        "parsley, basil, dill": "parsley",
        "cup of parsley": "parsley",
        "baking soda": "baking soda",
        "baking powder pinch": "baking powder",
    }

    # Check for exact match first
    if item in synonyms:
        item = synonyms[item]
    else:
        # Try partial matches
        for old, new in synonyms.items():
            if old in item:
                item = new
                break

    return item.strip()


# =============================================================================
# EQUIPMENT FILTER - Items that are not food
# =============================================================================

EQUIPMENT_WORDS = {
    # Kitchen equipment
    "mixing-bowl", "mixing bowl", "bowl", "mixing-spoon", "spoon", "fork",
    "dover beater", "beater", "double-boiler", "double boiler", "saucepan",
    "flour sifter", "sifter", "vegetable-knife", "knife", "grater",
    "egg mixing-bowl", "butter mixing-bowl", "ugar mixing-spoon",
    "milk dover beater", "milk double-boiler",
    # Batch 16: More equipment
    "bamboo sushi mat", "sushi mat", "rolling mat", "bamboo mat",
    "plastic wrap", "parchment paper", "aluminum foil", "wax paper",
    "skewer", "skewers", "toothpick", "toothpicks",
    "specialist kit",
    # Meta instructions
    "for the cake:", "for the frosting:", "for the filling:",
    "mrs.wilson's cookbook", "-inch", "-sized",
    # Non-food items
    "each", "s", "d 227", "egg .03",
    # Batch 1 - Equipment from historical cookbooks
    "frying-pan", "frying pan", "pancake-turner", "pancake turner",
    "wooden cake-spoon", "cake-spoon", "small saucepan", "cake-pan",
    "bread-board", "rolling-pin", "cookie-cutter", "muffin pan",
    "bread-boardmteaspoon", "rouing-pin", "cake-pan (with tube)",
    # Batch 1 - Garbage/index entries
    "index to armed forces", "armed forces recipe service",
    "recipe service", "tm 10-412", "appetizers.",
    "general principles", "standard recipe", "recipe conversion",
    "guide for hot-roll", "hot-roll makeup",
}

def is_equipment(item):
    """Check if an item is equipment/non-food rather than an ingredient."""
    item_lower = item.lower().strip()

    # Direct matches
    if item_lower in EQUIPMENT_WORDS:
        return True

    # Partial matches for equipment patterns
    equipment_patterns = [
        "mixing-bowl", "mixing bowl", "double-boiler", "double boiler",
        "dover beater", "vegetable-knife", "flour sifter",
        "for the ", "cookbook", "-inch", "-sized potatoes vegetable",
        "for topping", "for serving", "for dipping", "for garnish",
        "for dusting", "(optional)", "optional",
    ]
    for pattern in equipment_patterns:
        if pattern in item_lower:
            return True

    # Very short items that are likely OCR garbage
    if len(item_lower) <= 2 and not item_lower.isdigit():
        return True

    return False


# =============================================================================
# SERVING INFERENCE - Smart defaults based on category
# =============================================================================

def infer_servings(recipe):
    """Infer serving size based on recipe characteristics."""
    # Check if we have explicit servings
    servings_yield = recipe.get("servings_yield", "")
    if servings_yield:
        parsed = parse_servings(servings_yield)
        if parsed:
            return parsed

    category = recipe.get("category", "").lower()
    title = recipe.get("title", "").lower()
    ingredients = recipe.get("ingredients", [])

    # Count key ingredients to estimate yield
    flour_cups = 0
    meat_lbs = 0
    egg_count = 0

    for ing in ingredients:
        item = ing.get("item", "").lower()
        unit = ing.get("unit", "").lower()
        try:
            qty = float(ing.get("quantity", 0) or 0)
        except:
            qty = 1

        if "flour" in item and "cup" in unit:
            flour_cups += qty
        elif any(m in item for m in ["beef", "chicken", "pork", "turkey", "lamb"]) and "lb" in unit:
            meat_lbs += qty
        elif "egg" in item and unit in ("", "each", "large"):
            egg_count += qty

    # Category-based defaults
    if category == "beverages":
        return 4
    elif category == "appetizers":
        return 8  # Appetizers usually serve more
    elif category == "desserts":
        if "cookie" in title or "bar" in title:
            return 24  # Cookies/bars make many
        elif "cake" in title:
            return 12
        elif "pie" in title:
            return 8
        elif flour_cups >= 3:
            return 16  # Large batch
        else:
            return 8
    elif category == "breads":
        if "muffin" in title:
            return 12
        elif "roll" in title or "biscuit" in title:
            return 12
        elif "loaf" in title or "bread" in title:
            return 12  # One loaf = ~12 slices
        else:
            return 8
    elif category == "breakfast":
        if "pancake" in title or "waffle" in title:
            return 4
        else:
            return 4
    elif category == "mains":
        if meat_lbs >= 2:
            return 8
        elif meat_lbs >= 1:
            return 6
        else:
            return 4
    elif category == "soups":
        return 6
    elif category == "salads":
        return 6
    elif category == "sides":
        return 6

    # Fallback based on ingredient volume
    if flour_cups >= 4:
        return 16
    elif flour_cups >= 2:
        return 8
    elif meat_lbs >= 2:
        return 8

    return 4  # Default


# =============================================================================
# NUTRITION CALCULATION
# =============================================================================

def get_nutrition_for_ingredient(ingredient):
    """Calculate nutrition for a single ingredient entry."""
    raw_item = ingredient.get("item", "")
    raw_unit = ingredient.get("unit", "")

    # Extract OCR-embedded unit prefixes from item (e.g., "c sugar" -> unit="cup", item="sugar")
    ocr_unit_prefixes = {
        "c ": "cup",
        "t ": "tsp",
        "T ": "tbsp",
        "slices ": "slice",
        "slice ": "slice",
        "ears ": "ear",
        "ear ": "ear",
        "qt. ": "quart",
        "qt ": "quart",
        "pt. ": "pint",
        "pt ": "pint",
        "oz ": "oz",
        "lb ": "lb",
        "cups ": "cup",
        "cup ": "cup",
        "tbsp ": "tbsp",
        "tsp ": "tsp",
        "tblsp. ": "tbsp",
        "tblsps. ": "tbsp",
    }
    extracted_unit = None
    for prefix, unit_name in ocr_unit_prefixes.items():
        if raw_item.lower().startswith(prefix.lower()) and not raw_unit:
            extracted_unit = unit_name
            raw_item = raw_item[len(prefix):]
            break

    item = normalize_ingredient(raw_item)
    unit = str(raw_unit).lower() if raw_unit else (extracted_unit or "")

    # Skip equipment and non-food items
    if is_equipment(item):
        return {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0, "_skipped": True}

    # Skip items where unit indicates non-countable usage (greasing, brushing, serving, etc.)
    non_countable_units = [
        "for greasing", "for brushing", "for drizzling", "as needed",
        "to serve", "for serving", "to garnish", "for garnish",
        "to sprinkle", "for dusting", "for topping", "for decorating",
        "for dipping", "optional", "to taste", "for coating"
    ]
    if any(ncu in unit for ncu in non_countable_units):
        return {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0, "_skipped": True}

    quantity = parse_quantity(ingredient.get("quantity", "1"))
    # Only normalize unit if we didn't extract one from OCR prefix
    if not extracted_unit:
        unit = normalize_unit(ingredient.get("unit", ""))

    # Handle compound units like "5-oz" or "6-inch" -> extract multiplier
    compound_match = re.match(r'^(\d+(?:\.\d+)?)-?(\w+)$', unit)
    if compound_match:
        unit_multiplier = float(compound_match.group(1))
        unit = compound_match.group(2)
        quantity = quantity * unit_multiplier

    # Handle "to taste" / "to sweeten" - minimal impact (check unit, item, and prep_note)
    to_taste_fields = [
        str(ingredient.get("unit", "")).lower(),
        str(ingredient.get("item", "")).lower(),
        str(ingredient.get("prep_note", "")).lower()
    ]
    if any("to taste" in f or "to sweeten" in f for f in to_taste_fields):
        if "salt" in item or "pepper" in item:
            return {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 150, "fiber": 0, "sugar": 0}
        return {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}

    # Handle water
    if "water" in item and item not in NUTRITION_DB:
        return {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}

    # Try exact match
    if item in NUTRITION_DB:
        db_entry = NUTRITION_DB[item]
        if unit in db_entry:
            base = db_entry[unit]
            return {k: v * quantity for k, v in base.items()}
        elif "" in db_entry:  # Unit-less items
            base = db_entry[""]
            return {k: v * quantity for k, v in base.items()}
        # Try unit conversions
        elif unit == "tbsp" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 16 for k, v in base.items()}
        elif unit == "tsp" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 48 for k, v in base.items()}
        elif unit == "tsp" and "tbsp" in db_entry:
            base = db_entry["tbsp"]
            return {k: v * quantity / 3 for k, v in base.items()}
        elif unit == "tbsp" and "tsp" in db_entry:
            base = db_entry["tsp"]
            return {k: v * quantity * 3 for k, v in base.items()}
        # Pint/quart to cup conversions
        elif unit == "pint" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 2 for k, v in base.items()}  # 1 pint = 2 cups
        elif unit == "quart" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 4 for k, v in base.items()}  # 1 quart = 4 cups
        elif unit == "gallon" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 16 for k, v in base.items()}  # 1 gallon = 16 cups
        # ML to cup conversion
        elif unit == "ml" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 237 for k, v in base.items()}  # ~237 ml per cup
        # Historical measurement conversions (Batch 14)
        elif unit == "gill" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 0.5 for k, v in base.items()}  # 1 gill = 0.5 cup (4 fl oz)
        elif unit == "drachm" and "oz" in db_entry:
            base = db_entry["oz"]
            return {k: v * quantity / 8 for k, v in base.items()}  # 1 drachm = 1/8 oz
        elif unit == "drachm" and "tbsp" in db_entry:
            base = db_entry["tbsp"]
            return {k: v * quantity / 4 for k, v in base.items()}  # 1 fluid drachm ≈ 0.25 tbsp
        elif unit == "dessertspoon" and "tsp" in db_entry:
            base = db_entry["tsp"]
            return {k: v * quantity * 2 for k, v in base.items()}  # 1 dessertspoon = 2 tsp
        elif unit == "dessertspoon" and "tbsp" in db_entry:
            base = db_entry["tbsp"]
            return {k: v * quantity * 0.67 for k, v in base.items()}  # 1 dessertspoon = 2/3 tbsp
        elif unit == "dessertspoon" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 24 for k, v in base.items()}  # 24 dessertspoons = 1 cup
        elif unit == "saltspoon" and "tsp" in db_entry:
            base = db_entry["tsp"]
            return {k: v * quantity / 4 for k, v in base.items()}  # 1 saltspoon = 1/4 tsp
        elif unit == "saltspoon" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 192 for k, v in base.items()}  # 192 saltspoons = 1 cup
        # Batch 30: Dash and pinch conversions (for spices)
        elif unit == "dash" and "tsp" in db_entry:
            base = db_entry["tsp"]
            return {k: v * quantity / 8 for k, v in base.items()}  # 1 dash ≈ 1/8 tsp
        elif unit == "pinch" and "tsp" in db_entry:
            base = db_entry["tsp"]
            return {k: v * quantity / 16 for k, v in base.items()}  # 1 pinch ≈ 1/16 tsp
        elif unit == "wineglass" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 0.5 for k, v in base.items()}  # 1 wineglass ≈ 0.5 cup (4 fl oz)
        elif unit == "teacup" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 0.75 for k, v in base.items()}  # 1 teacup ≈ 0.75 cup (6 fl oz)
        elif unit == "coffeecup" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity for k, v in base.items()}  # 1 coffeecup ≈ 1 cup
        elif unit == "jigger" and "tbsp" in db_entry:
            base = db_entry["tbsp"]
            return {k: v * quantity * 3 for k, v in base.items()}  # 1 jigger = 3 tbsp (1.5 oz)
        elif unit == "jigger" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 5.33 for k, v in base.items()}  # 1 jigger ≈ 3/16 cup
        elif unit == "peck" and "quart" in db_entry:
            base = db_entry["quart"]
            return {k: v * quantity * 8 for k, v in base.items()}  # 1 peck = 8 quarts
        elif unit == "peck" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 32 for k, v in base.items()}  # 1 peck = 32 cups
        elif unit == "bushel" and "quart" in db_entry:
            base = db_entry["quart"]
            return {k: v * quantity * 32 for k, v in base.items()}  # 1 bushel = 32 quarts
        elif unit == "bushel" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity * 128 for k, v in base.items()}  # 1 bushel = 128 cups
        # Batch 15: Weight to volume conversions for common baking items
        elif unit == "lb" and "cup" in db_entry:
            # Common conversions: flour ~4 cups/lb, sugar ~2.25 cups/lb, butter ~2 cups/lb
            if "flour" in item:
                base = db_entry["cup"]
                return {k: v * quantity * 4 for k, v in base.items()}  # 1 lb flour ≈ 4 cups
            elif "sugar" in item:
                base = db_entry["cup"]
                return {k: v * quantity * 2.25 for k, v in base.items()}  # 1 lb sugar ≈ 2.25 cups
            else:
                base = db_entry["cup"]
                return {k: v * quantity * 2 for k, v in base.items()}  # Generic: 1 lb ≈ 2 cups
        elif unit == "oz" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 8 for k, v in base.items()}  # 8 oz = 1 cup (volume)
        elif unit == "oz" and "tbsp" in db_entry:
            base = db_entry["tbsp"]
            return {k: v * quantity * 2 for k, v in base.items()}  # 1 oz = 2 tbsp
        elif unit == "tsp" and "cup" in db_entry:
            base = db_entry["cup"]
            return {k: v * quantity / 48 for k, v in base.items()}  # 48 tsp = 1 cup
        # Empty unit fallback - use first available unit as reasonable default
        elif unit == "" and db_entry:
            # Prefer common units in order
            for preferred in ["tbsp", "tsp", "cup", "oz", "each", ""]:
                if preferred in db_entry:
                    base = db_entry[preferred]
                    return {k: v * quantity for k, v in base.items()}

    # Try without unit for counted items
    if item in NUTRITION_DB and "" in NUTRITION_DB[item]:
        base = NUTRITION_DB[item][""]
        return {k: v * quantity for k, v in base.items()}

    return None


def parse_servings(servings_str, default=4):
    """Parse servings from yield string. Default to 4 if not specified."""
    if not servings_str:
        return default

    servings_str = str(servings_str).lower()

    # Handle range like "6-8 servings" - take midpoint
    range_match = re.search(r'(\d+)\s*[-–to]+\s*(\d+)', servings_str)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        return (low + high) // 2

    # Handle simple number
    match = re.search(r'(\d+)', servings_str)
    if match:
        return int(match.group(1))

    # Handle word-based
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twelve": 12, "dozen": 12, "several": 4
    }
    for word, num in word_map.items():
        if word in servings_str:
            return num

    return default


def calculate_recipe_nutrition(recipe, default_servings=4):
    """Calculate complete nutrition for a recipe."""
    ingredients = recipe.get("ingredients", [])

    # Use smart serving inference
    servings = infer_servings(recipe)
    serving_inferred = not recipe.get("servings_yield")

    total = {"cal": 0, "fat": 0, "carbs": 0, "protein": 0, "sodium": 0, "fiber": 0, "sugar": 0}
    missing = []
    skipped_equipment = 0
    actual_ingredients = 0

    for ing in ingredients:
        nutr = get_nutrition_for_ingredient(ing)
        if nutr:
            # Check if it was skipped equipment
            if nutr.get("_skipped"):
                skipped_equipment += 1
            else:
                actual_ingredients += 1
                for key in total:
                    total[key] += nutr.get(key, 0)
        else:
            # Check if it's equipment before adding to missing
            item = normalize_ingredient(ing.get("item", ""))
            if not is_equipment(item):
                actual_ingredients += 1
                ing_str = f"{ing.get('quantity', '')} {ing.get('unit', '')} {ing.get('item', '')}".strip()
                if ing_str:
                    missing.append(ing_str)

    # Calculate per-serving values
    per_serving = {
        "calories": round(total["cal"] / servings),
        "fat_g": round(total["fat"] / servings, 1),
        "carbs_g": round(total["carbs"] / servings, 1),
        "protein_g": round(total["protein"] / servings, 1),
        "sodium_mg": round(total["sodium"] / servings),
        "fiber_g": round(total["fiber"] / servings, 1),
        "sugar_g": round(total["sugar"] / servings, 1)
    }

    # Determine status (based on actual food ingredients, not equipment)
    total_food_ingredients = actual_ingredients
    missing_count = len(missing)

    if missing_count == 0:
        status = "complete"
    elif missing_count <= 2 or (total_food_ingredients > 0 and missing_count / total_food_ingredients <= 0.2):
        status = "partial"
    else:
        status = "insufficient_data"

    assumptions = [f"Calculated for {servings} servings"]
    if serving_inferred:
        category = recipe.get("category", "unknown")
        assumptions.append(f"Serving size inferred from {category} category")

    return {
        "status": status,
        "per_serving": per_serving,
        "missing_inputs": missing[:10] if len(missing) > 10 else missing,  # Limit to 10
        "assumptions": assumptions
    }


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main():
    """Main entry point with CLI argument handling."""
    parser = argparse.ArgumentParser(
        description='Elite nutrition estimation for family recipes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/estimate_nutrition_elite.py --dry-run
  python scripts/estimate_nutrition_elite.py --verbose --force
  python scripts/estimate_nutrition_elite.py --recipe-id apple-pie
  python scripts/estimate_nutrition_elite.py --collection grandma-baker
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without saving changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output for each recipe')
    parser.add_argument('--recipe-id', type=str,
                        help='Process only this recipe ID')
    parser.add_argument('--force', action='store_true',
                        help='Re-estimate recipes that already have nutrition')
    parser.add_argument('--collection', type=str,
                        help='Filter by collection ID')
    args = parser.parse_args()

    # Find recipes file
    script_dir = Path(__file__).parent
    master_path = script_dir.parent / 'data' / 'recipes_master.json'

    # Also support sharded structure
    if not master_path.exists():
        shard_files = sorted(glob.glob(str(script_dir.parent / 'data' / 'recipes-*.json')))
        if shard_files:
            print(f"Using sharded structure: {len(shard_files)} files")
        else:
            print(f"ERROR: Cannot find {master_path} or recipe shards")
            return 1
    else:
        shard_files = None

    # Process single master file or shards
    if shard_files:
        files_to_process = shard_files
    else:
        files_to_process = [str(master_path)]

    total_processed = 0
    total_skipped = 0
    stats = {'complete': 0, 'partial': 0, 'insufficient_data': 0}
    all_missing = []

    for file_path in files_to_process:
        print(f"Loading: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        recipes = data.get('recipes', [])
        print(f"Found {len(recipes)} recipes")

        for recipe in recipes:
            rid = recipe.get('id', 'unknown')

            # Filter by collection
            if args.collection and recipe.get('collection') != args.collection:
                continue

            # Filter by recipe ID
            if args.recipe_id and rid != args.recipe_id:
                continue

            # Skip tips category
            if recipe.get('category') == 'tips':
                continue

            # Skip flagged content
            if recipe.get('flagged_for_review'):
                continue

            # Skip if already has nutrition (unless force)
            existing = recipe.get('nutrition', {})
            if not args.force and existing.get('status') in ['complete', 'partial']:
                total_skipped += 1
                continue

            # Calculate nutrition
            nutrition = calculate_recipe_nutrition(recipe, default_servings=4)
            status = nutrition.get('status', 'insufficient_data')
            stats[status] = stats.get(status, 0) + 1

            # Collect missing ingredients for gap analysis
            missing = nutrition.get('missing_inputs', [])
            all_missing.extend(missing)

            if args.verbose:
                per_serving = nutrition.get('per_serving', {})
                cal = per_serving.get('calories', 'N/A')
                print(f"  {rid}: {status} ({cal} cal/serving)")
                if missing:
                    print(f"    Missing: {', '.join(missing[:5])}")

            # Update recipe
            if not args.dry_run:
                recipe['nutrition'] = nutrition
            total_processed += 1

        # Save if not dry run
        if not args.dry_run and total_processed > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    # Summary
    print()
    print("=" * 60)
    print("NUTRITION ESTIMATION SUMMARY")
    print("=" * 60)
    print(f"Processed: {total_processed}")
    print(f"Skipped (already have nutrition): {total_skipped}")
    print()
    print(f"Complete (100% matched):     {stats.get('complete', 0)}")
    print(f"Partial (some missing):      {stats.get('partial', 0)}")
    print(f"Insufficient (<50% matched): {stats.get('insufficient_data', 0)}")

    # Gap analysis - most common missing ingredients
    if all_missing:
        print()
        print("Top 20 missing ingredients (add to NUTRITION_DB for better coverage):")
        missing_counts = Counter(all_missing)
        for item, count in missing_counts.most_common(20):
            print(f"  {count:>4}x  {item}")

    if args.dry_run:
        print()
        print("DRY RUN - no changes saved")

    return 0


if __name__ == "__main__":
    sys.exit(main())
