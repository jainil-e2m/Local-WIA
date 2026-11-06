"""Only confirmed publications enter the research/brief history contract."""


def confirmed(conn, angle_id):
    return [
        r["body"]
        for r in conn.execute(
            """
        SELECT jsonb_build_object('calendar_entry_id',ce.calendar_entry_id,
          'asset_id',ce.asset_id,'asset_content_hash',ce.asset_content_hash,
          'channel',ce.channel,'status',ce.status,'published_at',ce.published_at,
          'published_url',ce.published_url) AS body
        FROM calendar_entries ce JOIN content_assets ca USING(asset_id)
        JOIN content_briefs b USING(brief_id)
        WHERE b.angle_id=%s AND ce.status='published' AND ce.published_at IS NOT NULL
          AND ce.asset_content_hash=ca.content_hash
        ORDER BY ce.calendar_entry_id
    """,
            (angle_id,),
        )
    ]
