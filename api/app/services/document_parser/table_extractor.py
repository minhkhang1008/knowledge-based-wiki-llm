class PptxTableExtractor:
    @staticmethod
    def extract(shape) -> str:
        """Nhận vào một shape, kiểm tra và trích xuất cấu trúc bảng sang Markdown."""
        if not shape.has_table:
            return ""
            
        table = shape.table
        num_rows = len(table.rows)
        num_cols = len(table.columns)
        
        if num_rows == 0 or num_cols == 0:
            return ""
            
        # Khởi tạo ma trận lưới dữ liệu rỗng
        grid = [["" for _ in range(num_cols)] for _ in range(num_rows)]
        
        # Duyệt qua ma trận ô (cells) để bóc tách text
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                # Xóa khoảng trắng thừa và đổi ký tự xuống dòng thành khoảng trắng 
                # để tránh làm vỡ định dạng hàng (|) của Markdown Table
                text = cell.text.strip().replace("\n", " ")
                grid[r_idx][c_idx] = text
                
        # Xây dựng chuỗi Markdown Table
        markdown_table = ""
        
        # 1. Tạo dòng tiêu đề (Header)
        markdown_table += "| " + " | ".join(grid[0]) + " |\n"
        
        # 2. Tạo hàng phân cách tiêu đề (Separator)
        markdown_table += "| " + " | ".join(["---" for _ in range(num_cols)]) + " |\n"
        
        # 3. Tạo các dòng dữ liệu (Data rows)
        for r_idx in range(1, num_rows):
            markdown_table += "| " + " | ".join(grid[r_idx]) + " |\n"
            
        return markdown_table + "\n"