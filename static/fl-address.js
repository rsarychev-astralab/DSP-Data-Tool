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
})();
