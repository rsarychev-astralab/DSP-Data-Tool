(() => {
  const queryInput = document.getElementById("fl-address-query");
  const checkBtn = document.getElementById("fl-address-check-btn");
  const statusEl = document.getElementById("fl-address-status");
  const resultEl = document.getElementById("fl-address-result");

  if (!queryInput || !checkBtn) return;

  const setStatus = (text, kind) => {
    if (!text) {
      statusEl.className = "d-none";
      statusEl.textContent = "";
      return;
    }
    const cls =
      kind === "error"
        ? "alert-danger"
        : kind === "warn"
          ? "alert-warning"
          : kind === "ok"
            ? "alert-success"
            : "alert-info";
    statusEl.className = `alert py-2 mb-0 ${cls}`;
    statusEl.textContent = text;
  };

  const escapeHtml = (value) =>
    String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  const extractInn = (text) => {
    const digits = (text || "").replace(/\D/g, "");
    if (digits.length === 10 || digits.length === 12) return digits;
    return null;
  };

  const fieldRow = (label, value, extraClass = "") => {
    const display = value == null || value === "" ? "—" : value;
    return (
      `<dt class="col-12 col-md-4">${escapeHtml(label)}</dt>` +
      `<dd class="col-12 col-md-8 ${extraClass}">${escapeHtml(display)}</dd>`
    );
  };

  const renderResult = (data) => {
    resultEl.classList.remove("d-none");
    resultEl.innerHTML = `
      <div class="info-title">
        <span class="dadata-result-name">Предлагаемый адрес</span>
        <button type="button" class="btn btn-outline-secondary btn-sm" id="fl-address-copy-btn">
          Копировать адрес
        </button>
      </div>
      <p class="fl-address-value mb-3">${escapeHtml(data.address)}</p>
      <dl class="row mb-2 small g-1">
        ${fieldRow("ИНН", data.inn, "font-monospace")}
        ${fieldRow("Код региона", data.region_code, "font-monospace")}
        ${fieldRow("Субъект РФ", data.region)}
      </dl>
      <p class="text-muted small mb-0">${escapeHtml(data.note)} Если это ИП — точный адрес во вкладке DaData.</p>
    `;

    const copyBtn = document.getElementById("fl-address-copy-btn");
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(data.address);
        copyBtn.textContent = "Скопировано";
        setTimeout(() => {
          copyBtn.textContent = "Копировать адрес";
        }, 1500);
      } catch {
        setStatus("Не удалось скопировать адрес", "error");
      }
    });
  };

  const apiErrorMessage = (payload, status) => {
    const detail = payload?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
    }
    return `Ошибка обработки (${status})`;
  };

  async function lookup(inn) {
    const response = await fetch(
      `/api/fl-address/lookup?inn=${encodeURIComponent(inn)}`
    );
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiErrorMessage(payload, response.status));
    }
    return payload;
  }

  async function onCheck() {
    const raw = queryInput.value.trim();
    if (!raw) {
      setStatus("Введите ИНН физлица (12 цифр)", "error");
      return;
    }

    const inn = extractInn(raw);
    if (!inn) {
      setStatus("Нужен ИНН из 12 цифр", "error");
      return;
    }
    if (inn.length === 10) {
      setStatus(
        "ИНН из 10 цифр — это юрлицо. Проверьте во вкладке «Проверка юридических лиц».",
        "error"
      );
      resultEl.classList.add("d-none");
      return;
    }

    checkBtn.disabled = true;
    setStatus("Проверяем…", "info");
    resultEl.classList.add("d-none");

    try {
      const data = await lookup(inn);
      renderResult(data);
      setStatus("Регион определён", "ok");
    } catch (error) {
      setStatus(error.message || "Ошибка запроса", "error");
    } finally {
      checkBtn.disabled = false;
    }
  }

  checkBtn.addEventListener("click", onCheck);
  queryInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      onCheck();
    }
  });

  const batchFile = document.getElementById("fl-address-file");
  const batchBtn = document.getElementById("fl-address-batch-btn");
  const batchStatus = document.getElementById("fl-address-batch-status");
  const dropZone = document.getElementById("fl-address-drop-zone");
  const dropPlaceholder = document.getElementById("fl-address-drop-placeholder");
  const dropSelected = document.getElementById("fl-address-drop-selected");
  const fileNameEl = document.getElementById("fl-address-file-name");
  const fileSizeEl = document.getElementById("fl-address-file-size");
  const fileRemoveBtn = document.getElementById("fl-address-file-remove");
  const outputFormat = document.getElementById("fl-address-output-format");
  const progressWrap = document.getElementById("fl-address-batch-progress-wrap");
  const progressLabel = document.getElementById("fl-address-batch-progress-label");
  const progressPct = document.getElementById("fl-address-batch-progress-pct");
  const progressBar = document.getElementById("fl-address-batch-progress-bar");

  if (!batchFile || !batchBtn || !dropZone) return;

  let pollTimer = null;

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + " Б";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " КБ";
    return (bytes / (1024 * 1024)).toFixed(1) + " МБ";
  };

  const setBatchStatus = (text, kind, extraHtml = "") => {
    if (!text) {
      batchStatus.className = "d-none";
      batchStatus.textContent = "";
      return;
    }
    const cls =
      kind === "error"
        ? "alert-danger"
        : kind === "warn"
          ? "alert-warning"
          : kind === "ok"
            ? "alert-success"
            : "alert-info";
    batchStatus.className = `alert py-2 mb-0 ${cls}`;
    batchStatus.innerHTML = extraHtml
      ? `${escapeHtml(text)}${extraHtml}`
      : escapeHtml(text);
  };

  const problemsHtml = (payload) => {
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (!items.length) return "";
    const total = Number(payload.total) || items.length;
    const rows = items
      .map((item) => {
        const inn = item.inn
          ? `, ИНН <span class="font-monospace">${escapeHtml(item.inn)}</span>`
          : "";
        return `<li>строка ${escapeHtml(String(item.row))}${inn}: ${escapeHtml(item.error || "")}</li>`;
      })
      .join("");
    const more =
      total > items.length
        ? `<li class="text-muted">и ещё ${total - items.length}</li>`
        : "";
    return (
      `<p class="small fw-semibold mt-2 mb-1">Проблемы (${total}):</p>` +
      `<ul class="validation-list mb-0 ps-3">${rows}${more}</ul>`
    );
  };

  const setProgress = (processed, total) => {
    const safeTotal = total || 0;
    const percent = safeTotal ? Math.round((processed / safeTotal) * 100) : 0;
    progressWrap.classList.remove("d-none");
    progressLabel.textContent = "Проверяем адреса…";
    progressBar.classList.remove("progress-bar-animated");
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute("aria-valuenow", String(percent));
    progressPct.textContent = `${processed} / ${safeTotal} (${percent}%)`;
  };

  const hideProgress = () => {
    progressWrap.classList.add("d-none");
    progressBar.style.width = "0%";
    progressBar.setAttribute("aria-valuenow", "0");
    progressPct.textContent = "";
  };

  const updateBatchFileUI = () => {
    const file = batchFile.files[0];
    if (file) {
      dropZone.classList.add("has-file");
      dropPlaceholder.classList.add("d-none");
      dropSelected.classList.remove("d-none");
      fileNameEl.textContent = file.name;
      fileSizeEl.textContent = formatSize(file.size);
      batchBtn.disabled = false;
    } else {
      dropZone.classList.remove("has-file");
      dropPlaceholder.classList.remove("d-none");
      dropSelected.classList.add("d-none");
      batchBtn.disabled = true;
    }
  };

  const resultFilename = (format) => {
    const value = (format || "xlsx").toLowerCase();
    if (value === "xlsx") return "fl_address_result.xlsx";
    if (value === "xls") return "fl_address_result.xls";
    return "fl_address_result.csv";
  };

  async function downloadJobResult(jobId, fallbackFormat) {
    const response = await fetch(`/api/fl-address/batch/${jobId}/download`);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(apiErrorMessage(payload, response.status));
    }

    const blob = await response.blob();
    const format = response.headers.get("X-Output-Format") || fallbackFormat;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = resultFilename(format);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  const stopPolling = () => {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  };

  const finishOk = async (jobId, payload, fallbackFormat) => {
    stopPolling();
    await downloadJobResult(jobId, fallbackFormat);
    hideProgress();
    const extras = [];
    if (payload.errors) extras.push(`ошибок: ${payload.errors}`);
    if (payload.empty) extras.push(`пустых ИНН: ${payload.empty}`);
    const suffix = extras.length ? ` (${extras.join(", ")})` : "";
    setBatchStatus(
      `Готово: адрес записан для ${payload.filled || 0} из ${payload.total || 0}. Файл скачан.${suffix}`,
      payload.errors ? "warn" : "ok",
      problemsHtml(payload.problems)
    );
    updateBatchFileUI();
  };

  async function pollJob(jobId, totalHint, fallbackFormat) {
    const response = await fetch(`/api/fl-address/batch/${jobId}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiErrorMessage(payload, response.status));
    }

    setProgress(payload.processed || 0, payload.total || totalHint || 0);

    if (payload.status === "completed") {
      await finishOk(jobId, payload, fallbackFormat);
      return;
    }

    if (payload.status === "failed") {
      stopPolling();
      throw new Error(payload.error || "Задача завершилась с ошибкой");
    }

    setBatchStatus("Проверяем адреса…", "info");
    pollTimer = setTimeout(() => {
      pollJob(jobId, totalHint, fallbackFormat).catch((error) => {
        stopPolling();
        hideProgress();
        setBatchStatus(error.message || "Ошибка массовой проверки", "error");
        updateBatchFileUI();
      });
    }, 500);
  }

  const clearBatchFile = () => {
    stopPolling();
    batchFile.value = "";
    updateBatchFileUI();
    hideProgress();
    setBatchStatus("", "");
  };

  dropZone.addEventListener("click", (e) => {
    if (e.target.closest("#fl-address-file-remove")) return;
    batchFile.click();
  });
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      batchFile.click();
    }
  });
  fileRemoveBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    clearBatchFile();
  });
  batchFile.addEventListener("change", () => {
    updateBatchFileUI();
    hideProgress();
    setBatchStatus("", "");
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragover");
    });
  });
  dropZone.addEventListener("drop", (event) => {
    const files = event.dataTransfer?.files;
    if (!files?.length) return;
    const file = files[0];
    if (!/\.(xlsx|xlsm|xls|csv|txt|tsv)$/i.test(file.name)) {
      setBatchStatus("Нужен файл .xlsx, .xls, .csv, .txt или .tsv", "error");
      return;
    }
    const dt = new DataTransfer();
    dt.items.add(file);
    batchFile.files = dt.files;
    updateBatchFileUI();
    hideProgress();
    setBatchStatus("", "");
  });

  batchBtn.addEventListener("click", async () => {
    const file = batchFile.files?.[0];
    if (!file) {
      setBatchStatus("Выберите файл с колонкой ИНН", "error");
      return;
    }

    stopPolling();
    batchBtn.disabled = true;
    hideProgress();
    setBatchStatus("Загружаем файл и запускаем проверку…", "info");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("output_format", outputFormat?.value || "auto");

    try {
      const response = await fetch("/api/fl-address/batch", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(apiErrorMessage(payload, response.status));
      }

      setProgress(payload.processed || 0, payload.total || 0);
      setBatchStatus("Проверяем адреса…", "info");
      if (payload.status === "completed") {
        await finishOk(payload.job_id, payload, outputFormat?.value || "auto");
        return;
      }
      await pollJob(payload.job_id, payload.total, outputFormat?.value || "auto");
    } catch (error) {
      stopPolling();
      hideProgress();
      setBatchStatus(error.message || "Ошибка массовой проверки", "error");
      updateBatchFileUI();
    }
  });
})();
