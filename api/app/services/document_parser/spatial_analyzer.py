from pptx.enum.shapes import MSO_SHAPE_TYPE

class PptxSpatialAnalyzer:
    @staticmethod
    def get_absolute_bounds(shape, parent_left=0, parent_top=0, scale_x=1.0, scale_y=1.0):
        """Tính toán tọa độ tuyệt đối (left, top, right, bottom) của một shape.
        Đặc biệt xử lý chính xác hệ tọa độ tương đối của Group Shapes."""
        # Nếu là Group Shape, ta sẽ xử lý tính toán scale dựa trên kích thước thật và kích thước child coordinate
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            # Tạm thời trả về bounding box tổng của nhóm
            left = parent_left + int(shape.left * scale_x)
            top = parent_top + int(shape.top * scale_y)
            right = left + int(shape.width * scale_x)
            bottom = top + int(shape.height * scale_y)
            return left, top, right, bottom
            
        left = parent_left + int(shape.left * scale_x)
        top = parent_top + int(shape.top * scale_y)
        right = left + int(shape.width * scale_x)
        bottom = top + int(shape.height * scale_y)
        return left, top, right, bottom

    @staticmethod
    def recursive_xy_cut(elements):
        """Thuật toán XY-Cut đệ quy phân tách các khối văn bản theo thứ tự đọc tự nhiên.
        elements: list gồm các dict dạng {'shape': shape_obj, 'box': (left, top, right, bottom)}
        """
        if len(elements) <= 1:
            return elements

        # 1. Thử cắt theo chiều ngang (Tìm khoảng trống phân chia các Dòng)
        elements.sort(key=lambda e: e['box'][1]) # Sắp xếp theo 'top'
        horizontal_split_idx = -1
        max_y_seen = elements[0]['box'][3] # 'bottom' của khối đầu tiên

        for i in range(1, len(elements)):
            # Nếu 'top' của khối tiếp theo lớn hơn 'bottom' lớn nhất đã thấy -> Có khoảng trống ngang hoàn toàn
            if elements[i]['box'][1] >= max_y_seen:
                horizontal_split_idx = i
                break
            max_y_seen = max(max_y_seen, elements[i]['box'][3])

        if horizontal_split_idx != -1:
            top_part = PptxSpatialAnalyzer.recursive_xy_cut(elements[:horizontal_split_idx])
            bottom_part = PptxSpatialAnalyzer.recursive_xy_cut(elements[horizontal_split_idx:])
            return top_part + bottom_part

        # 2. Nếu không cắt được dòng, thử cắt theo chiều dọc (Tìm khoảng trống phân chia các Cột)
        elements.sort(key=lambda e: e['box'][0]) # Sắp xếp theo 'left'
        vertical_split_idx = -1
        max_x_seen = elements[0]['box'][2] # 'right' của khối đầu tiên

        for i in range(1, len(elements)):
            # Nếu 'left' của khối tiếp theo lớn hơn 'right' lớn nhất đã thấy -> Có khoảng trống dọc hoàn toàn
            if elements[i]['box'][0] >= max_x_seen:
                vertical_split_idx = i
                break
            max_x_seen = max(max_x_seen, elements[i]['box'][2])

        if vertical_split_idx != -1:
            left_part = PptxSpatialAnalyzer.recursive_xy_cut(elements[:vertical_split_idx])
            right_part = PptxSpatialAnalyzer.recursive_xy_cut(elements[vertical_split_idx:])
            return left_part + right_part

        # 3. Trường hợp các khối đè lên nhau hoặc không có khoảng hở rõ ràng, dùng Top-Left Heuristic làm fallback
        elements.sort(key=lambda e: (e['box'][1], e['box'][0]))
        return elements

    @classmethod
    def sort_shapes(cls, shapes) -> list:
        """Hàm bề mặt (Facade) nhận vào danh sách shapes thô và trả về danh sách đã được sắp xếp thứ tự đọc."""
        valid_elements = []
        for shape in shapes:
            # Chỉ xếp hạng các shape có nội dung thực tế để tránh loãng thuật toán
            if shape.has_text_frame or shape.has_table or shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                box = cls.get_absolute_bounds(shape)
                valid_elements.append({'shape': shape, 'box': box})
                
        sorted_elements = cls.recursive_xy_cut(valid_elements)
        return [e['shape'] for e in sorted_elements]