# Auto MC Tools

Набор утилит-кнопок для подготовки карточек с **множественным выбором**:

- Генерация дистракторов и запись их в поле `AutoOptions`.
- Сборка медиапака `wordpool.txt` из текущей колоды или всей коллекции — для JS-шаблона.
- Перемешивание `<img>` в поле `Image` у заметок.

Работает на **десктопе**. Результат (поля и `wordpool.txt`) корректно отображается и на мобильных клиентах, потому что в шаблонах используется чистый HTML/JS.

---

## Установка

1. В Anki: **Инструменты → Дополнения → Открыть папку дополнений**.  
2. Скопируйте сюда папку `auto_mc_tools`.  
3. Перезапустите Anki.

---

## Требуемые поля в типе заметки

- `Word` — правильный ответ (можно переименовать в конфиге).
- `AutoOptions` — строка для дистракторов, формат: `opt1; opt2; opt3`.
- `Image` — (опционально) поле с картинками, если хотите «тасовать» `<img>`.

---

## Меню

### Инструменты → **Auto MC**

- **Сгенерировать дистракторы → текущая колода**  
  Обходит все заметки текущей колоды и пишет N дистракторов в `AutoOptions`.

- **Сгенерировать дистракторы → вся коллекция**  
  То же самое по всей коллекции.

- **Обновить `wordpool.txt` из текущей колоды**  
- **Обновить `wordpool.txt` из всей коллекции**  
  Собирает уникальные слова из поля `wordField` и сохраняет в медиа-файл `wordpool.txt`.

- **Перемешать картинки в поле Image (текущая колода / вся коллекция)**  
  Меняет порядок `<img>`-тегов внутри поля `Image`.

### Браузер → ПКМ по выделенным → **Auto MC**

- **Сгенерировать дистракторы → AutoOptions (для выделенных)**  
- **Перемешать картинки в поле Image (для выделенных)**

---

## Конфигурация

Откройте: **Инструменты → Дополнения → Auto MC Tools → Конфигурация**.

```json
{
  "wordField": "Word",          // из какого поля брать правильный ответ
  "optionsField": "AutoOptions",// куда писать дистракторы (через ; )
  "imageField": "Image",        // поле с картинками
  "distractorCount": 3,         // сколько ложных вариантов генерировать
  "sameDeckOnly": true          // (для режимов "по выделенным"): кандидаты только из той же колоды
}
```

## Рекомендуемый шаблон (Back)

> Кроссплатформенный JS-блок: сначала берёт варианты из AutoOptions, а если мало — добирает из wordpool.txt.

```html
<div class="prompt">Выберите правильное слово:</div>

<!-- data-count — сколько дистракторов (лишних слов) показывать -->
<div id="mc"
     data-word="{{Word}}"
     data-opts="{{AutoOptions}}"
     data-count="{{#MCCount}}{{MCCount}}{{/MCCount}}">
</div>

<div class="after">
  <div class="ipa">{{#IPA}}[{{IPA}}]{{/IPA}}</div>
  <div class="tr">{{Translation}}</div>
</div>

<style>
:root{
  --mc-green:#22c55e; --mc-red:#ef4444;
  --mc-bg:#f8fafc; --mc-fg:#111827; --mc-border:#e5e7eb; --mc-hover:rgba(0,0,0,.04);
}
.prompt{font-size:28px;margin:12px 0 18px;text-align:center;}
#mc{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;}
.mc-btn{
  padding:12px 18px; min-width:120px; border-radius:16px; border:1px solid var(--mc-border);
  background:var(--mc-bg); color:var(--mc-fg); font-size:20px; cursor:pointer;
  transition:transform .05s, box-shadow .15s, background .15s; box-shadow:0 1px 2px rgba(0,0,0,.06);
}
.mc-btn:hover{background:var(--mc-hover);} .mc-btn:active{transform:translateY(1px);}
.mc-btn.correct{background:rgba(34,197,94,.12); border-color:var(--mc-green); color:#065f46; box-shadow:0 0 0 3px rgba(34,197,94,.25);}
.mc-btn.wrong{background:rgba(239,68,68,.12); border-color:var(--mc-red); color:#7f1d1d; box-shadow:0 0 0 3px rgba(239,68,68,.25);}
.mc-btn:disabled{opacity:.9; cursor:default;}
.after{margin-top:16px;text-align:center;opacity:0;transition:opacity .2s;} .after.show{opacity:1;}
</style>

<script>
(async function(){
  const host=document.getElementById('mc'); if(!host) return;
  const WORD=(host.dataset.word||'').trim(); if(!WORD) return;

  let COUNT=parseInt(host.dataset.count,10); if(!Number.isFinite(COUNT)||COUNT<1) COUNT=3;

  // 1) берем из AutoOptions
  let opts=(host.dataset.opts||'').split(/[;,|]/).map(s=>s.trim()).filter(Boolean);

  // 2) при необходимости добираем из wordpool.txt
  async function loadPool(){ try{const r=await fetch('wordpool.txt'); if(!r.ok) return []; return (await r.text()).split(/\r?\n/).map(s=>s.trim()).filter(Boolean);}catch(e){return [];} }
  function sim(a,b){a=a.toLowerCase();b=b.toLowerCase(); const grams=s=>new Set(Array.from({length:Math.max(0,s.length-1)},(_,i)=>s.slice(i,i+2)));
    const A=grams(a),B=grams(b); let inter=0; for(const g of A) if(B.has(g)) inter++; const j=(A.size||B.size)?inter/(A.size+B.size-inter):0;
    const len=1-Math.min(1,Math.abs(a.length-b.length)/Math.max(a.length,b.length,1)); return j*0.7+len*0.3; }
  function fallback(n){ const out=new Set(), ab='abcdefghijklmnopqrstuvwxyz';
    while(out.size<n){ let s=WORD.split(''), i=Math.floor(Math.random()*WORD.length);
      if(Math.random()<0.5 && WORD.length>3){ const j=Math.min(WORD.length-1,i+1); [s[i],s[j]]=[s[j],s[i]]; } else { s[i]=ab[Math.floor(Math.random()*ab.length)]; }
      const v=s.join(''); if(v.toLowerCase()!==WORD.toLowerCase()) out.add(v); } return [...out]; }

  if(opts.length<COUNT){
    const pool=(await loadPool()).filter(w=>w.toLowerCase()!==WORD.toLowerCase());
    if(pool.length){
      const top=pool.map(w=>({w,s:sim(w,WORD)})).sort((a,b)=>b.s-a.s).slice(0,30);
      while(opts.length<COUNT && top.length){ const i=Math.floor(Math.random()*top.length); const p=top.splice(i,1)[0].w; if(!opts.includes(p)) opts.push(p); }
    }
  }
  if(opts.length<COUNT) fallback(COUNT-opts.length).forEach(v=>opts.push(v));
  opts=opts.slice(0,COUNT);

  const options=[WORD, ...opts];
  for(let i=options.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [options[i],options[j]]=[options[j],options[i]]; }

  const after=document.querySelector('.after');
  options.forEach(txt=>{
    const b=document.createElement('button'); b.className='mc-btn'; b.textContent=txt; b.dataset.v=txt;
    b.onclick=()=>{ host.querySelectorAll('.mc-btn').forEach(x=>x.disabled=true);
      if(txt===WORD){ b.classList.add('correct'); }
      else{ b.classList.add('wrong'); host.querySelectorAll('.mc-btn').forEach(x=>{ if(x.dataset.v===WORD) x.classList.add('correct'); }); }
      after?.classList.add('show'); };
    host.appendChild(b);
  });
})();
</script>

```
## Типичный рабочий процесс

1. На десктопе в Браузере выделите нужные заметки → ПКМ → Auto MC → Сгенерировать дистракторы → AutoOptions.
2. (Опционально) Инструменты → Auto MC → Обновить wordpool.txt (текущая колода или вся коллекция).
3. Синхронизируйте. На ПК и телефоне JS-шаблон покажет варианты (из AutoOptions и/или wordpool.txt).
4. (Опционально) Перемешайте картинки тем же меню.

## Совместимость

> Проверено на Anki 25.07.5 (Qt6/PyQt6). Для 2.1.* предусмотрены альтернативные ветки API.
