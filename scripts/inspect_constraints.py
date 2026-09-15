"""DB 스키마 조회 도구. 마이그레이션 전후 제약/컬럼 검증용."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import connect  # noqa: E402


def main() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'review.ontology_candidate'::regclass
                  AND contype = 'c'
                """
            )
            print("=== CHECK constraints ===")
            for row in cur.fetchall():
                print(row)

            cur.execute(
                """
                SELECT column_name, data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'review'
                  AND table_name = 'ontology_candidate'
                ORDER BY ordinal_position
                """
            )
            print("\n=== columns ===")
            for row in cur.fetchall():
                print(row)


if __name__ == "__main__":
    main()