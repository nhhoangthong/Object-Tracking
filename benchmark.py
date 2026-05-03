import cv2
import os
import sys
import time
import glob # Dùng để tìm file ảnh
import csv

# --- PHẦN 1: HÀM TÍNH TOÁN IoU ---

def calculate_iou(boxA, boxB):
    """
    Tính Intersection over Union (IoU) giữa 2 bounding box.
    Các box có định dạng [x, y, w, h]
    """
    # Chuyển sang dạng [x1, y1, x2, y2] (tọa độ góc trên-trái và dưới-phải)
    boxA_coords = [boxA[0], boxA[1], boxA[0] + boxA[2], boxA[1] + boxA[3]]
    boxB_coords = [boxB[0], boxB[1], boxB[0] + boxB[2], boxB[1] + boxB[3]]

    # Xác định tọa độ (x, y) của vùng giao nhau (intersection)
    xA = max(boxA_coords[0], boxB_coords[0])
    yA = max(boxA_coords[1], boxB_coords[1])
    xB = min(boxA_coords[2], boxB_coords[2])
    yB = min(boxA_coords[3], boxB_coords[3])

    # Tính diện tích phần giao nhau
    # max(0, ...) để đảm bảo nếu 2 box không giao nhau thì diện tích là 0
    interArea = max(0, xB - xA) * max(0, yB - yA)

    # Tính diện tích của từng box
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]

    # Tính diện tích hợp nhất (union)
    unionArea = float(boxAArea + boxBArea - interArea)

    # Nếu unionArea = 0 (ví dụ: 2 box có diện tích 0), trả về 0
    if unionArea == 0:
        return 0

    # Tính IoU
    iou = interArea / unionArea
    return iou

# --- PHẦN 2: HÀM HỖ TRỢ ĐỌC DỮ LIỆU ---

def load_ground_truth(gt_path):
    """
    Đọc file groundtruth_rect.txt.
    File này có thể phân tách bằng dấu phẩy (,) hoặc tab (\t).
    """
    ground_truth = []
    with open(gt_path, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            if ',' in line:
                parts = line.split(',')
            elif '\t' in line:
                parts = line.split('\t')
            else:
                parts = line.split()
                
            # Chuyển [x, y, w, h] sang số nguyên
            try:
                ground_truth.append([int(float(p)) for p in parts])
            except ValueError as e:
                print(f"Lỗi khi đọc dòng: '{line}' trong file: {gt_path}. Lỗi: {e}")
                
    return ground_truth

def load_video_frames(video_folder_path):
    """
    Lấy danh sách ĐÃ SẮP XẾP của tất cả các frame ảnh trong thư mục 'img'.
    """
    # Đường dẫn đến thư mục chứa ảnh (thường là 'img' trong OTB)
    img_folder_path = os.path.join(video_folder_path, 'img')
    
    # Tìm tất cả các file ảnh (jpg, png, bmp)
    frame_list = glob.glob(os.path.join(img_folder_path, '*.jpg'))
    if not frame_list:
        frame_list = glob.glob(os.path.join(img_folder_path, '*.png'))
    if not frame_list:
        frame_list = glob.glob(os.path.join(img_folder_path, '*.bmp'))
        
    if not frame_list:
        print(f"Không tìm thấy frame ảnh nào trong: {img_folder_path}")
        return None

    # Sắp xếp lại danh sách frame cho đúng thứ tự (ví dụ: 0001.jpg, 0002.jpg, ...)
    frame_list.sort()
    return frame_list

# --- PHẦN 3: ĐỊNH NGHĨA CÁC TRACKER ---

def create_tracker(tracker_type):
    """Hàm factory để tạo tracker dựa trên tên."""
    if tracker_type == 'KCF':
        return cv2.TrackerKCF_create()
    if tracker_type == 'CSRT':
        return cv2.TrackerCSRT_create()
    
    # legacy tracker
    if tracker_type == 'MOSSE':
        return cv2.legacy.TrackerMOSSE_create()
    if tracker_type == 'MedianFlow':
        return cv2.legacy.TrackerMedianFlow_create()
    
    print(f"Tracker '{tracker_type}' không hợp lệ.")
    return None

# --- PHẦN 4: KỊCH BẢN CHÍNH ---

def main():
    # 1. Cấu hình
    # Đường dẫn OTB Dataset
    otb_dataset_path = "OTB-dataset-main\OTB100" 
    
    # Danh sách các tracker bạn muốn so sánh
    tracker_types = ['KCF', 'CSRT', 'MOSSE', 'MedianFlow']
    
    # Chỉ chạy trên vài video để test (để trống [] nếu muốn chạy tất cả)
    # videos_to_run = ['Basketball', 'Biker', 'Car4'] 
    videos_to_run = [] # Để trống để chạy tất cả 100 video

    # Nơi lưu kết quả tổng
    all_results = {} # { 'KCF': {'avg_iou': [], 'avg_fps': []}, 'CSRT': ... }
    detailed_csv_data = [] # Dùng để lưu dữ liệu ghi vào file detail csv
    
    # Lấy danh sách video
    if not videos_to_run:
        video_names = [d for d in os.listdir(otb_dataset_path) if os.path.isdir(os.path.join(otb_dataset_path, d))]
    else:
        video_names = videos_to_run

    print(f"Bắt đầu chạy benchmark trên {len(video_names)} video...")

    # VÒNG LẶP 1: Lặp qua từng video
    for video_name in video_names:
        video_folder_path = os.path.join(otb_dataset_path, video_name)
        
        # --- Tìm file ground truth CÓ DỮ LIỆU ---
        ground_truth = [] # Khởi tạo là danh sách rỗng
        gt_path_found = "" # Đường dẫn của file gt hợp lệ sẽ được lưu ở đây
        
        # Bước 1: Thử file chuẩn 'groundtruth_rect.txt' trước
        gt_path_standard = os.path.join(video_folder_path, 'groundtruth_rect.txt')
        if os.path.exists(gt_path_standard):
            # Thử đọc file chuẩn
            temp_gt = load_ground_truth(gt_path_standard)
            if temp_gt: # Nếu file chuẩn CÓ DỮ LIỆU
                ground_truth = temp_gt
                gt_path_found = gt_path_standard
        
        # Bước 2: Nếu file chuẩn rỗng hoặc không tồn tại, thử các file '.*.txt'
        if not ground_truth: # Chỉ chạy nếu Bước 1 thất bại
            gt_files_pattern = os.path.join(video_folder_path, 'groundtruth_rect.*.txt')
            gt_files_list = glob.glob(gt_files_pattern)
            gt_files_list.sort() # Sắp xếp (ưu tiên .1.txt, .2.txt, ...)

            # LẶP QUA TỪNG FILE TÌM ĐƯỢC
            for file_path in gt_files_list:
                temp_gt = load_ground_truth(file_path)
                if temp_gt: # Ngay khi tìm thấy file CÓ DỮ LIỆU
                    ground_truth = temp_gt # Lưu dữ liệu
                    gt_path_found = file_path # Lưu đường dẫn
                    print(f"  (Video {video_name} dùng file: {os.path.basename(gt_path_found)})")
                    break # Dừng vòng lặp, vì đã tìm thấy file hợp lệ
        # 2. Đọc dữ liệu frame
        frame_paths = load_video_frames(video_folder_path)
        
        # 3. Chốt an toàn CUỐI CÙNG
            # Kiểm tra xem:
            # (A) Có tìm được frame không?
            # (B) Sau tất cả các bước, ground_truth CÓ còn rỗng không?
        if not frame_paths or not ground_truth:
            print(f"Bỏ qua video {video_name}: Thiếu frame hoặc ground truth.")
            continue
            
        if len(frame_paths) != len(ground_truth):
            print(f"Bỏ qua video {video_name}: Số lượng frame ({len(frame_paths)}) và ground truth ({len(ground_truth)}) không khớp.")
            continue

        print(f"\n--- Đang xử lý video: {video_name} ({len(frame_paths)} frames) ---")

        # Lấy frame đầu tiên và box đầu tiên để khởi tạo
        init_frame = cv2.imread(frame_paths[0])
        init_bbox = tuple(ground_truth[0]) # [x, y, w, h]

        # VÒNG LẶP 2: Lặp qua từng tracker
        for tracker_type in tracker_types:
            
            # Khởi tạo lại tracker cho mỗi lần chạy
            tracker = create_tracker(tracker_type)
            if tracker is None:
                continue
                
            tracker.init(init_frame, init_bbox)

            iou_scores = []
            frame_times = []

            # VÒNG LẶP 3: Lặp qua các frame (bắt đầu từ frame thứ 2)
            for i in range(1, len(frame_paths)):
                frame = cv2.imread(frame_paths[i])
                if frame is None:
                    print(f"Lỗi đọc frame: {frame_paths[i]}")
                    break
                
                # Bắt đầu đo thời gian
                start_time = time.time()
                
                # 3. Chạy tracker
                (success, predicted_box) = tracker.update(frame)
                
                # Dừng đo thời gian
                processing_time = time.time() - start_time
                frame_times.append(processing_time)

                # 4. Tính IoU
                gt_box = ground_truth[i]
                
                if success:
                    iou = calculate_iou(gt_box, predicted_box)
                else:
                    iou = 0.0 # Thất bại, IoU = 0
                
                iou_scores.append(iou)

            # 5. Tính kết quả trung bình cho video này
            avg_iou = sum(iou_scores) / len(iou_scores)
            avg_fps = 1.0 / (sum(frame_times) / len(frame_times))

            print(f"  Tracker: {tracker_type.ljust(10)} | Avg. IoU: {avg_iou:.3f} | Avg. FPS: {int(avg_fps)}")

            # Thêm data cho file CSV chi tiết
            detailed_csv_data.append({
                'video': video_name,
                'tracker': tracker_type,
                'avg_iou': f"{avg_iou:.4f}", # Định dạng 4 chữ số thập phân
                'avg_fps': f"{int(avg_fps)}"
            })
            
            # Lưu kết quả
            if tracker_type not in all_results:
                all_results[tracker_type] = {'iou': [], 'fps': []}
            all_results[tracker_type]['iou'].append(avg_iou)
            all_results[tracker_type]['fps'].append(avg_fps)


# --- PHẦN 5: GHI FILE VÀ IN KẾT QUẢ TỔNG KẾT ---
    
    # 5.1 Ghi file chi tiết (results_detailed.csv)
    print("\nĐang ghi file 'results_detailed.csv'...")
    try:
        with open('results_detailed.csv', 'w', newline='', encoding='utf-8') as f:
            # Lấy key từ hàng đầu tiên để làm header
            if detailed_csv_data:
                fieldnames = detailed_csv_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(detailed_csv_data)
        print("Ghi 'results_detailed.csv' thành công.")
    except Exception as e:
        print(f"LỖI khi ghi file chi tiết: {e}")

    # 5.2 Chuẩn bị dữ liệu và Ghi file tổng kết (results_summary.csv)
    print("Đang ghi file 'results_summary.csv'...")
    
    print("\n--- KẾT QUẢ TỔNG KẾT (TRUNG BÌNH TRÊN TẤT CẢ VIDEO) ---")
    print("======================================================")
    print(f"{'Tracker'.ljust(12)} | {'Avg. IoU'.ljust(10)} | {'Avg. FPS'.ljust(10)}")
    print("------------------------------------------------------")
    
    try:
        # Mở file để ghi
        with open('results_summary.csv', 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['tracker', 'avg_iou', 'avg_fps']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Lặp qua, tính toán, in ra terminal VÀ ghi vào file
            for tracker_type, results in all_results.items():
                if not results['iou']: # Đề phòng tracker bị lỗi
                    continue
                    
                total_avg_iou = sum(results['iou']) / len(results['iou'])
                total_avg_fps = sum(results['fps']) / len(results['fps'])
                
                # In ra terminal (giống như cũ)
                print(f"{tracker_type.ljust(12)} | {total_avg_iou:<10.3f} | {int(total_avg_fps):<10}")
                
                # Ghi vào file
                writer.writerow({
                    'tracker': tracker_type,
                    'avg_iou': f"{total_avg_iou:.4f}",
                    'avg_fps': f"{int(total_avg_fps)}"
                })
        print("\nGhi 'results_summary.csv' thành công.")
    except Exception as e:
        print(f"LỖI khi ghi file tổng kết: {e}")
        
    # 6. In kết quả tổng kết
    print("\n--- KẾT QUẢ TỔNG KẾT (TRUNG BÌNH TRÊN TẤT CẢ VIDEO) ---")
    print("======================================================")
    print(f"{'Tracker'.ljust(12)} | {'Avg. IoU'.ljust(10)} | {'Avg. FPS'.ljust(10)}")
    print("------------------------------------------------------")
    
    for tracker_type, results in all_results.items():
        total_avg_iou = sum(results['iou']) / len(results['iou'])
        total_avg_fps = sum(results['fps']) / len(results['fps'])
        print(f"{tracker_type.ljust(12)} | {total_avg_iou:<10.3f} | {int(total_avg_fps):<10}")

if __name__ == '__main__':
    # Kiểm tra cài đặt opencv-contrib-python
    try:
        cv2.TrackerCSRT_create()
    except AttributeError:
        print("LỖI: Bạn cần cài 'opencv-contrib-python'.")
        print("Chạy lệnh: pip uninstall opencv-python")
        print("Và sau đó:  pip install opencv-contrib-python")
        sys.exit()
        
    main()