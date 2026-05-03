import cv2
import tempfile
import numpy as np
from typing import Tuple, Optional

# Constants
GREEN = (0, 255, 0)
RED = (0, 0, 255)
BLUE = (255, 0, 0)
DEFAULT_FPS = 24.0
DEFAULT_FONT_SCALE = 0.7
DEFAULT_FONT_THICKNESS = 2

Trackers = ['CSRT', 'KCF', 'MOSSE', 'MedianFlow']


def create_tracker(tracker_name: str):
    """Tạo tracker theo tên. Xem DOCS.md để biết chi tiết."""
    if tracker_name == 'CSRT':
        return cv2.TrackerCSRT_create()
    elif tracker_name == 'KCF':
        return cv2.TrackerKCF_create()
    elif tracker_name == 'MOSSE':
        return cv2.legacy.TrackerMOSSE_create()
    elif tracker_name == 'MedianFlow':
        return cv2.legacy.TrackerMedianFlow_create()
    else:
        raise ValueError(f"Tracker '{tracker_name}' không hỗ trợ. Chọn: {Trackers}")


def get_video_info(video_path: str) -> dict:
    """Lấy thông tin video (total_frames, fps, width, height)."""
    if video_path is None:
        return None
    cap = cv2.VideoCapture(video_path)
    info = {
        'total_frames': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'fps': cap.get(cv2.CAP_PROP_FPS) or DEFAULT_FPS,
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    }
    cap.release()
    return info


def get_frame_at_index(video_path: str, frame_index: int, convert_rgb: bool = True):
    """Lấy frame tại vị trí frame_index."""
    if video_path is None:
        return None
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if convert_rgb else frame
    return None


def points_to_bbox(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Chuyển 2 điểm thành bbox (x, y, w, h)."""
    x1, y1 = p1
    x2, y2 = p2
    return (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))


def run_tracking(
    video_path: str,
    tracker_name: str,
    bbox: Tuple[int, int, int, int],
    start_frame_idx: int = 0,
    output_path: Optional[str] = None,
    draw_overlay: bool = True
) -> Tuple[Optional[str], int, str]:
    """
    Chạy tracking trên video.
    
    Returns: (output_path, frame_count, message)
    """
    if video_path is None:
        return None, 0, "Lỗi: Chưa có video!"
    if bbox is None or len(bbox) != 4:
        return None, 0, "Lỗi: Bbox không hợp lệ!"
    if bbox[2] == 0 or bbox[3] == 0:
        return None, 0, "Lỗi: Box quá nhỏ!"

    try:
        tracker = create_tracker(tracker_name)
    except Exception as e:
        return None, 0, f"Lỗi khởi tạo Tracker: {e}"

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_idx)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or DEFAULT_FPS

    if output_path is None:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            output_path = tmp.name

    fourcc_options = ['avc1', 'H264', 'X264', 'mp4']
    out = None
    for codec in fourcc_options:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if out.isOpened():
            break
        out.release()
    if not out or not out.isOpened():
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    ret, frame = cap.read()
    if not ret:
        cap.release()
        out.release()
        return None, 0, "Lỗi đọc frame đầu."

    tracker.init(frame, bbox)

    if draw_overlay:
        p1 = (int(bbox[0]), int(bbox[1]))
        p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
        cv2.rectangle(frame, p1, p2, GREEN, 3)
    out.write(frame)

    frame_count = 1
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timer = cv2.getTickCount()
        success, box = tracker.update(frame)
        fps_val = cv2.getTickFrequency() / (cv2.getTickCount() - timer)

        if draw_overlay:
            if success:
                x, y, w, h = [int(v) for v in box]
                cv2.rectangle(frame, (x, y), (x + w, y + h), GREEN, 2)
                cv2.putText(frame, tracker_name, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, DEFAULT_FONT_SCALE, GREEN, DEFAULT_FONT_THICKNESS)
            else:
                cv2.putText(frame, "Lost", (50, 80),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.75, RED, DEFAULT_FONT_THICKNESS)
            cv2.putText(frame, f"FPS: {int(fps_val)}", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, DEFAULT_FONT_SCALE, BLUE, DEFAULT_FONT_THICKNESS)

        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()
    return output_path, frame_count, f"Hoàn tất! Track {frame_count} frames."


# def track_video_interactive(video_path: str, tracker_name: str = 'CSRT'):
#     """Chạy tracking với GUI OpenCV. Nhấn 'q' để thoát."""
#     cap = cv2.VideoCapture(video_path)
    
#     ret, frame = cap.read()
#     if not ret:
#         print("Không thể đọc video")
#         return
    
#     print("Kéo chuột chọn vùng, ENTER xác nhận, C hủy")
#     bbox = cv2.selectROI("Tracking", frame, False)
#     cv2.destroyWindow("Tracking")
    
#     if bbox[2] == 0 or bbox[3] == 0:
#         print("Chưa chọn vùng")
#         cap.release()
#         return
    
#     try:
#         tracker = create_tracker(tracker_name)
#     except Exception as e:
#         print(f"Lỗi: {e}")
#         cap.release()
#         return
    
#     tracker.init(frame, bbox)
#     print(f"Tracking với {tracker_name}... Nhấn 'q' để thoát")
    
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
        
#         success, box = tracker.update(frame)
        
#         if success:
#             x, y, w, h = [int(v) for v in box]
#             cv2.rectangle(frame, (x, y), (x + w, y + h), GREEN, 2)
#             cv2.putText(frame, f"Tracking ({tracker_name})", (x, y - 5),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 2)
#         else:
#             cv2.putText(frame, "Lost", (100, 80),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.75, RED, 2)
        
#         cv2.imshow("Frame", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
    
#     cap.release()
#     cv2.destroyAllWindows()


# if __name__ == "__main__":
    video_path = "Videos/People.mp4"
    print(f"Video: {video_path}")
    track_video_interactive(video_path, tracker_name='CSRT')
