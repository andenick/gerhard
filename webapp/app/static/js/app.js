// Gerhard — client glue. Hydrates chart embeds and the explorer.
(function () {
  "use strict";

  function dlButtons(dl) {
    if (!dl || (!dl.csv && !dl.xlsx)) return "";
    var b = '<span class="dl-btns">Download:';
    if (dl.csv) b += ' <a href="' + dl.csv + '">CSV</a>';
    if (dl.xlsx) b += ' <a href="' + dl.xlsx + '">XLSX</a>';
    return b + "</span>";
  }

  function renderChart(el, payload) {
    var fig = payload.figure || {};
    el.innerHTML = "";
    var holder = document.createElement("div");
    holder.style.minHeight = "400px";
    el.appendChild(holder);
    if (fig.data && window.Plotly) {
      Plotly.newPlot(holder, fig.data, fig.layout || {}, { responsive: true, displaylogo: false });
    } else {
      holder.innerHTML = '<p style="color:#888;padding:20px">' + (payload.caption || "Chart unavailable.") + "</p>";
    }
    var meta = document.createElement("div");
    meta.className = "chart-meta";
    meta.innerHTML = "<span>" + (payload.caption || "") + "</span>" + dlButtons(payload.download);
    el.appendChild(meta);
  }

  function hydrate(el) {
    var key = el.getAttribute("data-chart");
    var params = (el.getAttribute("data-params") || "").replace(/&amp;/g, "&");
    if (!key) return;
    el.innerHTML = '<p style="color:#aaa;padding:20px">Loading chart…</p>';
    fetch("/api/chart/" + key + params)
      .then(function (r) { return r.json(); })
      .then(function (p) { renderChart(el, p); })
      .catch(function () { el.innerHTML = '<p style="color:#c0504d;padding:20px">Failed to load chart.</p>'; });
  }

  function hydrateAll() { document.querySelectorAll(".chart-embed[data-chart]").forEach(hydrate); }

  function initExplorer() {
    var root = document.getElementById("explorer");
    if (!root) return;
    var selSeries = document.getElementById("ex-series");
    var selVar = document.getElementById("ex-variable");
    var selCountry = document.getElementById("ex-country");
    var chart = document.getElementById("ex-chart");

    fetch("/api/explorer/options").then(function (r) { return r.json(); }).then(function (opts) {
      opts.forEach(function (o) {
        var op = document.createElement("option");
        op.value = o.id; op.textContent = o.id + " — " + o.name; selSeries.appendChild(op);
      });
      if (opts.length) { selSeries.value = "S006"; if (!selSeries.value) selSeries.value = opts[0].id; loadMeta(); }
    });

    function loadMeta() {
      fetch("/api/explorer/series/" + selSeries.value + "/meta")
        .then(function (r) { return r.json(); })
        .then(function (m) {
          selVar.innerHTML = "";
          (m.metric_columns || []).forEach(function (c) {
            var op = document.createElement("option"); op.value = c;
            op.textContent = c.replace(/_/g, " "); selVar.appendChild(op);
          });
          selCountry.innerHTML = "";
          if (m.countries && m.countries.length) {
            selCountry.disabled = false; selCountry.size = 6;
            m.countries.forEach(function (c) {
              var op = document.createElement("option"); op.value = c; op.textContent = c;
              if (["US", "GB", "DE", "JP", "CN"].indexOf(c) >= 0) op.selected = true;
              selCountry.appendChild(op);
            });
          } else { selCountry.disabled = true; selCountry.size = 1; }
          draw();
        });
    }
    function draw() {
      var countries = Array.from(selCountry.selectedOptions || []).map(function (o) { return o.value; });
      var url = "/api/chart/generic?series=" + selSeries.value + "&variable=" + encodeURIComponent(selVar.value) +
        (countries.length ? "&countries=" + countries.join(",") : "");
      chart.innerHTML = '<p style="color:#aaa;padding:20px">Loading…</p>';
      fetch(url).then(function (r) { return r.json(); }).then(function (p) { renderChart(chart, p); });
    }
    selSeries.addEventListener("change", loadMeta);
    selVar.addEventListener("change", draw);
    selCountry.addEventListener("change", draw);
  }

  document.addEventListener("DOMContentLoaded", function () { hydrateAll(); initExplorer(); });
})();
