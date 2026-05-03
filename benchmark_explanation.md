# Giải thích chi tiết Benchmark.py

## Tổng quan
File này thực hiện benchmark (đánh giá hiệu suất) của 4 thuật toán object tracking trên dataset OTB100, so sánh độ chính xác (IoU) và tốc độ xử lý (FPS).

---

## PHẦN 1: HÀM TÍNH TOÁN IoU

### `calculate_iou(boxA, boxB)`

**Mục đích:** Đo độ chính xác của việc tracking bằng cách tính IoU (Intersection over Union) giữa 2 bounding box.

**Tại sao cần:** IoU là metric chuẩn để đánh giá xem box dự đoán của tracker có khớp với ground truth không. Giá trị từ 0 (không khớp) đến 1 (khớp hoàn toàn).

**Flow:**
```
Input: boxA [x, y, w, h], boxB [x, y, w, h]
  ↓
1. Tính tọa độ vùng giao nhau (intersection)
   - xA = max(boxA.x, boxB.x)
   - yA = max(boxA.y, boxB.y)
   - xB = min(boxA.x + boxA.w, boxB.x + boxB.w)
   - yB = min(boxA.y + boxA.h, boxB.y + boxB.h)
  ↓
2. Tính diện tích intersection
   - interArea = max(0, xB - xA) × max(0, yB - yA)
   - max(0, ...) để xử lý trường hợp không giao nhau
  ↓
3. Tính diện tích từng box
   - boxAArea = w × h của boxA
   - boxBArea = w × h của boxB
  ↓
4. Tính diện tích union
   - unionArea = boxAArea + boxBArea - interArea
  ↓
5. Tính IoU
   - IoU = interArea / unionArea
   - Return 0 nếu unionArea = 0
  ↓
Output: IoU score (0.0 - 1.0)
```

**Công thức:**
```
IoU = Diện tích giao nhau / Diện tích hợp nhất
    = Intersection / Union
```

---

## PHẦN 2: HÀM HỖ TRỢ ĐỌC DỮ LIỆU

### `load_ground_truth(gt_path)`

**Mục đích:** Đọc file ground truth (vị trí thật của object qua các frame) từ file text.

**Tại sao cần:** Dataset OTB cung cấp ground truth dưới dạng file text, mỗi dòng là tọa độ [x, y, w, h] của object ở frame tương ứng. Cần parse file này để so sánh với kết quả tracking.

**Flow:**
```
Input: Đường dẫn đến file groundtruth_rect.txt
  ↓
1. Mở file và đọc từng dòng
  ↓
2. Với mỗi dòng:
   - Loại bỏ khoảng trắng đầu/cuối
   - Phát hiện delimiter: dấu phẩy (,), tab (\t), hoặc space
   - Split dòng thành các phần tử
  ↓
3. Convert các phần tử sang int
   - [x, y, w, h] = [int(float(p)) for p in parts]
   - Dùng float() trước để xử lý số thập phân
  ↓
4. Xử lý lỗi (nếu có)
   - In thông báo lỗi nếu không parse được
  ↓
Output: List các bbox [[x1,y1,w1,h1], [x2,y2,w2,h2], ...]
```

**Lưu ý:** File OTB có thể dùng nhiều format khác nhau (`,`, `\t`, space) nên cần xử lý linh hoạt.

---

### `load_video_frames(video_folder_path)`

**Mục đích:** Lấy danh sách đường dẫn của tất cả các frame ảnh trong video, đã sắp xếp theo thứ tự.

**Tại sao cần:** Dataset OTB lưu video dưới dạng chuỗi ảnh (không phải file .mp4). Cần load danh sách ảnh theo đúng thứ tự để tracking tuần tự.

**Flow:**
```
Input: Đường dẫn đến thư mục video
  ↓
1. Tạo đường dẫn đến thư mục 'img'
   - img_folder_path = video_folder_path/img
  ↓
2. Tìm tất cả file ảnh theo thứ tự ưu tiên:
   a. Thử tìm *.jpg
   b. Nếu không có, thử *.png
   c. Nếu không có, thử *.bmp
  ↓
3. Kiểm tra có tìm được frame không
   - Nếu không → In lỗi và return None
  ↓
4. Sắp xếp danh sách theo tên file
   - frame_list.sort()
   - Đảm bảo thứ tự: 0001.jpg, 0002.jpg, ...
  ↓
Output: List đường dẫn frame đã sắp xếp
```

**Ví dụ output:**
```python
[
  'OTB-dataset-main/OTB100/Basketball/img/0001.jpg',
  'OTB-dataset-main/OTB100/Basketball/img/0002.jpg',
  ...
]
```

---

### `find_ground_truth_file(video_folder_path, video_name)`

**Mục đích:** Tìm và đọc file ground truth hợp lệ (có dữ liệu) cho video.

**Tại sao cần:** 
- Một số video OTB có nhiều file ground truth (ví dụ: groundtruth_rect.1.txt, groundtruth_rect.2.txt)
- Một số file có thể rỗng hoặc không tồn tại
- Cần logic để tìm file hợp lệ theo thứ tự ưu tiên

**Flow:**
```
Input: Đường dẫn video + tên video
  ↓
1. Khởi tạo biến rỗng
   - ground_truth = []
   - gt_path_found = ""
  ↓
2. BƯỚC 1: Thử file chuẩn 'groundtruth_rect.txt'
   - Kiểm tra file có tồn tại không
   - Nếu có → Load và kiểm tra có dữ liệu không
   - Nếu có dữ liệu → Lưu lại và dừng
  ↓
3. BƯỚC 2: Nếu file chuẩn rỗng/không tồn tại
   - Tìm tất cả file khớp pattern 'groundtruth_rect.*.txt'
   - Sắp xếp danh sách
   - Lặp qua từng file:
     * Load file
     * Nếu có dữ liệu → Lưu lại và dừng
     * In thông báo đang dùng file nào
  ↓
Output: (ground_truth_list, file_path)
        hoặc ([], "") nếu không tìm thấy
```

**Ví dụ:**
```
Video 'Jogging' có:
  - groundtruth_rect.txt (rỗng)
  - groundtruth_rect.1.txt (có dữ liệu)
  - groundtruth_rect.2.txt (có dữ liệu)
→ Chọn groundtruth_rect.1.txt (file đầu tiên có dữ liệu)
```

---

## PHẦN 3: ĐỊNH NGHĨA CÁC TRACKER

### `create_tracker(tracker_type)`

**Mục đích:** Factory function để tạo instance của tracker theo tên (design pattern).

**Tại sao cần:** 
- Tránh lặp code khi khởi tạo nhiều tracker
- Dễ thêm/bớt tracker mới
- Xử lý tập trung lỗi tracker không hợp lệ

**Flow:**
```
Input: Tên tracker (string)
  ↓
1. Kiểm tra tracker_type và tạo instance tương ứng:
   - 'KCF' → cv2.TrackerKCF_create()
   - 'CSRT' → cv2.TrackerCSRT_create()
   - 'MOSSE' → cv2.legacy.TrackerMOSSE_create()
   - 'MedianFlow' → cv2.legacy.TrackerMedianFlow_create()
  ↓
2. Nếu không khớp tên nào
   - In lỗi "Tracker không hợp lệ"
   - Return None
  ↓
Output: Tracker object hoặc None
```

**Các tracker được sử dụng:**
- **KCF** (Kernelized Correlation Filters): Nhanh, độ chính xác khá
- **CSRT** (Channel and Spatial Reliability Tracker): Chậm hơn nhưng chính xác cao
- **MOSSE** (Minimum Output Sum of Squared Error): Rất nhanh, độ chính xác thấp
- **MedianFlow**: Cân bằng giữa tốc độ và độ chính xác

---

## PHẦN 4: HÀM MAIN - FLOW CHÍNH

### `main()`

**Mục đích:** Điều phối toàn bộ quá trình benchmark.

**Flow tổng thể:**
```
START
  ↓
1. CÁC HỐ HÌNH
  ↓
2. VÒNG LẶP 1: Lặp qua từng VIDEO
  ↓
3. VÒNG LẶP 2: Lặp qua từng TRACKER
  ↓
4. VÒNG LẶP 3: Lặp qua từng FRAME
  ↓
5. GHI KẾT QUẢ VÀO FILE CSV
  ↓
END
```

#### **Bước 1: Cấu hình**
```python
otb_dataset_path = "OTB-dataset-main\OTB100"
tracker_types = ['KCF', 'CSRT', 'MOSSE', 'MedianFlow']
videos_to_run = []  # Trống = chạy tất cả

all_results = {}  # Lưu kết quả tổng
detailed_csv_data = []  # Lưu kết quả chi tiết
```

**Tại sao:** Định nghĩa các tham số đầu vào và cấu trúc dữ liệu để lưu kết quả.

---

#### **Bước 2: VÒNG LẶP 1 - Lặp qua từng VIDEO**

**Flow:**
```
Lấy danh sách video (tất cả hoặc theo cấu hình)
  ↓
FOR EACH video IN video_names:
    ↓
  2.1. Tìm file ground truth
       - Gọi find_ground_truth_file()
    ↓
  2.2. Load danh sách frame
       - Gọi load_video_frames()
    ↓
  2.3. Kiểm tra tính hợp lệ
       - Có frame không?
       - Có ground truth không?
       - Số lượng frame = số lượng ground truth?
       - Nếu KHÔNG → Bỏ qua video này
    ↓
  2.4. Đọc frame đầu tiên và bbox đầu tiên
       - init_frame = cv2.imread(frame_paths[0])
       - init_bbox = ground_truth[0]
    ↓
  2.5. Chuyển sang VÒNG LẶP 2 (tracker)
```

**Tại sao cần kiểm tra:**
- Dataset OTB có thể có video lỗi, thiếu file
- Số frame và ground truth phải khớp để tính IoU đúng

---

#### **Bước 3: VÒNG LẶP 2 - Lặp qua từng TRACKER**

**Flow:**
```
FOR EACH tracker_type IN ['KCF', 'CSRT', 'MOSSE', 'MedianFlow']:
    ↓
  3.1. Khởi tạo tracker mới
       - tracker = create_tracker(tracker_type)
       - Nếu None → Bỏ qua tracker này
    ↓
  3.2. Khởi tạo tracker với frame đầu tiên
       - tracker.init(init_frame, init_bbox)
    ↓
  3.3. Chuẩn bị list lưu kết quả
       - iou_scores = []
       - frame_times = []
    ↓
  3.4. Chuyển sang VÒNG LẶP 3 (frame)
    ↓
  3.5. Tính kết quả trung bình cho video này
       - avg_iou = sum(iou_scores) / len(iou_scores)
       - avg_fps = 1.0 / (sum(frame_times) / len(frame_times))
    ↓
  3.6. Lưu kết quả
       - Thêm vào detailed_csv_data
       - Thêm vào all_results[tracker_type]
```

**Tại sao khởi tạo lại tracker mỗi lần:**
- Mỗi tracker cần bắt đầu từ trạng thái sạch
- Đảm bảo công bằng khi so sánh

---

#### **Bước 4: VÒNG LẶP 3 - Lặp qua từng FRAME**

**Flow:**
```
FOR i FROM 1 TO len(frame_paths) - 1:
    ↓
  4.1. Đọc frame hiện tại
       - frame = cv2.imread(frame_paths[i])
       - Nếu lỗi → Break
    ↓
  4.2. Bắt đầu đo thời gian
       - start_time = time.time()
    ↓
  4.3. Chạy tracker
       - (success, predicted_box) = tracker.update(frame)
    ↓
  4.4. Dừng đo thời gian
       - processing_time = time.time() - start_time
       - frame_times.append(processing_time)
    ↓
  4.5. Lấy ground truth box
       - gt_box = ground_truth[i]
    ↓
  4.6. Tính IoU
       - Nếu success = True:
           iou = calculate_iou(gt_box, predicted_box)
       - Nếu success = False:
           iou = 0.0  (tracker thất bại)
    ↓
  4.7. Lưu IoU score
       - iou_scores.append(iou)
```

**Tại sao bắt đầu từ frame 1 (không phải 0):**
- Frame 0 đã dùng để khởi tạo tracker (`tracker.init()`)
- Chỉ tracking từ frame thứ 2 trở đi

**Tại sao đo thời gian:**
- Tính FPS (frames per second) để đánh giá tốc độ xử lý
- FPS = 1 / average_processing_time

---

## PHẦN 5: GHI FILE VÀ IN KẾT QUẢ

### **5.1. Ghi file chi tiết (results_detailed.csv)**

**Mục đích:** Lưu kết quả IoU và FPS của từng tracker trên từng video.

**Flow:**
```
1. Kiểm tra có dữ liệu không
   - Nếu detailed_csv_data rỗng → In cảnh báo
  ↓
2. Mở file 'results_detailed.csv' (mode write)
  ↓
3. Tạo CSV writer với fieldnames từ dict đầu tiên
   - fieldnames = ['video', 'tracker', 'avg_iou', 'avg_fps']
  ↓
4. Ghi header
   - writer.writeheader()
  ↓
5. Ghi tất cả rows
   - writer.writerows(detailed_csv_data)
  ↓
6. Xử lý lỗi
   - PermissionError: File đang mở
   - Exception khác: In lỗi
```

**Format file:**
```csv
video,tracker,avg_iou,avg_fps
Basketball,KCF,0.6234,45
Basketball,CSRT,0.7123,18
Basketball,MOSSE,0.5421,78
...
```

---

### **5.2. Ghi file tổng kết (results_summary.csv)**

**Mục đích:** Lưu kết quả trung bình của từng tracker trên TẤT CẢ các video.

**Flow:**
```
1. Kiểm tra có kết quả không
   - Nếu all_results rỗng → In cảnh báo
  ↓
2. In header terminal
   - "KẾT QUẢ TỔNG KẾT..."
  ↓
3. Mở file 'results_summary.csv' (mode write)
  ↓
4. Tạo CSV writer với fieldnames
   - fieldnames = ['tracker', 'avg_iou', 'avg_fps']
  ↓
5. Ghi header
  ↓
6. FOR EACH tracker IN all_results:
     a. Tính trung bình IoU
        - total_avg_iou = sum(results['iou']) / len(results['iou'])
     b. Tính trung bình FPS
        - total_avg_fps = sum(results['fps']) / len(results['fps'])
     c. In ra terminal
     d. Ghi vào file CSV
  ↓
7. Xử lý lỗi (tương tự file chi tiết)
```

**Format file:**
```csv
tracker,avg_iou,avg_fps
KCF,0.5234,45
CSRT,0.6123,18
MOSSE,0.4421,78
MedianFlow,0.5012,32
```

---

## ĐIỂM KHỞI CHẠY

### `if __name__ == '__main__':`

**Flow:**
```
1. Kiểm tra opencv-contrib-python đã cài chưa
   - Thử tạo cv2.TrackerCSRT_create()
   - Nếu AttributeError:
     * In hướng dẫn cài đặt
     * sys.exit()
  ↓
2. Gọi main()
```

**Tại sao cần kiểm tra:**
- Các tracker (KCF, CSRT, MOSSE, MedianFlow) chỉ có trong `opencv-contrib-python`
- Package `opencv-python` chuẩn không có
- Tránh lỗi runtime giữa chừng

---

## FLOW TỔNG THỂ (SIMPLIFIED)

```
START
  ↓
Kiểm tra dependencies
  ↓
Cấu hình (dataset path, tracker list)
  ↓
┌─────────────────────────────────────┐
│ FOR EACH Video (100 videos)        │
│   ↓                                 │
│   Load ground truth + frames       │
│   Kiểm tra tính hợp lệ             │
│   ↓                                 │
│ ┌─────────────────────────────┐   │
│ │ FOR EACH Tracker (4 trackers)│   │
│ │   ↓                          │   │
│ │   Khởi tạo tracker           │   │
│ │   ↓                          │   │
│ │ ┌─────────────────────────┐ │   │
│ │ │ FOR EACH Frame          │ │   │
│ │ │   ↓                     │ │   │
│ │ │   Tracker update        │ │   │
│ │ │   Đo thời gian          │ │   │
│ │ │   Tính IoU              │ │   │
│ │ └─────────────────────────┘ │   │
│ │   ↓                          │   │
│ │   Tính avg_iou, avg_fps     │   │
│ │   Lưu kết quả               │   │
│ └─────────────────────────────┘   │
└─────────────────────────────────────┘
  ↓
Ghi file results_detailed.csv
  ↓
Ghi file results_summary.csv
  ↓
In kết quả tổng kết
  ↓
END
```

---

## TÓM TẮT CẤU TRÚC DỮ LIỆU

### `all_results`
```python
{
  'KCF': {
    'iou': [0.62, 0.58, 0.71, ...],  # 100 giá trị (100 videos)
    'fps': [45, 43, 47, ...]
  },
  'CSRT': {
    'iou': [0.71, 0.68, 0.79, ...],
    'fps': [18, 17, 19, ...]
  },
  ...
}
```

### `detailed_csv_data`
```python
[
  {'video': 'Basketball', 'tracker': 'KCF', 'avg_iou': '0.6234', 'avg_fps': '45'},
  {'video': 'Basketball', 'tracker': 'CSRT', 'avg_iou': '0.7123', 'avg_fps': '18'},
  ...
  # 400 rows total (100 videos × 4 trackers)
]
```

---

## KẾT LUẬN

Script này thực hiện benchmark hệ thống với:
- **Input:** OTB100 dataset (100 videos tracking)
- **Process:** Test 4 tracker algorithms × 100 videos = 400 lần chạy
- **Metrics:** IoU (độ chính xác) và FPS (tốc độ)
- **Output:** 2 file CSV (chi tiết + tổng kết)

**Thời gian chạy:** Khoảng 2-4 giờ cho toàn bộ dataset (tùy phần cứng).
