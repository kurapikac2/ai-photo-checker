# Verification and privacy review

Reviewed 2026-11-09 on Windows / Python 3.12.10. This is a local prototype review, not a production security certification.

## Executed checks

- 43 Django tests passed, zero skips. The new score-presentation test failed against the previous template before the wording fix.
- System check, migration consistency, Python compilation and `pip check` passed. Fresh isolated demo database applied all migrations; no existing user database was accessed.
- `pip-audit -r requirements.txt` initially reported 104 advisory records across Django, Pillow, requests and python-dotenv. Updated those four direct pins; repeat audit found no known vulnerabilities. This is an advisory snapshot, not proof of absence of vulnerabilities.
- Gitleaks 8.30.1 scanned the fetched Git history (20 commits before this change), with no findings.
- Deployment check reports four warnings: HSTS, SSL redirect, secure session cookie and secure CSRF cookie. They remain explicit requirements for any separate deployment review.

- Real Chromium 141.0.7390.37 verified a synthetic upload, external consent off, completed local processing, score disclaimer, stranger denial, and no page errors or horizontal overflow at 1440/768/390 px. Captures were inspected visually. No historical visual baseline or full accessibility audit is claimed.
- Browser testing reproduced a 403 on legitimate uploads: `no-referrer` caused `Origin: null`. Changing the document policy to `same-origin` preserves CSRF enforcement and suppresses cross-origin referrers. The new regression failed before the change; browser upload passes afterward.

## Issue #2 acceptance evidence

| Boundary | Implementation | Executed regression coverage |
| --- | --- | --- |
| Session ownership | `owned_checks` filters by random session token | Another session cannot read results/history/images; legacy ownerless rows are inaccessible |
| Private storage | Protected `/image/<id>/`; no raw media route | Owned PNG readable; stranger and raw `/media/` URL return 404 |
| CSRF and deletion | POST-only deletion, Django CSRF middleware | Missing CSRF rejected on upload/delete; valid owner deletion removes row and file; stranger rejected |
| Retention | Expiry check and opt-in purge command | Expired data hidden; dry run preserves data; purge removes only expired test fixtures |
| Retry safety | File deletion before row deletion | Storage failure preserves row and file; processing cannot recreate a deleted row |
| Sensitive responses | `never_cache`, generic errors, no stored raw model response | Result/image/history are `no-store`; internal errors and upstream bodies are not exposed |
| External processing | Explicit per-upload consent | Default makes no provider call; consent path is mocked in tests |
| Upload validation | Size/pixel bounds, format verification and decode | Malformed, oversized and spoofed images rejected; JPEG/PNG/WEBP accepted |

The original issue's application-level criteria are covered. This does not make public deployment safe: operators must enforce private storage at the proxy, protect backups, configure HTTPS, schedule retention, limit abuse and remove third-party executable assets. No deployment or external AI call was made.

## Screenshot reproduction

Start the app on loopback in a fresh checkout with no provider key. Create a 640×480 PNG containing only geometric shapes using Pillow, upload with external consent unchecked, and capture the resulting page in Chromium at 1440×1000 and 390×1000. The fixture contains no person, EXIF or private data. Tracked images are unedited application output. Their purpose is UI inspection, not detector evaluation.

## Remaining evaluation work

[Issue #4](https://github.com/kurapikac2/ai-photo-checker/issues/4) remains open: no representative, independently labeled benchmark has been run. [CALIBRATION.md](../CALIBRATION.md) defines provenance, rights review, split integrity, offline predictions and failure reporting required before making accuracy claims.

To rerun the browser regression, install Node.js, run `npm ci --prefix e2e`, then `cd e2e; npx playwright install chromium`. Start the isolated app on port 8014 with an empty `OPENROUTER_API_KEY`, then run `npm test` from `e2e`. It uses the checked-in synthetic fixture and writes ignored `test-results/`. CI executes the same check.
