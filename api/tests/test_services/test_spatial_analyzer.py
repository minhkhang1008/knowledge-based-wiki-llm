import pytest
from app.services.document_parser.spatial_analyzer import PptxSpatialAnalyzer

def test_recursive_xy_cut_separates_columns_correctly():
    # Giả lập 3 khối văn bản trên slide chia làm 2 cột:
    # Cột 1 (Bên trái) có Khối A (ở trên), Khối B (ở dưới)
    # Cột 2 (Bên phải) có Khối C (trải dài từ trên xuống)
    
    mock_shape_a = "Shape_A_Left_Top"
    mock_shape_b = "Shape_B_Left_Bottom"
    mock_shape_c = "Shape_C_Right"
    
    elements = [
        {'shape': mock_shape_b, 'box': (10, 200, 100, 350)}, # Cột trái - dưới
        {'shape': mock_shape_c, 'box': (150, 50, 250, 350)}, # Cột phải - trải dài
        {'shape': mock_shape_a, 'box': (10, 50, 100, 150)},  # Cột trái - trên
    ]
    
    # Thực thi thuật toán sắp xếp
    sorted_res = PptxSpatialAnalyzer.recursive_xy_cut(elements)
    sorted_shapes = [e['shape'] for e in sorted_res]
    
    # Thứ tự đọc chuẩn của con người: Cột 1 đọc từ trên xuống -> Cột 2
    # Kết quả mong đợi: Khối A -> Khối B -> Khối C
    assert sorted_shapes == [mock_shape_a, mock_shape_b, mock_shape_c]