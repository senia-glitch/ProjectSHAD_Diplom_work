#!/usr/bin/env sh
# Развёртывание SHAD на Linux-сервере с Docker Engine и Compose v2. Запуск из корня проекта:
#   sh deploy/deploy.sh init      создать .env.production с новыми секретами (существующий не меняется)
#   sh deploy/deploy.sh up        собрать и запустить (миграции применяются отдельным сервисом migrate)
#   sh deploy/deploy.sh update    git pull и перезапуск с пересборкой
#   sh deploy/deploy.sh admin LOGIN EMAIL   создать администратора (пароль вводится скрытно)
#   sh deploy/deploy.sh backup    резервная копия БД в backups/
#   sh deploy/deploy.sh restore FILE        восстановить БД из копии (останавливает приложение)
#   sh deploy/deploy.sh logs | ps | down
# Профиль HTTPS (Caddy) включается, если в .env.production задан SHAD_DOMAIN.
set -eu

cd "$(dirname "$0")/.."
ENV_FILE=.env.production

setting() { sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1; }

compose() {
  [ -f "$ENV_FILE" ] || { echo "Нет $ENV_FILE: выполните sh deploy/deploy.sh init" >&2; exit 1; }
  if [ -n "$(setting SHAD_DOMAIN)" ]; then set -- --profile https "$@"; fi
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.prod.yml "$@"
}

secret() { od -An -N32 -tx1 /dev/urandom | tr -d ' \n'; }

init() {
  if [ -f "$ENV_FILE" ]; then echo "$ENV_FILE уже есть, оставлен без изменений"; return; fi
  umask 077
  sed -e "s/^POSTGRES_PASSWORD=__GENERATE__/POSTGRES_PASSWORD=$(secret)/" \
      -e "s/^CORE_JWT_SECRET=__GENERATE__/CORE_JWT_SECRET=$(secret)/" .env.production.example > "$ENV_FILE"
  echo "Создан $ENV_FILE (права 600). Задайте SHAD_DOMAIN (SHAD_TIMEZONE — только для переноса старых данных), затем: sh deploy/deploy.sh up"
}

up() {
  compose up -d --build --wait --wait-timeout 300
  compose ps
  if [ -n "$(setting SHAD_DOMAIN)" ]; then
    echo "Сайт: https://$(setting SHAD_DOMAIN)"
  else
    echo "Сайт: http://$(setting SHAD_BIND):$(setting SHAD_HTTP_PORT) (за вашим обратным прокси с HTTPS)"
  fi
}

backup() {
  mkdir -p backups
  file="backups/shad-$(date +%Y%m%d-%H%M%S).sql.gz"
  compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip > "$file"
  echo "Копия БД: $file"
}

restore() {
  file="${1:?Укажите файл копии: sh deploy/deploy.sh restore backups/....sql.gz}"
  [ -f "$file" ] || { echo "Нет файла $file" >&2; exit 1; }
  printf 'Текущие данные БД будут заменены копией %s. Продолжить? [yes/N] ' "$file"
  read -r answer
  [ "$answer" = "yes" ] || { echo "Отменено"; exit 1; }
  compose stop app web
  compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
  gunzip -c "$file" | compose exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
  up
}

command="${1:-help}"
[ $# -gt 0 ] && shift
case "$command" in
  init) init ;;
  up) up ;;
  update) git pull --ff-only && up ;;
  admin)
    [ $# -ge 2 ] || { echo "Использование: sh deploy/deploy.sh admin LOGIN EMAIL" >&2; exit 1; }
    compose run --rm migrate python -m scripts.create_admin --username "$1" --email "$2" ;;
  backup) backup ;;
  restore) restore "$@" ;;
  logs) compose logs -f --tail 200 "$@" ;;
  ps) compose ps ;;
  down) compose down ;;
  *) sed -n '2,10p' "$0" ;;
esac
