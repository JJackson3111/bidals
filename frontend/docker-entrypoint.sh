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

if [ "${BIDALS_DOCKER_DEV:-}" = "1" ]; then
  is_build_command=0
  if [ "${1:-}" = "npm" ] && [ "${2:-}" = "run" ] && [ "${3:-}" = "build" ]; then
    is_build_command=1
  elif [ "${1:-}" = "npx" ] && [ "${2:-}" = "next" ] && [ "${3:-}" = "build" ]; then
    is_build_command=1
  elif [ "${1:-}" = "next" ] && [ "${2:-}" = "build" ]; then
    is_build_command=1
  fi

  if [ "$is_build_command" = "1" ]; then
    export NODE_ENV=production
    export NEXT_DIST_DIR="${NEXT_DIST_DIR:-.next-build}"
    echo "Using ${NEXT_DIST_DIR} for this one-off build so the dev .next volume remains untouched."

    backup_dir="$(mktemp -d)"
    for generated_file in next-env.d.ts tsconfig.json; do
      if [ -f "$generated_file" ]; then
        cp "$generated_file" "$backup_dir/$generated_file"
      fi
    done

    "$@"
    status="$?"

    for generated_file in next-env.d.ts tsconfig.json; do
      if [ -f "$backup_dir/$generated_file" ]; then
        cp "$backup_dir/$generated_file" "$generated_file"
      fi
    done
    rm -rf "$backup_dir"
    exit "$status"
  fi
fi

exec "$@"
