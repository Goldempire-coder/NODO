from __future__ import annotations


def insert_credit_purchase_proof_file_pg(
    conn,
    *,
    owner_user_id: str,
    purchase_id: str,
    storage_path: str,
    mime_type: str,
    size_bytes: int,
):  # type: ignore[no-untyped-def]
    return conn.execute(
        """
        insert into file_assets (
            owner_user_id, resource_type, resource_id, file_type, storage_path,
            mime_type, size_bytes, created_at
        )
        values (%s, 'credit_purchase', %s, 'credit_purchase_proof', %s, %s, %s, now())
        returning *
        """,
        (owner_user_id, purchase_id, storage_path, mime_type, size_bytes),
    ).fetchone()
