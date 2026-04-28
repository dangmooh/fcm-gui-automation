const form = document.getElementById("fcmForm");
const statusBox = document.getElementById("statusBox");

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const token = String(formData.get("token") || "").trim();
  const title = String(formData.get("title") || "").trim();
  const message = String(formData.get("message") || "").trim();

  if (!token || !title || !message) {
    statusBox.textContent = "모든 입력창을 채워주세요.";
    return;
  }

  statusBox.textContent =
    "기본 UI 동작 확인 완료: 실제 FCM 전송 기능은 다음 단계에서 연결하면 됩니다.";
});
