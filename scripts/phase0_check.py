import benchmarks.loader as L
from collections import Counter

all_cases = []
suite_cases = L.load_all_suites()
if isinstance(suite_cases, dict):
    for suite_name, cases in suite_cases.items():
        print(f'suite {suite_name}: {len(cases)} cases')
        all_cases.extend(cases)
else:
    print(f'capability_suites: {len(suite_cases)} cases')
    all_cases.extend(suite_cases)

for dataset_name in ['easy', 'medium', 'hard', 'enriched']:
    cases = L.load_dataset(f'benchmarks.datasets.{dataset_name}')
    print(f'{dataset_name}: {len(cases)} cases')
    all_cases.extend(cases)

ids = [c['id'] for c in all_cases]
counts = Counter(ids)
duplicates = {k: v for k, v in counts.items() if v > 1}

print(f'\nTotal cases: {len(all_cases)}')
print(f'Unique IDs: {len(set(ids))}')
print(f'Duplicates: {len(all_cases) - len(set(ids))}')
gt_count = sum(1 for c in all_cases if c.get('ground_truth'))
print(f'With ground_truth: {gt_count}')
print(f'Without ground_truth: {len(all_cases) - gt_count}')

if duplicates:
    print('Duplicate IDs:')
    for case_id, count in duplicates.items():
        print(f'  {case_id}: {count}')

assert len(all_cases) == 64, f'Expected 64 cases, got {len(all_cases)}'
assert len(set(ids)) == 64, f'Expected 64 unique IDs, got {len(set(ids))}'
assert not duplicates, f'Found duplicates: {duplicates}'
assert gt_count >= 50, f'Too few ground_truth cases: {gt_count}'

print('\nPHASE 0: PASS')
