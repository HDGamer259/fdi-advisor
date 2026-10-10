"""Nạp & kiểm tra fdi_data.csv, ánh xạ nguồn trích dẫn theo từng trường."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "fdi_data.csv"

REQUIRED_COLUMNS = {
    "id", "province", "province_note", "zone_detail", "economic_region",
    "land_price_min_usd", "land_price_max_usd", "land_price_unit", "land_price_source",
    "min_wage_region", "min_wage_vnd", "min_wage_legal_basis", "cit_standard_pct",
    "incentive_type", "incentive_cit_rate_pct", "incentive_rate_years",
    "tax_exemption_years", "tax_reduction_pct", "tax_reduction_years",
    "incentive_summary", "infrastructure_highlights",
    "source", "source_url", "updated_at", "is_mock",
}

# Vai trò nguồn của từng trường thông tin:
#  - "market": báo cáo thị trường / cổng địa phương (phần tử ĐẦU trong source/source_url)
#  - "legal" : văn bản pháp lý - Cổng TT Chính phủ (phần tử CUỐI)
FIELD_SOURCE_ROLE = {
    "region": "market",
    "land": "market",
    "infra": "market",
    "wage": "legal",
    "cit": "legal",
    "incentive": "legal",
    "admin": "legal",
}

SOURCE_NAME_SEP = " & "
SOURCE_URL_SEP = "|"


class DataError(Exception):
    """Lỗi dữ liệu đầu vào (thiếu file, sai schema, sai kiểu)."""


@dataclass(frozen=True)
class SourceRef:
    name: str
    url: str


@dataclass
class ProvinceRecord:
    id: str
    province: str
    province_note: str
    zone_detail: str
    economic_region: str
    land_price_min_usd: float
    land_price_max_usd: float
    land_price_unit: str
    land_price_source: str
    min_wage_region: str
    min_wage_vnd: int
    min_wage_legal_basis: str
    cit_standard_pct: float
    incentive_type: str
    incentive_cit_rate_pct: float
    incentive_rate_years: int
    tax_exemption_years: int
    tax_reduction_pct: float
    tax_reduction_years: int
    incentive_summary: str
    infrastructure_highlights: str
    source: str
    source_url: str
    updated_at: str
    is_mock: bool
    sources: dict[str, SourceRef] = field(default_factory=dict)

    def source_for(self, field_name: str) -> SourceRef:
        role = FIELD_SOURCE_ROLE.get(field_name, "market")
        return self.sources[role]


def parse_sources(source: str, source_url: str) -> dict[str, SourceRef]:
    """Ghép tên nguồn (tách ' & ') với URL (tách '|') theo vị trí.

    'Báo cáo JLL & Cổng Thông tin Chính phủ' + 'https://jll | https://chinhphu'
      -> market=(Báo cáo JLL, https://jll), legal=(Cổng TT Chính phủ, https://chinhphu)
    Nếu số lượng không khớp -> dùng nguyên chuỗi cho cả 2 vai trò (an toàn, không đoán).
    """
    names = [n.strip() for n in (source or "").split(SOURCE_NAME_SEP) if n.strip()]
    urls = [u.strip() for u in (source_url or "").split(SOURCE_URL_SEP) if u.strip()]
    if not names or not urls:
        raise DataError("source / source_url rỗng.")
    if len(names) != len(urls):
        whole = SourceRef(" & ".join(names), " | ".join(urls))
        return {"market": whole, "legal": whole}
    pairs = [SourceRef(n, u) for n, u in zip(names, urls)]
    return {"market": pairs[0], "legal": pairs[-1]}


def _to_bool(value: str) -> bool:
    v = str(value).strip().lower()
    if v in {"true", "1", "yes"}:
        return True
    if v in {"false", "0", "no"}:
        return False
    raise DataError(f"is_mock không hợp lệ: {value!r}")


def _row_to_record(row: dict) -> ProvinceRecord:
    try:
        rec = ProvinceRecord(
            id=row["id"].strip(),
            province=row["province"].strip(),
            province_note=row["province_note"].strip(),
            zone_detail=row["zone_detail"].strip(),
            economic_region=row["economic_region"].strip(),
            land_price_min_usd=float(row["land_price_min_usd"]),
            land_price_max_usd=float(row["land_price_max_usd"]),
            land_price_unit=row["land_price_unit"].strip(),
            land_price_source=row["land_price_source"].strip(),
            min_wage_region=row["min_wage_region"].strip(),
            min_wage_vnd=int(row["min_wage_vnd"]),
            min_wage_legal_basis=row["min_wage_legal_basis"].strip(),
            cit_standard_pct=float(row["cit_standard_pct"]),
            incentive_type=row["incentive_type"].strip(),
            incentive_cit_rate_pct=float(row["incentive_cit_rate_pct"]),
            incentive_rate_years=int(row["incentive_rate_years"]),
            tax_exemption_years=int(row["tax_exemption_years"]),
            tax_reduction_pct=float(row["tax_reduction_pct"]),
            tax_reduction_years=int(row["tax_reduction_years"]),
            incentive_summary=row["incentive_summary"].strip(),
            infrastructure_highlights=row["infrastructure_highlights"].strip(),
            source=row["source"].strip(),
            source_url=row["source_url"].strip(),
            updated_at=row["updated_at"].strip(),
            is_mock=_to_bool(row["is_mock"]),
        )
    except (KeyError, ValueError, AttributeError) as exc:
        raise DataError(f"Bản ghi lỗi ({row.get('id', '?')}): {exc}") from exc
    rec.sources = parse_sources(rec.source, rec.source_url)
    return rec


def load_records(path: Path | str = DEFAULT_CSV) -> list[ProvinceRecord]:
    path = Path(path)
    if not path.is_file():
        raise DataError(f"Không tìm thấy file dữ liệu: {path}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise DataError(f"Thiếu cột: {sorted(missing)}")
            records = [_row_to_record(r) for r in reader]
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise DataError(f"Không đọc được CSV: {exc}") from exc
    if not records:
        raise DataError("File dữ liệu rỗng.")
    return records
