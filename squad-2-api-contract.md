# API Contract - Squad 2 (Knowledge Engine)

- Thành công: `{"success": true, "data": {...}, "message": "...", "error": null}`

- Thất bại: `{"success": false, "data": null, "message": "...", "error": {"code": "...", "detail": "..."}}`

---

## 1. Nhóm API Quản lý Bài viết Wiki (Articles)

### 1.1. API Lấy Danh Sách Bài Viết
* **Địa chỉ (URL):** `/api/articles`
* **Phương thức (Method):** `GET`
* **Chức năng:** Lấy danh sách các bài viết wiki trong hệ thống. Hỗ trợ tìm kiếm theo từ khóa.

### Dữ liệu gửi lên
```json
{
  "skip" : 0,
  "limit" : 20,
  "search" : "Hướng dẫn docker"
}
```
#### Các biến skip, limit, search là Optional, có thể điền hoặc không

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": [
    {
      "id": "wiki_01",
      "document_id" : "docker_01",
      "title": "Hướng dẫn Docker cơ bản",
      "content" : "Hướng dẫn sử dụng docker dành cho người mới",
      "source_file" : "docker_01",
      "created_at" : "2026-08-07 20:22:36",
      "updated_at" : "2026-08-07 20:22:36"
    }
  ],
  "message": "Lấy danh sách bài viết thành công.",
  "error" : null
}
```

---

### 1.2. API Chi Tiết Bài Viết
* **Địa chỉ (URL):** `/api/articles/{article_id}`
* **Phương thức (Method):** `GET`
* **Chức năng:** Lấy thông tin chi tiết đầy đủ của một bài viết wiki cụ thể dựa trên ID.

### Dữ liệu gửi lên (Path Parameters)

* Chọn giá trị cho **{article_id}** ở trên URL

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": {
    "id": "wiki_01",
    "document_id" : "docker_01",
    "title": "Hướng dẫn Docker cơ bản",
    "content" : "Hướng dẫn sử dụng docker dành cho người mới",
    "source_file" : "docker_01",
    "created_at" : "2026-08-07 20:36:36",
    "updated_at" : "2026-08-07 20:36:36"
  },
  "message": "Lấy chi tiết bài viết thành công.",
  "error" : null
}
```

---

###  1.3. API Tạo Bài Viết Mới
* **Địa chỉ (URL):** `/api/articles`
* **Phương thức (Method):** `POST`
* **Chức năng:** Tiếp nhận thông tin tiêu đề, nội dung markdown và danh mục để tạo ra một bài viết wiki mới trong hệ thống.

### Dữ liệu gửi lên (Request Body)
Định dạng: `application/json`

```json
{
  "document_id" : "docker_67",
  "title" : "Hướng dẫn docker cơ bản với 67 bước",
  "content" : "# Hướng dẫn docker cơ bản với 67 bước",
  "source_file" : "docker_6767"
}
```

Ghi chú: Tất cả các biến đều yêu cầu từ 1 kí tự trở lên. `content` lưu trữ định dạng Markdown dưới dạng chuỗi kí tự (String).

### Dữ liệu trả về khi thành công (Response - 201 Created)
```json
{
  "success": true,
  "data": {
    "id": "wiki_03",
    "document_id" : "docker_67",
    "title" : "Hướng dẫn docker cơ bản với 67 bước",
    "content" : "# Hướng dẫn docker cơ bản với 67 bước",
    "source_file" : "docker_6767"
    "created_at" : "2026-08-07 20:36:36",
    "updated_at" : "2026-08-07 20:36:36"
  },
  "message": "Tạo bài viết mới thành công.",
  "error" : null
}
```

---

###  1.4. API Cập Nhật Bài Viết
* **Địa chỉ (URL):** `/api/articles/{article_id}`
* **Phương thức (Method):** `PUT`
* **Chức năng:** Chỉnh sửa và cập nhật nội dung mới cho một bài viết wiki đã tồn tại dựa trên ID.

### Dữ liệu gửi lên (Request Body)

* Chọn giá trị cho **{article_id}** ở trên URL

```json
{
  "title": "Tổng quan về RAG (Cập nhật)",
  "content": "# RAG và Ollama\nNội dung đã được chỉnh sửa...",
  "source_file" : "docker_67"
}
```

Ghi chú cho Pydantic Schema: Các trường hợp gửi lên trong body sẽ đè lên dữ liệu cũ của bài viết có `article_id` tương ứng trên thanh URL.

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": {
    "id": "wiki_03",
    "document_id" : "docker_36",
    "title" : "Tổng quan về RAG (Cập nhật)",
    "content" : "# RAG và Ollama\nNội dung đã được chỉnh sửa...",
    "source_file" : "docker_67"
    "created_at" : "2026-08-07 20:36:36",
    "updated_at" : "2026-08-07 20:36:36"
  },
  "message": "Cập nhật nội dung bài viết thành công.",
  "error" : null
}
```

### 1.5. API Xóa Bài Viết:
* **Địa chỉ (URL):** `/api/articles/{article_id}`
* **Phương thức (Method):** `DELETE`
* **Chức năng:** Xóa bài viết

### Dữ liệu gửi lên (Request Body)
* Chọn giá trị cho **{article_id}** ở trên URL

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": null,
  "message": "Xóa article thành công",
  "error" : null
}
```

### 1.6. API Upsert Bài Viết:
* **Địa chỉ (URL):** `/api/articles/by-document/{document_id}`
* **Phương thức (Method):** `PUT`
* **Chức năng:** Tạo hoặc cập nhật bài viết dành cho developer

### Dữ liệu gửi lên (Request Body)

* Chọn giá trị cho **{document_id}** ở trên URL

```json
{
  "title" : "Hướng dẫn sử dụng docker với 36 bước",
  "content" : "# Hướng dẫn sử dụng docker với 36 bước",
  "source_file" : "docker36"
}
```

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": {
    "id": "wiki_03",
    "document_id" : "docker_36",
    "title" : "Hướng dẫn sử dụng docker với 36 bước",
    "content" : "Hướng dẫn sử dụng docker với 36 bước",
    "source_file" : "docker36"
    "created_at" : "2026-08-07 20:36:36",
    "updated_at" : "2026-08-07 20:36:36"
  },
  "message": "Upsert article thành công ",
  "error" : null
}
```

---

## 2. Nhóm API Tìm kiếm & Hỏi đáp AI (Core Engine)

### 2.1. API Tìm Kiếm Kết Hợp (Hybrid Search)
* **Địa chỉ (URL):** `/api/search`
* **Phương thức (Method):** `POST`
* **Chức năng:** Thực hiện tìm kiếm kết hợp cả từ khóa (Keyword) và ngữ nghĩa (Semantic) trong kho dữ liệu wiki.

### Dữ liệu gửi lên (Request Body)
Định dạng: `application/json`

```json
{
  "query": "cách deploy docker lên server"
}
```

Ghi chú cho Pydantic Schema: `query` là bắt buộc, không được để trống và phải có độ dài tối thiểu là 2 ký tự để vector hóa tìm kiếm.

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": [
    {
      "text" : "cách deploy docker lên server",
      "article_id" : "docker_36",
      "source_file" : "docker36",
      "page_number" : 36,
      "distant" : 0.36
    }
  ],
  "message": "Tìm kiếm thành công",
  "error" : null
}
```

---

### 2.2. API Hỏi Đáp Tài Liệu (RAG Q&A)
* **Địa chỉ (URL):** `/api/qa/ask`
* **Phương thức (Method):** `POST`
* **Chức năng:** Tiếp nhận câu hỏi bằng tiếng Việt, thực hiện truy vấn ngữ nghĩa và dùng LLM để tổng hợp câu trả lời dựa trên tài liệu.

### Dữ liệu gửi lên (Request Body)
Định dạng: `application/json`

```json
{
  "question": "Quy định về số ngày nghỉ phép năm 2025 của nhân viên như thế nào?",
  "chat_history" : [
    {
      "role" : "user",
      "content" : "Quy định về số ngày nghỉ phép năm 2025 của nhân viên như thế nào?"
    }
  ]
}
```

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": {
    "answer": "Theo quy định, nhân viên có 12 ngày nghỉ phép năm...",
    "sources": [
      {
        "text" : "Quy chế nhân sự 2025",
        "article_id": "wiki_05",
        "source_file": "/articles/wiki_05",
        "page_number" : 36,
        "distance" : 0.36
      }
    ],
    "no_answer_reason" : null
  },
  "message": "Xử lý câu hỏi RAG thành công.",
  "error" : null
}
```

---

## 3. Nhóm API Thống kê (Analytics)

### 3.1. API Lấy Số Liệu Thống Kê Tổng Hợp
* **Địa chỉ (URL):** `/api/stats`
* **Phương thức (Method):** `GET`
* **Chức năng:** Trả về các số liệu thống kê tổng hợp của toàn hệ thống phục vụ cho Squad 3 vẽ biểu đồ Dashboard.

### Dữ liệu gửi lên (Request Body)
Định dạng: `Không có (None)`

###  Dữ liệu trả về khi thành công (Response - 200 OK)
~~~json
{
  "success": true,
  "data": {
    "total_articles": 142,
    "total_qa_logs": 3420,
    "total_indexed_chunks" : 3000
  },
  "message": "Lấy dữ liệu thống kê thành công.",
  "error" : null
}
~~~


## 4. Quy định mã lỗi  (Error Contract)

### 4.1. Request không hợp lệ (Response - 422 Unprocessable Entity)
### Dữ liệu trả về khi thất bại
~~~json
{
  "success": false,
  "data": null,
  "message": "Request sai",
  "error" : {
    "code" : "INVALID_REQUEST",
    "detail" : "..."
  }
}
~~~

### 4.2 Article không tồn tại (Response - 404 Not Found)
### Dữ liệu trả về khi thất bại
~~~json
{
  "success": false,
  "data": null,
  "message": "Article không tồn tại",
  "error" : {
    "code" : "ARTICLE_NOT_FOUND",
    "detail" : "Article không tồn tại"
  }
}
~~~

### 4.3 Trùng document_id (Response - 409 Conflict)
### Dữ liệu trả về khi thất bại
~~~json
{
  "success": false,
  "data": null,
  "message": "Trùng document_id",
  "error" : {
    "code" : "DUPLICATE_DOCUMENT_ERROR",
    "detail" : "..."
  }
}
~~~

### 4.4 Ollama ngoại tuyến (Response - 503 Service Unavailable)
### Dữ liệu trả về khi thất bại
~~~json
{
  "success": false,
  "data": null,
  "message": "Hệ thống AI hiện đang ngoại tuyến",
  "error" : {
    "code" : "503 Service Unavailable",
    "detail" : "Ollama ngoại tuyến hoặc chưa kết nối"
  }
}
~~~

### 4.5 Lỗi không dự kiến (Response - 500 Internal Server Error)
### Dữ liệu trả về khi thất bại
~~~json
{
  "success": false,
  "data": null,
  "message": "Lỗi không dự kiến",
  "error" : {
    "code" : "UNEXPECTED_ERROR",
    "detail" : "..."
  }
}
~~~