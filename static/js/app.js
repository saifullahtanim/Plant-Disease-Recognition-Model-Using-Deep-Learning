(function () {
  function $(id) {
    return document.getElementById(id);
  }

  function setAlert(message, type) {
    const el = $("uiAlert");
    if (!el) return;
    if (!message) {
      el.classList.add("d-none");
      el.textContent = "";
      return;
    }

    const t = type || "info";
    el.className = "alert alert-" + t;
    el.textContent = String(message);
    el.classList.remove("d-none");
  }

  const STORAGE_KEY = "phasel.analysisHistory.v1";
  const HISTORY_MAX = 20;

  function loadHistory() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory(items) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      // ignore
    }
  }

  function upsertHistoryItem(item) {
    const items = loadHistory();
    const filtered = items.filter(function (x) {
      return x && x.imageUrl !== item.imageUrl;
    });
    filtered.unshift(item);
    saveHistory(filtered.slice(0, HISTORY_MAX));
  }

  function formatTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch (e) {
      return iso;
    }
  }

  async function loadServerHistory() {
    try {
      const res = await fetch("/api/history", {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) return null;
      const data = await res.json();
      return Array.isArray(data) ? data : null;
    } catch (e) {
      return null;
    }
  }

  async function deleteServerHistoryItem(id) {
    try {
      const res = await fetch("/api/history/" + String(id), {
        method: "DELETE",
      });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  async function renderHistory() {
    const historyEmpty = $("historyEmpty");
    const historyList = $("historyList");
    const historyLoading = $("historyLoading");
    const historySource = $("historySource");
    if (!historyEmpty || !historyList) return;

    if (historyLoading) historyLoading.classList.remove("d-none");

    const serverItems = await loadServerHistory();
    const items = serverItems || loadHistory();

    if (historyLoading) historyLoading.classList.add("d-none");
    if (historySource) {
      historySource.textContent = serverItems ? "Saved on server" : "Saved on this browser";
    }

    if (!items.length) {
      historyEmpty.classList.remove("d-none");
      historyList.classList.add("d-none");
      historyList.innerHTML = "";
      return;
    }

    historyEmpty.classList.add("d-none");
    historyList.classList.remove("d-none");

    historyList.innerHTML = items
      .map(function (x) {
        const isServer = x && typeof x.id === "number";
        const title = isServer
          ? String(x.prediction_name || "(Unknown)")
          : x && x.title
            ? String(x.title)
            : "(Unknown)";
        const time = isServer
          ? formatTime(String(x.created_at || ""))
          : x && x.createdAt
            ? formatTime(String(x.createdAt))
            : "";
        const img = isServer
          ? String(x.image_url || "")
          : x && x.imageUrl
            ? String(x.imageUrl)
            : "";
        const dataUrl = img ? img.replace(/"/g, "&quot;") : "";
        const dataId = isServer ? String(x.id) : "";
        const conf = isServer && typeof x.confidence === "number" ? (x.confidence * 100).toFixed(1) + "%" : "";

        const openUrl = isServer && dataId ? "/report/" + dataId : img;

        const ariaOpen = isServer
          ? "Open report for " + title
          : "Open image";

        return (
          '<div class="list-group-item bg-transparent history-item" role="button" tabindex="0" data-open-url="' +
          (openUrl ? String(openUrl).replace(/"/g, "&quot;") : "") +
          '" aria-label="' +
          String(ariaOpen).replace(/"/g, "&quot;") +
          '">' +
          '<div class="history-thumb">' +
          (img ? '<img src="' + img + '" alt="" loading="lazy">' : "") +
          "</div>" +
          '<div class="history-meta">' +
          '<p class="history-title text-truncate">' +
          title +
          "</p>" +
          '<p class="history-sub">' +
          time +
          (conf ? " • " + conf : "") +
          "</p>" +
          "</div>" +
          '<div class="history-actions">' +
          '<button type="button" class="btn btn-outline-danger btn-sm history-delete" aria-label="Delete from history" data-id="' +
          dataId +
          '" data-image-url="' +
          dataUrl +
          '">Delete</button>' +
          "</div>" +
          "</div>"
        );
      })
      .join("");
  }

  const fileInput = $("img");
  const previewImg = $("previewImg");
  const previewPlaceholder = $("previewPlaceholder");
  const qualityHint = $("qualityHint");
  const uploadForm = $("uploadForm");
  const submitBtn = $("submitBtn");
  const resultName = $("resultName");
  const resultImage = $("resultImage");
  const historyBtn = $("historyBtn");

  function setFile(file) {
    if (!fileInput) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fileInput.dispatchEvent(new Event("change"));
  }

  if (fileInput && previewImg && previewPlaceholder) {
    fileInput.addEventListener("change", function () {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        previewImg.classList.add("d-none");
        previewPlaceholder.classList.remove("d-none");
        previewImg.removeAttribute("src");
        if (qualityHint) qualityHint.textContent = "";
        return;
      }

      const url = URL.createObjectURL(file);
      previewImg.src = url;
      previewImg.classList.remove("d-none");
      previewPlaceholder.classList.add("d-none");

      previewImg.onload = function () {
        URL.revokeObjectURL(url);

        if (qualityHint) {
          const w = previewImg.naturalWidth || 0;
          const h = previewImg.naturalHeight || 0;
          const mp = (w * h) / 1_000_000;
          const sizeMb = file.size / (1024 * 1024);
          const warnings = [];
          if (w && h && (w < 200 || h < 200)) warnings.push("low resolution");
          if (mp && mp > 18) warnings.push("very large image");
          if (sizeMb > 5) warnings.push("large file");
          qualityHint.textContent = warnings.length ? "Note: " + warnings.join(", ") : "";
        }
      };
    });
  }

  // Drag & drop anywhere
  document.addEventListener("dragover", function (e) {
    e.preventDefault();
  });
  document.addEventListener("drop", function (e) {
    e.preventDefault();
    const files = e.dataTransfer && e.dataTransfer.files;
    if (!files || !files.length) return;
    const file = files[0];
    if (!file.type || !file.type.startsWith("image/")) return;
    setFile(file);
  });

  // Paste image
  document.addEventListener("paste", function (e) {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (it.type && it.type.startsWith("image/")) {
        const file = it.getAsFile();
        if (file) setFile(file);
        break;
      }
    }
  });

  if (uploadForm && submitBtn) {
    uploadForm.addEventListener("submit", function () {
      submitBtn.disabled = true;
      const spinner = submitBtn.querySelector(".btn-spinner");
      const label = submitBtn.querySelector(".btn-label");
      if (spinner) spinner.classList.remove("d-none");
      if (label) label.textContent = "Analyzing...";
    });
  }

  // Local fallback history (server history is the main source).
  if (resultName && resultImage && resultImage.getAttribute("src")) {
    upsertHistoryItem({
      title: resultName.textContent.trim(),
      imageUrl: resultImage.getAttribute("src"),
      createdAt: new Date().toISOString(),
    });
  }

  renderHistory();
  if (historyBtn) {
    historyBtn.addEventListener("click", function () {
      renderHistory();
    });
  }

  const historyList = $("historyList");
  if (historyList) {
    historyList.addEventListener("click", function (e) {
      const btn =
        e.target && e.target.closest
          ? e.target.closest(".history-delete")
          : null;
      if (btn) {
        const id = btn.getAttribute("data-id");
        const url = btn.getAttribute("data-image-url") || "";

        if (id) {
          deleteServerHistoryItem(id).then(function (ok) {
            setAlert(ok ? "Deleted from history." : "Could not delete. Please try again.", ok ? "success" : "danger");
            renderHistory();
          });
        } else {
          const items = loadHistory().filter(function (x) {
            return x && x.imageUrl !== url;
          });
          saveHistory(items);
          setAlert("Deleted from history.", "success");
          renderHistory();
        }

        e.preventDefault();
        e.stopPropagation();
        return;
      }

      const row =
        e.target && e.target.closest ? e.target.closest(".history-item") : null;
      if (!row) return;
      const openUrl = row.getAttribute("data-open-url") || "";
      if (!openUrl) return;

      window.open(openUrl, "_blank", "noopener");
      e.preventDefault();
    });

    historyList.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" && e.key !== " ") return;

      const onDelete =
        e.target && e.target.closest ? e.target.closest(".history-delete") : null;
      if (onDelete) return;

      const row =
        e.target && e.target.closest ? e.target.closest(".history-item") : null;
      if (!row) return;
      const openUrl = row.getAttribute("data-open-url") || "";
      if (!openUrl) return;
      window.open(openUrl, "_blank", "noopener");
      e.preventDefault();
      e.stopPropagation();
    });
  }
})();
