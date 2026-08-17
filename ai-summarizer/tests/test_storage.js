// Tests for static/js/storage.js — the browser has no test runner, so this
// loads the real file into a Node vm context with a tiny localStorage
// polyfill and exercises it with node:test + node:assert.
//
// Run with:  node --test tests/test_storage.js

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class FakeLocalStorage {
  constructor() { this._store = new Map(); }
  getItem(key) { return this._store.has(key) ? this._store.get(key) : null; }
  setItem(key, value) { this._store.set(key, String(value)); }
  removeItem(key) { this._store.delete(key); }
  clear() { this._store.clear(); }
}

function loadStorageModule() {
  const src = fs.readFileSync(
    path.join(__dirname, "..", "static", "js", "storage.js"),
    "utf-8"
  );
  const sandbox = { localStorage: new FakeLocalStorage(), console };
  vm.createContext(sandbox);
  vm.runInContext(
    src + `
    ;globalThis.__exports = {
      signupUser, loginUser, findUserByEmail, getUsers,
      setCurrentUser, getCurrentUser, clearCurrentUser,
      saveSummary, getSummaries, deleteSummary,
      saveQuiz, getQuizzes, deleteQuiz,
      saveFlashcards, getFlashcards, deleteFlashcard,
      savePdfRecord, getPdfRecords, deletePdfRecord,
      clearAllHistory
    };`,
    sandbox
  );
  return sandbox.__exports;
}

// ── Signup ──────────────────────────────────────────────────────

test("signup: creates a new account", () => {
  const s = loadStorageModule();
  const result = s.signupUser({ name: "Alice", email: "alice@test.com", password: "secret123" });
  assert.ok(result.user);
  assert.equal(result.user.email, "alice@test.com");
  assert.equal(s.getUsers().length, 1);
});

test("signup: rejects missing fields", () => {
  const s = loadStorageModule();
  const result = s.signupUser({ name: "", email: "a@test.com", password: "secret123" });
  assert.ok(result.error);
});

test("signup: rejects short password", () => {
  const s = loadStorageModule();
  const result = s.signupUser({ name: "Bob", email: "bob@test.com", password: "123" });
  assert.ok(result.error);
});

test("signup: rejects duplicate email", () => {
  const s = loadStorageModule();
  s.signupUser({ name: "Bob", email: "dupe@test.com", password: "secret123" });
  const result = s.signupUser({ name: "Bob2", email: "dupe@test.com", password: "secret456" });
  assert.match(result.error, /already exists/i);
});

test("signup: email is case-insensitive for duplicate check", () => {
  const s = loadStorageModule();
  s.signupUser({ name: "Bob", email: "Case@Test.com", password: "secret123" });
  const result = s.signupUser({ name: "Bob2", email: "case@test.com", password: "secret456" });
  assert.match(result.error, /already exists/i);
});

// ── Login ───────────────────────────────────────────────────────

test("login: unknown account is rejected with 404-style error", () => {
  const s = loadStorageModule();
  const result = s.loginUser({ email: "nobody@test.com", password: "whatever" });
  assert.match(result.error, /account not found/i);
  assert.equal(result.status, 404);
});

test("login: wrong password is rejected with 401-style error", () => {
  const s = loadStorageModule();
  s.signupUser({ name: "Carl", email: "carl@test.com", password: "correctpass" });
  const result = s.loginUser({ email: "carl@test.com", password: "wrongpass" });
  assert.match(result.error, /incorrect password/i);
  assert.equal(result.status, 401);
});

test("login: correct credentials succeed and set current user", () => {
  const s = loadStorageModule();
  s.signupUser({ name: "Dana", email: "dana@test.com", password: "correctpass" });
  const result = s.loginUser({ email: "dana@test.com", password: "correctpass" });
  assert.ok(result.user);
  const current = s.getCurrentUser();
  assert.equal(current.email, "dana@test.com");
});

test("logout: clears current user", () => {
  const s = loadStorageModule();
  s.signupUser({ name: "Eve", email: "eve@test.com", password: "correctpass" });
  s.loginUser({ email: "eve@test.com", password: "correctpass" });
  s.clearCurrentUser();
  assert.equal(s.getCurrentUser(), null);
});

test("passwords are not stored in plaintext", () => {
  const s = loadStorageModule();
  s.signupUser({ name: "Frank", email: "frank@test.com", password: "correctpass" });
  const user = s.findUserByEmail("frank@test.com");
  assert.notEqual(user.password, "correctpass");
});

// ── Per-user history isolation ────────────────────────────────────

test("history: users cannot see each other's summaries", () => {
  const s = loadStorageModule();
  const u1 = s.signupUser({ name: "A", email: "a@test.com", password: "secret123" }).user;
  const u2 = s.signupUser({ name: "B", email: "b@test.com", password: "secret123" }).user;

  s.saveSummary(u1.id, { original_text: "hello world", summary: "summary A", depth: "concise" });
  s.saveSummary(u2.id, { original_text: "other text", summary: "summary B", depth: "concise" });

  const u1Summaries = s.getSummaries(u1.id);
  const u2Summaries = s.getSummaries(u2.id);

  assert.equal(u1Summaries.length, 1);
  assert.equal(u2Summaries.length, 1);
  assert.equal(u1Summaries[0].summary, "summary A");
  assert.equal(u2Summaries[0].summary, "summary B");
});

test("history: delete removes only the targeted summary", () => {
  const s = loadStorageModule();
  const u = s.signupUser({ name: "A", email: "a@test.com", password: "secret123" }).user;
  const rec1 = s.saveSummary(u.id, { original_text: "t1", summary: "s1" });
  const rec2 = s.saveSummary(u.id, { original_text: "t2", summary: "s2" });

  s.deleteSummary(u.id, rec1.id);

  const remaining = s.getSummaries(u.id);
  assert.equal(remaining.length, 1);
  assert.equal(remaining[0].id, rec2.id);
});

test("history: quizzes, flashcards, and pdf records save/list/delete correctly", () => {
  const s = loadStorageModule();
  const u = s.signupUser({ name: "A", email: "a@test.com", password: "secret123" }).user;

  const quiz = s.saveQuiz(u.id, { source_text: "text", questions: ["Q1?", "Q2?"] });
  assert.equal(s.getQuizzes(u.id).length, 1);
  s.deleteQuiz(u.id, quiz.id);
  assert.equal(s.getQuizzes(u.id).length, 0);

  const cards = s.saveFlashcards(u.id, { source_text: "text", cards: ["c1", "c2"] });
  assert.equal(s.getFlashcards(u.id).length, 1);
  s.deleteFlashcard(u.id, cards.id);
  assert.equal(s.getFlashcards(u.id).length, 0);

  const pdf = s.savePdfRecord(u.id, { filename: "doc.pdf", page_count: 3, word_count: 500 });
  assert.equal(s.getPdfRecords(u.id).length, 1);
  s.deletePdfRecord(u.id, pdf.id);
  assert.equal(s.getPdfRecords(u.id).length, 0);
});

test("history: clearAllHistory wipes only the given user's data", () => {
  const s = loadStorageModule();
  const u1 = s.signupUser({ name: "A", email: "a@test.com", password: "secret123" }).user;
  const u2 = s.signupUser({ name: "B", email: "b@test.com", password: "secret123" }).user;

  s.saveSummary(u1.id, { original_text: "t", summary: "s1" });
  s.saveSummary(u2.id, { original_text: "t", summary: "s2" });

  s.clearAllHistory(u1.id);

  assert.equal(s.getSummaries(u1.id).length, 0);
  assert.equal(s.getSummaries(u2.id).length, 1); // untouched
});
