#!/usr/bin/env sh
# Executa todos os scripts do zero, em ordem. Para no primeiro erro.
# Uso: MYSQL="mysql -uroot -p -h127.0.0.1 -P3306" ./scripts/rodar_tudo.sh
set -e
MYSQL=${MYSQL:-"mysql -uroot -p"}
cd "$(dirname "$0")/../sql"
for f in 01_ddl.sql 02_dml.sql 03_views.sql 04_functions.sql 05_procedures.sql 06_triggers.sql; do
  echo ">> $f"
  $MYSQL --default-character-set=utf8mb4 < "$f"
done
echo "OK: banco bdr_api criado e carregado."
