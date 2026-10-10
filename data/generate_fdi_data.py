"""
Bước 1 - Data: Sinh file fdi_data.csv cho "Trợ lý phân tích & so sánh chính sách FDI".

- Chỉ dùng thư viện chuẩn (csv, pathlib) -> chạy được ở Local / Streamlit Cloud / Render.
- Dữ liệu do người dùng cung cấp (chuẩn hóa 2026): is_mock=False, updated_at="Năm 2026".
- Lương tối thiểu vùng theo Nghị định 293/2025/NĐ-CP (thay thế NĐ 74/2024/NĐ-CP).
- Script tự validate trước khi ghi file; vi phạm -> raise ValueError, không ghi file lỗi.

Chạy:  python data/generate_fdi_data.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent / "fdi_data.csv"
ENCODING = "utf-8-sig"  # BOM để Excel hiển thị đúng tiếng Việt

UPDATED_AT = "Năm 2026"
WAGE_DECREE = "Nghị định 293/2025/NĐ-CP"
# Bảng lương tối thiểu vùng 2026 chuẩn (dùng để chặn nhập nhầm số cũ NĐ 74/2024)
OFFICIAL_MIN_WAGE_2026 = {"Vùng I": 5_310_000, "Vùng II": 4_730_000}
DEPRECATED_WAGES = {4_960_000, 4_410_000, 3_860_000, 3_450_000}  # mức NĐ 74/2024

CHINHPHU_URL = "https://chinhphu.vn"

# Thứ tự cột = schema chính thức (các cột validation mục B ở cuối)
COLUMNS = [
    "id",
    "province",
    "province_note",
    "zone_detail",
    "economic_region",
    "land_price_min_usd",
    "land_price_max_usd",
    "land_price_unit",
    "land_price_source",
    "min_wage_region",
    "min_wage_vnd",
    "min_wage_legal_basis",
    "cit_standard_pct",
    "incentive_type",
    "incentive_cit_rate_pct",
    "incentive_rate_years",
    "tax_exemption_years",
    "tax_reduction_pct",
    "tax_reduction_years",
    "incentive_summary",
    "infrastructure_highlights",
    "source",
    "source_url",
    "updated_at",
    "is_mock",
]
REQUIRED_VALIDATION_COLUMNS = ["source", "source_url", "updated_at", "is_mock"]

RECORDS: list[dict] = [
    {
        "id": "BN",
        "province": "Bắc Ninh",
        "province_note": "Bắc Ninh (sau sáp nhập với Bắc Giang)",
        "zone_detail": "Các KCN tỉnh Bắc Ninh",
        "economic_region": "Vùng Kinh tế trọng điểm Bắc Bộ",
        "land_price_min_usd": 155,
        "land_price_max_usd": 175,
        "land_price_unit": "USD/m2/chu kỳ thuê",
        "land_price_source": "JLL/Savills",
        "min_wage_region": "Vùng II",
        "min_wage_vnd": 4_730_000,
        "min_wage_legal_basis": WAGE_DECREE,
        "cit_standard_pct": 20,
        "incentive_type": "Dự án Công nghệ cao",
        "incentive_cit_rate_pct": 10,
        "incentive_rate_years": 15,
        "tax_exemption_years": 4,
        "tax_reduction_pct": 50,
        "tax_reduction_years": 9,
        "incentive_summary": (
            "Thuế suất 10% trong 15 năm; Miễn thuế 4 năm đầu, "
            "giảm 50% trong 9 năm tiếp theo."
        ),
        "infrastructure_highlights": (
            "Cách sân bay Nội Bài 30km; trung tâm chuỗi cung ứng điện tử khu vực "
            "(Samsung, Amkor, Goertek)."
        ),
        "source": "Báo cáo JLL & Cổng Thông tin Chính phủ",
        "source_url": f"https://www.jll.com.vn | {CHINHPHU_URL}",
    },
    {
        "id": "HP",
        "province": "Hải Phòng",
        "province_note": "Hải Phòng (sau sáp nhập với Hải Dương)",
        "zone_detail": "Khu kinh tế Đình Vũ - Cát Hải",
        "economic_region": "Vùng Kinh tế trọng điểm Bắc Bộ",
        "land_price_min_usd": 120,
        "land_price_max_usd": 137,
        "land_price_unit": "USD/m2/chu kỳ thuê",
        "land_price_source": "Cổng TTĐT TP. Hải Phòng",
        "min_wage_region": "Vùng I",
        "min_wage_vnd": 5_310_000,
        "min_wage_legal_basis": WAGE_DECREE,
        "cit_standard_pct": 20,
        "incentive_type": "Đặc thù Khu kinh tế",
        "incentive_cit_rate_pct": 10,
        "incentive_rate_years": 15,
        "tax_exemption_years": 4,
        "tax_reduction_pct": 50,
        "tax_reduction_years": 9,
        "incentive_summary": (
            "Thuế suất 10% trong 15 năm; Miễn thuế 4 năm, "
            "giảm 50% số thuế trong 9 năm tiếp theo."
        ),
        "infrastructure_highlights": (
            "Cảng nước sâu Lạch Huyện; sân bay quốc tế Cát Bi; "
            "kết nối cao tốc Hà Nội - Hải Phòng."
        ),
        "source": "Cổng TTĐT TP. Hải Phòng & Cổng Thông tin Chính phủ",
        "source_url": f"https://haiphong.gov.vn | {CHINHPHU_URL}",
    },
    {
        "id": "BD",
        "province": "Bình Dương",
        "province_note": "Bình Dương (nay thuộc TP.HCM)",
        "zone_detail": "Các KCN tỉnh Bình Dương (mạng lưới VSIP)",
        "economic_region": "Vùng Kinh tế trọng điểm phía Nam",
        "land_price_min_usd": 175,
        "land_price_max_usd": 220,
        "land_price_unit": "USD/m2/chu kỳ thuê",
        "land_price_source": "CBRE",
        "min_wage_region": "Vùng I",
        "min_wage_vnd": 5_310_000,
        "min_wage_legal_basis": WAGE_DECREE,
        "cit_standard_pct": 20,
        "incentive_type": "Dự án Công nghệ cao",
        "incentive_cit_rate_pct": 10,
        "incentive_rate_years": 15,
        "tax_exemption_years": 4,
        "tax_reduction_pct": 50,
        "tax_reduction_years": 9,
        "incentive_summary": (
            "Thuế suất 10% trong 15 năm; Miễn thuế 4 năm đầu, "
            "giảm 50% trong 9 năm tiếp theo."
        ),
        "infrastructure_highlights": (
            "Hệ sinh thái công nghiệp phụ trợ phát triển nhất cả nước; "
            "mạng lưới KCN VSIP; tiếp giáp TP.HCM."
        ),
        "source": "Báo cáo CBRE & Cổng Thông tin Chính phủ",
        "source_url": f"https://www.cbrevietnam.com | {CHINHPHU_URL}",
    },
]

# Gán cột validation bắt buộc (mục B) cho dữ liệu thật do người dùng cung cấp
for _r in RECORDS:
    _r["updated_at"] = UPDATED_AT
    _r["is_mock"] = False


def validate(records: list[dict]) -> list[str]:
    """Trả về danh sách lỗi (rỗng = hợp lệ)."""
    errors: list[str] = []
    if not records:
        return ["Không có bản ghi nào."]

    ids = [r.get("id") for r in records]
    if len(ids) != len(set(ids)):
        errors.append("Trùng id.")

    for r in records:
        rid = r.get("id", "?")
        missing = [c for c in COLUMNS if c not in r]
        extra = [c for c in r if c not in COLUMNS]
        if missing:
            errors.append(f"[{rid}] thiếu cột: {missing}")
        if extra:
            errors.append(f"[{rid}] cột ngoài schema: {extra}")
        empty = [c for c in COLUMNS if c in r and (r[c] is None or str(r[c]).strip() == "")]
        if empty:
            errors.append(f"[{rid}] giá trị rỗng: {empty}")

        if r.get("is_mock") is not False:
            errors.append(f"[{rid}] is_mock phải là False.")
        if r.get("updated_at") != UPDATED_AT:
            errors.append(f"[{rid}] updated_at phải là '{UPDATED_AT}'.")

        urls = [u.strip() for u in str(r.get("source_url", "")).split("|")]
        if not all(u.startswith("https://") for u in urls):
            errors.append(f"[{rid}] source_url phải là https: {urls}")

        lo, hi = r.get("land_price_min_usd"), r.get("land_price_max_usd")
        if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and 0 < lo <= hi):
            errors.append(f"[{rid}] giá thuê đất không hợp lệ: {lo}-{hi}")

        region, wage = r.get("min_wage_region"), r.get("min_wage_vnd")
        if wage in DEPRECATED_WAGES:
            errors.append(f"[{rid}] dùng mức lương cũ NĐ 74/2024: {wage}")
        if OFFICIAL_MIN_WAGE_2026.get(region) != wage:
            errors.append(f"[{rid}] lương {wage} không khớp {WAGE_DECREE} cho {region}")
        if r.get("min_wage_legal_basis") != WAGE_DECREE:
            errors.append(f"[{rid}] căn cứ lương phải là {WAGE_DECREE}")

        for c in ("cit_standard_pct", "incentive_cit_rate_pct", "tax_reduction_pct"):
            v = r.get(c)
            if not (isinstance(v, (int, float)) and 0 <= v <= 100):
                errors.append(f"[{rid}] {c} ngoài khoảng 0-100: {v}")
        if r.get("incentive_cit_rate_pct", 0) > r.get("cit_standard_pct", 0):
            errors.append(f"[{rid}] thuế ưu đãi > thuế phổ thông")
    return errors


def write_csv(records: list[dict], path: Path = OUTPUT_PATH) -> Path:
    errors = validate(records)
    if errors:
        raise ValueError("Dữ liệu không hợp lệ:\n- " + "\n- ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=ENCODING, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(records)
    return path


def main() -> int:
    # Console Windows mặc định cp1252 -> in tiếng Việt bị UnicodeEncodeError
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:
        out = write_csv(RECORDS)
    except (ValueError, OSError) as exc:
        print(f"[LỖI] {exc}", file=sys.stderr)
        return 1
    print(f"[OK] Đã ghi {len(RECORDS)} bản ghi, {len(COLUMNS)} cột -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
