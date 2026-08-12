class RequestTimeoutError(Exception):
      # Bắt lỗi Timeout
      pass

class ModelNotFoundError(Exception):
      # Bắt lỗi Model hong tồn tại
      pass

class InvalidResponseError(Exception):
      # Bắt lỗi response hong hợp lệ
      pass

class EmptyEmbeddingError(Exception):
      # Bắt lỗi Embedding rỗng
      pass

class RAG_VectorDBError(Exception):
      # Bắt lỗi ChromaDB
      pass

class RAG_ChromaError(Exception):
      # Lỗi ChromaDB
      pass

class RAG_InvalidDimensionException(Exception):
      # Lỗi hong phù hợp kích thước
      pass

class RAG_OperationalError(Exception):
      # Lỗi SQLite
      pass

class ArticleNotFound(Exception):
      # Lỗi article không tồn tại
      pass
class DuplicateDocumentError(Exception):
      # Lỗi article trùng lặp
      pass
class InvalidRequest(Exception):
      # Lỗi reuqest sai
      pass
class AIModelOfflineException(Exception):
      # Lỗi Ollama ngoại tuyến
      pass
class UnexpectedError(Exception):
      # Lỗi ngoài dự kiến
      pass