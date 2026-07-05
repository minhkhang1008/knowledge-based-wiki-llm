# API Contract - Squad 2 (Knowledge Engine)

- Thành công: `{"success": true, "data": {...}, "message": "...", "error": null}`

- Thất bại: `{"success": false, "data": null, "message": "...", "error": {"code": "...", "detail": "..."}}`

---

## 1. Nhóm API Quản lý Bài viết Wiki (Articles)

### 1.1. API Lấy Danh Sách Bài Viết
* **Địa chỉ (URL):** `/api/articles`
* **Phương thức (Method):** `GET`
* **Chức năng:** Lấy danh sách các bài viết wiki trong hệ thống. Hỗ trợ các tham số lọc theo danh mục hoặc tìm kiếm theo từ khóa.

### Dữ liệu gửi lên (Query Parameters)
Định dạng: `URL Parameters`

Ghi chú: `search` và `category` là không bắt buộc (Optional). Nếu để trống, hệ thống sẽ trả về toàn bộ danh sách bài viết.

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": [
    {
      "id": "wiki_01",
      "title": "Hướng dẫn Docker cơ bản",
      "category": "devops",
    }
  ],
  "message": "Lấy danh sách bài viết thành công."
}
```

---

### 1.2. API Chi Tiết Bài Viết
* **Địa chỉ (URL):** `/api/articles/{id}`
* **Phương thức (Method):** `GET`
* **Chức năng:** Lấy thông tin chi tiết đầy đủ của một bài viết wiki cụ thể dựa trên ID.

### Dữ liệu gửi lên (Path Parameters)
Định dạng: `string` trong URL path.

Ghi chú cho Pydantic Schema: ID truyền vào bắt buộc phải đúng định dạng string và tồn tại trong cơ sở dữ liệu hệ thống.

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": {
    "id": "art_01",
    "title": "Hướng dẫn Docker cơ bản",
    "content": "# Docker là gì?\nDocker là một nền tảng...",
    "category": "devops",
    "author": "Nguyen Van A",
  },
  "message": "Lấy chi tiết bài viết thành công."
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
  "title": "Tổng quan về RAG",
  "content": "# RAG là gì?\nRetrieval-Augmented Generation...",
  "category": "ai"
}
```

Ghi chú cho Pydantic Schema: `title` bắt buộc từ 5 ký tự trở lên. `content` lưu trữ định dạng Markdown dưới dạng chuỗi kí tự (String). `category` bắt buộc để phân loại bài viết.

### Dữ liệu trả về khi thành công (Response - 201 Created)
```json
{
  "success": true,
  "data": {
    "id": "wiki_03",
    "title": "Tổng quan về RAG",
    "category": "ai",
  },
  "message": "Tạo bài viết mới thành công."
}
```

---

###  1.4. API Cập Nhật Bài Viết
* **Địa chỉ (URL):** `/api/articles/{id}`
* **Phương thức (Method):** `PUT`
* **Chức năng:** Chỉnh sửa và cập nhật nội dung mới cho một bài viết wiki đã tồn tại dựa trên ID.

### Dữ liệu gửi lên (Request Body)
Định dạng: `application/json`

```json
{
  "title": "Tổng quan về RAG (Cập nhật)",
  "content": "# RAG và Ollama\nNội dung đã được chỉnh sửa...",
  "category": "ai"
}
```

Ghi chú cho Pydantic Schema: Các trường hợp gửi lên trong body sẽ đè lên dữ liệu cũ của bài viết có `id` tương ứng trên thanh URL.

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": {
    "id": "art_03",
    "title": "Tổng quan về RAG (Cập nhật)",
  },
  "message": "Cập nhật nội dung bài viết thành công."
}
```

---

## 2. Nhóm API Tìm kiếm & Hỏi đáp AI (Core Engine)

### 2.1. API Tìm Kiếm Kết Hợp (Hybrid Search)
* **Địa chỉ (URL):** `/api/search`
* **Phương thức (Method):** `POST`
* **Chức năng:** Thực hiện tìm kiếm kết hợp cả từ khóa (Keyword) và ngữ nghĩa (Semantic) trong kho dữ liệu wiki.

### ### Dữ liệu gửi lên (Request Body)
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
      "id": "wiki_01",
      "title": "Hướng dẫn Docker cơ bản",
      "score": 0.92,
      "match_type": "semantic"
    }
  ],
  "message": "Tìm kiếm kết quả hoàn tất."
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
  "question": "Quy định về số ngày nghỉ phép năm 2025 của nhân viên như thế nào?"
}
```

Ghi chú cho Pydantic Schema: `question` bắt buộc phải là String, không được để trống và có độ dài tối thiểu là 5 ký tự để tránh người dùng gửi chuỗi rỗng.

### Dữ liệu trả về khi thành công (Response - 200 OK)
```json
{
  "success": true,
  "data": {
    "answer": "Theo quy định, nhân viên có 12 ngày nghỉ phép năm...",
    "sources": [
      {
        "id": "wiki_05",
        "title": "Quy chế nhân sự 2025",
        "url": "/articles/wiki_05"
      }
    ]
  },
  "message": "Xử lý câu hỏi RAG thành công."
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
```json
{
  "success": true,
  "data": {
    "total_articles": 142,
    "total_ai_queries": 3420,
  },
  "message": "Lấy dữ liệu thống kê thành công."
}
```