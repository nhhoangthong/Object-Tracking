# Giải Thích Chi Tiết File gradio_app.py

## Tổng Quan

File `gradio_app.py` xây dựng một ứng dụng web tương tác để tracking đối tượng trong video. Ứng dụng sử dụng thư viện Gradio để tạo giao diện người dùng, cho phép người dùng upload video, chọn frame bất kỳ, click chuột để vẽ bounding box, chọn thuật toán tracking, và xem kết quả trực tiếp trên trình duyệt. Đây là một wrapper UI cho các chức năng đã được implement trong module `object_tracking.py`.

---

## 1. Import và Khởi Tạo

### Import Thư Viện

```python
import gradio as gr
import cv2
import numpy as np
from object_tracking import (
    Trackers,
    get_video_info,
    get_frame_at_index,
    points_to_bbox,
    run_tracking
)
```

Đầu tiên, chúng ta import các thư viện cần thiết. Thư viện `gradio` là framework chính để xây dựng giao diện web một cách nhanh chóng mà không cần viết HTML/CSS/JavaScript. Thư viện `cv2` (OpenCV) được sử dụng để vẽ các hình dạng lên frame như hình tròn và hình chữ nhật khi người dùng click chuột. `numpy` được dùng để xử lý array của ảnh.

**Import từ module `object_tracking`:**

Từ module `object_tracking.py`, chúng ta import 5 thành phần chính:

#### 1. **Trackers** (List Constants)
```python
Trackers = ['CSRT', 'KCF', 'MOSSE', 'MedianFlow']
```
Đây là một list chứa tên các thuật toán tracking được hỗ trợ. List này được dùng làm choices cho Dropdown component trong UI, cho phép người dùng chọn thuật toán tracking mong muốn. Mỗi tracker có đặc điểm riêng về tốc độ và độ chính xác.

#### 2. **get_video_info(video_path: str) -> dict**
```python
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
```
Hàm này mở video bằng `cv2.VideoCapture()` và đọc các metadata quan trọng: tổng số frame (dùng để set maximum cho slider), fps (frames per second - dùng khi ghi video output), width và height (dimensions của video). Sau khi lấy xong thông tin, hàm giải phóng video capture bằng `cap.release()` để tránh memory leak. Hàm trả về dictionary chứa tất cả thông tin này.

#### 3. **get_frame_at_index(video_path: str, frame_index: int, convert_rgb: bool = True)**
```python
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
```
Hàm này lấy một frame cụ thể từ video tại vị trí `frame_index`. Nó sử dụng `cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)` để nhảy đến frame mong muốn thay vì phải đọc tuần tự từ đầu. Tham số `convert_rgb` (mặc định True) rất quan trọng: OpenCV mặc định đọc ảnh theo format BGR (Blue-Green-Red), nhưng Gradio và hầu hết các thư viện Python khác dùng RGB (Red-Green-Blue). Nếu không convert, màu sắc sẽ bị đảo ngược khi hiển thị trên UI (màu đỏ thành xanh và ngược lại).

#### 4. **points_to_bbox(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int, int, int]**
```python
def points_to_bbox(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Chuyển 2 điểm thành bbox (x, y, w, h)."""
    x1, y1 = p1
    x2, y2 = p2
    return (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
```
Hàm này chuyển đổi hai điểm bất kỳ thành định dạng bounding box chuẩn của OpenCV: `(x, y, width, height)`. Điều quan trọng là hàm tự động normalize - nó dùng `min()` để đảm bảo `x`, `y` luôn là góc trên-trái (tọa độ nhỏ nhất), và `abs()` để đảm bảo width và height luôn dương, bất kể người dùng kéo chuột theo hướng nào (từ trái-phải hoặc phải-trái, từ trên-xuống hoặc dưới-lên).

#### 5. **run_tracking(...) -> Tuple[Optional[str], int, str]**
```python
def run_tracking(
    video_path: str,
    tracker_name: str,
    bbox: Tuple[int, int, int, int],
    start_frame_idx: int = 0,
    output_path: Optional[str] = None,
    draw_overlay: bool = True
) -> Tuple[Optional[str], int, str]:
```
Đây là hàm chính thực hiện toàn bộ quá trình tracking. Hàm nhận các tham số: đường dẫn video, tên tracker, bounding box ban đầu, frame bắt đầu, và tùy chọn output path. Nó thực hiện các bước:
1. Khởi tạo tracker với `create_tracker(tracker_name)`
2. Mở video và seek đến frame bắt đầu
3. Khởi tạo VideoWriter để ghi video output với codec phù hợp
4. Init tracker với frame đầu tiên và bbox
5. Loop qua tất cả frame từ start đến cuối:
   - Gọi `tracker.update(frame)` để track đối tượng trong frame mới
   - Vẽ bounding box (xanh nếu thành công, hiển thị "Lost" nếu mất dấu)
   - Vẽ thêm tracker name và FPS lên frame
   - Ghi frame đã xử lý vào output video
6. Giải phóng resources và trả về tuple (output_path, frame_count, message)

Hàm này là "core business logic" của ứng dụng - nơi thực sự diễn ra magic của object tracking.

### Biến Global để Lưu Trạng Thái Click

```python
click_points = {"p1": None, "p2": None}
```

Đây là một dictionary global dùng để lưu trữ hai điểm mà người dùng click trên ảnh. Gradio là framework event-driven, mỗi lần người dùng tương tác (click chuột) sẽ gọi một callback function mới. Do đó, chúng ta cần một biến global để maintain state giữa các lần click. Khi người dùng click lần đầu, tọa độ sẽ được lưu vào `p1`, click lần hai sẽ lưu vào `p2`. Hai điểm này định nghĩa hai góc đối diện của bounding box mà người dùng muốn track.

---

## 2. Hàm Xử Lý Click Chuột

### Hàm handle_click()

```python
def handle_click(image, evt: gr.SelectData):
    global click_points
    
    if image is None:
        return image, "Chưa có ảnh"
    
    x, y = evt.index[0], evt.index[1]
    
    if click_points["p1"] is None:
        click_points["p1"] = (x, y)
        click_points["p2"] = None
        img_copy = image.copy()
        cv2.circle(img_copy, (x, y), 5, (255, 0, 0), -1)
        return img_copy, f"Điểm 1: ({x}, {y}) - Click điểm 2"
    else:
        click_points["p2"] = (x, y)
        img_copy = image.copy()
        p1, p2 = click_points["p1"], click_points["p2"]
        cv2.rectangle(img_copy, p1, p2, (0, 255, 0), 2)
        return img_copy, f"Box: ({p1[0]}, {p1[1]}) -> ({p2[0]}, {p2[1]})"
```

Hàm `handle_click` là callback được gọi mỗi khi người dùng click lên component Image trong Gradio. Tham số `image` là numpy array của ảnh hiện tại (frame gốc chưa bị modified), còn `evt` là một object đặc biệt của Gradio chứa thông tin về sự kiện click, trong đó `evt.index` chứa tọa độ `(x, y)` của điểm được click. 

**Flow xử lý:**

1. **Kiểm tra ảnh**: Nếu `image` là `None` thì trả về nguyên image và thông báo lỗi.

2. **Extract tọa độ**: Lấy tọa độ `x, y` từ `evt.index[0]` và `evt.index[1]`. Lưu ý `evt.index` trả về tuple `(x, y)` theo tọa độ pixel, với gốc `(0, 0)` ở góc trên-trái của ảnh.

3. **Click đầu tiên** (nếu `p1` là `None`):
   - Lưu tọa độ vào `click_points["p1"]`
   - Reset `p2` về `None`
   - Tạo copy của ảnh gốc bằng `image.copy()`
   - Vẽ hình tròn đỏ tại vị trí click: `cv2.circle(img_copy, (x, y), 5, (255, 0, 0), -1)`
     - Bán kính 5 pixels
     - Màu `(255, 0, 0)` là đỏ trong RGB
     - `-1` nghĩa là fill đầy hình tròn
   - Trả về ảnh đã vẽ và message hướng dẫn click điểm 2

4. **Click thứ hai** (nếu `p1` đã có giá trị):
   - Lưu tọa độ vào `click_points["p2"]`
   - Tạo copy của ảnh gốc
   - Vẽ rectangle xanh: `cv2.rectangle(img_copy, p1, p2, (0, 255, 0), 2)`
     - Màu `(0, 255, 0)` là xanh lá trong RGB
     - Độ dày nét 2 pixels
     - OpenCV tự động xử lý `p1` và `p2` ở bất kỳ vị trí nào
   - Trả về ảnh đã vẽ và hiển thị tọa độ cả hai điểm

### Ý Nghĩa Thiết Kế

Thiết kế này cho phép người dùng linh hoạt trong việc chọn vùng tracking:
- **Intuitive**: Click chuột thay vì nhập tọa độ số
- **Visual feedback**: Điểm đỏ cho click đầu, rectangle xanh cho bounding box hoàn chỉnh
- **Safe**: Sử dụng `image.copy()` đảm bảo không modify ảnh gốc
- **Flexible**: Người dùng có thể reset và chọn lại bất cứ lúc nào

---

## 3. Hàm Reset

### Hàm reset_click_points()

```python
def reset_click_points():
    global click_points
    click_points = {"p1": None, "p2": None}
```

Đây là một utility function đơn giản để reset trạng thái của click points về giá trị ban đầu. Hàm này set cả `p1` và `p2` về `None`, cho phép người dùng bắt đầu quá trình chọn bounding box từ đầu. Việc tách hàm này ra giúp code dễ maintain và có thể được gọi từ nhiều nơi khác nhau (ví dụ khi upload video mới, khi thay đổi frame, hoặc khi nhấn nút Reset).

### Hàm reset_box()

```python
def reset_box(image):
    reset_click_points()
    return image, "Click điểm 1"
```

Hàm `reset_box` được dùng làm callback cho nút "Reset" trong UI. Nó gọi `reset_click_points()` để xóa các điểm đã click, sau đó trả về ảnh gốc (không có vẽ gì) và message hướng dẫn người dùng click điểm đầu tiên. Tham số `image` ở đây là ảnh gốc được lưu trong State (sẽ được giải thích sau). Khi người dùng nhấn nút Reset, UI sẽ hiển thị lại frame sạch sẽ và reset state để có thể chọn vùng mới.

---

## 4. Hàm Lấy Bounding Box

### Hàm get_bbox_from_clicks()

```python
def get_bbox_from_clicks():
    global click_points
    if click_points["p1"] is None or click_points["p2"] is None:
        return None
    return points_to_bbox(click_points["p1"], click_points["p2"])
```

Hàm này chuyển đổi hai điểm đã click thành định dạng bounding box chuẩn của OpenCV. Đầu tiên, nó kiểm tra xem cả hai điểm đã được click chưa - nếu một trong hai vẫn là `None`, nghĩa là người dùng chưa hoàn thành việc chọn box, hàm trả về `None` để báo hiệu không có bbox hợp lệ. Nếu cả hai điểm đều có giá trị, hàm gọi `points_to_bbox()` từ module `object_tracking` để chuyển đổi hai điểm thành tuple `(x, y, width, height)`. Hàm `points_to_bbox` xử lý việc normalize - đảm bảo `x`, `y` là góc trên-trái và `width`, `height` luôn dương, bất kể người dùng kéo chuột theo hướng nào.

---

## 5. Xử Lý Upload Video

### Hàm on_video_upload()

```python
def on_video_upload(video_path):
    reset_click_points()
    if video_path is None:
        return gr.update(value=0, maximum=1), None, "Click điểm 1"
```

Hàm `on_video_upload` được trigger mỗi khi người dùng upload một video mới. Tham số `video_path` là đường dẫn tạm thời đến file video đã được upload lên server Gradio. Đầu tiên, hàm gọi `reset_click_points()` để xóa bất kỳ bounding box nào đã được chọn từ video trước đó. Nếu `video_path` là `None` (người dùng xóa file hoặc chưa upload), hàm trả về các giá trị mặc định: cập nhật slider về giá trị 0 với maximum là 1, image là `None`, và message hướng dẫn.

```python
    info = get_video_info(video_path)
    first_frame = get_frame_at_index(video_path, 0)
    return (
        gr.update(maximum=info['total_frames'] - 1, value=0, 
                  label=f"Chọn Frame (Tổng: {info['total_frames']})"),
        first_frame,
        "Click điểm 1"
    )
```

Khi có video hợp lệ, hàm sử dụng `get_video_info()` để lấy metadata của video, đặc biệt là tổng số frame. Sau đó, `get_frame_at_index()` được gọi với index 0 để lấy frame đầu tiên của video (đã được convert sang RGB để hiển thị đúng trên Gradio). Hàm trả về một tuple ba phần tử:

1. **gr.update()** cho slider: Đây là một cách đặc biệt trong Gradio để cập nhật properties của một component mà không cần recreate nó. Chúng ta set `maximum` của slider là tổng số frame trừ 1 (vì index bắt đầu từ 0), set `value` về 0 (frame đầu tiên), và update `label` để hiển thị tổng số frame cho người dùng biết. Việc dùng `gr.update()` giữ nguyên các properties khác của slider như `minimum` và `step`.

2. **first_frame**: Frame đầu tiên dạng numpy array (RGB) sẽ được hiển thị trong Image component, cho phép người dùng ngay lập tức chọn vùng tracking.

3. **Message string**: Hướng dẫn người dùng click điểm đầu tiên.

Thiết kế này tạo trải nghiệm smooth - ngay sau khi upload video, người dùng thấy frame đầu tiên và có thể bắt đầu chọn vùng ngay lập tức.

---

## 6. Xử Lý Thay Đổi Frame

### Hàm on_frame_change()

```python
def on_frame_change(video_path, frame_index):
    reset_click_points()
    frame = get_frame_at_index(video_path, frame_index)
    return frame, "Click điểm 1"
```

Hàm `on_frame_change` được gọi khi người dùng kéo slider để chọn frame khác. Nó nhận hai tham số: `video_path` (đường dẫn video hiện tại) và `frame_index` (vị trí frame mới được chọn từ slider). Đầu tiên, hàm reset các click points vì người dùng đang chọn frame mới để track, nên bounding box cũ không còn phù hợp nữa. Sau đó, `get_frame_at_index()` được gọi để lấy frame tại vị trí mới. Hàm trả về frame mới và message hướng dẫn click lại từ đầu.

**Lưu ý quan trọng**: Hàm này được bind với event `slider_frame.release` (không phải `change`). Điều này có nghĩa là callback chỉ được gọi khi người dùng **thả chuột** sau khi kéo slider, không phải mỗi lần giá trị slider thay đổi. Đây là một optimization quan trọng vì việc đọc frame từ video là operation tương đối nặng - nếu dùng `change`, mỗi lần slider di chuyển 1 pixel sẽ gọi function và có thể làm UI bị lag.

---

## 7. Hàm Chạy Tracking

### Hàm on_run_tracking()

```python
def on_run_tracking(video_path, tracker_name, start_frame_idx):
    if video_path is None:
        return None, None
    
    bbox = get_bbox_from_clicks()
    if bbox is None:
        return None, None
    
    output_path, frame_count, msg = run_tracking(
        video_path=video_path,
        tracker_name=tracker_name,
        bbox=bbox,
        start_frame_idx=int(start_frame_idx)
    )
    
    if output_path:
        return output_path, output_path
    return None, None
```

Hàm `on_run_tracking` là callback chính khi người dùng nhấn nút "RUN" để bắt đầu quá trình tracking. 

**Flow xử lý:**

1. **Kiểm tra video**: Nếu không có video path, trả về `None` cho cả hai output (video player và download link).

2. **Lấy bounding box**: Gọi `get_bbox_from_clicks()` để lấy bbox từ hai điểm đã click. Nếu bbox là `None` (người dùng chưa click đủ hai điểm), trả về `None` để không làm gì.

3. **Chạy tracking**: Gọi hàm `run_tracking()` từ module `object_tracking` với các tham số:
   - `video_path`: Đường dẫn video
   - `tracker_name`: Thuật toán tracking từ dropdown
   - `bbox`: Bounding box đã chuyển đổi sang format `(x, y, w, h)`
   - `start_frame_idx`: Frame bắt đầu (cast sang `int` vì slider có thể trả về float)
   
   Hàm `run_tracking()` thực hiện:
   - Load video và khởi tạo tracker
   - Loop qua tất cả frame từ start_frame_idx đến cuối video
   - Track đối tượng trong mỗi frame
   - Vẽ bounding box và thông tin lên frame
   - Ghi video output với codec phù hợp
   
   Quá trình này có thể mất vài giây đến vài phút tùy độ dài video. Gradio hiển thị loading indicator trong thời gian chờ.

4. **Trả về kết quả**: Nếu có `output_path`, trả về path này hai lần để cập nhật:
   - Component `Video`: Play video trực tiếp trong browser
   - Component `File`: Link download video
   
   Nếu có lỗi (output_path là None), trả về None cho cả hai.

---

## 8. Xây Dựng Giao Diện với Gradio Blocks

### Khởi Tạo Blocks

```python
with gr.Blocks(title="Demo Object Tracking") as demo:
```

Gradio cung cấp hai cách tạo UI: `Interface` (đơn giản, template sẵn) và `Blocks` (linh hoạt, custom layout). Chúng ta sử dụng `Blocks` vì cần layout phức tạp với nhiều components và interactions tùy chỉnh. Context manager `with` được dùng để define scope của demo app. Tham số `title` set title cho tab trình duyệt.

### Layout Chính: Row với 2 Columns

```python
    with gr.Row():
        with gr.Column(scale=4):
```

Gradio sử dụng hệ thống layout dựa trên Row và Column giống như grid system. `gr.Row()` tạo một hàng ngang, và bên trong chúng ta tạo các `gr.Column()` để chia thành cột. Tham số `scale=4` nghĩa là cột này chiếm 4 phần trong tổng số phần của row. Cột đầu tiên (trái) chứa các controls và input.

```python
            inp_video = gr.File(label="Upload Video", file_types=["video"])
```

Component `gr.File()` tạo một file uploader. Tham số `label` hiển thị text phía trên component. `file_types=["video"]` giới hạn chỉ cho phép upload các file video (browser sẽ filter sẵn khi mở file dialog). Khi người dùng upload file, Gradio tự động lưu file vào thư mục temporary và trả về đường dẫn.

```python
            slider_frame = gr.Slider(minimum=0, maximum=1, step=1, value=0, 
                                     label="Chọn Frame bắt đầu")
```

Component `gr.Slider()` tạo một thanh trượt. Initially, chúng ta set `maximum=1` (giá trị placeholder) vì chưa biết video có bao nhiêu frame - giá trị này sẽ được update động khi video được upload. `step=1` nghĩa là slider chỉ có thể chọn giá trị nguyên (frame index). `value=0` là giá trị ban đầu.

```python
            frame_image = gr.Image(label="Click 2 điểm để vẽ box", 
                                   type="numpy", interactive=False, height=400)
```

Component `gr.Image()` hiển thị ảnh. Tham số quan trọng ở đây:
- `type="numpy"`: Gradio sẽ xử lý ảnh dưới dạng numpy array (thay vì PIL Image hoặc file path). Điều này quan trọng vì OpenCV hoạt động với numpy arrays.
- `interactive=False`: Người dùng không thể upload ảnh vào component này (nó chỉ để display). Tuy nhiên, vẫn có thể click vào ảnh để trigger select event.
- `height=400`: Giới hạn chiều cao display để UI không bị quá dài.

```python
            box_status = gr.Textbox(label="Tọa độ", interactive=False)
```

`gr.Textbox()` với `interactive=False` tạo một readonly textbox để hiển thị thông tin (tọa độ các điểm đã click). Người dùng không thể edit text trong đây.

```python
            btn_reset = gr.Button("Reset", variant="secondary")
```

`gr.Button()` tạo nút bấm. `variant="secondary"` cho styling khác biệt (thường là màu xám nhạt hơn) để phân biệt với nút chính "RUN".

```python
            with gr.Row():
                inp_tracker = gr.Dropdown(Trackers, value="CSRT", show_label=False)
                btn_run = gr.Button("RUN", variant="primary")
```

Nested row bên trong column để đặt dropdown và nút RUN cạnh nhau trên cùng một hàng. `gr.Dropdown()` nhận danh sách `Trackers` (đã import từ module) làm choices, với giá trị mặc định là "CSRT". `show_label=False` ẩn label vì UI đã rõ ràng. Button với `variant="primary"` thường có màu nổi bật (như màu xanh) để nhấn mạnh đây là action chính.

### Cột Output (Phải)

```python
        with gr.Column(scale=6):
            out_video = gr.Video(label="Video Output")
            out_file = gr.File(label="Tải về")
```

Cột thứ hai với `scale=6` chiếm nhiều không gian hơn (ratio 4:6, tương đương 40%:60%). Component `gr.Video()` tạo video player có thể play video trực tiếp trong browser. Component `gr.File()` thứ hai này ở chế độ output (không phải input), cho phép người dùng download file video đã xử lý về máy.

---

## 9. Event Bindings (Kết Nối Events)

Phần này là "bộ não" của ứng dụng - nơi định nghĩa các components phản ứng như thế nào với user interactions.

### Event 1: Upload Video

```python
    inp_video.change(fn=on_video_upload, inputs=inp_video, 
                     outputs=[slider_frame, frame_image, box_status])
```

Khi component `inp_video` thay đổi (người dùng upload file mới hoặc xóa file), event handler `on_video_upload` được gọi. Cú pháp:
- `fn=on_video_upload`: Function callback
- `inputs=inp_video`: Giá trị của `inp_video` (đường dẫn file) được pass làm argument vào function
- `outputs=[slider_frame, frame_image, box_status]`: Ba giá trị return từ function sẽ update ba components này theo thứ tự

Kết quả: Khi upload video, slider được update với số frame đúng, ảnh hiển thị frame đầu tiên, và textbox hiển thị hướng dẫn.

### Event 2: Thay Đổi Frame

```python
    slider_frame.release(fn=on_frame_change, inputs=[inp_video, slider_frame], 
                         outputs=[frame_image, box_status])
```

Event `release` trigger khi người dùng thả chuột sau khi kéo slider. Function `on_frame_change` nhận hai inputs (video path và frame index mới) và update ảnh hiển thị cùng status message.

### Event 3: State Management cho Frame Gốc

```python
    original_frame = gr.State(None)
```

`gr.State()` là một component đặc biệt trong Gradio - nó không hiển thị trên UI nhưng lưu trữ data giữa các function calls. Đây là một internal state variable, giống như React state. Chúng ta cần lưu frame gốc (chưa vẽ) vì:

1. Khi người dùng click lần đầu, chúng ta vẽ điểm đỏ lên frame
2. Khi click lần hai, nếu chúng ta vẽ lên frame đã có điểm đỏ, kết quả sẽ có cả điểm đỏ và rectangle
3. Chúng ta cần frame "sạch" ban đầu để vẽ lại từ đầu mỗi lần click

```python
    inp_video.change(fn=lambda v: get_frame_at_index(v, 0), 
                     inputs=inp_video, outputs=original_frame)
```

Khi upload video mới, chúng ta lưu frame đầu tiên vào state. Lambda function inline gọi `get_frame_at_index` với index 0.

```python
    slider_frame.release(fn=lambda v, i: get_frame_at_index(v, i), 
                         inputs=[inp_video, slider_frame], outputs=original_frame)
```

Tương tự, khi slider thay đổi, chúng ta lưu frame mới vào state. Lambda nhận hai arguments (video path và frame index) để get frame.

**Tại sao cần cả `frame_image` và `original_frame`?**
- `frame_image`: Hiển thị trên UI, có thể có vẽ thêm (điểm đỏ, rectangle)
- `original_frame`: State internal, luôn giữ frame sạch để có thể vẽ lại

### Event 4: Click Trên Ảnh

```python
    frame_image.select(fn=handle_click, inputs=[original_frame], 
                       outputs=[frame_image, box_status])
```

Event `select` trigger khi người dùng click vào Image component. Đặc biệt ở đây:
- **Input**: Chúng ta pass `original_frame` (state - frame sạch), không phải `frame_image` (có thể đã vẽ)
- **Outputs**: Update `frame_image` (hiển thị) và `box_status` (message)
- Function `handle_click` tự động nhận thêm tham số `evt: gr.SelectData` chứa tọa độ click

**Flow logic**:
1. Người dùng click vào ảnh đang hiển thị (`frame_image`)
2. Gradio gọi `handle_click` với frame gốc (`original_frame`)
3. Function vẽ lên frame gốc và return
4. Gradio update `frame_image` với ảnh đã vẽ mới

Thiết kế này đảm bảo mỗi lần click đều vẽ trên frame sạch, không bị chồng chéo.

### Event 5: Reset Button

```python
    btn_reset.click(fn=reset_box, inputs=[original_frame], 
                    outputs=[frame_image, box_status])
```

Khi người dùng click nút Reset, function `reset_box` được gọi với frame gốc, reset state, và return frame sạch để hiển thị lại.

### Event 6: Run Tracking

```python
    btn_run.click(fn=on_run_tracking, inputs=[inp_video, inp_tracker, slider_frame], 
                  outputs=[out_video, out_file])
```

Khi nhấn nút RUN, function `on_run_tracking` nhận ba inputs (video path, tracker name, start frame) và sau khi xử lý xong, update cả video player và download file với đường dẫn video output.

---

## 10. Launch Application

```python
if __name__ == "__main__":
    demo.launch()
```

Đây là Python idiom chuẩn để code chỉ chạy khi file được execute trực tiếp (không phải khi import). `demo.launch()` start Gradio server, mở browser tự động, và print URL. Mặc định, server chạy local trên `http://127.0.0.1:7860`. Có thể thêm parameters như `share=True` để tạo public link, `server_port=8080` để đổi port, hoặc `auth=("username", "password")` để thêm authentication.

---

## Luồng Hoạt Động Tổng Thể

### Workflow Từ Đầu Đến Cuối

Khi người dùng mở ứng dụng, họ sẽ trải qua flow sau:

1. **Upload Video**: Người dùng click vào File component và chọn file video từ máy tính. Gradio upload file lên server temporary directory và trigger event `inp_video.change`.

2. **Xử Lý Video Upload**: Function `on_video_upload` được gọi, nó đọc metadata video để biết tổng số frame, update slider với range đúng, load frame đầu tiên và hiển thị. Đồng thời, frame này được lưu vào `original_frame` state.

3. **Chọn Frame (Optional)**: Nếu người dùng không muốn track từ frame đầu tiên, họ có thể kéo slider để chọn frame khác. Khi thả chuột, `on_frame_change` được gọi, load frame mới và update cả display và state.

4. **Click Điểm 1**: Người dùng click vào vị trí đầu tiên trên ảnh (ví dụ góc trên-trái của đối tượng cần track). Event `select` trigger `handle_click`, function kiểm tra thấy `p1` là None nên đây là click đầu tiên. Nó lưu tọa độ vào `click_points["p1"]`, vẽ điểm đỏ lên frame gốc, và update display. User thấy điểm đỏ và message "Click điểm 2".

5. **Click Điểm 2**: Người dùng click vị trí thứ hai (ví dụ góc dưới-phải của đối tượng). `handle_click` được gọi lại, lần này `p1` đã có giá trị nên nó biết đây là click thứ hai. Function lưu tọa độ vào `p2`, vẽ rectangle xanh từ `p1` đến `p2` trên frame gốc, và update display. User thấy bounding box xanh bao quanh vùng đã chọn.

6. **Chọn Tracker (Optional)**: Người dùng có thể chọn thuật toán tracking từ dropdown. Mặc định là CSRT. Mỗi thuật toán có trade-off khác nhau về tốc độ và độ chính xác.

7. **Run Tracking**: Người dùng nhấn nút RUN. Function `on_run_tracking` được gọi, nó:
   - Lấy bbox từ `get_bbox_from_clicks()`, chuyển đổi hai điểm thành format `(x, y, w, h)`
   - Gọi `run_tracking()` với tất cả parameters
   - `run_tracking()` mở video, khởi tạo tracker với frame bắt đầu và bbox, loop qua tất cả frame từ start đến cuối, track đối tượng, vẽ bounding box và info lên mỗi frame, ghi vào file video mới
   - Sau khi hoàn tất (có thể mất vài phút), function trả về đường dẫn video output

8. **Hiển Thị Kết Quả**: Gradio nhận đường dẫn video output và update component Video để play video, đồng thời update File component để cho phép download. Người dùng có thể xem video tracking trực tiếp trong browser và/hoặc download về máy.

9. **Retry (Optional)**: Nếu kết quả không như mong muốn, người dùng có thể:
   - Nhấn Reset để chọn lại bounding box
   - Kéo slider để chọn frame khác
   - Chọn thuật toán tracker khác
   - Upload video mới

---

## Các Pattern và Best Practices

### 1. State Management với gr.State()

Gradio là stateless framework - mỗi function call độc lập. Để maintain state giữa các calls (như click points), chúng ta sử dụng:
- **Global variables** (`click_points`): Đơn giản nhưng có vấn đề với concurrent users
- **gr.State()** (`original_frame`): Best practice cho session-specific data

Trong production app, nên chuyển `click_points` thành State thay vì global variable để avoid race conditions khi nhiều user cùng dùng.

### 2. Separation of Concerns

Code được tổ chức rõ ràng:
- **object_tracking.py**: Core logic (tracking algorithms, video processing)
- **gradio_app.py**: UI layer (interface, event handling)

Thiết kế này cho phép:
- Test core logic độc lập với UI
- Reuse tracking functions trong các contexts khác (CLI, batch processing)
- Dễ maintain và debug

### 3. Event Binding Strategy

Sử dụng các events phù hợp:
- `change`: Trigger ngay khi value thay đổi (dùng cho file upload)
- `release`: Trigger khi thả chuột (dùng cho slider để tránh spam)
- `click`: Trigger khi click button
- `select`: Trigger khi click vào vị trí trên Image

### 4. Progressive Disclosure

UI được thiết kế để user chỉ thấy info cần thiết:
- Ban đầu: Chỉ thấy upload button
- Sau upload: Slider và frame xuất hiện
- Sau chọn box: Có thể run tracking
- Sau tracking: Video output và download link

### 5. User Feedback

App luôn cho user biết họ đang ở đâu trong workflow:
- "Click điểm 1": Chưa có điểm nào
- "Điểm 1: (x, y) - Click điểm 2": Đã có điểm đầu
- "Box: (x1, y1) -> (x2, y2)": Hoàn thành selection
- Gradio tự động hiển thị loading spinner khi processing

---

## Cải Tiến Có Thể

### 1. Error Handling

Hiện tại app thiếu error messages rõ ràng. Có thể thêm:
```python
def on_run_tracking(video_path, tracker_name, start_frame_idx):
    if video_path is None:
        return None, None, gr.Warning("Vui lòng upload video!")
    bbox = get_bbox_from_clicks()
    if bbox is None:
        return None, None, gr.Warning("Vui lòng chọn vùng tracking!")
    # ... rest of code
```

### 2. Progress Bar

Thêm progress indicator cho quá trình tracking:
```python
def on_run_tracking(video_path, tracker_name, start_frame_idx, progress=gr.Progress()):
    # ... code
    for i, frame in enumerate(frames):
        # tracking logic
        progress((i+1)/total_frames, desc=f"Tracking frame {i+1}/{total_frames}")
```

### 3. Preview Mode

Cho phép user preview tracking trên một vài frame trước khi process toàn bộ video:
```python
btn_preview = gr.Button("Preview (10 frames)")
btn_preview.click(fn=preview_tracking, inputs=[...], outputs=[preview_video])
```

### 4. Multi-Object Tracking

Mở rộng để track nhiều objects:
```python
click_points = {"objects": []}  # List of bboxes
# Add "Add Object" button
# Display multiple bounding boxes với màu khác nhau
```

### 5. Session State Management

Chuyển global variable thành proper session state:
```python
session_state = gr.State({"click_points": {"p1": None, "p2": None}})
def handle_click(image, state, evt):
    state["click_points"]["p1"] = ...
    return image, message, state
```

### 6. Caching

Cache video info và frames đã load:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_frame_cached(video_path, frame_idx):
    return get_frame_at_index(video_path, frame_idx)
```

### 7. Keyboard Shortcuts

Sử dụng Gradio's keyboard event handling:
```python
# Press 'r' to reset, 'space' to run, etc.
```

---

## Tổng Kết

File `gradio_app.py` là một ứng dụng web hoàn chỉnh cho object tracking, được xây dựng với kiến trúc rõ ràng và user experience tốt. Nó kết hợp các concepts quan trọng:

- **Event-driven programming**: UI phản ứng với user actions qua event handlers
- **State management**: Sử dụng global variables và gr.State để maintain data
- **Separation of concerns**: UI logic tách biệt với business logic
- **Progressive enhancement**: User được guided từng bước một cách tự nhiên
- **Visual feedback**: Vẽ trực tiếp lên ảnh để user thấy những gì họ đã chọn

Thiết kế cho phép người dùng không cần biết gì về code hay command line - chỉ cần upload video, click chuột chọn vùng, và nhận kết quả. Đây là một excellent example của việc biến một thuật toán phức tạp thành một tool dễ sử dụng cho end users.
