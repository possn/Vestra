'use strict';
const fs = require('fs');
const source = fs.readFileSync('dashboard-weekly-events.js','utf8');
function must(fragment, message) {
  if (!source.includes(fragment)) throw new Error(message || `Missing ${fragment}`);
}
must("const VERSION = '1.6'", 'weekly events version must advance to 1.6');
must('resultMetricSchema: text(row?.result_metric_schema)', 'structured metric schema must be mapped from snapshot');
must('resultMetrics: normaliseOfficialMetrics(row?.result_metrics)', 'structured official metrics must be normalised');
must("'Headline MoM'", 'headline MoM label missing');
must("'Headline YoY'", 'headline YoY label missing');
must("'Core MoM'", 'core MoM label missing');
must("'Core YoY'", 'core YoY label missing');
must('formatOfficialPercent', 'official percentages need a dedicated formatter');
must('hasStructuredOfficialMetrics', 'UI must distinguish structured official metrics');
must("grid.className = 'weekly-detail-grid weekly-detail-grid--official'", 'official metric grid must have its own semantic class');
if (/event\.actual\s*=\s*event\.resultMetrics/.test(source)) throw new Error('Official BLS metrics must never be coerced into generic Actual');
console.log('weekly structured macro metric contract ok');
