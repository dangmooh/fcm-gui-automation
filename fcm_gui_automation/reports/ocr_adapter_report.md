# OCR Adapter 구현 상세 보고서

작성일: 2026-05-03  
대상 프로젝트: `D:\app\fcm_gui_automation`  
대상 기능: `recognition/ocr_adapter.py` 기반 OCR 텍스트 읽기 기능

## 1. 이 프로그램은 무엇이고 어떻게 동작하는가

이번에 구현한 OCR 기능은 이미지 안에 그려진 글자를 문자열로 읽어내기 위한 보조 인식 모듈이다. 현재 프로젝트의 핵심 자동화 방식은 `pywinauto`를 이용해 GUI 컨트롤을 직접 찾고, 입력하고, 클릭하고, 컨트롤의 `window_text()` 값을 검증하는 구조다. 하지만 실제 GUI 자동화에서는 컨트롤 계층에서 텍스트가 잘 노출되지 않거나, 캔버스/이미지/커스텀 위젯처럼 화면에는 글자가 보이지만 UI Automation 트리에서는 텍스트를 읽을 수 없는 경우가 있다.

`OCRAdapter`는 이런 상황을 대비해 이미지 기반으로 텍스트를 읽는 기능을 제공한다. 즉, 화면 전체나 특정 영역을 캡처한 이미지 파일 또는 `PIL.Image` 객체를 입력받고, 그 이미지를 Tesseract OCR 엔진에 전달해서 사람이 보는 글자를 프로그램이 사용할 수 있는 문자열로 변환한다.

현재 구현된 기능의 핵심 목표는 다음과 같다.

- 이미지 파일에서 텍스트 읽기
- 메모리상의 `PIL.Image` 객체에서 텍스트 읽기
- OCR 결과에 기대 문자열이 포함되어 있는지 검증하기
- Tesseract 실행 파일 경로 자동 탐색
- CLI 명령으로 OCR 기능을 단독 테스트하기
- 나중에 `PyWinAutoAdapter`의 화면 캡처 기능이나 시나리오 action과 연결할 수 있는 독립 모듈 제공

현재 OCR 기능은 전체 자동화 시나리오에 강하게 결합되어 있지 않다. 의도적으로 먼저 독립 모듈로 만들었다. 이렇게 하면 OCR 엔진 자체가 정상 동작하는지 따로 확인할 수 있고, 이후 `verify_ocr_text` 같은 action을 추가할 때도 기존 구조를 크게 흔들지 않고 확장할 수 있다.

## 2. 전체 동작 흐름

OCR 기능은 다음 순서로 동작한다.

1. 사용자가 이미지 경로 또는 `PIL.Image` 객체를 `OCRAdapter.read_text()`에 전달한다.
2. `_open_image()`가 입력값의 종류를 확인한다.
3. 입력값이 이미 `PIL.Image`이면 복사본을 만든다.
4. 입력값이 문자열 또는 `Path`이면 실제 이미지 파일 경로로 해석하고 파일을 연다.
5. `preprocess=True`이면 `_preprocess()`가 이미지를 OCR에 유리한 형태로 바꾼다.
6. 전처리된 이미지를 `pytesseract.image_to_string()`에 전달한다.
7. Tesseract OCR 엔진이 이미지에서 텍스트를 추출한다.
8. `_normalize_text()`가 OCR 결과의 앞뒤 공백과 빈 줄을 정리한다.
9. 최종 문자열을 반환한다.

이를 코드 관점에서 간단히 나타내면 다음과 같다.

```python
adapter = OCRAdapter()
text = adapter.read_text("sample.png")
print(text)
```

검증 용도로는 다음처럼 사용할 수 있다.

```python
adapter = OCRAdapter()
adapter.verify_text("sample.png", "Hello OCR")
```

위 코드는 `sample.png` 이미지에서 OCR로 읽은 문자열 안에 `"Hello OCR"`이 들어 있으면 정상 종료하고, 없으면 `AssertionError`를 발생시킨다.

## 3. 이 기능이 필요한 이유

GUI 자동화에서 텍스트 검증은 크게 두 방식으로 할 수 있다.

첫 번째 방식은 UI Automation 계층에서 컨트롤을 찾아 텍스트 속성을 읽는 방식이다. 현재 프로젝트의 `PyWinAutoAdapter.verify_text()`가 이 방식을 사용한다. 이 방식은 빠르고 안정적이지만, 텍스트가 접근성 트리에 노출되어 있어야 한다.

두 번째 방식은 실제 화면 이미지를 캡처한 뒤 이미지 안의 글자를 OCR로 읽는 방식이다. 이번 `OCRAdapter`가 담당하는 방식이다. 이 방식은 UI Automation 정보가 부족한 화면에서도 동작할 수 있다. 예를 들어 다음과 같은 경우에 유용하다.

- 커스텀 페인팅된 PyQt 위젯
- 이미지로 렌더링되는 텍스트
- 브라우저 캔버스 또는 게임 화면
- UI Automation tree에 노출되지 않는 상태 메시지
- 컨트롤 이름과 실제 화면 표시 문자열이 다른 경우
- 외부 프로그램이라 내부 구조를 알 수 없는 경우

현재 프로젝트에서는 먼저 `ocr_adapter.py`에 OCR 읽기 자체를 구현했다. 다음 단계에서는 `PyWinAutoAdapter`가 창을 캡처한 이미지를 `OCRAdapter`에 넘기도록 연결할 수 있다.

## 4. 필요한 의존성과 환경 설정

OCR 기능을 사용하려면 Python 패키지와 외부 실행 파일이 모두 필요하다.

## 4-1. Python 패키지 의존성

`fcm_gui_automation/requirements.txt`에는 다음 의존성이 들어 있다.

```text
pywinauto>=0.6.8
PyQt6>=6.7.0
PyYAML>=6.0.2
Pillow>=10.4.0
pytesseract>=0.3.13
```

각 의존성의 역할은 다음과 같다.

- `pywinauto`: Windows GUI 자동화, 창 연결, 컨트롤 탐색, 클릭, 입력, 캡처 등에 사용된다.
- `PyQt6`: 테스트 대상 데스크톱 앱인 `fcm_desktop.py` 실행에 필요하다.
- `PyYAML`: YAML 시나리오 파일을 읽는 데 사용된다.
- `Pillow`: 이미지 파일 열기, 이미지 전처리, `PIL.Image` 객체 처리에 사용된다.
- `pytesseract`: Python 코드에서 Tesseract OCR 엔진을 호출하기 위한 래퍼다.

중요한 점은 `pytesseract` 자체가 OCR 엔진이 아니라는 것이다. `pytesseract`는 Python에서 Tesseract 실행 파일을 호출해주는 연결 계층이다. 실제 OCR 처리는 별도로 설치된 `tesseract.exe`가 수행한다.

## 4-2. Tesseract OCR 실행 파일

Windows에서는 Tesseract OCR 프로그램을 별도로 설치해야 한다. 현재 확인된 설치 경로는 다음과 같다.

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

현재 환경에서는 `tesseract` 명령이 PATH에 등록되어 있지는 않았다. 그래서 다음 명령은 실패했다.

```powershell
tesseract --version
```

하지만 직접 경로를 지정하면 정상 실행된다.

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
```

확인된 버전은 다음과 같다.

```text
tesseract v5.5.0.20241111
```

`OCRAdapter`는 PATH에 `tesseract`가 없더라도 Windows의 일반적인 설치 경로를 자동으로 찾아 사용하도록 구현되어 있다. 그래서 현재 환경에서는 다음 코드가 별도 경로 지정 없이 동작한다.

```python
from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter

adapter = OCRAdapter()
text = adapter.read_text("sample.png")
```

## 4-3. 설치 확인 명령

Python 패키지 설치 여부는 다음처럼 확인할 수 있다.

```powershell
python -c "import pytesseract; import PIL; print('ok')"
```

Tesseract 실행 파일 경로는 다음처럼 확인할 수 있다.

```powershell
where.exe tesseract
```

PATH에 등록되어 있지 않으면 `where.exe`는 찾지 못할 수 있다. 이 경우 직접 설치 경로를 확인한다.

```powershell
Test-Path 'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

현재 구현은 위 경로를 자동 탐색 후보에 포함하고 있다.

## 4-4. 한국어 OCR에 필요한 추가 설정

현재 `OCRAdapter`의 기본 언어는 영어다.

```python
lang: str = "eng"
```

한글을 읽으려면 Tesseract에 한국어 학습 데이터가 설치되어 있어야 하고, `lang="kor"` 또는 영어와 한글을 함께 쓰는 `lang="eng+kor"`를 넘겨야 한다.

예시는 다음과 같다.

```python
adapter = OCRAdapter(lang="kor")
text = adapter.read_text("korean_sample.png")
```

또는 CLI에서 다음처럼 실행할 수 있다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter korean_sample.png --lang kor
```

한국어 데이터 파일은 일반적으로 Tesseract 설치 폴더의 `tessdata` 안에 있어야 한다.

```text
C:\Program Files\Tesseract-OCR\tessdata\kor.traineddata
```

## 5. 소스 파일 구성

이번 OCR 기능과 직접 관련된 파일은 두 개다.

```text
fcm_gui_automation/
  recognition/
    ocr_adapter.py
  requirements.txt
```

`ocr_adapter.py`는 실제 OCR 기능을 담고 있다. 이미지 입력을 열고, 전처리하고, Tesseract로 텍스트를 읽고, 결과를 정리하는 코드가 들어 있다. 또한 이 파일은 모듈로 직접 실행할 수 있는 CLI도 포함한다.

`requirements.txt`는 OCR 기능에 필요한 Python 패키지 `pytesseract`를 추가로 명시한다.

## 6. `requirements.txt` 상세 설명

현재 파일 내용은 다음과 같다.

```text
pywinauto>=0.6.8
PyQt6>=6.7.0
PyYAML>=6.0.2
Pillow>=10.4.0
pytesseract>=0.3.13
```

이번 OCR 작업에서 새로 추가된 줄은 다음이다.

```text
pytesseract>=0.3.13
```

이 줄은 Python 코드에서 다음 import가 가능하도록 한다.

```python
import pytesseract
from pytesseract import TesseractNotFoundError
```

`pytesseract`는 내부적으로 `subprocess`를 사용해 `tesseract.exe`를 실행한다. 그래서 Python 패키지만 설치되어 있고 실제 Tesseract 프로그램이 없으면 OCR은 수행할 수 없다. 이 경우 `TesseractNotFoundError`가 발생한다.

이번 구현에서는 이 에러를 그대로 외부에 노출하지 않고, 사용자가 이해하기 쉬운 `RuntimeError`로 바꿔서 다시 발생시키도록 했다.

## 7. `ocr_adapter.py` 전체 코드와 구조

현재 `ocr_adapter.py`의 전체 코드는 다음과 같다.

```python
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from typing import Union

from PIL import Image, ImageOps
import pytesseract
from pytesseract import TesseractNotFoundError


ImageSource = Union[str, Path, Image.Image]


class OCRAdapter:
    def __init__(
        self,
        tesseract_cmd: str | None = None,
        lang: str = "eng",
        config: str = "--psm 6",
    ) -> None:
        resolved_cmd = tesseract_cmd or self._find_tesseract_cmd()
        if resolved_cmd:
            pytesseract.pytesseract.tesseract_cmd = str(resolved_cmd)
        self.lang = lang
        self.config = config

    def read_text(self, source: ImageSource, preprocess: bool = True) -> str:
        image = self._open_image(source)
        if preprocess:
            image = self._preprocess(image)

        try:
            text = pytesseract.image_to_string(
                image,
                lang=self.lang,
                config=self.config,
            )
        except TesseractNotFoundError as error:
            raise RuntimeError(
                "Tesseract executable was not found. Install Tesseract OCR "
                "or pass its path to OCRAdapter(tesseract_cmd=...)."
            ) from error

        return self._normalize_text(text)

    def read_text_from_file(self, image_path: str | Path, preprocess: bool = True) -> str:
        return self.read_text(image_path, preprocess=preprocess)

    def verify_text(
        self,
        source: ImageSource,
        expected: str,
        preprocess: bool = True,
    ) -> None:
        actual = self.read_text(source, preprocess=preprocess)
        if expected not in actual:
            raise AssertionError(
                f"Expected OCR text not found. expected={expected!r}, actual={actual!r}"
            )

    def _open_image(self, source: ImageSource) -> Image.Image:
        if isinstance(source, Image.Image):
            return source.copy()

        image_path = Path(source).expanduser().resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"OCR image file not found: {image_path}")

        return Image.open(image_path)

    def _preprocess(self, image: Image.Image) -> Image.Image:
        grayscale = ImageOps.grayscale(image)
        scaled = grayscale.resize(
            (grayscale.width * 2, grayscale.height * 2),
            Image.Resampling.LANCZOS,
        )
        return scaled.point(lambda pixel: 255 if pixel > 180 else 0)

    def _normalize_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _find_tesseract_cmd(self) -> str | None:
        found = shutil.which("tesseract")
        if found:
            return found

        candidates = [
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read text from an image with OCR.")
    parser.add_argument("image", help="Image path to read.")
    parser.add_argument("--lang", default="eng", help="Tesseract language code.")
    parser.add_argument(
        "--tesseract-cmd",
        help="Path to tesseract.exe when it is not available in PATH.",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Read the original image without grayscale/upscale/threshold preprocessing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    adapter = OCRAdapter(tesseract_cmd=args.tesseract_cmd, lang=args.lang)
    print(adapter.read_text(args.image, preprocess=not args.no_preprocess))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 8. 코드 상세 설명

## 8-1. future annotations

```python
from __future__ import annotations
```

이 코드는 타입 힌트를 런타임에 바로 평가하지 않고 문자열처럼 지연 평가하게 해준다. 이 파일에서는 다음과 같은 타입 힌트를 사용한다.

```python
tesseract_cmd: str | None = None
```

Python 3.10 이상에서는 `str | None` 문법이 가능하지만, `from __future__ import annotations`를 사용하면 타입 힌트 처리에서 더 유연하게 동작한다. 또한 `Image.Image` 같은 외부 타입을 타입 힌트에 사용할 때 런타임 의존성 부담을 줄이는 데 도움이 된다.

## 8-2. 표준 라이브러리 import

```python
import argparse
from pathlib import Path
import shutil
from typing import Union
```

각 import의 역할은 다음과 같다.

`argparse`는 CLI 실행을 위해 사용한다. 이 파일은 단순 라이브러리로 import해서 사용할 수도 있지만, 다음처럼 직접 실행할 수도 있다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png
```

이때 명령행 인자를 해석하는 코드가 `argparse`다.

`Path`는 파일 경로를 다루기 위해 사용한다. 문자열 경로를 안전하게 절대 경로로 바꾸거나 파일 존재 여부를 확인할 때 쓴다.

```python
image_path = Path(source).expanduser().resolve()
```

`shutil`은 실행 파일 탐색에 사용한다. 특히 `shutil.which("tesseract")`는 현재 PATH에서 `tesseract` 명령을 찾는다.

```python
found = shutil.which("tesseract")
```

`Union`은 타입 힌트에서 여러 입력 타입을 허용하기 위해 사용한다.

## 8-3. 외부 라이브러리 import

```python
from PIL import Image, ImageOps
import pytesseract
from pytesseract import TesseractNotFoundError
```

`Image`는 Pillow의 이미지 객체를 다루기 위해 사용한다. 이미지 파일을 열거나, 이미 만들어진 `PIL.Image` 객체인지 검사할 때 필요하다.

```python
if isinstance(source, Image.Image):
    return source.copy()
```

`ImageOps`는 이미지 변환 기능을 제공한다. 이번 구현에서는 컬러 이미지를 흑백 이미지로 바꾸는 데 사용한다.

```python
grayscale = ImageOps.grayscale(image)
```

`pytesseract`는 Tesseract OCR 엔진을 Python에서 호출하기 위한 라이브러리다. 실제 텍스트 추출은 다음 함수가 수행한다.

```python
text = pytesseract.image_to_string(
    image,
    lang=self.lang,
    config=self.config,
)
```

`TesseractNotFoundError`는 Tesseract 실행 파일을 찾을 수 없을 때 발생하는 예외다. 이 예외를 잡아서 더 이해하기 쉬운 메시지로 바꿔준다.

## 8-4. ImageSource 타입 정의

```python
ImageSource = Union[str, Path, Image.Image]
```

`ImageSource`는 OCR 입력으로 허용하는 값의 종류를 정의한다.

현재 허용되는 입력은 세 가지다.

- `str`: 이미지 파일 경로 문자열
- `Path`: `pathlib.Path` 이미지 파일 경로
- `Image.Image`: 이미 메모리에 올라와 있는 Pillow 이미지 객체

이 타입 정의 덕분에 `read_text()`는 파일 경로와 메모리 이미지를 모두 받을 수 있다.

예시는 다음과 같다.

```python
adapter = OCRAdapter()

text1 = adapter.read_text("sample.png")
text2 = adapter.read_text(Path("sample.png"))
text3 = adapter.read_text(pil_image)
```

이 설계는 나중에 `PyWinAutoAdapter`와 연결할 때 중요하다. `pywinauto`의 창 캡처는 파일로 저장하지 않고도 `PIL.Image` 객체를 반환할 수 있다. 따라서 화면 캡처 이미지를 곧바로 OCR로 넘길 수 있다.

```python
screenshot = self.window.capture_as_image()
text = self.ocr_adapter.read_text(screenshot)
```

## 8-5. OCRAdapter 클래스

```python
class OCRAdapter:
```

`OCRAdapter`는 OCR 관련 책임을 한 곳에 모아둔 클래스다. 현재 프로젝트의 `recognition` 폴더에는 여러 인식 방식이 들어갈 수 있다.

```text
recognition/
  pywinauto_adapter.py
  color_adapter.py
  opencv_adapter.py
  ocr_adapter.py
```

`pywinauto_adapter.py`는 UI Automation 기반 인식과 조작을 담당한다. `color_adapter.py`는 특정 영역의 색상 검증을 담당한다. `ocr_adapter.py`는 이미지 기반 텍스트 인식을 담당한다.

이렇게 분리하면 다음 장점이 있다.

- OCR 로직이 `PyWinAutoAdapter` 안에 섞이지 않는다.
- OCR 전처리나 언어 설정을 별도로 관리할 수 있다.
- OCR 기능만 단독 테스트할 수 있다.
- 나중에 Tesseract가 아닌 다른 OCR 엔진으로 교체할 때 영향 범위가 줄어든다.

## 8-6. `__init__` 생성자

```python
def __init__(
    self,
    tesseract_cmd: str | None = None,
    lang: str = "eng",
    config: str = "--psm 6",
) -> None:
    resolved_cmd = tesseract_cmd or self._find_tesseract_cmd()
    if resolved_cmd:
        pytesseract.pytesseract.tesseract_cmd = str(resolved_cmd)
    self.lang = lang
    self.config = config
```

생성자는 OCRAdapter 객체를 만들 때 OCR 실행에 필요한 기본 설정을 저장한다.

매개변수는 세 개다.

`tesseract_cmd`는 `tesseract.exe`의 직접 경로다. 기본값은 `None`이다. 사용자가 직접 지정하면 그 경로를 사용한다.

```python
adapter = OCRAdapter(
    tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
```

`lang`은 OCR 언어다. 기본값은 `"eng"`이다. 영어 텍스트를 읽는 설정이다. 한국어를 읽으려면 `"kor"` 또는 `"eng+kor"`로 바꿀 수 있다.

```python
adapter = OCRAdapter(lang="eng+kor")
```

`config`는 Tesseract에 전달하는 세부 옵션이다. 기본값은 `"--psm 6"`이다.

```python
config: str = "--psm 6"
```

`--psm`은 Page Segmentation Mode의 약자다. OCR 엔진이 이미지를 어떤 구조의 텍스트로 볼지 결정한다. `--psm 6`은 일반적으로 "하나의 균일한 텍스트 블록"으로 보는 모드다. 버튼 라벨, 상태 메시지, 작은 텍스트 영역을 읽는 자동화 목적에서는 비교적 무난한 기본값이다.

생성자 내부의 첫 줄은 다음과 같다.

```python
resolved_cmd = tesseract_cmd or self._find_tesseract_cmd()
```

이 코드는 사용자가 직접 `tesseract_cmd`를 넘겼으면 그 값을 우선 사용하고, 넘기지 않았으면 `_find_tesseract_cmd()`로 자동 탐색한다.

다음 코드는 찾은 경로를 `pytesseract`에 설정한다.

```python
if resolved_cmd:
    pytesseract.pytesseract.tesseract_cmd = str(resolved_cmd)
```

`pytesseract.pytesseract.tesseract_cmd`는 `pytesseract`가 내부적으로 호출할 Tesseract 실행 파일 경로다. PATH에 `tesseract`가 등록되어 있으면 굳이 설정하지 않아도 되지만, 현재 환경처럼 PATH에는 없고 설치 폴더에는 있는 경우 이 설정이 필요하다.

마지막으로 객체 속성에 언어와 config를 저장한다.

```python
self.lang = lang
self.config = config
```

이 값들은 `read_text()`에서 실제 OCR 호출 시 사용된다.

## 8-7. `read_text()`

```python
def read_text(self, source: ImageSource, preprocess: bool = True) -> str:
    image = self._open_image(source)
    if preprocess:
        image = self._preprocess(image)

    try:
        text = pytesseract.image_to_string(
            image,
            lang=self.lang,
            config=self.config,
        )
    except TesseractNotFoundError as error:
        raise RuntimeError(
            "Tesseract executable was not found. Install Tesseract OCR "
            "or pass its path to OCRAdapter(tesseract_cmd=...)."
        ) from error

    return self._normalize_text(text)
```

`read_text()`는 이 모듈의 핵심 메서드다. 외부 코드가 OCR을 사용하려면 보통 이 메서드를 호출한다.

첫 줄은 입력 이미지를 연다.

```python
image = self._open_image(source)
```

`source`가 문자열 경로이면 파일을 열고, `Path`이면 파일을 열고, 이미 `Image.Image`이면 복사해서 반환한다.

다음 코드는 전처리 여부를 결정한다.

```python
if preprocess:
    image = self._preprocess(image)
```

기본값은 `True`다. 즉, 기본적으로 OCR 전에 이미지를 흑백화하고 확대하고 이진화한다. 전처리를 끄고 원본 이미지 그대로 OCR을 하고 싶으면 다음처럼 호출한다.

```python
text = adapter.read_text("sample.png", preprocess=False)
```

실제 OCR 호출은 다음 부분이다.

```python
text = pytesseract.image_to_string(
    image,
    lang=self.lang,
    config=self.config,
)
```

`image_to_string()`은 이미지 안의 글자를 문자열로 반환한다. 여기서 `lang`과 `config`는 생성자에서 저장한 값을 사용한다.

Tesseract 실행 파일을 찾지 못하면 `TesseractNotFoundError`가 발생한다. 이 구현에서는 그 예외를 잡아서 다음 메시지를 가진 `RuntimeError`로 바꾼다.

```python
"Tesseract executable was not found. Install Tesseract OCR "
"or pass its path to OCRAdapter(tesseract_cmd=...)."
```

이렇게 한 이유는 사용자가 `pytesseract` 내부 에러 메시지보다 더 직접적인 해결 방법을 볼 수 있게 하기 위해서다.

마지막 줄은 OCR 결과를 정리한다.

```python
return self._normalize_text(text)
```

Tesseract 결과에는 빈 줄이나 앞뒤 공백이 섞일 수 있다. `_normalize_text()`는 이런 불필요한 공백을 줄인다.

## 8-8. `read_text_from_file()`

```python
def read_text_from_file(self, image_path: str | Path, preprocess: bool = True) -> str:
    return self.read_text(image_path, preprocess=preprocess)
```

이 메서드는 파일 경로에서 텍스트를 읽는다는 의도를 더 명확하게 표현하기 위한 편의 메서드다.

내부에서는 별도 로직을 만들지 않고 `read_text()`를 그대로 호출한다. 이렇게 하면 OCR 처리 로직이 중복되지 않는다.

다음 두 코드는 사실상 같은 동작을 한다.

```python
adapter.read_text("sample.png")
```

```python
adapter.read_text_from_file("sample.png")
```

`read_text_from_file()`은 호출하는 쪽 코드가 파일 기반 OCR이라는 의미를 드러내고 싶을 때 사용할 수 있다.

## 8-9. `verify_text()`

```python
def verify_text(
    self,
    source: ImageSource,
    expected: str,
    preprocess: bool = True,
) -> None:
    actual = self.read_text(source, preprocess=preprocess)
    if expected not in actual:
        raise AssertionError(
            f"Expected OCR text not found. expected={expected!r}, actual={actual!r}"
        )
```

`verify_text()`는 OCR 결과가 기대 문자열을 포함하는지 검증한다.

먼저 OCR을 수행한다.

```python
actual = self.read_text(source, preprocess=preprocess)
```

그 다음 기대 문자열이 OCR 결과 안에 포함되어 있는지 확인한다.

```python
if expected not in actual:
```

포함되어 있지 않으면 `AssertionError`를 발생시킨다.

```python
raise AssertionError(
    f"Expected OCR text not found. expected={expected!r}, actual={actual!r}"
)
```

이 에러 메시지에는 기대값과 실제 OCR 결과가 모두 들어간다. 자동화 실패 시 무엇을 기대했고 실제로 무엇을 읽었는지 확인할 수 있다.

예시는 다음과 같다.

```python
adapter = OCRAdapter()
adapter.verify_text("result.png", "Saved successfully")
```

이 코드는 `result.png` 안에서 `"Saved successfully"`를 OCR로 찾는다. 찾으면 아무 것도 반환하지 않고 정상 종료한다. 찾지 못하면 테스트 실패로 볼 수 있는 `AssertionError`를 발생시킨다.

## 8-10. `_open_image()`

```python
def _open_image(self, source: ImageSource) -> Image.Image:
    if isinstance(source, Image.Image):
        return source.copy()

    image_path = Path(source).expanduser().resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"OCR image file not found: {image_path}")

    return Image.open(image_path)
```

`_open_image()`는 OCR 입력값을 `PIL.Image` 객체로 통일하는 내부 메서드다.

먼저 입력값이 이미 Pillow 이미지인지 확인한다.

```python
if isinstance(source, Image.Image):
    return source.copy()
```

이미 이미지 객체라면 `copy()`를 반환한다. 원본 이미지를 직접 수정하지 않기 위해서다. 이후 `_preprocess()`에서 흑백화, 확대, 이진화 같은 처리가 이루어질 수 있으므로 원본 객체를 보호하는 것이 안전하다.

입력값이 이미지 객체가 아니면 파일 경로로 처리한다.

```python
image_path = Path(source).expanduser().resolve()
```

이 코드는 다음 처리를 한다.

- 문자열 또는 `Path`를 `Path` 객체로 만든다.
- `~`가 들어간 사용자 홈 경로를 확장한다.
- 상대 경로를 절대 경로로 바꾼다.

그 다음 실제 파일이 있는지 확인한다.

```python
if not image_path.is_file():
    raise FileNotFoundError(f"OCR image file not found: {image_path}")
```

파일이 없으면 즉시 `FileNotFoundError`를 발생시킨다. OCR 단계까지 가기 전에 입력 경로 오류를 명확하게 알려주기 위함이다.

파일이 있으면 Pillow로 이미지를 연다.

```python
return Image.open(image_path)
```

## 8-11. `_preprocess()`

```python
def _preprocess(self, image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    scaled = grayscale.resize(
        (grayscale.width * 2, grayscale.height * 2),
        Image.Resampling.LANCZOS,
    )
    return scaled.point(lambda pixel: 255 if pixel > 180 else 0)
```

`_preprocess()`는 OCR 인식률을 높이기 위한 간단한 이미지 전처리를 수행한다.

첫 단계는 흑백 변환이다.

```python
grayscale = ImageOps.grayscale(image)
```

컬러 정보는 텍스트 OCR에 항상 필요한 것은 아니다. 오히려 배경색이나 장식 색상이 OCR을 방해할 수 있다. 흑백으로 바꾸면 Tesseract가 글자와 배경의 밝기 차이에 집중할 수 있다.

두 번째 단계는 2배 확대다.

```python
scaled = grayscale.resize(
    (grayscale.width * 2, grayscale.height * 2),
    Image.Resampling.LANCZOS,
)
```

GUI 화면의 작은 글자는 OCR이 놓치기 쉽다. 이미지를 2배 키우면 작은 글자의 획이 더 뚜렷해진다. `Image.Resampling.LANCZOS`는 고품질 리샘플링 방식이다.

세 번째 단계는 이진화다.

```python
return scaled.point(lambda pixel: 255 if pixel > 180 else 0)
```

이 코드는 각 픽셀의 밝기를 검사한다. 밝기가 180보다 크면 흰색 255로 만들고, 그렇지 않으면 검은색 0으로 만든다. 결과적으로 이미지는 검정과 흰색만 가진 이미지가 된다.

이진화의 장점은 글자와 배경의 경계를 명확하게 만든다는 것이다. 단점은 배경이 복잡하거나 글자가 연한 색일 때 정보가 과하게 날아갈 수 있다는 점이다. 그래서 `read_text()`에는 전처리를 끌 수 있는 옵션이 있다.

```python
adapter.read_text("sample.png", preprocess=False)
```

향후 개선한다면 threshold 값 `180`을 설정값으로 빼거나, adaptive threshold, denoise, crop 같은 옵션을 추가할 수 있다.

## 8-12. `_normalize_text()`

```python
def _normalize_text(self, text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
```

`_normalize_text()`는 OCR 결과 문자열을 정리한다.

Tesseract는 결과에 빈 줄이나 불필요한 앞뒤 공백을 포함하는 경우가 있다. 이 메서드는 먼저 줄 단위로 나눈다.

```python
text.splitlines()
```

각 줄의 앞뒤 공백을 제거한다.

```python
line.strip()
```

그 결과를 리스트로 만든다.

```python
lines = [line.strip() for line in text.splitlines()]
```

마지막으로 빈 줄은 제외하고 다시 줄바꿈으로 합친다.

```python
return "\n".join(line for line in lines if line)
```

예를 들어 OCR 원본 결과가 다음과 같다고 하자.

```text

  Hello OCR 123

```

정규화 후에는 다음처럼 바뀐다.

```text
Hello OCR 123
```

이렇게 하면 이후 `expected in actual` 비교가 더 안정적이다.

## 8-13. `_find_tesseract_cmd()`

```python
def _find_tesseract_cmd(self) -> str | None:
    found = shutil.which("tesseract")
    if found:
        return found

    candidates = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None
```

`_find_tesseract_cmd()`는 Tesseract 실행 파일을 자동으로 찾는다.

첫 번째로 PATH에서 찾는다.

```python
found = shutil.which("tesseract")
if found:
    return found
```

사용자가 Tesseract 설치 과정에서 PATH 등록을 했다면 여기서 찾을 수 있다.

PATH에서 못 찾으면 Windows 기본 설치 후보 경로를 확인한다.

```python
candidates = [
    Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
    Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
]
```

각 후보 경로에 실제 파일이 있는지 검사한다.

```python
for candidate in candidates:
    if candidate.is_file():
        return str(candidate)
```

찾으면 문자열 경로를 반환한다. 아무 것도 찾지 못하면 `None`을 반환한다.

```python
return None
```

`None`이 반환되면 생성자에서 `pytesseract.pytesseract.tesseract_cmd`를 설정하지 않는다. 이 상태에서 OCR을 실행하면 `pytesseract`가 기본 방식으로 `tesseract`를 찾으려고 시도하고, 실패하면 `TesseractNotFoundError`가 발생한다.

## 8-14. `parse_args()`

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read text from an image with OCR.")
    parser.add_argument("image", help="Image path to read.")
    parser.add_argument("--lang", default="eng", help="Tesseract language code.")
    parser.add_argument(
        "--tesseract-cmd",
        help="Path to tesseract.exe when it is not available in PATH.",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Read the original image without grayscale/upscale/threshold preprocessing.",
    )
    return parser.parse_args()
```

`parse_args()`는 명령행에서 이 파일을 직접 실행할 때 옵션을 해석한다.

기본 사용법은 다음과 같다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png
```

필수 위치 인자는 `image`다.

```python
parser.add_argument("image", help="Image path to read.")
```

OCR 언어는 `--lang`으로 지정한다.

```python
parser.add_argument("--lang", default="eng", help="Tesseract language code.")
```

예를 들어 한국어 OCR은 다음처럼 실행할 수 있다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png --lang kor
```

Tesseract 실행 파일 경로를 직접 지정하려면 `--tesseract-cmd`를 사용한다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

전처리를 끄려면 `--no-preprocess`를 사용한다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png --no-preprocess
```

`--no-preprocess`는 `action="store_true"`로 정의되어 있다.

```python
parser.add_argument(
    "--no-preprocess",
    action="store_true",
    help="Read the original image without grayscale/upscale/threshold preprocessing.",
)
```

이 옵션이 있으면 `args.no_preprocess`가 `True`가 된다.

## 8-15. `main()`

```python
def main() -> int:
    args = parse_args()
    adapter = OCRAdapter(tesseract_cmd=args.tesseract_cmd, lang=args.lang)
    print(adapter.read_text(args.image, preprocess=not args.no_preprocess))
    return 0
```

`main()`은 CLI 실행 시 실제 작업을 수행한다.

먼저 명령행 인자를 읽는다.

```python
args = parse_args()
```

그 다음 인자값으로 OCRAdapter를 만든다.

```python
adapter = OCRAdapter(tesseract_cmd=args.tesseract_cmd, lang=args.lang)
```

사용자가 `--tesseract-cmd`를 넘겼으면 그 경로를 사용한다. 넘기지 않았으면 생성자 내부에서 자동 탐색한다.

마지막으로 이미지를 OCR로 읽고 결과를 출력한다.

```python
print(adapter.read_text(args.image, preprocess=not args.no_preprocess))
```

여기서 `preprocess=not args.no_preprocess`가 중요하다. 기본적으로 `args.no_preprocess`는 `False`다. 그래서 `not False`는 `True`가 되어 전처리를 수행한다. 사용자가 `--no-preprocess`를 지정하면 `args.no_preprocess`가 `True`가 되고, `not True`는 `False`가 되어 전처리를 하지 않는다.

정상 종료를 나타내기 위해 `0`을 반환한다.

```python
return 0
```

## 8-16. 모듈 직접 실행 구문

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

이 코드는 파일이 직접 실행될 때만 `main()`을 호출한다.

예를 들어 다음처럼 실행하면 동작한다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png
```

하지만 다른 코드에서 import할 때는 실행되지 않는다.

```python
from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter
```

`raise SystemExit(main())`는 `main()`의 반환값을 프로세스 종료 코드로 사용하게 한다. `main()`이 `0`을 반환하면 정상 종료로 처리된다.

## 9. 현재 검증한 내용

이번 구현 후 다음 검증을 수행했다.

## 9-1. Tesseract 직접 실행 확인

다음 명령으로 Tesseract 실행 파일이 실제로 동작하는지 확인했다.

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
```

확인된 버전은 다음과 같다.

```text
tesseract v5.5.0.20241111
```

## 9-2. Python에서 Tesseract 버전 확인

다음 코드로 `pytesseract`에서 직접 경로를 지정했을 때 Tesseract 버전을 읽을 수 있는지 확인했다.

```powershell
python -c "import pytesseract; pytesseract.pytesseract.tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe'; print(pytesseract.get_tesseract_version())"
```

결과는 다음과 같았다.

```text
5.5.0.20241111
```

## 9-3. OCRAdapter 기본 경로 자동 탐색 확인

처음에는 PATH에 `tesseract`가 없어서 `OCRAdapter()` 기본 생성자가 실패할 수 있었다. 그래서 `_find_tesseract_cmd()`를 추가해 Windows 기본 설치 경로를 자동 탐색하도록 개선했다.

개선 후 다음 테스트가 성공했다.

```powershell
python -c "from PIL import Image, ImageDraw, ImageFont; from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter; img=Image.new('RGB',(520,140),'white'); draw=ImageDraw.Draw(img); font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',48); draw.text((30,35),'Hello OCR 123',fill='black',font=font); print(repr(OCRAdapter().read_text(img)))"
```

결과는 다음과 같았다.

```text
'Hello OCR 123'
```

즉, 파일이 아닌 메모리 이미지에서도 OCRAdapter가 정상적으로 텍스트를 읽었다.

## 9-4. 문법 컴파일 확인

다음 명령으로 문법 오류가 없는지 확인했다.

```powershell
python -m compileall fcm_gui_automation\recognition\ocr_adapter.py
```

컴파일은 정상 통과했다.

## 9-5. CLI help 확인

다음 명령으로 CLI 옵션이 정상 표시되는지 확인했다.

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter --help
```

출력은 다음 구조로 표시되었다.

```text
usage: ocr_adapter.py [-h] [--lang LANG] [--tesseract-cmd TESSERACT_CMD]
                      [--no-preprocess]
                      image

Read text from an image with OCR.
```

## 10. 사용 예시

## 10-1. 이미지 파일에서 텍스트 읽기

```python
from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter

adapter = OCRAdapter()
text = adapter.read_text("reports/screenshots/result.png")
print(text)
```

## 10-2. Tesseract 경로를 직접 지정하기

```python
from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter

adapter = OCRAdapter(
    tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
text = adapter.read_text("sample.png")
print(text)
```

## 10-3. 한국어 OCR 사용하기

```python
from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter

adapter = OCRAdapter(lang="kor")
text = adapter.read_text("korean_sample.png")
print(text)
```

영어와 한국어가 섞여 있으면 다음처럼 쓸 수 있다.

```python
adapter = OCRAdapter(lang="eng+kor")
```

## 10-4. OCR 결과 검증하기

```python
from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter

adapter = OCRAdapter()
adapter.verify_text("result.png", "Hello OCR")
```

기대 문자열이 OCR 결과 안에 없으면 `AssertionError`가 발생한다.

## 10-5. CLI에서 실행하기

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png
```

한국어 OCR:

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png --lang kor
```

전처리 없이 OCR:

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png --no-preprocess
```

Tesseract 경로 직접 지정:

```powershell
python -m fcm_gui_automation.recognition.ocr_adapter sample.png --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## 11. 현재 구현의 한계

현재 OCRAdapter는 첫 단계 구현이므로 기능이 단순하다.

첫 번째 한계는 전처리 방식이 고정되어 있다는 점이다. 현재 threshold 값은 `180`으로 고정되어 있다.

```python
return scaled.point(lambda pixel: 255 if pixel > 180 else 0)
```

배경이 어둡거나 글자가 연한 색이면 이 값이 맞지 않을 수 있다.

두 번째 한계는 영역 OCR이 아직 없다. 현재는 입력 이미지 전체를 읽는다. 실제 GUI 자동화에서는 창 전체보다 특정 영역만 OCR하는 것이 더 안정적일 수 있다. 예를 들어 상태 표시줄, 결과 영역, 버튼 근처만 잘라서 OCR하면 오인식이 줄어든다.

세 번째 한계는 시나리오 action에 아직 연결되어 있지 않다는 점이다. 지금은 `OCRAdapter`를 직접 호출하거나 CLI로 실행해야 한다. 아직 YAML에서 다음과 같은 action을 바로 쓸 수는 없다.

```yaml
- action: "verify_ocr_text"
  value: "Saved successfully"
```

네 번째 한계는 OCR 결과 보정이 최소화되어 있다는 점이다. OCR은 `0`과 `O`, `1`과 `l`, 공백, 줄바꿈을 잘못 인식할 수 있다. 현재는 앞뒤 공백과 빈 줄만 정리한다.

다섯 번째 한계는 언어 데이터 설치 여부를 별도로 검사하지 않는다는 점이다. `lang="kor"`를 지정했는데 `kor.traineddata`가 없으면 Tesseract가 에러를 낼 수 있다.

## 12. 다음 확장 방향

## 12-1. `PyWinAutoAdapter`에 OCRAdapter 연결

가장 자연스러운 다음 단계는 `PyWinAutoAdapter` 안에 `OCRAdapter`를 포함시키는 것이다.

예상 구조는 다음과 같다.

```python
from recognition.ocr_adapter import OCRAdapter

class PyWinAutoAdapter(RecognitionAdapter):
    def __init__(self, base_dir: Path, config: dict, logger) -> None:
        ...
        self.ocr_adapter = OCRAdapter()
```

이후 창 캡처 이미지를 OCR로 읽을 수 있다.

```python
def read_window_text_by_ocr(self) -> str:
    if self.window is None:
        raise RuntimeError("Window is not connected.")
    screenshot = self.window.capture_as_image()
    return self.ocr_adapter.read_text(screenshot)
```

## 12-2. `verify_ocr_text` action 추가

`core/action_executor.py`에 새 action을 추가할 수 있다.

예상 YAML은 다음과 같다.

```yaml
- action: "verify_ocr_text"
  value: "Saved successfully"
```

예상 executor 코드는 다음과 같다.

```python
self.handlers = {
    ...
    "verify_ocr_text": self._verify_ocr_text,
}

def _verify_ocr_text(self, step: dict) -> None:
    self.adapter.verify_ocr_text(step["value"])
```

그리고 `PyWinAutoAdapter`에는 다음 메서드를 추가할 수 있다.

```python
def verify_ocr_text(self, expected: str) -> None:
    if self.window is None:
        raise RuntimeError("Window is not connected.")
    screenshot = self.window.capture_as_image()
    self.ocr_adapter.verify_text(screenshot, expected)
    self.logger.info("Verified OCR text: %s", expected)
```

## 12-3. 특정 영역 OCR

전체 창을 OCR하면 불필요한 글자가 많아져 오인식 가능성이 커진다. 그래서 영역 지정 기능을 추가하는 것이 좋다.

예상 YAML은 다음과 같다.

```yaml
- action: "verify_ocr_text"
  value: "Saved successfully"
  region:
    x: 10
    y: 300
    width: 500
    height: 80
```

Pillow에서는 다음처럼 이미지를 자를 수 있다.

```python
cropped = image.crop((x, y, x + width, y + height))
```

이 기능을 `OCRAdapter`에 넣을 수도 있고, `PyWinAutoAdapter`에서 캡처한 뒤 crop해서 넘길 수도 있다.

## 12-4. OCR 결과 로그와 실패 스크린샷 저장

OCR 검증이 실패하면 실제 OCR 결과와 이미지를 함께 저장하는 것이 좋다. 예를 들어 다음 정보를 로그에 남길 수 있다.

- 기대 문자열
- 실제 OCR 결과
- OCR 대상 이미지 경로
- 전처리 여부
- 언어 설정
- Tesseract config

실패 이미지까지 저장하면 나중에 오인식 원인을 분석하기 쉽다.

## 12-5. 전처리 옵션 확장

현재 전처리는 다음 세 단계다.

1. grayscale
2. 2배 확대
3. threshold 180 이진화

향후에는 다음 옵션을 추가할 수 있다.

- 확대 배율 설정
- threshold 값 설정
- 전처리 이미지 저장
- adaptive threshold
- blur 또는 sharpen
- 색상 반전
- 특정 배경색 제거

## 13. 결론

이번 `OCRAdapter` 구현은 이미지 기반 텍스트 인식을 프로젝트에 도입하기 위한 첫 번째 안정적인 기반이다. 지금 단계에서는 자동화 시나리오와 직접 연결하기보다, OCR 엔진을 독립적으로 호출하고 검증할 수 있는 작은 모듈로 구성했다.

현재 구현으로 가능한 일은 다음과 같다.

- 이미지 파일에서 텍스트 읽기
- `PIL.Image` 객체에서 텍스트 읽기
- OCR 결과 문자열 정리
- 기대 문자열 포함 여부 검증
- Tesseract 실행 파일 자동 탐색
- CLI로 OCR 기능 단독 실행

검증 결과, 현재 설치된 Tesseract 5.5.0 환경에서 샘플 이미지 `"Hello OCR 123"`을 정확히 읽는 것을 확인했다.

다음 개발 단계에서는 이 모듈을 `PyWinAutoAdapter`와 연결해 실제 앱 창 캡처 이미지를 OCR로 읽고, YAML 시나리오에서 `verify_ocr_text` 같은 action으로 사용할 수 있게 만드는 것이 적절하다.
