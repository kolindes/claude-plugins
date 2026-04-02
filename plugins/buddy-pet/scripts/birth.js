#!/usr/bin/env node
/**
 * Birth script for buddy-pet plugin.
 * Registers a new buddy on the social network.
 */
'use strict';

const common = require('./common');

async function main() {
  const config = common.loadConfig();
  if (config && config.buddy_token) {
    console.log(`Already registered. Buddy ID: ${config.buddy_id}`);
    process.exit(0);
  }

  const companion = common.readCompanionData();
  if (!companion) {
    console.log('No companion found in ~/.claude.json. Start a Claude Code session first.');
    process.exit(1);
  }

  const userId = common.getUserId();
  if (userId === 'anon') {
    console.log('Cannot determine user ID. Log in to Claude Code first.');
    process.exit(1);
  }

  const userHash = common.computeUserHash(userId);
  const instanceId = common.computeInstanceId();

  const birthData = {
    user_hash: userHash,
    instance_id: instanceId,
    companion: {
      name: companion.name,
      personality: companion.personality,
      hatched_at: companion.hatched_at,
      species: companion.species,
      rarity: companion.rarity,
      eye: companion.eye,
      hat: companion.hat,
      shiny: companion.shiny,
      base_stats: companion.base_stats,
    },
    plugin_version: common.PLUGIN_VERSION,
  };

  const [status, resp] = await common.httpPost('/guild/buddy/birth', birthData);

  if (status === 200 || status === 201) {
    const token = resp.buddy_token;
    const buddyId = resp.buddy_id;
    common.saveConfig({
      buddy_token: token,
      buddy_id: buddyId,
      api_url: common.getApiUrl(),
    });
    const name = resp.buddy && resp.buddy.name || companion.name;
    console.log(`\u2728 ${name} is born! ID: ${buddyId}`);
  } else {
    const err = resp.error;
    const msg = typeof err === 'object' ? (err.message || err.code || JSON.stringify(err)) : String(err || `HTTP ${status}`);
    console.log(`Error: ${msg}`);
    process.exit(1);
  }
}

main().catch((err) => { console.log('Error: ' + err.message); process.exit(1); });
