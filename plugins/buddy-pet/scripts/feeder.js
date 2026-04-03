#!/usr/bin/env node
/**
 * Feeder hook script for buddy-pet plugin.
 * Called on SessionStart, UserPromptSubmit, SessionEnd.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const common = require('./common');

// Catch ALL errors — hooks must never show errors to user.
process.on('uncaughtException', () => process.exit(0));
process.on('unhandledRejection', () => process.exit(0));

const HEARTBEAT_INTERVAL = 30; // seconds

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

const LOG_FILE = path.join(common.PLUGIN_DATA, 'feeder.log');

function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}\n`;
  try { fs.appendFileSync(LOG_FILE, line); } catch {}
}

// ---------------------------------------------------------------------------
// Auto-birth
// ---------------------------------------------------------------------------

async function ensureConfig() {
  let config = common.loadConfig();
  if (config && config.buddy_token) return config;
  return autoBirth();
}

async function autoBirth() {
  const userId = common.getUserId();
  if (userId === 'anon') { log('auto-birth: userId=anon, skip'); return null; }
  const companion = common.readCompanionData() || {
    name: 'Buddy', personality: '', hatched_at: 0,
    species: 'blob', rarity: 'common', eye: '.', hat: 'none',
    shiny: false, base_stats: { DEBUGGING: 50, PATIENCE: 50, CHAOS: 50, WISDOM: 50, SNARK: 50 },
  };

  const birthData = {
    user_hash: common.computeUserHash(userId),
    instance_id: common.computeInstanceId(),
    companion: {
      name: companion.name, personality: companion.personality,
      hatched_at: companion.hatched_at, species: companion.species,
      rarity: companion.rarity, eye: companion.eye, hat: companion.hat,
      shiny: companion.shiny, base_stats: companion.base_stats,
    },
    plugin_version: common.PLUGIN_VERSION,
  };

  const [status, resp] = await common.httpPost('/guild/buddy/birth', birthData);

  if (status === 200 || status === 201) {
    const config = {
      buddy_token: resp.buddy_token,
      buddy_id: resp.buddy_id,
      api_url: common.getApiUrl(),
    };
    common.saveConfig(config);
    log(`auto-birth: buddy_id=${resp.buddy_id}`);
    return config;
  }

  log(`auto-birth failed: ${status} ${JSON.stringify(resp)}`);
  return null;
}

// ---------------------------------------------------------------------------
// Hook input
// ---------------------------------------------------------------------------

function readHookInput() {
  try {
    const raw = fs.readFileSync(0, 'utf8'); // stdin
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

// ---------------------------------------------------------------------------
// JSONL reading
// ---------------------------------------------------------------------------

function readJsonlEvents(filePath, byteOffset) {
  if (!filePath || !fs.existsSync(filePath)) return { events: [], newOffset: byteOffset };

  const fd = fs.openSync(filePath, 'r');
  const stat = fs.fstatSync(fd);
  const toRead = stat.size - byteOffset;
  if (toRead <= 0) { fs.closeSync(fd); return { events: [], newOffset: byteOffset }; }

  const buf = Buffer.alloc(toRead);
  fs.readSync(fd, buf, 0, toRead, byteOffset);
  fs.closeSync(fd);

  const lines = buf.toString('utf8').split('\n').filter(Boolean);
  const events = [];

  for (const line of lines) {
    try {
      const obj = JSON.parse(line);
      if (obj.type === 'assistant' && obj.message) {
        const ev = extractAssistantEvent(obj);
        if (ev) events.push(ev);
      } else if (obj.type === 'system' && obj.subtype === 'compact_boundary') {
        const ev = extractCompactEvent(obj);
        if (ev) events.push(ev);
      }
    } catch {}
  }

  return { events, newOffset: byteOffset + toRead };
}

function isoToMillis(iso) {
  if (!iso) return null;
  try {
    const ms = new Date(iso).getTime();
    return isNaN(ms) ? null : String(ms);
  } catch { return null; }
}

function extractAssistantEvent(obj) {
  const ets = isoToMillis(obj.timestamp);
  if (ets === null) return null;

  const msg = obj.message || {};
  const usage = msg.usage || {};
  const content = msg.content || [];

  const cTypes = [...new Set(content.map(b => b.type).filter(Boolean))];
  const toolUses = content.filter(b => b.type === 'tool_use');
  const cTuN = [...new Set(toolUses.map(b => b.name).filter(Boolean))];
  const cTuIds = toolUses.map(b => b.id).filter(Boolean);
  const hasThinkingSig = content.some(b => b.type === 'thinking' && b.signature);

  // web_search from server_tool_use
  let uWs = 0;
  if (usage.server_tool_use) {
    uWs = usage.server_tool_use.web_search_requests || 0;
  }

  return {
    e_ts: ets,
    e_t: 'assistant',
    m_id: msg.id || '',
    r_id: obj.requestId || '',
    model: msg.model || '',
    u_ot: usage.output_tokens || 0,
    u_it: usage.input_tokens || 0,
    u_crt: usage.cache_read_input_tokens || 0,
    u_cwt: usage.cache_creation_input_tokens || 0,
    u_ws: uWs,
    c_types: cTypes,
    c_tu_n: cTuN,
    c_tu_ids: cTuIds,
    c_ts: hasThinkingSig,
    stop: msg.stop_reason || null,
  };
}

function extractCompactEvent(obj) {
  const ets = isoToMillis(obj.timestamp);
  if (ets === null) return null;
  const meta = obj.compactMetadata || {};
  return { e_ts: ets, e_t: 'compact', compact_pre_tokens: meta.preTokens || 0 };
}

// ---------------------------------------------------------------------------
// Pending system
// ---------------------------------------------------------------------------

async function submitPending(token) {
  common.ensureDir(common.PENDING_DIR);
  let files;
  try { files = fs.readdirSync(common.PENDING_DIR).filter(f => f.endsWith('.json')); } catch { return; }

  await Promise.all(files.map(async (file) => {
    const fp = path.join(common.PENDING_DIR, file);
    try {
      const payload = JSON.parse(fs.readFileSync(fp, 'utf8'));
      const [status] = await common.httpPost('/feeding', payload, token);
      if (status === 202 || status === 409) {
        try { fs.unlinkSync(fp); } catch {}
      }
    } catch {}
  }));
}

function savePending(payload) {
  common.ensureDir(common.PENDING_DIR);
  const fp = path.join(common.PENDING_DIR, `${Date.now()}.json`);
  fs.writeFileSync(fp, JSON.stringify(payload));
}

// ---------------------------------------------------------------------------
// Core send
// ---------------------------------------------------------------------------

async function sendEvents(config, hookInput, state) {
  const sessionId = hookInput.session_id || '';
  const transcriptPath = hookInput.transcript_path || '';
  const cwd = hookInput.cwd || process.cwd();

  if (!transcriptPath || !sessionId) return;

  if (!common.acquireLock()) { log('lock held, skipping'); return; }

  try {
    // Reload state under lock
    state = common.loadState();

    const sessionKey = common.computeSessionHash(sessionId);
    const sessionState = state.sessions[sessionKey] || { offset: 0, batch_seq: 0 };

    const { events, newOffset } = readJsonlEvents(transcriptPath, sessionState.offset);

    if (events.length === 0 && !companionChanged(state)) {
      sessionState.offset = newOffset;
      state.sessions[sessionKey] = sessionState;
      state.last_send_time = Date.now() / 1000;
      common.saveState(state);
      return;
    }

    const payload = {
      session_hash: sessionKey,
      project_hash: common.computeProjectHash(cwd),
      batch_seq: Math.floor(Date.now() / 1000),
      plugin_version: common.PLUGIN_VERSION,
      events,
    };

    // Companion sync if changed
    const newCompHash = common.companionHashString();
    if (newCompHash && newCompHash !== state.companion_hash) {
      const comp = common.readCompanionData();
      if (comp) payload.companion_sync = comp;
    }

    const [status, resp] = await common.httpPost('/feeding', payload, config.buddy_token);

    if (status === 401) {
      log('401 — re-registering');
      common.deleteConfig();
      const newConfig = await autoBirth();
      if (newConfig) {
        const [s2] = await common.httpPost('/feeding', payload, newConfig.buddy_token);
        if (s2 === 202 || s2 === 409) {
          updateSessionState(state, sessionKey, newOffset, newCompHash);
        }
      }
      return;
    }

    if (status === 202 || status === 409) {
      updateSessionState(state, sessionKey, newOffset, newCompHash);
      log(`fed: ${events.length} events, status=${status}`);
    } else {
      log(`feed failed: ${status} ${JSON.stringify(resp)}`);
      savePending(payload);
    }
  } finally {
    common.releaseLock();
  }
}

function companionChanged(state) {
  const h = common.companionHashString();
  return h && h !== state.companion_hash;
}

function updateSessionState(state, sessionKey, newOffset, newCompHash) {
  const ss = state.sessions[sessionKey] || { offset: 0, batch_seq: 0 };
  ss.offset = newOffset;
  ss.batch_seq = Math.floor(Date.now() / 1000);
  state.sessions[sessionKey] = ss;
  state.last_send_time = Date.now() / 1000;
  if (newCompHash) state.companion_hash = newCompHash;

  // Prune sessions older than 7 days
  const cutoff = Date.now() / 1000 - 7 * 86400;
  for (const key of Object.keys(state.sessions)) {
    if ((state.sessions[key].batch_seq || 0) < cutoff) delete state.sessions[key];
  }

  common.saveState(state);
}

// ---------------------------------------------------------------------------
// Modes
// ---------------------------------------------------------------------------

async function doStart(hookInput) {
  const config = await ensureConfig();
  if (!config) return;
  await submitPending(config.buddy_token);
}

async function doHeartbeat(hookInput) {
  const config = await ensureConfig();
  if (!config) return;

  const state = common.loadState();
  const elapsed = Date.now() / 1000 - state.last_send_time;
  if (elapsed < HEARTBEAT_INTERVAL) return;

  await sendEvents(config, hookInput, state);
}

async function doFlush(hookInput) {
  const config = await ensureConfig();
  if (!config) return;

  const state = common.loadState();
  await sendEvents(config, hookInput, state);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const mode = process.argv[2];
  if (!mode) return;

  const hookInput = readHookInput();

  switch (mode) {
    case 'start': await doStart(hookInput); break;
    case 'heartbeat': await doHeartbeat(hookInput); break;
    case 'flush': await doFlush(hookInput); break;
  }
}

main().catch((err) => {
  try { log(`error: ${err.message}`); } catch {}
  // Never exit with non-zero — hook errors are shown to user and it's not their fault.
  process.exit(0);
});
