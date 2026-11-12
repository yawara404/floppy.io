"""floppy.io — 投稿の整形 / いいね"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from .db import fetch_all, fetch_one
from .utils.avatars import icon_url
from .utils.uploads import floppy_kind, upload_url

POST_COLUMNS = """p.id,
  p.user_id,
  p.reply_to_id,
  p.disk_id,
  u.username,
  u.display_name,
  u.avatar_path,
  u.icon_pixel,
  u.allow_replies AS author_allow_replies,
  p.text,
  p.pixel_data,
  p.pixel_width,
  p.pixel_height,
  p.image_path,
  p.image_mime,
  p.image_bytes,
  p.image_width,
  p.image_height,
  p.youtube_id,
  p.youtube_title,
  p.youtube_thumbnail,
  p.floppy_path,
  p.floppy_name,
  p.floppy_bytes,
  p.text_bytes,
  p.pixel_bytes,
  p.total_bytes,
  p.created_at"""


BOT_USERNAMES = {"hagumeta", "heisei_vipper", "adachi_rei", "nyanpuppu3", "nyanpuppu"}


def is_bot_username(username: str | None) -> bool:
    if not username:
        return False
    u = username.lower()
    return u in BOT_USERNAMES or u.startswith("nyanpuppu")


def with_media(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return row
    result = dict(row)
    result["is_bot"] = is_bot_username(str(result.get("username") or ""))
    result["image_url"] = upload_url(row.get("image_path"))
    result["floppy_url"] = upload_url(row.get("floppy_path"))
    result["floppy_kind"] = (
        floppy_kind(row["floppy_name"]) if row.get("floppy_name") else None
    )

    # 投稿者のアイコン URL。プロフィールの 32×32 アイコン → アップロード画像 →
    # 最新の正方形ドット絵、の順で /api/icon/<username>.svg が解決する。
    result["author_avatar_url"] = upload_url(row.get("avatar_path"))
    result["author_icon_url"] = icon_url(
        row["username"], row.get("icon_pixel"), row.get("avatar_path")
    )
    result.pop("avatar_path", None)
    result.pop("icon_pixel", None)

    # 返信の受け付け設定（投稿者本人の設定）。既定はオフ＝返信できない。
    result["replies_enabled"] = bool(int(row.get("author_allow_replies") or 0))
    result.pop("author_allow_replies", None)
    result["reply_to_id"] = (
        int(row["reply_to_id"]) if row.get("reply_to_id") else None
    )
    result["disk_id"] = int(row["disk_id"]) if row.get("disk_id") else None
    result["pixel_width"] = int(row.get("pixel_width") or 16)
    result["pixel_height"] = int(row.get("pixel_height") or 16)
    return result


def attach_likes(
    posts: list[dict[str, Any]], user: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    if not posts:
        return posts

    ids = [int(post["id"]) for post in posts]
    placeholders = ",".join(["%s"] * len(ids))

    counts = {
        int(row["post_id"]): int(row["c"])
        for row in fetch_all(
            f"""SELECT post_id, COUNT(*) AS c
                  FROM likes
                 WHERE post_id IN ({placeholders})
                 GROUP BY post_id""",
            tuple(ids),
        )
    }

    liked: set[int] = set()
    if user:
        liked = {
            int(row["post_id"])
            for row in fetch_all(
                f"""SELECT post_id FROM likes
                     WHERE user_id = %s AND post_id IN ({placeholders})""",
                (int(user["id"]), *ids),
            )
        }

    for post in posts:
        post_id = int(post["id"])
        post["like_count"] = counts.get(post_id, 0)
        post["liked"] = post_id in liked

    return posts


def attach_reply_counts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """各投稿に、その投稿をルートとする返信の件数を付ける"""
    if not posts:
        return posts

    ids = [int(post["id"]) for post in posts]
    placeholders = ",".join(["%s"] * len(ids))

    counts = {
        int(row["reply_to_id"]): int(row["c"])
        for row in fetch_all(
            f"""SELECT reply_to_id, COUNT(*) AS c
                  FROM posts
                 WHERE reply_to_id IN ({placeholders})
                 GROUP BY reply_to_id""",
            tuple(ids),
        )
    }

    for post in posts:
        post["reply_count"] = counts.get(int(post["id"]), 0)

    return posts


def like_count(post_id: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM likes WHERE post_id = %s", (post_id,)
    )
    return int(row["c"]) if row else 0


def attach_reposts(
    posts: list[dict[str, Any]], user: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """各投稿にリポスト数と「自分がリポスト済みか」を付ける (attach_likes と同型)"""
    if not posts:
        return posts

    ids = sorted({int(post["id"]) for post in posts})
    placeholders = ",".join(["%s"] * len(ids))

    counts = {
        int(row["post_id"]): int(row["c"])
        for row in fetch_all(
            f"""SELECT post_id, COUNT(*) AS c
                  FROM reposts
                 WHERE post_id IN ({placeholders})
                 GROUP BY post_id""",
            tuple(ids),
        )
    }

    mine: set[int] = set()
    if user:
        mine = {
            int(row["post_id"])
            for row in fetch_all(
                f"""SELECT post_id FROM reposts
                     WHERE user_id = %s AND post_id IN ({placeholders})""",
                (int(user["id"]), *ids),
            )
        }

    for post in posts:
        post_id = int(post["id"])
        post["repost_count"] = counts.get(post_id, 0)
        post["reposted"] = post_id in mine

    return posts


def repost_count(post_id: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM reposts WHERE post_id = %s", (post_id,)
    )
    return int(row["c"]) if row else 0


def merge_repost_items(
    posts: list[dict[str, Any]],
    repost_items: list[dict[str, Any]],
    limit: int = 200,
) -> list[dict[str, Any]]:
    """時系列 TL 用: 通常投稿とリポスト表示を時刻降順に混ぜる。

    通常投稿は created_at、リポスト表示は timeline_at (リポスト時刻) で並べる。
    日時は "YYYY-MM-DD HH:MM:SS" 文字列なので辞書順 = 時刻順になる。
    """

    def at(post: dict[str, Any]) -> str:
        return str(post.get("timeline_at") or post.get("created_at") or "")

    return sorted([*posts, *repost_items], key=at, reverse=True)[:limit]


# ---------------------------------------------------------------------------
# おすすめタイムライン (feed=recommended)
#
# デフォルト TL 専用の並べ替え。フォロー中・検索・ディスク・プロフィールは
# これまで通り時系列 (掲示板式) のまま。
# 方針: 新しさ × 反応 (いいね/返信) でスコア付けし、人間と bot を不規則に
# 混ぜる (上限: bot が人間を超えない)。人間がいる限り半分以上は人間になる。
# ---------------------------------------------------------------------------

RECOMMENDED_BOT_FACTOR = 0.22  # bot 投稿のスコア倍率
RECOMMENDED_HALF_LIFE_HOURS = 18.0  # 新しさの半減期


def _created_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
    return None


def recommended_score(post: dict[str, Any], now: datetime | None = None) -> float:
    now = now or datetime.now()
    created = _created_at(post.get("created_at"))
    if created is None:
        recency = 0.5
    else:
        age_hours = max(0.0, (now - created).total_seconds() / 3600.0)
        recency = 0.5 ** (age_hours / RECOMMENDED_HALF_LIFE_HOURS)
    engagement = 1.0 + 2.0 * int(post.get("like_count") or 0) + 3.0 * int(
        post.get("reply_count") or 0
    )
    # 古くても反応のある投稿が少し浮くよう、減衰には下限を付ける
    score = engagement * (0.35 + 0.65 * recency)
    if post.get("is_bot"):
        score *= RECOMMENDED_BOT_FACTOR
    # 読み込むたびに少し並びが変わるよう、弱いランダム要素を混ぜる
    # (bot の割引が jitter の最大幅でも逆転しない範囲に収めている)
    score *= random.uniform(0.85, 1.18)
    return score


def rank_recommended(
    posts: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    """おすすめ順に並べ替える。like_count / reply_count / is_bot が付いた投稿用。

    人間と bot を別々にスコア順に並べ、不規則に混ぜる。ただし「その時点までの
    bot 数が人間数を超えない」という上限だけは守るので、人間の投稿がある限り
    タイムラインの半分以上は人間になる (間隔はランダムで、規則的な交互には
    ならない)。人間が尽きたら残りの bot を、bot が尽きたら残りの人間を続ける。
    """
    now = now or datetime.now()
    scored = sorted(
        posts,
        key=lambda p: (recommended_score(p, now), int(p.get("id") or 0)),
        reverse=True,
    )
    humans = [p for p in scored if not p.get("is_bot")]
    bots = [p for p in scored if p.get("is_bot")]

    result: list[dict[str, Any]] = []
    hi = bi = 0  # 取り出した人間 / bot の数
    while hi < len(humans) and bi < len(bots):
        deficit = hi - bi  # bot が人間より遅れている数 (0 のときは bot 不可)
        if deficit <= 0:
            pick_bot = False
        else:
            # 遅れが大きいほど bot を挟む確率を上げる (最大 0.8)
            pick_bot = random.random() < min(0.35 + 0.15 * deficit, 0.8)
        if pick_bot:
            result.append(bots[bi])
            bi += 1
        else:
            result.append(humans[hi])
            hi += 1
    result.extend(humans[hi:])
    result.extend(bots[bi:])
    return result
