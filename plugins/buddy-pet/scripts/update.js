#!/usr/bin/env node
/**
 * Self-update script for buddy-pet plugin.
 * Checks if a newer version is available before reinstalling.
 */
'use strict';

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function run(args) {
  return execFileSync('claude', args, { encoding: 'utf8', timeout: 120000 }).trim();
}

function getCurrentVersion() {
  try {
    return require(path.join(__dirname, 'common.js')).PLUGIN_VERSION || 'unknown';
  } catch {
    return 'unknown';
  }
}

function getRemoteVersion() {
  // Update marketplace to get latest
  try { run(['plugins', 'marketplace', 'update', 'kolindes-claude-plugins']); } catch {}

  // Read version from the freshly cloned marketplace
  const marketDir = path.join(require('os').homedir(), '.claude', 'plugins', 'marketplaces', 'kolindes-claude-plugins');
  try {
    const pluginJson = JSON.parse(fs.readFileSync(path.join(marketDir, 'plugins', 'buddy-pet', '.claude-plugin', 'plugin.json'), 'utf8'));
    return pluginJson.version || 'unknown';
  } catch {
    return 'unknown';
  }
}

const current = getCurrentVersion();
console.log(`Current version: ${current}`);

const remote = getRemoteVersion();
console.log(`Latest version:  ${remote}`);

if (current === remote) {
  console.log('\nAlready up to date.');
  process.exit(0);
}

console.log(`\nUpdating ${current} -> ${remote}...`);
try {
  run(['plugins', 'uninstall', 'buddy-pet']);
  run(['plugins', 'install', 'buddy-pet']);
  console.log(`\nUpdated to ${remote}. Run /reload-plugins to apply.`);
} catch (err) {
  console.log(`Error: ${err.message}`);
  process.exit(1);
}
