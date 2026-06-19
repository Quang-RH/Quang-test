# Deploy public (chạy 24/7)

App có backend Python → **không** up tĩnh kiểu Netlify được. Phải deploy lên host chạy Python.
Đã có sẵn `Dockerfile` nên deploy được trên Render / Google Cloud Run / Fly.io.

## ⚠️ Trước khi deploy

- **Tạo API key Gemini MỚI** (key cũ đã từng lộ trong chat) → https://aistudio.google.com/apikey
  → key nhập vào phần *Environment Variables* của host, **không** nằm trong code.

> `.env` đã được `.gitignore` → key **không bao giờ** bị đẩy lên repo/host theo code.
> App KHÔNG còn lớp mật khẩu — ai có URL đều dùng được (theo yêu cầu). Lưu ý: người lạ có link cũng dùng được quota Gemini.

---

## Cách A — Render (khuyến nghị, dễ nhất, có free tier)

Cần: 1 tài khoản GitHub + 1 tài khoản Render (free).

1. Code đã được đẩy lên repo: **https://github.com/Quang-RH/Quang-test** (key không bị đẩy vì đã gitignore).
2. Vào https://render.com → **New** → **Web Service** → kết nối repo `Quang-RH/Quang-test`.
3. Render tự phát hiện `Dockerfile`. Để mặc định (Render tự set `PORT`).
4. Mục **Environment Variables**, thêm:
   | Key | Value |
   |---|---|
   | `GEMINI_API_KEY` | *(key Gemini MỚI — tự tạo)* |
   | `GEMINI_MODEL` | `gemini-2.5-flash` |
   | `FOOTER_TEXT` | *(tùy)* |
5. **Create Web Service** → đợi build → được URL kiểu `https://quang-test.onrender.com`.

> Free tier: dịch vụ "ngủ" sau ~15 phút không dùng → lần mở đầu sau khi ngủ chờ ~30-60s (cold start) rồi chạy bình thường. Hợp với nhu cầu thỉnh thoảng tạo biên bản.

---

## Cách B — Google Cloud Run (không cần GitHub, deploy thẳng từ máy)

Cần: cài `gcloud` CLI + 1 project GCP (bật billing — free tier phủ mức dùng thấp).

```bash
cd C:\QUANG.HO_IT\ai-meeting-notes
gcloud run deploy ai-meeting-notes \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=<KEY_MOI>,GEMINI_MODEL=gemini-2.5-flash
```

`--source .` build thẳng từ thư mục local (không cần đẩy GitHub). Cloud Run **scale về 0** khi không dùng (gần như miễn phí khi rảnh), free tier rộng.

---

## Sau khi deploy

- Mở URL → dùng ngay (không cần đăng nhập).
- Đổi key: sửa Environment Variables trên host rồi redeploy.
- Theo dõi chi phí Gemini ở Google AI Studio.
