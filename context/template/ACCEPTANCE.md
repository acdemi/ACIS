# Acceptance - <Sprint Name>

> Definition of Done. Every item must be checked before the sprint closes.

## Functional
- [ ] <Verifiable behavior 1>
- [ ] <Verifiable behavior 2>

## Non-Functional
- [ ] No public API changed (or change is documented and approved)
- [ ] Backward compatibility preserved
- [ ] No duplicate logic introduced
- [ ] No unused code added

## Validation
- [ ] `pytest` green (baseline count preserved or grown)
- [ ] `ruff` clean
- [ ] `mypy` clean (if configured)
- [ ] Architecture review (workflow Step 6) passed

## Regression
- [ ] `python evals/smoke_eval.py` green
- [ ] `python evals/fixture_eval.py` green (12 scenarios)