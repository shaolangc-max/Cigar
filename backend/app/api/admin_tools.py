"""
/admin-tools — 辅助管理工具页面（需要 admin session）
功能：从未匹配条目直接创建别名，或新建品牌/系列/雪茄后绑定别名。
新建雪茄后自动扫描同来源未匹配条目，批量建立别名。
"""
import asyncio
import json
import re
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.alias import ScraperNameAlias
from app.models.brand import Brand
from app.models.category import Category
from app.models.cigar import Cigar
from app.models.scraper_run import UnmatchedItem
from app.models.series import Series
from app.scrapers.matcher import similarity
from app.scrapers.edition_detector import detect_edition

router = APIRouter(prefix="/admin-tools", tags=["admin-tools"])


# ── 工具函数 ───────────────────────────────────────────────────────────────────

def _require_admin(request: Request) -> bool:
    return request.session.get("admin", False)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


async def _get_or_create_brand(db, name: str) -> Brand:
    slug = _slugify(name)
    result = await db.execute(select(Brand).where(Brand.slug == slug))
    brand = result.scalar_one_or_none()
    if not brand:
        brand = Brand(name=name, slug=slug)
        db.add(brand)
        await db.flush()
    return brand


async def _get_or_create_series(db, name: str, brand_id: int) -> Series:
    brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = brand_result.scalar_one()
    slug = _slugify(f"{brand.slug}-{name}")
    result = await db.execute(select(Series).where(Series.slug == slug))
    series = result.scalar_one_or_none()
    if not series:
        series = Series(name=name, slug=slug, brand_id=brand_id)
        db.add(series)
        await db.flush()
    return series


async def _unique_cigar_slug(db, base_slug: str) -> str:
    slug = base_slug
    i = 2
    while True:
        result = await db.execute(select(Cigar).where(Cigar.slug == slug))
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base_slug}-{i}"
        i += 1


async def _upsert_alias(db, source_slug: str, raw_name: str, cigar_id: int):
    result = await db.execute(
        select(ScraperNameAlias).where(
            ScraperNameAlias.source_slug == source_slug,
            ScraperNameAlias.raw_name == raw_name,
        )
    )
    alias = result.scalar_one_or_none()
    if alias:
        alias.cigar_id = cigar_id
    else:
        db.add(ScraperNameAlias(source_slug=source_slug, raw_name=raw_name, cigar_id=cigar_id))


# ── GET 表单 ───────────────────────────────────────────────────────────────────

@router.get("/match/{unmatched_id}", response_class=HTMLResponse)
async def match_form(unmatched_id: int, request: Request):
    if not _require_admin(request):
        return RedirectResponse("/admin/login")

    async with AsyncSessionLocal() as db:
        item = await db.get(UnmatchedItem, unmatched_id)
        if not item:
            return HTMLResponse("<h3>条目不存在</h3>", status_code=404)

        cigars_result = await db.execute(select(Cigar).order_by(Cigar.name))
        all_cigars = cigars_result.scalars().all()

        brands_result = await db.execute(select(Brand).order_by(Brand.name))
        all_brands = brands_result.scalars().all()

        series_result = await db.execute(select(Series).order_by(Series.name))
        all_series = series_result.scalars().all()

        categories_result = await db.execute(
            select(Category).order_by(Category.sort_order, Category.id)
        )
        all_categories = categories_result.scalars().all()

        # Build category_id → dominant series_id mapping (via cigar.category_id)
        # For each catalog category, find which series most of its cigars belong to
        from sqlalchemy import text as _sql
        cat_series_rows = await db.execute(_sql("""
            SELECT category_id, series_id, COUNT(*) as cnt
            FROM cigars
            WHERE category_id IS NOT NULL
            GROUP BY category_id, series_id
            ORDER BY category_id, cnt DESC
        """))
        cat_series_map: dict[int, int] = {}
        for row in cat_series_rows:
            cid, sid = row[0], row[1]
            if cid not in cat_series_map:   # keep first = most common
                cat_series_map[cid] = sid

        existing_result = await db.execute(
            select(ScraperNameAlias).where(
                ScraperNameAlias.source_slug == item.source_slug,
                ScraperNameAlias.raw_name == item.raw_name,
            )
        )
        existing_alias = existing_result.scalar_one_or_none()

    # 自动检测 edition
    auto_edition_type, auto_edition = detect_edition(item.raw_name)

    cigar_options = "\n".join(
        f'<option value="{c.id}"'
        + (" selected" if existing_alias and existing_alias.cigar_id == c.id else "")
        + f">{c.name}</option>"
        for c in all_cigars
    )
    # parent 选项（供新建特别版时指定父雪茄）
    parent_options = '<option value="">— 无（标准版）—</option>\n' + "\n".join(
        f'<option value="{c.id}">{c.name}</option>'
        for c in all_cigars if not c.edition_type  # 只列标准版作为父节点
    )
    brand_options = "\n".join(
        f'<option value="{b.id}">{b.name}</option>' for b in all_brands
    )

    brands_json = json.dumps(
        [{"id": b.id, "name": b.name} for b in all_brands]
    )
    series_json = json.dumps(
        [{"id": s.id, "name": s.name, "brand_id": s.brand_id, "slug": s.slug} for s in all_series]
    )
    categories_json = json.dumps([
        {"id": c.id, "brand_id": c.brand_id, "parent_id": c.parent_id,
         "name": c.name, "sort_order": c.sort_order}
        for c in all_categories
    ])
    cat_series_json = json.dumps(cat_series_map)   # category_id → dominant series_id
    cigars_json = json.dumps(
        [{"id": c.id, "name": c.name, "series_id": c.series_id,
          "vitola": c.vitola, "length_mm": c.length_mm, "ring_gauge": c.ring_gauge}
         for c in all_cigars]
    )

    existing_banner = (
        '<div class="banner-warn">⚠️ 该条目已有别名映射，提交将覆盖。</div>'
        if existing_alias else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>创建匹配别名</title>
<style>
  *{{box-sizing:border-box}}
  body{{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 20px;color:#1e293b}}
  h2{{margin-bottom:4px}}
  .sub{{color:#64748b;margin-bottom:20px;font-size:14px}}
  .banner-warn{{background:#fef9c3;border:1px solid #eab308;padding:10px 16px;border-radius:6px;margin-bottom:16px;font-size:14px}}
  .info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-bottom:20px}}
  .info-item label{{font-size:11px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px}}
  .info-item .val{{font-size:14px;color:#1e293b;margin-top:2px;word-break:break-all}}
  .info-item .val.score{{font-family:monospace}}
  .tabs{{display:flex;gap:0;margin-bottom:20px;border-bottom:2px solid #e2e8f0}}
  .tab{{padding:10px 20px;cursor:pointer;font-size:14px;font-weight:500;color:#64748b;border-bottom:2px solid transparent;margin-bottom:-2px;user-select:none}}
  .tab.active{{color:#3b82f6;border-bottom-color:#3b82f6}}
  .panel{{display:none}}.panel.active{{display:block}}
  .field{{margin-bottom:14px}}
  label.lbl{{display:block;font-size:13px;font-weight:600;margin-bottom:5px;color:#374151}}
  select,input[type=text]{{width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px}}
  select[size]{{height:auto}}
  .hint{{font-size:12px;color:#9ca3af;margin-top:3px}}
  .row2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
  .or-divider{{text-align:center;color:#94a3b8;font-size:12px;margin:6px 0}}
  .actions{{display:flex;gap:12px;margin-top:24px;align-items:center}}
  .btn-primary{{padding:10px 24px;background:#3b82f6;color:#fff;border:none;border-radius:6px;font-size:14px;cursor:pointer;font-weight:600}}
  .btn-primary:hover{{background:#2563eb}}
  .back{{color:#6b7280;text-decoration:none;font-size:14px}}
  .back:hover{{color:#111}}
  .auto-badge{{font-size:11px;background:#dcfce7;color:#166534;padding:2px 8px;border-radius:10px;margin-left:8px;vertical-align:middle}}
</style>
</head>
<body>
<h2>创建匹配别名</h2>
<p class="sub">将爬取到的原始名称绑定到数据库中的雪茄，下次爬取时自动命中。</p>

{existing_banner}

<div class="info-grid">
  <div class="info-item"><label>来源站点</label><div class="val">{item.source_slug}</div></div>
  <div class="info-item"><label>匹配分数</label><div class="val score">{item.match_score or 0:.3f} → {item.best_candidate or '—'}</div></div>
  <div class="info-item" style="grid-column:1/-1"><label>原始名称</label><div class="val">{item.raw_name}</div></div>
  <div class="info-item" style="grid-column:1/-1"><label>原始链接</label><div class="val">{f'<a href="{item.product_url}" target="_blank" rel="noopener" style="color:#3b82f6">{item.product_url}</a>' if item.product_url else '—'}</div></div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('existing')">选择已有雪茄</div>
  <div class="tab" onclick="switchTab('create')">新建雪茄 <span class="auto-badge">自动批量匹配</span></div>
</div>

<!-- ── 选择已有雪茄 ─────────────────────────── -->
<div id="panel-existing" class="panel active">
  <form method="post" action="/admin-tools/match">
    <input type="hidden" name="action" value="select">
    <input type="hidden" name="unmatched_id" value="{item.id}">
    <input type="hidden" name="source_slug" value="{item.source_slug}">
    <input type="hidden" name="raw_name" value="{item.raw_name}">

    <div class="field">
      <label class="lbl">搜索过滤</label>
      <input type="text" id="search-existing" placeholder="输入名称过滤列表…" oninput="filterExisting(this.value)">
    </div>
    <div class="field">
      <label class="lbl">选择雪茄 *</label>
      <select name="cigar_id" id="sel-existing" size="10" required>
        {cigar_options}
      </select>
      <p class="hint">点击选中后提交</p>
    </div>
    <div class="actions">
      <button class="btn-primary" type="submit">确认绑定</button>
      <a class="back" href="/admin/unmatched-item/list">← 返回</a>
    </div>
  </form>
</div>

<!-- ── 新建雪茄 ────────────────────────────── -->
<div id="panel-create" class="panel">
  <form method="post" action="/admin-tools/match">
    <input type="hidden" name="action" value="create">
    <input type="hidden" name="unmatched_id" value="{item.id}">
    <input type="hidden" name="source_slug" value="{item.source_slug}">
    <input type="hidden" name="raw_name" value="{item.raw_name}">
    <input type="hidden" name="category_id" id="inp-category-id" value="">

    <div class="field">
      <label class="lbl">品牌 *</label>
      <select id="sel-brand" name="brand_id" onchange="onBrandChange()" style="margin-bottom:6px">
        <option value="">— 选择已有品牌 —</option>
        {brand_options}
      </select>
      <div class="or-divider">或</div>
      <input type="text" name="brand_name" id="inp-brand-name" placeholder="新品牌名（填写后忽略上方选择）">
      <p class="hint">填写新品牌名则自动建立品牌，留空则使用上方选择</p>
    </div>

    <div class="field">
      <label class="lbl">分类（从 Catalog 目录选择）</label>
      <div id="cat-tree-sel" style="border:1px solid #d1d5db;border-radius:6px;padding:8px 10px;
           max-height:220px;overflow-y:auto;background:#fafafa;font-size:14px">
        <span style="color:#9ca3af">先选品牌</span>
      </div>
      <div id="cat-path-display" style="margin-top:6px;font-size:12px;color:#0071e3;display:none">
        ✓ 已选：<span id="cat-path-text"></span>
      </div>
    </div>

    <div class="field">
      <label class="lbl">系列（自动匹配，可覆盖）</label>
      <select id="sel-series" name="series_id" style="margin-bottom:6px" onchange="onSeriesChange()">
        <option value="">— 先选分类 —</option>
      </select>
      <div class="or-divider">或</div>
      <input type="text" name="series_name" id="inp-series-name" placeholder="新系列名（填写后忽略上方选择）">
      <p class="hint">选择分类后自动推荐系列，也可手动选择或填写新系列名</p>
    </div>

    <div class="field">
      <label class="lbl">父雪茄（特别版时选择对应标准版）</label>
      <select id="sel-parent" name="parent_cigar_id" onchange="onParentChange()">
        {parent_options}
      </select>
      <p class="hint">选择后名称/规格自动继承，前端将显示「所有版本」切换栏</p>
    </div>

    <div class="row2">
      <div class="field">
        <label class="lbl">雪茄名称 *</label>
        <input type="text" id="inp-cigar-name" name="cigar_name" value="{item.raw_name}" required>
        <p class="hint" id="hint-cigar-name">可编辑为标准名称</p>
      </div>
      <div class="field">
        <label class="lbl">茄型（可选）</label>
        <input type="text" id="inp-vitola" name="vitola" placeholder="如 Robusto / No.2">
      </div>
    </div>

    <div class="row2">
      <div class="field">
        <label class="lbl">长度 mm（可选）</label>
        <input type="text" id="inp-length" name="length_mm" placeholder="如 124">
      </div>
      <div class="field">
        <label class="lbl">环径（可选）</label>
        <input type="text" id="inp-ring" name="ring_gauge" placeholder="如 50">
      </div>
    </div>

    <div class="row2">
      <div class="field">
        <label class="lbl">版本类型（自动检测）</label>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:4px">
          {''.join(
            f'''<label style="cursor:pointer">
              <input type="radio" name="edition_type" value="{val}"
                     {'checked' if auto_edition_type == val else ''}
                     style="display:none" class="et-radio">
              <span class="et-badge" style="
                display:inline-flex;align-items:center;gap:4px;
                font-size:12px;font-weight:600;
                padding:5px 11px;border-radius:8px;border:2px solid {border};
                background:{bg};color:{color};
                outline: {'3px solid #3b82f6' if auto_edition_type == val else 'none'};
                outline-offset:2px;
              ">{icon} {label}</span>
            </label>'''
            for val, bg, border, color, icon, label in [
              ('edicion_limitada', '#ede9fe','#c4b5fd','#5b21b6','✦','Edición Limitada'),
              ('regional',         '#d1fae5','#6ee7b7','#065f46','🌍','Regional'),
              ('reserva',          '#fef3c7','#fcd34d','#92400e','🍂','Reserva'),
              ('gran_reserva',     '#fff7ed','#fb923c','#7c2d12','🔥','Gran Reserva'),
              ('aniversario',      '#fce7f3','#f9a8d4','#9d174d','★','Aniversario'),
              ('lcdh',             '#f0f9ff','#7dd3fc','#0c4a6e','🏛','LCDH'),
            ]
          )}
          <label style="cursor:pointer">
            <input type="radio" name="edition_type" value=""
                   {'checked' if not auto_edition_type else ''}
                   style="display:none" class="et-radio">
            <span class="et-badge" style="
              display:inline-flex;align-items:center;
              font-size:12px;font-weight:600;
              padding:5px 11px;border-radius:8px;border:2px solid #d1d5db;
              background:#f9fafb;color:#6b7280;
              outline: {'3px solid #3b82f6' if not auto_edition_type else 'none'};
              outline-offset:2px;
            ">标准版（留空）</span>
          </label>
        </div>
        <p class="hint">点击选择，蓝色外框为当前选中</p>
      </div>
      <div class="field">
        <label class="lbl">版本标签（自动检测）</label>
        <input type="text" name="edition" value="{auto_edition or ''}"
               placeholder="如 Cosecha 2014 / Edición Limitada 2021">
      </div>
    </div>
<script>
document.querySelectorAll('.et-radio').forEach(function(radio) {{
  radio.addEventListener('change', function() {{
    document.querySelectorAll('.et-badge').forEach(function(badge) {{
      badge.style.outline = 'none';
    }});
    if (this.checked) {{
      this.nextElementSibling.style.outline = '3px solid #3b82f6';
      this.nextElementSibling.style.outlineOffset = '2px';
    }}
  }});
}});
</script>

    <div class="actions">
      <button class="btn-primary" type="submit">新建并绑定</button>
      <a class="back" href="/admin/unmatched-item/list">← 返回</a>
    </div>
  </form>
</div>

<script>
const ALL_BRANDS     = {brands_json};
const ALL_SERIES     = {series_json};
const ALL_CIGARS     = {cigars_json};
const ALL_CATEGORIES = {categories_json};
const CAT_SERIES_MAP = {cat_series_json};  // category_id → dominant series_id

function switchTab(name) {{
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', (name==='existing'&&i===0)||(name==='create'&&i===1)));
  document.getElementById('panel-existing').classList.toggle('active', name==='existing');
  document.getElementById('panel-create').classList.toggle('active', name==='create');
}}

// 已有雪茄列表过滤
const existingOpts = Array.from(document.getElementById('sel-existing').options).map(o => ({{value:o.value,text:o.text,selected:o.selected}}));
function filterExisting(q) {{
  const sel = document.getElementById('sel-existing');
  const lower = q.toLowerCase();
  sel.innerHTML = '';
  existingOpts.filter(o => !q || o.text.toLowerCase().includes(lower)).forEach(o => {{
    const opt = document.createElement('option');
    opt.value = o.value; opt.text = o.text;
    if (o.selected) opt.selected = true;
    sel.appendChild(opt);
  }});
}}

// 品牌切换 → 构建 catalog 分类树选择器 + 填充系列下拉（备用）
function onBrandChange() {{
  const brandId  = parseInt(document.getElementById('sel-brand').value);
  const brandCats = ALL_CATEGORIES.filter(c => c.brand_id === brandId);
  const brandSeries = ALL_SERIES.filter(s => s.brand_id === brandId);

  // Reset
  document.getElementById('inp-category-id').value = '';
  document.getElementById('cat-path-display').style.display = 'none';
  buildSeriesSelect(brandSeries);   // populate series dropdown (backup)

  // Build category tree widget
  const container = document.getElementById('cat-tree-sel');
  if (!brandId || !brandCats.length) {{
    container.innerHTML = '<span style="color:#9ca3af">' + (!brandId ? '先选品牌' : '该品牌暂无分类，请先在 Catalog 管理页建立') + '</span>';
    updateParentCigars(null);
    return;
  }}
  container.innerHTML = buildCatTreeHtml(null, brandCats, 0);
  updateParentCigars(null);
}}

function buildCatTreeHtml(parentId, brandCats, depth) {{
  const kids = brandCats
    .filter(c => (c.parent_id ?? null) === parentId)
    .sort((a, b) => a.sort_order - b.sort_order);
  if (!kids.length) return '';
  return kids.map(c => {{
    const children = buildCatTreeHtml(c.id, brandCats, depth + 1);
    const hasChildren = brandCats.some(x => x.parent_id === c.id);
    const indent = depth * 16;
    return `<div style="margin-left:${{indent}}px">
      <div class="cat-row" data-cat-id="${{c.id}}" onclick="onCatSelect(${{c.id}})"
           style="padding:5px 8px;border-radius:6px;cursor:pointer;display:flex;align-items:center;gap:6px">
        <span style="font-size:12px;color:#94a3b8">${{hasChildren ? '▸' : '◦'}}</span>
        <span style="font-size:14px">${{c.name}}</span>
      </div>
      ${{children}}
    </div>`;
  }}).join('');
}}

// 用户点击 catalog 分类 → 设置 category_id + 自动推荐系列
function onCatSelect(catId) {{
  // Highlight selected row
  document.querySelectorAll('.cat-row').forEach(el => {{
    el.style.background = el.dataset.catId == catId ? '#dbeafe' : '';
    el.style.fontWeight = el.dataset.catId == catId ? '600' : '';
  }});

  document.getElementById('inp-category-id').value = catId;

  // Build breadcrumb path
  const path = [];
  let cur = ALL_CATEGORIES.find(c => c.id === catId);
  while (cur) {{
    path.unshift(cur.name);
    cur = cur.parent_id ? ALL_CATEGORIES.find(c => c.id === cur.parent_id) : null;
  }}
  document.getElementById('cat-path-text').textContent = path.join(' › ');
  document.getElementById('cat-path-display').style.display = '';

  // Auto-select dominant series for this category
  const domSeriesId = CAT_SERIES_MAP[String(catId)];
  const sel = document.getElementById('sel-series');
  if (domSeriesId) {{
    sel.value = String(domSeriesId);
    updateParentCigars(domSeriesId);
  }} else {{
    sel.value = '';
    updateParentCigars(null);
  }}
}}

function buildSeriesSelect(brandSeries) {{
  const sel = document.getElementById('sel-series');
  sel.innerHTML = '<option value="">— 自动 / 手动选择 —</option>';
  brandSeries.forEach(s => {{
    const opt = document.createElement('option');
    opt.value = s.id;
    const hint = s.slug.replace(/^[a-z0-9]+-/, '');
    opt.text = hint && hint !== s.name.toLowerCase().replace(/\s+/g,'-')
      ? s.name + '  [' + hint + ']' : s.name;
    sel.appendChild(opt);
  }});
}}

// 系列手动切换 → 更新父雪茄下拉（不覆盖已选分类）
function onSeriesChange() {{
  const seriesId = parseInt(document.getElementById('sel-series').value) || null;
  updateParentCigars(seriesId);
}}

// 父雪茄选择 → 自动填充并锁定名称/规格
function onParentChange() {{
  const parentId = parseInt(document.getElementById('sel-parent').value) || null;
  const nameInp   = document.getElementById('inp-cigar-name');
  const vitolaInp = document.getElementById('inp-vitola');
  const lengthInp = document.getElementById('inp-length');
  const ringInp   = document.getElementById('inp-ring');
  const hint      = document.getElementById('hint-cigar-name');
  const lockStyle = 'background:#f1f5f9;color:#64748b;cursor:not-allowed;border-color:#e2e8f0';

  if (!parentId) {{
    // 清空父雪茄 → 解锁
    [nameInp, vitolaInp, lengthInp, ringInp].forEach(el => {{
      el.readOnly = false; el.style.cssText = '';
    }});
    hint.textContent = '可编辑为标准名称';
    return;
  }}

  const parent = ALL_CIGARS.find(c => c.id === parentId);
  if (!parent) return;

  nameInp.value   = parent.name;
  vitolaInp.value = parent.vitola || '';
  lengthInp.value = parent.length_mm != null ? parent.length_mm : '';
  ringInp.value   = parent.ring_gauge != null ? parent.ring_gauge : '';

  [nameInp, vitolaInp, lengthInp, ringInp].forEach(el => {{
    el.readOnly = true; el.style.cssText = lockStyle;
  }});
  hint.textContent = '已从父雪茄继承，不可修改';
}}

// 根据 seriesId 过滤父雪茄列表（只列标准版）
function updateParentCigars(seriesId) {{
  const sel = document.getElementById('sel-parent');
  sel.innerHTML = '<option value="">— 无（标准版）—</option>';
  const filtered = ALL_CIGARS.filter(c => {{
    if (c.series_id === undefined) return false; // 无 series_id 数据时跳过
    if (seriesId) return c.series_id === seriesId;
    // 未选系列时：若选了品牌则按品牌下所有系列过滤
    const brandId = parseInt(document.getElementById('sel-brand').value) || null;
    if (brandId) {{
      const brandSeriesIds = new Set(ALL_SERIES.filter(s => s.brand_id === brandId).map(s => s.id));
      return brandSeriesIds.has(c.series_id);
    }}
    return true; // 品牌系列都未选，显示全部
  }});
  filtered.forEach(c => {{
    const opt = document.createElement('option');
    opt.value = c.id; opt.text = c.name;
    sel.appendChild(opt);
  }});
}}
</script>
</body>
</html>"""

    return HTMLResponse(html)


# ── POST 处理 ──────────────────────────────────────────────────────────────────

@router.post("/match", response_class=HTMLResponse)
async def match_submit(
    request: Request,
    action: str = Form(...),
    unmatched_id: int = Form(...),
    source_slug: str = Form(...),
    raw_name: str = Form(...),
    # 选择已有雪茄
    cigar_id: Optional[int] = Form(None),
    # 新建雪茄
    brand_id: Optional[str] = Form(None),
    brand_name: Optional[str] = Form(None),
    series_id: Optional[str] = Form(None),
    series_name: Optional[str] = Form(None),
    cigar_name: Optional[str] = Form(None),
    vitola: Optional[str] = Form(None),
    length_mm: Optional[str] = Form(None),
    ring_gauge: Optional[str] = Form(None),
    edition_type: Optional[str] = Form(None),
    edition: Optional[str] = Form(None),
    parent_cigar_id: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
):
    if not _require_admin(request):
        return RedirectResponse("/admin/login")

    async with AsyncSessionLocal() as db:

        if action == "select":
            # ── 绑定已有雪茄 ──────────────────────────
            await _upsert_alias(db, source_slug, raw_name, cigar_id)
            item = await db.get(UnmatchedItem, unmatched_id)
            if item:
                await db.delete(item)
            await db.commit()

        elif action == "create":
            # ── 新建品牌 ──────────────────────────────
            brand_name = (brand_name or "").strip()
            brand_id_int = int(brand_id) if brand_id and brand_id.strip() else None
            if brand_name:
                brand = await _get_or_create_brand(db, brand_name)
            elif brand_id_int:
                brand = await db.get(Brand, brand_id_int)
            else:
                return HTMLResponse("<h3>请选择或填写品牌</h3>", status_code=400)

            # ── 新建系列 ──────────────────────────────
            series_name = (series_name or "").strip()
            series_id_int = int(series_id) if series_id and series_id.strip() else None
            if series_name:
                series = await _get_or_create_series(db, series_name, brand.id)
            elif series_id_int:
                series = await db.get(Series, series_id_int)
            else:
                return HTMLResponse("<h3>请选择或填写系列</h3>", status_code=400)

            # ── 新建雪茄 ──────────────────────────────
            cigar_name = (cigar_name or raw_name).strip()
            base_slug = _slugify(cigar_name)
            slug = await _unique_cigar_slug(db, base_slug)

            lmm = float(length_mm) if length_mm and length_mm.strip() else None
            rg  = float(ring_gauge) if ring_gauge and ring_gauge.strip() else None

            # edition：优先用表单填写，若为空则自动检测
            et = (edition_type or "").strip() or None
            el = (edition or "").strip() or None
            if not et:
                et, el = detect_edition(cigar_name)
            pid = int(parent_cigar_id) if parent_cigar_id and parent_cigar_id.strip() else None

            cat_id = int(category_id) if category_id and category_id.strip() else None

            new_cigar = Cigar(
                series_id=series.id,
                name=cigar_name,
                slug=slug,
                vitola=vitola.strip() if vitola and vitola.strip() else None,
                length_mm=lmm,
                ring_gauge=rg,
                edition_type=et,
                edition=el,
                parent_cigar_id=pid,
                category_id=cat_id,
            )
            db.add(new_cigar)
            await db.flush()  # 获取 new_cigar.id
            cigar_id = new_cigar.id

            # ── 建立当前条目的别名 ────────────────────
            await _upsert_alias(db, source_slug, raw_name, cigar_id)

            # ── 删除当前条目 ──────────────────────────
            item = await db.get(UnmatchedItem, unmatched_id)
            if item:
                await db.delete(item)

            # ── 扫描同来源未匹配条目，批量建立别名并删除 ───
            unmatched_result = await db.execute(
                select(UnmatchedItem).where(UnmatchedItem.source_slug == source_slug)
            )
            others = unmatched_result.scalars().all()
            auto_count = 0
            for u in others:
                score = similarity(u.raw_name, cigar_name)
                if score > 0.75:
                    await _upsert_alias(db, source_slug, u.raw_name, cigar_id)
                    await db.delete(u)
                    auto_count += 1

            await db.commit()

            if auto_count:
                return HTMLResponse(
                    f"""<html><head><meta charset="utf-8">
                    <style>body{{font-family:system-ui;max-width:500px;margin:60px auto;padding:0 20px}}</style>
                    </head><body>
                    <h3>✅ 新建成功</h3>
                    <p>雪茄「{cigar_name}」已建立，别名已绑定。</p>
                    <p>另外自动匹配了 <strong>{auto_count}</strong> 条相似的未匹配记录。</p>
                    <p><a href="/admin/unmatched-item/list">← 返回未匹配列表</a></p>
                    </body></html>"""
                )

    return RedirectResponse("/admin/unmatched-item/list", status_code=303)


# ── 爬虫触发（session 鉴权，供 SQLAdmin 页内 JS 调用）─────────────────────────

@router.post("/trigger", summary="触发全站爬取")
async def trigger_all(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from app.scheduler.tasks import run_all_scrapers
    asyncio.create_task(run_all_scrapers())
    return JSONResponse({"status": "triggered", "target": "all"})


@router.post("/trigger/{source_slug}", summary="触发单站爬取")
async def trigger_one(source_slug: str, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    import app.scrapers.sites  # noqa: F401
    from app.scrapers.registry import get_by_slug
    from app.scheduler.tasks import run_single_scraper
    if not get_by_slug(source_slug):
        return JSONResponse({"error": f"未知站点: {source_slug}"}, status_code=404)
    asyncio.create_task(run_single_scraper(source_slug))
    return JSONResponse({"status": "triggered", "target": source_slug})
