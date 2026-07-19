#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review.py — 基于 SM-2 算法的自适应复习系统（P0 + P1 最小可用版）

P0: 真自适应 — 每次复习打分（0-3），用 SM-2 算法动态调整间隔
P1: 显式追踪 — 用 `review` 命令，不用文件 mtime（防 typo 误判）

设计原则：
- 0 外部依赖（纯 Python 标准库）
- 数据透明（JSON，单文件）
- 显式优于隐式（必须主动 add / review）
- 默认在仓库根的 review_data.json 存储
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ============================================================================
# 常量
# ============================================================================

DATA_FILE = Path(__file__).parent / "review_data.json"

# SM-2 算法参数
INITIAL_EF = 2.5        # 初始 easiness factor
MIN_EF = 1.3            # 最小 EF（低于此难度不再下调）
MIN_INTERVAL = 1        # 最小间隔（天）
GRADUATE_REPS = 3       # 连续成功 3 次后进入"已掌握"候选

# 用户打分（0-3）→ SM-2 quality（0-5）映射
# 0 = 完全忘了；1 = 吃力记住；2 = 想了一会儿；3 = 秒答
SCORE_TO_QUALITY = {
    0: 1,   # 失败
    1: 3,   # 吃力
    2: 4,   # 还可以
    3: 5,   # 完美
}

# Leech 阈值：连续失败 3 次标记为 leech
LEECH_FAIL_THRESHOLD = 3


# ============================================================================
# 数据模型
# ============================================================================

def load_data() -> dict:
    """加载数据文件，不存在则返回空结构。"""
    if not DATA_FILE.exists():
        return {"items": {}, "meta": {"version": 1, "created": today_str()}}
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    """保存数据到文件。"""
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# SM-2 算法
# ============================================================================

def sm2_update(
    ef: float,
    interval: int,
    reps: int,
    score: int,
) -> tuple[float, int, int, int]:
    """SM-2 算法核心。

    Args:
        ef: 当前 easiness factor
        interval: 当前间隔（天）
        reps: 连续成功次数
        score: 本次复习打分（0-3）

    Returns:
        (new_ef, new_interval, new_reps, total_fail_count)
        total_fail_count 用来触发 leech 检测（在 caller 端处理）
    """
    q = SCORE_TO_QUALITY[score]

    # 1) 更新 EF（对所有打分都生效）
    new_ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = max(MIN_EF, new_ef)

    # 2) 决定 interval 和 reps
    if q < 3:
        # 失败：重置 reps，interval 回到 1 天
        new_reps = 0
        new_interval = 1
    else:
        # 成功
        new_reps = reps + 1
        if new_reps == 1:
            new_interval = 1
        elif new_reps == 2:
            new_interval = 6
        else:
            new_interval = max(MIN_INTERVAL, round(interval * new_ef))

    return new_ef, new_interval, new_reps, 0  # fail_count 由 caller 算


# ============================================================================
# 命令实现
# ============================================================================

def cmd_add(args) -> int:
    """添加新条目。"""
    data = load_data()
    item_id = args.id

    if item_id in data["items"]:
        print(f"❌ 条目 {item_id} 已存在（用 'show {item_id}' 查看）")
        return 1

    item = {
        "id": item_id,
        "title": args.title,
        "file": args.file or "",
        "difficulty_hint": args.difficulty,  # 1/2/3，仅作初始参考
        "ef": INITIAL_EF,
        "interval": 0,
        "reps": 0,
        "fail_streak": 0,        # 连续失败次数
        "total_reviews": 0,
        "total_failures": 0,
        "is_leech": False,
        "is_mastered": False,
        "added_date": today_str(),
        "last_review": None,
        "next_due": today_str(),  # 立即到期
        "history": [],
    }
    data["items"][item_id] = item
    save_data(data)
    print(f"✅ 已添加: [{item_id}] {args.title}")
    print(f"   文件: {args.file or '(无)'}")
    print(f"   初始难度提示: {args.difficulty}/3（首次复习后会按表现调整）")
    return 0


def cmd_list(args) -> int:
    """列出所有条目。"""
    data = load_data()
    items = data["items"]

    if not items:
        print("📭 还没有任何条目。用 'add' 添加。")
        return 0

    print(f"{'ID':<25} {'标题':<35} {'到期':<12} {'EF':<5} {'复习':<5} {'状态':<8}")
    print("-" * 95)

    today = today_str()
    for item_id, item in sorted(items.items()):
        status = []
        if item["is_leech"]:
            status.append("🩹leech")
        if item["is_mastered"]:
            status.append("🎓mastered")
        if item["next_due"] <= today and not item["is_mastered"]:
            status.append("⏰due")
        status_str = ",".join(status) if status else "-"

        due_marker = "⚠️ " if item["next_due"] <= today else "  "
        print(
            f"{item_id:<25} {item['title'][:33]:<35} "
            f"{due_marker}{item['next_due']:<10} {item['ef']:<5.2f} "
            f"{item['total_reviews']:<5} {status_str:<8}"
        )
    return 0


def cmd_due(args) -> int:
    """显示今日应复习的条目。"""
    data = load_data()
    today = today_str()

    due_items = [
        item for item in data["items"].values()
        if item["next_due"] <= today and not item["is_mastered"]
    ]

    if not due_items:
        print("🎉 今天没有需要复习的！")
        return 0

    print(f"📚 今日应复习 {len(due_items)} 项：\n")
    for item in sorted(due_items, key=lambda x: x["next_due"]):
        marker = "🩹" if item["is_leech"] else "  "
        overdue_days = (
            (datetime.now() - datetime.strptime(item["next_due"], "%Y-%m-%d")).days
        )
        overdue_str = f"（逾期 {overdue_days} 天）" if overdue_days > 0 else "（今天）"
        print(
            f"{marker} [{item['id']}] {item['title']}\n"
            f"   复习次数: {item['total_reviews']} | "
            f"EF: {item['ef']:.2f} | "
            f"下次原定: {item['next_due']} {overdue_str}\n"
        )
    return 0


def cmd_review(args) -> int:
    """复习一个条目（核心命令：记录打分 + 触发 SM-2）。"""
    data = load_data()
    item_id = args.id

    if item_id not in data["items"]:
        print(f"❌ 条目 {item_id} 不存在")
        return 1

    item = data["items"][item_id]

    if item["is_mastered"]:
        print(f"🎓 [{item_id}] 已标记为 mastered。强制复习请加 --force")
        if not args.force:
            return 0

    # 显示条目信息
    print(f"\n📖 复习: [{item_id}] {item['title']}")
    if item["file"]:
        print(f"   文件: {item['file']}")
    print(
        f"   当前: 复习 {item['total_reviews']} 次 | "
        f"EF {item['ef']:.2f} | "
        f"间隔 {item['interval']} 天 | "
        f"连续成功 {item['reps']} 次"
    )
    if item["is_leech"]:
        print("   ⚠️  这是个 leech（多次失败）")
    print()

    # 读取打分
    if args.score is not None:
        # 命令行直接给
        score = args.score
    else:
        # 交互式
        try:
            score_input = input(
                "打分 (0=忘了 1=吃力 2=还可以 3=秒答, q=退出): "
            ).strip()
            if score_input == "q":
                print("已取消")
                return 0
            score = int(score_input)
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return 130
        except ValueError:
            print("❌ 必须是 0/1/2/3 或 q")
            return 1

    if score not in (0, 1, 2, 3):
        print("❌ 分数必须是 0/1/2/3")
        return 1

    # 跑 SM-2
    new_ef, new_interval, new_reps, _ = sm2_update(
        ef=item["ef"],
        interval=item["interval"],
        reps=item["reps"],
        score=score,
    )

    # 更新元数据
    item["ef"] = round(new_ef, 2)
    item["interval"] = new_interval
    item["reps"] = new_reps
    item["total_reviews"] += 1

    # 失败处理
    if score == 0:
        item["fail_streak"] += 1
        item["total_failures"] += 1
        if item["fail_streak"] >= LEECH_FAIL_THRESHOLD:
            if not item["is_leech"]:
                print(f"   🩹 标记为 leech（连续失败 {item['fail_streak']} 次）")
            item["is_leech"] = True
    else:
        item["fail_streak"] = 0
        # 检查是否可以"毕业"
        if new_reps >= GRADUATE_REPS and new_ef >= 2.5:
            if not item["is_mastered"]:
                print(f"   🎓 标记为 mastered（连续成功 {new_reps} 次，EF {new_ef:.2f}）")
            item["is_mastered"] = True
        else:
            item["is_mastered"] = False

    # 记录 history
    item["last_review"] = now_str()
    next_due_date = datetime.now() + timedelta(days=new_interval)
    item["next_due"] = next_due_date.strftime("%Y-%m-%d")
    item["history"].append({
        "date": now_str(),
        "score": score,
        "ef": item["ef"],
        "interval": new_interval,
        "next_due": item["next_due"],
    })

    save_data(data)

    # 反馈
    score_emoji = {0: "😢", 1: "😅", 2: "🙂", 3: "🎉"}[score]
    print(
        f"\n{score_emoji} 记录完成: 分数 {score} | "
        f"EF {item['ef']:.2f} | "
        f"间隔 {new_interval} 天 | "
        f"下次复习 {item['next_due']}"
    )
    return 0


def cmd_show(args) -> int:
    """显示条目详情。"""
    data = load_data()
    item_id = args.id

    if item_id not in data["items"]:
        print(f"❌ 条目 {item_id} 不存在")
        return 1

    item = data["items"][item_id]
    print(f"\n📋 [{item_id}] {item['title']}")
    print(f"   文件: {item['file'] or '(无)'}")
    print(f"   初始难度: {item['difficulty_hint']}/3")
    print(f"   添加日期: {item['added_date']}")
    print(f"   状态: " + (
        "🎓 mastered" if item["is_mastered"]
        else "🩹 leech" if item["is_leech"]
        else "📚 学习中"
    ))
    print(f"   复习总次数: {item['total_reviews']}（失败 {item['total_failures']}）")
    print(f"   连续成功: {item['reps']} | 连续失败: {item['fail_streak']}")
    print(f"   EF: {item['ef']:.2f} | 当前间隔: {item['interval']} 天")
    print(f"   上次复习: {item['last_review'] or '(从未)'}")
    print(f"   下次到期: {item['next_due']}")

    if item["history"]:
        print(f"\n   📜 复习历史（最近 10 次）:")
        for h in item["history"][-10:]:
            print(
                f"      {h['date']} | 分 {h['score']} | "
                f"EF {h['ef']:.2f} | 间隔 {h['interval']}d | "
                f"下次 {h['next_due']}"
            )
    return 0


def cmd_stats(args) -> int:
    """统计概览。"""
    data = load_data()
    items = list(data["items"].values())

    if not items:
        print("📭 还没有任何条目")
        return 0

    today = today_str()
    total = len(items)
    mastered = sum(1 for it in items if it["is_mastered"])
    leech = sum(1 for it in items if it["is_leech"])
    due_today = sum(
        1 for it in items
        if it["next_due"] <= today and not it["is_mastered"]
    )
    in_progress = total - mastered - leech

    total_reviews = sum(it["total_reviews"] for it in items)
    total_failures = sum(it["total_failures"] for it in items)
    success_rate = (
        (total_reviews - total_failures) / total_reviews * 100
        if total_reviews > 0 else 0
    )

    avg_ef = (
        sum(it["ef"] for it in items) / total
        if total > 0 else 0
    )

    print(f"\n📊 复习系统概览\n")
    print(f"   总条目:        {total}")
    print(f"   🎓 已掌握:     {mastered} ({mastered/total*100:.0f}%)")
    print(f"   🩹 Leech:      {leech}")
    print(f"   📚 学习中:     {in_progress}")
    print(f"   ⏰ 今日到期:   {due_today}")
    print()
    print(f"   复习总次数:    {total_reviews}")
    print(f"   失败总次数:    {total_failures}")
    print(f"   成功率:        {success_rate:.1f}%")
    print(f"   平均 EF:       {avg_ef:.2f}")
    print()

    # 即将到期（7 天内）
    upcoming = []
    for it in items:
        if it["is_mastered"]:
            continue
        days_to_due = (
            datetime.strptime(it["next_due"], "%Y-%m-%d")
            - datetime.now()
        ).days
        if 0 <= days_to_due <= 7:
            upcoming.append((days_to_due, it))

    if upcoming:
        print("   📅 未来 7 天到期:")
        for days, it in sorted(upcoming):
            print(f"      {days} 天后: [{it['id']}] {it['title']}")
    return 0


def cmd_remove(args) -> int:
    """删除条目。"""
    data = load_data()
    if args.id not in data["items"]:
        print(f"❌ 条目 {args.id} 不存在")
        return 1
    title = data["items"][args.id]["title"]
    del data["items"][args.id]
    save_data(data)
    print(f"🗑️  已删除: [{args.id}] {title}")
    return 0


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="基于 SM-2 的自适应复习系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s add --id agentscope-arch --title "AgentScope 架构全景" \\
                       --file notes/phase-1/architecture.md --difficulty 2
  %(prog)s due                # 看今天要复习啥
  %(prog)s review agentscope-arch     # 复习（交互式打分）
  %(prog)s review agentscope-arch --score 3   # 复习（直接给 3 分）
  %(prog)s stats              # 看统计
  %(prog)s list               # 列出所有
        """,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="添加新条目")
    p_add.add_argument("--id", required=True, help="唯一 ID（字母数字下划线）")
    p_add.add_argument("--title", required=True, help="标题")
    p_add.add_argument("--file", default="", help="关联的文件路径")
    p_add.add_argument(
        "--difficulty", type=int, choices=[1, 2, 3], default=2,
        help="初始难度提示（1=简单/2=中等/3=困难）",
    )
    p_add.set_defaults(func=cmd_add)

    # list
    p_list = sub.add_parser("list", help="列出所有条目")
    p_list.set_defaults(func=cmd_list)

    # due
    p_due = sub.add_parser("due", help="显示今日应复习")
    p_due.set_defaults(func=cmd_due)

    # review
    p_review = sub.add_parser("review", help="复习一个条目")
    p_review.add_argument("id", help="条目 ID")
    p_review.add_argument(
        "--score", type=int, choices=[0, 1, 2, 3], default=None,
        help="直接给分（0=忘了 1=吃力 2=还可以 3=秒答）",
    )
    p_review.add_argument(
        "--force", action="store_true",
        help="强制复习 mastered 条目",
    )
    p_review.set_defaults(func=cmd_review)

    # show
    p_show = sub.add_parser("show", help="显示条目详情")
    p_show.add_argument("id", help="条目 ID")
    p_show.set_defaults(func=cmd_show)

    # stats
    p_stats = sub.add_parser("stats", help="统计概览")
    p_stats.set_defaults(func=cmd_stats)

    # remove
    p_remove = sub.add_parser("remove", help="删除条目")
    p_remove.add_argument("id", help="条目 ID")
    p_remove.set_defaults(func=cmd_remove)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
