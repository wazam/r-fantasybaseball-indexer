var THEME_KEY = 'aga_theme';
var PER_PAGE_KEY = 'aga_per_page';
var REL_TS_KEY = 'aga_relative_timestamps';
var AUTO_COLLAPSE_KEY = 'aga_auto_collapse';
var WIDE_KEY = 'aga_wider_width';
var TEXT_SIZE_KEY = 'aga_text_size';

// Text size
function setTextSize(size) {
  document.documentElement.classList.remove('text-small', 'text-large');
  if (size === 'small') document.documentElement.classList.add('text-small');
  if (size === 'large') document.documentElement.classList.add('text-large');
  if (size === 'standard') {
    localStorage.removeItem(TEXT_SIZE_KEY);
  } else {
    localStorage.setItem(TEXT_SIZE_KEY, size);
  }
  syncTextSizeControl();
}

function syncTextSizeControl() {
  var size = localStorage.getItem(TEXT_SIZE_KEY) || 'standard';
  document.querySelectorAll('.segment-btn').forEach(function(btn) {
    btn.classList.toggle('active', btn.dataset.size === size);
  });
}

// Night mode
function toggleNightMode() {
  var isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light');
  syncNightModeToggle();
}

function syncNightModeToggle() {
  var isDark = document.documentElement.classList.contains('dark');
  var toggle = document.getElementById('night-mode-toggle');
  if (toggle) toggle.checked = isDark;
}

// Wider width
function toggleWiderWidth() {
  var isWide = document.documentElement.classList.toggle('wide');
  localStorage.setItem(WIDE_KEY, isWide ? 'true' : 'false');
  var toggle = document.getElementById('wider-width-toggle');
  if (toggle) toggle.checked = isWide;
}

// Relative timestamps — default ON (only off if explicitly set to 'false')
function toggleRelativeTimestamps() {
  var enabled = localStorage.getItem(REL_TS_KEY) !== 'false';
  enabled = !enabled;
  localStorage.setItem(REL_TS_KEY, enabled ? 'true' : 'false');
  var toggle = document.getElementById('rel-ts-toggle');
  if (toggle) toggle.checked = enabled;
}

function timeAgo(utcStr) {
  var date = new Date(utcStr);
  var now = new Date();
  var diff = now - date;
  var mins = Math.floor(diff / 60000);
  var hours = Math.floor(diff / 3600000);
  var days = Math.floor(diff / 86400000);
  if (days >= 7) return null;
  if (days >= 1) return days + 'd ago';
  if (hours >= 1) return hours + 'h ago';
  if (mins >= 1) return mins + 'm ago';
  return 'just now';
}

function applyRelativeTimestamps() {
  if (localStorage.getItem(REL_TS_KEY) === 'false') return;
  document.querySelectorAll('[data-utc]').forEach(function(el) {
    var rel = timeAgo(el.dataset.utc);
    if (rel) el.textContent = rel;
  });
}

// Auto-collapse — default threshold -1
function saveCollapseThreshold() {
  var input = document.getElementById('collapse-threshold');
  if (!input) return;
  var val = input.value.trim();
  if (val === '') {
    localStorage.removeItem(AUTO_COLLAPSE_KEY);
    return;
  }
  var num = Number(val);
  if (!Number.isInteger(num)) {
    input.value = '';
    localStorage.removeItem(AUTO_COLLAPSE_KEY);
    return;
  }
  localStorage.setItem(AUTO_COLLAPSE_KEY, String(num));
}

function applyAutoCollapse() {
  if (!window.location.pathname.match(/^\/threads\//)) return;
  var threshold = localStorage.getItem(AUTO_COLLAPSE_KEY);
  if (threshold === null) threshold = '-1';
  if (threshold === '') return;
  threshold = parseInt(threshold);
  if (isNaN(threshold)) return;
  document.querySelectorAll('.comment').forEach(function(comment) {
    var scoreEl = comment.querySelector('.comment-score');
    if (!scoreEl) return;
    var score = parseInt(scoreEl.textContent);
    if (isNaN(score) || score > threshold) return;
    var btn = comment.querySelector('.collapse-btn');
    if (btn && btn.dataset.collapsed !== 'true') btn.click();
  });
}

// Rows per page preference
function savePerPageSetting(value) {
  if (value === '100') {
    localStorage.removeItem(PER_PAGE_KEY);
  } else {
    localStorage.setItem(PER_PAGE_KEY, value);
  }
}

function applyPerPageDefault() {
  var saved = localStorage.getItem(PER_PAGE_KEY);
  if (!saved || saved === '100') return;
  var url = new URL(window.location.href);
  if (!url.searchParams.has('per_page')) {
    url.searchParams.set('per_page', saved);
    window.location.replace(url.toString());
  }
}

// Focus search on /
document.addEventListener('keydown', function(e) {
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault();
    var input = document.getElementById('search-input');
    if (input) input.focus();
  }
});

document.addEventListener('DOMContentLoaded', function() {
  applyPerPageDefault();
  syncNightModeToggle();
  syncTextSizeControl();
  var wideToggle = document.getElementById('wider-width-toggle');
  if (wideToggle) wideToggle.checked = localStorage.getItem(WIDE_KEY) === 'true';
  applyRelativeTimestamps();
  applyAutoCollapse();
});
