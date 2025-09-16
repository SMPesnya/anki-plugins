# Auto MC Distractors — генерирует варианты автоматически из поля Word
from aqt import mw
import random, html
from difflib import SequenceMatcher

# --------- конфиг ---------
def get_cfg():
    cfg = mw.addonManager.getConfig(__name__) or {}
    return {
        "distractorCount": int(cfg.get("distractorCount", 3)),
        "sameDeckOnly": bool(cfg.get("sameDeckOnly", True)),
        "fieldName": str(cfg.get("fieldName", "Word")),
    }

CFG = get_cfg()
if mw.addonManager.getConfig(__name__) is None:
    mw.addonManager.writeConfig(__name__, CFG)

# --------- утилиты ---------
def _similar(a: str, b: str) -> float:
    return SequenceMatcher(a=a.lower(), b=b.lower()).ratio()

def _get_deck_name_from_ctx(ctx) -> str | None:
    try:
        card = getattr(ctx, "card", None)
        if not card:
            return None
        did = getattr(card, "did", None)
        if did is None:
            did = getattr(card, "deck_id", None)
        if did is None:
            return None
        d = mw.col.decks.get(did)
        # старые версии возвращают dict, новые — объект
        if isinstance(d, dict):
            return d.get("name")
        return getattr(d, "name", None)
    except Exception:
        return None

def _pick_distractors(word: str, ctx):
    same_deck = CFG["sameDeckOnly"]
    field_name = CFG["fieldName"]
    need = CFG["distractorCount"]

    # строим поисковый запрос
    if same_deck:
        deck_name = _get_deck_name_from_ctx(ctx)
        q = f'deck:"{deck_name}"' if deck_name else ""
    else:
        q = ""

    try:
        nids = mw.col.find_notes(q)
    except Exception:
        # на очень старых версиях
        nids = mw.col.find_notes(q) if hasattr(mw.col, "find_notes") else mw.col.findNotes(q)

    cand = []
    for nid in nids:
        try:
            if hasattr(ctx, "note") and nid == ctx.note.id:
                continue
        except Exception:
            pass
        n = mw.col.get_note(nid)
        if field_name in n and n[field_name].strip():
            w = n[field_name].strip()
            if w.lower() != word.lower():
                cand.append(w)

    # фильтр по длине и похожести
    def ok(x):
        return abs(len(x) - len(word)) <= 2 and 0.35 <= _similar(x, word) <= 0.85

    pool = [c for c in cand if ok(c)]
    random.shuffle(pool)

    seen = set()
    out = []
    for x in pool:
        xl = x.lower()
        if xl not in seen:
            out.append(x)
            seen.add(xl)
        if len(out) >= need:
            break

    if len(out) < need:
        random.shuffle(cand)
        for x in cand:
            xl = x.lower()
            if xl not in seen:
                out.append(x)
                seen.add(xl)
            if len(out) >= need:
                break
    return out[:need]

# --------- сам фильтр ---------
def auto_mc_field_filter(field_text, field_name, filter_name, ctx):
    # Используем как {{auto_mc:Word}}
    if filter_name != "auto_mc":
        return field_text

    word = (field_text or "").strip()
    if not word:
        return field_text

    options = [word] + _pick_distractors(word, ctx)
    random.shuffle(options)

    btns = []
    for opt in options:
        esc = html.escape(opt)
        btns.append(f'<button class="mc-btn" data-v="{esc}">{esc}</button>')

    correct = html.escape(word)
    return f"""
<div class="prompt">Выберите правильное слово:</div>
<div id="auto-mc" data-correct="{correct}">
  {' '.join(btns)}
</div>
<style>
.prompt{{font-size:28px;margin:12px 0 18px;text-align:center;}}
#auto-mc{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;}}
.mc-btn{{padding:10px 14px;border-radius:14px;border:1px solid #ccc;font-size:20px;cursor:pointer;background:#f7f7f7;}}
.mc-btn.correct{{background:#c8f7c5;border-color:#7bc47f;}}
.mc-btn.wrong{{background:#ffd4d4;border-color:#ff8a8a;}}
.mc-btn:disabled{{opacity:.7;cursor:default;}}
</style>
<script>
(function(){{
  const host = document.getElementById('auto-mc');
  if(!host) return;
  const ans = host.dataset.correct;
  host.querySelectorAll('.mc-btn').forEach(b => {{
    b.addEventListener('click', () => {{
      host.querySelectorAll('.mc-btn').forEach(x => x.disabled = true);
      if (b.dataset.v === ans) {{
        b.classList.add('correct');
      }} else {{
        b.classList.add('wrong');
        host.querySelectorAll('.mc-btn').forEach(x => {{
          if (x.dataset.v === ans) x.classList.add('correct');
        }});
      }}
    }});
  }});
}})();
</script>
"""

# --------- регистрация хука: новая и старая API ---------
_registered = False
try:
    # новые версии (если объект-список hooks существует)
    from aqt import gui_hooks
    if hasattr(gui_hooks, "template_will_render"):
        # fallback: ставим на рендеринг шаблона и заменяем только когда встретится наш фильтр
        # но в 25.x есть именно "template_will_render"? оставим как универсальный путь ниже
        pass
    if hasattr(gui_hooks, "field_filter"):
        gui_hooks.field_filter.append(auto_mc_field_filter)
        _registered = True
except Exception:
    pass

if not _registered:
    # старый способ
    try:
        from anki.hooks import field_filter
        field_filter.append(auto_mc_field_filter)
        _registered = True
    except Exception:
        # ультра-старые — функция addHook
        try:
            from anki.hooks import addHook
            addHook("fieldFilter", auto_mc_field_filter)
            _registered = True
        except Exception:
            pass
