# PROJECT PLAN: BX-T4 - VIDEO INTELLIGENCE ENGINE
## Hệ thống RAG Đa phương thức cho Video Thương mại Điện tử Đông Nam Á

Bản kế hoạch này được thiết kế để triển khai cấp tốc trong khuôn khổ Hackathon, tối ưu hóa theo các tiêu chí chấm điểm: Độ chính xác (30%), Thực tế & UX (20%), Triển khai kỹ thuật (20%).

---

## 1. TỔNG QUAN KIẾN TRÚC & TECH STACK

### 1.1. Công nghệ Sử dụng
- **AI Core Model:** `Seed-2.0-mini-260428` (Thông qua BytePlus ModelArk API) - Xử lý Omni (ASR, OCR, Visual Understanding).
- **Backend:** Python (FastAPI) - Xử lý bất đồng bộ, streaming tốt.
- **Frontend:** React.js / Next.js + TailwindCSS + Lucide Icons + Chart.js.
- **Video Processing:** `ffmpeg` (Trích xuất frame) + `PySceneDetect` (Cắt cảnh tự động).
- **Database:** SQLite (Lưu trữ Metadata, Timeline, Transcript).

### 1.2. Sơ đồ Luồng Dữ liệu (Pipeline)
1. **Video Input** -> 2. **PySceneDetect** (Tách Shot) -> 3. **FFmpeg** (Bóc 1 Frame/s) -> 4. **Seed 2.0 Mini Omni** (Trích xuất Metadata JSON) -> 5. **Lưu Trữ SQLite DB** -> 6. **User Query** -> 7. **Two-Stage Retrieval Engine** -> 8. **Grounded Answer UI** (Video Player Sync).

---

## 2. KẾ HOẠCH HÀNH ĐỘNG CHI TIẾT (4 NGÀY SPRINT)

### GIAI ĐOẠN 1: SETUP HẠ TẦNG & PIPELINE XỬ LÝ VIDEO TRONG SUỐT (NGÀY 1)
*Mục tiêu: Xây dựng xong lõi Backend, bóc tách được video thành dữ liệu có cấu trúc.*

- [ ] **Task 1.1:** Khởi tạo Workspace dự án, cấu hình môi trường ảo Python và quản lý dependencies.
- [ ] **Task 1.2:** Khởi tạo project FastAPI. Viết module tiếp nhận video (Upload local hoặc URL) và lưu vào thư mục tạm `/storage/raw_videos`.
- [ ] **Task 1.3:** Tích hợp `PySceneDetect` để tự động chia video thành các phân đoạn demo SKU (Virtual Windows).
- [ ] **Task 1.4:** Viết script `ffmpeg` trích xuất khung hình với mật độ 1 frame/giây, lưu vào `/storage/thumbnails/{video_id}/{timestamp}.jpg`.
- [ ] **Task 1.5:** Viết hàm gọi API `Seed-2.0-mini-260428` để phân tích từng đoạn video ngắn, yêu cầu model trả về cấu trúc JSON: Lời thoại (ASR), Văn bản màn hình (OCR giá, voucher), Sự kiện âm thanh (nhạc jingle, tiếng cười), và Thực thể (SKU nào đang xuất hiện).

### GIAI ĐOẠN 2: THIẾT KẾ DATABASE & CƠ CHẾ TRUY VẤN HAI TẦNG (NGÀY 2)
*Mục tiêu: Lưu trữ dữ liệu thông minh và xây dựng bộ lọc câu hỏi đạt độ chính xác ±3s.*

- [ ] **Task 2.1:** Thiết kế Schema Database (SQLite):
  - Bảng `Videos`: `id`, `name`, `url`, `duration`, `status`.
  - Bảng `Timeline_Metadata`: `id`, `video_id`, `timestamp_start`, `timestamp_end`, `transcript`, `ocr_text`, `audio_event`, `detected_skus`, `energy_score`.
- [ ] **Task 2.2:** Xây dựng **Two-Stage Retrieval Engine (Bộ lọc 2 tầng)**:
  - *Tầng 1:* Quét nhanh bằng từ khóa / Full-text Search trên SQLite để tìm ra phân đoạn (khoảng 1-2 phút) chứa từ khóa hoặc SKU người dùng hỏi.
  - *Tầng 2:* Gửi phân đoạn video ngắn đó + Câu hỏi của User lên `Seed-2.0-mini-260428` để lập luận sâu và trả ra câu trả lời cuối cùng.
- [ ] **Task 2.3:** Viết API `POST /api/query` nhận câu hỏi, trả về câu trả lời định dạng: `answer`, `timestamp`, `thumbnail_url`, `reasoning_proof`.
- [ ] **Task 2.4:** Viết API Kiểm tra Compliance (`GET /api/compliance`): Hệ thống tự động quét tìm các khoảnh khắc lời nói mâu thuẫn với hình ảnh (Ví dụ: Host nói "Chính hãng" nhưng không có chứng nhận trên màn hình).

### GIAI ĐOẠN 3: TRIỂN KHAI GIAO DIỆN 3 CỘT (NGÀY 3)
*Mục tiêu: Đạt điểm tối đa phần UX/UI thực tế, đồng bộ Video Player.*

- [ ] **Task 3.1:** Dựng Layout UI 3 Cột bằng TailwindCSS:
  - *Cột Trái:* Trình khám phá Timeline (SKU Highlights, Sự kiện âm thanh, Điểm vi phạm Compliance).
  - *Cột Giữa:* Video Player (Sử dụng `video.js` hoặc `react-player`) + Biểu đồ đường cong năng lượng (Energy Curve) nằm ngay dưới thanh tua video.
  - *Cột Phải:* Khung Chatbot Q&A đa ngôn ngữ.
- [ ] **Task 3.2:** Phát triển tính năng **"Click-to-Jump"**: Khi người dùng click vào một mốc thời gian ở Cột Trái hoặc trong câu trả lời của Chatbot ở Cột Phải, Video Player tự động nhảy (`seekTo`) đến đúng giây đó.
- [ ] **Task 3.3:** Xây dựng **Cost & Latency Dashboard Component** hiển thị trực quan ở góc dưới màn hình:
  - Thống kê số lượng Token đã tiêu thụ (Input, Output, Cache Read).
  - Quy đổi ra USD thời gian thực.
  - Đo lường Đồ thị Latency/Throughput của từng câu hỏi.

### GIAI ĐOẠN 4: TỐI ƯU HÓA, CHUẨN BỊ DATA DEMO & NỘP BÀI (NGÀY 4)
*Mục tiêu: Hoàn thiện sản phẩm, đóng gói tài liệu để chấm điểm.*

- [ ] **Task 4.1:** Tối ưu hóa Context Caching cho API Seed 2.0 để giảm 75% chi phí và hạ độ trễ phản hồi xuống dưới 3 giây.
- [ ] **Task 4.2:** Chuẩn bị dữ liệu Demo mẫu (Pre-rendered Demo):
  - Video 1 (15 phút): Livestream TikTok Shop Việt Nam (chứa tiếng lóng, code-switching Việt-Anh) để demo tìm SKU và check giá.
  - Video 2 (10 phút): Batch quảng cáo 5-10 biến thể để demo tính năng tìm "Winning Hook Pattern".
- [ ] **Task 4.3:** Thực hiện Record Screencast (Quay màn hình): Thể hiện quá trình demo sản phẩm và luồng hoạt động end-to-end để nộp ban giám khảo.
- [ ] **Task 4.4:** Đóng gói mã nguồn lên GitHub, viết file `README.md` hướng dẫn cài đặt và chạy dự án.

---

## 3. CÁC PROMPTS MẪU ĐỂ ĐIỀU KHIỂN AI CODING AGENT

Bạn có thể dùng các prompt này với AI coding agent (Cursor, Copilot, Claude...) theo đúng tiến độ dự án:

### Prompt 1: Dựng Khung Dự Án (Chạy ở đầu Ngày 1)
```text
Tôi đang làm đề tài Hackathon BX-T4 (Video Intelligence Engine). Hãy tạo cho tôi cấu trúc một dự án Fullstack bao gồm:
1. Thư mục '/backend' sử dụng FastAPI (Python), có sẵn file main.py và các thư mục con cho api, services, models. Cài đặt các thư viện cơ bản: fastapi, uvicorn, pydantic, sqlite3.
2. Thư mục '/frontend' sử dụng React (Vite hoặc Next.js) cài sẵn TailwindCSS và Lucide-react.
Thiết kế giao diện thô dạng Dashboard 3 cột: Cột trái hiển thị danh sách SKU/Timeline, Cột giữa là Trình phát video, Cột phải là Khung chat Q&A. Đảm bảo chạy được lệnh khởi tạo mà không có lỗi.
```

### Prompt 2: Viết Pipeline Xử Lý Video (Chạy ở cuối Ngày 1)
```text
Hãy viết script Python trong backend để xử lý video đầu vào:
1. Sử dụng thư viện 'pyscenedetect' để phát hiện các đoạn chuyển cảnh trong video.
2. Sử dụng 'ffmpeg' thông qua lệnh hệ thống để bóc tách khung hình với mật độ 1 frame/giây và lưu vào thư mục '/storage/thumbnails'.
3. Viết cấu trúc hàm (chừa sẵn chỗ gọi API Seed-2.0-mini-260428) để nhận vào frame + audio segment và trả về dữ liệu metadata dạng JSON chứa: transcript, ocr_text, skus_detected.
```

### Prompt 3: Hoàn thiện Tính năng Click-to-Jump và Dashboard Chi phí (Chạy ở Ngày 3)
```text
Hãy kết nối Frontend React với API backend:
1. Cấu hình Trình phát video sao cho khi người dùng click vào một phần tử có thuộc tính 'timestamp' (ví dụ: 01:23), trình phát sẽ tự động tua đến giây thứ 83.
2. Tạo cấu trúc một Dashboard hiển thị ở góc dưới giao diện để tính toán chi phí API theo thời gian thực dựa trên số lượng token tiêu thụ. Giả định giá: Input Token = $0.15/M, Cache Read = $0.04/M, Output Token = $0.60/M. Vẽ biểu đồ hiển thị độ trễ (latency) bằng Chart.js hoặc Tailwind div bars.
```

---

## 4. CHECKLIST KIỂM TRA BẮT BUỘC TRƯỚC KHI NỘP BÀI (HARD CONSTRAINTS)

- [ ] Sử dụng đúng mã model `Seed-2.0-mini-260428` cho tất cả các tác vụ lập luận đa phương thức.
- [ ] Mọi câu trả lời Q&A từ Chatbot đều phải hiển thị kèm ít nhất 1 Timestamp chính xác và 1 ảnh chụp Thumbnail của khung hình đó làm bằng chứng (Grounded Answer).
- [ ] Có ít nhất một tính năng/workflow chuyên dụng cho việc kiểm tra Compliance (Xác minh Claim lời nói có khớp với Hình ảnh hiển thị hay không).
- [ ] Hệ thống xử lý được ít nhất 2 ngôn ngữ Đông Nam Á (Ưu tiên Tiếng Việt + Tiếng Anh/Thái).
- [ ] Giao diện Demo hiển thị trực tiếp bảng đo Chi phí (Cost) và Độ trễ (Latency).
- [ ] Có sẵn video demo quay lại quá trình hoạt động end-to-end của sản phẩm.
