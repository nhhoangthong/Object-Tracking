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

click_points = {"p1": None, "p2": None}


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


def reset_click_points():
    global click_points
    click_points = {"p1": None, "p2": None}


def reset_box(image):
    reset_click_points()
    return image, "Click điểm 1"


def get_bbox_from_clicks():
    global click_points
    if click_points["p1"] is None or click_points["p2"] is None:
        return None
    return points_to_bbox(click_points["p1"], click_points["p2"])


def on_video_upload(video_path):
    reset_click_points()
    if video_path is None:
        return gr.update(value=0, maximum=1), None, "Click điểm 1"
    
    info = get_video_info(video_path)
    first_frame = get_frame_at_index(video_path, 0)
    return (
        gr.update(maximum=info['total_frames'] - 1, value=0, 
                  label=f"Chọn Frame (Tổng: {info['total_frames']})"),
        first_frame,
        "Click điểm 1"
    )


def on_frame_change(video_path, frame_index):
    reset_click_points()
    frame = get_frame_at_index(video_path, frame_index)
    return frame, "Click điểm 1"


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


with gr.Blocks(title="Demo Object Tracking") as demo:
    with gr.Row():
        with gr.Column(scale=4):
            inp_video = gr.File(label="Upload Video", file_types=["video"])
            slider_frame = gr.Slider(minimum=0, maximum=1, step=1, value=0, 
                                     label="Chọn Frame bắt đầu")
            frame_image = gr.Image(label="Click 2 điểm để vẽ box", 
                                   type="numpy", interactive=False, height=400)
            box_status = gr.Textbox(label="Tọa độ", interactive=False)
            btn_reset = gr.Button("Reset", variant="secondary")
            
            with gr.Row():
                inp_tracker = gr.Dropdown(Trackers, value="CSRT", show_label=False)
                btn_run = gr.Button("RUN", variant="primary")

        with gr.Column(scale=6):
            out_video = gr.Video(label="Video Output")
            out_file = gr.File(label="Tải về")

    inp_video.change(fn=on_video_upload, inputs=inp_video, 
                     outputs=[slider_frame, frame_image, box_status])
    slider_frame.release(fn=on_frame_change, inputs=[inp_video, slider_frame], 
                         outputs=[frame_image, box_status])
    
    original_frame = gr.State(None)
    inp_video.change(fn=lambda v: get_frame_at_index(v, 0), 
                     inputs=inp_video, outputs=original_frame)
    slider_frame.release(fn=lambda v, i: get_frame_at_index(v, i), 
                         inputs=[inp_video, slider_frame], outputs=original_frame)
    
    frame_image.select(fn=handle_click, inputs=[original_frame], 
                       outputs=[frame_image, box_status])
    btn_reset.click(fn=reset_box, inputs=[original_frame], 
                    outputs=[frame_image, box_status])
    btn_run.click(fn=on_run_tracking, inputs=[inp_video, inp_tracker, slider_frame], 
                  outputs=[out_video, out_file])


if __name__ == "__main__":
    demo.launch()
