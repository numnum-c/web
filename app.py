import streamlit as st
import cv2
from ultralytics import YOLO
import tempfile
from PIL import Image
import numpy as np


# Load YOLO model
model = YOLO("models/my_model.pt")

# YOLO class names
yolo_classes = [
    "battery",
    "biological",
    "cardboard",
    "clothes",
    "glass",
    "metal",
    "paper",
    "plastic",
    "shoes",
    "trash",
]

st.set_page_config(
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Object Detection",
)

# Initialize session state variables
if "is_detecting" not in st.session_state:
    st.session_state.is_detecting = False
if "is_webcam_active" not in st.session_state:
    st.session_state.is_webcam_active = False


# Function for live object detection using webcam
def live_streaming(conf_threshold, selected_classes):
    stframe = st.empty()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error(
            "Error: Could not access the webcam. Please make sure your webcam is working."
        )
        return

    try:
        while st.session_state.get("is_detecting", False) and st.session_state.get(
            "is_webcam_active", False
        ):
            ret, frame = cap.read()

            if not ret:
                st.warning("Warning: Failed to read frame from the webcam. Retrying...")
                continue

            try:
                results = model.predict(source=frame, conf=conf_threshold)
                detections = results[0]

                # Extract bounding boxes, confidence scores, and class IDs
                boxes = (
                    detections.boxes.xyxy.cpu().numpy() if len(detections) > 0 else []
                )
                confs = (
                    detections.boxes.conf.cpu().numpy() if len(detections) > 0 else []
                )
                class_ids = (
                    detections.boxes.cls.cpu().numpy().astype(int)
                    if len(detections) > 0
                    else []
                )

                # Filter based on selected classes
                if selected_classes:
                    filtered = [
                        (box, conf, class_id)
                        for box, conf, class_id in zip(boxes, confs, class_ids)
                        if yolo_classes[class_id] in selected_classes
                    ]
                    if filtered:
                        boxes, confs, class_ids = zip(*filtered)
                    else:
                        boxes, confs, class_ids = [], [], []

                # Draw bounding boxes and labels on the frame
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = map(int, box)
                    label = f"{yolo_classes[class_ids[i]]}: {confs[i]:.2f}"
                    cv2.rectangle(
                        frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2
                    )
                    cv2.putText(
                        frame,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                    )

                # Display the frame in Streamlit
                stframe.image(frame, channels="BGR")

            except Exception as e:
                st.error(f"Error during model prediction: {str(e)}")

    finally:
        # Ensure resources are properly released
        cap.release()
        cv2.destroyAllWindows()


def video_streaming(uploaded_file, conf_threshold, selected_classes):
    stframe = st.empty()
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        video_path = tmp_file.name

    cap = cv2.VideoCapture(video_path)

    while cap.isOpened() and st.session_state.is_detecting:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.predict(source=frame, conf=conf_threshold)
        detections = results[0]

        boxes = detections.boxes.xyxy.cpu().numpy()
        confs = detections.boxes.conf.cpu().numpy()
        class_ids = detections.boxes.cls.cpu().numpy().astype(int)

        if selected_classes:
            filtered = [
                (box, conf, class_id)
                for box, conf, class_id in zip(boxes, confs, class_ids)
                if yolo_classes[class_id] in selected_classes
            ]
            if filtered:
                boxes, confs, class_ids = zip(*filtered)
            else:
                boxes, confs, class_ids = [], [], []

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box)
            label = f"{yolo_classes[class_ids[i]]}: {confs[i]:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)
            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )

        stframe.image(frame, channels="BGR")

    cap.release()
    cv2.destroyAllWindows()


# Function for object detection on uploaded image
def image_detection(uploaded_file, conf_threshold, selected_classes):
    image = Image.open(uploaded_file)
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    results = model.predict(source=image_cv, conf=conf_threshold)
    detections = results[0]

    boxes = detections.boxes.xyxy.cpu().numpy()
    confs = detections.boxes.conf.cpu().numpy()
    class_ids = detections.boxes.cls.cpu().numpy().astype(int)

    if selected_classes:
        filtered = [
            (box, conf, class_id)
            for box, conf, class_id in zip(boxes, confs, class_ids)
            if yolo_classes[class_id] in selected_classes
        ]
        if filtered:
            boxes, confs, class_ids = zip(*filtered)
        else:
            boxes, confs, class_ids = [], [], []

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)
        label = f"{yolo_classes[class_ids[i]]}: {confs[i]:.2f}"
        cv2.rectangle(image_cv, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)
        cv2.putText(
            image_cv,
            label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
        )

    st.image(image_cv, channels="BGR")


# Sidebar controls for user input
with st.sidebar:
    st.title("Object Detection Settings " + "⚙️")
    confidence_threshold = st.slider("Confidence Threshold",0.0,1.0,0.2)
    selected_classes = st.multiselect(
        "Select classes for object detection", yolo_classes
    )

    # Unified file uploader for both images and videos
    uploaded_file = st.file_uploader(
        "Upload an image or video " + "📤",
        type=["mp4", "mov", "avi", "m4v", "jpg", "png", "jpeg"],
    )

    if st.button(
        "Use Webcam 📷" if not st.session_state.is_webcam_active else "Stop Webcam 🛑"
    ):
        st.session_state.is_webcam_active = not st.session_state.is_webcam_active
        if st.session_state.is_webcam_active:
            st.session_state.is_detecting = True
        else:
            st.session_state.is_detecting = False

    detect_button = st.button(
        (
            "Start Detection ▶️"
            if not st.session_state.is_detecting
            else "Stop Detection 🛑"
        ),
        disabled=(not uploaded_file and not st.session_state.is_webcam_active),
    )

    if detect_button:
        st.session_state.is_detecting = not st.session_state.is_detecting

# Handle object detection based on user input
if st.session_state.is_detecting:
    if st.session_state.is_webcam_active:
        st.info("Detecting objects using webcam...")
        live_streaming(confidence_threshold, selected_classes)
    elif uploaded_file:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        if file_extension in ["mp4", "mov", "avi", "m4v"]:
            st.info("Detecting objects in video...")
            video_streaming(uploaded_file, confidence_threshold, selected_classes)
        elif file_extension in ["jpg", "jpeg", "png"]:
            st.info("Detecting objects in image...")
            image_detection(uploaded_file, confidence_threshold, selected_classes)
else:
    st.title("Object Detection")
    st.info("Upload an image or video, or start the webcam for object detection.")

    st.write(
        """
        ### What is YOLO?
        YOLO (You Only Look Once) is a state-of-the-art, real-time object detection system that excels in speed and accuracy. It processes images in a single pass, making it highly efficient for applications requiring rapid object detection.

        ### How YOLO Works
        YOLO divides the input image into a grid and predicts bounding boxes and class probabilities for each grid cell. This allows it to identify multiple objects simultaneously, making it suitable for real-time scenarios.

        ### Training YOLO
        To train a YOLO model on your own dataset, follow these key steps:

        1. **Dataset Preparation**:
            - Collect and annotate your images with bounding box coordinates and class labels. You can use annotation tools like LabelImg or Roboflow.

        2. **Environment Setup**:
            - Install the necessary libraries and dependencies as specified in the Ultralytics repository. This typically involves using Python and libraries like PyTorch.

        3. **Model Configuration**:
            - Choose a model architecture (e.g., YOLOv5) and configure it based on your dataset’s requirements. This includes setting the number of classes and adjusting the input image size.

        4. **Training**:
            - Use the command line interface to start the training process. The typical command looks like this:
              ```bash
              python train.py --img 640 --batch 16 --epochs 50 --data your_dataset.yaml --weights yolov10s.pt
              ```
            - Here, you specify parameters like image size, batch size, number of epochs, dataset configuration, and pre-trained weights.

        5. **Evaluation**:
            - After training, evaluate the model's performance using validation data. This step helps in understanding the accuracy and making necessary adjustments.

        For detailed instructions, examples, and best practices, please refer to the [Ultralytics YOLO Training Documentation](https://docs.ultralytics.com/models/yolov10/train/).

        Now, go ahead and upload your image or video, or start the webcam to see YOLO in action!
    """
    )