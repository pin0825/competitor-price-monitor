const API_BASE = "/api/v1";
const SERIES_COLOURS = ["#147a59", "#ff8b6a", "#7289da", "#e8a935"];

const state = {
  products: [],
  product: null,
  currentPrices: [],
  history: [],
  statistics: [],
  days: 30,
};

const elements = {
  productSelect: document.querySelector("#product-select"),
  collectButton: document.querySelector("#collect-button"),
  productName: document.querySelector("#product-name"),
  productMeta: document.querySelector("#product-meta"),
  trackingSince: document.querySelector("#tracking-since"),
  heroBestPrice: document.querySelector("#hero-best-price"),
  heroBestRetailer: document.querySelector("#hero-best-retailer"),
  heroSaving: document.querySelector("#hero-saving"),
  lowestPrice: document.querySelector("#lowest-price"),
  lowestRetailer: document.querySelector("#lowest-retailer"),
  marketSpread: document.querySelector("#market-spread"),
  spreadCaption: document.querySelector("#spread-caption"),
  retailerCount: document.querySelector("#retailer-count"),
  retailerCaption: document.querySelector("#retailer-caption"),
  lastObservation: document.querySelector("#last-observation"),
  observationCaption: document.querySelector("#observation-caption"),
  chartContainer: document.querySelector("#chart-container"),
  chartLegend: document.querySelector("#chart-legend"),
  retailerTable: document.querySelector("#retailer-table"),
  runStatus: document.querySelector("#run-status"),
  runPercentage: document.querySelector("#run-percentage"),
  runTitle: document.querySelector("#run-title"),
  runSubtitle: document.querySelector("#run-subtitle"),
  activityList: document.querySelector("#activity-list"),
  sidebarCollectionStatus: document.querySelector(
    "#sidebar-collection-status",
  ),
  toast: document.querySelector("#toast"),
  toastTitle: document.querySelector("#toast-title"),
  toastMessage: document.querySelector("#toast-message"),
};

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = value ?? "";
  return node.innerHTML;
}

function formatMoney(value, currency = "GBP") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function formatDate(value, options = {}) {
  if (!value) return "—";
  const { year, ...dateTimeOptions } = options;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: year ? "numeric" : undefined,
    ...dateTimeOptions,
  }).format(new Date(value));
}

function timeAgo(value) {
  if (!value) return "Not collected";
  const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hr ago`;
  const days = Math.floor(seconds / 86400);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // JSON이 아닌 오류 응답은 기본 메시지를 사용한다.
    }
    throw new Error(detail);
  }

  return response.json();
}

function showToast(title, message, isError = false) {
  elements.toastTitle.textContent = title;
  elements.toastMessage.textContent = message;
  const icon = elements.toast.querySelector(".toast-icon");
  icon.textContent = isError ? "!" : "✓";
  icon.style.background = isError ? "#ffb1a2" : "";
  elements.toast.classList.add("visible");
  window.setTimeout(() => elements.toast.classList.remove("visible"), 4200);
}

async function initialise() {
  try {
    state.products = await request(`${API_BASE}/products`);
    renderProductOptions();

    if (state.products.length === 0) {
      renderEmptyWorkspace();
      return;
    }

    const storedId = Number(window.localStorage.getItem("selectedProductId"));
    const initialProduct =
      state.products.find((product) => product.id === storedId) ||
      state.products[0];
    elements.productSelect.value = String(initialProduct.id);
    await loadProduct(initialProduct.id);
    await loadLatestRun();
  } catch (error) {
    renderFatalError(error);
  }
}

function renderProductOptions() {
  if (!state.products.length) {
    elements.productSelect.innerHTML =
      '<option value="">No products configured</option>';
    elements.productSelect.disabled = true;
    return;
  }

  elements.productSelect.innerHTML = state.products
    .map(
      (product) =>
        `<option value="${product.id}">${escapeHtml(product.name)}</option>`,
    )
    .join("");
}

async function loadProduct(productId) {
  state.product = state.products.find(
    (product) => product.id === Number(productId),
  );
  if (!state.product) return;

  window.localStorage.setItem("selectedProductId", String(productId));
  renderProductIdentity();
  setLoadingState();

  try {
    const [current, history, statistics] = await Promise.all([
      request(`${API_BASE}/products/${productId}/prices/current`),
      request(
        `${API_BASE}/products/${productId}/prices/history?days=${state.days}`,
      ),
      request(
        `${API_BASE}/products/${productId}/statistics?days=${state.days}`,
      ),
    ]);

    state.currentPrices = current.prices;
    state.history = history.observations;
    state.statistics = statistics.listings;
    renderDashboard();
  } catch (error) {
    renderFatalError(error);
  }
}

function renderProductIdentity() {
  const product = state.product;
  elements.productName.textContent = product.name;
  elements.productMeta.textContent = [
    product.brand,
    product.model_number && `Model ${product.model_number}`,
  ]
    .filter(Boolean)
    .join(" · ");
  elements.trackingSince.textContent = formatDate(product.created_at, {
    year: true,
  });
  elements.retailerCount.textContent = product.listings.length;
  const activeCount = product.listings.filter((listing) => listing.is_active)
    .length;
  elements.retailerCaption.textContent = `${activeCount} active source${
    activeCount === 1 ? "" : "s"
  }`;
}

function setLoadingState() {
  elements.chartContainer.innerHTML =
    '<div class="chart-loading"><span class="loader"></span>Loading price history</div>';
  elements.retailerTable.innerHTML =
    '<tr><td colspan="7" class="table-loading">Loading retailer data…</td></tr>';
}

function renderDashboard() {
  renderSummary();
  renderChart();
  renderRetailerTable();
}

function renderSummary() {
  const prices = state.currentPrices;
  if (!prices.length) {
    elements.heroBestPrice.textContent = "—";
    elements.heroBestRetailer.textContent = "Waiting for observations";
    elements.heroSaving.textContent = "Run a collection to begin";
    elements.lowestPrice.textContent = "—";
    elements.lowestRetailer.textContent = "No price collected";
    elements.marketSpread.textContent = "—";
    elements.lastObservation.textContent = "—";
    elements.observationCaption.textContent = "Not collected yet";
    return;
  }

  const sorted = [...prices].sort((a, b) => Number(a.price) - Number(b.price));
  const lowest = sorted[0];
  const highest = sorted.at(-1);
  const spread = Number(highest.price) - Number(lowest.price);
  const latestObservation = [...prices].sort(
    (a, b) => new Date(b.observed_at) - new Date(a.observed_at),
  )[0];

  elements.heroBestPrice.textContent = formatMoney(
    lowest.price,
    lowest.currency,
  );
  elements.heroBestRetailer.textContent = `at ${lowest.retailer}`;
  elements.lowestPrice.textContent = formatMoney(
    lowest.price,
    lowest.currency,
  );
  elements.lowestRetailer.textContent = `Best at ${lowest.retailer}`;
  elements.marketSpread.textContent = formatMoney(spread, lowest.currency);
  elements.spreadCaption.textContent =
    prices.length > 1
      ? `${formatMoney(lowest.price, lowest.currency)} — ${formatMoney(
          highest.price,
          highest.currency,
        )}`
      : "One retailer has price data";
  elements.lastObservation.textContent = timeAgo(latestObservation.observed_at);
  elements.observationCaption.textContent = formatDate(
    latestObservation.observed_at,
    { hour: "2-digit", minute: "2-digit" },
  );

  if (spread > 0) {
    elements.heroSaving.textContent = `Save ${formatMoney(
      spread,
      lowest.currency,
    )} against the highest offer`;
  } else {
    elements.heroSaving.textContent =
      prices.length > 1 ? "Prices currently aligned" : "First source collected";
  }
}

function renderChart() {
  const observations = [...state.history].reverse();
  if (!observations.length) {
    elements.chartLegend.innerHTML = "";
    elements.chartContainer.innerHTML =
      '<div class="chart-empty">No history yet — collect prices to build the trend.</div>';
    return;
  }

  const grouped = new Map();
  observations.forEach((observation) => {
    if (!grouped.has(observation.retailer)) {
      grouped.set(observation.retailer, []);
    }
    grouped.get(observation.retailer).push(observation);
  });

  const series = [...grouped.entries()].map(([retailer, points], index) => ({
    retailer,
    points,
    colour: SERIES_COLOURS[index % SERIES_COLOURS.length],
  }));

  elements.chartLegend.innerHTML = series
    .map(
      (item) =>
        `<span class="legend-item"><i style="background:${item.colour}"></i>${escapeHtml(
          item.retailer,
        )}</span>`,
    )
    .join("");

  const allPrices = observations.map((item) => Number(item.price));
  const allDates = observations.map((item) => new Date(item.observed_at));
  let minimum = Math.min(...allPrices);
  let maximum = Math.max(...allPrices);
  if (minimum === maximum) {
    minimum = Math.max(0, minimum - Math.max(10, minimum * 0.05));
    maximum += Math.max(10, maximum * 0.05);
  } else {
    const padding = (maximum - minimum) * 0.18;
    minimum = Math.max(0, minimum - padding);
    maximum += padding;
  }

  let dateMinimum = Math.min(...allDates.map(Number));
  let dateMaximum = Math.max(...allDates.map(Number));
  if (dateMinimum === dateMaximum) {
    dateMinimum -= 12 * 60 * 60 * 1000;
    dateMaximum += 12 * 60 * 60 * 1000;
  }

  const width = 720;
  const height = 250;
  const bounds = { left: 48, right: 16, top: 12, bottom: 27 };
  const plotWidth = width - bounds.left - bounds.right;
  const plotHeight = height - bounds.top - bounds.bottom;
  const x = (date) =>
    bounds.left +
    ((Number(date) - dateMinimum) / (dateMaximum - dateMinimum)) * plotWidth;
  const y = (price) =>
    bounds.top +
    ((maximum - Number(price)) / (maximum - minimum)) * plotHeight;

  const grid = Array.from({ length: 5 }, (_, index) => {
    const ratio = index / 4;
    const gridY = bounds.top + plotHeight * ratio;
    const price = maximum - (maximum - minimum) * ratio;
    return `
      <line class="chart-grid-line" x1="${bounds.left}" x2="${
        width - bounds.right
      }" y1="${gridY}" y2="${gridY}" />
      <text class="chart-axis-label" x="0" y="${gridY + 3}">${formatMoney(
        price,
      )}</text>
    `;
  }).join("");

  const dateLabels = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3;
    const dateValue = dateMinimum + (dateMaximum - dateMinimum) * ratio;
    const labelX = bounds.left + plotWidth * ratio;
    const anchor = index === 0 ? "start" : index === 3 ? "end" : "middle";
    return `<text class="chart-axis-label" text-anchor="${anchor}" x="${labelX}" y="${
      height - 5
    }">${formatDate(dateValue)}</text>`;
  }).join("");

  const paths = series
    .map((item, seriesIndex) => {
      const coordinates = item.points.map((point) => [
        x(new Date(point.observed_at)),
        y(point.price),
      ]);
      const linePath = coordinates
        .map(([pointX, pointY], index) =>
          `${index === 0 ? "M" : "L"} ${pointX.toFixed(2)} ${pointY.toFixed(2)}`,
        )
        .join(" ");
      const areaPath = `${linePath} L ${coordinates
        .at(-1)[0]
        .toFixed(2)} ${bounds.top + plotHeight} L ${coordinates[0][0].toFixed(
        2,
      )} ${bounds.top + plotHeight} Z`;
      const points = coordinates
        .map(
          ([pointX, pointY]) =>
            `<circle class="chart-point" cx="${pointX}" cy="${pointY}" r="3.5" fill="${item.colour}" />`,
        )
        .join("");

      return `
        ${
          seriesIndex === 0
            ? `<path class="chart-area" d="${areaPath}" fill="${item.colour}" />`
            : ""
        }
        <path class="chart-line" d="${linePath}" stroke="${item.colour}" />
        ${points}
      `;
    })
    .join("");

  elements.chartContainer.innerHTML = `
    <svg class="price-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Retailer price history">
      ${grid}
      ${dateLabels}
      ${paths}
    </svg>
  `;
}

function renderRetailerTable() {
  const listings = state.product.listings;
  if (!listings.length) {
    elements.retailerTable.innerHTML =
      '<tr><td colspan="7" class="table-loading">No retailer listings configured.</td></tr>';
    return;
  }

  const priceMap = new Map(
    state.currentPrices.map((price) => [price.listing_id, price]),
  );
  const statisticsMap = new Map(
    state.statistics.map((item) => [item.listing_id, item]),
  );
  const numericPrices = state.currentPrices.map((item) => Number(item.price));
  const minimumPrice = numericPrices.length ? Math.min(...numericPrices) : null;

  elements.retailerTable.innerHTML = listings
    .map((listing) => {
      const price = priceMap.get(listing.id);
      const statistics = statisticsMap.get(listing.id);
      const isBest = price && Number(price.price) === minimumPrice;
      const initials = listing.retailer
        .split(/\s+/)
        .map((word) => word[0])
        .join("")
        .slice(0, 2)
        .toUpperCase();
      const change = statistics?.percentage_change;
      const changeClass =
        change === null || change === undefined || Number(change) === 0
          ? "flat"
          : Number(change) < 0
            ? "down"
            : "up";
      const changeText =
        change === null || change === undefined
          ? "—"
          : `${Number(change) > 0 ? "+" : ""}${Number(change).toFixed(2)}%`;

      return `
        <tr>
          <td>
            <div class="retailer-name">
              <span class="retailer-logo">${initials}</span>
              <div>
                <strong>${escapeHtml(listing.retailer)}</strong>
                <span>${escapeHtml(new URL(listing.url).hostname.replace("www.", ""))}</span>
              </div>
            </div>
          </td>
          <td class="price-cell">
            ${formatMoney(price?.price, listing.currency)}
            ${isBest ? '<span class="best-label">BEST</span>' : ""}
          </td>
          <td>${
            statistics
              ? `${formatMoney(
                  statistics.minimum_price,
                  listing.currency,
                )} – ${formatMoney(statistics.maximum_price, listing.currency)}`
              : "—"
          }</td>
          <td>${formatMoney(statistics?.average_price, listing.currency)}</td>
          <td><span class="change ${changeClass}">${changeText}</span></td>
          <td>${price ? timeAgo(price.observed_at) : "Never"}</td>
          <td><span class="source-status ${
            price ? "" : "waiting"
          }">${price ? "Reporting" : "Awaiting data"}</span></td>
        </tr>
      `;
    })
    .join("");
}

async function runCollection() {
  elements.collectButton.disabled = true;
  elements.collectButton.classList.add("loading");
  elements.collectButton.querySelector("span").textContent = "Collecting…";
  elements.runStatus.textContent = "Running";
  elements.runStatus.className = "run-status running";
  elements.sidebarCollectionStatus.textContent = "Running";
  elements.runTitle.textContent = "Contacting retailer sources";
  elements.runSubtitle.textContent =
    "Requests run concurrently and failures are isolated.";

  try {
    const result = await request(`${API_BASE}/collection-runs`, {
      method: "POST",
    });
    renderCollectionRun(result);
    await refreshProducts();
    await loadProduct(state.product.id);
    showToast(
      "Collection complete",
      `${result.created} new, ${result.unchanged} unchanged, ${result.failed} failed.`,
      false,
    );
  } catch (error) {
    elements.runStatus.textContent = "Failed";
    elements.runStatus.className = "run-status partial";
    elements.sidebarCollectionStatus.textContent = "Error";
    showToast("Collection failed", error.message, true);
  } finally {
    elements.collectButton.disabled = false;
    elements.collectButton.classList.remove("loading");
    elements.collectButton.querySelector("span").textContent = "Collect prices";
  }
}

async function loadLatestRun() {
  try {
    const run = await request(`${API_BASE}/collection-runs/latest`);
    if (!run) return;

    renderCollectionRun(
      {
        run_id: run.id,
        requested: run.requested_count,
        created: run.created_count,
        unchanged: run.unchanged_count,
        failed: run.failed_count,
        status: run.status,
        started_at: run.started_at,
        finished_at: run.finished_at,
        results: run.attempts,
      },
      true,
    );
  } catch (error) {
    // 가격 화면은 정상 사용할 수 있도록 실행 이력 오류만 콘솔에 남긴다.
    console.warn("Unable to restore latest collection run", error);
  }
}

function renderCollectionRun(result, restored = false) {
  const successful = result.created + result.unchanged;
  const percentage = result.requested
    ? Math.round((successful / result.requested) * 100)
    : 100;
  elements.runPercentage.textContent = `${percentage}%`;
  elements.runTitle.textContent =
    result.failed > 0
      ? `${
          restored ? `Run #${result.run_id} · ` : ""
        }${successful} of ${result.requested} sources responded`
      : `${restored ? `Run #${result.run_id} · ` : ""}All ${
          result.requested
        } sources completed`;
  const completedLabel =
    restored && result.finished_at ? `${timeAgo(result.finished_at)} · ` : "";
  elements.runSubtitle.textContent = `${completedLabel}${result.created} new · ${result.unchanged} unchanged · ${result.failed} failed`;
  const hasFailures = result.status === "failed" || result.failed > 0;
  elements.runStatus.textContent =
    result.status === "failed" ? "Failed" : hasFailures ? "Partial" : "Complete";
  elements.runStatus.className = `run-status ${
    hasFailures ? "partial" : "complete"
  }`;
  elements.sidebarCollectionStatus.textContent = hasFailures
    ? "Partial"
    : "Complete";

  elements.activityList.innerHTML = result.results
    .map((item) => {
      const symbol =
        item.status === "failed" ? "!" : item.status === "unchanged" ? "=" : "✓";
      return `
        <div class="activity-item">
          <span class="activity-symbol ${item.status}">${symbol}</span>
          <div class="activity-copy">
            <strong>${escapeHtml(item.retailer)}</strong>
            <span>${escapeHtml(item.message)} · ${item.duration_ms} ms</span>
          </div>
          <span class="activity-price">${formatMoney(
            item.price,
            item.currency || "GBP",
          )}</span>
        </div>
      `;
    })
    .join("");
}

async function refreshProducts() {
  state.products = await request(`${API_BASE}/products`);
  state.product = state.products.find(
    (product) => product.id === state.product.id,
  );
  renderProductOptions();
  elements.productSelect.value = String(state.product.id);
}

function renderEmptyWorkspace() {
  elements.productName.textContent = "No products configured";
  elements.productMeta.textContent =
    "Create a product in the API explorer to start monitoring.";
  elements.collectButton.disabled = true;
  elements.chartContainer.innerHTML =
    '<div class="chart-empty">Your price history will appear here.</div>';
  elements.retailerTable.innerHTML =
    '<tr><td colspan="7" class="table-loading">Add a product and retailer listing through Swagger.</td></tr>';
}

function renderFatalError(error) {
  elements.chartContainer.innerHTML = `<div class="chart-empty">Unable to load dashboard: ${escapeHtml(
    error.message,
  )}</div>`;
  elements.retailerTable.innerHTML =
    '<tr><td colspan="7" class="table-loading">API data is currently unavailable.</td></tr>';
  showToast("Dashboard unavailable", error.message, true);
}

elements.productSelect.addEventListener("change", (event) => {
  loadProduct(Number(event.target.value));
});

elements.collectButton.addEventListener("click", runCollection);

document.querySelectorAll(".period-control button").forEach((button) => {
  button.addEventListener("click", async () => {
    document
      .querySelectorAll(".period-control button")
      .forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.days = Number(button.dataset.days);
    await loadProduct(state.product.id);
  });
});

initialise();
