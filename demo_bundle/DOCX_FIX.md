# Fix DOCX Processing Issue

## Vấn đề
Script hiện tại không thể xử lý file DOCX do xung đột NumPy version:
- NumPy 2.x không tương thích với pymilvus
- Downgrade NumPy có thể ảnh hưởng các package khác

## Giải pháp tạm thời
Hiện tại script chỉ xử lý file PDF. DOCX bị tạm thời disable.

## Giải pháp lâu dài

### Phương án 1: Tạo môi trường riêng cho DOCX
```bash
# Tạo môi trường conda riêng
conda create -n docx_env python=3.10
conda activate docx_env
pip install "numpy<2" langchain-community langchain-milvus docx2txt

# Chạy script DOCX trong môi trường này
python scripts/test_docx_ingest.py "data/QuyDinh.docx"
```

### Phương án 2: Chuyển đổi DOCX sang PDF
```bash
# Sử dụng tool khác để convert DOCX -> PDF trước
# Rồi ingest PDF như bình thường
```

### Phương án 3: Sử dụng alternative loader
- Thử `python-docx` thay vì `docx2txt`
- Hoặc sử dụng `unstructured` với cấu hình khác

## Kích hoạt lại DOCX
Khi đã fix NumPy issue, uncomment các dòng sau trong `demo_ingest.ps1`:
```powershell
$files += Get-ChildItem -Path $DataDir -Filter *.docx -Recurse -ErrorAction SilentlyContinue
$files += Get-ChildItem -Path $DataDir -Filter *.doc -Recurse -ErrorAction SilentlyContinue
```
