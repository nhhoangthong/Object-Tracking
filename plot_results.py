import pandas as pd
import matplotlib.pyplot as plt
import os

# --- HÀM VẼ BIỂU ĐỒ ---

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

    # Tạo thư mục 'charts' nếu chưa có
    output_dir = "charts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Đang lưu tất cả biểu đồ vào thư mục '{output_dir}/'")

    # --- Biểu đồ 1a: Xếp hạng avg_iou (Horizontal Bar) ---
    df_iou = df.sort_values(by='avg_iou', ascending=True) # Sắp xếp tăng dần
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(df_iou['tracker'], df_iou['avg_iou'], color='#1f77b4')
    plt.title('avg_iou by tracker', fontsize=16)
    plt.xlabel('avg_iou', fontsize=12)
    plt.ylabel('tracker', fontsize=12)
    plt.xlim(0, 1.0) # IoU luôn từ 0 đến 1

    # Thêm số liệu vào cuối thanh
    for bar in bars:
        plt.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2 - 0.1,
                 f"{bar.get_width():.3f}", va='center')
        
    plt.tight_layout() # Tự động căn chỉnh
    plt.savefig(os.path.join(output_dir, 'chart_1a_iou_leaderboard.png'))
    print("Đã lưu 'chart_1a_iou_leaderboard.png'")

    # --- Biểu đồ 1b: Xếp hạng avg_fps (Horizontal Bar) ---
    df_fps = df.sort_values(by='avg_fps', ascending=True) # Sắp xếp tăng dần
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(df_fps['tracker'], df_fps['avg_fps'], color='#ff7f0e')
    plt.title('avg_fps by tracker', fontsize=16)
    plt.xlabel('avg_fps', fontsize=12)
    plt.ylabel('tracker', fontsize=12)

    # Thêm số liệu vào cuối thanh
    for bar in bars:
        plt.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2 - 0.1,
                 f"{int(bar.get_width())}", va='center')
                 
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chart_1b_fps_leaderboard.png'))
    print("Đã lưu 'chart_1b_fps_leaderboard.png'")

    # --- Biểu đồ 2: Hợp nhất (avg_iou Bar + avg_fps Text) ---
    # Sử dụng lại df_iou đã sắp xếp
    plt.figure(figsize=(12, 7))
    bars = plt.barh(df_iou['tracker'], df_iou['avg_iou'], color='#2ca02c')
    plt.title('Consolidated Chart: avg_iou (Bar) vs. avg_fps (Text)', fontsize=16)
    plt.xlabel('avg_iou', fontsize=12)
    plt.ylabel('tracker', fontsize=12)
    plt.xlim(0, 1.0)

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

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chart_2_consolidated.png'))
    print("Đã lưu 'chart_2_consolidated.png'")

    # --- Biểu đồ 3: Phân tán "Đánh đổi" (Trade-off Scatter) ---
    plt.figure(figsize=(10, 7))
    
    # Lấy colormap theo API mới
    cmap = plt.colormaps['tab10'] # <--- DÒNG MỚI

    # i là chỉ số (0, 1, 2, 3...)
    for i, row in df.iterrows():
        # Lấy màu thứ i từ colormap
        color = cmap(i) 
        
        plt.scatter(row['avg_fps'], row['avg_iou'], s=150, alpha=0.7, label=row['tracker'], color=color) # <--- DÙNG Ở ĐÂY
        # Thêm tên tracker vào điểm
        plt.text(row['avg_fps'] + 3, row['avg_iou'], row['tracker'], fontsize=11)
    
    plt.title('Trade-off Plot: avg_iou vs. avg_fps', fontsize=16)
    plt.xlabel('avg_fps', fontsize=12)
    plt.ylabel('avg_iou', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6) # Thêm lưới mờ
    plt.xlim(left=0) # FPS bắt đầu từ 0
    plt.ylim(0, 1.0) # IoU từ 0 đến 1
    # plt.legend() 

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chart_3_tradeoff_scatter.png'))
    print("Đã lưu 'chart_3_tradeoff_scatter.png'")
    
    print("\nHoàn thành! Tất cả biểu đồ đã được lưu trong thư mục 'charts'.")
    
    # Hiển thị các biểu đồ (tùy chọn)
    # plt.show()

# --- CHẠY CHƯƠG TRÌNH ---
if __name__ == "__main__":
    plot_charts('results_summary.csv')