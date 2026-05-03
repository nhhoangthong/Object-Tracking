# Giải Thích Chi Tiết File plot_results.py

## Tổng Quan

File `plot_results.py` đóng vai trò như một cây cầu nối giữa dữ liệu số khô khan và insight trực quan dễ hiểu. Sau khi file `benchmark.py` chạy xong và tạo ra file `results_summary.csv` chứa đầy những con số về IoU và FPS, file này sẽ biến những con số đó thành những biểu đồ màu sắc, giúp chúng ta nhìn thấy ngay được tracker nào tốt nhất, nhanh nhất, và có sự đánh đổi như thế nào giữa tốc độ và độ chính xác. Chương trình tạo ra bốn loại biểu đồ khác nhau để phân tích hiệu suất từ nhiều góc độ: leaderboards để xếp hạng, consolidated chart để xem tổng quan, và scatter plot để hiểu mối quan hệ trade-off.

---

## 1. Khởi Đầu: Import Các Thư Viện Cần Thiết

```python
import pandas as pd
import matplotlib.pyplot as plt
import os
```

Ngay từ những dòng đầu tiên, file `plot_results.py` import ba thư viện quan trọng, mỗi thư viện đảm nhận một vai trò riêng trong công việc visualization. Thư viện **pandas** (với alias `pd`) là công cụ data analysis mạnh mẽ nhất của Python ecosystem, được thiết kế đặc biệt để làm việc với dữ liệu dạng bảng. Trong file này, pandas được dùng để đọc file CSV thông qua hàm `read_csv()` - một hàm thông minh có khả năng tự động phát hiện delimiter, parse header row thành column names, và convert data sang đúng data type. Pandas không chỉ đơn thuần đọc file mà còn biến data thành DataFrame object - một data structure 2D giống như Excel spreadsheet, cho phép chúng ta dễ dàng sort (`df.sort_values()`), filter, và aggregate data. Điều đặc biệt là pandas cung cấp khả năng indexing linh hoạt với `.iloc[]` để access data theo vị trí số.

Thư viện thứ hai, **matplotlib.pyplot** (alias `plt`), là trái tim của toàn bộ chương trình visualization này. Matplotlib là thư viện vẽ biểu đồ chuẩn của Python, được phát triển từ năm 2003 và đã trở thành tiêu chuẩn công nghiệp. Module `pyplot` cung cấp interface giống MATLAB, giúp việc tạo biểu đồ trở nên trực quan. Trong file này, pyplot được dùng để tạo nhiều loại biểu đồ: horizontal bar chart với `plt.barh()` cho leaderboards, scatter plot với `plt.scatter()` cho trade-off analysis, và còn cho phép customize mọi thứ từ màu sắc, labels (`plt.xlabel()`, `plt.ylabel()`), titles (`plt.title()`), đến layout (`plt.tight_layout()`). Matplotlib có thể lưu biểu đồ ra nhiều format file khác nhau bằng `plt.savefig()`.

Cuối cùng, module **os** là một module chuẩn của Python để tương tác với operating system và file system. Trong file này, os được sử dụng cho ba mục đích chính: kiểm tra sự tồn tại của folder với `os.path.exists()`, tạo folder mới với `os.makedirs()` (có thể tạo nested folders), và construct đường dẫn file cross-platform với `os.path.join()`. Việc dùng `os.path.join('charts', 'chart_1a.png')` thay vì ghép string `'charts/' + 'chart_1a.png'` đảm bảo code chạy được trên cả Windows (dùng backslash) và Linux/MacOS (dùng forward slash).

---

## 2. Đọc Dữ Liệu và Chuẩn Bị Output Folder

```python
def plot_charts(csv_file_path):
    # 1. Đọc file CSV
    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file '{csv_file_path}'.")
        print("Hãy đảm bảo bạn đã chạy benchmark.py để tạo ra file này.")
        return
    except Exception as e:
        print(f"Lỗi khi đọc file CSV: {e}")
        return
```

Hàm chính `plot_charts()` bắt đầu với việc đọc dữ liệu từ file CSV. Câu lệnh `df = pd.read_csv(csv_file_path)` tuy trông đơn giản nhưng thực ra đằng sau nó là một quá trình xử lý phức tạp. Pandas mở file, đọc từng dòng, phân tích cấu trúc, xác định data types, và xây dựng một DataFrame object hoàn chỉnh. DataFrame này có structure giống như bảng Excel với rows và columns - ví dụ từ `results_summary.csv` sẽ có ba columns: `tracker`, `avg_iou`, và `avg_fps`. Mỗi row đại diện cho một tracker với metrics tương ứng. Toàn bộ operation được wrap trong khối `try-except` để handle errors một cách graceful. Nếu file không tồn tại (`FileNotFoundError` - thường xảy ra khi chưa chạy benchmark.py), chương trình sẽ in ra message hướng dẫn rõ ràng thay vì crash với stack trace khó hiểu. Clause `except Exception as e:` bắt các lỗi khác như file bị corrupt hoặc permission denied, hiển thị error message, và return sớm để tránh code tiếp tục với dữ liệu không hợp lệ.

```python
    # Tạo thư mục 'charts' nếu chưa có
    output_dir = "charts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Đang lưu tất cả biểu đồ vào thư mục '{output_dir}/'")
```

Sau khi đọc data thành công, chương trình chuẩn bị folder output để lưu biểu đồ. Thay vì scatter các PNG files khắp working directory, tất cả charts được tổ chức gọn trong folder `charts/`. Conditional check `if not os.path.exists(output_dir):` kiểm tra folder đã tồn tại chưa - nếu chưa thì `os.makedirs(output_dir)` tạo mới. Code này là **idempotent** - chạy nhiều lần không gây lỗi vì nếu folder đã có, code skip việc tạo. Function `os.makedirs()` có thể tạo nested folders (ví dụ `charts/detailed/2024/` tạo cả ba levels), mạnh hơn `os.mkdir()` chỉ tạo được một level. Message cuối inform user nơi lưu outputs để dễ tìm sau khi chương trình chạy xong.

---

## 3. Biểu Đồ 1a: Xếp Hạng IoU (Accuracy Leaderboard)

```python
    # --- Biểu đồ 1a: Xếp hạng avg_iou (Horizontal Bar) ---
    df_iou = df.sort_values(by='avg_iou', ascending=True) # Sắp xếp tăng dần
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(df_iou['tracker'], df_iou['avg_iou'], color='#1f77b4')
    plt.title('avg_iou by tracker', fontsize=16)
    plt.xlabel('avg_iou', fontsize=12)
    plt.ylabel('tracker', fontsize=12)
    plt.xlim(0, 1.0) # IoU luôn từ 0 đến 1
```

Biểu đồ đầu tiên là leaderboard xếp hạng trackers theo độ chính xác (average IoU). Dòng `df_iou = df.sort_values(by='avg_iou', ascending=True)` sắp xếp DataFrame theo column 'avg_iou' với `ascending=True` nghĩa là tăng dần từ thấp đến cao. Lý do sắp xếp tăng dần là vì trong horizontal bar chart, bar dưới cùng được vẽ trước, nên với ascending=True thì tracker tốt nhất (IoU cao nhất) sẽ xuất hiện ở **trên cùng** của biểu đồ - vị trí tự nhiên nhất. Sort này tạo DataFrame mới không modify gốc.

`plt.figure(figsize=(10, 6))` tạo một canvas/figure mới với kích thước 10 inches chiều rộng, 6 inches chiều cao. Việc tạo figure mới ensure mỗi biểu đồ độc lập, không overlap. `bars = plt.barh(df_iou['tracker'], df_iou['avg_iou'], color='#1f77b4')` vẽ horizontal bars với y-axis là tên trackers (từ column 'tracker'), x-axis là độ dài bars (từ column 'avg_iou'), và màu xanh dương `#1f77b4` từ color palette mặc định của matplotlib. Function return `BarContainer` object chứa tất cả bars, lưu vào biến `bars` để thêm labels sau.

`plt.title()`, `plt.xlabel()`, `plt.ylabel()` thêm title và axis labels với font sizes khác nhau (16 cho title nổi bật, 12 cho labels). Quan trọng nhất là `plt.xlim(0, 1.0)` fix range trục X từ 0 đến 1 vì IoU theo định nghĩa bounded trong [0, 1]. Việc fix range giúp comparison nhất quán giữa các runs - nếu không fix, matplotlib auto-scale có thể zoom vào [0.4, 0.7] làm differences trông lớn hơn thực tế (misleading).

```python
    # Thêm số liệu vào cuối thanh
    for bar in bars:
        plt.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2 - 0.1,
                 f"{bar.get_width():.3f}", va='center')
```

Phần này thêm **data labels** - con số chính xác ở cuối mỗi bar. Loop qua từng bar trong container: `bar.get_width()` trả về độ dài bar (giá trị IoU), `bar.get_y()` trả về vị trí Y bottom của bar, `bar.get_height()` trả về chiều cao bar. Position X của text là `bar.get_width() + 0.01` (ngay sau bar, offset 0.01 để không dính), position Y là `bar.get_y() + bar.get_height()/2 - 0.1` (giữa bar theo chiều cao, offset -0.1 để center tốt hơn). Text là f-string `f"{bar.get_width():.3f}"` format 3 decimal places (ví dụ: 0.652). Parameter `va='center'` là vertical alignment center. Data labels cho phép đọc exact values thay vì estimate từ bar length.

```python
    plt.tight_layout() # Tự động căn chỉnh
    plt.savefig(os.path.join(output_dir, 'chart_1a_iou_leaderboard.png'))
    print("Đã lưu 'chart_1a_iou_leaderboard.png'")
```

`plt.tight_layout()` tự động adjust spacing để tất cả elements (title, labels, bars) fit trong figure mà không bị crop hay overlap. Always call trước `savefig()`. `plt.savefig()` lưu figure ra file PNG, với path constructed bằng `os.path.join()` để cross-platform compatible. Print message confirm file đã được tạo.

---

## 4. Biểu Đồ 1b: Xếp Hạng FPS (Speed Leaderboard)

```python
    # --- Biểu đồ 1b: Xếp hạng avg_fps (Horizontal Bar) ---
    df_fps = df.sort_values(by='avg_fps', ascending=True) # Sắp xếp tăng dần
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(df_fps['tracker'], df_fps['avg_fps'], color='#ff7f0e')
    plt.title('avg_fps by tracker', fontsize=16)
    plt.xlabel('avg_fps', fontsize=12)
    plt.ylabel('tracker', fontsize=12)
```

Biểu đồ thứ hai tương tự biểu đồ đầu nhưng focus vào tốc độ (FPS) thay vì accuracy (IoU). `df_fps = df.sort_values(by='avg_fps', ascending=True)` sort theo column 'avg_fps'. Figure mới được tạo cùng kích thước, nhưng lần này dùng màu **cam** `#ff7f0e` thay vì xanh dương để phân biệt rõ ràng đây là metric khác. Việc dùng màu khác cho metrics khác nhau là data visualization best practice - người xem ngay lập tức nhận ra đây là two different measurements. Màu cam cũng từ matplotlib default color cycle, đảm bảo harmony.

```python
    # Thêm số liệu vào cuối thanh
    for bar in bars:
        plt.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2 - 0.1,
                 f"{int(bar.get_width())}", va='center')
```

Phần thêm data labels có hai differences so với chart 1a. Thứ nhất, offset X là `+ 5` thay vì `+ 0.01` vì FPS values có thể lên hàng trăm (ví dụ: 283 FPS) - nếu dùng 0.01 offset, text sẽ dính sát bar. Thứ hai, format là `f"{int(bar.get_width())}"` convert sang integer thay vì 3 decimals vì trong practice người ta nói "45 FPS" chứ không "45.274 FPS". Chi tiết này làm chart professional hơn.

```python
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chart_1b_fps_leaderboard.png'))
    print("Đã lưu 'chart_1b_fps_leaderboard.png'")
```

Chart không có `plt.xlim()` để fix X range vì FPS vary rất nhiều (từ ~12 CSRT đến ~300 MOSSE). Để matplotlib auto-scale đảm bảo tất cả bars visible. Tight layout và save tương tự chart 1a.

---

## 5. Biểu Đồ 2: Consolidated Chart (Hợp Nhất IoU + FPS)

```python
    # --- Biểu đồ 2: Hợp nhất (avg_iou Bar + avg_fps Text) ---
    # Sử dụng lại df_iou đã sắp xếp
    plt.figure(figsize=(12, 7))
    bars = plt.barh(df_iou['tracker'], df_iou['avg_iou'], color='#2ca02c')
    plt.title('Consolidated Chart: avg_iou (Bar) vs. avg_fps (Text)', fontsize=16)
    plt.xlabel('avg_iou', fontsize=12)
    plt.ylabel('tracker', fontsize=12)
    plt.xlim(0, 1.0)
```

Biểu đồ thứ ba là consolidated chart kết hợp cả IoU và FPS trong một visualization. Chart reuse `df_iou` (đã sorted theo IoU), nhưng figure **lớn hơn** `(12, 7)` để accommodate thêm information. Bars dùng màu **xanh lá** `#2ca02c` - màu thứ ba để phân biệt đây là chart mới. Bars represent IoU values (như chart 1a), xlim fixed [0, 1.0].

```python
    # Thêm 2 loại text: giá trị IoU (cuối thanh) và giá trị FPS (đầu thanh)
    for i, bar in enumerate(bars):
        iou_val = bar.get_width()
        # Lấy fps tương ứng
        fps_val = df_iou['avg_fps'].iloc[i] 
        
        # Ghi IoU ở cuối thanh
        plt.text(iou_val + 0.01, bar.get_y() + bar.get_height()/2,
                 f"{iou_val:.3f}", va='center', ha='left', fontsize=10, weight='bold')
                 
        # Ghi FPS ở gần đầu thanh (bên trong)
        plt.text(0.01, bar.get_y() + bar.get_height()/2,
                 f"FPS: {int(fps_val)}", va='center', ha='left', fontsize=10, color='white')
```

Đây là phần đặc biệt của chart này - thêm **hai loại labels** khác nhau. `enumerate(bars)` loop với cả index `i` và bar object. `iou_val = bar.get_width()` lấy IoU value. `fps_val = df_iou['avg_fps'].iloc[i]` lấy FPS tương ứng - trick thông minh vì df_iou đã sorted nên row thứ i tương ứng exact với bar thứ i.

**Label thứ nhất** (IoU) được vẽ **bên ngoài bar**: position X là `iou_val + 0.01` (sau bar), format `:.3f`, màu đen (default), font đậm (`weight='bold'`), `ha='left'` (horizontal alignment left - text bắt đầu từ position). 

**Label thứ hai** (FPS) được vẽ **bên trong bar**: position X là `0.01` (gần đầu bar), prefix "FPS: " để rõ ràng, màu **trắng** (`color='white'`) để contrast với bar xanh lá. Điều này tạo visual hierarchy: bar length = IoU (primary), white text inside = FPS (secondary), black text outside = exact IoU value. Người xem scan nhanh thấy ngay trade-off giữa accuracy và speed.

```python
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chart_2_consolidated.png'))
    print("Đã lưu 'chart_2_consolidated.png'")
```

Save chart với tên `chart_2_consolidated.png` - một compact summary perfect cho presentations.

---

## 6. Biểu Đồ 3: Trade-off Scatter Plot (Phân Tích Đánh Đổi)

```python
    # --- Biểu đồ 3: Phân tán "Đánh đổi" (Trade-off Scatter) ---
    plt.figure(figsize=(10, 7))
    
    # Lấy colormap theo API mới
    cmap = plt.colormaps['tab10'] # <--- DÒNG MỚI
```

Biểu đồ cuối cùng là trade-off scatter plot, visualize relationship giữa FPS và IoU trong coordinate system 2D. Figure được tạo với kích thước `(10, 7)`. `cmap = plt.colormaps['tab10']` lấy colormap 'tab10' bằng **API mới** của matplotlib (version 3.5+) thay vì API cũ `plt.cm.get_cmap()` đã deprecated. 'tab10' là Tableau 10 color palette - một bộ 10 màu được thiết kế cho categorical data, đảm bảo dễ phân biệt và color-blind friendly. Colormap là callable object - `cmap(i)` return RGBA tuple của màu thứ i.

```python
    # i là chỉ số (0, 1, 2, 3...)
    for i, row in df.iterrows():
        # Lấy màu thứ i từ colormap
        color = cmap(i) 
        
        plt.scatter(row['avg_fps'], row['avg_iou'], s=150, alpha=0.7, label=row['tracker'], color=color)
        # Thêm tên tracker vào điểm
        plt.text(row['avg_fps'] + 3, row['avg_iou'], row['tracker'], fontsize=11)
```

`df.iterrows()` loop qua từng row, trả về tuple `(index, row)`. Row là pandas Series, access columns bằng `row['avg_fps']` và `row['avg_iou']`. `color = cmap(i)` lấy màu unique cho tracker thứ i.

`plt.scatter(row['avg_fps'], row['avg_iou'], ...)` vẽ point tại coordinate (FPS, IoU). Parameters: `s=150` set marker size khá lớn để dễ thấy, `alpha=0.7` làm marker hơi transparent (nếu overlap vẫn thấy được), `label=row['tracker']` cho legend (nhưng bị comment out sau), `color=color` từ colormap.

`plt.text(row['avg_fps'] + 3, row['avg_iou'], row['tracker'], ...)` vẽ text label ngay bên phải point (offset +3 trên trục X, cùng Y level). Điều này tạo instant identification - không cần look up legend, nhìn thấy tên ngay.

```python
    plt.title('Trade-off Plot: avg_iou vs. avg_fps', fontsize=16)
    plt.xlabel('avg_fps', fontsize=12)
    plt.ylabel('avg_iou', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6) # Thêm lưới mờ
    plt.xlim(left=0) # FPS bắt đầu từ 0
    plt.ylim(0, 1.0) # IoU từ 0 đến 1
    # plt.legend() 
```

`plt.grid(True, linestyle='--', alpha=0.6)` thêm grid với dashed lines (`--`) và transparency 0.6 (mờ để không che points). Grid giúp estimate coordinates dễ hơn. `plt.xlim(left=0)` set X-axis bắt đầu từ 0 (FPS không thể âm), right boundary auto-scale. `plt.ylim(0, 1.0)` fix Y-axis [0, 1] vì IoU bounded. Bắt đầu từ origin (0,0) quan trọng để avoid misleading - cho thấy rõ "worst case" và "best case". `plt.legend()` bị comment vì text labels đã đủ.

```python
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chart_3_tradeoff_scatter.png'))
    print("Đã lưu 'chart_3_tradeoff_scatter.png'")
```

Save scatter plot - một powerful analytical tool. Data scientist nhìn vào thấy ngay trade-off curve, có thể draw mentally "requirement box" (min IoU, min FPS) và chọn trackers trong box.

---

## 7. Completion và Entry Point

```python
    print("\nHoàn thành! Tất cả biểu đồ đã được lưu trong thư mục 'charts'.")
    
    # Hiển thị các biểu đồ (tùy chọn)
    # plt.show()
```

Sau khi tất cả charts được tạo và lưu, final message confirm với user. `plt.show()` bị comment vì trong batch mode chỉ cần generate files, không cần interactive window. Nếu uncomment, sẽ mở window với tất cả figures, user phải close mới tiếp tục - không suitable cho automation hoặc server mode.

```python
# --- CHẠY CHƯƠG TRÌNH ---
if __name__ == "__main__":
    plot_charts('results_summary.csv')
```

Entry point là Python idiom chuẩn `if __name__ == "__main__":` - code chỉ chạy khi file executed directly, không khi imported as module. Gọi `plot_charts('results_summary.csv')` với filename hardcoded, assume user đã chạy benchmark.py trước. Có thể improve bằng argparse để accept command-line arguments.

---

## Tổng Kết và Workflow Integration

File `plot_results.py` là final piece trong benchmark pipeline, transform raw CSV numbers thành visual insights. Complete workflow: run `benchmark.py` (nhiều giờ) → `results_summary.csv` → run `plot_results.py` (vài giây) → 4 PNG charts trong `charts/`. Bộ charts provide multiple perspectives: Chart 1a (accuracy ranking), Chart 1b (speed ranking), Chart 2 (quick overview cả hai), Chart 3 (trade-off analysis). Researchers dùng cho papers, developers dùng để choose tracker cho production, managers dùng cho presentations. Chương trình demonstrate data visualization best practices: appropriate chart types, consistent colors, clear labels, data labels cho exact values, organized output. Excellent example của việc transform data thành knowledge.
