# Evaluation status and reproducible benchmark plan

**No validated accuracy or calibration result is available.** The old claim of an approximately 70% false-positive reduction had no dataset, predictions or experiment record and has been withdrawn. Changing thresholds is tuning, not calibration. No accuracy figure should be inferred from the software tests or demo screenshots.

## What the scores mean

The implementation combines manually chosen metadata, ELA and artifact rules with an optional model response. Outputs are bounded 0–100 indicators. Historical database field names ending in `_probability` are retained for compatibility; they do not confer probabilistic meaning. Model self-reported confidence is also uncalibrated. Missing EXIF, resizing and JPEG recompression can affect scores on ordinary photographs. A low score is not evidence of authenticity.

## Proposed evaluation (not executed)

1. Select a versioned, independently sourced labeled dataset. One candidate for **edited-image localization/detection**, not a general AI-photo benchmark, is [CocoGlide from the TruFor authors](https://github.com/grip-unina/TruFor). Verify the dataset's own image licenses, source permissions and redistribution terms separately from the code license before downloading or redistributing it. This review has not cleared those rights. No dataset is bundled.
2. Add genuine camera photographs with documented provenance and permission, and generated images from multiple known generators. Keep the AI-generated and edited-image tasks separate; do not label an edited camera photo as fully generated. Exclude private images. A convenience sample cannot establish population accuracy.
3. Record a CSV manifest with `sha256,relative_path,source_url,license,origin_label,transform,parent_id,split`. Split by source/parent image and generator before tuning to avoid near-duplicate leakage. Keep held-out sources and compression variants.
4. Pin the repository commit, Python/dependency versions, manifest hash and fixed thresholds. Run `detector.services.image_analysis.run_local_analysis` and `detector.services.scoring.calculate_final_score` locally, with the external-analysis branch disabled. Store per-image scores, labels, errors and timings. The optional provider path needs a separate, explicitly approved cost/privacy evaluation with model version and request settings.
5. On the untouched test split, publish sample counts, class balance, confusion matrices, false-positive and false-negative rates with confidence intervals, abstentions and processing failures. Stratify by source, generator, resolution and recompression. Show licensed false-positive/negative examples, not only successes.
6. Only if probabilities are needed, fit a calibration method on a separate calibration split and evaluate reliability diagrams and Brier score on held-out data. Never fit and report on the same images. Document all uncertainty and dataset limitations.

## Acceptance criteria for issue #4

- Dataset provenance and usage rights reviewed; reproducible manifest committed without private images.
- Versioned offline evaluator, raw predictions and error records.
- Independent held-out measurements for the two tasks, including failure examples and uncertainty.
- UI and documentation consistently distinguish heuristic scores from calibrated probabilities.

Only the last criterion is addressed by this portfolio change. [Issue #4](https://github.com/kurapikac2/ai-photo-checker/issues/4) remains open. The synthetic screenshot demonstrates software behavior only, not detector quality.
