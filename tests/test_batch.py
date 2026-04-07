import csv

from bharataddress import parse_batch, parse_csv


def test_parse_batch_returns_list_in_order():
    out = parse_batch([
        "Sector 31, Gurgaon 122001",
        "Anna Salai, Chennai 600002",
    ])
    assert len(out) == 2
    assert out[0].pincode == "122001"
    assert out[1].pincode == "600002"


def test_parse_batch_handles_empty_and_non_string():
    out = parse_batch(["", None, "Sector 31, Gurgaon 122001"])  # type: ignore[list-item]
    assert len(out) == 3
    assert out[2].pincode == "122001"


def test_parse_csv_writes_parsed_columns(tmp_path):
    src = tmp_path / "in.csv"
    with src.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "address"])
        w.writerow(["1", "Sector 31, Gurgaon 122001"])
        w.writerow(["2", "Anna Salai, Chennai 600002"])

    out_path = parse_csv(src, column="address")
    assert out_path.exists()
    with out_path.open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["parsed_pincode"] == "122001"
    assert rows[0]["parsed_state"] == "Haryana"
    assert rows[1]["parsed_pincode"] == "600002"


def test_parse_csv_missing_column_raises(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("id,foo\n1,bar\n", encoding="utf-8")
    try:
        parse_csv(src, column="address")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
