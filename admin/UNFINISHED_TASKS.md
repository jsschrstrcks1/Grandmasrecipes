# Unfinished Tasks

| library_task_id | priority | title |
|---|---|---|
| audit0827-gmr-health-detection-criticals | 0 | P0 AUDIT-0827: the three CRITICAL health-detection defects documented 2026-01-30 (.claude/HEALTH_AUDIT_REPORT.md via .claude/REPO_STATUS_REVIEW.md:98-111) are still present: (a) script.js:872 reverse partial match flaggedIng.includes(ingText); (b) :872-877 breaks on first match instead of merging all interactions; (c) data/health-considerations.json ace_potassium severity 'moderate' against the review's 'potentially life-threatening' assessment; plus 9 HIGH false-allergen classifications. Fix the matcher and re-classify. |

<!-- library register 2026-08-27T05:05:26.939Z -->
| audit0827-gmr-hub-aggregation-stale | 1 | P1 AUDIT-0827: this repo is the de-facto hub (4-collection registry, aggregate scripts) and its aggregation is 7 months stale: recipes_master.json last_aggregation 2026-01-23; index shows all:5722 while Allrecipes alone now has 9,989 and granny-hudson 184 vs true 201; collections.json repeats the stale counts. No CI job aggregates (rebuild-indexes.yml only shards). Run aggregate_collections.py and add an aggregation job or cadence. |

<!-- library register 2026-08-27T05:05:27.342Z -->
| audit0827-gmr-kitchen-tips-never-render | 1 | P1 AUDIT-0827: loadKitchenTips() (script.js:798-802) does kitchenTipsData.categories.reduce(...) but data/kitchen-tips.json's only top-level key is tips — the TypeError is swallowed (:804-808 'Non-fatal - tips just won't show') and the same wrong assumption repeats at :1074 and :1109, so 156 aggregated family tips never render. Fix the loader (or the aggregator's schema) and un-swallow the error. |

<!-- library register 2026-08-27T05:05:27.769Z -->
| audit0827-gmr-remote-scan-images-dead | 1 | P1 AUDIT-0827: getCollectionImagePath(collection, isRemote=false, remoteSiteUrl=null) supports remote bases (script.js:5208-5215) but the sole caller at :5223 passes one argument — of 3,753 image_refs, 764 local grandma-baker refs resolve and 3,489 remote-collection refs (1,940 mommom, 1,222 all, 327 granny) point at nonexistent local paths. Pass the remote args per collection registry. |

<!-- library register 2026-08-27T05:05:28.221Z -->
| audit0827-gmr-pwa-manifest-missing | 2 | P2 AUDIT-0827: sw.js is live (registered index.html:857-859) but Phase 3's web-app manifest does not exist (no manifest.json/site.webmanifest, no link rel=manifest) so the PWA cannot install; no offline.html fallback (Phase 1); sw.js CACHE_VERSION is still 'v1.0.0' despite repeated site changes, with no bump automation. Also reconcile the SERVICE_WORKER_PLAN/INGREDIENT-SEARCH-PLAN trackers whose ~75 checkboxes are all unchecked while most of the work shipped. |

<!-- library register 2026-08-27T05:05:28.602Z -->
| audit0827-gmr-processed-images-missing | 2 | P2 AUDIT-0827: data/processed/ does not exist and 924 oversized local images have no AI-safe versions — flagged HIGH PRIORITY in .claude/REPO_STATUS_REVIEW.md:66,72-73 and still open. Run scripts/process_images.py. |

<!-- library register 2026-08-27T05:05:28.988Z -->
| audit0827-gmr-legacy-shards-14mb | 2 | P2 AUDIT-0827: 15 legacy hyphen-named shard files (14.4 MB — recipes-mains 4.5 MB, recipes-desserts 2.9 MB, recipes-index.json 1.5 MB...) are published and unreachable by any page; script.js:360 fetches the underscore-named recipes_index.json, and the coexisting recipes-index.json vs recipes_index.json is a live trap. Delete the legacy set (also consider not serving the 28 MB recipes_master.json). |

<!-- library register 2026-08-27T05:05:29.415Z -->
| audit0827-gmr-count-discrepancies | 2 | P2 AUDIT-0827: three different numbers for local counts: recipes_master.json meta total_recipes 9397 vs actual array 9396; meta collection_counts.grandma-baker 938 vs 933 in recipes_index.json and collections.json. Fix the meta and add a count check to the rebuild workflow. |

<!-- library register 2026-08-27T05:05:29.811Z -->
| audit0827-gmr-health-json-no-edit-surface | 2 | P2 AUDIT-0827: clinically-consequential classifications (health-considerations.json severities, carb-database, heart-smart, diabetic-substitutions, scaling-rules) are changeable only by hand-editing JSON — no admin view, no in-app correction path — which the audit identifies as the structural reason the P0 mis-classification sat unfixed ~7 months. Build a minimal owner-only editing surface or a validated edit script. |

<!-- library register 2026-08-27T05:05:30.319Z -->
| audit0827-gmr-calculator-orphan | 3 | P3 AUDIT-0827: calculator.html has zero inbound links from index/recipe/script/sw and is not in PRECACHE_ASSETS — reachable only by typed URL. Link it from the nav or retire it. |

<!-- library register 2026-08-27T05:05:30.708Z -->
| audit0827-gmr-readme-stale | 3 | P3 AUDIT-0827: README.md:246-252 'Current recipes' still lists exactly 5 recipes and :45 says 'small but growing recipe set' against 933 local / 9,392 total; Known-issues covers only 2 of those 5. Regenerate the README sections from data. |
