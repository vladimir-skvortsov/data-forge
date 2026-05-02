from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_EXT: dict[str, str] = {
    'json': '.json',
    'yaml': '.yaml',
    'csv': '.csv',
    'parquet': '.parquet',
}

_SOURCE_COL = '_source_file'


def write_results(
    results: list[dict[str, Any]],
    job_dir: Path,
    output_format: str = 'json',
) -> Path:
    fmt = output_format.lower()
    result_path = job_dir / f'result{_EXT.get(fmt, ".json")}'
    result_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == 'yaml':
        import yaml  # noqa: PLC0415

        result_path.write_text(
            yaml.dump(
                results, allow_unicode=True, sort_keys=False, default_flow_style=False
            ),
            encoding='utf-8',
        )

    elif fmt in ('csv', 'parquet'):
        import pandas as pd  # noqa: PLC0415

        rows = []
        for record in results:
            row: dict[str, Any] = {_SOURCE_COL: record.get('file', '')}
            row.update(record.get('structured') or {})
            rows.append(row)

        df = pd.DataFrame(rows)
        if fmt == 'csv':
            df.to_csv(result_path, index=False)
        else:
            df.to_parquet(result_path, index=False, engine='pyarrow')

    else:
        result_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8'
        )

    return result_path


def read_results(result_path: Path) -> list[dict[str, Any]]:
    suffix = result_path.suffix.lower()

    if suffix == '.yaml':
        import yaml  # noqa: PLC0415

        data = yaml.safe_load(result_path.read_text(encoding='utf-8'))
        return list(data) if data else []

    if suffix == '.csv':
        import pandas as pd  # noqa: PLC0415

        df = pd.read_csv(result_path)
        return _tabular_to_records(df)

    if suffix == '.parquet':
        import pandas as pd  # noqa: PLC0415

        df = pd.read_parquet(result_path, engine='pyarrow')
        return _tabular_to_records(df)

    return list(json.loads(result_path.read_text(encoding='utf-8')))


def _tabular_to_records(df: Any) -> list[dict[str, Any]]:
    records = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        source_file = str(row_dict.pop(_SOURCE_COL, ''))
        records.append({'file': source_file, 'structured': row_dict})
    return records
