(() => {
  const queryInput = document.getElementById("dadata-query");
  const suggestionsEl = document.getElementById("dadata-suggestions");
  const checkBtn = document.getElementById("dadata-check-btn");
  const statusEl = document.getElementById("dadata-status");
  const resultEl = document.getElementById("dadata-result");
  const configInfo = document.getElementById("dadata-config-info");

  if (!queryInput || !checkBtn) return;

  let debounceTimer = null;
  let activeIndex = -1;
  let currentSuggestions = [];
  let abortController = null;
  let dadataReady = false;

  const STATUS_MAP = {
    ACTIVE: { label: "Действующая", cls: "text-bg-success" },
    LIQUIDATING: { label: "Ликвидируется", cls: "text-bg-warning" },
    LIQUIDATED: { label: "Ликвидирована", cls: "text-bg-danger" },
    BANKRUPT: { label: "Банкротство", cls: "text-bg-danger" },
    REORGANIZING: { label: "Реорганизация", cls: "text-bg-warning" },
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + " Б";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " КБ";
    return (bytes / (1024 * 1024)).toFixed(1) + " МБ";
  };

  const setAlert = (el, text, kind) => {
    if (!text) {
      el.className = "d-none";
      el.textContent = "";
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
    el.className = `alert py-2 mb-0 ${cls}`;
    el.textContent = text;
  };

  const setStatus = (text, kind) => setAlert(statusEl, text, kind);

  const extractInn = (text) => {
    const digits = (text || "").replace(/\D/g, "");
    if (digits.length === 10 || digits.length === 12) return digits;
    return null;
  };

  const hideSuggestions = () => {
    suggestionsEl.hidden = true;
    suggestionsEl.classList.remove("show");
    suggestionsEl.innerHTML = "";
    queryInput.setAttribute("aria-expanded", "false");
    activeIndex = -1;
  };

  const escapeHtml = (value) =>
    String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  const renderSuggestions = (items) => {
    currentSuggestions = items;
    activeIndex = -1;

    if (!items.length) {
      hideSuggestions();
      return;
    }

    suggestionsEl.innerHTML = "";
    items.forEach((item, index) => {
      const data = item.data || {};
      const title = item.value || data.name?.short_with_opf || "—";
      const inn = data.inn || "—";
      const kpp = data.kpp ? ` · КПП ${data.kpp}` : "";
      const type = data.type === "INDIVIDUAL" ? "ИП" : "ЮЛ";
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "dropdown-item";
      btn.dataset.index = String(index);
      btn.innerHTML =
        `<span class="dadata-suggestion-title">${escapeHtml(title)}</span>` +
        `<span class="dadata-suggestion-meta">${type} · ИНН ${escapeHtml(inn)}${escapeHtml(kpp)}</span>`;
      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        selectSuggestion(currentSuggestions[index]);
      });
      li.appendChild(btn);
      suggestionsEl.appendChild(li);
    });

    suggestionsEl.hidden = false;
    suggestionsEl.classList.add("show");
    queryInput.setAttribute("aria-expanded", "true");
  };

  const formatDate = (ms) => {
    if (!ms && ms !== 0) return "—";
    const date = new Date(Number(ms));
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleDateString("ru-RU");
  };

  const fieldRow = (label, value, mono = false) => {
    const display = value == null || value === "" ? "—" : value;
    const valueClass = mono ? "font-monospace" : "";
    return (
      `<dt class="col-12 col-md-5">${escapeHtml(label)}</dt>` +
      `<dd class="col-12 col-md-7 ${valueClass}">${escapeHtml(display)}</dd>`
    );
  };

  const renderParty = (party) => {
    const data = party.data || {};
    const name = data.name || {};
    const state = data.state || {};
    const management = data.management || {};
    const address = data.address || {};
    const statusInfo = STATUS_MAP[state.status] || {
      label: state.status || "Неизвестно",
      cls: "text-bg-secondary",
    };
    const typeLabel = data.type === "INDIVIDUAL" ? "ИП" : "Юридическое лицо";
    const branch =
      data.branch_type === "BRANCH"
        ? "Филиал"
        : data.branch_type === "MAIN"
          ? "Головная организация"
          : null;

    const title =
      name.short_with_opf ||
      party.value ||
      (data.fio
        ? [data.fio.surname, data.fio.name, data.fio.patronymic].filter(Boolean).join(" ")
        : "Организация");

    resultEl.classList.remove("d-none");
    resultEl.innerHTML = `
      <div class="info-title">
        <span class="dadata-result-name">${escapeHtml(title)}</span>
        <span class="badge ${statusInfo.cls}">${escapeHtml(statusInfo.label)}</span>
      </div>
      <p class="dadata-result-full mb-2">${escapeHtml(name.full_with_opf || "")}</p>
      <dl class="row mb-0 small g-1">
        ${fieldRow("Тип", typeLabel)}
        ${fieldRow("Подразделение", branch)}
        ${fieldRow("ИНН", data.inn, true)}
        ${fieldRow("КПП", data.kpp, true)}
        ${fieldRow("ОГРН", data.ogrn, true)}
        ${fieldRow("ОКВЭД", data.okved, true)}
        ${fieldRow("Руководитель", management.name)}
        ${fieldRow("Должность", management.post)}
        ${fieldRow("Дата регистрации", formatDate(state.registration_date))}
        ${fieldRow("Актуальность", formatDate(state.actuality_date))}
        ${fieldRow("Адрес", address.unrestricted_value || address.value)}
      </dl>
    `;
  };

  const apiErrorMessage = (payload, status) => {
    const detail = payload?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
    }
    return `Ошибка обработки (${status})`;
  };

  async function fetchSuggestions(query) {
    if (abortController) abortController.abort();
    abortController = new AbortController();

    const response = await fetch(
      `/api/dadata/suggest?query=${encodeURIComponent(query)}&count=8`,
      { signal: abortController.signal }
    );

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Ошибка подсказок (${response.status})`);
    }

    const data = await response.json();
    return data.suggestions || [];
  }

  async function fetchPartyByInn(inn) {
    const response = await fetch(`/api/dadata/party?inn=${encodeURIComponent(inn)}`);
    if (response.status === 404) {
      throw new Error("Организация с таким ИНН не найдена");
    }
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Ошибка проверки (${response.status})`);
    }
    return response.json();
  }

  async function selectSuggestion(item) {
    hideSuggestions();
    const inn = item?.data?.inn;
    if (!inn) {
      setStatus("У выбранной организации нет ИНН", "error");
      return;
    }
    queryInput.value = inn;
    await checkByInn(inn);
  }

  async function checkByInn(inn) {
    checkBtn.disabled = true;
    setStatus("Проверяем…", "info");
    resultEl.classList.add("d-none");

    try {
      const party = await fetchPartyByInn(inn);
      renderParty(party);
      setStatus("Найдено", "ok");
    } catch (error) {
      setStatus(error.message || "Ошибка запроса", "error");
    } finally {
      updateSingleEnabled();
    }
  }

  async function onCheck() {
    if (!dadataReady) {
      setStatus("Ключ DaData не задан на сервере", "error");
      return;
    }
    const raw = queryInput.value.trim();
    if (!raw) {
      setStatus("Введите ИНН или название", "error");
      return;
    }

    const inn = extractInn(raw);
    if (inn) {
      await checkByInn(inn);
      return;
    }

    checkBtn.disabled = true;
    setStatus("Ищем организацию…", "info");

    try {
      const items = await fetchSuggestions(raw);
      if (!items.length) {
        setStatus("Ничего не найдено", "error");
        return;
      }
      const firstInn = items[0]?.data?.inn;
      if (!firstInn) {
        setStatus("Не удалось получить ИНН из подсказки", "error");
        return;
      }
      queryInput.value = firstInn;
      await checkByInn(firstInn);
    } catch (error) {
      if (error.name !== "AbortError") {
        setStatus(error.message || "Ошибка поиска", "error");
      }
    } finally {
      updateSingleEnabled();
    }
  }

  const updateSingleEnabled = () => {
    checkBtn.disabled = !dadataReady;
  };

  queryInput.addEventListener("input", () => {
    const value = queryInput.value.trim();
    clearTimeout(debounceTimer);

    if (value.length < 2) {
      hideSuggestions();
      setStatus("", "");
      return;
    }

    debounceTimer = setTimeout(async () => {
      if (!dadataReady) return;
      try {
        const items = await fetchSuggestions(value);
        renderSuggestions(items);
        setStatus(items.length ? "" : "Нет совпадений", items.length ? "" : "warn");
      } catch (error) {
        if (error.name !== "AbortError") {
          hideSuggestions();
          setStatus(error.message || "Ошибка подсказок", "error");
        }
      }
    }, 280);
  });

  queryInput.addEventListener("keydown", (event) => {
    const items = suggestionsEl.querySelectorAll(".dropdown-item");
    if (suggestionsEl.hidden || !items.length) {
      if (event.key === "Enter") {
        event.preventDefault();
        onCheck();
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (activeIndex >= 0) {
        selectSuggestion(currentSuggestions[activeIndex]);
      } else {
        onCheck();
      }
      return;
    } else if (event.key === "Escape") {
      hideSuggestions();
      return;
    } else {
      return;
    }

    items.forEach((el, index) => el.classList.toggle("active", index === activeIndex));
  });

  queryInput.addEventListener("blur", () => {
    setTimeout(hideSuggestions, 120);
  });

  checkBtn.addEventListener("click", onCheck);

  const batchFile = document.getElementById("dadata-file");
  const batchBtn = document.getElementById("dadata-batch-btn");
  const batchStatus = document.getElementById("dadata-batch-status");
  const dropZone = document.getElementById("dadata-drop-zone");
  const dropPlaceholder = document.getElementById("dadata-drop-placeholder");
  const dropSelected = document.getElementById("dadata-drop-selected");
  const fileNameEl = document.getElementById("dadata-file-name");
  const fileSizeEl = document.getElementById("dadata-file-size");
  const fileRemoveBtn = document.getElementById("dadata-file-remove");
  const outputFormat = document.getElementById("dadata-output-format");
  const progressWrap = document.getElementById("dadata-batch-progress-wrap");
  const progressLabel = document.getElementById("dadata-batch-progress-label");
  const progressPct = document.getElementById("dadata-batch-progress-pct");
  const progressBar = document.getElementById("dadata-batch-progress-bar");

  let pollTimer = null;

  const setBatchStatus = (text, kind) => setAlert(batchStatus, text, kind);

  const setProgress = (processed, total) => {
    const safeTotal = total || 0;
    const percent = safeTotal ? Math.round((processed / safeTotal) * 100) : 0;
    progressWrap.classList.remove("d-none");
    progressLabel.textContent = "Проверяем ИНН через DaData…";
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
    } else {
      dropZone.classList.remove("has-file");
      dropPlaceholder.classList.remove("d-none");
      dropSelected.classList.add("d-none");
    }
    updateBatchEnabled();
  };

  const updateBatchEnabled = () => {
    batchBtn.disabled = !(dadataReady && !!batchFile.files[0]);
  };

  const resultFilename = (format) => {
    const value = (format || "csv").toLowerCase();
    if (value === "xlsx") return "dadata_result.xlsx";
    if (value === "xls") return "dadata_result.xls";
    return "dadata_result.csv";
  };

  async function downloadJobResult(jobId, fallbackFormat) {
    const response = await fetch(`/api/dadata/batch/${jobId}/download`);
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

  async function pollJob(jobId, totalHint) {
    const response = await fetch(`/api/dadata/batch/${jobId}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiErrorMessage(payload, response.status));
    }

    setProgress(payload.processed || 0, payload.total || totalHint || 0);

    if (payload.status === "completed") {
      stopPolling();
      await downloadJobResult(jobId, outputFormat.value);
      const suffix = payload.message ? ` ${payload.message}` : "";
      setBatchStatus(
        `Готово: обработано ${payload.processed} из ${payload.total}. Файл скачан.${suffix}`,
        payload.message ? "warn" : "ok"
      );
      updateBatchEnabled();
      return;
    }

    if (payload.status === "failed") {
      stopPolling();
      throw new Error(payload.error || "Задача завершилась с ошибкой");
    }

    setBatchStatus("Проверяем ИНН через DaData…", "info");
    pollTimer = setTimeout(() => {
      pollJob(jobId, totalHint).catch((error) => {
        stopPolling();
        hideProgress();
        setBatchStatus(error.message || "Ошибка массовой проверки", "error");
        updateBatchEnabled();
      });
    }, 500);
  }

  const clearBatchFile = () => {
    batchFile.value = "";
    updateBatchFileUI();
    hideProgress();
    setBatchStatus("", "");
  };

  dropZone.addEventListener("click", (e) => {
    if (e.target.closest("#dadata-file-remove")) return;
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
    if (!/\.(xlsx|xls|csv|txt|tsv)$/i.test(file.name)) {
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
      setBatchStatus("Выберите файл с ИНН", "error");
      return;
    }
    if (!dadataReady) {
      setBatchStatus("Ключ DaData не задан на сервере", "error");
      return;
    }

    stopPolling();
    batchBtn.disabled = true;
    hideProgress();
    setBatchStatus("Загружаем файл и запускаем проверку…", "info");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("output_format", outputFormat.value || "auto");

    try {
      const response = await fetch("/api/dadata/batch", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(apiErrorMessage(payload, response.status));
      }

      setProgress(0, payload.total || 0);
      setBatchStatus("Проверяем ИНН через DaData…", "info");
      await pollJob(payload.job_id, payload.total);
    } catch (error) {
      stopPolling();
      hideProgress();
      setBatchStatus(error.message || "Ошибка массовой проверки", "error");
      updateBatchEnabled();
    }
  });

  const applyConfig = (configured) => {
    dadataReady = !!configured;
    if (configured) {
      configInfo.className = "alert alert-success py-2 px-3 small mb-3";
      configInfo.textContent = "DaData подключена. Можно проверять ИНН.";
    } else {
      configInfo.className = "alert alert-warning py-2 px-3 small mb-3";
      configInfo.innerHTML =
        "Ключ <code>DADATA_API_KEY</code> не задан в окружении сервера. " +
        "Разовая и массовая проверка недоступны, пока ключ не пропишут в <code>.env</code>.";
    }
    updateSingleEnabled();
    updateBatchEnabled();
  };

  const loadDadataStatus = () =>
    fetch("/health")
      .then((r) => r.json())
      .then((d) => applyConfig(d.dadata_configured))
      .catch(() => {
        configInfo.className = "alert alert-danger py-2 px-3 small mb-3";
        configInfo.textContent = "Не удалось проверить статус DaData.";
        dadataReady = false;
        updateSingleEnabled();
        updateBatchEnabled();
      });

  const tabBtn = document.getElementById("tab-dadata-btn");
  if (tabBtn) {
    tabBtn.addEventListener("shown.bs.tab", loadDadataStatus);
  }
  loadDadataStatus();
})();
