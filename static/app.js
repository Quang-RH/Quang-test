"use strict";

const $ = (id) => document.getElementById(id);

function esc(s) {
  return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

/* ===================== TAB SWITCHING ===================== */
document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    const tab = t.dataset.tab;
    $("tab-meeting").hidden = tab !== "meeting";
    $("tab-review").hidden = tab !== "review";
  })
);

/* shared: gắn kéo-thả cho 1 dropzone */
function wireDropzone(zone, input, onFile) {
  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => onFile(input.files[0]));
  ["dragover", "dragenter"].forEach((ev) =>
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
    })
  );
  zone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) onFile(e.dataTransfer.files[0]);
  });
}

function setStatus(el, msg, cls) {
  el.textContent = msg;
  el.className = "status" + (cls ? " " + cls : "");
}

/* ===================== TAB 1: BIÊN BẢN HỌP ===================== */
let meetingFile = null;
let meetingMarkdown = "";

wireDropzone($("dropzone"), $("fileInput"), (f) => {
  if (!f) return;
  meetingFile = f;
  $("fileName").textContent = `📎 ${f.name} (${(f.size / 1024 / 1024).toFixed(1)} MB)`;
  $("btnRun").disabled = false;
  setStatus($("status"), "", "");
});

$("btnRun").addEventListener("click", async () => {
  if (!meetingFile) return;
  $("btnRun").disabled = true;
  setStatus($("status"), "⏳ Đang tải file lên và xử lý bằng AI… (file dài có thể vài phút)", "loading");

  const fd = new FormData();
  fd.append("file", meetingFile);
  fd.append("title", $("mTitle").value.trim());
  fd.append("meeting_date", $("mDate").value.trim());

  try {
    const res = await fetch("/process", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Lỗi không xác định");
    meetingMarkdown = data.markdown;
    renderMeeting(data.meeting);
    setStatus($("status"), "✅ Đã tạo biên bản.", "ok");
    $("actionbar").hidden = false;
    $("doc").hidden = false;
    $("doc").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    setStatus($("status"), "❌ " + err.message, "err");
  } finally {
    $("btnRun").disabled = false;
  }
});

function renderMeeting(m) {
  let html = "";
  html += `<h1 class="doc-title">BIÊN BẢN HỌP: MEETING SUMMARY</h1>`;
  html += `<div class="doc-id">${esc(m.meeting_id)}</div>`;
  html += `<div class="doc-meta">
    <div><strong>Tên cuộc họp:</strong> ${esc(m.title)}</div>
    <div><strong>Ngày họp:</strong> ${esc(m.meeting_date)}</div>
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
    <th style="width:34%">Tên công việc</th>
    <th style="width:20%">Trạng thái / Deadline</th>
    <th>Ghi chú từ cuộc họp</th></tr></thead><tbody>`;
  (m.action_items || []).forEach((a) => {
    html += `<tr><td>${esc(a.task)}</td><td>${esc(a.status_deadline)}</td><td>${esc(a.note)}</td></tr>`;
  });
  html += `</tbody></table>`;
  html += `<div class="footer-note">Biên bản này được tổng hợp tự động bởi ${esc(m.footer)}.</div>`;
  $("doc").innerHTML = html;
}

$("btnPrint").addEventListener("click", () => window.print());
$("btnCopy").addEventListener("click", () => copyText(meetingMarkdown, $("status")));
$("btnDownload").addEventListener("click", () => downloadText(meetingMarkdown, "bien-ban-hop.md"));

/* ===================== TAB 2: REVIEW TÀI LIỆU ===================== */
let reviewFile = null;
let lastReview = null; // { filename, text, review }

wireDropzone($("rDropzone"), $("rFileInput"), (f) => {
  if (!f) return;
  reviewFile = f;
  $("rFileName").textContent = `📎 ${f.name} (${(f.size / 1024 / 1024).toFixed(1)} MB)`;
  $("rBtnRun").disabled = false;
  setStatus($("rStatus"), "", "");
});

$("rBtnRun").addEventListener("click", async () => {
  if (!reviewFile) return;
  $("rBtnRun").disabled = true;
  setStatus($("rStatus"), "⏳ Đang đọc tài liệu và review bằng AI…", "loading");

  const fd = new FormData();
  fd.append("file", reviewFile);

  try {
    const res = await fetch("/review-doc", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Lỗi không xác định");
    lastReview = data;
    renderReview(data);
    setStatus($("rStatus"), "✅ Đã review xong.", "ok");
    $("reviewResult").hidden = false;
    $("reviewResult").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    setStatus($("rStatus"), "❌ " + err.message, "err");
  } finally {
    $("rBtnRun").disabled = false;
  }
});

function sevClass(s) {
  return s === "cao" ? "sev-high" : s === "vừa" ? "sev-mid" : "sev-low";
}

function scoreClass(s) {
  return s === "Đạt" ? "sc-ok" : s === "Một phần" ? "sc-mid" : "sc-bad";
}

/* tìm vị trí quote chưa bị range nào chiếm */
function findQuoteIndex(text, quote, ranges) {
  let from = 0;
  while (from <= text.length) {
    const idx = text.indexOf(quote, from);
    if (idx < 0) return -1;
    const end = idx + quote.length;
    const overlap = ranges.some((r) => idx < r.end && end > r.start);
    if (!overlap) return idx;
    from = idx + 1;
  }
  return -1;
}

function renderReview(data) {
  const r = data.review;
  const text = data.text || "";
  const findings = r.findings || [];

  // 1) thanh tổng quan + scorecard
  let scHtml = "";
  if (r.scorecard && r.scorecard.length) {
    scHtml =
      `<table class="scorecard"><tbody>` +
      r.scorecard
        .map(
          (d) =>
            `<tr><td class="sc-dim">${esc(d.dimension)}</td>` +
            `<td><span class="sc ${scoreClass(d.score)}">${esc(d.score)}</span></td>` +
            `<td class="sc-note">${esc(d.note)}</td></tr>`
        )
        .join("") +
      `</tbody></table>`;
  }
  $("overallBar").innerHTML =
    `<div class="rating">Xếp loại: ${esc(r.rating)}</div>` +
    `<div class="overall-text"><strong>${esc(r.doc_type)}</strong> — ${esc(r.overall)}</div>` +
    scHtml;

  // 2) định vị highlight trong text
  const ranges = [];
  findings.forEach((f, i) => {
    const q = (f.quote || "").trim();
    if (!q) { f._located = false; return; }
    const idx = findQuoteIndex(text, q, ranges);
    if (idx >= 0) {
      ranges.push({ start: idx, end: idx + q.length, id: i, sev: f.severity });
      f._located = true;
    } else {
      f._located = false;
    }
  });
  ranges.sort((a, b) => a.start - b.start);

  let docHtml = "", cur = 0;
  for (const rg of ranges) {
    docHtml += esc(text.slice(cur, rg.start));
    docHtml += `<mark class="hl ${sevClass(rg.sev)}" data-id="${rg.id}" id="hl-${rg.id}">${esc(
      text.slice(rg.start, rg.end)
    )}</mark>`;
    cur = rg.end;
  }
  docHtml += esc(text.slice(cur));
  $("docPane").innerHTML = docHtml || "<em>(không có nội dung)</em>";

  // 3) thẻ phát hiện
  let findHtml = `<div class="find-count">${findings.length} phát hiện</div>`;
  findings.forEach((f, i) => {
    findHtml += `<div class="finding" data-id="${i}" id="card-${i}">
      <div class="f-head">
        <span class="f-num">#${i + 1}</span>
        <span class="dot ${sevClass(f.severity)}"></span>
        <span class="badge">${esc(f.type)}</span>
        <span class="badge">${esc(f.severity)}</span>
      </div>
      ${f.quote ? `<div class="quote">${esc(f.quote)}</div>` : ""}
      <div class="f-issue"><strong>Vì sao:</strong> ${esc(f.why)}</div>
      <div class="f-fix"><strong>Sửa:</strong> ${esc(f.suggestion)}</div>
      ${f._located ? "" : `<div class="nolocate">⚠ Không định vị được trong text</div>`}
    </div>`;
  });
  $("findPane").innerHTML = findHtml;
}

/* link 2 chiều: bấm highlight ↔ thẻ */
function flash(el) {
  if (!el) return;
  el.classList.add("flash");
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  setTimeout(() => el.classList.remove("flash"), 1500);
}
$("docPane").addEventListener("click", (e) => {
  const m = e.target.closest("mark.hl");
  if (m) flash($("card-" + m.dataset.id));
});
$("findPane").addEventListener("click", (e) => {
  const c = e.target.closest(".finding");
  if (c) flash($("hl-" + c.dataset.id));
});

/* xuất ra trang HTML riêng để in */
$("rBtnPrint").addEventListener("click", () => {
  if (!lastReview) return;
  const w = window.open("", "_blank");
  w.document.write(buildPrintable(lastReview));
  w.document.close();
});
$("rBtnCopy").addEventListener("click", () => copyText(reviewToMarkdown(lastReview), $("rStatus")));

function buildPrintable(data) {
  const r = data.review;
  const scRows = (r.scorecard || [])
    .map((d) => `<tr><td>${esc(d.dimension)}</td><td>${esc(d.score)}</td><td>${esc(d.note)}</td></tr>`)
    .join("");
  const scTable = scRows
    ? `<table class="sc"><thead><tr><th>Tiêu chí</th><th>Đánh giá</th><th>Nhận xét</th></tr></thead><tbody>${scRows}</tbody></table>`
    : "";
  const items = (r.findings || [])
    .map(
      (x, i) => `<div class="pf">
      <div class="pf-h">${i + 1}. [${esc(x.type)} · ${esc(x.severity)}]</div>
      ${x.quote ? `<blockquote>${esc(x.quote)}</blockquote>` : ""}
      <div><b>Vì sao:</b> ${esc(x.why)}</div>
      <div><b>Đề xuất sửa:</b> ${esc(x.suggestion)}</div>
    </div>`
    )
    .join("");
  return `<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
  <title>Review - ${esc(data.filename)}</title>
  <style>
    body{font-family:Segoe UI,Arial,sans-serif;max-width:800px;margin:24px auto;padding:0 16px;line-height:1.6;color:#1a1a1a}
    h1{color:#1f5fa8;font-size:24px} h2{font-size:18px;margin-top:24px}
    .rating{font-weight:700} blockquote{border-left:3px solid #ddd;margin:6px 0;padding:4px 10px;color:#444;background:#fafafa}
    .pf{margin:14px 0;padding-bottom:10px;border-bottom:1px solid #eee} .pf-h{font-weight:700;color:#1f5fa8}
    table.sc{border-collapse:collapse;width:100%;margin:8px 0;font-size:14px}
    table.sc th,table.sc td{border:1px solid #ddd;padding:6px 10px;text-align:left}
    table.sc th{background:#f0f2f5}
  </style></head><body>
  <h1>Báo cáo Review tài liệu</h1>
  <p><b>Tài liệu:</b> ${esc(data.filename)} &nbsp;·&nbsp; <b>Loại:</b> ${esc(r.doc_type)}</p>
  <p class="rating">Xếp loại: ${esc(r.rating)}</p>
  <h2>Đánh giá tổng quan</h2>
  <p>${esc(r.overall)}</p>
  ${scTable ? `<h2>Bảng điểm</h2>${scTable}` : ""}
  <h2>Phát hiện &amp; đề xuất sửa (${(r.findings || []).length})</h2>
  ${items}
  </body></html>`;
}

function reviewToMarkdown(data) {
  const r = data.review;
  let md = `# Review tài liệu: ${data.filename}\n\n`;
  md += `**Loại:** ${r.doc_type}  \n**Xếp loại:** ${r.rating}\n\n`;
  md += `## Đánh giá tổng quan\n\n${r.overall}\n\n`;
  if (r.scorecard && r.scorecard.length) {
    md += `## Bảng điểm\n\n| Tiêu chí | Đánh giá | Nhận xét |\n|---|---|---|\n`;
    r.scorecard.forEach((d) => {
      md += `| ${d.dimension} | ${d.score} | ${(d.note || "").replace(/\n/g, " ")} |\n`;
    });
    md += `\n`;
  }
  md += `## Phát hiện & đề xuất sửa\n\n`;
  (r.findings || []).forEach((x, i) => {
    md += `${i + 1}. **[${x.type} · ${x.severity}]**\n`;
    if (x.quote) md += `   > ${x.quote.replace(/\n/g, " ")}\n`;
    md += `   - Vì sao: ${x.why}\n   - Sửa: ${x.suggestion}\n\n`;
  });
  return md;
}

/* ===================== tiện ích chung ===================== */
async function copyText(text, statusEl) {
  try {
    await navigator.clipboard.writeText(text || "");
    setStatus(statusEl, "📋 Đã copy.", "ok");
  } catch {
    setStatus(statusEl, "Không copy được (trình duyệt chặn clipboard).", "err");
  }
}
function downloadText(text, filename) {
  const blob = new Blob([text || ""], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
