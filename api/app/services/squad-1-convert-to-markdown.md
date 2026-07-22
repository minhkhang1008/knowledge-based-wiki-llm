services/
├── document_parser/    ← Chuyển đổi file → Markdown text
│   ├── __init__.py
│   ├── pipeline.py
│   ├── converter_registry.py
│   ├── pdf_converter.py
│   ├── image_converter.py
│   ├── image_extractor.py
│   ├── docx_converter.py
│   ├── excel_converter.py
│   ├── pptx_core.py
│   ├── spatial_analyzer.py
│   ├── table_extractor.py
│   └── (spatial_analyzer, table_extractor dùng cho pptx)
├── ocr/                ← OCR engine abstraction
│   ├── base.py
│   ├── factory.py
│   ├── easyocr_engine.py
│   ├── tesseract_engine.py
│   └── ocr_utils.py
├── rag_service.py      ← RAG logic
├── prompt_builder.py   ← Xây dựng prompt cho LLM
└── services_vector_db.py ← ChromaDB vector search
