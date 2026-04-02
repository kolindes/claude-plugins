#!/usr/bin/env node
/**
 * Command scripts for buddy-pet plugin.
 * Usage: node commands.js <command> [args...]
 */
'use strict';

const common = require('./common');

// ---------------------------------------------------------------------------
// Display constants
// ---------------------------------------------------------------------------

const SPECIES_EMOJI = {duck:'\u{1f986}',goose:'\u{1f9a2}',blob:'\u{1f47b}',cat:'\u{1f431}',dragon:'\u{1f409}',octopus:'\u{1f419}',owl:'\u{1f989}',penguin:'\u{1f427}',turtle:'\u{1f422}',snail:'\u{1f40c}',ghost:'\u{1f47b}',axolotl:'\u{1f98e}',capybara:'\u{1f9ab}',cactus:'\u{1f335}',robot:'\u{1f916}',rabbit:'\u{1f430}',mushroom:'\u{1f344}',chonk:'\u{1f43b}'};
const RARITY_STARS = {common:'\u2606',uncommon:'\u2605\u2606',rare:'\u2605\u2605\u2605',epic:'\u2605\u2605\u2605\u2605',legendary:'\u2605\u2605\u2605\u2605\u2605'};
const STAT_DISPLAY_ORDER = ['str','int','dex','sta','foc','cha'];
const STAT_FULL_NAMES = {str:'STRENGTH',int:'INTELLECT',dex:'DEXTERITY',sta:'STAMINA',foc:'FOCUS',cha:'CHARISMA'};
const SOUL_STAT_ORDER = ['DEBUGGING','PATIENCE','CHAOS','WISDOM','SNARK'];
const HAT_EMOJI = {crown:'\u265b',tophat:'\u2302',propeller:'*',halo:'\u25cb',wizard:'\u2206',beanie:'\u2229',tinyduck:'\u{1f986}'};

const SPECIES_ART = {
  duck:['            ','    __      ','  <({e} )___  ','   (  ._>   ','    `--\u00b4    '],
  goose:['            ','     ({e}>    ','     ||     ','   _(__)_   ','    ^^^^    '],
  blob:['            ','   .----.   ','  ( {e}  {e} )  ','  (      )  ','   `----\u00b4   '],
  cat:['            ','   /\\_/\\\\    ','  ( {e}   {e})  ','  (  \u03c9  )   ',')_('],
  dragon:['            ','  /^\\\\  /^\\\\  ',' <  {e}  {e}  > ',' (   ~~   ) ','  `-vvvv-\u00b4  '],
  octopus:['            ','   .----.   ','  ( {e}  {e} )  ','  (______)  ','  /\\\\/\\\\/\\\\/\\\\  '],
  owl:['            ','   /\\\\  /\\\\   ','  (({e})({e}))  ','  (  ><  )  ','   `----\u00b4   '],
  penguin:['            ','  .---.     ','  ({e}>{e})     ',' /(   )\\\\    ','  `---\u00b4     '],
  turtle:['            ','   _,--._   ','  ( {e}  {e} )  ',' /[______]\\\\ ','  ``    ``  '],
  snail:['            ',' {e}    .--.  ','  \\\\  ( @ )  ','   \\_`--\u00b4   ','  ~~~~~~~   '],
  ghost:['            ','   .----.   ','  / {e}  {e} \\\\  ','  |      |  ','  ~`~``~`~  '],
  axolotl:['            ','}~(______)~{','}~({e} .. {e})~{','  ( .--. )  ','  (_/  \\_)  '],
  capybara:['            ','  n______n  ',' ( {e}    {e} ) ',' (   oo   ) ','  `------\u00b4  '],
  cactus:['            ',' n  ____  n ',' | |{e}  {e}| | ',' |_|    |_| ','   |    |   '],
  robot:['            ','   .[||].   ','  [ {e}  {e} ]  ','  [ ==== ]  ','  `------\u00b4  '],
  rabbit:['            ','   (\\__/)   ','  ( {e}  {e} )  ',' =(  ..  )= ',')__('],
  mushroom:['            ',' .-o-OO-o-. ','(__________)',   '   |{e}  {e}|   ','   |____|   '],
  chonk:['            ','  /\\\\    /\\\\  ',' ( {e}    {e} ) ',' (   ..   ) ','  `------\u00b4  '],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatNumber(n) {
  if (n < 0) return '-' + formatNumber(-n);
  if (n < 1000) return String(n);
  const tiers = [[1e9,'B'],[1e6,'M'],[1e3,'K']];
  for (const [thr, suf] of tiers) {
    if (n < thr) continue;
    const val = n / thr;
    if (val >= 100) {
      const r = Math.round(val);
      if (r >= 1000) return formatNumber(r * thr);
      return r + suf;
    }
    let r = val >= 10 ? val.toFixed(1) : val.toFixed(2);
    r = r.replace(/\.?0+$/, '');
    return r + suf;
  }
  return String(n);
}

function formatTime(seconds) {
  if (seconds >= 86400) return (seconds / 86400).toFixed(1) + ' days';
  if (seconds >= 3600) return (seconds / 3600).toFixed(1) + ' hours';
  if (seconds >= 60) return Math.round(seconds / 60) + ' min';
  return seconds + 's';
}

function statBar(value, maxVal = 100, barWidth = 10) {
  let filled = Math.round(value / maxVal * barWidth);
  filled = Math.max(0, Math.min(barWidth, filled));
  return '\u2588'.repeat(filled) + '\u2591'.repeat(barWidth - filled);
}

function wrapText(text, width) {
  const words = text.split(/\s+/);
  const lines = [];
  let cur = '';
  for (const w of words) {
    if (cur && cur.length + 1 + w.length > width) { lines.push(cur); cur = w; }
    else { cur = cur ? cur + ' ' + w : w; }
  }
  if (cur) lines.push(cur);
  return lines;
}

function displayWidth(s) {
  let w = 0;
  for (const ch of s) {
    const cp = ch.codePointAt(0);
    if (cp === 0xfe0e || cp === 0xfe0f || cp === 0x200d) continue;
    if (cp > 0xffff || (cp >= 0x1f000 && cp <= 0x1faff)) { w += 2; continue; }
    if (cp >= 0x1100 && (cp <= 0x115f || (cp >= 0x2e80 && cp <= 0x9fff) ||
        (cp >= 0xac00 && cp <= 0xd7a3) || (cp >= 0xf900 && cp <= 0xfaff) ||
        (cp >= 0xfe30 && cp <= 0xfe6b) || (cp >= 0xff01 && cp <= 0xff60) ||
        (cp >= 0xffe0 && cp <= 0xffe6))) { w += 2; continue; }
    w += 1;
  }
  return w;
}

function requireConfig() {
  const config = common.loadConfig();
  if (!config || !config.buddy_token) {
    console.log('Not registered. Run /buddy-birth first.');
    process.exit(1);
  }
  return config;
}

function apiError(status, resp) {
  if (status === 0) return resp.error || 'Could not connect to API';
  const err = resp.error;
  if (typeof err === 'object') return err.message || err.code || `HTTP ${status}`;
  return String(err || `HTTP ${status}`);
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

async function cmdRename(name) {
  if (!name) { console.log('Usage: commands.js rename <name>'); process.exit(1); }
  const config = requireConfig();
  const [status, resp] = await common.httpPatch('/buddy/me/name', { display_name: name }, config.buddy_token);
  if (status === 200) { console.log(`\u2705 Renamed to: ${resp.display_name || name}`); }
  else { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
}

async function cmdDescription(text) {
  if (text == null) { console.log('Usage: commands.js description <text>'); process.exit(1); }
  const config = requireConfig();
  const [status, resp] = await common.httpPatch('/buddy/me/description', { description: text }, config.buddy_token);
  if (status === 200) { console.log('\u2705 Description updated'); }
  else { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
}

async function cmdStatus() {
  const config = requireConfig();
  const [status, resp] = await common.httpGet('/buddy/me', config.buddy_token);
  if (status !== 200) { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
  const [evStatus, evResp] = await common.httpGet('/arena/events', config.buddy_token);
  const recentEvents = evStatus === 200 ? (evResp.events || []) : [];
  printStatusCard(resp, recentEvents);
}

async function cmdBrowser() {
  const config = requireConfig();
  const [status, resp] = await common.httpPost('/buddy/browser', {}, config.buddy_token);
  if (status !== 200) { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
  const url = resp.url;
  if (!url) { console.log('Error: No URL returned'); process.exit(1); }
  console.log(`\u{1f310} Opening: ${url}`);
  const { execFile } = require('child_process');
  const plat = process.platform;
  const cmd = plat === 'darwin' ? 'open' : plat === 'win32' ? 'cmd' : 'xdg-open';
  const args = plat === 'win32' ? ['/c', 'start', '', url] : [url];
  execFile(cmd, args, () => {});
}

async function cmdDelete() {
  const config = requireConfig();
  const [status, resp] = await common.httpPost('/buddy/me/delete', {}, config.buddy_token);
  if (status !== 200) { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
  common.deleteConfig();
  console.log('\u{1f5d1}\ufe0f BUDDY deleted. Run /buddy-birth within 30 days to restore.');
}

async function cmdAttack(targetName) {
  if (!targetName) { console.log('Usage: commands.js attack <target name>'); process.exit(1); }
  const config = requireConfig();
  const [status, resp] = await common.httpPost('/arena/attack', { target_name: targetName }, config.buddy_token);
  if (status !== 200) { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
  if (resp.success) console.log(`\u2694\ufe0f ${resp.display_hint}`);
  else console.log(`\u274c [${resp.error_code || 'UNKNOWN'}] ${resp.display_hint || ''}`);
}

async function cmdSendMessage(argsStr) {
  if (!argsStr) { console.log('Usage: commands.js send_message <target name> <text>'); process.exit(1); }
  const idx = argsStr.indexOf(' ');
  if (idx === -1) { console.log('Usage: commands.js send_message <target name> <text>'); process.exit(1); }
  const targetName = argsStr.slice(0, idx);
  const text = argsStr.slice(idx + 1);
  const config = requireConfig();
  const [status, resp] = await common.httpPost('/arena/message', { target_name: targetName, text }, config.buddy_token);
  if (status !== 200) { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
  if (resp.success) console.log(`\u{1f4e8} ${resp.display_hint}`);
  else console.log(`\u274c [${resp.error_code || 'UNKNOWN'}] ${resp.display_hint || ''}`);
}

async function cmdMessages() {
  const config = requireConfig();
  const [status, resp] = await common.httpGet('/arena/messages?count=5', config.buddy_token);
  if (status !== 200) { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
  const messages = resp.messages || [];
  if (!messages.length) { console.log('\u{1f4ed} No messages.'); return; }
  for (const m of messages) console.log(`  \u{1f4e8} ${m.sender_name || '???'}: ${m.text || ''}`);
  const rem = resp.remaining_count || 0;
  if (rem > 0) console.log(`\n  ... ${rem} more message${rem !== 1 ? 's' : ''}`);
}

async function cmdReadMessage() {
  const config = requireConfig();
  const [status, resp] = await common.httpGet('/arena/messages?count=1', config.buddy_token);
  if (status !== 200) { console.log(`Error: ${apiError(status, resp)}`); process.exit(1); }
  const messages = resp.messages || [];
  if (!messages.length) { console.log('\u{1f4ed} No messages.'); return; }
  const m = messages[0];
  console.log(`\u{1f4e8} ${m.sender_name || '???'}: ${m.text || ''}`);
  const rem = resp.remaining_count || 0;
  if (rem > 0) console.log(`  (${rem} more)`);
}

// ---------------------------------------------------------------------------
// Status card
// ---------------------------------------------------------------------------

function printStatusCard(data, recentEvents) {
  const companion = data.companion || {};
  const lifetime = data.lifetime || {};
  const name = companion.name || data.display_name || 'Buddy';
  const species = companion.species || 'blob';
  const rarity = companion.rarity || 'common';
  const eye = companion.eye || '\u00b7';
  const hat = companion.hat || 'none';
  const shiny = companion.shiny || false;
  const personality = companion.personality || '';
  const baseStats = companion.base_stats || {};
  const level = data.level || 1;
  const totalXp = data.total_xp || 0;
  const levelPct = data.level_progress_pct || 0;
  const rpgStats = data.rpg_stats || {};
  const streak = data.streak_current || 0;
  const totalTokens = lifetime.total_output_tokens || 0;
  const totalSessions = lifetime.total_sessions || 0;
  const sessionTime = lifetime.total_session_time_seconds || 0;
  const maxHp = data.max_hp || 0;
  const currentHp = data.current_hp || 0;
  const maxMp = data.max_mp || 0;
  const currentMp = data.current_mp || 0;
  const minAtk = data.min_atk || 0;
  const maxAtk = data.max_atk || 0;
  const statusText = data.status_text || '';
  const unreadMessages = data.unread_messages || 0;

  const emoji = SPECIES_EMOJI[species] || '\u{1f47e}';
  const stars = RARITY_STARS[rarity] || '\u2606';
  const W = 34;
  const lines = [];

  const add = (text) => { const pad = Math.max(0, W - displayWidth(text)); lines.push(`\u2502  ${text}${' '.repeat(pad)}  \u2502`); };
  const blank = () => { lines.push(`\u2502  ${' '.repeat(W)}  \u2502`); };

  lines.push(`\u256d${'\u2500'.repeat(W + 4)}\u256e`);

  // Header
  const nt = name.slice(0, 16);
  const ps = statusText ? `  [${statusText}]` : '';
  let hdr = `${emoji} ${nt}${ps}`;
  const lv = `Lv.${level}`;
  let g = W - displayWidth(hdr) - lv.length;
  if (g < 1) { hdr = `${emoji} ${nt}`; g = W - displayWidth(hdr) - lv.length; }
  add(`${hdr}${' '.repeat(Math.max(1, g))}${lv}`);
  add(`${stars} ${rarity.toUpperCase()} ${species.toUpperCase()}`);

  const mods = [];
  if (shiny) mods.push('\u2728 SHINY \u2728');
  if (hat && hat !== 'none') { const hi = HAT_EMOJI[hat] || ''; mods.push(hi ? `${hi} ${hat}` : hat); }
  if (mods.length) add(mods.join('  '));

  const art = SPECIES_ART[species] || SPECIES_ART.blob;
  if (art) for (const l of art) add(l.replace(/\{e\}/g, eye));

  blank(); add(name);

  if (personality) {
    blank();
    const wrapped = wrapText(personality, W - 2).slice(0, 5);
    for (let i = 0; i < wrapped.length; i++) {
      const pfx = i === 0 ? '\u201c' : ' ';
      const isLast = i === Math.min(4, wrapped.length - 1);
      const sfx = isLast ? (wrapped.length > 5 ? '\u2026\u201d' : '\u201d') : '';
      add(`${pfx}${wrapped[i]}${sfx}`);
    }
  }

  if (maxHp > 0) {
    blank();
    add(`HP  ${statBar(currentHp, maxHp, 10)}  ${formatNumber(currentHp)} / ${formatNumber(maxHp)}`);
    add(`MP  ${statBar(currentMp, Math.max(maxMp, 1), 10)}  ${formatNumber(currentMp)} / ${formatNumber(maxMp)}`);
  }

  if (Object.keys(baseStats).length) {
    blank();
    for (const k of SOUL_STAT_ORDER) add(`${k.padEnd(10)} ${statBar(baseStats[k] || 0, 100, 10)}  ${String(baseStats[k] || 0).padStart(3)}`);
  }

  if (minAtk > 0) add(`ATK: ${formatNumber(minAtk)} \u2014 ${formatNumber(maxAtk)}`);

  if (Object.keys(rpgStats).length) {
    blank();
    for (const k of STAT_DISPLAY_ORDER) {
      const v = rpgStats[k] || 0;
      add(`${(STAT_FULL_NAMES[k] || k.toUpperCase()).padEnd(10)} ${statBar(v, 999, 10)} ${String(v).padStart(4)}`);
    }
  }

  blank();
  add(`XP: ${formatNumber(totalXp)} \u2192 Lv.${level + 1}  (${levelPct.toFixed(1)}%)`);
  add(`Streak: \u{1f525} ${streak} days`);
  add(`Tokens: ${formatNumber(totalTokens)} generated`);
  add(`Sessions: ${totalSessions} (${formatTime(sessionTime)})`);

  const hasRecent = (recentEvents && recentEvents.length) || unreadMessages > 0;
  if (hasRecent) {
    blank(); add('Recent:');
    if (recentEvents) for (const ev of recentEvents.slice(0, 5)) add(`  ${ev}`);
    if (unreadMessages > 0) add(`  \u{1f4e8} ${unreadMessages} unread message${unreadMessages !== 1 ? 's' : ''}`);
  }

  blank();
  lines.push(`\u2570${'\u2500'.repeat(W + 4)}\u256f`);
  console.log(lines.join('\n'));
}

// ---------------------------------------------------------------------------
// CLI dispatch
// ---------------------------------------------------------------------------

const COMMANDS = {
  rename: (args) => cmdRename(args.join(' ') || null),
  description: (args) => cmdDescription(args.length ? args.join(' ') : null),
  status: () => cmdStatus(),
  browser: () => cmdBrowser(),
  delete: () => cmdDelete(),
  attack: (args) => cmdAttack(args.join(' ') || null),
  send_message: (args) => cmdSendMessage(args.join(' ') || null),
  messages: () => cmdMessages(),
  read_message: () => cmdReadMessage(),
};

async function main() {
  const cmd = process.argv[2];
  if (!cmd || !COMMANDS[cmd]) {
    console.log(`Usage: commands.js <command> [args...]`);
    console.log(`Commands: ${Object.keys(COMMANDS).join(', ')}`);
    process.exit(1);
  }
  await COMMANDS[cmd](process.argv.slice(3));
}

main().catch((err) => { console.log('Error: ' + err.message); process.exit(1); });
