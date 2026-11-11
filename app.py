"""きもち絵文字メーカー（moodemoji）

日本語の気持ち・文章を入力すると、その気分に合った絵文字の
並びを返す小さなツール。気分カテゴリのキーワード辞書で
スコアリングして上位の気分を選び、「すごく」「ちょっと」などの
修飾で強さ（並びの長さ）を変える。同じ入力には同じ出力を返す
（入力文字列のハッシュで決定的に選ぶ）。単一ファイル Flask。
"""
import hashlib
import os

from flask import Flask, render_template_string, request

app = Flask(__name__)

# 気分カテゴリ: (名前, キーワード一覧, 絵文字シーケンスの候補)
MOODS = [
    ("うれしい",
     ["うれしい", "嬉しい", "しあわせ", "幸せ", "最高", "やった", "ハッピー"],
     ["😊✨", "😄🎉", "🥰✨", "😆💫"]),
    ("楽しい",
     ["楽しい", "たのしい", "ワクワク", "わくわく", "面白い", "おもしろい"],
     ["🎉😆", "🎶✨", "😄🎵", "🥳🎉"]),
    ("悲しい",
     ["悲しい", "かなしい", "泣き", "涙", "落ち込", "しょんぼり", "さみしい", "寂しい"],
     ["😢💧", "😭🌧️", "🥲💧", "😞💙"]),
    ("怒り",
     ["ムカつく", "むかつく", "イライラ", "いらいら", "腹立", "許せない", "怒"],
     ["😠💢", "😡🔥", "💢💢", "😤💨"]),
    ("疲れた",
     ["疲れ", "つかれ", "へとへと", "だるい", "しんどい", "ぐったり", "クタクタ"],
     ["😩💦", "🥱🛋️", "😮‍💨🍵", "🫠💦"]),
    ("眠い",
     ["眠い", "ねむい", "眠たい", "寝たい", "おやすみ", "眠気"],
     ["😴💤", "🥱🌙", "😪💤", "🌙⭐"]),
    ("お腹すいた",
     ["お腹すいた", "おなかすいた", "お腹空いた", "おなか空いた", "腹減", "はらへ", "空腹"],
     ["🍜😋", "🍙✨", "🍔😋", "🤤🍽️"]),
    ("ドキドキ",
     ["ドキドキ", "どきどき", "きゅん", "キュン", "恋", "大好き", "好き"],
     ["💓😍", "💕✨", "😳💓", "💖🥰"]),
    ("びっくり",
     ["びっくり", "驚", "まさか", "衝撃", "ええっ", "信じられない"],
     ["😲‼️", "😳✨", "🫢💥", "😮⚡"]),
    ("不安",
     ["不安", "心配", "緊張", "そわそわ", "ソワソワ", "怖い", "こわい", "焦"],
     ["😰💦", "😟🌫️", "😖💦", "🫨💦"]),
    ("リラックス",
     ["リラックス", "のんびり", "落ち着", "ほっこり", "ゆったり", "癒", "まったり"],
     ["😌🍵", "🌿✨", "☕😊", "🍃😌"]),
    ("やる気",
     ["やる気", "やるき", "頑張", "がんば", "集中", "燃え", "気合い", "気合"],
     ["💪🔥", "📚✨", "🔥💪", "🏃💨"]),
    ("感謝",
     ["ありがとう", "感謝", "助か", "おかげ"],
     ["🙏✨", "😊💐", "🙇✨", "💝🙏"]),
]

SEQS_BY_MOOD = {name: seqs for name, _kw, seqs in MOODS}
NEUTRAL_SEQS = ["🙂🌱", "😌✨", "🌈🙂", "🍀😊"]

STRONG_WORDS = ["すごく", "とても", "めちゃくちゃ", "めっちゃ", "めちゃ",
                "超", "かなり", "本当に", "ほんとに"]
WEAK_WORDS = ["ちょっと", "少し", "やや", "なんとなく", "軽く", "多少"]


def score_moods(text):
    """気分カテゴリごとのキーワード出現回数を数える。"""
    scores = {}
    for name, keywords, _seqs in MOODS:
        total = sum(text.count(kw) for kw in keywords)
        if total:
            scores[name] = total
    return scores


def detect_intensity(text):
    """強さ（1=弱い, 2=ふつう, 3=強い）を返す。"""
    level = 2
    if any(w in text for w in STRONG_WORDS):
        level = 3
    if any(w in text for w in WEAK_WORDS):
        level = 1
    if text.count("！") >= 2 or text.count("!") >= 2:
        level = min(3, level + 1)
    return level


def _seed_int(text):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def analyze(text):
    """入力を解析して {moods, intensity, emoji} を返す。"""
    text = (text or "").strip()
    if not text:
        return {"moods": [], "intensity": 2, "emoji": ""}
    seed = _seed_int(text)
    intensity = detect_intensity(text)
    scores = score_moods(text)
    if not scores:
        seq = NEUTRAL_SEQS[seed % len(NEUTRAL_SEQS)]
        return {"moods": [], "intensity": intensity, "emoji": seq * intensity}
    top = max(scores.values())
    # 同点はカテゴリ定義順を保つ
    winners = [name for name, _kw, _s in MOODS
               if scores.get(name) == top]
    primary = winners[0]
    seqs = SEQS_BY_MOOD[primary]
    result = seqs[seed % len(seqs)] * intensity
    if len(winners) > 1:
        sub_seqs = SEQS_BY_MOOD[winners[1]]
        result += sub_seqs[seed % len(sub_seqs)]
    return {"moods": winners, "intensity": intensity, "emoji": result}


def mood_emoji(text):
    """気持ちの文章から絵文字の並びを作る（同じ入力には同じ出力）。"""
    return analyze(text)["emoji"]


PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>きもち絵文字メーカー</title>
<style>
  :root { color-scheme: light; --bg:#fdfdf8; --fg:#222; --card:#fff;
          --border:#ddd; --accent:#e8862e; }
  @media (prefers-color-scheme: dark) {
    :root { color-scheme: dark; --bg:#16181d; --fg:#eee; --card:#22252c;
            --border:#3a3f4a; --accent:#f0a04b; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font-family: sans-serif; line-height:1.6; }
  main { max-width: 560px; margin: 0 auto; padding: 16px; }
  h1 { font-size: 1.4rem; }
  .card { background: var(--card); border: 1px solid var(--border);
          border-radius: 12px; padding: 16px; }
  textarea { width: 100%; font-size: 1rem; padding: 8px;
             border: 1px solid var(--border); border-radius: 8px;
             background: var(--bg); color: var(--fg); }
  button { font-size: 1rem; padding: 8px 16px; border: 0; border-radius: 8px;
           background: var(--accent); color: #fff; cursor: pointer; }
  button.sub { background: transparent; color: var(--accent);
               border: 1px solid var(--accent); }
  .result { font-size: 2rem; text-align: center; padding: 16px 0;
            overflow-wrap: anywhere; }
  .mood { text-align: center; opacity: .8; font-size: .9rem; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
  .note { font-size: .85rem; opacity: .75; }
</style>
</head>
<body>
<main>
  <h1>💭 きもち絵文字メーカー</h1>
  <p>いまの気持ちを文章で入れると、気分に合った絵文字の並びを作ります。</p>
  <div class="card">
    <form method="post" action="/">
      <textarea name="text" rows="3" maxlength="200"
        placeholder="例：今日はすごくうれしい！">{{ text|e }}</textarea>
      <div class="row">
        <button type="submit">絵文字にする</button>
      </div>
    </form>
    {% if emoji %}
    <div class="result" id="resultEmoji">{{ emoji }}</div>
    {% if moods %}
    <p class="mood">気分：{{ moods|join("・") }}</p>
    {% else %}
    <p class="mood">気分：ふつう</p>
    {% endif %}
    <div class="row">
      <button type="button" class="sub" id="copyBtn">コピーする</button>
      <span class="note" id="copyMsg"></span>
    </div>
    {% endif %}
  </div>
  <p class="note">「すごく」「とても」などがあると並びが長く、
     「ちょっと」「少し」などがあると短くなります。
     同じ文章を入れると、いつも同じ並びが出ます。</p>
</main>
<script>
(function () {
  var btn = document.getElementById("copyBtn");
  if (!btn) return;
  btn.addEventListener("click", function () {
    var text = document.getElementById("resultEmoji").textContent;
    var msg = document.getElementById("copyMsg");
    function done() { msg.textContent = "コピーしました"; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {
        msg.textContent = "コピーできませんでした";
      });
    } else {
      var ta = document.createElement("textarea");
      ta.value = text; document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); done(); }
      catch (e) { msg.textContent = "コピーできませんでした"; }
      document.body.removeChild(ta);
    }
  });
})();
</script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    text = ""
    emoji = ""
    moods = []
    if request.method == "POST":
        text = request.form.get("text", "")
        result = analyze(text)
        emoji = result["emoji"]
        moods = result["moods"]
    return render_template_string(PAGE, text=text, emoji=emoji, moods=moods)


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
