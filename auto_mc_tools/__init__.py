# Auto MC Tools — генерировать дистракторы в поле, обновлять wordpool.txt, тасовать картинки
from __future__ import annotations
from aqt import mw
from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, askUser
from aqt.browser import Browser
from aqt import gui_hooks
import re, random
from difflib import SequenceMatcher

# ---------- конфиг ----------
DEFAULT_CFG = {
    "wordField": "Word",           # из какого поля брать правильный ответ
    "optionsField": "AutoOptions", # в какое поле писать дистракторы (через ; )
    "imageField": "Image",         # поле с картинками
    "distractorCount": 3,          # сколько ложных вариантов
    "sameDeckOnly": True           # брать кандидатов только из той же колоды (для действий по выделению)
}
cfg = mw.addonManager.getConfig(__name__) or {}
for k, v in DEFAULT_CFG.items():
    cfg.setdefault(k, v)
mw.addonManager.writeConfig(__name__, cfg)

# ---------- утилиты ----------
def _similar(a: str, b: str) -> float:
    return SequenceMatcher(a=a.lower(), b=b.lower()).ratio()

def _search_nids(query: str):
    try:
        return mw.col.find_notes(query)
    except Exception:
        return mw.col.findNotes(query)

def _current_deck_name() -> str | None:
    try:
        did = mw.col.sched.get_current_deck_id()
        d = mw.col.decks.get(did)
        return d["name"] if isinstance(d, dict) else getattr(d, "name", None)
    except Exception:
        try:
            d = mw.col.decks.current()
            # в некоторых версиях current() возвращает dict
            if isinstance(d, dict):
                return d.get("name")
            return getattr(d, "name", None)
        except Exception:
            return None

def _pick_distractors(word: str, candidate_words: list[str], need: int) -> list[str]:
    wl = word.lower()
    cand = [w for w in candidate_words if (w and w.lower() != wl)]
    def ok(x):
        return abs(len(x)-len(word)) <= 2 and 0.35 <= _similar(x, word) <= 0.85
    pool = [c for c in cand if ok(c)]
    random.shuffle(pool)
    seen, out = set(), []
    for x in pool:
        xl = x.lower()
        if xl not in seen:
            out.append(x); seen.add(xl)
        if len(out) >= need: break
    if len(out) < need:
        random.shuffle(cand)
        for x in cand:
            xl = x.lower()
            if xl not in seen:
                out.append(x); seen.add(xl)
            if len(out) >= need: break
    return out[:need]

def _collect_words_from_nids(nids: list[int], field_name: str) -> list[str]:
    acc = []
    for nid in nids:
        n = mw.col.get_note(nid)
        if field_name in n:
            w = n[field_name].strip()
            if w:
                acc.append(w)
    return acc

def _collect_nids_scope(deck_only: bool) -> list[int]:
    if deck_only:
        dn = _current_deck_name()
        q = f'deck:"{dn}"' if dn else ""
    else:
        q = ""
    return _search_nids(q)

def _browser_selected_note_ids(br: Browser) -> list[int]:
    return br.selected_note_ids() if hasattr(br, "selected_note_ids") else br.selectedNotes()

# ---------- генерация дистракторов ----------
def _generate_options_for_nids(nids: list[int], candidate_words: list[str]):
    wordF = cfg["wordField"]; optF = cfg["optionsField"]
    need  = int(cfg["distractorCount"])
    updated = 0; skipped = 0
    for nid in nids:
        n = mw.col.get_note(nid)
        if wordF not in n or optF not in n:
            skipped += 1; continue
        word = n[wordF].strip()
        if not word:
            skipped += 1; continue
        opts = _pick_distractors(word, candidate_words, need)
        n[optF] = "; ".join(opts)
        n.flush()
        updated += 1
    mw.col.reset(); mw.reset()
    showInfo(f"Готово: обновлено {updated} заметок, пропущено {skipped}.")

def action_generate_options_selected(br: Browser):
    nids = _browser_selected_note_ids(br)
    if not nids:
        showInfo("Выделите заметки в Браузере."); return
    # кандидаты — из той же колоды (или всей коллекции) по настройке
    if bool(cfg["sameDeckOnly"]):
        # возьмём имя колоды по первой карте первого нида
        dn = _current_deck_name()
        q = f'deck:"{dn}"' if dn else ""
    else:
        q = ""
    all_nids = _search_nids(q)
    candidates = _collect_words_from_nids(all_nids, cfg["wordField"])
    _generate_options_for_nids(nids, candidates)

def action_generate_options_scope(deck_only: bool):
    """Через меню Инструменты: по текущей колоде или по всей коллекции."""
    scope_nids = _collect_nids_scope(deck_only)
    if not scope_nids:
        showInfo("Не найдено заметок в выбранной области."); return
    candidates = _collect_words_from_nids(scope_nids, cfg["wordField"])
    _generate_options_for_nids(scope_nids, candidates)

# ---------- wordpool.txt ----------
def action_build_wordpool(deck_only: bool):
    nids = _collect_nids_scope(deck_only)
    words = sorted(set(_collect_words_from_nids(nids, cfg["wordField"])), key=str.lower)
    mw.col.media.write_data("wordpool.txt", ("\n".join(words) + ("\n" if words else "")).encode("utf-8"))
    scope = "текущей колоды" if deck_only else "всей коллекции"
    showInfo(f"wordpool.txt обновлён из {scope} ({len(words)} слов).")

# ---------- тасовать картинки ----------
def _shuffle_images_in_nids(nids: list[int]):
    imgF = cfg["imageField"]
    changed = 0; skipped = 0
    for nid in nids:
        n = mw.col.get_note(nid)
        if imgF not in n:
            skipped += 1; continue
        val = n[imgF]
        parts = re.split(r'(<img\b[^>]*>)', val, flags=re.I)
        imgs = [p for p in parts if re.match(r'<img\b', p, flags=re.I)]
        if len(imgs) <= 1:
            skipped += 1; continue
        nonimgs = [p for p in parts if not re.match(r'<img\b', p or '', flags=re.I)]
        random.shuffle(imgs)
        new_val = ""
        if nonimgs: new_val += nonimgs[0]
        new_val += "".join(imgs)
        if len(nonimgs) > 1: new_val += "".join(nonimgs[1:])
        if new_val != val:
            n[imgF] = new_val
            n.flush()
            changed += 1
    mw.col.reset(); mw.reset()
    showInfo(f"Перемешано {changed} заметок, пропущено {skipped}.")

def action_shuffle_images_selected(br: Browser):
    nids = _browser_selected_note_ids(br)
    if not nids:
        showInfo("Выделите заметки в Браузере."); return
    _shuffle_images_in_nids(nids)

def action_shuffle_images_scope(deck_only: bool):
    nids = _collect_nids_scope(deck_only)
    if not nids:
        showInfo("Не найдено заметок.")
        return
    _shuffle_images_in_nids(nids)

# ---------- меню ----------
def _add_tools_menu():
    m = QMenu("Auto MC", mw)

    # Генерация дистракторов по области
    a1 = QAction("Сгенерировать дистракторы → текущая колода", mw)
    a1.triggered.connect(lambda: action_generate_options_scope(True))
    m.addAction(a1)

    a2 = QAction("Сгенерировать дистракторы → вся коллекция", mw)
    a2.triggered.connect(lambda: action_generate_options_scope(False))
    m.addAction(a2)

    m.addSeparator()
    b1 = QAction("Обновить wordpool.txt из текущей колоды", mw)
    b1.triggered.connect(lambda: action_build_wordpool(True))
    m.addAction(b1)

    b2 = QAction("Обновить wordpool.txt из всей коллекции", mw)
    b2.triggered.connect(lambda: action_build_wordpool(False))
    m.addAction(b2)

    m.addSeparator()
    c1 = QAction("Перемешать картинки в поле Image (текущая колода)", mw)
    c1.triggered.connect(lambda: action_shuffle_images_scope(True))
    m.addAction(c1)

    c2 = QAction("Перемешать картинки в поле Image (вся коллекция)", mw)
    c2.triggered.connect(lambda: action_shuffle_images_scope(False))
    m.addAction(c2)

    mw.form.menuTools.addMenu(m)

def _browser_menu(br: Browser, menu: QMenu):
    sub = menu.addMenu("Auto MC")
    x1 = QAction("Сгенерировать дистракторы → AutoOptions (для выделенных)", br)
    x1.triggered.connect(lambda: action_generate_options_selected(br))
    sub.addAction(x1)

    x2 = QAction("Перемешать картинки в поле Image (для выделенных)", br)
    x2.triggered.connect(lambda: action_shuffle_images_selected(br))
    sub.addAction(x2)

gui_hooks.main_window_did_init.append(_add_tools_menu)
gui_hooks.browser_will_show_context_menu.append(_browser_menu)
