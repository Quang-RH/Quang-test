"use strict";

const $ = (id) => document.getElementById(id);
const dropzone = $("dropzone");
const fileInput = $("fileInput");
const fileName = $("fileName");
const btnRun = $("btnRun");
const statusEl = $("status");
const docEl = $("doc");
const actionbar = $("actionbar");

let selectedFile = null;
let lastMarkdown = "";

/* ---------- Chọn file ---------- */
dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

["dragover", "dragenter"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});

function setFile(f) {
  if (!f) return;
  selectedFile = f;
  fileName.textContent = `📎 ${f.name} (${(f.size / 1024 / 1024).toFixed(1)} MB)`;
  btnRun.disabled = false;
  setStatus("", "");
}

function setStatus(msg, cls) {
  statusEl.textContent = msg;
  statusEl.className = "status" + (cls ? " " + cls : "");
}

/* ---------- Gửi xử lý ---------- */
btnRun.addEventListener("click", async () => {
  if (!selectedFile) return;
  btnRun.disabled = true;
  setStatus("⏳ Đang tải file lên và xử lý bằng AI… (có thể mất vài phút với file dài)", "loading");

  const fd = new FormData();
  fd.append("file", selectedFile);
  fd.append("title", $("mTitle").value.trim());
  fd.append("meeting_date", $("mDate").value.trim());
  fd.append("participants", $("mParticipants").value.trim());

  try {
    const res = await fetch("/process", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Lỗi không xác định");
    lastMarkdown = data.markdown;
    renderDoc(data.meeting);
    setStatus("✅ Đã tạo biên bản.", "ok");
    actionbar.hidden = false;
    docEl.hidden = false;
    docEl.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    setStatus("❌ " + err.message, "err");
  } finally {
    btnRun.disabled = false;
  }
});

/* ---------- Render biên bản ---------- */
function esc(s) {
  return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

function renderDoc(m) {
  let html = "";
  html += `<h1 class="doc-title">BIÊN BẢN HỌP: MEETING SUMMARY</h1>`;
  html += `<div class="doc-id">${esc(m.meeting_id)}</div>`;
  html += `<div class="doc-meta">
    <div><strong>Tên cuộc họp:</strong> ${esc(m.title)}</div>
    <div><strong>Ngày họp:</strong> ${esc(m.meeting_date)}</div>
    <div><strong>Đối tượng:</strong> ${esc(m.participants)}</div>
  </div>`;

  html += `<h2 class="sec">1. Tóm tắt cuộc họp (Summary)</h2>`;
  html += `<p>${esc(m.summary)}</p>`;

  html += `<h2 class="sec">2. Các quyết định quan trọng (Key Decisions)</h2>`;
  (m.key_decisions || []).forEach((g) => {
    html += `<h3 class="cat">${esc(g.category)}</h3>`;
    (g.items || []).forEach((it) => {
      html += `<div class="dec-title">${esc(it.title)}</div>`;
      html += `<p class="dec-detail">${esc(it.detail)}</p>`;
    });
  });

  html += `<h2 class="sec">3. Danh sách công việc (Action Items)</h2>`;
  html += `<table><thead><tr>
    <th style="width:24%">Tên công việc</th>
    <th style="width:14%">Người phụ trách</th>
    <th style="width:16%">Trạng thái / Deadline</th>
    <th>Ghi chú từ cuộc họp</th></tr></thead><tbody>`;
  (m.action_items || []).forEach((a) => {
    html += `<tr><td>${esc(a.task)}</td><td>${esc(a.owner)}</td><td>${esc(a.status_deadline)}</td><td>${esc(a.note)}</td></tr>`;
  });
  html += `</tbody></table>`;

  html += `<h2 class="sec">4. Phân công nhân sự (Personnel Assignments)</h2>`;
  html += `<table><thead><tr>
    <th style="width:30%">Thành viên</th>
    <th style="width:22%">Tổ chức</th>
    <th>Vai trò / Nhiệm vụ phụ trách</th></tr></thead><tbody>`;
  (m.personnel || []).forEach((p) => {
    html += `<tr><td>${esc(p.member)}</td><td>${esc(p.organization)}</td><td>${esc(p.role)}</td></tr>`;
  });
  html += `</tbody></table>`;

  html += `<div class="footer-note">Biên bản này được tổng hợp tự động bởi ${esc(m.footer)}.</div>`;

  docEl.innerHTML = html;
}

/* ---------- Hành động ---------- */
$("btnPrint").addEventListener("click", () => window.print());

$("btnCopy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(lastMarkdown);
    setStatus("📋 Đã copy markdown.", "ok");
  } catch {
    setStatus("Không copy được (trình duyệt chặn clipboard).", "err");
  }
});

$("btnDownload").addEventListener("click", () => {
  const blob = new Blob([lastMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "bien-ban-hop.md";
  a.click();
  URL.revokeObjectURL(url);
});
