"""ICE 3 – Pair Programming (residential, one repo per pair named <term>_ice3_<owner-username>).

The bot keeps a pair checklist on every pull request and explains the merge
conflict the moment it appears. Humans do all the reviewing and merging.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import box, readme_problems, explain  # noqa: E402
from ghclient import BOT_LOGIN, comment_once, upsert_marked_comment  # noqa: E402

MARK = "<!-- ice3_checklist -->"


def evaluate(repo):
    pulls = [p for p in repo.list_pulls() if p["user"] != BOT_LOGIN]
    base = repo.default_branch()
    prs = []
    for p in pulls:
        files = [f["filename"] for f in repo.pr_files(p["number"])]
        commits = repo.pr_commits(p["number"])
        reviews = [r for r in repo.pr_reviews(p["number"]) if r["user"] not in (p["user"], BOT_LOGIN, None)]
        comments = [c for c in repo.pr_review_comments(p["number"]) if c["user"] != p["user"]]
        prs.append({
            "pr": p, "separate_branch": p["head_ref"] != base,
            "edits_readme": "README.md" in files,
            "merge_commit": any(c["parents"] > 1 for c in commits),
            "approvers": sorted({r["user"] for r in reviews if r["state"] == "APPROVED"}),
            "commented": bool(comments) or any(r["body"].strip() for r in reviews),
        })
    authors = sorted({e["pr"]["user"] for e in prs})
    main_text = repo.file_text("README.md", base)
    return {
        "prs": prs, "authors": authors,
        "two_authors": len(authors) >= 2,
        "review_ok": any(e["approvers"] and e["commented"] for e in prs),
        "first_merged": any(e["pr"]["merged"] for e in prs),
        "conflict_resolved": any(e["merge_commit"] for e in prs),
        "all_merged": len(prs) >= 2 and all(e["pr"]["merged"] for e in prs if e["edits_readme"]),
        "readme_problems": readme_problems(main_text),
    }


def checklist(s):
    lines = [
        "### ICE 3 pair checklist",
        "_Shared by both partners. Updates itself on every push, review, and merge._", "",
        f"- {box(s['two_authors'])} Both partners opened a pull request ({', '.join('@' + a for a in s['authors']) or 'none yet'})",
        f"- {box(all(e['separate_branch'] for e in s['prs']) and s['prs'])} Every PR comes from its own branch (not `main`)",
        f"- {box(s['review_ok'])} A partner left a review comment and approved",
        f"- {box(s['first_merged'])} First pull request merged",
        f"- {box(s['conflict_resolved'])} Merge conflict resolved (a merge commit shows in the history)",
        f"- {box(s['all_merged'] and not s['readme_problems'])} Both PRs merged; README on `main` lists both partners with no `TBD` or conflict markers",
    ]
    if s["all_merged"] and s["readme_problems"]:
        lines += ["", "**Still to fix on `main`:**", explain(s["readme_problems"])]
    return "\n".join(lines)


def score_student(login, s):
    """Points out of 5: README (2, pair) + own PR (1) + review (1, pair) + conflict (1, pair)."""
    notes, pts = [], 0
    if s["all_merged"] and not s["readme_problems"]:
        pts += 2
    else:
        notes.append("README on main incomplete")
    own = [e for e in s["prs"] if e["pr"]["user"].lower() == login.lower()]
    if any(e["separate_branch"] for e in own):
        pts += 1
    else:
        notes.append("no PR from own branch")
    if s["review_ok"]:
        pts += 1
    else:
        notes.append("no review comment + approval")
    if s["conflict_resolved"]:
        pts += 1
    else:
        notes.append("no resolved conflict in history")
    return pts, "; ".join(notes) or "complete"


def act(repo):
    s = evaluate(repo)
    body = checklist(s)
    for e in s["prs"]:
        pr = e["pr"]
        if pr["state"] == "open" and s["first_merged"] and repo.get_mergeable(pr["number"]) is False:
            comment_once(repo, pr["number"], "<!-- ice3_conflict -->",
                         "💥 **Merge conflict!** Your partner's PR merged first, and you both changed the "
                         "same line of `README.md`. This is the point of today's exercise. Together, click "
                         "**Resolve conflicts**, keep **both** lines, delete the `<<<<<<<`, `=======`, and "
                         "`>>>>>>>` markers, then **Mark as resolved → Commit merge**.")
        if pr["state"] == "open" or pr["merged"]:
            upsert_marked_comment(repo, pr["number"], MARK, body)


def main():
    from ghclient import Repo
    act(Repo(os.environ["GITHUB_REPOSITORY"]))


if __name__ == "__main__":
    main()
