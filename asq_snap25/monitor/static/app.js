import { VolumeLandscape3D } from "./volume3d.js";

const REFRESH_MS = 5000;
const FX = 6.77;

let lastSnap = null;
let charts = {};
let scene3d = null;

function fmt(n, d = 0) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });
}

function clsSigned(n) {
  if (n > 0) return "pos";
  if (n < 0) return "neg";
  return "neu";
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setHTML(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function renderTicker(s) {
  const items = [...s.ticker, ...s.ticker];
  setHTML("ticker", items.map((t) => `<span>${t}</span>`).join(""));
}

function renderHero(s) {
  setText("hero-submit", `${fmt(s.submit_notional_cny, 1)} 万 ¥`);
  setText("hero-submit-sub", `${fmt(s.submit_notional_usdt, 0)} USDT · ${fmt(s.submit_count, 0)} orders`);

  setText("hero-fill", `${fmt(s.fill_notional_cny, 1)} 万 ¥`);
  setText("hero-fill-sub", `${fmt(s.fill_notional_usdt, 0)} USDT · ${fmt(s.fill_count, 0)} fills`);

  setText("hero-rate", `${s.fill_rate_pct}%`);
  setText("hero-rate-sub", `proj 24h ≈ ${fmt(s.proj_fill_cny_24h, 1)} 万 ¥`);

  setText("hero-eth", fmt(s.vol_eth, 1));
  setText("hero-eth-sub", `${s.runtime_hours}h session · maker ${((s.maker_count / Math.max(s.fill_count, 1)) * 100).toFixed(1)}%`);

  if (scene3d) {
    scene3d.update(s.hours, s.hourly_submit_wan_cny, s.hourly_fill_wan_cny);
  }

  const strip = s.hours
    .map((h, i) => {
      const sub = s.hourly_submit_wan_cny[i] ?? 0;
      const fill = s.hourly_fill_wan_cny[i] ?? 0;
      const rate = sub > 0 ? ((fill / sub) * 100).toFixed(0) : "—";
      return `<div class="hour-chip">
        <div class="h">${h}:00</div>
        <div class="sub-v">S ${sub.toFixed(0)}</div>
        <div class="fill-v">F ${fill.toFixed(0)}</div>
        <div style="color:#666;margin-top:2px">${rate}%</div>
      </div>`;
    })
    .join("");
  setHTML("hour-strip", strip);
}

function renderKpis(s) {
  setText("k-runtime", `${s.runtime_hours}h`);
  setText("k-runtime-sub", `${s.session_start_cst} → ${s.session_end_cst}`);

  setText("k-eq", fmt(s.equity_cny, 0));
  setText("k-eq-sub", `${fmt(s.equity_usdt, 2)} USDT`);

  const eqCls = clsSigned(s.equity_delta_cny);
  setText("k-pnl", `${s.equity_delta_cny >= 0 ? "+" : ""}${fmt(s.equity_delta_cny, 0)} ¥`);
  document.getElementById("k-pnl").className = `value ${eqCls}`;
  setText("k-pnl-sub", `price ex-fee ${s.price_pnl_cny >= 0 ? "+" : ""}${fmt(s.price_pnl_cny, 0)} ¥`);

  setText("k-fee", fmt(s.fees_cny, 0));
  setText("k-fee-sub", `${s.fee_bps} bp · ${fmt(s.fees_usdt, 1)} USDT`);

  setText("k-net", `${s.net_position_eth >= 0 ? "+" : ""}${s.net_position_eth}`);
  document.getElementById("k-net").className = `value ${clsSigned(s.net_position_eth)}`;
  setText("k-net-sub", "net_position ETH");
}

function renderRisk(s) {
  const rows = [
    ["AS fit OK / Skip", `${s.as_ok} / ${s.as_skip}`],
    ["Quote cycles", `both ${s.quote_both} · sell ${s.quote_sell_only}`],
    ["Spread mode", `${s.spread_ticks_mode} ticks`],
    ["Hold med / P90", `${s.med_hold_s}s / ${s.p90_hold_s}s`],
    ["Closed", `${s.closed_count}`],
    ["−2011", `${s.err_2011}`],
    ["Proj 24h submit", `${fmt(s.proj_sub_cny_24h, 1)}万 ¥`],
    ["Proj 24h fill", `${fmt(s.proj_fill_cny_24h, 1)}万 ¥`],
  ];
  setHTML(
    "risk-grid",
    rows
      .map(([k, v]) => `<div class="risk-item"><div class="k">${k}</div><div class="v">${v}</div></div>`)
      .join("")
  );
}

function renderFills(s) {
  const rows = s.recent_fills
    .map((f) => {
      const sideCls = f.side === "BUY" ? "pos" : "neg";
      return `<tr>
        <td>${f.t_cst}</td>
        <td class="${sideCls}">${f.side}</td>
        <td>${f.qty.toFixed(3)}</td>
        <td>${f.px.toFixed(2)}</td>
        <td>${fmt(f.notional_usdt * FX, 0)}</td>
        <td>${f.liq}</td>
      </tr>`;
    })
    .join("");
  setHTML("fills-body", rows || `<tr><td colspan="6">No fills</td></tr>`);
}

function renderWorst(s) {
  const rows = s.worst_closed
    .map((w) => {
      const rp = w.realized_cny;
      return `<tr>
        <td>${w.t_cst}</td>
        <td>${w.entry}</td>
        <td>${w.peak.toFixed(3)}</td>
        <td>${Math.round(w.dur_s)}s</td>
        <td class="${clsSigned(rp)}">${fmt(rp, 0)}</td>
      </tr>`;
    })
    .join("");
  setHTML("worst-body", rows || `<tr><td colspan="5">—</td></tr>`);
}

function chartOpts() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: {
      legend: { labels: { color: "#7a7a88", boxWidth: 10, font: { size: 10, family: "IBM Plex Mono" } } },
    },
    scales: {
      x: {
        ticks: { color: "#7a7a88", font: { size: 10, family: "IBM Plex Mono" } },
        grid: { color: "rgba(255,255,255,0.04)" },
      },
      y: {
        ticks: { color: "#7a7a88", font: { size: 10, family: "IBM Plex Mono" } },
        grid: { color: "rgba(255,255,255,0.04)" },
      },
    },
  };
}

function upsertChart(id, cfg) {
  const el = document.getElementById(id);
  if (!el) return;
  if (charts[id]) {
    charts[id].data = cfg.data;
    charts[id].update();
    return;
  }
  charts[id] = new Chart(el, cfg);
}

function renderCharts(s) {
  const labels = s.hours.map((h) => `${h}:00`);

  upsertChart("chart-equity", {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Equity Δ ¥",
        data: s.hourly_equity_delta_cny,
        borderColor: "#ff4d4d",
        backgroundColor: "rgba(255,77,77,0.1)",
        fill: true,
        tension: 0.25,
        pointRadius: 2,
      }],
    },
    options: chartOpts(),
  });

  upsertChart("chart-fee", {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Fee ¥",
        data: s.hourly_fee_cny,
        backgroundColor: "rgba(255,176,32,0.65)",
        borderWidth: 0,
      }],
    },
    options: chartOpts(),
  });
}

function renderMeta(s) {
  const pill = document.getElementById("status-pill");
  pill.className = `status-pill ${s.alive_hint === "LIVE" ? "live" : "stale"}`;
  pill.innerHTML = `<span class="pulse"></span> ${s.alive_hint}`;
  setText("meta-updated", s.generated_at);
  setText("meta-mtime", s.log_mtime);
  setText("meta-fx", `FX ${s.fx_cny}`);
  setText("footer-line", `ASQ COMMAND · ${s.generated_at}`);
}

async function refresh() {
  try {
    const res = await fetch(`/api/snapshot?fx=${FX}&t=${Date.now()}`);
    const s = await res.json();
    if (s.error) throw new Error(s.error);
    lastSnap = s;
    renderTicker(s);
    renderHero(s);
    renderKpis(s);
    renderRisk(s);
    renderFills(s);
    renderWorst(s);
    renderCharts(s);
    renderMeta(s);
  } catch (err) {
    setText("footer-line", `ERROR: ${err.message}`);
  }
}

function init3D() {
  const canvas = document.getElementById("scene3d");
  if (!canvas) return;
  scene3d = new VolumeLandscape3D(canvas);
}

init3D();
refresh();
setInterval(refresh, REFRESH_MS);
