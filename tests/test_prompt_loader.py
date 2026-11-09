"""
Offline tests for the caption-table helpers in common/prompt_loader.py
(Load Caption Prompt). The module is loaded by path, without ComfyUI.
"""

import importlib.util
import os

import pytest

PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(PACKAGE_DIR, "common", "prompt_loader.py")
REAL_CSV = "G:/Ai/workspace/input/prompts/captions-2.csv"


@pytest.fixture(scope="module")
def pl():
    spec = importlib.util.spec_from_file_location("dockercpu_prompt_loader", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CSV_TEXT = (
    "Caption,Aspect Ratio,Nudity,Artistic Quality,Erotic Score,Pornographic Score,Males,Females,Clothing,Location\n"
    '"A photograph of Alice in a dress, Alice\'s hair loose.",2:3,,0.85,0.2,0.0,0,1,"[\'dress\']",bedroom\n'
    '"Alice and Bella on a beach.",3:2,Partial,0.75,0.6,0.1,0,2,"[\'swimwear\']",beach\n'
    '"Alicent stands alone, Alice nearby.",1:1,Full,0.5,0.9,0.4,1,1,"[]",studio\n'
)


@pytest.fixture()
def table(tmp_path):
    path = tmp_path / "captions.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")
    return str(path)


def test_parse_replacements(pl):
    pairs = pl.parse_replacements("# comment\nAlice = ohwx woman\n\nBella =\n  Adam=sks man  ")
    assert pairs == [("Alice", "ohwx woman"), ("Bella", ""), ("Adam", "sks man")]
    with pytest.raises(ValueError, match="line 1"):
        pl.parse_replacements("Alice ohwx")
    with pytest.raises(ValueError, match="nothing to find"):
        pl.parse_replacements(" = x")


def test_whole_word_and_possessive(pl):
    pairs = [("Alice", "ohwx woman")]
    text = "Alice smiles. Alice's ring, Alicent's cat, (Alice)."
    assert pl.apply_replacements(text, pairs) == "ohwx woman smiles. ohwx woman's ring, Alicent's cat, (ohwx woman)."
    assert pl.apply_replacements("Alicent", pairs, whole_word=False) == "ohwx womannt"


def test_case_and_single_pass_swap(pl):
    assert pl.apply_replacements("alice and ALICE", [("Alice", "X")]) == "alice and ALICE"
    assert pl.apply_replacements("alice and ALICE", [("Alice", "X")], case_sensitive=False) == "X and X"
    swap = [("Alice", "Bella"), ("Bella", "Alice")]
    assert pl.apply_replacements("Alice hugs Bella", swap) == "Bella hugs Alice"


def test_longest_match_and_removal(pl):
    pairs = [("Alice", "A"), ("Alice Smith", "ohwx")]
    assert pl.apply_replacements("Alice Smith and Alice", pairs) == "ohwx and A"
    assert pl.apply_replacements("Alice and Bella , smiling", [("Bella", "")]) == "Alice and, smiling"


def test_csv_load_types(pl, table):
    columns, rows = pl.load_caption_table(table)
    assert columns[0] == "Caption" and len(rows) == 3
    assert rows[0]["Nudity"] is None and rows[1]["Nudity"] == "Partial"
    assert rows[0]["Clothing"] == ["dress"] and rows[2]["Clothing"] == []
    assert rows[0]["Artistic Quality"] == 0.85 and rows[1]["Females"] == 2


def test_parquet_matches_csv(pl, table, tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    df = pd.read_csv(table)
    df["Clothing"] = [["dress"], ["swimwear"], []]
    pq_path = str(tmp_path / "captions.parquet")
    df.to_parquet(pq_path)
    _, csv_rows = pl.load_caption_table(table)
    _, pq_rows = pl.load_caption_table(pq_path)
    for a, b in zip(csv_rows, pq_rows):
        assert a["Caption"] == b["Caption"] and a["Clothing"] == b["Clothing"] and a["Nudity"] == b["Nudity"]


def test_filters(pl, table):
    columns, rows = pl.load_caption_table(table)
    f = lambda **kw: pl.filter_rows(columns, rows, **kw)
    assert f() == [0, 1, 2]
    assert f(max_people=1) == [0]
    assert f(exclude="bella") == [0, 2]
    assert f(contains="alice, beach") == [1]
    assert f(aspect_ratio="3:2") == [1]
    assert f(nudity="none") == [0]
    assert f(nudity="partial or full") == [1, 2]
    assert f(location="Bedroom, studio") == [0, 2]
    assert f(min_artistic_quality=0.7) == [0, 1]
    assert f(max_pornographic_score=0.2) == [0, 1]
    with pytest.raises(ValueError, match="no 'Missing' column"):
        f(caption_column="Missing")


def test_aspect_to_size(pl):
    assert pl.aspect_to_size("1:1") == (1024, 1024)
    w, h = pl.aspect_to_size("2:3")
    assert w % 16 == 0 and h % 16 == 0 and h > w
    assert pl.aspect_to_size("junk") == (1024, 1024)


def test_node_execute(pl, table, monkeypatch):
    monkeypatch.setattr(pl, "_resolve_prompt_file", lambda name: table)
    node = pl.LoadCaptionPrompt()
    out = node.execute("captions.csv", 4, "Alice = ohwx woman", max_people=0)["result"]
    prompt, original, aspect, width, height, row, count, metadata = out
    assert (row, count, aspect) == (1, 3, "3:2")  # 4 % 3 = 1
    assert prompt == "ohwx woman and Bella on a beach." and original.startswith("Alice and Bella")
    assert width > height and '"Location": "beach"' in metadata
    with pytest.raises(ValueError, match="No captions"):
        node.execute("captions.csv", 0, "", location="moon")


@pytest.mark.skipif(not os.path.isfile(REAL_CSV), reason="captions-2.csv not present")
def test_real_table(pl):
    columns, rows = pl.load_caption_table(REAL_CSV)
    keep = pl.filter_rows(columns, rows, max_people=1)
    assert keep and len(keep) < len(rows)
    prompt = pl.apply_replacements(rows[keep[0]]["Caption"], [("Alice", "ohwx woman")])
    assert "Alice" not in prompt and "ohwx woman" in prompt
