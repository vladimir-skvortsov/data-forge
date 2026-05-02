import json


def deduplicate(results: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for record in results:
        key = json.dumps(record.get('structured'), sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


def remove_outliers(results: list[dict]) -> list[dict]:
    import numpy as np
    from sklearn.ensemble import IsolationForest

    structured = [r.get('structured') or {} for r in results]
    if len(structured) < 3:  # not enough samples for IsolationForest
        return results

    # Collect all numeric fields present across all records
    numeric_keys = {
        k for rec in structured for k, v in rec.items() if isinstance(v, int | float)
    }
    if not numeric_keys:
        return results

    matrix = np.array(
        [[float(rec.get(k, 0)) for k in sorted(numeric_keys)] for rec in structured]
    )

    clf = IsolationForest(contamination='auto', random_state=42)
    labels = clf.fit_predict(matrix)  # 1 = inlier, -1 = outlier

    return [r for r, label in zip(results, labels) if label == 1]
