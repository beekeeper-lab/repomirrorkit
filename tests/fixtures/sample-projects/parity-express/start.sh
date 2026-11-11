#!/usr/bin/env bash
[ -d node_modules ] || npm install --no-audit --no-fund
exec node server.js
