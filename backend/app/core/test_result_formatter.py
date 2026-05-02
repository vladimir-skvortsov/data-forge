from __future__ import annotations

import json
from pathlib import Path


from app.core.result_formatter import read_results, write_results

_RECORDS = [
    {
        'file': 'a.txt',
        'structured': {'name': 'Alice', 'age': 30},
        'processed_path': '/tmp/a.txt',
    },
    {
        'file': 'b.txt',
        'structured': {'name': 'Bob', 'age': 25},
        'processed_path': '/tmp/b.txt',
    },
]


# ── write_results ─────────────────────────────────────────────────────────────


def test_write_json_creates_json_file(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'json')
    assert path.suffix == '.json'
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data) == 2
    assert data[0]['file'] == 'a.txt'


def test_write_yaml_creates_yaml_file(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'yaml')
    assert path.suffix == '.yaml'
    assert path.exists()
    assert 'Alice' in path.read_text(encoding='utf-8')


def test_write_csv_creates_csv_file(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'csv')
    assert path.suffix == '.csv'
    assert path.exists()
    content = path.read_text(encoding='utf-8')
    assert '_source_file' in content
    assert 'Alice' in content


def test_write_parquet_creates_parquet_file(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'parquet')
    assert path.suffix == '.parquet'
    assert path.exists()
    assert path.stat().st_size > 0


def test_write_unknown_format_falls_back_to_json(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'xml')
    assert path.suffix == '.json'


def test_write_empty_results(tmp_path: Path) -> None:
    path = write_results([], tmp_path, 'json')
    assert json.loads(path.read_text()) == []


def test_write_results_with_null_structured(tmp_path: Path) -> None:
    records = [{'file': 'x.txt', 'structured': None, 'processed_path': '/tmp/x.txt'}]
    path = write_results(records, tmp_path, 'csv')
    assert path.exists()


# ── round-trip ────────────────────────────────────────────────────────────────


def test_json_round_trip(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'json')
    result = read_results(path)
    assert result[0]['file'] == 'a.txt'
    assert result[0]['structured']['name'] == 'Alice'


def test_yaml_round_trip(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'yaml')
    result = read_results(path)
    assert len(result) == 2
    assert result[1]['structured']['name'] == 'Bob'


def test_csv_round_trip(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'csv')
    result = read_results(path)
    assert len(result) == 2
    files = [r['file'] for r in result]
    assert 'a.txt' in files
    names = [r['structured']['name'] for r in result]
    assert 'Alice' in names


def test_parquet_round_trip(tmp_path: Path) -> None:
    path = write_results(_RECORDS, tmp_path, 'parquet')
    result = read_results(path)
    assert len(result) == 2
    assert any(r['structured'].get('age') == 30 for r in result)


def test_read_empty_yaml(tmp_path: Path) -> None:
    empty_yaml = tmp_path / 'result.yaml'
    empty_yaml.write_text('', encoding='utf-8')
    assert read_results(empty_yaml) == []
