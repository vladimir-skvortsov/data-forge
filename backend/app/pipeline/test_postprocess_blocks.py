from app.pipeline.postprocess_blocks import deduplicate, remove_outliers


def test_deduplicate_removes_exact_duplicates() -> None:
    records = [
        {'file': 'a.txt', 'structured': {'name': 'Alice', 'age': 30}},
        {'file': 'b.txt', 'structured': {'name': 'Alice', 'age': 30}},
        {'file': 'c.txt', 'structured': {'name': 'Bob', 'age': 25}},
    ]
    result = deduplicate(records)
    assert len(result) == 2
    names = {r['structured']['name'] for r in result}
    assert names == {'Alice', 'Bob'}


def test_deduplicate_preserves_order() -> None:
    records = [
        {'file': 'a', 'structured': {'x': 1}},
        {'file': 'b', 'structured': {'x': 2}},
        {'file': 'c', 'structured': {'x': 1}},
    ]
    result = deduplicate(records)
    assert [r['file'] for r in result] == ['a', 'b']


def test_deduplicate_empty_list() -> None:
    assert deduplicate([]) == []


def test_deduplicate_all_unique() -> None:
    records = [{'structured': {'x': i}} for i in range(5)]
    assert len(deduplicate(records)) == 5


def test_deduplicate_handles_null_structured() -> None:
    records = [
        {'file': 'a', 'structured': None},
        {'file': 'b', 'structured': None},
    ]
    result = deduplicate(records)
    assert len(result) == 1


def test_remove_outliers_filters_numeric_outliers() -> None:
    records = [
        {'structured': {'value': 10.0}},
        {'structured': {'value': 11.0}},
        {'structured': {'value': 10.5}},
        {'structured': {'value': 9.5}},
        {'structured': {'value': 1000.0}},  # outlier
    ]
    result = remove_outliers(records)
    values = [r['structured']['value'] for r in result]
    assert 1000.0 not in values
    assert len(result) < len(records)


def test_remove_outliers_too_few_samples_returns_all() -> None:
    records = [
        {'structured': {'value': 1.0}},
        {'structured': {'value': 2.0}},
    ]
    assert remove_outliers(records) == records


def test_remove_outliers_no_numeric_fields_returns_all() -> None:
    records = [
        {'structured': {'name': 'Alice'}},
        {'structured': {'name': 'Bob'}},
        {'structured': {'name': 'Charlie'}},
    ]
    assert remove_outliers(records) == records


def test_remove_outliers_empty_list() -> None:
    assert remove_outliers([]) == []
