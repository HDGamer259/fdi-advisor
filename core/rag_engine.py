"""RAG engine: truy hồi từ fdi_data.csv -> câu trả lời trích xuất có citation / fallback.

- KHÔNG dùng LLM sinh nội dung: mọi số liệu được lấy nguyên văn từ CSV và
  lắp vào template cố định -> loại bỏ hallucination.
- Mọi câu trả lời có dữ liệu kết thúc bằng: [Nguồn: <tên nguồn>, <ngày cập nhật>]
- Ngoài dữ liệu -> FALLBACK_MESSAGE (nguyên văn, không citation).
- Không log nội dung query (tránh lưu PII).
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .data_loader import DEFAULT_CSV, ProvinceRecord, load_records
from .intent import QueryIntent, parse_query
from .retriever import Chunk, Retriever
from .text_utils import format_vnd

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "Không đủ dữ liệu để trả lời. Vui lòng tham khảo thêm."
MAX_QUERY_CHARS = 500
DISTINCTIVE_MAX_DF = 3  # token xuất hiện trong <= 3 chunk mới coi là thực thể đặc trưng

OVERVIEW_FIELDS = ["region", "admin", "land", "wage", "cit", "incentive", "infra"]
COMPARE_DEFAULT_FIELDS = ["land", "wage", "cit", "incentive"]
SUPERLATIVE_DEFAULT_FIELDS = ["land", "wage"]
FIELD_ORDER = {f: i for i, f in enumerate(OVERVIEW_FIELDS)}

FIELD_LABELS = {
    "land": "Giá thuê đất KCN",
    "wage": "Lương tối thiểu vùng",
    "cit": "Thuế TNDN phổ thông",
    "incentive": "Thuế suất ưu đãi",
}


@dataclass(frozen=True)
class Citation:
    name: str
    url: str
    updated_at: str


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    provinces: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    is_fallback: bool = False
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def format_citation(citations: list[Citation]) -> str:
    """[Nguồn: A; B, Năm 2026] hoặc [Nguồn: A, d1; B, d2] nếu khác ngày."""
    dates = {c.updated_at for c in citations}
    if len(dates) == 1:
        names = "; ".join(dict.fromkeys(c.name for c in citations))
        return f"[Nguồn: {names}, {dates.pop()}]"
    parts = "; ".join(dict.fromkeys(f"{c.name}, {c.updated_at}" for c in citations))
    return f"[Nguồn: {parts}]"


def _num(x: float) -> str:
    return f"{x:g}"


def _label(r: ProvinceRecord) -> str:
    return r.province if r.zone_detail.startswith("Các KCN") else f"{r.province} ({r.zone_detail})"


def _value(fname: str, r: ProvinceRecord) -> str:
    if fname == "land":
        return f"{_num(r.land_price_min_usd)} - {_num(r.land_price_max_usd)} {r.land_price_unit}"
    if fname == "wage":
        return f"{r.min_wage_region} – {format_vnd(r.min_wage_vnd)} VNĐ/tháng"
    if fname == "cit":
        return f"{_num(r.cit_standard_pct)}%"
    if fname == "incentive":
        return f"{_num(r.incentive_cit_rate_pct)}% trong {r.incentive_rate_years} năm"
    raise KeyError(fname)


def _rank_key(fname: str, r: ProvinceRecord) -> float:
    if fname == "land":
        return (r.land_price_min_usd + r.land_price_max_usd) / 2
    if fname == "wage":
        return float(r.min_wage_vnd)
    if fname == "cit":
        return r.cit_standard_pct
    if fname == "incentive":
        return r.incentive_cit_rate_pct
    raise KeyError(fname)


def render_field(fname: str, r: ProvinceRecord) -> str:
    lbl = _label(r)
    if fname == "region":
        return f"{lbl} thuộc {r.economic_region}."
    if fname == "admin":
        return f"Lưu ý địa giới hành chính: {r.province_note}."
    if fname == "land":
        return f"Giá thuê đất KCN tại {lbl}: {_value('land', r)} (theo {r.land_price_source})."
    if fname == "wage":
        return (f"Lương tối thiểu vùng tại {lbl}: {_value('wage', r)} "
                f"(theo {r.min_wage_legal_basis}).")
    if fname == "cit":
        return f"Thuế TNDN phổ thông tại {lbl}: {_value('cit', r)}."
    if fname == "incentive":
        return f"Ưu đãi thuế TNDN ({r.incentive_type}) tại {lbl}: {r.incentive_summary}"
    if fname == "infra":
        return f"Điểm mạnh hạ tầng {lbl}: {r.infrastructure_highlights}"
    raise KeyError(fname)


class FDIAssistant:
    def __init__(self, records: list[ProvinceRecord]) -> None:
        self.records = records
        self.by_id = {r.id: r for r in records}
        chunks = [
            Chunk(r.id, f, render_field(f, r)) for r in records for f in OVERVIEW_FIELDS
        ]
        self.retriever = Retriever(chunks)

    @classmethod
    def from_csv(cls, path: Path | str = DEFAULT_CSV) -> "FDIAssistant":
        return cls(load_records(path))

    # ---------- public ----------
    def answer(self, query: object) -> Answer:
        start = time.perf_counter()
        try:
            result = self._answer(query)
        except Exception:  # Reliability: không bao giờ crash UI
            logger.exception("Lỗi xử lý truy vấn (len=%s)", len(str(query or "")))
            result = self._fallback()
        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return result

    # ---------- internal ----------
    @staticmethod
    def _fallback() -> Answer:
        return Answer(text=FALLBACK_MESSAGE, is_fallback=True)

    def _cite(self, r: ProvinceRecord, fname: str) -> Citation:
        src = r.source_for(fname)
        return Citation(src.name, src.url, r.updated_at)

    def _finalize(self, lines: list[str], pairs: list[tuple[ProvinceRecord, str]]) -> Answer:
        citations = list(dict.fromkeys(self._cite(r, f) for r, f in pairs))
        if not lines or not citations:
            return self._fallback()
        text = "\n".join(lines) + "\n\n" + format_citation(citations)
        return Answer(
            text=text,
            citations=citations,
            provinces=list(dict.fromkeys(r.id for r, _ in pairs)),
            fields=list(dict.fromkeys(f for _, f in pairs)),
        )

    def _answer(self, query: object) -> Answer:
        if not isinstance(query, str):
            return self._fallback()
        query = query[:MAX_QUERY_CHARS]
        intent = parse_query(query)
        if intent.out_of_scope:
            return self._fallback()

        provinces = [p for p in intent.provinces if p in self.by_id]
        fields = list(intent.fields)

        if intent.leftover_tokens:
            tokens = intent.leftover_tokens
            if fields:  # đã rõ trường -> chỉ bổ sung bằng thực thể đặc trưng (vd Samsung)
                tokens = [t for t in tokens
                          if self.retriever.token_df.get(t, 0) <= DISTINCTIVE_MAX_DF]
            hits = self.retriever.search(tokens, set(provinces) or None)
            if hits:
                best = hits[0].coverage
                hits = [h for h in hits if h.coverage == best]
                if not provinces:
                    provinces = list(dict.fromkeys(h.chunk.province_id for h in hits))
                fields += [h.chunk.field for h in hits if h.chunk.field not in fields]
            elif not fields:
                return self._fallback()  # có nội dung lạ, không có bằng chứng

        if intent.superlative:
            rankable = [f for f in fields if f in FIELD_LABELS] or (
                SUPERLATIVE_DEFAULT_FIELDS if not fields else []
            )
            if rankable:
                return self._rank(rankable, provinces, intent)

        if not fields:
            if not provinces and not intent.compare:
                return self._fallback()
            multi = intent.compare and len(provinces) != 1
            fields = COMPARE_DEFAULT_FIELDS if multi else OVERVIEW_FIELDS

        targets = [self.by_id[p] for p in provinces] or self.records
        fields.sort(key=lambda f: FIELD_ORDER.get(f, 99))
        return self._render(fields, targets)

    def _render(self, fields: list[str], targets: list[ProvinceRecord]) -> Answer:
        lines, pairs = [], []
        multi = len(targets) > 1
        for f in fields:
            for r in targets:
                lines.append(("- " if multi else "") + render_field(f, r))
                pairs.append((r, f))
        return self._finalize(lines, pairs)

    def _rank(self, fields: list[str], provinces: list[str], intent: QueryIntent) -> Answer:
        targets = [self.by_id[p] for p in provinces] or self.records
        if len(targets) < 2:
            targets = self.records
        lines, pairs = [], []
        for f in fields:
            label = FIELD_LABELS[f]
            ordered = sorted(targets, key=lambda r: _rank_key(f, r))
            values = {_rank_key(f, r) for r in ordered}
            for r in ordered:
                pairs.append((r, f))
            if len(values) == 1:
                lines.append(f"{label}: tất cả tỉnh/thành trong dữ liệu bằng nhau "
                             f"({_value(f, ordered[0])}).")
                continue
            pick = min(values) if intent.superlative == "min" else max(values)
            winners = [r for r in ordered if _rank_key(f, r) == pick]
            word = "thấp nhất" if intent.superlative == "min" else "cao nhất"
            names = ", ".join(r.province for r in winners)
            tie = " (đồng hạng)" if len(winners) > 1 else ""
            lines.append(f"{label} {word}: {names}{tie} – {_value(f, winners[0])}.")
            basis = " (theo trung bình khoảng giá)" if f == "land" else ""
            ranking = "; ".join(f"{i}. {r.province}: {_value(f, r)}"
                                for i, r in enumerate(ordered, 1))
            lines.append(f"Xếp hạng thấp → cao{basis}: {ranking}.")
        return self._finalize(lines, pairs)


if __name__ == "__main__":  # Demo CLI: python -m core.rag_engine
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    bot = FDIAssistant.from_csv()
    for q in sys.argv[1:] or ["Giá thuê đất Bắc Ninh?", "Giá điện Đà Nẵng?"]:
        a = bot.answer(q)
        print(f"Q: {q}\nA: {a.text}\n({a.latency_ms} ms)\n")
