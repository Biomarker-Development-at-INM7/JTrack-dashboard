// stats.js
(function () {
  'use strict';

  window.JDash = window.JDash || {};

  /* =========================================
   * Utilities
   * ========================================= */
  function isVisible(el) {
    return !!el && el.offsetWidth > 0 && el.offsetHeight > 0;
  }
 

  /* =========================================
   * PIE CHARTS (existing)
   * ========================================= */
  JDash.renderStudyPies = function renderStudyPies() {
    var pies = document.querySelectorAll('.study-pie');
  
    pies.forEach(function (el) {
      if (el.dataset.rendered === '1') return;
      if (typeof isVisible === 'function' && !isVisible(el)) return;
  
      var hasPlatform = (typeof el.dataset.ios !== 'undefined') || (typeof el.dataset.android !== 'undefined');
  
      var values, labels, colors;
      if (hasPlatform) {
        var ios = Number(el.dataset.ios || 0);
        var android = Number(el.dataset.android || 0);
        values = [ios, android];
        labels = ['iOS', 'Android'];
        colors = ['#6c757d', '#28a745'];
      } else {
        var stats = {
          completed: Number(el.dataset.completed || 0),
          instudy:   Number(el.dataset.instudy || 0),
          left:      Number(el.dataset.left || 0),
          removed:   Number(el.dataset.removed || 0)
        };
        values = [stats.completed, stats.instudy, stats.left, stats.removed];
        labels = ['Completed', 'InStudy', 'Left', 'Removed'];
        colors = ['#28a745', '#ffc107', '#007bff', '#dc3545'];
      }
  
      var allZero = values.every(function (v) { return v === 0; });
      if (allZero) {
        values = [0];
        labels = ['No data'];
        colors = ['#e0e0e0'];
      }
  
      // Legend on LEFT — shrink pie domain slightly from the left
      var leftLegendPieDomain = { x: [0.22, 1], y: [0, 1] }; // ~22% for legend
      var legendX = 0.215; // just to the left of the pie start (0.22) to minimize gap
  
      var data = [{
        values: values,
        labels: labels,
        type: 'pie',
        hole: 0.4,
        textinfo: allZero ? 'label' : 'value',
        hoverinfo: allZero ? 'label' : 'label+value+percent',
        marker: { colors: colors },
        domain: allZero ? { x: [0, 1], y: [0, 1] } : leftLegendPieDomain
      }];
  
      var layout = {
        // tiny right margin; a hair of left margin so legend doesn't clip
        margin: { l: allZero ? 0 : 12, r: 0, t: 0, b: allZero ? 24 : 0 },
        height: el.clientHeight || 200,
        showlegend: !allZero,
        legend: !allZero ? {
          orientation: 'v',
          x: legendX,           // next to pie
          xanchor: 'right',     // align legend's right edge to x
          y: 0.5,
          yanchor: 'middle',
          font: { size: 11 }
        } : {
          orientation: 'h',
          x: 0.5, xanchor: 'center',
          y: -0.15,
          font: { size: 10 }
        }
      };
  
      Plotly.newPlot(el, data, layout, { displayModeBar: false, responsive: true })
        .then(function () { el.dataset.rendered = '1'; });
    });
  };
  
  /* =========================================
 * HEATMAPS (sensor rows payload: {x, y, z})
 * ========================================= */
  JDash.renderStudyHeatmaps = function renderHeatmaps(){
    const zMax = (Z) => Array.isArray(Z) ? Math.max(0, ...Z.flat().map(v => +v || 0)) : 0;
  
    // Colorscale: force 0 -> white, then continue like YlGnBu
    const zeroWhiteYlGnBu = [
      [0.00, '#ffffff'],  // zero
      [0.001, '#ffffd9'],
      [0.125, '#edf8b1'],
      [0.250, '#c7e9b4'],
      [0.375, '#7fcdbb'],
      [0.500, '#41b6c4'],
      [0.625, '#1d91c0'],
      [0.750, '#225ea8'],
      [0.875, '#253494'],
      [1.000, '#081d58']
    ];
  
    document.querySelectorAll('.study-heat').forEach(function(el){
      if (el.dataset.rendered === '1') return;
      if (!window.Plotly) { console.error('Plotly not loaded'); return; }
  
      // Expect heat-<counter>-... ; capture <counter>
      const m = (el.id || '').match(/^heat-(\d+)(?:-.+)?$/);
      const counter = m ? m[1] : null;
  
      // Try by id first (sensor-map-<counter>)
      let script = counter ? document.getElementById('sensor-map-' + counter) : null;
  
      // Fallback: nearest JSON script sibling
      if (!script) {
        const nextJson = el.parentElement?.querySelector('script[type="application/json"]');
        if (nextJson) script = nextJson;
      }
      if (!script) { console.warn('heatmap: JSON script not found for', el.id); return; }
  
      let cfg = {};
      try { cfg = JSON.parse(script.textContent || '{}'); } catch(e){ console.error('Bad JSON', e); return; }
  
      const x = Array.isArray(cfg.x) ? cfg.x : [];
      const y = Array.isArray(cfg.y) ? cfg.y : [];
      const z = Array.isArray(cfg.z) ? cfg.z : [];
      if (!x.length || !y.length || !z.length) { console.warn('Empty heatmap data for', el.id); return; }
  
      const zmaxVal = Math.max(1, zMax(z)); // avoid zmax=0
  
      Plotly.newPlot(el, [{
        x, y, z,
        type: 'heatmap',
        colorscale: zeroWhiteYlGnBu,
        hoverongaps: false,
        zmin: 0,
        zmax: zmaxVal
      }], {
        margin: { l: 90, r: 10, t: 10, b: 40 },
        height: el.clientHeight || 200,
        // removed axis titles
        xaxis: { type: 'date', tickformat: '%Y-%m-%d', automargin: true },
        yaxis: { automargin: true }
      }, { displayModeBar:false, responsive:true })
      .then(() => {
        el.dataset.rendered = '1';
        // keep domain consistent if data updates
        Plotly.relayout(el, { 'zmax': zmaxVal, 'zmin': 0 });
      })
      .catch(console.error);
    });
  };
  
  
 
  /* =========================================
   * INIT / EVENTS
   * ========================================= */
  function boot() {
    JDash.renderStudyPies();
    JDash.renderStudyHeatmaps();
  }

  

  document.addEventListener('DOMContentLoaded', function () {
    if (typeof Plotly === 'undefined') {
      var tries = 0, intId = setInterval(function () {
        if (typeof Plotly !== 'undefined' || tries++ > 30) {
          clearInterval(intId);
          if (typeof Plotly !== 'undefined') boot();
        }
      }, 120);
    } else {
      boot();
    }
  });

  var resizeTimeout;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function () {
      JDash.renderStudyPies();
      JDash.renderStudyHeatmaps();
      document.querySelectorAll('.study-pie, .study-heat').forEach(function (el) {
        if (el.dataset.rendered === '1') Plotly.Plots.resize(el);
      });
    }, 120);
  });

  document.addEventListener('shown.bs.tab', boot);
  document.addEventListener('shown.bs.collapse', boot);

  if ('ResizeObserver' in window) {
    var ro = new ResizeObserver(function (entries) {
      entries.forEach(function (entry) {
        var el = entry.target;
        if (!el.classList) return;
        if (el.dataset.rendered !== '1' && isVisible(el)) {
          if (el.classList.contains('study-pie')) JDash.renderStudyPies();
          if (el.classList.contains('study-heat')) JDash.renderStudyHeatmaps();
        }
      });
    });
    document.querySelectorAll('.study-pie, .study-heat').forEach(function (el) { ro.observe(el); });
  }
})();
