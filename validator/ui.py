"""Render ui/index.html: one static page listing contracts, attempts, and outcomes."""

from html import escape

CSS = """
:root { --bg: #fbfbf9; --fg: #1d1d1b; --muted: #5f5f5a; --line: #deded8; --yes: #1f6f3f; --no: #8a2a1f; --other: #5f5f5a; --banner: #fff4d6; }
@media (prefers-color-scheme: dark) { :root { --bg: #161615; --fg: #ececea; --muted: #a3a39d; --line: #34342f; --yes: #7fcf9b; --no: #f0a094; --other: #a3a39d; --banner: #3a3220; } }
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; }
main { max-width: 960px; margin: 0 auto; }
h1 { font-size: 1.6rem; margin: 0 0 4px; }
h2 { font-size: 1.2rem; margin: 32px 0 8px; }
p, li { color: var(--muted); }
.banner { background: var(--banner); color: var(--fg); padding: 12px 16px; border-radius: 6px; margin: 16px 0; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.95rem; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 600; }
.YES { color: var(--yes); font-weight: 700; } .NO { color: var(--no); font-weight: 700; } .OTHER { color: var(--other); font-weight: 700; }
code { font-size: 0.9em; }
"""


def render(outcomes, registry):
    parts = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             "<title>AI Safety Claims</title>", f"<style>{CSS}</style></head><body><main>",
             "<h1>AI Safety Claims</h1>",
             "<p>Published AI-safety evaluations scored against frozen market contracts. "
             "Each market resolves YES (a qualifying attempt met the bars), NO (every qualifying attempt missed), "
             "or OTHER (no qualifying attempt).</p>"]
    if not registry["resolutionSource"]:
        parts.append('<div class="banner"><strong>Not a resolution source.</strong> No host organization owns this '
                     "registry yet. Contracts are drafts and no outcome below resolves any question.</div>")
    parts.append('<div class="table-wrap"><table><thead><tr><th>Market</th><th>Contract</th><th>Evidence cutoff</th>'
                 "<th>Attempts</th><th>Qualifying</th><th>Outcome</th></tr></thead><tbody>")
    for name, o in outcomes.items():
        qualifying = sum(1 for a in o["attempts"] if a["qualifying"])
        parts.append(f'<tr><td><a href="#{escape(o["market"])}">{escape(o["market"])}</a> {escape(o["title"])}</td>'
                     f'<td>v{o["contractVersion"]} ({escape(o["contractStatus"])})</td><td>{escape(o["evidenceCutoff"])}</td>'
                     f'<td>{len(o["attempts"])}</td><td>{qualifying}</td>'
                     f'<td class="{o["outcome"]}">{o["outcome"]}</td></tr>')
    parts.append("</tbody></table></div>")
    for name, o in outcomes.items():
        parts.append(f'<h2 id="{escape(o["market"])}">{escape(o["market"])} v{o["contractVersion"]}: {escape(o["title"])}</h2>')
        parts.append(f'<p>Outcome <span class="{o["outcome"]}">{o["outcome"]}</span> ({escape(o["reason"])}). '
                     f'File <code>market-outcomes/{escape(name)}</code>. Window closes {escape(o["windowCloses"])}.</p>')
        if not o["attempts"]:
            parts.append("<p>No attempts filed.</p>")
            continue
        parts.append('<div class="table-wrap"><table><thead><tr><th>Attempt</th><th>Type</th><th>Qualifying</th>'
                     "<th>Bars met</th><th>Reason</th></tr></thead><tbody>")
        for a in o["attempts"]:
            details = "".join(f"<li>{escape(d)}</li>" for d in a["details"])
            parts.append(f'<tr><td><code>{escape(a["id"])}</code></td><td>{escape(str(a["attemptType"]))}</td>'
                         f'<td>{"yes" if a["qualifying"] else "no"}</td>'
                         f'<td>{"n/a" if a["barsMet"] is None else ("yes" if a["barsMet"] else "no")}</td>'
                         f'<td>{escape(a["reason"])}{f"<ul>{details}</ul>" if details else ""}</td></tr>')
        parts.append("</tbody></table></div>")
    parts.append("</main></body></html>")
    return "\n".join(parts) + "\n"
