"""Phân tích ý định truy vấn: tỉnh/thành, trường thông tin, so sánh/xếp hạng, chặn ngoài phạm vi.

Nguyên tắc chống hallucination: chỉ nhận diện những gì CÓ trong dữ liệu.
Mọi tín hiệu ngoài phạm vi (tỉnh khác, chủ đề khác, năm khác, xin tư vấn,
prompt injection) -> đánh dấu out_of_scope để engine trả fallback.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .text_utils import (
    contains_phrase,
    has_diacritics,
    lower_clean,
    remove_phrase,
    strip_accents,
)

DATA_YEAR = "2026"

PROVINCE_ALIASES: dict[str, list[str]] = {
    "BN": ["bắc ninh"],
    "HP": ["hải phòng", "đình vũ cát hải", "đình vũ", "cát hải"],
    "BD": ["bình dương", "vsip"],
}

# Địa danh sáp nhập: chỉ chấp nhận khi đi kèm tỉnh tương ứng trong dữ liệu
# (dữ liệu KHÔNG bao phủ KCN của địa phương cũ này).
MERGER_PARTNERS: dict[str, list[str]] = {
    "BN": ["bắc giang"],
    "HP": ["hải dương"],
    "BD": ["thành phố hồ chí minh", "hồ chí minh", "tp hcm", "tphcm", "hcm", "sài gòn"],
}

OTHER_PROVINCES = [
    "hà nội", "đà nẵng", "cần thơ", "huế", "thừa thiên huế", "quảng ninh", "hưng yên",
    "thái bình", "hà nam", "nam định", "ninh bình", "vĩnh phúc", "phú thọ", "thái nguyên",
    "lạng sơn", "cao bằng", "hà giang", "tuyên quang", "lào cai", "yên bái", "điện biên",
    "lai châu", "sơn la", "hòa bình", "bắc kạn", "thanh hóa", "nghệ an", "hà tĩnh",
    "quảng bình", "quảng trị", "quảng nam", "quảng ngãi", "bình định", "phú yên",
    "khánh hòa", "ninh thuận", "bình thuận", "kon tum", "gia lai", "đắk lắk", "đắk nông",
    "lâm đồng", "bình phước", "tây ninh", "đồng nai", "bà rịa vũng tàu", "vũng tàu",
    "long an", "tiền giang", "bến tre", "trà vinh", "vĩnh long", "đồng tháp", "an giang",
    "kiên giang", "hậu giang", "sóc trăng", "bạc liêu", "cà mau",
]

FIELD_KEYWORDS: dict[str, list[str]] = {
    "land": ["giá thuê", "thuê đất", "giá đất", "tiền thuê", "cho thuê", "đất kcn",
             "đất công nghiệp", "land", "rent", "usd m2"],
    "wage": ["lương", "tiền lương", "mức lương", "lương tối thiểu", "nhân công",
             "chi phí lao động", "wage", "salary"],
    "cit": ["thuế tndn", "tndn", "thuế thu nhập doanh nghiệp", "thuế suất phổ thông",
            "thuế phổ thông", "cit", "corporate income tax"],
    "incentive": ["ưu đãi", "miễn thuế", "giảm thuế", "miễn giảm", "công nghệ cao",
                  "thuế suất ưu đãi", "incentive", "tax holiday"],
    "infra": ["hạ tầng", "sân bay", "cảng", "cảng biển", "cao tốc", "logistics",
              "chuỗi cung ứng", "kết nối", "giao thông", "infrastructure", "airport", "port"],
    "region": ["vị trí", "vùng kinh tế", "ở đâu", "nằm ở", "thuộc vùng", "location", "region"],
    "admin": ["sáp nhập", "hợp nhất", "địa giới", "tên mới", "merge", "merger"],
}
GENERIC_TAX = ["thuế", "tax"]
# Cụm "thuê" (đất) cần loại trước khi dò "thue" chung ở chế độ không dấu
LAND_PLAIN_PHRASES = ["gia thue", "thue dat", "tien thue", "cho thue", "di thue", "thue kcn"]

SUPERLATIVE_MIN = ["rẻ nhất", "thấp nhất", "ít nhất", "cheapest", "lowest"]
SUPERLATIVE_MAX = ["cao nhất", "đắt nhất", "nhiều nhất", "highest", "most expensive"]
COMPARE = ["so sánh", "khác nhau", "khác biệt", "compare", "versus", "vs"]
OVERVIEW = ["thông tin", "tổng quan", "giới thiệu", "chính sách", "tóm tắt", "overview"]

OUT_OF_SCOPE = [
    # chủ đề không có trong dữ liệu
    "giá điện", "tiền điện", "điện năng", "giá nước", "nước sạch", "vat", "gtgt",
    "giá trị gia tăng", "nhập khẩu", "xuất khẩu", "tncn", "thu nhập cá nhân", "thuế đất",
    "tiền sử dụng đất", "nhà xưởng", "kho bãi", "văn phòng", "visa", "thị thực",
    "giấy phép lao động", "số dự án", "số lượng dự án", "vốn fdi", "vốn đăng ký",
    "vốn đầu tư", "tổng vốn", "tỷ giá", "lãi suất", "bảo hiểm xã hội", "bhxh",
    "dự báo", "tương lai", "năm sau", "năm tới",
    # xin tư vấn / suy diễn
    "nên đầu tư", "nên chọn", "có nên", "tốt nhất", "lời khuyên", "khuyên", "tư vấn",
    "nên đặt",
    # prompt injection
    "bỏ qua", "ignore", "bịa", "giả sử", "tưởng tượng", "đoán", "ước tính",
]

# Từ không dấu dễ nhầm (thuê/thuế, lương/lượng, cảng/càng, huế/huệ)
AMBIGUOUS_PLAIN_WORDS = {"thue", "luong", "cang", "hue"}
PLAIN_NEGATIVE_PHRASES = [
    "so luong", "chat luong", "san luong", "khoi luong", "nang luong", "luu luong",
    "dung luong", "cang ngay", "cang tot", "cang re", "cang cao", "cang nhieu", "cang it",
]

STOPWORDS = set(
    """la bao nhieu the nao nhu cua o tai va voi cho toi biet hay gi khong co duoc hien
    nay nam 2026 tinh thanh pho tp muc ve xin vui long giup minh em anh chi ban cac nhung
    sao tro ly fdi dau tu kcn khu cong nghiep doanh nha du an trung binh khoang hon nhat
    re dat cao thap it nhieu giua hoac thi may ra bay gio so lam nhe a vay day kia muon
    can hoi cau tra loi oi nhi what is are the in of how much which province and vs
    sanh thong tin tong quan chinh sach dang moi nguoi gom nhung loai mot hai ba""".split()
)

_YEAR_RE = re.compile(r"(?<![\d/])(19|20)\d{2}(?![\d/])")


@dataclass
class QueryIntent:
    provinces: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    superlative: str | None = None  # "min" | "max"
    compare: bool = False
    leftover_tokens: list[str] = field(default_factory=list)
    out_of_scope: bool = False
    reason: str = ""


class _Matcher:
    def __init__(self, query: str) -> None:
        self.lower = lower_clean(query)
        self.diacritic_mode = has_diacritics(query)
        plain = strip_accents(self.lower)
        if not self.diacritic_mode:
            for neg in PLAIN_NEGATIVE_PHRASES:
                plain = remove_phrase(plain, neg)
        self.plain = plain
        self.residual = plain  # phần còn lại sau khi gỡ các cụm đã nhận diện

    @staticmethod
    def _is_ambiguous(kw: str) -> bool:
        kw_lower = lower_clean(kw)
        kw_plain = strip_accents(kw_lower)
        return kw_lower != kw_plain and bool(AMBIGUOUS_PLAIN_WORDS & set(kw_plain.split()))

    def match(self, kw: str, strict: bool = False) -> bool:
        """strict=True: từ khóa mơ hồ (thuế/thuê...) chỉ khớp bản CÓ dấu."""
        kw_lower = lower_clean(kw)
        if contains_phrase(self.lower, kw_lower):
            return True
        kw_plain = strip_accents(kw_lower)
        if contains_phrase(self.plain, kw_plain):
            if self.diacritic_mode or strict:
                return not self._is_ambiguous(kw)
            return True
        return False

    def match_any(self, kws: list[str], consume: bool = True, strict: bool = False) -> bool:
        hit = False
        # cụm dài trước để gỡ trọn vẹn
        for kw in sorted(kws, key=len, reverse=True):
            if self.match(kw, strict=strict):
                hit = True
                if consume:
                    self.residual = remove_phrase(self.residual, strip_accents(lower_clean(kw)))
        return hit


def _has_foreign_year(raw: str) -> bool:
    return any(m.group(0) != DATA_YEAR for m in _YEAR_RE.finditer(raw))


def parse_query(query: str) -> QueryIntent:
    intent = QueryIntent()
    raw = unicodedata.normalize("NFC", query)
    m = _Matcher(raw)

    def oos(reason: str) -> QueryIntent:
        intent.out_of_scope, intent.reason = True, reason
        return intent

    if not m.plain or not re.search(r"\w", m.plain):
        return oos("empty")
    if _has_foreign_year(raw):
        return oos("year")
    if m.match_any(OUT_OF_SCOPE, consume=False, strict=True):
        return oos("topic")

    for pid, aliases in PROVINCE_ALIASES.items():
        if m.match_any(aliases):
            intent.provinces.append(pid)
    for pid, partners in MERGER_PARTNERS.items():
        if m.match_any(partners):
            if pid not in intent.provinces:
                return oos("merged_area_not_covered")
    if m.match_any(OTHER_PROVINCES, consume=False):
        return oos("province")

    if m.match_any(SUPERLATIVE_MIN):
        intent.superlative = "min"
    elif m.match_any(SUPERLATIVE_MAX):
        intent.superlative = "max"
    intent.compare = m.match_any(COMPARE)
    m.match_any(OVERVIEW)

    for fname, kws in FIELD_KEYWORDS.items():
        if m.match_any(kws):
            intent.fields.append(fname)

    if "cit" not in intent.fields and "incentive" not in intent.fields:
        if m.diacritic_mode:
            generic_tax = m.match("thuế") or m.match("tax")
        else:
            stripped = m.plain
            for p in LAND_PLAIN_PHRASES:
                stripped = remove_phrase(stripped, p)
            generic_tax = contains_phrase(stripped, "thue") or contains_phrase(stripped, "tax")
        if generic_tax:
            intent.fields += ["cit", "incentive"]
    m.match_any(GENERIC_TAX)

    intent.leftover_tokens = [t for t in m.residual.split() if t not in STOPWORDS]
    return intent
