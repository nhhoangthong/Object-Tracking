import cv2
import os
# import sys
import time
import glob
import csv
import numpy as np
from benchmark import calculate_iou, load_ground_truth, load_video_frames

# --- HÀM GHI CSV ---
def append_csv(file_path, data_dict):
    """
    Hàm này sẽ ghi nối (append) 1 hàng vào file CSV.
    Nếu file chưa tồn tại, nó sẽ tự tạo header.
    """
    file_exists = os.path.isfile(file_path)
    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            fieldnames = data_dict.keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader() # Chỉ viết header nếu file là file mới
                
            writer.writerow(data_dict)
        return True
    except Exception as e:
        print(f"LỖI khi ghi file {file_path}: {e}")
        return False

# --- MAIN ---
def main():
    # 1. Cấu hình
    # Đường dẫn OTB Dataset
    otb_dataset_path = "OTB-dataset-main\OTB100" 
    tracker_type = 'Kalman_PredictOnly'
    detailed_csv_file = 'results_detailed.csv'
    summary_csv_file = 'results_summary.csv'
    
    videos_to_run = [] 
    kalman_results = {'iou': [], 'fps': []}

    if not videos_to_run:
        video_names = [d for d in os.listdir(otb_dataset_path) if os.path.isdir(os.path.join(otb_dataset_path, d))]
    else:
        video_names = videos_to_run

    print(f"Bắt đầu chạy benchmark cho '{tracker_type}' trên {len(video_names)} video...")

    # VÒNG LẶP 1: Lặp qua từng video
    for video_name in video_names:
        video_folder_path = os.path.join(otb_dataset_path, video_name)
        
        # --- Logic tìm Ground Truth ---
        ground_truth = []
        gt_path_found = ""
        gt_path_standard = os.path.join(video_folder_path, 'groundtruth_rect.txt')
        if os.path.exists(gt_path_standard):
            temp_gt = load_ground_truth(gt_path_standard) # <-- Đã import
            if temp_gt:
                ground_truth = temp_gt
                gt_path_found = gt_path_standard
        if not ground_truth:
            gt_files_pattern = os.path.join(video_folder_path, 'groundtruth_rect.*.txt')
            gt_files_list = glob.glob(gt_files_pattern)
            gt_files_list.sort()
            for file_path in gt_files_list:
                temp_gt = load_ground_truth(file_path) # <-- Đã import
                if temp_gt:
                    ground_truth = temp_gt
                    gt_path_found = file_path
                    print(f"  (Video {video_name} dùng file: {os.path.basename(gt_path_found)})")
                    break
        # --- Kết thúc logic tìm GT ---

        frame_paths = load_video_frames(video_folder_path) # <-- Đã import

        if not frame_paths or not ground_truth:
            print(f"CẢNH BÁO: Bỏ qua video {video_name}. Thiếu frame hoặc GT.")
            continue
        if len(frame_paths) != len(ground_truth):
            print(f"CẢNH BÁO: Bỏ qua video {video_name}: Số frame ({len(frame_paths)}) và GT ({len(ground_truth)}) không khớp.")
            continue

        print(f"\n--- Đang xử lý video: {video_name} ({len(frame_paths)} frames) ---")

        # 2. Khởi tạo Kalman Filter
        kalman = cv2.KalmanFilter(4, 2)
        kalman.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
        kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        kalman.processNoiseCov = 1e-5 * np.eye(4, dtype=np.float32)
        kalman.measurementNoiseCov = 1e-1 * np.eye(2, dtype=np.float32)
        kalman.errorCovPost = 1.0 * np.eye(4, dtype=np.float32)

        # 3. Khởi tạo trạng thái ban đầu
        init_bbox = ground_truth[0]
        w, h = init_bbox[2], init_bbox[3]
        x_c = init_bbox[0] + w / 2
        y_c = init_bbox[1] + h / 2
        kalman.statePost = np.array([x_c, y_c, 0, 0], dtype=np.float32).reshape(4, 1)

        iou_scores = [1.0] # Frame 1 có IoU là 1.0
        frame_times = []
        
        # VÒNG LẶP 3: Lặp qua các frame (bắt đầu từ frame thứ 2)
        for i in range(1, len(frame_paths)):
            start_time = time.time()
            
            # 1. Chỉ dự đoán (PREDICT)
            prediction = kalman.predict()
            # 2. KHÔNG BAO GIỜ GỌI HÀM .correct()
            
            processing_time = time.time() - start_time
            frame_times.append(processing_time)
            
            pred_x_c, pred_y_c = prediction[0, 0], prediction[1, 0]
            pred_x = pred_x_c - w / 2
            pred_y = pred_y_c - h / 2
            predicted_box = [pred_x, pred_y, w, h]

            # 4. Tính IoU
            gt_box = ground_truth[i]
            iou = calculate_iou(gt_box, predicted_box) # <-- Đã import
            iou_scores.append(iou)

        # 5. Tính kết quả trung bình cho video này
        avg_iou = sum(iou_scores) / len(iou_scores)
        
        total_time = sum(frame_times)
        num_frames = len(frame_times)
        
        if num_frames == 0 or total_time == 0.0:
            # Xử lý 2 trường hợp:
            # 1. Video chỉ có 1 frame (num_frames == 0)
            # 2. Video chạy quá nhanh (total_time == 0.0)
            avg_fps = 0.0 # Gán là 0 (hoặc 1e9 nếu bạn muốn thể hiện là "rất nhanh")
        else:
            # Tính FPS như bình thường
            avg_fps = 1.0 / (total_time / num_frames)

        print(f"  Tracker: {tracker_type.ljust(20)} | Avg. IoU: {avg_iou:.3f} | Avg. FPS: {int(avg_fps)}")

        # 6. Ghi nối vào file CSV chi tiết
        detailed_data = {
            'video': video_name,
            'tracker': tracker_type,
            'avg_iou': f"{avg_iou:.4f}",
            'avg_fps': f"{int(avg_fps)}"
        }
        append_csv(detailed_csv_file, detailed_data)
        kalman_results['iou'].append(avg_iou)
        kalman_results['fps'].append(avg_fps)

    # 7. In và Ghi kết quả tổng kết
    if kalman_results['iou']:
        total_avg_iou = sum(kalman_results['iou']) / len(kalman_results['iou'])
        total_avg_fps = sum(kalman_results['fps']) / len(kalman_results['fps'])

        print("\n--- KẾT QUẢ TỔNG KẾT (KALMAN FILTER) ---")
        print(f"{tracker_type.ljust(20)} | {total_avg_iou:<10.3f} | {int(total_avg_fps):<10}")

        summary_data = {
            'tracker': tracker_type,
            'avg_iou': f"{total_avg_iou:.4f}",
            'avg_fps': f"{int(total_avg_fps)}"
        }
        append_csv(summary_csv_file, summary_data)
        print(f"\nĐã ghi nối kết quả vào '{summary_csv_file}' và '{detailed_csv_file}'.")
    else:
        print("Không có video nào được xử lý.")

if __name__ == '__main__':
    main()