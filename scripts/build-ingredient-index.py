#!/usr/bin/env python3
"""
Build Ingredient Index for Grandma's Kitchen Recipe Archive

Generates data/ingredient-index.json from recipes_master.json.
This pre-compiled index enables fast ingredient-based recipe search.

Features:
- Normalized ingredient names (lowercase, trimmed)
- Plural/singular normalization
- Synonym support (hamburger = ground beef)
- Recipe ID references for each ingredient
- Ingredient frequency counts

Usage:
    python scripts/build-ingredient-index.py

Output:
    data/ingredient-index.json (~50KB estimated)
"""

import json
import re
import os
import urllib.request
import urllib.error
import signal
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

# Timeout for remote collection fetches (can be overridden via REMOTE_TIMEOUT env var)
REMOTE_TIMEOUT = int(os.environ.get('REMOTE_TIMEOUT', '60'))


class TimeoutError(Exception):
    """Raised when a remote fetch exceeds the timeout."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Remote fetch timed out")

# Remote collections to fetch (in addition to local recipes)
REMOTE_COLLECTIONS = [
    {
        "id": "mommom-baker",
        "name": "MomMom Baker",
        "urls": [
            "https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json",
        ]
    },
    {
        "id": "granny-hudson",
        "name": "Granny Hudson",
        "urls": [
            "https://jsschrstrcks1.github.io/Grannysrecipes/data/recipes.json",
            "https://jsschrstrcks1.github.io/Grannysrecipes/granny/recipes_master.json",
            "https://raw.githubusercontent.com/jsschrstrcks1/Grannysrecipes/main/granny/recipes_master.json",
        ]
    },
    {
        "id": "all",
        "name": "Other Recipes",
        "urls": [
            "https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json",
            "https://jsschrstrcks1.github.io/Allrecipes/all/recipes_master.json",
            "https://raw.githubusercontent.com/jsschrstrcks1/Allrecipes/main/all/recipes_master.json",
        ]
    },
]

# Common ingredient synonyms (bidirectional)
SYNONYMS = {
    # Meats
    "hamburger": "ground beef",
    "ground beef": "hamburger",
    "hamburger meat": "ground beef",
    "beef mince": "ground beef",
    "mince": "ground beef",
    "bacon bits": "bacon",
    "pork sausage": "sausage",
    "italian sausage": "sausage",
    "breakfast sausage": "sausage",
    "chicken breast": "chicken",
    "chicken thigh": "chicken",
    "chicken thighs": "chicken",
    "chicken breasts": "chicken",

    # Dairy - Butter
    "butter": "butter",
    "margarine": "butter",
    "oleo": "butter",
    "butter or margarine": "butter",
    "margarine or butter": "butter",
    "butter or oleo": "butter",
    "oleo or butter": "butter",
    "melted butter or margarine": "butter",
    "melted margarine or butter": "butter",
    "softened butter or margarine": "butter",
    "shortening, margarine, or butter": "butter",
    "melted butter": "butter",
    "softened butter": "butter",
    "cold butter": "butter",
    "firm butter or margarine": "butter",
    "sweet butter": "butter",
    "unsalted butter": "butter",
    "salted butter": "butter",
    "stick butter": "butter",
    "soft butter": "butter",
    "room temperature butter": "butter",
    "cubed butter": "butter",

    # Dairy - Cream
    "heavy cream": "cream",
    "whipping cream": "cream",
    "heavy whipping cream": "cream",
    "heavy or whipping cream": "cream",
    "light cream": "cream",
    "half and half": "cream",
    "half & half": "cream",
    "half-and-half": "cream",
    "whipping cream or milk": "cream",
    "sour cream": "sour cream",
    "dairy sour cream": "sour cream",
    "cream cheese": "cream cheese",
    "soft cream cheese": "cream cheese",

    # Dairy - Cheese
    "cheddar": "cheddar cheese",
    "cheddar cheese": "cheddar",
    "shredded cheddar cheese": "cheddar cheese",
    "sharp cheddar cheese": "cheddar cheese",
    "cubed or shredded cheese": "cheese",
    "american cheese": "cheese",
    "shredded american cheese": "cheese",
    "velveeta": "cheese",
    "velveeta cheese": "cheese",
    "grated cheese": "cheese",
    "parmesan": "parmesan cheese",
    "parmesan cheese": "parmesan",
    "grated parmesan cheese": "parmesan cheese",
    "parmigiano": "parmesan cheese",
    "mozzarella": "mozzarella cheese",
    "mozzarella cheese": "mozzarella",
    "shredded mozzarella cheese": "mozzarella cheese",
    "grated mozzarella": "mozzarella cheese",
    "swiss cheese": "swiss cheese",
    "shredded swiss cheese": "swiss cheese",
    "shredded jarlsberg or swiss cheese": "swiss cheese",
    "shredded edam cheese": "cheese",
    "ricotta cheese": "ricotta",
    "ricotta": "ricotta cheese",
    "cottage cheese": "cottage cheese",

    # Dairy - Milk (all types normalize to "milk")
    "dry milk": "milk",
    "nonfat dry milk": "milk",
    "nonfat dry milk powder": "milk",
    "non-fat dry milk": "milk",
    "warm milk": "milk",
    "nonfat milk": "milk",
    "non-fat milk": "milk",
    "1% milk": "milk",
    "1% low-fat milk": "milk",
    "2% milk": "milk",
    "low-fat milk": "milk",
    "reduced fat milk": "milk",
    "reduced-fat milk": "milk",
    "fat-free milk": "milk",
    "fat free milk": "milk",
    "lukewarm milk": "milk",
    "scalded milk": "milk",
    "cold milk": "milk",
    "room temperature milk": "milk",

    # Eggs
    "egg": "eggs",
    "eggs": "egg",
    "large egg": "eggs",
    "large eggs": "eggs",
    "beaten egg": "eggs",
    "beaten eggs": "eggs",
    "slightly beaten eggs": "eggs",
    "lightly beaten eggs": "eggs",
    "hard-cooked eggs": "eggs",
    "hard-boiled eggs": "eggs",
    "hard-boiled egg": "eggs",
    "hard boiled eggs": "eggs",
    "egg yolk": "egg yolks",
    "egg yolks": "egg yolk",
    "egg white": "egg whites",
    "egg whites": "egg white",

    # Flours and starches
    "all-purpose flour": "flour",
    "all purpose flour": "flour",
    "ap flour": "flour",
    "plain flour": "flour",
    "white flour": "flour",
    "sifted flour": "flour",
    "unsifted flour": "flour",
    "presifted flour": "flour",
    "enriched flour": "flour",
    "sifted cake flour": "cake flour",
    "pillsbury's best all-purpose flour": "flour",
    "warm pillsbury's best all-purpose flour": "flour",
    "self-rising flour": "self-rising flour",
    "self rising flour": "self-rising flour",
    "self-raising flour": "self-rising flour",
    "bread flour": "flour",
    "cake flour": "flour",
    "cake flour or all-purpose flour": "flour",
    "cake flour, sifted": "flour",
    "whole wheat flour": "whole wheat flour",
    "whole-wheat flour": "whole wheat flour",
    "whole wheat pastry flour": "whole wheat flour",
    "rye flour": "rye flour",
    "cornstarch": "corn starch",
    "corn starch": "cornstarch",
    "argo or kingsford's corn starch": "cornstarch",
    "unsifted cornstarch": "cornstarch",
    # Flour tortillas
    "flour tortillas": "tortillas",
    "flour tortillas , warmed": "tortillas",
    "corn tortillas": "tortillas",
    "tortilla": "tortillas",

    # Sugars
    "granulated sugar": "sugar",
    "white sugar": "sugar",
    "granulated white sugar": "sugar",
    "fine sugar": "sugar",
    "superfine sugar": "sugar",
    "caster sugar": "sugar",
    "castor sugar": "sugar",
    "regular sugar": "sugar",
    "table sugar": "sugar",
    "powdered sugar": "confectioners sugar",
    "confectioners sugar": "powdered sugar",
    "confectioners' sugar": "powdered sugar",
    "icing sugar": "powdered sugar",
    "confectioner's sugar": "powdered sugar",
    "sifted powdered sugar": "powdered sugar",
    "unsifted powdered sugar": "powdered sugar",
    "10x sugar": "powdered sugar",
    "light brown sugar": "brown sugar",
    "dark brown sugar": "brown sugar",
    "packed brown sugar": "brown sugar",
    "firmly packed brown sugar": "brown sugar",
    "packed light brown sugar": "brown sugar",
    "packed dark brown sugar": "brown sugar",
    "golden brown sugar": "brown sugar",

    # Oils
    "vegetable oil": "oil",
    "canola oil": "oil",
    "cooking oil": "oil",
    "salad oil": "oil",
    "corn oil": "oil",
    "shortening or cooking oil": "oil",
    "olive oil or vegetable oil": "oil",
    "vegetable or olive oil": "oil",
    "olive or salad oil": "oil",
    "corn oil or clarified butter": "oil",
    "mazola right blend canola & corn oil": "oil",
    "olive oil": "oil",
    "evoo": "olive oil",
    "extra virgin olive oil": "olive oil",
    "shortening": "shortening",
    "vegetable shortening": "shortening",
    "solid shortening": "shortening",
    "crisco": "shortening",

    # Baking
    "baking soda": "baking soda",
    "bicarbonate of soda": "baking soda",
    "bicarb": "baking soda",
    "baking powder": "baking powder",

    # Tomatoes
    "tomato": "tomatoes",
    "tomatoes": "tomato",
    "cherry tomatoes": "tomatoes",
    "grape tomatoes": "tomatoes",
    "roma tomatoes": "tomatoes",
    "plum tomatoes": "tomatoes",
    "canned tomatoes": "tomatoes",
    "diced tomatoes": "tomatoes",
    "crushed tomatoes": "tomatoes",
    "tomato sauce": "tomato sauce",
    "tomato paste": "tomato paste",

    # Onions
    "onion": "onions",
    "onions": "onion",
    "yellow onion": "onions",
    "yellow onions": "onions",
    "white onion": "onions",
    "white onions": "onions",
    "red onion": "onions",
    "red onions": "onions",
    "sweet onion": "onions",
    "vidalia onion": "onions",
    "spanish onion": "onions",
    "small onion": "onions",
    "medium onion": "onions",
    "large onion": "onions",
    "chopped onion": "onions",
    "chopped onions": "onions",
    "diced onion": "onions",
    "minced onion": "onions",
    "sliced onion": "onions",
    "finely chopped onion": "onions",
    "finely minced onion": "onions",
    "onion flakes": "onions",
    "dried onion": "onions",
    "dried minced onion": "onions",
    "instant minced onion": "onions",
    "onion powder": "onion powder",
    "onion salt": "onion salt",
    "green onion": "green onions",
    "green onions": "green onion",
    "scallion": "green onions",
    "scallions": "green onions",
    "spring onion": "green onions",
    "spring onions": "green onions",
    "chopped green onion": "green onions",
    "chopped green onions": "green onions",
    "sliced green onions": "green onions",
    "finely sliced green onions": "green onions",
    "thinly green onions": "green onions",
    "green onions, thinly": "green onions",
    "thinly sliced green onions": "green onions",

    # Garlic
    "garlic": "garlic",
    "garlic clove": "garlic",
    "garlic cloves": "garlic",
    "clove garlic": "garlic",
    "cloves garlic": "garlic",
    "large cloves garlic": "garlic",
    "minced garlic": "garlic",
    "crushed garlic": "garlic",
    "chopped garlic": "garlic",
    "pressed garlic": "garlic",
    "fresh garlic": "garlic",
    "granulated garlic": "garlic powder",
    "garlic powder": "garlic powder",
    "garlic salt": "garlic salt",

    # Peppers
    "bell pepper": "bell peppers",
    "bell peppers": "bell pepper",
    "green pepper": "bell peppers",
    "green peppers": "bell peppers",
    "big green peppers": "bell peppers",
    "large green pepper": "bell peppers",
    "chopped green pepper": "bell peppers",
    "red bell pepper": "bell peppers",
    "sweet pepper": "bell peppers",

    # Beans
    "kidney beans": "beans",
    "black beans": "beans",
    "pinto beans": "beans",
    "navy beans": "beans",
    "white beans": "beans",
    "cannellini beans": "beans",
    "great northern beans": "beans",

    # Broths/Stocks
    "chicken stock": "chicken broth",
    "chicken broth": "chicken stock",
    "chicken bouillon cubes": "chicken broth",
    "chicken bouillon cube": "chicken broth",
    "reduced-sodium chicken broth": "chicken broth",
    "low-sodium chicken broth": "chicken broth",
    "fat-free, less-sodium chicken broth": "chicken broth",
    "fat-free chicken broth": "chicken broth",
    "beef stock": "beef broth",
    "beef broth": "beef stock",
    "beef bouillon cube": "beef broth",
    "beef bouillon cubes": "beef broth",
    "instant beef broth": "beef broth",
    "reduced-sodium beef broth": "beef broth",
    "low-sodium beef broth": "beef broth",
    "beef bouillon granules": "beef broth",
    "bouillon cube": "broth",
    "bouillon cubes": "broth",
    "vegetable stock": "vegetable broth",
    "vegetable broth": "vegetable stock",

    # Water
    "boiling water": "water",
    "lukewarm water": "water",
    "ice water": "water",
    "cold water": "water",
    "warm water": "water",
    "hot water": "water",
    "room temperature water": "water",

    # Milk
    "whole milk": "milk",
    "2% milk": "milk",
    "skim milk": "milk",
    "low-fat milk": "milk",
    "evaporated milk": "evaporated milk",
    "condensed milk": "sweetened condensed milk",
    "sweetened condensed milk": "condensed milk",

    # Salt
    "salt": "salt",
    "table salt": "salt",
    "kosher salt": "salt",
    "coarse salt": "salt",
    "coarse (kosher) salt": "salt",
    "sea salt": "salt",
    "fine salt": "salt",
    "iodized salt": "salt",
    "salt to taste": "salt",
    "seasoned salt": "salt",
    "salt and pepper": "salt",
    "salt and black pepper": "salt",
    "salt and white pepper": "salt",

    # Pepper
    "pepper": "black pepper",
    "black pepper": "pepper",
    "ground pepper": "black pepper",
    "ground black pepper": "black pepper",
    "freshly ground pepper": "black pepper",
    "freshly ground black pepper": "black pepper",
    "fresh cracked black pepper": "black pepper",
    "cracked pepper": "black pepper",
    "cracked black pepper": "black pepper",
    "freshly black pepper": "black pepper",
    "freshly black pepper, divided": "black pepper",
    "kosher salt and freshly pepper": "black pepper",
    "kosher salt and black pepper": "black pepper",
    "white pepper": "white pepper",
    "ground white pepper": "white pepper",
    "cayenne pepper": "cayenne",
    "cayenne": "cayenne pepper",
    "red pepper": "cayenne",
    "ground red pepper": "cayenne",
    "crushed red pepper": "red pepper flakes",
    "red pepper flakes": "crushed red pepper",
    "crushed red pepper flakes": "red pepper flakes",

    # Misc
    "vanilla": "vanilla extract",
    "vanilla extract": "vanilla",
    "pure vanilla": "vanilla extract",
    "pure vanilla extract": "vanilla extract",
    "lemon juice": "lemon juice",
    "fresh lemon juice": "lemon juice",
    "bottled lemon juice": "lemon juice",
    "lime juice": "lime juice",
    "fresh lime juice": "lime juice",
    "worcestershire": "worcestershire sauce",
    "worcestershire sauce": "worcestershire",
    "soy sauce": "soy sauce",
    "shoyu": "soy sauce",
    "tamari": "soy sauce",
    "low-sodium soy sauce": "soy sauce",
    "reduced-sodium soy sauce": "soy sauce",
    "light soy sauce": "soy sauce",
    "dark soy sauce": "soy sauce",

    # Mustard
    "dry mustard": "mustard",
    "dijon mustard": "mustard",
    "dijon-style mustard": "mustard",
    "prepared mustard": "mustard",
    "yellow mustard": "mustard",

    # Mayonnaise
    "mayonnaise": "mayonnaise",
    "mayo": "mayonnaise",
    "hellmann's or best foods real or low fat mayonnaise dressing": "mayonnaise",
    "hellmann's or best foods real or low fat mayonnaise or dressing": "mayonnaise",
    "mayonnaise or cream cheese": "mayonnaise",

    # Chocolate
    "chocolate chips": "chocolate chips",
    "semisweet chocolate chips": "chocolate chips",
    "semi-sweet chocolate chips": "chocolate chips",
    "semisweet chocolate morsels": "chocolate chips",
    "semi-sweet chocolate morsels": "chocolate chips",
    "nestle toll house semi-sweet chocolate morsels": "chocolate chips",
    "semisweet chocolate pieces": "chocolate chips",
    "white chocolate chips": "white chocolate",
    "white chocolate": "white chocolate chips",

    # Oats
    "oats": "oats",
    "rolled oats": "oats",
    "quick oats": "oats",
    "old fashioned oats": "oats",
    "quaker oats": "oats",

    # Peanut butter
    "peanut butter": "peanut butter",
    "creamy peanut butter": "peanut butter",
    "crunchy peanut butter": "peanut butter",
    "skippy creamy peanut butter": "peanut butter",

    # Evaporated milk brands
    "carnation evaporated milk": "evaporated milk",
    "evaporated milk or crisco": "evaporated milk",

    # Gelatin
    "gelatin": "gelatin",
    "unflavored gelatin": "gelatin",
    "knox gelatin": "gelatin",

    # Asian ingredients
    "sesame oil": "sesame oil",
    "toasted sesame oil": "sesame oil",
    "oyster sauce": "oyster sauce",
    "sake": "cooking wine",
    "chinese cooking wine": "cooking wine",
    "rice wine": "cooking wine",
    "mirin": "cooking wine",

    # Vinegars
    "vinegar": "vinegar",
    "white vinegar": "vinegar",
    "apple cider vinegar": "vinegar",
    "cider vinegar": "vinegar",
    "balsamic vinegar": "balsamic vinegar",
    "red wine vinegar": "vinegar",
    "white wine vinegar": "vinegar",
    "rice vinegar": "vinegar",

    # Pepper flakes/crushed
    "red pepper flakes": "crushed red pepper",
    "crushed red pepper": "red pepper flakes",
    "crushed red pepper flakes": "crushed red pepper",

    # Pasta/Noodles
    "pasta": "pasta",
    "noodles": "pasta",
    "egg noodles": "pasta",
    "fresh chinese noodles": "noodles",
    "lasagna noodles": "pasta",
    "uncooked lasagna noodles": "pasta",
    "spaghetti": "pasta",
    "linguine": "pasta",
    "penne": "pasta",
    "macaroni": "pasta",
    "elbow macaroni": "pasta",

    # Broccoli
    "broccoli": "broccoli",
    "broccoli florets": "broccoli",
    "broccoli flowerettes": "broccoli",
    "fresh broccoli": "broccoli",
    "frozen broccoli": "broccoli",
    "frozen broccoli spears": "broccoli",

    # Ginger
    "ginger": "ginger",
    "fresh ginger": "ginger",
    "grated ginger": "ginger",
    "minced ginger": "ginger",
    "ground ginger": "ginger",

    # Carrots
    "carrot": "carrots",
    "carrots": "carrot",
    "large carrots": "carrots",
    "grated carrots": "carrots",
    "shredded carrots": "carrots",
    "sliced carrots": "carrots",

    # Celery
    "celery": "celery",
    "celery stalks": "celery",
    "celery stalk": "celery",
    "sliced celery": "celery",
    "chopped celery": "celery",

    # Cake mixes and brand items
    "cake mix": "cake mix",
    "yellow cake mix": "cake mix",
    "white cake mix": "cake mix",
    "yellow or white cake mix": "cake mix",
    "duncan hines pineapple cake mix": "cake mix",
    "pasta sauce": "pasta sauce",
    "marinara sauce": "pasta sauce",
    "spaghetti sauce": "pasta sauce",
    "ragu old world style pasta sauce": "pasta sauce",

    # Lemon (zest, peel, rind all normalize)
    "lemon": "lemon",
    "lemon zest": "lemon zest",
    "lemon peel": "lemon zest",
    "lemon rind": "lemon zest",
    "grated lemon peel": "lemon zest",
    "grated lemon rind": "lemon zest",
    "grated lemon zest": "lemon zest",
    "finely grated lemon zest": "lemon zest",
    "lemon slices": "lemon",
    "lemon wedges": "lemon",

    # Lime
    "lime": "lime",
    "lime zest": "lime zest",
    "lime peel": "lime zest",
    "lime rind": "lime zest",
    "grated lime zest": "lime zest",
    "key lime": "lime",
    "key lime juice": "lime juice",

    # Orange
    "orange": "orange",
    "orange zest": "orange zest",
    "orange peel": "orange zest",
    "orange rind": "orange zest",
    "grated orange zest": "orange zest",
    "grated orange peel": "orange zest",

    # Cocoa
    "cocoa powder": "cocoa",
    "cocoa": "cocoa powder",
    "unsweetened cocoa powder": "cocoa",
    "unsweetened cocoa": "cocoa",
    "dutch-process cocoa powder": "cocoa",
    "dutch process cocoa": "cocoa",
    "baking cocoa": "cocoa",
    "unsweetened baking cocoa": "cocoa",
    "hershey's cocoa": "cocoa",

    # Cinnamon
    "cinnamon": "cinnamon",
    "ground cinnamon": "cinnamon",
    "cinnamon stick": "cinnamon",
    "cinnamon sticks": "cinnamon",
    "stick cinnamon": "cinnamon",

    # Nutmeg
    "nutmeg": "nutmeg",
    "ground nutmeg": "nutmeg",
    "freshly grated nutmeg": "nutmeg",
    "grated nutmeg": "nutmeg",

    # Tomato (consolidate)
    "tomato": "tomatoes",
    "tomatoes": "tomato",
    "plum tomato": "tomatoes",
    "plum tomatoes": "tomatoes",
    "roma tomato": "tomatoes",
    "roma tomatoes": "tomatoes",
    "cherry tomato": "tomatoes",
    "grape tomatoes": "tomatoes",
    "tomato slices": "tomatoes",
    "diced tomato": "tomatoes",

    # Chicken (consolidate)
    "chicken": "chicken",
    "chicken breast": "chicken",
    "chicken breast halves": "chicken",
    "boneless chicken": "chicken",
    "skinless chicken": "chicken",
    "rotisserie chicken": "chicken",

    # Beef (consolidate)
    "beef": "ground beef",
    "lean beef": "ground beef",
    "ground beef": "beef",
    "extra lean beef": "ground beef",
    "ground chuck": "ground beef",
    "ground sirloin": "ground beef",

    # Olive oil (consolidate variants)
    "olive oil": "olive oil",
    "extra-virgin olive oil": "olive oil",
    "extra virgin olive oil": "olive oil",
    "virgin olive oil": "olive oil",
    "light olive oil": "olive oil",
    "pure olive oil": "olive oil",
    "olive oil, divided": "olive oil",
    "extra-virgin olive oil, divided": "olive oil",

    # Herbs - Parsley
    "parsley": "parsley",
    "parsley flakes": "parsley",
    "flat-leaf parsley": "parsley",
    "italian parsley": "parsley",
    "curly parsley": "parsley",
    "parsley leaves": "parsley",
    "parsley sprigs": "parsley",

    # Herbs - Basil
    "basil": "basil",
    "basil leaves": "basil",
    "leaf basil": "basil",
    "thai basil": "basil",
    "sweet basil": "basil",

    # Herbs - Oregano
    "oregano": "oregano",
    "oregano leaves": "oregano",
    "leaf oregano": "oregano",

    # Herbs - Thyme
    "thyme": "thyme",
    "thyme leaves": "thyme",
    "thyme sprigs": "thyme",
    "leaf thyme": "thyme",

    # Herbs - Cilantro
    "cilantro": "cilantro",
    "cilantro leaves": "cilantro",
    "coriander leaves": "cilantro",

    # Herbs - Dill
    "dill": "dill",
    "dillweed": "dill",
    "dill weed": "dill",
    "dill sprigs": "dill",

    # Herbs - Rosemary
    "rosemary": "rosemary",
    "rosemary leaves": "rosemary",
    "rosemary sprig": "rosemary",
    "rosemary sprigs": "rosemary",

    # Cheese consolidation
    "mozzarella": "mozzarella cheese",
    "mozzarella cheese": "mozzarella",
    "part-skim mozzarella cheese": "mozzarella cheese",
    "part-skim mozzarella": "mozzarella cheese",
    "low-moisture mozzarella": "mozzarella cheese",
    "feta": "feta cheese",
    "feta cheese": "feta",
    "crumbled feta": "feta cheese",
    "blue cheese": "blue cheese",
    "crumbled blue cheese": "blue cheese",
    "gorgonzola": "blue cheese",

    # Applesauce
    "applesauce": "applesauce",
    "unsweetened applesauce": "applesauce",
    "chunky applesauce": "applesauce",
}


# Words to strip from ingredients for normalization
STRIP_WORDS = [
    "fresh", "dried", "frozen", "canned", "chopped", "diced", "sliced",
    "minced", "crushed", "ground", "grated", "shredded", "melted",
    "softened", "room temperature", "cold", "warm", "hot", "cooked",
    "uncooked", "raw", "prepared", "peeled", "seeded", "pitted",
    "boneless", "skinless", "bone-in", "skin-on", "trimmed",
    "large", "medium", "small", "extra-large", "jumbo", "mini",
    "thick", "thin", "finely", "coarsely", "roughly",
    "optional", "or more", "to taste", "as needed", "for garnish",
    "divided", "snipped", "crumbled", "packed", "firmly packed",
    "drained", "rinsed", "undrained", "rinsed and drained",
    "plus more", "plus extra", "for serving", "for topping",
    "thinly", "julienned", "matchstick", "cubed",
]

# Plural patterns for normalization
PLURAL_RULES = [
    (r"ies$", "y"),      # berries -> berry
    (r"oes$", "o"),      # tomatoes -> tomato, potatoes -> potato
    (r"ves$", "f"),      # loaves -> loaf
    (r"ves$", "fe"),     # knives -> knife
    (r"s$", ""),         # general plural
]


def normalize_ingredient(name):
    """
    Normalize an ingredient name for consistent matching.

    - Lowercase
    - Strip quantities and measurements
    - Strip common modifiers (fresh, chopped, etc.)
    - Handle plurals
    - Trim whitespace
    """
    if not name:
        return ""

    # Lowercase and trim
    normalized = name.lower().strip()

    # Remove content in parentheses
    normalized = re.sub(r'\([^)]*\)', '', normalized)

    # Strip leading quantities: "1/2 cup", "2 tablespoons", "1-1/2 cups", etc.
    # Pattern matches: numbers, fractions, ranges at the start followed by measurements
    quantity_pattern = r'^[\d\s/\-\.]+\s*(cups?|tablespoons?|tbsps?|teaspoons?|tsps?|ounces?|ozs?|pounds?|lbs?|cans?|packages?|pkgs?|cloves?|heads?|bunches?|stalks?|slices?|pieces?|sticks?|pinch(?:es)?|dash(?:es)?|sprigs?)\s+'
    normalized = re.sub(quantity_pattern, '', normalized, flags=re.IGNORECASE)

    # Also strip standalone leading numbers/fractions (e.g., "2 eggs" -> "eggs")
    normalized = re.sub(r'^[\d\s/\-\.]+\s+', '', normalized)

    # Strip common modifiers
    for word in STRIP_WORDS:
        # Word boundary matching to avoid partial matches
        pattern = r'\b' + re.escape(word) + r'\b'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Clean up extra whitespace
    normalized = ' '.join(normalized.split())

    # Remove leading/trailing punctuation
    normalized = normalized.strip('.,;:')

    return normalized.strip()


def singularize(word):
    """
    Convert plural to singular form.
    Simple rule-based approach for common cooking ingredients.
    """
    word = word.lower().strip()

    # Special cases that don't follow rules
    irregulars = {
        "leaves": "leaf",
        "halves": "half",
        "dice": "dice",
        "mice": "mouse",
        "teeth": "tooth",
        "feet": "foot",
        "geese": "goose",
        "men": "man",
        "women": "woman",
        "children": "child",
        "fish": "fish",
        "sheep": "sheep",
        "deer": "deer",
        "series": "series",
        "species": "species",
    }

    if word in irregulars:
        return irregulars[word]

    # Apply plural rules
    for pattern, replacement in PLURAL_RULES:
        if re.search(pattern, word):
            singular = re.sub(pattern, replacement, word)
            # Avoid over-singularizing (e.g., "cheese" shouldn't become "chees")
            if len(singular) >= 2:
                return singular

    return word


def get_canonical_name(ingredient):
    """
    Get the canonical (primary) name for an ingredient.
    Uses synonym mapping to normalize variants.
    """
    normalized = normalize_ingredient(ingredient)

    # Check direct synonym match
    if normalized in SYNONYMS:
        return SYNONYMS[normalized]

    # Try singularized form
    singular = singularize(normalized)
    if singular in SYNONYMS:
        return SYNONYMS[singular]

    return normalized


def extract_base_ingredient(item):
    """
    Extract the base ingredient name from an ingredient line.
    Handles compound ingredients like "cheddar cheese, shredded"
    """
    # Split on common separators
    base = item.split(',')[0]
    base = base.split(' or ')[0]
    base = base.split('/')[0]

    return normalize_ingredient(base)


def build_ingredient_index(recipes):
    """
    Build the ingredient index from a list of recipes.

    Returns a dictionary with:
    - ingredients: dict mapping canonical names to recipe IDs
    - synonyms: dict mapping variant names to canonical names
    - frequency: dict mapping canonical names to usage counts
    - all_names: list of all ingredient names for autocomplete
    """
    # Maps canonical ingredient name -> set of recipe IDs
    ingredient_recipes = defaultdict(set)

    # Maps all seen names to their canonical form
    name_to_canonical = {}

    # Frequency count for each canonical ingredient
    frequency = defaultdict(int)

    # All unique ingredient names seen (for autocomplete)
    all_names = set()

    for recipe in recipes:
        recipe_id = recipe.get('id', '')
        ingredients = recipe.get('ingredients', [])

        for ing in ingredients:
            if not isinstance(ing, dict):
                continue

            item = ing.get('item', '')
            if not item:
                continue

            # Store original name
            all_names.add(item.lower().strip())

            # Get normalized and canonical names
            normalized = normalize_ingredient(item)
            canonical = get_canonical_name(item)
            base = extract_base_ingredient(item)

            # Map names to canonical
            name_to_canonical[item.lower().strip()] = canonical
            name_to_canonical[normalized] = canonical
            if base:
                name_to_canonical[base] = canonical

            # Add recipe to ingredient's recipe list
            ingredient_recipes[canonical].add(recipe_id)
            frequency[canonical] += 1

            # Also index the base ingredient separately if different
            if base and base != canonical:
                base_canonical = get_canonical_name(base)
                ingredient_recipes[base_canonical].add(recipe_id)

    # Convert sets to sorted lists for JSON serialization
    ingredients_dict = {
        name: sorted(list(recipe_ids))
        for name, recipe_ids in ingredient_recipes.items()
    }

    # Sort frequency by count desc for top ingredients
    sorted_frequency = dict(sorted(
        frequency.items(),
        key=lambda x: (-x[1], x[0])  # Sort by frequency desc, then name asc
    ))

    # Top 100 ingredients for autocomplete suggestions (sorted by frequency)
    top_ingredients = list(sorted_frequency.keys())[:100]

    return {
        "meta": {
            "version": "2.0.0",
            "description": "Slim ingredient index for all family recipe collections",
            "total_ingredients": len(ingredients_dict),
            "total_recipes_indexed": len(recipes),
            "built_at": datetime.now(timezone.utc).isoformat(),
        },
        "ingredients": ingredients_dict,
        "synonyms": SYNONYMS,
        "top": top_ingredients,  # Top 100 for quick autocomplete
    }


def fetch_remote_recipes(collection):
    """
    Fetch recipes from a remote collection.
    Tries multiple URLs in order until one succeeds.
    Returns dict with recipes, count, url, and timestamp.

    Respects REMOTE_TIMEOUT env var (default 60s) for the entire collection.
    On timeout or failure, returns None (caller should warn and proceed).
    """
    collection_id = collection["id"]
    collection_name = collection["name"]
    fetch_time = datetime.now(timezone.utc).isoformat()

    # Set up timeout for entire collection fetch (Unix only, graceful fallback on Windows)
    use_signal_timeout = hasattr(signal, 'SIGALRM')
    if use_signal_timeout:
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(REMOTE_TIMEOUT)

    try:
        for url in collection["urls"]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "GrandmasRecipes/1.0"})
                # Per-URL timeout is min of 30s or remaining time
                with urllib.request.urlopen(req, timeout=min(30, REMOTE_TIMEOUT)) as response:
                    data = json.loads(response.read().decode('utf-8'))

                    # Handle both {recipes: [...]} and [...] formats
                    if isinstance(data, list):
                        recipes = data
                    else:
                        recipes = data.get('recipes', [])

                    if recipes:
                        print(f"    ✓ {collection_name}: {len(recipes)} recipes from {url}")
                        return {
                            "recipes": recipes,
                            "count": len(recipes),
                            "source": url,
                            "fetched_at": fetch_time
                        }

            except urllib.error.HTTPError as e:
                if e.code != 404:
                    print(f"    ✗ {collection_name}: HTTP {e.code} from {url}")
            except urllib.error.URLError as e:
                print(f"    ✗ {collection_name}: Network error - {e.reason}")
            except json.JSONDecodeError:
                print(f"    ✗ {collection_name}: Invalid JSON from {url}")
            except TimeoutError:
                print(f"    ⚠ {collection_name}: Timed out after {REMOTE_TIMEOUT}s (proceeding without)")
                return None
            except Exception as e:
                print(f"    ✗ {collection_name}: Error - {e}")

        print(f"    ✗ {collection_name}: No valid source found (proceeding without)")
        return None

    except TimeoutError:
        print(f"    ⚠ {collection_name}: Timed out after {REMOTE_TIMEOUT}s (proceeding without)")
        return None
    finally:
        # Reset alarm
        if use_signal_timeout:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def main():
    """Main entry point."""
    # Get paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    recipes_path = project_root / "data" / "recipes_master.json"
    output_path = project_root / "data" / "ingredient-index.json"

    print(f"Building ingredient index...")
    print(f"  Output: {output_path}")

    all_recipes = []
    collection_stats = {}

    build_time = datetime.now(timezone.utc).isoformat()

    def extract_tags_and_categories(recipes_list):
        """Extract unique tags and categories from a list of recipes."""
        tags = set()
        categories = set()
        for recipe in recipes_list:
            if recipe.get('tags'):
                for tag in recipe['tags']:
                    if tag:
                        tags.add(tag.lower().strip())
            if recipe.get('category'):
                categories.add(recipe['category'].lower().strip())
        return sorted(list(tags)), sorted(list(categories))

    # Load local recipes (Grandma Baker)
    print(f"\n  Loading local recipes...")
    if recipes_path.exists():
        with open(recipes_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        local_recipes = data.get('recipes', [])
        local_tags, local_categories = extract_tags_and_categories(local_recipes)
        print(f"    ✓ Grandma Baker: {len(local_recipes)} recipes, {len(local_tags)} tags from {recipes_path}")
        all_recipes.extend(local_recipes)
        collection_stats["grandma-baker"] = {
            "count": len(local_recipes),
            "source": "local",
            "fetched_at": build_time,
            "tags": local_tags,
            "categories": local_categories
        }
    else:
        print(f"    ✗ Grandma Baker: {recipes_path} not found")

    # Fetch remote collections
    print(f"\n  Fetching remote collections (timeout: {REMOTE_TIMEOUT}s per collection)...")
    failed_collections = []
    for collection in REMOTE_COLLECTIONS:
        result = fetch_remote_recipes(collection)
        if result:
            remote_tags, remote_categories = extract_tags_and_categories(result["recipes"])
            all_recipes.extend(result["recipes"])
            collection_stats[collection["id"]] = {
                "count": result["count"],
                "source": result["source"],
                "fetched_at": result["fetched_at"],
                "tags": remote_tags,
                "categories": remote_categories
            }
            print(f"      ({len(remote_tags)} tags, {len(remote_categories)} categories)")
        else:
            failed_collections.append(collection["name"])
            collection_stats[collection["id"]] = {
                "count": 0,
                "source": "failed",
                "fetched_at": build_time,
                "error": "timeout or network failure"
            }

    if failed_collections:
        print(f"\n  ⚠ Warning: {len(failed_collections)} collection(s) failed: {', '.join(failed_collections)}")
        print(f"    Proceeding with available recipes...")

    print(f"\n  Total: {len(all_recipes)} recipes from {len(collection_stats)} collections")

    if not all_recipes:
        print("Error: No recipes found")
        return 1

    # Build index
    index = build_ingredient_index(all_recipes)

    # Add collection stats to metadata
    index["meta"]["collections"] = collection_stats
    index["meta"]["description"] = "Combined ingredient index for all family recipe collections"

    print(f"  Indexed {index['meta']['total_ingredients']} unique ingredients")

    # Write minified output (no whitespace)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, separators=(',', ':'), ensure_ascii=False)

    # Report file size
    size_kb = output_path.stat().st_size / 1024
    print(f"  Output size: {size_kb:.1f} KB")

    # Show top 10 most common ingredients
    print("\n  Top 10 most common ingredients:")
    for i, name in enumerate(index['top'][:10], 1):
        recipe_count = len(index['ingredients'].get(name, []))
        print(f"    {i}. {name}: {recipe_count} recipes")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())
