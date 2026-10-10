# 🏭 Trợ lý so sánh chính sách FDI – Bắc Ninh · Hải Phòng · Bình Dương

So sánh giá thuê đất KCN, lương tối thiểu vùng (NĐ 293/2025/NĐ-CP), thuế TNDN & ưu đãi, hạ tầng. Chatbot RAG trích xuất, **mọi câu trả lời có citation**, ngoài dữ liệu → fallback (không suy diễn).

## Chạy local
```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest tests -v        # cần: pip install pytest
```

## Cấu trúc
```
app.py                 UI Streamlit (dashboard + chat + disclaimer)
core/text_utils.py     chuẩn hóa tiếng Việt có/không dấu
core/data_loader.py    nạp CSV, ánh xạ nguồn theo từng trường
core/intent.py         nhận diện tỉnh/trường, chặn ngoài phạm vi
core/retriever.py      TF-IDF embedding thuần Python
core/rag_engine.py     trả lời + citation + fallback
data/generate_fdi_data.py → data/fdi_data.csv
tests/                 pytest (65 test case)
scripts/keepalive.py   chống sleep (GitHub Actions)
docs/QA.md             ISO/IEC 25010 + user test
```

## Cập nhật dữ liệu
Sửa `RECORDS` trong `data/generate_fdi_data.py` → `python data/generate_fdi_data.py` (tự validate) → chạy test.

> Dữ liệu tổng hợp từ báo cáo thị trường Savills, CBRE, JLL và quy định hiện hành. Giá thuê đất và ưu đãi thuế mang tính chất tham khảo, có thể thay đổi tùy KCN, loại dự án, thời điểm ký hợp đồng và chính sách từng địa phương. Ứng dụng không thay thế tư vấn pháp lý/đầu tư.
