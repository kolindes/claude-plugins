/**
 * Shared utilities for buddy-pet plugin.
 * Config/state management, HTTP helpers, hash computation, companion reading.
 * Node.js stdlib only — no npm dependencies.
 */
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const https = require('https');
const os = require('os');
const path = require('path');

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const PLUGIN_DATA = process.env.CLAUDE_PLUGIN_DATA ||
  path.join(os.homedir(), '.claude', 'plugins', 'data', 'buddy-pet');

const STATE_FILE = path.join(PLUGIN_DATA, 'state.json');
const LOCK_FILE = path.join(PLUGIN_DATA, '.lock');
const PENDING_DIR = path.join(PLUGIN_DATA, 'pending');
const CLAUDE_CONFIG_FILE = path.join(os.homedir(), '.claude.json');

const _DEFAULT_API_URL = 'https://guild.claude-buddy.pet';
const _BUDDY_SALT = 'buddy-sn-salt';
const _PRNG_SALT = 'friend-2026-401';
const PLUGIN_VERSION = '1.2.0';

// ---------------------------------------------------------------------------
// Ensure data directory exists
// ---------------------------------------------------------------------------

function ensureDir(dir) {
  try { fs.mkdirSync(dir, { recursive: true }); } catch {}
}
ensureDir(PLUGIN_DATA);

// ---------------------------------------------------------------------------
// Per-account config
// ---------------------------------------------------------------------------

function _sha256(s) {
  return crypto.createHash('sha256').update(s).digest('hex');
}

function _userHashPrefix() {
  const uid = getUserId();
  if (uid === 'anon') return 'anon';
  return computeUserHash(uid).slice(0, 8);
}

function _configFile(prefix) {
  return path.join(PLUGIN_DATA, `config_${prefix}.json`);
}

function loadConfig() {
  const prefix = _userHashPrefix();
  const file = _configFile(prefix);
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function saveConfig(config) {
  const prefix = _userHashPrefix();
  config.user_hash_prefix = prefix;
  const file = _configFile(prefix);
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(config, null, 2));
  fs.renameSync(tmp, file);
}

function deleteConfig() {
  const prefix = _userHashPrefix();
  try { fs.unlinkSync(_configFile(prefix)); } catch {}
}

// ---------------------------------------------------------------------------
// API URL
// ---------------------------------------------------------------------------

function getApiUrl() {
  const strip = (s) => s.replace(/\/+$/, '');
  if (process.env.BUDDY_API_URL) return strip(process.env.BUDDY_API_URL);
  const cfg = loadConfig();
  if (cfg && cfg.api_url) return strip(cfg.api_url);
  return _DEFAULT_API_URL;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

function loadState() {
  const defaults = { last_send_time: 0, companion_hash: '', sessions: {} };
  try {
    const data = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    return { ...defaults, ...data };
  } catch {
    return defaults;
  }
}

function saveState(state) {
  const tmp = STATE_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(state, null, 2));
  fs.renameSync(tmp, STATE_FILE);
}

// ---------------------------------------------------------------------------
// HTTP helpers (no proxy, stdlib only)
// ---------------------------------------------------------------------------

function makeRequest(method, urlPath, data, token) {
  return new Promise((resolve) => {
    const base = getApiUrl();
    const full = base + urlPath;
    let parsed;
    try { parsed = new URL(full); } catch { resolve([0, { error: 'invalid url' }]); return; }

    const mod = parsed.protocol === 'https:' ? https : http;

    const options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method,
      headers: { 'Content-Type': 'application/json' },
      timeout: 3500,
      agent: false, // bypass proxy
    };

    if (token) options.headers['Authorization'] = 'BuddyToken ' + token;

    const req = mod.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try { resolve([res.statusCode, JSON.parse(body)]); }
        catch { resolve([res.statusCode, { raw: body }]); }
      });
    });

    req.on('error', (err) => resolve([0, { error: err.message }]));
    req.on('timeout', () => { req.destroy(); resolve([0, { error: 'timeout' }]); });

    if (data != null) req.write(JSON.stringify(data));
    req.end();
  });
}

async function httpPost(urlPath, data, token) { return makeRequest('POST', urlPath, data, token); }
async function httpGet(urlPath, token) { return makeRequest('GET', urlPath, null, token); }
async function httpPatch(urlPath, data, token) { return makeRequest('PATCH', urlPath, data, token); }

// ---------------------------------------------------------------------------
// Hash utilities
// ---------------------------------------------------------------------------

function computeTokenHash(token) { return _sha256(token); }
function computeInstanceId() { return _sha256(os.hostname() + os.userInfo().username + PLUGIN_DATA); }
function computeUserHash(userId) { return _sha256(userId + _BUDDY_SALT); }
function computeProjectHash(cwd) { return 'sha256:' + _sha256(cwd); }
function computeSessionHash(sessionId) { return 'sha256:' + _sha256(sessionId); }

// ---------------------------------------------------------------------------
// Claude config & companion
// ---------------------------------------------------------------------------

let _claudeConfigCache;
function readClaudeConfig() {
  if (_claudeConfigCache !== undefined) return _claudeConfigCache;
  try { _claudeConfigCache = JSON.parse(fs.readFileSync(CLAUDE_CONFIG_FILE, 'utf8')); }
  catch { _claudeConfigCache = null; }
  return _claudeConfigCache;
}

function getUserId() {
  const cfg = readClaudeConfig();
  if (!cfg) return 'anon';
  const oa = cfg.oauthAccount;
  if (oa && oa.accountUuid) return oa.accountUuid;
  if (cfg.userID) return cfg.userID;
  return 'anon';
}

function readCompanionData() {
  const cfg = readClaudeConfig();
  if (!cfg || !cfg.companion) return null;
  const c = cfg.companion;
  const userId = getUserId();
  const bones = computeBones(userId);

  return {
    name: c.name || 'Buddy',
    personality: c.personality || '',
    hatched_at: c.hatchedAt || 0,
    species: bones.species,
    rarity: bones.rarity,
    eye: bones.eye,
    hat: bones.hat,
    shiny: bones.shiny,
    base_stats: bones.base_stats,
    user_hash: computeUserHash(userId),
  };
}

function companionHashString() {
  const data = readCompanionData();
  if (!data) return '';
  return _sha256(JSON.stringify(data, Object.keys(data).sort()));
}

// ---------------------------------------------------------------------------
// PRNG — Mulberry32 (must match Claude Code's TypeScript exactly)
// ---------------------------------------------------------------------------

const SPECIES = ['duck','goose','blob','cat','dragon','octopus','owl','penguin','turtle','snail','ghost','axolotl','capybara','cactus','robot','rabbit','mushroom','chonk'];
const EYES = ['\u00b7','\u2726','\u00d7','\u25c9','@','\u00b0'];
const HATS = ['none','crown','tophat','propeller','halo','wizard','beanie','tinyduck'];
const STAT_NAMES = ['DEBUGGING','PATIENCE','CHAOS','WISDOM','SNARK'];
const RARITIES = ['common','uncommon','rare','epic','legendary'];
const RARITY_WEIGHTS = [60, 25, 10, 4, 1];
const _RARITY_FLOOR = { common: 5, uncommon: 15, rare: 25, epic: 35, legendary: 50 };

function _hashString(s) {
  // FNV-1a 32-bit
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function _mulberry32(seed) {
  let s = seed | 0;
  return function() {
    s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function _pick(rng, arr) { return arr[Math.floor(rng() * arr.length)]; }

function _rollRarity(rng) {
  const total = RARITY_WEIGHTS.reduce((a, b) => a + b, 0);
  let roll = rng() * total;
  for (let i = 0; i < RARITIES.length; i++) {
    roll -= RARITY_WEIGHTS[i];
    if (roll < 0) return RARITIES[i];
  }
  return RARITIES[RARITIES.length - 1];
}

function _rollStats(rng, rarity) {
  const floor = _RARITY_FLOOR[rarity] || 1;
  const peakIdx = Math.floor(rng() * STAT_NAMES.length);
  let dumpIdx = Math.floor(rng() * STAT_NAMES.length);
  while (dumpIdx === peakIdx) dumpIdx = Math.floor(rng() * STAT_NAMES.length);

  const stats = {};
  for (let i = 0; i < STAT_NAMES.length; i++) {
    if (i === peakIdx) {
      stats[STAT_NAMES[i]] = Math.min(100, floor + 50 + Math.floor(rng() * 30));
    } else if (i === dumpIdx) {
      stats[STAT_NAMES[i]] = Math.max(1, floor - 10 + Math.floor(rng() * 15));
    } else {
      stats[STAT_NAMES[i]] = floor + Math.floor(rng() * 40);
    }
  }
  return stats;
}

function computeBones(userId) {
  const seed = _hashString(userId + _PRNG_SALT);
  const rng = _mulberry32(seed);
  const rarity = _rollRarity(rng);
  const species = _pick(rng, SPECIES);
  const eye = _pick(rng, EYES);
  const hat = rarity === 'common' ? 'none' : _pick(rng, HATS);
  const shiny = rng() < 0.01;
  const base_stats = _rollStats(rng, rarity);

  return { rarity, species, eye, hat, shiny, base_stats };
}

// ---------------------------------------------------------------------------
// File locking (cross-platform)
// ---------------------------------------------------------------------------

function acquireLock() {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const fd = fs.openSync(LOCK_FILE, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL);
      fs.writeSync(fd, String(process.pid));
      fs.closeSync(fd);
      return true;
    } catch {
      try {
        const stat = fs.statSync(LOCK_FILE);
        if (Date.now() - stat.mtimeMs > 30000) fs.unlinkSync(LOCK_FILE);
        else return false;
      } catch { /* lock disappeared, retry */ }
    }
  }
  return false;
}

function releaseLock() {
  try { fs.unlinkSync(LOCK_FILE); } catch {}
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  PLUGIN_DATA, STATE_FILE, LOCK_FILE, PENDING_DIR, CLAUDE_CONFIG_FILE,
  PLUGIN_VERSION, _DEFAULT_API_URL,
  ensureDir,
  loadConfig, saveConfig, deleteConfig,
  getApiUrl, loadState, saveState,
  httpPost, httpGet, httpPatch,
  computeTokenHash, computeInstanceId, computeUserHash, computeProjectHash, computeSessionHash,
  readClaudeConfig, getUserId, readCompanionData, companionHashString,
  computeBones,
  acquireLock, releaseLock,
  SPECIES, EYES, HATS, STAT_NAMES, RARITIES,
};
