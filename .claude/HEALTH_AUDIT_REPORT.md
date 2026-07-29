# Health Features Audit Report

**Auditor:** Claude (Opus 4.5)
**Date:** 2026-01-30
**Scope:** All health-related data files, JavaScript modules, and detection logic
**Method:** Code review + independent verification against authoritative medical/nutritional sources

---

## Executive Summary

The health features are **ambitious and mostly well-sourced**, but contain **several factual errors in ingredient classification** that could mislead users. The most critical issues are false allergen flags that could cause unnecessary food avoidance, and one severity under-classification for a potentially life-threatening drug interaction. The medical claims in the converter tools (diabetic, heart-smart) are well-researched and accurate.

**Total issues found: 21**
- Critical (could cause harm): 3
- High (factual errors affecting user trust): 9
- Medium (inaccuracies, outdated info): 5
- Low (minor, code quality): 4

---

## CRITICAL Issues (Could Cause Harm)

### C1. ACE Inhibitor/Potassium Interaction Under-Classified as "moderate"

**File:** `data/health-considerations.json` line 42
**Issue:** The `ace_potassium` concern is classified as severity "moderate", but hyperkalemia from ACE inhibitors + high-potassium foods can cause fatal cardiac arrhythmias.
**Evidence:** NCBI StatPearls, Cleveland Clinic Journal of Medicine, and JAHA all classify severe hyperkalemia (>6.0 mEq/L) as a clinical emergency. The ACE inhibitor interaction is well-documented to cause life-threatening hyperkalemia, particularly in patients with CKD or on combined RAAS blockade.
**Risk:** A user on ACE inhibitors eating a high-potassium recipe might dismiss a "moderate" severity warning.
**Recommendation:** Upgrade to severity "high" to match the warfarin and grapefruit interactions, which carry similar life-threatening potential.

### C2. Detection Logic First-Match-Only Bug

**File:** `script.js` lines 871-876
**Issue:** The partial matching logic breaks after the first match:
```javascript
for (const [flaggedIng, flaggedConcerns] of Object.entries(db.ingredients)) {
  if (ingText.includes(flaggedIng) || flaggedIng.includes(ingText)) {
    concerns = flaggedConcerns;
    break;  // <-- Only gets first match
  }
}
```
This means if a recipe ingredient is "sharp cheddar cheese", the loop might match "cheddar" first (tyramine + milk + histamine warnings) but miss "cheese" (which has additional phosphorus warnings). Worse, the iteration order of `Object.entries()` is insertion order, so the match depends on which entry appears first in the JSON — not which is the best match.
**Risk:** Missed health warnings. A user with CKD might not see a phosphorus warning because a different (correct but incomplete) match was found first.
**Recommendation:** Collect ALL matching entries, merge their concern arrays, and deduplicate.

### C3. Reverse Partial Match Causes False Positives

**File:** `script.js` line 872
**Issue:** The condition `flaggedIng.includes(ingText)` means if a recipe ingredient is short (e.g., "oil"), it will match the first flagged ingredient containing "oil" — which could be "olive oil" (flagged for warfarin vitamin K). A recipe calling for "vegetable oil" would get a vitamin K warning meant for olive oil.
**Risk:** False health warnings that erode user trust, or worse, cause unnecessary dietary restrictions.
**Recommendation:** Remove the reverse-direction match (`flaggedIng.includes(ingText)`), or require a minimum match length, or use word-boundary matching.

---

## HIGH Issues (Factual Errors)

### H1. Cream of Tartar Falsely Flagged as Milk Allergen

**File:** `data/health-considerations.json` line 634-637
**Issue:** `cream of tartar` is tagged with `allergen_milk`. Cream of tartar is potassium bitartrate, a byproduct of winemaking. It contains **zero dairy**. The word "cream" in the name is misleading but it has no relation to milk.
**Source:** Food Allergy Research and Education (FARE), multiple allergen databases confirm cream of tartar is free of all top 14 allergens.
**Impact:** A user with milk allergy would be falsely warned to avoid recipes with cream of tartar.
**Fix:** Remove `allergen_milk` from cream of tartar.

### H2. Coconut Milk Falsely Flagged as Milk Allergen

**File:** `data/health-considerations.json` lines 790-795
**Issue:** `coconut milk` is tagged with `allergen_milk`. Coconut milk is a plant-based product — it is not dairy and does not contain milk proteins (casein, whey).
**Note:** As of January 2025, FDA also removed coconut from the tree nut allergen list. Coconut milk could be flagged as a potential concern for people with coconut allergy specifically, but NOT as a dairy allergen.
**Impact:** Could cause users to unnecessarily avoid coconut milk when they're allergic to dairy, or conversely, fail to flag it appropriately for those with coconut-specific allergy.
**Fix:** Remove `allergen_milk`. Consider adding a separate `allergen_coconut` category or noting coconut under `allergen_tree_nuts` with a caveat that FDA no longer requires tree nut labeling for coconut.

### H3. Peanut Butter Falsely Flagged as Milk Allergen

**File:** `data/health-considerations.json` lines 545-549
**Issue:** `peanut butter` is tagged with `allergen_milk`. Standard peanut butter (including Smucker's Natural at line 1492) contains only peanuts and salt — no dairy. Some commercial brands *may* have milk ingredients, but the default should not flag it.
**Impact:** False dairy warning on recipes using peanut butter.
**Fix:** Remove `allergen_milk`. The `allergen_peanuts` flag is correct and sufficient.

### H4. Water Chestnuts Falsely Flagged as Tree Nut Allergen

**File:** `data/health-considerations.json` lines 654-656
**Issue:** `water chestnuts` are tagged with `allergen_tree_nuts`. Water chestnuts are aquatic vegetable tubers (Eleocharis dulcis), completely unrelated to tree nuts botanically or allergologically. FAACT, FARE, and the FDA all confirm water chestnuts are safe for tree nut allergy.
**Impact:** False tree nut warning on Asian recipes using water chestnuts.
**Fix:** Remove `allergen_tree_nuts` from water chestnuts.

### H5. Sour Cream Questionably Flagged for Tyramine (MAOI)

**File:** `data/health-considerations.json` lines 526-530
**Issue:** `sour cream` is tagged with `maoi_tyramine`. Fresh, commercially produced sour cream is generally considered low-tyramine and safe for MAOI users in moderate amounts (<1/2 cup). Only aged, fermented, or spoiled dairy products are high-tyramine.
**Source:** PMC article "The Prescriber's Guide to the MAOI Diet" (2022); Gateway Psychiatric MAOI diet update; Ohio State University patient education on low-tyramine diet.
**Risk:** Overly restrictive. Users on MAOIs might unnecessarily avoid recipes with sour cream, which could reduce dietary enjoyment and compliance.
**Fix:** Either remove `maoi_tyramine` from sour cream, or add a qualifier in the database noting "low risk if fresh and commercially produced."

### H6. Buttermilk Questionably Flagged for Tyramine (MAOI)

**File:** `data/health-considerations.json` lines 568-571
**Issue:** Same as H5. Fresh, commercial buttermilk is cultured but low in tyramine. The PMC prescriber's guide lists buttermilk as "use with caution" at 1/2 cup, not "avoid."
**Fix:** Same as H5 — consider a more nuanced severity or remove.

### H7. Mixed Nuts "With No Peanuts" Flagged for Peanut Allergen

**File:** `data/health-considerations.json` lines 1429-1432
**Issue:** `mixed nuts with no peanuts` is tagged with `allergen_peanuts`. The ingredient name explicitly states no peanuts. While cross-contamination is a real concern, flagging the ingredient itself as containing peanuts is factually wrong.
**Fix:** Remove `allergen_peanuts`. The `allergen_tree_nuts` flag (if present) would be appropriate. A cross-contamination note could be added separately.

### H8. Scotch Bonnet Chiles Flagged for Alcohol Content

**File:** `data/health-considerations.json` lines 1446-1451
**Issue:** `scotch bonnet chiles` and `scotch bonnet chiles, bird peppers, datil peppers, or other chiles` are tagged with `alcohol_content`. Scotch bonnet is a variety of hot pepper — the word "scotch" has no relation to scotch whisky or alcohol.
**Impact:** False alcohol warning on recipes using scotch bonnet peppers.
**Fix:** Remove `alcohol_content` from these entries.

### H9. Prune Puree Flagged as Milk Allergen

**File:** `data/health-considerations.json` lines 1162-1167
**Issue:** `prune puree or prune butter` is tagged with `allergen_milk`. Prune puree is made from dried plums (prunes) and contains no dairy. The word "butter" in "prune butter" refers to the spreadable consistency, not dairy butter.
**Fix:** Remove `allergen_milk`.

---

## MEDIUM Issues (Inaccuracies, Outdated Info)

### M1. Coconut Flour Allergen Warning Outdated

**File:** `data/diabetic-substitutions.json` line 340
**Issue:** `"allergen_warning": "Contains coconut (classified as tree nut by FDA)."` — As of January 6, 2025, FDA removed coconut from the tree nut allergen labeling list. This claim is now outdated.
**Source:** FDA Guidance Document "Questions and Answers Regarding Food Allergens" Edition 5 (January 2025); FARE, Allergic Living, IDFA all confirmed the change.
**Fix:** Update to "Contains coconut. Note: As of 2025, FDA no longer classifies coconut as a tree nut for allergen labeling, but some individuals may still be allergic to coconut."

### M2. Blueberries Flagged for Vitamin K Without Context

**File:** `data/health-considerations.json` lines 284-286
**Issue:** `blueberries` are flagged for `warfarin_vitamin_k`, same as spinach and kale. But blueberries contain only ~28 mcg vitamin K per cup (moderate), while spinach has ~888 mcg per cup (very high). Flagging both equally without dose context could lead to over-restriction.
**Source:** USDA FoodData Central; Stony Brook Medicine warfarin food guide classifies blueberries as "moderate" (25-100 mcg).
**Recommendation:** Consider adding severity tiers within the vitamin K category (e.g., "high vitamin K" vs "moderate vitamin K") so users understand relative risk.

### M3. Coffee Creamer Flagged for Caffeine

**File:** `data/health-considerations.json` lines 1454-1456
**Issue:** `coffee creamer` is tagged with `caffeine_content`. Standard coffee creamers (liquid or powdered) contain no caffeine. They are dairy or non-dairy whiteners.
**Fix:** Remove `caffeine_content` from coffee creamer.

### M4. Orange Slice Candy Flagged for Potassium

**File:** `data/health-considerations.json` lines 1207-1211
**Issue:** `orange slice candy` is tagged with `ace_potassium` and `ckd_high_potassium`. Orange slice candy is primarily sugar and gelatin with orange flavoring — it contains negligible potassium.
**Fix:** Remove potassium flags from orange slice candy. The `diabetic_high_glycemic` flag is appropriate.

### M5. Pumpkin Pie Spice Flagged for High Potassium

**File:** `data/health-considerations.json` lines 1329-1332
**Issue:** `pumpkin pie spice` is tagged with `ace_potassium` and `ckd_high_potassium`. Pumpkin pie spice is a blend of cinnamon, ginger, nutmeg, allspice, and cloves used in teaspoon quantities. The potassium content of a teaspoon of spice is clinically insignificant.
**Fix:** Remove potassium flags. These are relevant for actual pumpkin (which has ~400 mg K per cup), not for the spice blend.

---

## LOW Issues (Minor)

### L1. Sesame Allergen Description Says "Added 2023"

**File:** `data/health-considerations.json` line 116
**Issue:** `"description": "Contains sesame. The 9th major allergen (added 2023)."` — Sesame was added to the US allergen labeling requirement by the FASTER Act, which took effect January 1, 2023. This is accurate but worth noting that the law was signed in 2021 and took effect 2023.
**Impact:** Minimal — factually correct, could be slightly more precise.

### L2. Hemp Hearts Allergen Warning Mentions Tree Nuts

**File:** `data/diabetic-substitutions.json` line 222
**Issue:** `"allergen_warning": "Tree nut and seed allergy consideration."` — Hemp seeds/hearts are not tree nuts. They are seeds. Including "tree nut" in this warning could confuse users.
**Fix:** Change to "Seed allergy consideration." Remove "tree nut" reference.

### L3. Almond Extract Flagged for Phosphorus

**File:** `data/health-considerations.json` lines 1276-1279
**Issue:** `almond extract` is flagged for `ckd_high_phosphorus`. Almond extract is used in teaspoon quantities — the phosphorus content is negligible at that serving size.
**Impact:** Minimal but technically incorrect for practical purposes.

### L4. No Distinction Between Fresh and Aged Yogurt for MAOI

**File:** `data/health-considerations.json` (multiple yogurt entries)
**Issue:** All yogurt variants (plain, low-fat, flavored) are flagged for `maoi_tyramine`. Fresh yogurt is low-tyramine per PMC evidence. Only very aged or improperly stored yogurt is a concern.
**Impact:** Overly broad flagging for MAOI users.

---

## What's Done Well

The audit found significant areas of quality:

1. **Drug-food interaction categories are medically accurate.** The warfarin/vitamin K, MAOI/tyramine, grapefruit/CYP3A4, and ACE inhibitor/potassium interactions are all correctly described with appropriate medication lists.

2. **USDA safe cooking temperatures are correct.** 145°F for whole cuts of beef/pork/lamb with 3-min rest, 160°F for ground meats, 165°F for all poultry — all match current USDA FSIS guidelines.

3. **Erythritol cardiovascular warning is well-sourced and accurate.** The Cleveland Clinic studies (Nature Medicine 2023, ATVB 2024) are correctly cited. The recommendation to prefer allulose is sound.

4. **AHA sodium targets are correctly stated.** <2,300 mg/day (ideal <1,500 mg/day) matches current AHA guidelines. Per-serving target of 600 mg (based on 4 meals/day) is a reasonable interpretation.

5. **Diabetic converter data is well-structured.** GI values, carb counts, and net carb calculations are consistent with USDA and Sydney University data. The SGLT2 inhibitor/ketoacidosis warning is a good safety inclusion.

6. **Curing salt / botulism safety warning is present.** The heart-smart database correctly warns against reducing salt in home-cured meats (FDA minimum 120 ppm sodium nitrite).

7. **Potassium chloride safety warning is present.** Correctly warns about kidney disease and ACE inhibitor interaction with salt substitutes.

8. **Medical disclaimers are present** in diabetic-converter.js, heart-smart-converter.js, and the health considerations panel in script.js.

9. **Mercury warnings on fish** are present in the protein substitution data for meaty/bold fish (swordfish, tuna steak, shark).

10. **Scaling rules are sensible.** Non-linear spice scaling exponents, pan size recommendations, and batch-cooking warnings for sauteing are all sound culinary science.

---

## Verification Sources Used

- [NIH Office of Dietary Supplements - Vitamin K](https://ods.od.nih.gov/factsheets/VitaminK-Consumer/)
- [NCBI StatPearls - MAOIs](https://www.ncbi.nlm.nih.gov/books/NBK539848/)
- [PMC - The Prescriber's Guide to the MAOI Diet](https://pmc.ncbi.nlm.nih.gov/articles/PMC9172554/)
- [FDA - Grapefruit Juice and Drugs](https://www.fda.gov/consumers/consumer-updates/grapefruit-juice-and-some-drugs-dont-mix)
- [Cleveland Clinic Journal of Medicine - ACE inhibitors and potassium](https://www.ccjm.org/content/86/9/601)
- [NCBI StatPearls - ACE Inhibitors](https://www.ncbi.nlm.nih.gov/books/NBK430896/)
- [Nature Medicine - Erythritol cardiovascular risk (2023)](https://www.nature.com/articles/s41591-023-02223-9)
- [AHA Journals - Erythritol platelet study (2024)](https://www.ahajournals.org/doi/10.1161/ATVBAHA.124.321019)
- [FDA Allergen Guidance Edition 5 (January 2025)](https://www.fda.gov/food/hfp-constituent-updates/fda-releases-allergen-food-safety-and-plant-based-alternative-labeling-guidances)
- [FAACT - Tree Nut Allergen](https://www.foodallergyawareness.org/food-allergy-and-anaphylaxis/food-allergens/tree-nuts/)
- [FARE - Cream of Tartar Safety](https://www.foodallergy.org)
- [USDA FSIS Safe Temperature Chart](https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/safe-temperature-chart)
- [AHA Sodium Guidelines](https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/sodium/how-much-sodium-should-i-eat-per-day)
- [Stony Brook Medicine - Warfarin Food Interactions](https://heart.stonybrookmedicine.edu/sites/default/files/heartpubfiles/Food_Interactions_with_Warfarin.pdf)
- [USDA FoodData Central](https://fdc.nal.usda.gov/)

---

## Recommended Priority for Fixes

1. **Immediate (Critical):** Fix C1 (ACE inhibitor severity), C2 (first-match-only bug), C3 (reverse partial match)
2. **High Priority:** Fix H1-H9 (false allergen/content flags)
3. **When Convenient:** Fix M1-M5 (outdated info, over-flagging)
4. **Low Priority:** Fix L1-L4 (minor improvements)

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness." — Proverbs 31:27*
