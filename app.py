"""Streamlit UI - Trợ lý phân tích & so sánh chính sách FDI. Chạy: streamlit run app.py"""
import altair as alt
import pandas as pd
import streamlit as st

from core import FDIAssistant
from core.data_loader import DataError

DISCLAIMER = ("Dữ liệu tổng hợp từ báo cáo thị trường Savills, CBRE, JLL và quy định hiện hành. "
              "Giá thuê đất và ưu đãi thuế mang tính chất tham khảo, có thể thay đổi tùy KCN, loại dự án, "
              "thời điểm ký hợp đồng và chính sách từng địa phương. "
              "Ứng dụng không thay thế tư vấn pháp lý/đầu tư.")
SUGGESTIONS = ["Tỉnh nào có giá thuê đất rẻ nhất?", "So sánh lương tối thiểu các tỉnh",
               "Ưu đãi thuế công nghệ cao ở Bắc Ninh", "Hạ tầng Hải Phòng có gì nổi bật?"]

st.set_page_config(page_title="Trợ lý FDI Việt Nam", page_icon="🏭", layout="wide")
# Mobile 375px + WCAG: chữ tối trên nền sáng (contrast > 4.5:1), vùng chạm >= 44px, focus rõ
st.markdown("""<style>
.block-container{padding:1rem 1rem 3rem;max-width:1100px}
html,body,[class*="css"]{font-size:16px;color:#1a1a1a}
button{min-height:44px} button:focus-visible{outline:3px solid #0b57d0!important}
.disc{font-size:.85rem;color:#3c3c3c;background:#f3f4f6;border-left:4px solid #0b57d0;padding:.75rem;border-radius:6px}
@media(max-width:640px){h1{font-size:1.5rem!important}.block-container{padding:.5rem .5rem 3rem}}
</style>""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_bot():
    return FDIAssistant.from_csv()


def disclaimer():
    st.markdown(f'<p class="disc" role="note">⚠️ {DISCLAIMER}</p>', unsafe_allow_html=True)


try:
    bot = get_bot()
except DataError as e:
    st.error(f"Không tải được dữ liệu: {e}")
    st.stop()

recs = bot.records
st.title("🏭 Trợ lý so sánh chính sách FDI")
st.caption(f"Bắc Ninh · Hải Phòng · Bình Dương — cập nhật {recs[0].updated_at}")
tab_dash, tab_chat = st.tabs(["📊 So sánh", "💬 Hỏi đáp"])

with tab_dash:
    table = pd.DataFrame({r.province: {
        "Ghi chú địa giới": r.province_note,
        "Vùng kinh tế": r.economic_region,
        "Giá thuê đất (USD/m²/chu kỳ)": f"{r.land_price_min_usd:g} - {r.land_price_max_usd:g}",
        "Lương tối thiểu (VNĐ/tháng)": f"{r.min_wage_vnd:,}".replace(",", ".") + f" ({r.min_wage_region})",
        "Thuế TNDN phổ thông": f"{r.cit_standard_pct:g}%",
        "Ưu đãi thuế": f"{r.incentive_type}: {r.incentive_summary}",
        "Hạ tầng": r.infrastructure_highlights,
        "Nguồn": r.source,
    } for r in recs})
    st.dataframe(table, width="stretch")
    disclaimer()

    df = pd.DataFrame([{"Tỉnh": r.province, "Thấp": r.land_price_min_usd, "Cao": r.land_price_max_usd,
                        "Lương": r.min_wage_vnd} for r in recs])
    c1, c2 = st.columns(2)  # tự xếp dọc trên mobile
    with c1:
        st.subheader("Giá thuê đất KCN")
        st.altair_chart(alt.Chart(df, title="Khoảng giá USD/m²/chu kỳ thuê").mark_bar(size=22).encode(
            y=alt.Y("Tỉnh:N", sort="x", title=None), x=alt.X("Thấp:Q", title="USD/m²"), x2="Cao:Q",
            color=alt.value("#0b57d0"), tooltip=["Tỉnh", "Thấp", "Cao"]), width="stretch")
        st.caption("Biểu đồ: " + "; ".join(f"{r.Tỉnh} {r.Thấp:g}-{r.Cao:g} USD" for r in df.itertuples()))
    with c2:
        st.subheader("Lương tối thiểu vùng")
        st.altair_chart(alt.Chart(df, title="VNĐ/tháng (NĐ 293/2025/NĐ-CP)").mark_bar(size=22).encode(
            y=alt.Y("Tỉnh:N", sort="-x", title=None), x=alt.X("Lương:Q", title="VNĐ"),
            color=alt.value("#b3261e"), tooltip=["Tỉnh", alt.Tooltip("Lương:Q", format=",")]),
            width="stretch")
        st.caption("Biểu đồ: " + "; ".join(f"{r.Tỉnh} {r.Lương:,} VNĐ" for r in df.itertuples()))

with tab_chat:
    st.session_state.setdefault("msgs", [])  # chỉ lưu trong phiên, không ghi file (không lưu PII)
    cols = st.columns(2)
    picked = next((q for i, q in enumerate(SUGGESTIONS) if cols[i % 2].button(q, width="stretch")), None)
    query = st.chat_input("Hỏi về giá đất, lương, thuế, hạ tầng...") or picked
    if query:
        ans = bot.answer(query)
        st.session_state.msgs += [("user", query, None), ("assistant", ans.text, ans)]
    for role, text, ans in st.session_state.msgs:
        with st.chat_message(role):
            st.markdown(text.replace("\n", "  \n"))
            if ans and ans.citations:
                st.caption(" · ".join(f"[{c.name}]({c.url})" for c in ans.citations)
                           + f" · ⏱ {ans.latency_ms} ms")

st.divider()
disclaimer()
