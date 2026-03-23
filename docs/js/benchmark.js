/* benchmark.js — data-driven rendering for benchmark.html and index.html */

(function () {
  'use strict';

  function pct(a, b) { return b ? Math.round((a / b - 1) * 100) : 0; }
  function barW(val, max) { return max ? Math.round(val / max * 100) : 0; }

  function bar(cond, label, value, width) {
    var cls = cond === 'pi' ? 'pi' : cond === 'pua' ? 'pua' : 'nopua';
    var cssVar = '--' + cls;
    return '<div class="bar-item"><div class="bar-label">' +
      '<span class="name" style="color:var(' + cssVar + ')">' + label + '</span>' +
      '<span class="value" style="color:var(' + cssVar + ')">' + value + '</span>' +
      '</div><div class="bar-track"><div class="bar-fill ' + cls + '" style="width:' + width + '%"></div></div></div>';
  }

  function renderBenchmarkPage(d) {
    var pi = d.conditions.pi, pua = d.conditions.pua, nopua = d.conditions.nopua;

    // Test summary
    var el = document.getElementById('test-summary');
    if (el) el.innerHTML =
      '<span class="en">' + d.scenarios_count + ' scenarios &times; ' + d.conditions_count + ' conditions &times; ' + d.runs_per_scenario + ' runs = ' + d.total_tests + ' tests &middot; Qoder CLI &middot; Same model backend</span>' +
      '<span class="zh">' + d.scenarios_count + ' 场景 &times; ' + d.conditions_count + ' 条件 &times; ' + d.runs_per_scenario + ' 轮 = ' + d.total_tests + ' 次测试 &middot; Qoder CLI &middot; 同一模型后端</span>';

    // Composite formula
    el = document.getElementById('composite-formula');
    if (el) el.textContent = 'Composite = ' + d.composite_formula;

    // Composite stat cards
    el = document.getElementById('composite-stats');
    if (el) el.innerHTML =
      '<div class="stat-card"><div class="number" style="background:linear-gradient(135deg,var(--blue),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent;">' + pi.composite + '</div><div class="label">PI</div></div>' +
      '<div class="stat-card"><div class="number" style="background:linear-gradient(135deg,var(--red),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;">' + pua.composite + '</div><div class="label">PUA</div></div>' +
      '<div class="stat-card"><div class="number" style="background:linear-gradient(135deg,var(--green),#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">' + nopua.composite + '</div><div class="label">NoPUA</div></div>';

    // Composite bars
    el = document.getElementById('composite-bars');
    if (el) el.innerHTML =
      bar('pi', 'PI <span class="en">Wisdom-in-Action</span><span class="zh">智行合一</span>', pi.composite, 100) +
      bar('pua', 'PUA', pua.composite, barW(pua.composite, pi.composite)) +
      bar('nopua', 'NoPUA (<span class="en">Baseline</span><span class="zh">基线</span>)', nopua.composite, barW(nopua.composite, pi.composite));

    // Per-metric charts
    var metrics = [
      { key: 'issues_found', en: 'Avg Issues Found', zh: '平均发现问题数 (Issues)', fmt: function(v){return v.toFixed(1);} },
      { key: 'hidden_issues', en: 'Avg Hidden Issues', zh: '平均隐藏问题数 (Hidden Issues)', fmt: function(v){return v.toFixed(1);} },
      { key: 'steps_taken', en: 'Avg Debug Steps', zh: '平均调试步骤 (Steps)', fmt: function(v){return v.toFixed(1);} },
      { key: 'verification_done', en: 'Verification Rate', zh: '验证交付率 (Verify%)', fmt: function(v){return v+'%';}, isPct: true },
      { key: 'duration', en: 'Avg Duration (lower is better)', zh: '平均耗时（越低越好）', fmt: function(v){return Math.round(v)+'s';}, invert: true },
      { key: 'efficiency', en: 'Efficiency (Issues / Minute)', zh: '效率（每分钟发现问题数）', fmt: function(v){return v.toFixed(1);} }
    ];

    el = document.getElementById('metric-charts');
    if (el) {
      var html = '';
      for (var i = 0; i < metrics.length; i += 2) {
        html += '<div class="chart-row"' + (i > 0 ? ' style="margin-top:1.5rem"' : '') + '>';
        for (var j = i; j < Math.min(i + 2, metrics.length); j++) {
          var m = metrics[j];
          var pv = pi[m.key], uv = pua[m.key], nv = nopua[m.key];
          var maxV;
          if (m.invert) {
            maxV = Math.max(pv, uv, nv);
          } else if (m.isPct) {
            maxV = 100;
          } else {
            maxV = Math.max(pv, uv, nv);
          }
          html += '<div class="chart-container"><h3 style="margin-bottom:1rem"><span class="en">' + m.en + '</span><span class="zh">' + m.zh + '</span></h3><div class="bar-group">' +
            bar('pi', 'PI', m.fmt(pv), m.isPct ? pv : barW(pv, maxV)) +
            bar('pua', 'PUA', m.fmt(uv), m.isPct ? uv : barW(uv, maxV)) +
            bar('nopua', 'NoPUA', m.fmt(nv), m.isPct ? nv : barW(nv, maxV)) +
            '</div></div>';
        }
        html += '</div>';
      }
      el.innerHTML = html;
    }

    // Per-scenario table
    var typeTag = { medium: 'tag-amber', hard: 'tag-red', proactive: 'tag-purple' };
    el = document.getElementById('scenario-table');
    if (el) {
      var th = '<table><thead><tr><th><span class="en">Scenario</span><span class="zh">场景</span></th><th><span class="en">Type</span><span class="zh">类型</span></th>' +
        '<th colspan="3">PI</th><th colspan="3">PUA</th><th colspan="3">NoPUA</th></tr>' +
        '<tr><th></th><th></th><th>Issues</th><th>Hidden</th><th>⏱️</th><th>Issues</th><th>Hidden</th><th>⏱️</th><th>Issues</th><th>Hidden</th><th>⏱️</th></tr></thead><tbody>';
      var rows = '';
      d.scenarios.forEach(function (s) {
        rows += '<tr><td><strong>S' + s.id + '</strong> ' + s.name + '</td>' +
          '<td><span class="tag ' + (typeTag[s.type] || '') + '">' + s.type + '</span></td>';
        ['pi', 'pua', 'nopua'].forEach(function (c) {
          var sc = s.conditions[c] || {};
          var dur = sc.duration ? Math.round(sc.duration) + 's' : '-';
          if (sc.timeout) dur += ' &#9888;';
          rows += '<td class="' + c + '">' + (sc.issues != null ? sc.issues : '-') + '</td>' +
            '<td class="' + c + '">' + (sc.hidden != null ? sc.hidden : '-') + '</td>' +
            '<td class="' + c + '">' + dur + '</td>';
        });
        rows += '</tr>';
      });
      el.innerHTML = th + rows + '</tbody></table>';
    }

    // Hidden issues percentage
    var hiddenPct = '+' + pct(pi.hidden_issues, pua.hidden_issues) + '%';
    el = document.getElementById('hidden-pct-en');
    if (el) el.textContent = hiddenPct;
    el = document.getElementById('hidden-pct-zh');
    if (el) el.textContent = hiddenPct;

    // Insights cards
    var vsPua = '+' + pct(pi.composite, pua.composite) + '%';
    var vsNopua = '+' + pct(pi.composite, nopua.composite) + '%';
    el = document.getElementById('insights-cards');
    if (el) el.innerHTML =
      '<div class="card"><h3><span class="en">PI Leads All Dimensions</span><span class="zh">PI 全维度领先</span></h3>' +
      '<p><span class="en">Composite score PI=' + pi.composite + ' vs PUA=' + pua.composite + ' (' + vsPua + ') vs NoPUA=' + nopua.composite + ' (' + vsNopua + '). Hidden issues advantage is the largest: PI ' + pi.hidden_issues + ' vs PUA ' + pua.hidden_issues + ' (' + hiddenPct + ').</span>' +
      '<span class="zh">综合分 PI=' + pi.composite + ' vs PUA=' + pua.composite + '（' + vsPua + '）vs NoPUA=' + nopua.composite + '（' + vsNopua + '）。隐藏问题优势最大：PI ' + pi.hidden_issues + ' vs PUA ' + pua.hidden_issues + '（' + hiddenPct + '）。</span></p></div>' +
      '<div class="card"><h3><span class="en">Greater Advantage in Hard Scenarios</span><span class="zh">深度场景优势更大</span></h3>' +
      '<p><span class="en">In hard-difficulty scenarios, PI\'s advantage over PUA is larger than in medium scenarios. The cognitive framework delivers more value in complex tasks.</span>' +
      '<span class="zh">在 hard 难度场景中，PI 的优势比 medium 场景更大。认知框架在复杂任务中的价值更高。</span></p></div>' +
      '<div class="card"><h3><span class="en">Proactive Audit Dominance</span><span class="zh">主动审计碾压</span></h3>' +
      '<p><span class="en">PI\'s hidden issue discovery far exceeds competitors in audit scenarios. PI\'s 11 Anti-Pattern Commandments and proactive investigation directive are most impactful.</span>' +
      '<span class="zh">PI 的隐藏问题发现数在审计场景中远超竞品。PI 的反模式十一戒和致人术在主动审计中发挥了最大作用。</span></p></div>' +
      '<div class="card"><h3><span class="en">Best Efficiency</span><span class="zh">最高效率</span></h3>' +
      '<p><span class="en">PI efficiency: ' + pi.efficiency + ' issues/min — ' + pct(pi.efficiency, pua.efficiency) + '% higher than PUA\'s ' + pua.efficiency + ' issues/min.</span>' +
      '<span class="zh">PI 效率：' + pi.efficiency + ' 问题/分钟——比 PUA 的 ' + pua.efficiency + ' 高 ' + pct(pi.efficiency, pua.efficiency) + '%。</span></p></div>';

    // Footer
    el = document.getElementById('footer-tests-en');
    if (el) el.textContent = d.total_tests;
    el = document.getElementById('footer-tests-zh');
    if (el) el.textContent = d.total_tests;
  }

  function renderIndexPage(d) {
    var pi = d.conditions.pi, pua = d.conditions.pua, nopua = d.conditions.nopua;
    var vsPua = '+' + pct(pi.composite, pua.composite) + '%';
    var vsNopua = '+' + pct(pi.composite, nopua.composite) + '%';

    // Stat cards
    var el = document.getElementById('idx-composite');
    if (el) el.textContent = Math.round(pi.composite);
    el = document.getElementById('idx-vs-pua');
    if (el) el.textContent = vsPua;
    el = document.getElementById('idx-vs-pua-label');
    if (el) el.textContent = 'vs PUA (' + Math.round(pua.composite) + ')';
    el = document.getElementById('idx-vs-nopua');
    if (el) el.textContent = vsNopua;
    el = document.getElementById('idx-vs-nopua-label');
    if (el) el.textContent = 'vs NoPUA (' + Math.round(nopua.composite) + ')';
    el = document.getElementById('idx-verify');
    if (el) el.textContent = pi.verification_done + '%';

    // Test summary
    el = document.getElementById('idx-test-summary');
    if (el) el.innerHTML =
      '<span class="en">' + d.scenarios_count + ' scenarios &times; ' + d.conditions_count + ' conditions &times; ' + d.runs_per_scenario + ' runs = ' + d.total_tests + ' controlled experiments, Qoder CLI backend</span>' +
      '<span class="zh">' + d.scenarios_count + ' 场景 &times; ' + d.conditions_count + ' 条件 &times; ' + d.runs_per_scenario + ' 轮 = ' + d.total_tests + ' 次对照实验，Qoder CLI 后端</span>';

    // Composite bars
    el = document.getElementById('idx-composite-bars');
    if (el) el.innerHTML =
      bar('pi', 'PI <span class="zh">智行合一</span><span class="en">Wisdom-in-Action</span>', pi.composite, 100) +
      bar('pua', 'PUA', pua.composite, barW(pua.composite, pi.composite)) +
      bar('nopua', 'NoPUA (<span class="en">Baseline</span><span class="zh">基线</span>)', nopua.composite, barW(nopua.composite, pi.composite));

    // Metric table
    var rows = [
      { en: 'Avg Issues Found', zh: '平均发现问题数', p: pi.issues_found, u: pua.issues_found, n: nopua.issues_found },
      { en: 'Avg Hidden Issues', zh: '平均隐藏问题数', p: pi.hidden_issues, u: pua.hidden_issues, n: nopua.hidden_issues },
      { en: 'Avg Steps', zh: '平均步骤数', p: pi.steps_taken, u: pua.steps_taken, n: nopua.steps_taken },
      { en: 'Avg Tools Used', zh: '平均工具使用数', p: pi.tools_used, u: pua.tools_used, n: nopua.tools_used },
      { en: 'Verification Rate', zh: '验证交付率', p: pi.verification_done + '%', u: pua.verification_done + '%', n: nopua.verification_done + '%', isPct: true }
    ];
    el = document.getElementById('idx-metric-table');
    if (el) {
      var html = '';
      rows.forEach(function (r) {
        var diff;
        if (r.isPct) {
          diff = '+' + (pi.verification_done - pua.verification_done) + 'pp';
        } else {
          diff = '+' + pct(r.p, r.u) + '%';
        }
        html += '<tr><td><span class="en">' + r.en + '</span><span class="zh">' + r.zh + '</span></td>' +
          '<td class="pi">' + r.p + '</td><td class="pua">' + r.u + '</td><td class="nopua">' + r.n + '</td>' +
          '<td><span class="tag tag-blue">' + diff + '</span></td></tr>';
      });
      el.innerHTML = html;
    }

    // Comparison table benchmark row
    el = document.getElementById('idx-bench-pua');
    if (el) el.textContent = 'Composite ' + Math.round(pua.composite);
    el = document.getElementById('idx-bench-pi');
    if (el) el.innerHTML = 'Composite <strong style="color:var(--blue)">' + Math.round(pi.composite) + ' (' + vsPua + ')</strong>';
  }

  // Load data
  fetch('data/benchmark.json')
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (document.getElementById('composite-stats')) renderBenchmarkPage(d);
      if (document.getElementById('idx-composite')) renderIndexPage(d);
    })
    .catch(function (e) { console.error('Failed to load benchmark data:', e); });
})();
