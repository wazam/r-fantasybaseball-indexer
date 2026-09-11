var THEME_KEY = 'aga_theme';
var PER_PAGE_KEY = 'aga_per_page';
var REL_TS_KEY = 'aga_relative_timestamps';
var AUTO_COLLAPSE_KEY = 'aga_auto_collapse';
var WIDE_KEY = 'aga_wider_width';
var TEXT_SIZE_KEY = 'aga_text_size';
var HIDE_FLAIRS_KEY = 'aga_hide_flairs';
var BLOCKED_USERS_KEY = 'aga_blocked_users';
var FAVORITED_USERS_KEY = 'aga_favorited_users';
var SAVED_COMMENTS_KEY = 'aga_saved_comments';

// Kicks off as soon as this script runs (before DOMContentLoaded), so the
// server's blocked-users list is cached into localStorage before anything
// that filters/renders based on it needs to read it.
var blockedUsersReady = fetch('/api/lists/blocked_users')
  .then(function(r) { return r.json(); })
  .then(function(items) {
    saveBlockedUsers(items);
    return items;
  })
  .catch(function() {
    return getBlockedUsers();
  });

var favoritedUsersReady = fetch('/api/lists/favorited_users')
  .then(function(r) { return r.json(); })
  .then(function(items) {
    saveFavoritedUsers(items);
    return items;
  })
  .catch(function() {
    return getFavoritedUsers();
  });

var savedCommentsReady = fetch('/api/lists/saved_comments')
  .then(function(r) { return r.json(); })
  .then(function(items) {
    saveSavedComments(items);
    return items;
  })
  .catch(function() {
    return getSavedComments();
  });

var SYNCED_SETTINGS_KEYS = [REL_TS_KEY, HIDE_FLAIRS_KEY, AUTO_COLLAPSE_KEY];

var settingsReady = fetch('/api/settings')
  .then(function(r) { return r.json(); })
  .then(function(data) {
    SYNCED_SETTINGS_KEYS.forEach(function(key) {
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        localStorage.setItem(key, data[key]);
      } else {
        localStorage.removeItem(key);
      }
    });
    // The <head> script already applied hide-flairs synchronously from
    // whatever was cached locally; correct it now in case the server's
    // value (e.g. set from a different browser) disagrees.
    document.documentElement.classList.toggle('hide-flairs', localStorage.getItem(HIDE_FLAIRS_KEY) === 'true');
    return data;
  })
  .catch(function() {
    return {};
  });

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
    if (btn.dataset.size) btn.classList.toggle('active', btn.dataset.size === size);
  });
}

// Night mode (Auto / Light / Dark)
var darkMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

function applyTheme() {
  var saved = localStorage.getItem(THEME_KEY);
  var isDark = saved ? saved === 'dark' : darkMediaQuery.matches;
  document.documentElement.classList.toggle('dark', isDark);
}

function setTheme(choice) {
  if (choice === 'auto') {
    localStorage.removeItem(THEME_KEY);
  } else {
    localStorage.setItem(THEME_KEY, choice);
  }
  applyTheme();
  syncThemeControl();
}

function syncThemeControl() {
  var choice = localStorage.getItem(THEME_KEY) || 'auto';
  document.querySelectorAll('.segment-btn').forEach(function(btn) {
    if (btn.dataset.theme) btn.classList.toggle('active', btn.dataset.theme === choice);
  });
}

darkMediaQuery.addEventListener('change', function() {
  if (!localStorage.getItem(THEME_KEY)) applyTheme();
});

// Wider width
function toggleWiderWidth() {
  var isWide = document.documentElement.classList.toggle('wide');
  localStorage.setItem(WIDE_KEY, isWide ? 'true' : 'false');
  var toggle = document.getElementById('wider-width-toggle');
  if (toggle) toggle.checked = isWide;
}

function persistSetting(key, value) {
  if (value === null) {
    fetch('/api/settings/' + key, { method: 'DELETE' }).catch(function() {});
  } else {
    fetch('/api/settings/' + key, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: value }),
    }).catch(function() {});
  }
}

// Relative timestamps — default OFF (only on if explicitly set to 'true')
function toggleRelativeTimestamps() {
  var enabled = localStorage.getItem(REL_TS_KEY) === 'true';
  enabled = !enabled;
  if (enabled) {
    localStorage.setItem(REL_TS_KEY, 'true');
    persistSetting(REL_TS_KEY, 'true');
  } else {
    localStorage.removeItem(REL_TS_KEY);
    persistSetting(REL_TS_KEY, null);
  }
  var toggle = document.getElementById('rel-ts-toggle');
  if (toggle) toggle.checked = enabled;
}

// Hide flairs — default OFF (only on if explicitly set to 'true')
function toggleHideFlairs() {
  var hidden = document.documentElement.classList.toggle('hide-flairs');
  if (hidden) {
    localStorage.setItem(HIDE_FLAIRS_KEY, 'true');
    persistSetting(HIDE_FLAIRS_KEY, 'true');
  } else {
    localStorage.removeItem(HIDE_FLAIRS_KEY);
    persistSetting(HIDE_FLAIRS_KEY, null);
  }
  var toggle = document.getElementById('hide-flairs-toggle');
  if (toggle) toggle.checked = hidden;
}

// Blocked users
function getBlockedUsers() {
  try {
    return JSON.parse(localStorage.getItem(BLOCKED_USERS_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveBlockedUsers(list) {
  if (list.length) {
    localStorage.setItem(BLOCKED_USERS_KEY, JSON.stringify(list));
  } else {
    localStorage.removeItem(BLOCKED_USERS_KEY);
  }
}

function isUserBlocked(username) {
  return getBlockedUsers().indexOf(username) !== -1;
}

function addBlockedUser(username) {
  username = username.trim();
  if (!username || isUserBlocked(username)) return;
  removeFavoritedUser(username);
  var list = getBlockedUsers();
  list.push(username);
  saveBlockedUsers(list);
  fetch('/api/lists/blocked_users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item: username }),
  }).catch(function() {});
}

function removeBlockedUser(username) {
  var list = getBlockedUsers().filter(function(u) { return u !== username; });
  saveBlockedUsers(list);
  fetch('/api/lists/blocked_users/' + encodeURIComponent(username), { method: 'DELETE' }).catch(function() {});
}

function applyBlockedUsers() {
  var blocked = getBlockedUsers();
  if (!blocked.length) return;
  document.querySelectorAll('.comment-author').forEach(function(btn) {
    if (blocked.indexOf(btn.textContent) === -1) return;
    var container = btn.closest('.comment, .search-result-item, .context-comment');
    if (container) container.style.display = 'none';
  });
}

// Favorited users
function getFavoritedUsers() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITED_USERS_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveFavoritedUsers(list) {
  if (list.length) {
    localStorage.setItem(FAVORITED_USERS_KEY, JSON.stringify(list));
  } else {
    localStorage.removeItem(FAVORITED_USERS_KEY);
  }
}

function isUserFavorited(username) {
  return getFavoritedUsers().indexOf(username) !== -1;
}

function addFavoritedUser(username) {
  username = username.trim();
  if (!username || isUserFavorited(username)) return;
  removeBlockedUser(username);
  var list = getFavoritedUsers();
  list.push(username);
  saveFavoritedUsers(list);
  fetch('/api/lists/favorited_users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item: username }),
  }).catch(function() {});
}

function removeFavoritedUser(username) {
  var list = getFavoritedUsers().filter(function(u) { return u !== username; });
  saveFavoritedUsers(list);
  fetch('/api/lists/favorited_users/' + encodeURIComponent(username), { method: 'DELETE' }).catch(function() {});
}

function applyFavoritedUsers() {
  var favorited = getFavoritedUsers();
  if (!favorited.length) return;
  document.querySelectorAll('.comment-author').forEach(function(btn) {
    if (favorited.indexOf(btn.textContent) !== -1) btn.classList.add('favorited');
  });
}

// Saved comments
function getSavedComments() {
  try {
    return JSON.parse(localStorage.getItem(SAVED_COMMENTS_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveSavedComments(list) {
  if (list.length) {
    localStorage.setItem(SAVED_COMMENTS_KEY, JSON.stringify(list));
  } else {
    localStorage.removeItem(SAVED_COMMENTS_KEY);
  }
}

function isCommentSaved(commentId) {
  return getSavedComments().indexOf(commentId) !== -1;
}

function toggleSavedComment(commentId, btn) {
  var list = getSavedComments();
  var idx = list.indexOf(commentId);
  var nowSaved = idx === -1;
  if (nowSaved) {
    list.push(commentId);
  } else {
    list.splice(idx, 1);
  }
  saveSavedComments(list);
  if (nowSaved) {
    fetch('/api/lists/saved_comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item: commentId }),
    }).catch(function() {});
  } else {
    fetch('/api/lists/saved_comments/' + encodeURIComponent(commentId), { method: 'DELETE' }).catch(function() {});
  }
  if (btn) {
    var saved = isCommentSaved(commentId);
    btn.classList.toggle('saved', saved);
    btn.setAttribute('aria-label', saved ? 'Unsave comment' : 'Save comment');
    if (!saved) {
      var savedPageItem = btn.closest('#saved-comments-container .search-result-item');
      if (savedPageItem) savedPageItem.remove();
    }
  }
}

var CONTEXT_ICON_VIEW = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
var CONTEXT_ICON_HIDE = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>';

function toggleContext(commentId, btn) {
  var container = document.getElementById('ctx-' + commentId);
  if (container.style.display !== 'none') {
    container.style.display = 'none';
    container.innerHTML = '';
    btn.innerHTML = CONTEXT_ICON_VIEW;
    btn.setAttribute('aria-label', 'View context');
    return;
  }
  btn.classList.add('loading');
  var query = document.querySelector('.search-results') ? document.querySelector('.search-results').dataset.query : '';
  fetch('/comment/' + commentId + '/context' + (query ? '?q=' + encodeURIComponent(query) : ''))
    .then(function(r) { return r.text(); })
    .then(function(html) {
      container.innerHTML = html;
      container.style.display = '';
      btn.classList.remove('loading');
      btn.innerHTML = CONTEXT_ICON_HIDE;
      btn.setAttribute('aria-label', 'Hide context');
      markTruncatedFlairs();
      blockedUsersReady.then(function() {
        applyBlockedUsers();
      });
      favoritedUsersReady.then(function() {
        applyFavoritedUsers();
      });
      savedCommentsReady.then(function() {
        applySavedComments();
      });
      settingsReady.then(function() {
        applyRelativeTimestamps();
      });
    })
    .catch(function() {
      btn.classList.remove('loading');
      btn.innerHTML = CONTEXT_ICON_VIEW;
    });
}

function applySavedComments() {
  var saved = getSavedComments();
  if (!saved.length) return;
  document.querySelectorAll('.comment-save-btn').forEach(function(btn) {
    if (saved.indexOf(btn.dataset.commentId) !== -1) {
      btn.classList.add('saved');
      btn.setAttribute('aria-label', 'Unsave comment');
    }
  });
}

function renderUserChipList(containerId, users, removeFn, rerenderFn) {
  var list = document.getElementById(containerId);
  if (!list) return;
  list.innerHTML = '';
  users.forEach(function(username) {
    var li = document.createElement('li');
    li.className = 'blocked-user-chip';
    var nameBtn = document.createElement('button');
    nameBtn.className = 'comment-author';
    nameBtn.textContent = username;
    nameBtn.setAttribute('aria-label', 'View profile for ' + username);
    nameBtn.onclick = function(e) { openAuthorSummary(username, e); };
    var removeBtn = document.createElement('button');
    removeBtn.className = 'blocked-user-remove';
    removeBtn.setAttribute('aria-label', 'Remove ' + username);
    removeBtn.textContent = '×';
    removeBtn.onclick = function() {
      removeFn(username);
      rerenderFn();
    };
    li.appendChild(nameBtn);
    li.appendChild(removeBtn);
    list.appendChild(li);
  });
}

function renderBlockedUsersList() {
  renderUserChipList('blocked-users-list', getBlockedUsers(), removeBlockedUser, renderBlockedUsersList);
  syncQuickAddButtons();
}

function renderFavoritedUsersList() {
  renderUserChipList('favorited-users-list', getFavoritedUsers(), removeFavoritedUser, renderFavoritedUsersList);
  applyFavoritedUsers();
}

function addFavoritedUserFromInput() {
  var input = document.getElementById('favorited-user-input');
  if (!input) return;
  addFavoritedUser(input.value);
  input.value = '';
  renderFavoritedUsersList();
  renderBlockedUsersList();
}

function syncQuickAddButtons() {
  document.querySelectorAll('.quickadd-btn').forEach(function(btn) {
    var already = isUserBlocked(btn.dataset.username);
    btn.disabled = already;
    btn.classList.toggle('added', already);
  });
}

function quickAddBlockedUser(username) {
  addBlockedUser(username);
  renderBlockedUsersList();
  renderFavoritedUsersList();
}

function addBlockedUserFromInput() {
  var input = document.getElementById('blocked-user-input');
  if (!input) return;
  addBlockedUser(input.value);
  input.value = '';
  renderBlockedUsersList();
  renderFavoritedUsersList();
}

function timeAgo(utcStr) {
  var date = new Date(utcStr);
  var now = new Date();
  var diff = now - date;
  var mins = Math.floor(diff / 60000);
  var hours = Math.floor(diff / 3600000);
  var days = Math.floor(diff / 86400000);
  var weeks = Math.floor(days / 7);
  if (days >= 30) return null;
  if (weeks >= 1) return weeks + 'w';
  if (days >= 1) return days + 'd';
  if (hours >= 1) return hours + 'h';
  if (mins >= 1) return mins + 'm';
  return 'just now';
}

function applyRelativeTimestamps() {
  if (localStorage.getItem(REL_TS_KEY) !== 'true') return;
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
    localStorage.setItem(AUTO_COLLAPSE_KEY, '');
    persistSetting(AUTO_COLLAPSE_KEY, '');
    return;
  }
  var num = Number(val);
  if (!Number.isInteger(num)) {
    input.value = '';
    localStorage.setItem(AUTO_COLLAPSE_KEY, '');
    persistSetting(AUTO_COLLAPSE_KEY, '');
    return;
  }
  localStorage.setItem(AUTO_COLLAPSE_KEY, String(num));
  persistSetting(AUTO_COLLAPSE_KEY, String(num));
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
  syncThemeControl();
  syncTextSizeControl();
  var wideToggle = document.getElementById('wider-width-toggle');
  if (wideToggle) wideToggle.checked = localStorage.getItem(WIDE_KEY) === 'true';
  markTruncatedFlairs();
  blockedUsersReady.then(function() {
    applyBlockedUsers();
  });
  favoritedUsersReady.then(function() {
    applyFavoritedUsers();
  });
  savedCommentsReady.then(function() {
    applySavedComments();
  });
  settingsReady.then(function() {
    applyRelativeTimestamps();
    applyAutoCollapse();
  });
});

// Author summary popup
function openAuthorSummary(username, event) {
  if (event) event.stopPropagation();
  var overlay = document.getElementById('author-summary-overlay');
  var panel = document.getElementById('author-summary-panel');
  if (!overlay || !panel) return;
  panel.innerHTML = '<div class="author-summary-loading">Loading…</div>';
  overlay.classList.add('open');
  document.body.classList.add('modal-open');
  fetch('/author/' + encodeURIComponent(username) + '/summary')
    .then(function(r) {
      if (!r.ok) throw new Error('not found');
      return r.text();
    })
    .then(function(html) {
      panel.innerHTML = html;
      syncAuthorActionButtons(panel, username);
    })
    .catch(function() {
      panel.innerHTML = '<div class="author-summary-loading">Could not load profile.</div>';
    });
}

function syncAuthorActionButtons(panel, username) {
  var blockBtn = panel.querySelector('.author-block-btn');
  var favoriteBtn = panel.querySelector('.author-favorite-btn');
  var blocked = isUserBlocked(username);
  var favorited = isUserFavorited(username);
  if (blockBtn) {
    blockBtn.classList.toggle('blocked', blocked);
    blockBtn.disabled = favorited;
    blockBtn.setAttribute('aria-label', (blocked ? 'Unblock u/' : 'Block u/') + username);
  }
  if (favoriteBtn) {
    favoriteBtn.classList.toggle('favorited', favorited);
    favoriteBtn.disabled = blocked;
    favoriteBtn.setAttribute('aria-label', (favorited ? 'Unfavorite u/' : 'Favorite u/') + username);
  }
}

function toggleBlockedUser(username, btn) {
  if (isUserBlocked(username)) {
    removeBlockedUser(username);
  } else {
    addBlockedUser(username);
  }
  syncAuthorActionButtons(btn.closest('.author-summary'), username);
}

function toggleFavoritedUser(username, btn) {
  if (isUserFavorited(username)) {
    removeFavoritedUser(username);
  } else {
    addFavoritedUser(username);
  }
  syncAuthorActionButtons(btn.closest('.author-summary'), username);
}

function closeAuthorSummary() {
  var overlay = document.getElementById('author-summary-overlay');
  if (!overlay) return;
  overlay.classList.remove('open');
  document.body.classList.remove('modal-open');
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeAuthorSummary();
});

// Tap-to-expand truncated flair text (only if actually truncated)
document.addEventListener('click', function(e) {
  var flair = e.target.closest('.comment-flair');
  if (!flair) return;
  var isExpanded = flair.classList.contains('expanded');
  if (!isExpanded && flair.scrollWidth <= flair.clientWidth + 1) return;
  flair.classList.toggle('expanded');
});

function markTruncatedFlairs() {
  document.querySelectorAll('.comment-flair:not(.expanded)').forEach(function(flair) {
    if (flair.scrollWidth > flair.clientWidth + 1) flair.classList.add('truncated');
  });
}
