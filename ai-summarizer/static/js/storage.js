/* =============================================================
 *  storage.js — Browser Local Storage layer (replaces MongoDB)
 *
 *  This is a college/demo project. Everything here lives in the
 *  browser's localStorage — there is NO server-side database and
 *  NO real security. Passwords are only lightly obfuscated
 *  (see hashPassword below), NOT cryptographically hashed like
 *  bcrypt. Do not reuse this pattern for a real application with
 *  real user data.
 *
 *  Local Storage keys used:
 *    aiSummarizerUsers        -> array of { id, name, email, password, created_at }
 *    aiSummarizerCurrentUser  -> the logged-in user's public info, or absent
 *    aiSummarizerData         -> { [userId]: { summaries, quizzes, flashcards, pdfs } }
 * ============================================================= */

const LS_USERS_KEY        = "aiSummarizerUsers";
const LS_CURRENT_USER_KEY = "aiSummarizerCurrentUser";
const LS_DATA_KEY         = "aiSummarizerData";

const HISTORY_LIMIT = 20; // keep each user's history to the most recent N items, like the old Mongo .limit(20)

// ── low-level JSON read/write helpers ──────────────────────────
function _readJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (e) {
    console.error(`storage.js: corrupted localStorage key "${key}", resetting it.`, e);
    return fallback;
  }
}
function _writeJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (e) {
    console.error(`storage.js: could not write to localStorage key "${key}".`, e);
    return false;
  }
}
function _uid(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/* NOT cryptographically secure. This only keeps plaintext passwords
 * out of localStorage for a demo project — it is NOT a substitute
 * for real hashing (bcrypt, argon2, etc.) in a production app. */
function hashPassword(password) {
  let hash = 0;
  for (let i = 0; i < password.length; i++) {
    hash = (hash << 5) - hash + password.charCodeAt(i);
    hash |= 0;
  }
  return `h_${hash}`;
}

// ═════════════════════════════════════════════════════════════
//  USERS
// ═════════════════════════════════════════════════════════════

function getUsers() {
  return _readJSON(LS_USERS_KEY, []);
}
function saveUsers(users) {
  _writeJSON(LS_USERS_KEY, users);
}
function findUserByEmail(email) {
  const normalized = (email || "").trim().toLowerCase();
  return getUsers().find(u => u.email === normalized) || null;
}

function publicUser(user) {
  return { id: user.id, name: user.name, email: user.email };
}

/**
 * Create a new account.
 * Returns { user } on success, or { error } on failure.
 */
function signupUser({ name, email, password }) {
  name  = (name || "").trim();
  email = (email || "").trim().toLowerCase();

  if (!name || !email || !password) {
    return { error: "Name, email, and password are all required." };
  }
  if (password.length < 6) {
    return { error: "Password must be at least 6 characters." };
  }
  if (!email.includes("@")) {
    return { error: "Invalid email address." };
  }
  if (findUserByEmail(email)) {
    return { error: "Account already exists. Please login." };
  }

  const users = getUsers();
  const user = {
    id: _uid("user"),
    name,
    email,
    password: hashPassword(password),
    created_at: new Date().toISOString()
  };
  users.push(user);
  saveUsers(users);

  return { user: publicUser(user) };
}

/**
 * Verify credentials and log the user in.
 * Returns { user } on success, or { error, status } on failure —
 * status mirrors the old backend's status codes for compatibility.
 */
function loginUser({ email, password }) {
  email = (email || "").trim().toLowerCase();

  if (!email || !password) {
    return { error: "Email and password are required.", status: 400 };
  }

  const user = findUserByEmail(email);
  if (!user) {
    return { error: "Account not found. Please sign up first.", status: 404 };
  }
  if (user.password !== hashPassword(password)) {
    return { error: "Incorrect password. Please try again.", status: 401 };
  }

  setCurrentUser(publicUser(user));
  return { user: publicUser(user) };
}

function setCurrentUser(user) {
  _writeJSON(LS_CURRENT_USER_KEY, user);
}
function getCurrentUser() {
  return _readJSON(LS_CURRENT_USER_KEY, null);
}
function clearCurrentUser() {
  localStorage.removeItem(LS_CURRENT_USER_KEY);
}

// ═════════════════════════════════════════════════════════════
//  PER-USER HISTORY (summaries / quizzes / flashcards / pdfs)
// ═════════════════════════════════════════════════════════════

function _emptyBucket() {
  return { summaries: [], quizzes: [], flashcards: [], pdfs: [] };
}
function _getAllData() {
  return _readJSON(LS_DATA_KEY, {});
}
function _saveAllData(all) {
  _writeJSON(LS_DATA_KEY, all);
}
function _getUserBucket(userId) {
  const all = _getAllData();
  return all[userId] ? all[userId] : _emptyBucket();
}
function _saveUserBucket(userId, bucket) {
  const all = _getAllData();
  all[userId] = bucket;
  _saveAllData(all);
}

// ── Summaries ───────────────────────────────────────────────────
function saveSummary(userId, { original_text, summary, depth }) {
  const bucket = _getUserBucket(userId);
  const record = {
    id: _uid("sum"),
    user_id: userId,
    original_text: (original_text || "").slice(0, 5000),
    summary: summary || "",
    depth: depth || "concise",
    created_at: new Date().toISOString()
  };
  bucket.summaries.unshift(record);
  bucket.summaries = bucket.summaries.slice(0, HISTORY_LIMIT);
  _saveUserBucket(userId, bucket);
  return record;
}
function getSummaries(userId) {
  return _getUserBucket(userId).summaries;
}
function deleteSummary(userId, id) {
  const bucket = _getUserBucket(userId);
  const before = bucket.summaries.length;
  bucket.summaries = bucket.summaries.filter(s => s.id !== id);
  _saveUserBucket(userId, bucket);
  return bucket.summaries.length < before;
}

// ── Quizzes ─────────────────────────────────────────────────────
function saveQuiz(userId, { source_text, questions }) {
  const bucket = _getUserBucket(userId);
  const record = {
    id: _uid("quiz"),
    user_id: userId,
    source_text: (source_text || "").slice(0, 2000),
    questions: questions || [],
    created_at: new Date().toISOString()
  };
  bucket.quizzes.unshift(record);
  bucket.quizzes = bucket.quizzes.slice(0, HISTORY_LIMIT);
  _saveUserBucket(userId, bucket);
  return record;
}
function getQuizzes(userId) {
  return _getUserBucket(userId).quizzes;
}
function deleteQuiz(userId, id) {
  const bucket = _getUserBucket(userId);
  const before = bucket.quizzes.length;
  bucket.quizzes = bucket.quizzes.filter(q => q.id !== id);
  _saveUserBucket(userId, bucket);
  return bucket.quizzes.length < before;
}

// ── Flashcards ──────────────────────────────────────────────────
function saveFlashcards(userId, { source_text, cards }) {
  const bucket = _getUserBucket(userId);
  const record = {
    id: _uid("card"),
    user_id: userId,
    source_text: (source_text || "").slice(0, 2000),
    cards: cards || [],
    created_at: new Date().toISOString()
  };
  bucket.flashcards.unshift(record);
  bucket.flashcards = bucket.flashcards.slice(0, HISTORY_LIMIT);
  _saveUserBucket(userId, bucket);
  return record;
}
function getFlashcards(userId) {
  return _getUserBucket(userId).flashcards;
}
function deleteFlashcard(userId, id) {
  const bucket = _getUserBucket(userId);
  const before = bucket.flashcards.length;
  bucket.flashcards = bucket.flashcards.filter(f => f.id !== id);
  _saveUserBucket(userId, bucket);
  return bucket.flashcards.length < before;
}

// ── PDF records ─────────────────────────────────────────────────
// NOTE: we deliberately do NOT store the extracted PDF text here —
// only lightweight metadata — to stay well within localStorage's
// practical size limits (usually ~5-10MB per origin).
function savePdfRecord(userId, { filename, page_count, word_count }) {
  const bucket = _getUserBucket(userId);
  const record = {
    id: _uid("pdf"),
    user_id: userId,
    filename: filename || "unknown.pdf",
    page_count: page_count || 0,
    word_count: word_count || 0,
    created_at: new Date().toISOString()
  };
  bucket.pdfs.unshift(record);
  bucket.pdfs = bucket.pdfs.slice(0, HISTORY_LIMIT);
  _saveUserBucket(userId, bucket);
  return record;
}
function getPdfRecords(userId) {
  return _getUserBucket(userId).pdfs;
}
function deletePdfRecord(userId, id) {
  const bucket = _getUserBucket(userId);
  const before = bucket.pdfs.length;
  bucket.pdfs = bucket.pdfs.filter(p => p.id !== id);
  _saveUserBucket(userId, bucket);
  return bucket.pdfs.length < before;
}

// ── Clear everything for one user ──────────────────────────────
function clearAllHistory(userId) {
  _saveUserBucket(userId, _emptyBucket());
}
