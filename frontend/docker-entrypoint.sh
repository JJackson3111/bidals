#!/bin/sh
set -e

if [ -f package-lock.json ]; then
  expected_hash="$(sha256sum package-lock.json | cut -d " " -f1)"
  actual_hash=""

  if [ -f node_modules/.bidals-package-lock.sha256 ]; then
    actual_hash="$(cat node_modules/.bidals-package-lock.sha256)"
  fi

  if [ ! -x node_modules/.bin/next ] || [ "$actual_hash" != "$expected_hash" ]; then
    echo "Installing frontend dependencies from package-lock.json..."
    npm ci
    printf "%s" "$expected_hash" > node_modules/.bidals-package-lock.sha256
  fi
fi

exec "$@"
