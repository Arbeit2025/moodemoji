"""moodemoji のテスト（外部通信なし）。"""
import pytest

import app as mood


# --- カテゴリ判定 -------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("うれしい", "うれしい"),
    ("楽しい", "楽しい"),
    ("悲しい", "悲しい"),
    ("イライラする", "怒り"),
    ("疲れた", "疲れた"),
    ("眠い", "眠い"),
    ("お腹すいた", "お腹すいた"),
    ("ドキドキする", "ドキドキ"),
    ("びっくりした", "びっくり"),
    ("不安だ", "不安"),
    ("のんびりしたい", "リラックス"),
    ("やる気が出てきた", "やる気"),
    ("ありがとう", "感謝"),
])
def test_each_mood_is_detected(text, expected):
    result = mood.analyze(text)
    assert result["moods"][0] == expected
    assert result["emoji"]


def test_score_counts_repeats():
    assert mood.score_moods("眠い、とにかく眠い")["眠い"] == 2


def test_top_mood_wins_by_score():
    result = mood.analyze("悲しいけど少しうれしい、うれしい")
    assert result["moods"][0] == "うれしい"


def test_tie_includes_second_mood():
    result = mood.analyze("うれしいし楽しい")
    assert result["moods"] == ["うれしい", "楽しい"]


# --- 強さ ---------------------------------------------------------------

def test_intensity_levels():
    assert mood.detect_intensity("悲しい") == 2
    assert mood.detect_intensity("ちょっと悲しい") == 1
    assert mood.detect_intensity("すごく悲しい") == 3
    assert mood.detect_intensity("とても悲しい") == 3
    assert mood.detect_intensity("悲しい！！") == 3


def test_intensity_changes_length():
    # うれしい の候補シーケンスはすべて2コードポイント
    assert len(mood.mood_emoji("ちょっとうれしい")) == 2
    assert len(mood.mood_emoji("うれしい")) == 4
    assert len(mood.mood_emoji("すごくうれしい")) == 6


# --- 決定性・フォールバック ----------------------------------------------

def test_deterministic():
    text = "今日はすごくうれしい！　明日も楽しみ"
    assert mood.mood_emoji(text) == mood.mood_emoji(text)
    assert mood.analyze(text) == mood.analyze(text)


def test_fallback_neutral_not_empty():
    result = mood.analyze("あいうえお")
    assert result["moods"] == []
    assert result["emoji"]
    seqs = {s * n for s in mood.NEUTRAL_SEQS for n in (1, 2, 3)}
    assert result["emoji"] in seqs


def test_empty_input():
    assert mood.mood_emoji("") == ""
    assert mood.mood_emoji("   ") == ""
    assert mood.mood_emoji(None) == ""


# --- Web ------------------------------------------------------------------

@pytest.fixture()
def client():
    mood.app.config["TESTING"] = True
    with mood.app.test_client() as c:
        yield c


def test_index_get(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "きもち絵文字メーカー" in res.get_data(as_text=True)


def test_index_post_returns_emoji(client):
    res = client.post("/", data={"text": "すごくうれしい"})
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert any(e in body for e in ("😊", "😄", "🥰", "😆"))


def test_index_post_unknown_text_still_returns_emoji(client):
    res = client.post("/", data={"text": "あいうえお"})
    assert res.status_code == 200
    assert "🙂" in res.get_data(as_text=True) or \
        "😌" in res.get_data(as_text=True) or \
        "🌈" in res.get_data(as_text=True) or \
        "🍀" in res.get_data(as_text=True)


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.get_data(as_text=True) == "ok"
