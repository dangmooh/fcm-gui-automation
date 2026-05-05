# YOLO 기반 UI 요소 탐지 실험

현재 버전: `v1.3.0`

이 폴더는 Python + Ultralytics YOLO로 스크린샷에서 UI 요소를 탐지하기 위한 실험 공간입니다.

목표 탐지 클래스 예시:

- `button`
- `text`
- `input_field`
- `checkbox`
- `dropdown`
- `icon`
- `popup`

## 1. 폴더 구조

```text
yolo/
  detect_ui.py
  detect_ui_elements.py
  train_ui_yolo.py
  requirements.txt
  README.md
  dataset/
    data.yaml
    images/
      train/
      val/
      test/
    labels/
      train/
      val/
      test/
  models/
    ui_model.pt
  screenshots/
    test.png
  outputs/
  runs/
  report/
    yolo_ui_detection_report.md
```

`models`, `screenshots`, `outputs`, `runs` 폴더는 필요할 때 직접 만들면 됩니다.

```powershell
New-Item -ItemType Directory -Force yolo\models, yolo\screenshots, yolo\outputs, yolo\runs
```

## 2. 설치

```powershell
pip install -r yolo\requirements.txt
```

`requirements.txt`:

```text
ultralytics
opencv-python
```

## 3. 공개 UI Detection 모델 준비

### 3.1 MacPaw Screen2AX UI Elements 모델

후보:

- Hugging Face: `macpaw-research/yolov11l-ui-elements-detection`
- 파일명: `ui-elements-detection.pt`
- 특징: macOS 앱 스크린샷에서 UI accessibility element 후보를 탐지하도록 fine-tuning 된 YOLO11 계열 모델
- 대표 클래스: `AXButton`, `AXDisclosureTriangle`, `AXImage`, `AXLink`, `AXTextArea`
- 라이선스: AGPL-3.0

외부망 PC에서 다운로드 예시:

```powershell
pip install huggingface_hub
huggingface-cli download macpaw-research/yolov11l-ui-elements-detection ui-elements-detection.pt --local-dir yolo\models
```

다운로드 후 내부망에서는 다음 파일을 사용합니다.

```text
yolo\models\ui-elements-detection.pt
```

### 3.2 Salesforce GPA-GUI-Detector

후보:

- Hugging Face: `Salesforce/GPA-GUI-Detector`
- 파일명: `model.pt`
- 특징: GUI Process Automation을 위한 YOLO 기반 GUI element detector
- 라이선스: MIT

외부망 PC에서 다운로드 예시:

```powershell
pip install huggingface_hub
huggingface-cli download Salesforce/GPA-GUI-Detector model.pt --local-dir yolo\models\gpa-gui-detector
```

내부망으로 반입 후 사용 경로 예시:

```text
yolo\models\gpa-gui-detector\model.pt
```

### 3.3 Roboflow 모델 또는 데이터셋

Roboflow에는 UI element detection 관련 공개 프로젝트나 데이터셋이 있을 수 있습니다. 단, 프로젝트마다 클래스 정의, 라이선스, export 형식이 다르므로 다음을 확인해야 합니다.

- 클래스가 `button`, `text`, `input_field` 등 목표와 맞는지
- YOLOv8/YOLOv11 형식으로 export 가능한지
- 상업적 또는 내부 사용 라이선스가 허용되는지
- 학습 데이터가 웹/모바일/데스크톱 중 어떤 화면 분포인지

Roboflow에서 YOLO 형식으로 export하면 일반적으로 다음 구조로 받을 수 있습니다.

```text
dataset/
  train/
    images/
    labels/
  valid/
    images/
    labels/
  test/
    images/
    labels/
  data.yaml
```

필요하면 이 프로젝트의 구조에 맞게 `images/train`, `images/val`, `labels/train`, `labels/val`로 옮겨 사용하면 됩니다.

## 4. 일반 COCO Pretrained YOLO가 UI 탐지에 약한 이유

일반 YOLO pretrained 모델은 보통 COCO 같은 자연 이미지 데이터셋으로 학습되어 있습니다. 이 모델은 사람, 자동차, 의자, 컵 같은 자연 이미지 객체에는 강하지만 GUI 요소에는 약합니다.

주요 이유:

- COCO 클래스에 `button`, `text`, `input_field`, `checkbox`, `dropdown` 같은 GUI 클래스가 없습니다.
- COCO는 카메라 사진 중심이고, GUI 스크린샷은 평면적이고 선명한 렌더링 이미지입니다.
- UI 요소는 작고 밀집되어 있으며, 픽셀 단위 경계가 중요합니다.
- 버튼과 입력 필드는 테마, 운영체제, 해상도, 다크 모드에 따라 형태가 크게 달라집니다.
- 텍스트 영역은 OCR 문제와 겹치므로 단순 object detection만으로 의미를 완전히 파악하기 어렵습니다.

따라서 COCO 모델은 UI 실험의 baseline으로는 사용할 수 있지만, 실제 `button`, `text`, `input_field` 탐지에는 UI 전용 모델이나 fine-tuned 모델이 필요합니다.

## 5. 추론 실행

### 5.1 기본 실행

로컬 `.pt` 모델과 스크린샷이 준비되었다면 다음처럼 실행합니다.

```powershell
python yolo\detect_ui.py --model yolo\models\ui_model.pt --image yolo\screenshots\test.png --conf 0.25 --imgsz 1280 --out yolo\outputs
```

Salesforce GPA 모델 예시:

```powershell
python yolo\detect_ui.py --model yolo\models\gpa-gui-detector\model.pt --image yolo\screenshots\test.png --conf 0.05 --iou 0.1 --imgsz 1280 --out yolo\outputs
```

MacPaw 모델 예시:

```powershell
python yolo\detect_ui.py --model yolo\models\ui-elements-detection.pt --image yolo\screenshots\test.png --conf 0.25 --iou 0.7 --imgsz 1280 --out yolo\outputs
```

### 5.2 출력

`yolo\outputs` 아래에 다음 파일이 생성됩니다.

```text
test_YYYYMMDD_HHMMSS_annotated.png
test_YYYYMMDD_HHMMSS_detections.json
```

JSON에는 다음 정보가 포함됩니다.

- 모델 경로
- 입력 이미지 경로
- 이미지 크기
- 추론 파라미터
- detection 개수
- 각 detection의 class id
- class name
- confidence
- bounding box 좌표
- 중심 좌표
- normalized bounding box 좌표

### 5.3 crop 저장

탐지된 영역 crop도 함께 저장하려면 `--save-crops`를 추가합니다.

```powershell
python yolo\detect_ui.py --model yolo\models\ui_model.pt --image yolo\screenshots\test.png --out yolo\outputs --save-crops
```

## 6. Fine-tuning 절차

UI 전용 모델이 없거나 성능이 낮으면 직접 데이터셋을 만들고 fine-tuning 해야 합니다.

### 6.1 데이터 수집

소콘 프로그램 또는 자동화 대상 프로그램 화면을 다양한 상태로 캡처합니다.

권장 캡처 조건:

- 기본 화면
- 팝업 열린 상태
- 드롭다운 열린 상태
- 체크박스 on/off 상태
- 입력 필드 focus 상태
- 에러 메시지 또는 알림 표시 상태
- 여러 해상도
- 라이트 모드와 다크 모드

### 6.2 라벨링 도구

사용 가능한 라벨링 도구:

- LabelImg
- CVAT
- Roboflow
- Label Studio

YOLO 형식으로 export해야 합니다.

### 6.3 클래스 정의

초기 클래스 예시:

```text
0 button
1 text
2 input_field
3 checkbox
4 dropdown
5 icon
6 popup
```

프로젝트가 커지면 `radio_button`, `tab`, `table`, `menu_item`, `slider` 등을 추가할 수 있습니다.

### 6.4 YOLO dataset 구조

```text
yolo/dataset/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
  data.yaml
```

라벨 파일은 이미지와 같은 stem 이름을 가져야 합니다.

```text
images/train/screen_001.png
labels/train/screen_001.txt
```

라벨 형식:

```text
class_id x_center y_center width height
```

좌표는 0부터 1 사이로 정규화된 YOLO 형식입니다.

### 6.5 data.yaml 예시

[dataset/data.yaml](dataset/data.yaml)을 참고하면 됩니다.

```yaml
path: ./yolo/dataset
train: images/train
val: images/val
test: images/test

names:
  0: button
  1: text
  2: input_field
  3: checkbox
  4: dropdown
  5: icon
  6: popup
```

### 6.6 학습 실행

외부망에서 base YOLO 모델을 다운로드한 뒤 내부망으로 반입했다면 다음처럼 학습합니다.

```powershell
python yolo\train_ui_yolo.py --data yolo\dataset\data.yaml --model yolo\models\yolo11n.pt --epochs 100 --imgsz 1280 --batch 8 --device 0 --project yolo\runs --name ui_yolo
```

CPU만 사용할 경우:

```powershell
python yolo\train_ui_yolo.py --data yolo\dataset\data.yaml --model yolo\models\yolo11n.pt --epochs 50 --imgsz 960 --batch 2 --device cpu --project yolo\runs --name ui_yolo_cpu
```

학습 완료 후 일반적으로 best checkpoint는 다음 위치에 저장됩니다.

```text
yolo\runs\ui_yolo\weights\best.pt
```

### 6.7 검증 실행

```powershell
python yolo\train_ui_yolo.py --val-only --data yolo\dataset\data.yaml --model yolo\runs\ui_yolo\weights\best.pt --imgsz 1280 --batch 8 --device 0
```

### 6.8 학습 모델로 추론

```powershell
python yolo\detect_ui.py --model yolo\runs\ui_yolo\weights\best.pt --image yolo\screenshots\test.png --conf 0.25 --imgsz 1280 --out yolo\outputs
```

## 7. 폐쇄망 환경 절차

### 7.1 외부망 PC에서 준비

외부망 PC에서 wheel 파일과 모델 파일을 다운로드합니다.

```powershell
New-Item -ItemType Directory -Force offline_packages, yolo\models
pip download -r yolo\requirements.txt -d offline_packages
huggingface-cli download Salesforce/GPA-GUI-Detector model.pt --local-dir yolo\models\gpa-gui-detector
huggingface-cli download macpaw-research/yolov11l-ui-elements-detection ui-elements-detection.pt --local-dir yolo\models
```

필요하면 base training model도 외부망에서 다운로드합니다.

```powershell
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```

Ultralytics cache에 저장된 `yolo11n.pt`를 찾아 `yolo\models\yolo11n.pt`로 복사합니다.

### 7.2 내부망 PC로 반입

다음 항목을 내부망 PC로 반입합니다.

```text
offline_packages/
yolo/models/*.pt
yolo/models/gpa-gui-detector/model.pt
```

### 7.3 내부망 PC에서 설치

```powershell
pip install --no-index --find-links offline_packages -r yolo\requirements.txt
```

### 7.4 내부망 PC에서 실행

인터넷 접근 없이 local `.pt`만 사용합니다.

```powershell
python yolo\detect_ui.py --model yolo\models\gpa-gui-detector\model.pt --image yolo\screenshots\test.png --conf 0.05 --iou 0.1 --imgsz 1280 --out yolo\outputs
```

## 8. 참고 링크

- MacPaw YOLO UI Elements Detection: https://huggingface.co/macpaw-research/yolov11l-ui-elements-detection
- Salesforce GPA-GUI-Detector: https://huggingface.co/Salesforce/GPA-GUI-Detector
- Ultralytics YOLO 문서: https://docs.ultralytics.com
- Roboflow: https://roboflow.com

## 9. v1.3.0 실행 결과 요약

실제 테스트 이미지:

```text
yolo\screenshots\test.png
```

Salesforce GPA-GUI-Detector 결과:

```text
model: yolo\models\gpa-gui-detector\model.pt
detections_count: 65
class distribution:
  icon: 65
```

MacPaw UI Elements Detection 결과:

```text
model: yolo\models\macpaw-ui-elements\ui-elements-detection.pt
detections_count: 81
class distribution:
  AXButton: 46
  AXTextArea: 34
  AXLink: 1
```

최종 판단:

```text
Salesforce 모델은 단일 icon 클래스 기반 클릭 후보 탐지에 가깝고,
MacPaw 모델은 버튼/텍스트 후보를 분리하므로 현재 UI 요소 탐지 실험에 더 적합하다.
```
