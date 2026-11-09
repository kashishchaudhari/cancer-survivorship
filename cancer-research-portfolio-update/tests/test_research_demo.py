import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('research_builder', ROOT / 'scripts/build_research_demo.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_released_values_match_public_reports():
    payload = builder.extract(ROOT / 'docs')
    liver = next(s for s in payload['studies'] if s['cohort'] == 'Liver')
    assert liver['index_patients'] == 64491
    assert liver['primary']['auc_ci'] == [0.809, 0.836]
    assert liver['temporal']['test_n'] == 5578
    assert liver['unknown_timing_pct'] == 57.0
    assert not payload['synthetic']


def test_disagreeing_published_tables_fail_closed(tmp_path):
    for name in ('CASE_STUDIES.md', 'RESULTS_SUMMARY.md'):
        text = (ROOT / 'docs' / name).read_text(encoding='utf-8')
        if name == 'CASE_STUDIES.md':
            text = text.replace('0.823 (0.809', '0.822 (0.809')
        (tmp_path / name).write_text(text, encoding='utf-8')
    with pytest.raises(ValueError, match='disagree'):
        builder.extract(tmp_path)
