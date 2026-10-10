# QA – ISO/IEC 25010 & User Test

## 1. Checklist ISO/IEC 25010
| Tiêu chí | Acceptance | Bằng chứng | Trạng thái |
|---|---|---|---|
| Functional suitability | 100% test pass | `pytest tests` → **65/65 passed** (14 data + 51 RAG) | ✅ |
| Performance – query | < 5s | `Answer.latency_ms` 0,4–12 ms; TC-R24 assert < 500 ms | ✅ |
| Performance – load | < 3s | Render script server-side **1,38s** (AppTest, cold, local). Cần đo Lighthouse trên link public | ⏳ đo sau deploy |
| Compatibility | Chrome, Safari, 375px | Chrome DevTools → iPhone SE (375px); Safari iOS thật. Chụp 3 ảnh làm bằng chứng | ⏳ test tay |
| Usability (WCAG 2.1 AA) | contrast ≥ 4.5:1, bàn phím, alt text | Text `#1a1a1a`/nền trắng ≈ 17:1; focus outline; caption mô tả biểu đồ. Lighthouse Accessibility ≥ 90 | ⏳ đo Lighthouse |
| Reliability | không crash | try/except trong `FDIAssistant.answer`; TC-R13 (None, rỗng, emoji, 10k ký tự) pass; `DataError` → `st.error` | ✅ |
| Security | không PII, key trong `.env` | Không gọi API ngoài → không cần key; `.env` trong `.gitignore`; chat chỉ lưu `session_state`; không log query; `gatherUsageStats=false` | ✅ |
| Maintainability | tách module, README | `core/` (text_utils, data_loader, intent, retriever, rag_engine), `data/`, `tests/`, README.md | ✅ |
| Portability | Local, Streamlit Cloud, Render | Local ✅ (uv). `requirements.txt` ghim phiên bản, `render.yaml` | ⏳ sau deploy |

**Cách đo Lighthouse:** Chrome → F12 → Lighthouse → Mobile → Performance + Accessibility → Analyze. Ghi lại: FCP, LCP (< 3s), điểm Accessibility. Chụp ảnh màn hình làm bằng chứng.

## 2. Kịch bản User Test (5 người)
**Đối tượng gợi ý:** 2 sinh viên kinh tế/luật, 1 nhân viên HR/kế toán, 1 người làm BĐS/KCN, 1 người không chuyên.
**Quy trình:** gửi link → bấm giờ từng task → người dùng tự làm, không hướng dẫn → hỏi điểm hài lòng ngay sau task → ghi lỗi. Không thu thập tên/SĐT (dùng mã U1–U5).

| Task | Nội dung | Thành công khi | Mục tiêu |
|---|---|---|---|
| T1 | Tìm tỉnh có giá thuê đất rẻ nhất | Nói đúng "Hải Phòng" | < 60s |
| T2 | Tìm lương tối thiểu vùng Bắc Ninh | Nói đúng 4.730.000 VNĐ | < 60s |
| T3 | Hỏi chatbot về ưu đãi thuế Bình Dương & chỉ ra nguồn | Đọc được dòng `[Nguồn: ...]` | < 90s |
| T4 | Hỏi chatbot 1 tỉnh ngoài dữ liệu (vd Đà Nẵng) | Nhận câu fallback, hiểu là không có data | < 60s |
| T5 | Mở app trên điện thoại, xem bảng so sánh | Đọc được bảng, không vỡ layout | < 60s |

**Phiếu ghi nhận (mỗi người 1 dòng/task):**
| User | Task | Thời gian (s) | Hoàn thành (Y/N) | Hài lòng (1-5) | Lỗi gặp phải | Thiết bị/Trình duyệt |
|---|---|---|---|---|---|---|
| U1 | T1 | | | | | |

**Chỉ số tổng hợp:** tỉ lệ hoàn thành (mục tiêu ≥ 90%), thời gian TB/task, điểm hài lòng TB (mục tiêu ≥ 4,0), số lỗi theo mức P0/P1/P2.

## 3. Phân loại lỗi & SLA fix
| Mức | Định nghĩa | Ví dụ | Xử lý |
|---|---|---|---|
| P0 | Sai số liệu, thiếu citation, crash, link chết | Trả lời số không có trong CSV | Fix ngay, trong ngày 10/10 |
| P1 | Không trả lời được câu hợp lệ, lỗi hiển thị mobile | "giá đất BN" bị fallback | Fix trước khi nộp 11/10 |
| P2 | Thẩm mỹ, câu chữ, gợi ý cải tiến | Muốn thêm tỉnh | Ghi backlog / pitch "hạn chế" |
