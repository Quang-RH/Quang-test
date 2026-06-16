# Deploy public (chạy 24/7)

App có backend Python → **không** up tĩnh kiểu Netlify được. Phải deploy lên host chạy Python.
Đã có sẵn `Dockerfile` nên deploy được trên Render / Google Cloud Run / Fly.io.

## ⚠️ Trước khi deploy — 2 việc bắt buộc

1. **Tạo API key Gemini MỚI** (key cũ đã từng lộ trong chat) → https://aistudio.google.com/apikey
   → key sẽ nhập vào phần *Environment Variables* của host, **không** nằm trong code.
2. **Đặt `APP_PASSWORD`** (một mật khẩu bất kỳ) khi deploy → trang sẽ hỏi mật khẩu, chặn người lạ đốt quota.

> `.env` đã được `.gitignore` → key **không bao giờ** bị đẩy lên repo/host theo code.

---

## Cách A — Render (khuyến nghị, dễ nhất, có free tier)

Cần: 1 tài khoản GitHub + 1 tài khoản Render (free).

1. **Đẩy code lên GitHub repo PRIVATE** (key không bị đẩy vì đã gitignore):
   ```bash
   cd C:\QUANG.HO_IT\ai-meeting-notes
   gh repo create ai-meeting-notes --private --source . --push
   # hoặc tạo repo private trên github.com rồi: git remote add origin <url> && git push -u origin main
   ```
2. Vào https://render.com → **New** → **Web Service** → kết nối GitHub repo vừa tạo.
3. Render tự phát hiện `Dockerfile`. Để mặc định (Render tự set `PORT`).
4. Mục **Environment Variables**, thêm:
   | Key | Value |
   |---|---|
   | `GEMINI_API_KEY` | *(key Gemini mới)* |
   | `GEMINI_MODEL` | `gemini-2.5-flash` |
   | `APP_PASSWORD` | *(mật khẩu bạn chọn)* |
   | `FOOTER_TEXT` | *(tùy)* |
5. **Create Web Service** → đợi build → được URL kiểu `https://ai-meeting-notes.onrender.com`.

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
  --set-env-vars GEMINI_API_KEY=<KEY_MOI>,GEMINI_MODEL=gemini-2.5-flash,APP_PASSWORD=<MAT_KHAU>
```

`--source .` build thẳng từ thư mục local (không cần đẩy GitHub). Cloud Run **scale về 0** khi không dùng (gần như miễn phí khi rảnh), free tier rộng.

---

## Sau khi deploy

- Mở URL → trình duyệt hỏi mật khẩu (`APP_PASSWORD`) → đăng nhập → dùng như local.
- Đổi mật khẩu / key: sửa Environment Variables trên host rồi redeploy.
- Theo dõi chi phí Gemini ở Google AI Studio.
