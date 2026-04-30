#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_amazon_links.py
===================

docs/reference/ 配下の .rst に残る旧形式 Amazon アフィリエイト HTML
（`ws-fe.amazon-adsystem.com` 経由で画像を取得する、リンク切れの形式）
を、ASIN ベースの `images-na.ssl-images-amazon.com` 固定 URL 形式に
一括置換するための使い捨てスクリプト。

使い方::

    # 1ファイル単位での段階実行
    python fix_amazon_links.py docs/reference/「た」シリーズ.rst

    # ディレクトリ単位での一括実行
    python fix_amazon_links.py docs/reference

処理概要:

1. 対象ファイルから ``.. _書名: https://amzn.to/xxx`` の行を収集し、
   「書名 → 短縮URL」の辞書を構築する。
2. 旧形式 HTML 行 (``ws-fe.amazon-adsystem.com`` を含む行) を正規表現で
   検出し、以下の形式に置換する:

   - ``href``: 書名が辞書にヒットすれば ``https://amzn.to/xxx``、
     未ヒットなら
     ``https://www.amazon.co.jp/dp/<ASIN>?tag=takaoutputblo-22&language=ja_JP``
   - ``img src``:
     ``https://images-na.ssl-images-amazon.com/images/P/<ASIN>.09._SCLZZZZZZZ_.jpg``
     (``width="75"`` 付き)
   - 末尾のトラッキングピクセル (``ir-jp.amazon-adsystem.com``) は削除。

3. ASIN が ``B`` で始まる (Kindle / 電子商品等) 場合は上記固定画像 URL
   では表示されない可能性が高いため、後日の目視修正候補として警告ログ
   に記録する。未ヒット書名も同様にログ記録する。

ログは ``fix_amazon_links_YYYYMMDD_HHMMSS.log`` (UTF-8) として
ワークスペース直下に出力される。``.gitignore`` でコミット対象外。
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

AFFILIATE_TAG = "takaoutputblo-22"

# 旧形式HTML行の検出用正規表現。
# <!--書名--><a href="...(/dp/|/gp/product/)ASIN..."...>
#   <img ... ws-fe.amazon-adsystem.com ...></a>
# [<img ... ir-jp.amazon-adsystem.com ... />]  ← トラッキングピクセル(任意)
OLD_LINE_RE = re.compile(
    r"""
    <!--(?P<title>.*?)-->                          # 書名コメント
    \s*
    <a\s+href="(?P<href>[^"]*?(?:/dp/|/gp/product/)(?P<asin>[0-9A-Z]{10})[^"]*?)"
       [^>]*>                                      # 開始 <a>
    \s*
    <img[^>]*ws-fe\.amazon-adsystem\.com[^>]*>     # 壊れた画像 <img>
    \s*
    </a>
    (?:[ \t]*<img[^>]*ir-jp\.amazon-adsystem\.com[^>]*/?>)?   # トラッキングピクセル(任意・同一行)
    """,
    re.VERBOSE,
)

# `.. _書名: https://amzn.to/xxx` 形式の rst ラベル行
AMZN_LABEL_RE = re.compile(
    r"^\.\.\s+_(?P<title>.+?):\s+(?P<url>https?://amzn\.to/\S+)\s*$"
)


# ---------------------------------------------------------------------------
# ロガー設定
# ---------------------------------------------------------------------------

def setup_logger(workspace_root: Path) -> tuple[logging.Logger, Path]:
    """タイムスタンプ付きログファイルを作成し、ロガーを返す。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = workspace_root / f"fix_amazon_links_{timestamp}.log"

    logger = logging.getLogger("fix_amazon_links")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # ファイルハンドラ (詳細)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    logger.addHandler(fh)

    # コンソールハンドラ (サマリのみ)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    return logger, log_path


# ---------------------------------------------------------------------------
# 置換ロジック
# ---------------------------------------------------------------------------

def collect_amzn_labels(text: str) -> dict[str, str]:
    """`.. _書名: https://amzn.to/xxx` を書名→URL辞書として収集。"""
    mapping: dict[str, str] = {}
    for line in text.splitlines():
        m = AMZN_LABEL_RE.match(line)
        if m:
            mapping[m.group("title").strip()] = m.group("url").strip()
    return mapping


def build_new_fragment(
    title: str,
    asin: str,
    amzn_short_url: str | None,
) -> str:
    """新形式の ``<!--書名--><a ...><img .../></a>`` 断片を組み立てる。"""
    if amzn_short_url:
        href = amzn_short_url
    else:
        href = (
            f"https://www.amazon.co.jp/dp/{asin}"
            f"?tag={AFFILIATE_TAG}&language=ja_JP"
        )
    img_src = (
        f"https://images-na.ssl-images-amazon.com/images/P/"
        f"{asin}.09._SCLZZZZZZZ_.jpg"
    )
    return (
        f'<!--{title}-->'
        f'<a href="{href}" target="_blank">'
        f'<img border="0" src="{img_src}" width="75"></a>'
    )


def process_file(
    path: Path,
    logger: logging.Logger,
    rel_display: str,
) -> tuple[int, list[tuple[str, str]], list[tuple[str, str]]]:
    """1 ファイルを処理する。

    Returns:
        (置換件数, 未ヒット書名リスト[(書名,ASIN)], Kindle系ASINリスト[(書名,ASIN)])
    """
    original = path.read_text(encoding="utf-8")
    amzn_map = collect_amzn_labels(original)

    unmatched_titles: list[tuple[str, str]] = []
    kindle_asins: list[tuple[str, str]] = []
    replace_count = 0

    def _repl(m: re.Match[str]) -> str:
        nonlocal replace_count
        title = m.group("title").strip()
        asin = m.group("asin")
        amzn_short = amzn_map.get(title)
        if amzn_short is None:
            unmatched_titles.append((title, asin))
            logger.warning(
                "[%s] amzn.to 短縮URL未ヒット: 書名=%r ASIN=%s → フォールバック URL を使用",
                rel_display, title, asin,
            )
        if asin.startswith("B"):
            kindle_asins.append((title, asin))
            logger.warning(
                "[%s] Kindle系ASIN(先頭B): 書名=%r ASIN=%s → "
                "images-na 固定画像URLでは表示されない可能性あり(要目視確認)",
                rel_display, title, asin,
            )
        replace_count += 1
        new_fragment = build_new_fragment(title, asin, amzn_short)
        logger.debug("[%s] 置換: 書名=%r ASIN=%s", rel_display, title, asin)
        return new_fragment

    new_text = OLD_LINE_RE.sub(_repl, original)

    if replace_count == 0:
        logger.info("[%s] 旧形式行なし。スキップ。", rel_display)
        return 0, unmatched_titles, kindle_asins

    if new_text == original:
        # 念のためのガード(通常はここに来ない)
        logger.info("[%s] 変更なし。スキップ。", rel_display)
        return 0, unmatched_titles, kindle_asins

    path.write_text(new_text, encoding="utf-8")
    logger.info("[%s] %d 件置換、保存完了。", rel_display, replace_count)
    return replace_count, unmatched_titles, kindle_asins


def iter_target_files(paths: list[Path]) -> list[Path]:
    """引数で与えられたパスから処理対象の .rst ファイルを列挙。"""
    targets: list[Path] = []
    for p in paths:
        if p.is_file():
            if p.suffix.lower() == ".rst":
                targets.append(p)
        elif p.is_dir():
            targets.extend(sorted(p.rglob("*.rst")))
        else:
            print(f"[警告] 存在しないパス: {p}", file=sys.stderr)
    return targets


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="旧形式 Amazon アフィリエイト HTML を一括修復します。"
    )
    parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="+",
        type=Path,
        help="処理対象の .rst ファイルまたはディレクトリ (複数指定可)",
    )
    args = parser.parse_args(argv)

    workspace_root = Path(__file__).resolve().parent
    logger, log_path = setup_logger(workspace_root)

    logger.info("=" * 60)
    logger.info("fix_amazon_links.py 実行開始")
    logger.info("ログファイル: %s", log_path)
    logger.info("対象指定: %s", [str(p) for p in args.paths])
    logger.info("=" * 60)

    targets = iter_target_files(args.paths)
    logger.info("処理対象ファイル数: %d", len(targets))

    total_replace = 0
    total_unmatched: list[tuple[str, str, str]] = []   # (file, title, asin)
    total_kindle: list[tuple[str, str, str]] = []       # (file, title, asin)
    changed_files = 0

    for path in targets:
        try:
            rel_display = path.relative_to(workspace_root).as_posix()
        except ValueError:
            rel_display = str(path)

        try:
            count, unmatched, kindle = process_file(path, logger, rel_display)
        except Exception as e:  # noqa: BLE001
            logger.error("[%s] 処理中にエラー: %s", rel_display, e)
            continue

        total_replace += count
        if count > 0:
            changed_files += 1
        for title, asin in unmatched:
            total_unmatched.append((rel_display, title, asin))
        for title, asin in kindle:
            total_kindle.append((rel_display, title, asin))

    # -------------------- サマリ --------------------
    logger.info("=" * 60)
    logger.info("処理完了サマリ")
    logger.info("  処理対象ファイル数 : %d", len(targets))
    logger.info("  変更されたファイル : %d", changed_files)
    logger.info("  置換した旧形式行数 : %d", total_replace)
    logger.info("  amzn.to 未ヒット数 : %d", len(total_unmatched))
    logger.info("  Kindle系ASIN警告数 : %d", len(total_kindle))
    logger.info("=" * 60)

    if total_unmatched:
        logger.info("--- amzn.to 短縮URL 未ヒット一覧 (フォールバックURL適用) ---")
        for fpath, title, asin in total_unmatched:
            logger.info("  [%s] 書名=%r ASIN=%s", fpath, title, asin)

    if total_kindle:
        logger.info("--- Kindle系ASIN一覧 (画像表示されない可能性、要目視確認) ---")
        for fpath, title, asin in total_kindle:
            logger.info("  [%s] 書名=%r ASIN=%s", fpath, title, asin)

    logger.info("ログファイル: %s", log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
