import html
import json
from pathlib import Path
import re

import pytest

from presentation import release_identity as identity

ROOT = Path(__file__).resolve().parents[1]


def outside_scripts(document):
    return "".join(piece for piece in re.split(r"(<script\b.*?</script>)", document, flags=re.S)
                   if not piece.startswith("<script"))


def test_every_relative_report_link_has_a_public_copy_for_standalone_readers():
    document = (ROOT / "results/study/report.html").read_text(encoding="utf-8")
    static = outside_scripts(document)
    anchors = re.findall(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>', static)
    relative = [target for target in anchors if identity.is_relative(html.unescape(target))]
    assert len(relative) >= 14
    for target in set(relative):
        url, _ = identity.public_url(*identity.resolve(html.unescape(target), "results/study"))
        follower = (f'<a href="{target}">', f' <a class="public-copy" href="{html.escape(url, quote=True)}"')
        count = len(re.findall(re.escape(follower[0]) + r".*?</a>" + re.escape(follower[1]), static, re.S))
        assert count == relative.count(target), target
    public = re.findall(r'class="public-copy" href="([^"]+)"', static)
    assert len(public) == len(relative)
    assert all(url.startswith(f"https://github.com/{identity.FORK}/blob/") for url in public)
    assert 'id="standalone-notice"' in static


def test_pinned_public_copies_hold_exactly_the_local_bytes():
    manifest = identity.load_manifest()
    assert manifest["repository"] == identity.FORK and manifest["files"]
    for path, pin in manifest["files"].items():
        assert re.fullmatch(r"[0-9a-f]{40}", pin["commit"])
        assert identity.sha256(ROOT / path) == pin["sha256"], path
        assert path not in identity.READER_DOCUMENTS


def test_changed_evidence_without_a_new_published_pin_fails_the_build():
    manifest = identity.load_manifest()
    path = "results/study/decision_data.json"
    manifest["files"][path] = dict(manifest["files"][path], sha256="0" * 64)
    with pytest.raises(ValueError, match="differs from its pinned public copy"):
        identity.public_url(path, manifest=manifest)
    with pytest.raises(KeyError, match="No published pin"):
        identity.public_url("results/study/abstract.txt", manifest={"files": {}})
    with pytest.raises(ValueError, match="leaves the entry"):
        identity.resolve("../../../outside.md", "results/study")


def test_record_tables_are_embedded_with_their_pins():
    document = (ROOT / "results/study/report.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="atlas-public-sources" type="application/json">(.*?)</script>', document)
    assert json.loads(match.group(1)) == identity.source_table_links()
    data = json.loads((ROOT / "results/study/decision_data.json").read_bytes())
    assert {record["source_csv"] for record in data["observations"]} <= set(json.loads(match.group(1)))


def test_notebook_markdown_links_offer_public_copies():
    notebook = json.loads((ROOT / identity.NOTEBOOK).read_bytes())
    for cell in notebook["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        for match in identity.MARKDOWN_LINK.finditer("".join(cell["source"])):
            if identity.is_relative(match.group(2)):
                url, _ = identity.public_url(*identity.resolve(match.group(2)))
                assert "".join(cell["source"])[match.end():].startswith(f" ([public copy]({url}))")


def test_notebook_is_bound_to_the_sealed_support_release():
    sealed = json.loads((ROOT / identity.CHECKSUMS).read_bytes())
    assert sealed == identity.release_files(ROOT)
    notebook = json.loads((ROOT / identity.NOTEBOOK).read_bytes())
    bootstrap = "".join(notebook["cells"][1]["source"])
    digest = re.search(r'EXPECTED_SUPPORT_DIGEST = \(\n    "([0-9a-f]{64})"\n\)', bootstrap).group(1)
    assert digest == identity.support_digest(sealed)
    assert identity.PLACEHOLDER not in bootstrap
    outputs = "".join("".join(output.get("text", "")) for output in notebook["cells"][1]["outputs"])
    assert f"verified against release {digest[:12]}" in outputs


def test_witness_rows_name_pinned_public_table_lines():
    from presentation.judge_decision import load_payload, notebook_view

    view = notebook_view(1.0, 1.0)
    sources = identity.source_table_links()
    record = next(r for r in load_payload()["observations"] if r["deadline_ns"] == 1.0
                  and abs(r["input_mv"]) >= 1.0 and r["outcome"] != "correct")
    source = sources[record["source_csv"]]
    assert (f'<a href="{source["url"]}">line {record["source_record"] + 1} @ {source["commit"][:7]}</a>'
            in view)
