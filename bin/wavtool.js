#!/usr/bin/env node
'use strict';
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PY_DIR = path.join(__dirname, '..', 'python');
const WV_HOME = path.join(os.homedir(), '.wavtool');
const VENV = path.join(WV_HOME, 'venv');
const VENV_PY = path.join(VENV, 'bin', 'python3');
const DEPS_MARKER = path.join(WV_HOME, 'deps-v3');
const VERSION = '2.1.0';

const HELP = `wavtool ${VERSION} - pack directories into WAV audio files

Usage:
  wavtool pack <dir> <out.wav>          Pack a directory into a WAV file
  wavtool pack <dir> <out.wav> --ultra  Higher-throughput format (96 kHz)
  wavtool rate [96000]                  Show or set the output device sample rate
  wavtool --version | --help

Options (pack):
  --no-compress     disable in-memory compression
  --padding <sec>   leading silence in seconds (default 10)

First run prepares a private Python environment (one-time, needs network).`;

function findPython() {
  const cands = ['python3', '/opt/homebrew/bin/python3', '/usr/local/bin/python3', '/usr/bin/python3'];
  for (const c of cands) {
    const r = spawnSync(c, ['-c', 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'], { encoding: 'utf8' });
    if (!r.error && r.status === 0) return c;
  }
  return null;
}

function ensureEnv() {
  if (fs.existsSync(VENV_PY) && fs.existsSync(DEPS_MARKER)) return;
  const sys = findPython();
  if (!sys) {
    console.error('[wavtool] Python 3.10+ not found. Install it first:');
    console.error('  macOS:  xcode-select --install    (or: brew install python3)');
    process.exit(1);
  }
  console.log('[wavtool] preparing private Python environment (one-time, needs network)...');
  fs.mkdirSync(WV_HOME, { recursive: true });
  if (!fs.existsSync(VENV_PY)) {
    const r0 = spawnSync(sys, ['-m', 'venv', VENV], { stdio: 'inherit' });
    if (r0.status !== 0) { console.error('[wavtool] failed to create venv'); process.exit(1); }
  }
  const env = Object.assign({}, process.env, { PIP_NO_CACHE_DIR: '1' });
  const r = spawnSync(VENV_PY, ['-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '--no-cache-dir', 'numpy', 'reedsolo', 'zstandard'],
    { stdio: 'inherit', env });
  if (r.status !== 0) { console.error('[wavtool] failed to install dependencies (network needed)'); process.exit(1); }
  fs.writeFileSync(DEPS_MARKER, 'numpy reedsolo zstandard\n');
  console.log('[wavtool] ready.');
}

const argv = process.argv.slice(2);
const cmd = argv[0];
if (!cmd || cmd === 'help' || cmd === '--help' || cmd === '-h') { console.log(HELP); process.exit(cmd ? 0 : 2); }
if (cmd === '--version' || cmd === '-v') { console.log(VERSION); process.exit(0); }
if (cmd === 'pack' || cmd === 'rate') {
  if (cmd === 'pack' && argv.length < 3) { console.log(HELP); process.exit(2); }
  ensureEnv();
  const r = spawnSync(VENV_PY, [path.join(PY_DIR, 'dispatch.py')].concat(argv), { stdio: 'inherit' });
  process.exit(r.status === null ? 1 : r.status);
}
console.error('unknown command: ' + cmd);
console.log(HELP);
process.exit(2);
