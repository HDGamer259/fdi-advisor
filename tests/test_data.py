"""Test Bước 1 - Data. Chạy: python -m pytest tests/test_data.py -v"""
import copy
import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))

import generate_fdi_data as g  # noqa: E402


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    out = tmp_path_factory.mktemp("d") / "fdi_data.csv"
    g.write_csv(g.RECORDS, out)
    with out.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def by_id(data, rid):
    return next(r for r in data if r["id"] == rid)


# TC-D01
def test_validation_columns_present(rows):
    header, _ = rows
    for c in g.REQUIRED_VALIDATION_COLUMNS:
        assert c in header


# TC-D02
def test_three_provinces(rows):
    _, data = rows
    assert {r["province"] for r in data} == {"Bắc Ninh", "Hải Phòng", "Bình Dương"}


# TC-D03
def test_is_mock_false_and_updated_at(rows):
    _, data = rows
    assert all(r["is_mock"] == "False" for r in data)
    assert all(r["updated_at"] == "Năm 2026" for r in data)


# TC-D04 - số liệu khớp 100% đầu vào
@pytest.mark.parametrize(
    "rid,lo,hi,region,wage",
    [
        ("BN", "155", "175", "Vùng II", "4730000"),
        ("HP", "120", "137", "Vùng I", "5310000"),
        ("BD", "175", "220", "Vùng I", "5310000"),
    ],
)
def test_input_values(rows, rid, lo, hi, region, wage):
    _, data = rows
    r = by_id(data, rid)
    assert (r["land_price_min_usd"], r["land_price_max_usd"]) == (lo, hi)
    assert (r["min_wage_region"], r["min_wage_vnd"]) == (region, wage)
    assert r["min_wage_legal_basis"] == "Nghị định 293/2025/NĐ-CP"
    assert r["cit_standard_pct"] == "20"
    assert (r["incentive_cit_rate_pct"], r["incentive_rate_years"]) == ("10", "15")
    assert (r["tax_exemption_years"], r["tax_reduction_pct"], r["tax_reduction_years"]) == ("4", "50", "9")


# TC-D05
def test_source_urls(rows):
    _, data = rows
    assert "jll.com.vn" in by_id(data, "BN")["source_url"]
    assert "haiphong.gov.vn" in by_id(data, "HP")["source_url"]
    assert "cbrevietnam.com" in by_id(data, "BD")["source_url"]
    assert all("chinhphu.vn" in r["source_url"] for r in data)


# TC-D06 - không còn ô trống
def test_no_empty_cells(rows):
    _, data = rows
    assert all(str(v).strip() for r in data for v in r.values())


# TC-D07 - chặn số lương cũ NĐ 74/2024
def test_reject_deprecated_wage():
    bad = copy.deepcopy(g.RECORDS)
    bad[0]["min_wage_vnd"] = 4_410_000
    with pytest.raises(ValueError):
        g.write_csv(bad, Path("unused.csv"))


# TC-D08 - chặn is_mock sai / thiếu cột
def test_reject_bad_schema():
    bad = copy.deepcopy(g.RECORDS)
    bad[1]["is_mock"] = True
    del bad[2]["source"]
    errs = g.validate(bad)
    assert any("is_mock" in e for e in errs)
    assert any("thiếu cột" in e for e in errs)


# TC-D09 - danh sách rỗng
def test_reject_empty():
    assert g.validate([]) == ["Không có bản ghi nào."]


# TC-D10 - chú thích sáp nhập tỉnh (rủi ro P0)
@pytest.mark.parametrize(
    "rid,note",
    [
        ("BN", "Bắc Ninh (sau sáp nhập với Bắc Giang)"),
        ("HP", "Hải Phòng (sau sáp nhập với Hải Dương)"),
        ("BD", "Bình Dương (nay thuộc TP.HCM)"),
    ],
)
def test_province_note(rows, rid, note):
    header, data = rows
    assert "province_note" in header
    assert by_id(data, rid)["province_note"] == note
