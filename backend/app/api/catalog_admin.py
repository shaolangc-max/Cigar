"""
/admin-tools/catalog — 品牌分类目录管理页面（需要 admin session）

功能：
  - 按品牌管理多级分类树（增删改、排序、父子关系）—— 即时保存
  - 将雪茄手工分配到分类（category_id）—— 暂存，统一保存
  - 查看并处理未匹配条目（按品牌过滤）
  - 雪茄行显示各来源网站小图标链接
"""
import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.db import AsyncSessionLocal
from app.models.brand import Brand
from app.models.category import Category
from app.models.cigar import Cigar
from app.models.price import Price
from app.models.series import Series
from app.models.source import Source
from app.models.scraper_run import UnmatchedItem
from app.models.alias import ScraperNameAlias
from app.models.ignored_raw_name import IgnoredRawName
from app.models.price import Price, PriceHistory
from app.scrapers.matcher import similarity
from sqlalchemy import select, func, text as _sql

router = APIRouter(prefix="/admin-tools/catalog", tags=["catalog-admin"])


def _require_admin(request: Request) -> bool:
    return request.session.get("admin", False)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


async def _unique_cat_slug(db, base_slug: str) -> str:
    slug = base_slug
    i = 2
    while True:
        r = await db.execute(select(Category).where(Category.slug == slug))
        if not r.scalar_one_or_none():
            return slug
        slug = f"{base_slug}-{i}"
        i += 1


# ── HTML 主页 ──────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def catalog_page(request: Request):
    if not _require_admin(request):
        return HTMLResponse("Unauthorized", status_code=401)

    async with AsyncSessionLocal() as db:
        brands_r = await db.execute(select(Brand).order_by(Brand.name))
        brands = brands_r.scalars().all()
        unmatched_total_r = await db.execute(
            select(func.count()).select_from(UnmatchedItem)
        )
        unmatched_total = unmatched_total_r.scalar() or 0

    brand_opts = "\n".join(
        f'<option value="{b.id}" data-name="{b.name}">{b.name}</option>'
        for b in brands
    )

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>分类目录管理</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f5f5f7; color: #1d1d1f; min-height: 100vh; }}
  .topbar {{ background: rgba(255,255,255,0.9); backdrop-filter: blur(20px);
             border-bottom: 1px solid #e0e0e5; padding: 0 20px;
             display: flex; align-items: center; gap: 14px; height: 52px;
             position: sticky; top: 0; z-index: 200; }}
  .topbar a {{ color: #0071e3; text-decoration: none; font-size: 14px; }}
  .topbar h1 {{ font-size: 17px; font-weight: 600; flex: 1; }}
  select {{ font-family: inherit; font-size: 14px; }}
  .brand-select {{ padding: 7px 10px; border: 1px solid #d0d0d5; border-radius: 8px;
                   background: #fff; max-width: 220px; width: 220px; }}
  /* layout */
  .layout {{ display: flex; height: calc(100vh - 52px); overflow: hidden; }}
  .panel {{ overflow-y: auto; padding: 16px; }}
  .panel-left {{ width: 300px; min-width: 160px; max-width: 640px;
                 flex-shrink: 0; border-right: 1px solid #e0e0e5; background: #fff; }}
  .panel-right {{ flex: 1; min-width: 0; background: #f5f5f7; padding-bottom: 80px;
                  overflow-y: auto; }}
  .resizer {{ width: 5px; flex-shrink: 0; cursor: col-resize; background: transparent;
              transition: background .15s; position: relative; z-index: 10; }}
  .resizer:hover, .resizer.is-dragging {{ background: #0071e3; }}
  /* cards */
  .card {{ background: #fff; border-radius: 12px; border: 1px solid #e0e0e5;
           padding: 14px; margin-bottom: 14px; }}
  .card h3 {{ font-size: 12px; font-weight: 600; color: #86868b;
              letter-spacing: .05em; text-transform: uppercase; margin-bottom: 10px; }}
  /* tabs */
  .tabs {{ display: flex; border-bottom: 1px solid #e0e0e5; margin-bottom: 14px; gap: 2px; }}
  .tab {{ padding: 8px 14px; font-size: 14px; cursor: pointer; border-radius: 8px 8px 0 0;
          color: #86868b; border: 1px solid transparent; border-bottom: none; user-select: none; }}
  .tab.active {{ color: #1d1d1f; background: #fff; border-color: #e0e0e5;
                 margin-bottom: -1px; font-weight: 500; }}
  .tab-count {{ font-size: 11px; background: #e0e0e5; border-radius: 10px;
                padding: 1px 6px; margin-left: 4px; color: #555; }}
  .tab.active .tab-count {{ background: #0071e3; color: #fff; }}
  /* buttons */
  .btn {{ padding: 7px 14px; border-radius: 8px; border: none; cursor: pointer;
          font-size: 13px; font-weight: 500; transition: opacity .15s; }}
  .btn:hover {{ opacity: .8; }}
  .btn-primary {{ background: #0071e3; color: #fff; }}
  .btn-danger  {{ background: #ff3b30; color: #fff; }}
  .btn-ghost   {{ background: #f5f5f7; color: #1d1d1f; border: 1px solid #d0d0d5; }}
  .btn-sm      {{ padding: 4px 10px; font-size: 12px; }}
  /* tree */
  .tree-item {{ display: flex; align-items: center; gap: 6px; padding: 6px 8px;
                border-radius: 8px; cursor: pointer; transition: background .15s; }}
  .tree-item:hover {{ background: #f5f5f7; }}
  .tree-item.selected {{ background: #e8f0fe; }}
  .tree-item .name {{ flex: 1; font-size: 14px; }}
  .cat-toggle {{ width: 16px; height: 16px; display: inline-flex; align-items: center;
                 justify-content: center; font-size: 9px; color: #86868b; flex-shrink: 0;
                 border-radius: 4px; transition: background .1s; }}
  .cat-toggle:hover {{ background: #d0d8ff; color: #0071e3; }}
  .cat-toggle-ph {{ width: 16px; flex-shrink: 0; }}
  .cat-edit-btn {{ opacity: 0; font-size: 11px; color: #86868b; cursor: pointer;
                   padding: 1px 4px; border-radius: 4px; transition: opacity .15s; flex-shrink:0; }}
  .tree-item:hover .cat-edit-btn {{ opacity: 1; }}
  .cat-edit-btn:hover {{ background: #e8f0fe; color: #0071e3; }}
  .cat-add-btn {{ opacity: 0; font-size: 14px; font-weight: 700; color: #86868b; cursor: pointer;
                  padding: 0 4px; border-radius: 4px; transition: opacity .15s; flex-shrink:0; line-height:1; }}
  .tree-item:hover .cat-add-btn {{ opacity: 1; }}
  .cat-add-btn:hover {{ background: #e8ffe8; color: #22c55e; }}
  .cat-inline-input {{ font-size: 13px; font-weight: 600; border: 1.5px solid #0071e3;
                       border-radius: 4px; padding: 0 6px; outline: none; background: #fff;
                       min-width: 80px; max-width: 180px; height: 22px; }}
  .inline-add-row {{ display: flex; align-items: center; gap: 8px; padding: 3px 8px; }}
  .inline-add-hint {{ font-size: 11px; color: #aaa; }}
  .drag-handle {{ cursor: grab; color: #c8c8d0; font-size: 13px; flex-shrink:0;
                  padding: 0 3px; user-select:none; }}
  .drag-handle:hover {{ color: #86868b; }}
  .drag-handle:active {{ cursor: grabbing; }}
  .tree-item.drop-before {{ border-top: 2px solid #0071e3; border-radius:0; }}
  .tree-item.drop-after  {{ border-bottom: 2px solid #0071e3; border-radius:0; }}
  .tree-item.drop-into   {{ background: #ddeaff; outline: 2px solid #0071e3; border-radius:8px; }}
  .indent-1 {{ margin-left: 0; }}
  .indent-2 {{ margin-left: 20px; }}
  .indent-3 {{ margin-left: 40px; }}
  .indent-4 {{ margin-left: 60px; }}
  .tree-cigar-handle {{ cursor: grab; color: transparent; font-size: 11px; padding: 0 2px; flex-shrink:0; user-select:none; }}
  .tree-cigar:hover .tree-cigar-handle {{ color: #c8c8d0; }}
  .tree-cigar-handle:hover {{ color: #86868b !important; }}
  .tree-cigar-handle:active {{ cursor: grabbing; }}
  .tree-cigar.drop-before {{ border-top: 2px solid #0071e3; }}
  .tree-cigar.drop-after  {{ border-bottom: 2px solid #0071e3; }}
  .tree-cigar-toggle {{ width:14px;flex-shrink:0;font-size:10px;color:#aaa;cursor:pointer;text-align:center;user-select:none; }}
  .tree-cigar-toggle:hover {{ color:#0071e3; }}
  .tree-source-row {{ display:flex;align-items:center;gap:6px;padding:2px 6px 2px 0;
                      font-size:12px;color:#555;cursor:pointer;border-radius:4px; }}
  .tree-source-row:hover {{ background:#f0f4ff;color:#0071e3; }}
  .tree-source-price {{ font-size:11px;color:#0071e3;flex-shrink:0; }}
  .tree-source-id {{ font-size:10px;color:#bbb;flex-shrink:0; }}
  /* 右侧详情面板 */
  .detail-panel {{ padding:16px;display:none; }}
  .detail-panel.active {{ display:block; }}
  .detail-back {{ font-size:13px;color:#0071e3;cursor:pointer;margin-bottom:14px;display:inline-flex;align-items:center;gap:4px; }}
  .detail-back:hover {{ text-decoration:underline; }}
  .detail-title {{ font-size:18px;font-weight:700;margin-bottom:4px; }}
  .detail-meta {{ font-size:13px;color:#888;margin-bottom:16px; }}
  .detail-section {{ font-size:12px;font-weight:700;color:#aaa;letter-spacing:.06em;text-transform:uppercase;margin:14px 0 8px; }}
  .detail-price-table {{ width:100%;border-collapse:collapse;font-size:13px; }}
  .detail-price-table th {{ text-align:left;padding:5px 8px;border-bottom:2px solid #e0e0e5;color:#888;font-weight:600;font-size:11px; }}
  .detail-price-table td {{ padding:6px 8px;border-bottom:1px solid #f0f0f5; }}
  .detail-price-table tr:hover td {{ background:#f8f9ff; }}
  .detail-alias-row {{ font-size:12px;padding:4px 0;border-bottom:1px solid #f5f5f5;display:flex;gap:8px; }}
  .detail-alias-src {{ color:#0071e3;font-weight:600;flex-shrink:0; }}
  .in-stock-dot {{ display:inline-block;width:7px;height:7px;border-radius:50%; }}
  .tree-cigar {{ display: flex; align-items: flex-start; padding: 3px 8px 3px 0;
                 font-size: 12px; color: #444; cursor: pointer; border-radius: 6px;
                 transition: background .12s; }}
  .tree-cigar:hover {{ background: #eef3ff; color: #0071e3; }}
  .tree-cigar.highlighted {{ background: #ddeaff; }}
  .tree-cigar-dot {{ width: 14px; flex-shrink: 0; text-align: center;
                     color: #c0c0c8; font-size: 9px; }}
  /* form inputs */
  .input-row {{ display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }}
  .input-row label {{ font-size: 13px; color: #86868b; min-width: 56px; }}
  .input-row input, .input-row select {{ flex: 1; padding: 7px 10px;
    border: 1px solid #d0d0d5; border-radius: 8px; font-size: 14px; font-family: inherit; }}
  .btn-row {{ display: flex; gap: 8px; margin-top: 10px; }}
  /* cigar rows */
  .cigar-del-btn {{ opacity: 0; font-size: 13px; color: #aaa; cursor: pointer; padding: 2px 5px;
                   border-radius: 4px; transition: opacity .15s; flex-shrink: 0; }}
  .cigar-row:hover .cigar-del-btn {{ opacity: 1; }}
  .cigar-del-btn:hover {{ background: #fee2e2; color: #dc2626; }}
  .cigar-row {{ display: flex; align-items: center; gap: 8px; padding: 9px 12px;
                border-radius: 10px; border: 1px solid #e0e0e5; margin-bottom: 6px;
                background: #fff; transition: background .2s; }}
  .cigar-row.pending {{ background: #fffbe6; border-color: #f5d76e; }}
  .cigar-row.highlighted {{ background: #ddeaff; border-color: #a0c0ff; transition: background .1s; }}
  .cigar-name {{ flex: 1; min-width: 0; }}
  .cigar-name .cn {{ font-size: 14px; font-weight: 500; white-space: nowrap;
                     overflow: hidden; text-overflow: ellipsis; }}
  .cigar-name .cv {{ font-size: 12px; color: #86868b; margin-top: 1px;
                     cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }}
  .cigar-name .cv:hover {{ color: #0071e3; }}
  .edit-hint {{ font-size: 10px; opacity: 0; transition: opacity .15s; }}
  .cigar-name .cv:hover .edit-hint {{ opacity: 1; }}
  .specs-inputs {{ display: inline-flex; align-items: center; gap: 4px; }}
  .specs-inputs input {{ width: 64px; font-size: 11px; padding: 2px 5px;
                         border: 1px solid #0071e3; border-radius: 5px;
                         font-family: inherit; outline: none; }}
  .specs-inputs button {{ font-size: 11px; padding: 2px 7px; border-radius: 5px;
                          border: 1px solid #d0d0d5; background: #f5f5f7;
                          cursor: pointer; font-family: inherit; }}
  .um-link-row {{ display:flex; gap:4px; margin-top:5px; align-items:center; }}
  .um-link-row input {{ flex:1; min-width:0; font-size:12px; padding:2px 6px;
                        border:1px solid #d0d0d5; border-radius:5px;
                        font-family:inherit; outline:none; }}
  .um-link-row input:focus {{ border-color:#0071e3; }}
  .um-link-btn {{ font-size:11px; padding:2px 8px; border-radius:5px; white-space:nowrap;
                  border:1px solid #0071e3; background:#e8f0ff; color:#0071e3;
                  cursor:pointer; font-family:inherit; flex-shrink:0; }}
  .um-link-btn:hover {{ background:#0071e3; color:#fff; }}
  .source-links {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .src-icon {{ display: inline-block; font-size: 10px; font-weight: 600; padding: 2px 5px;
               border-radius: 5px; background: #f0f0f5; color: #555; text-decoration: none;
               border: 1px solid #d8d8e0; line-height: 1.4; white-space: nowrap; }}
  .src-icon:hover {{ background: #e0e8ff; color: #0071e3; border-color: #b0c8ff; }}
  .ctag {{ font-size: 11px; padding: 2px 8px; border-radius: 20px; white-space: nowrap;
           flex-shrink: 0; }}
  .ctag.has {{ background: #e8f0fe; color: #0071e3; }}
  .ctag.none {{ background: #f5f5f7; color: #86868b; }}
  .cat-select {{ font-size: 12px; padding: 4px 6px; border-radius: 6px;
                 border: 1px solid #d0d0d5; font-family: inherit; min-width: 140px;
                 transition: border-color .2s; }}
  /* filter */
  .filter-row {{ display: flex; gap: 8px; margin-bottom: 12px; }}
  .filter-row input {{ flex: 1; padding: 8px 12px; border: 1px solid #d0d0d5;
                       border-radius: 8px; font-size: 14px; font-family: inherit; }}
  .filter-row select {{ padding: 8px 10px; border: 1px solid #d0d0d5;
                        border-radius: 8px; font-size: 14px; font-family: inherit;
                        background: #fff; max-width: 160px; }}
  /* unmatched rows */
  .um-row {{ background: #fff; border: 1px solid #e0e0e5; border-radius: 10px;
             padding: 10px 12px; margin-bottom: 6px; display: flex;
             align-items: flex-start; gap: 10px; }}
  .um-name {{ flex: 1; font-size: 14px; font-weight: 500; }}
  .um-meta {{ font-size: 12px; color: #86868b; margin-top: 2px; }}
  .um-ignore-btn {{ font-size: 14px; cursor: pointer; color: #c8c8d0; padding: 2px 4px;
                    border-radius: 4px; flex-shrink: 0; line-height: 1; transition: color .15s; }}
  .um-ignore-btn:hover {{ color: #ff3b30; }}
  /* trash bin */
  .trash-section {{ margin-top: 20px; border-top: 1px solid #e8e8ed; padding-top: 12px; }}
  .trash-header {{ display: flex; align-items: center; gap: 8px; cursor: pointer;
                   font-size: 13px; color: #86868b; padding: 4px 0; user-select: none; }}
  .trash-header:hover {{ color: #333; }}
  .trash-toggle {{ font-size: 10px; transition: transform .2s; }}
  .trash-toggle.open {{ transform: rotate(90deg); }}
  .trash-list {{ margin-top: 8px; display: none; }}
  .trash-list.open {{ display: block; }}
  .trash-row {{ display: flex; align-items: center; gap: 8px; padding: 7px 10px;
                background: #fff8f8; border: 1px solid #fde0e0; border-radius: 8px;
                margin-bottom: 5px; font-size: 13px; }}
  .trash-name {{ flex: 1; color: #555; }}
  .trash-src {{ font-size: 11px; color: #aaa; flex-shrink: 0; }}
  .trash-restore-btn {{ font-size: 11px; padding: 2px 8px; border-radius: 5px;
                        border: 1px solid #34c759; background: #eeffee; color: #22a047;
                        cursor: pointer; font-family: inherit; flex-shrink: 0; }}
  .trash-restore-btn:hover {{ background: #d4f8dc; }}
  .score-bar {{ display: inline-block; width: 40px; height: 4px; background: #e0e0e5;
                border-radius: 2px; vertical-align: middle; margin-right: 4px; }}
  .score-fill {{ height: 100%; border-radius: 2px; background: #34c759; }}
  /* floating save bar */
  .save-bar {{ position: fixed; bottom: 0; left: 300px; right: 0; z-index: 300;
               background: rgba(29,29,31,0.95); backdrop-filter: blur(10px);
               color: #fff; padding: 12px 24px; display: flex; align-items: center;
               gap: 12px; transform: translateY(100%); transition: transform .25s ease; }}
  .save-bar.visible {{ transform: translateY(0); }}
  .save-bar .info {{ flex: 1; font-size: 14px; }}
  .save-bar .dot {{ width: 8px; height: 8px; border-radius: 50%;
                    background: #ffd60a; display: inline-block; margin-right: 6px; }}
  /* toast */
  #toast {{ position: fixed; bottom: 24px; right: 24px; background: #1d1d1f; color: #fff;
            border-radius: 10px; padding: 10px 18px; font-size: 14px; opacity: 0;
            transition: opacity .3s; pointer-events: none; z-index: 9999; }}
  #toast.show {{ opacity: 1; }}
  /* empty state */
  .empty {{ color: #86868b; font-size: 13px; padding: 20px 0; text-align: center; }}
</style>
</head>
<body>

<div class="topbar">
  <a href="/admin-tools">← 工具首页</a>
  <h1>分类目录管理</h1>
  <select class="brand-select" id="brand-select" onchange="loadBrand(this.value, this.options[this.selectedIndex].dataset.name)">
    <option value="">— 选择品牌 —</option>
    <option value="__unmatched__" data-name="">全部未匹配 ({unmatched_total:,})</option>
    <optgroup label="──────────────">
    {brand_opts}
    </optgroup>
  </select>
</div>

<div class="layout">
  <!-- Left: category tree -->
  <div class="panel panel-left" id="left-panel">
    <div class="card">
      <h3>分类树</h3>
      <div id="tree-container"><p class="empty">请先选择品牌</p></div>
    </div>
    <div class="card" id="cat-form-card" style="display:none">
      <h3 id="cat-form-title">新建分类</h3>
      <div class="input-row">
        <label>名称</label>
        <input id="cat-name" type="text" placeholder="例如 Handmade Cigars">
      </div>
      <div class="input-row">
        <label>父分类</label>
        <select id="cat-parent"><option value="">（顶级）</option></select>
      </div>
      <div class="input-row">
        <label>排序</label>
        <input id="cat-order" type="number" value="0" style="max-width:80px">
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="saveCategory()">保存分类</button>
        <button class="btn btn-ghost" onclick="cancelCatForm()">取消</button>
        <button class="btn btn-danger btn-sm" id="cat-delete-btn" style="display:none" onclick="deleteCategory()">删除</button>
      </div>
    </div>
    <button class="btn btn-ghost" id="new-cat-btn" style="width:100%;margin-top:4px;display:none"
            onclick="newCategory()">+ 新建分类</button>
  </div>

  <!-- Resizer -->
  <div class="resizer" id="resizer" onmousedown="resizerMouseDown(event)"></div>

  <!-- Right: tabs -->
  <div class="panel panel-right" id="right-panel">
    <div class="tabs">
      <div class="tab active" id="tab-cigars" onclick="switchTab('cigars')">
        雪茄列表 <span class="tab-count" id="tc-cigars">0</span>
      </div>
      <div class="tab" id="tab-unmatched" onclick="switchTab('unmatched')">
        未匹配条目 <span class="tab-count" id="tc-unmatched">0</span>
      </div>
    </div>

    <!-- Cigar detail panel (shown when tree-cigar clicked) -->
    <div id="pane-detail" class="detail-panel">
      <div class="detail-back" onclick="closeDetail()">← 返回列表</div>
      <div id="detail-content"></div>
    </div>

    <!-- Cigar list panel -->
    <div id="pane-cigars">
      <div class="filter-row">
        <input id="cigar-search" type="text" placeholder="搜索雪茄名…" oninput="filterCigars()">
        <select id="cigar-filter-cat" onchange="filterCigars()">
          <option value="">全部</option>
          <option value="__uncat__">未分类</option>
        </select>
      </div>
      <div id="cigar-list"><p class="empty">请先选择品牌</p></div>
    </div>

    <!-- Unmatched panel -->
    <div id="pane-unmatched" style="display:none">
      <div class="filter-row">
        <input id="um-search" type="text" placeholder="搜索原始名称…" oninput="filterUnmatched()">
        <select id="um-filter-source" onchange="filterUnmatched()" style="max-width:180px">
          <option value="">全部来源</option>
        </select>
      </div>
      <div id="unmatched-list"><p class="empty">请先选择品牌</p></div>
      <!-- 垃圾箱 -->
      <div class="trash-section">
        <div class="trash-header" onclick="toggleTrashBin()">
          <span class="trash-toggle" id="trash-toggle">▶</span>
          🗑 垃圾箱
          <span class="tab-count" id="tc-ignored" style="display:none">0</span>
        </div>
        <div class="trash-list" id="trash-list"></div>
      </div>
    </div>
  </div>
</div>

<!-- Floating save bar -->
<div class="save-bar" id="save-bar">
  <span class="dot"></span>
  <span class="info" id="save-info">有 0 项雪茄分配未保存</span>
  <button class="btn btn-ghost btn-sm" onclick="discardChanges()">放弃</button>
  <button class="btn btn-primary" onclick="saveAllChanges()">保存</button>
</div>

<div id="toast"></div>

<script>
let currentBrandId   = null;
let currentBrandName = '';
let categories  = [];
let cigars      = [];
let unmatched   = [];
let pendingChanges = new Map();  // cigar_id → {{oldCatId, newCatId}}
let activeTab   = 'cigars';
let collapsedCats   = new Set();  // category ids that are collapsed in the tree
let expandedCigars  = new Set();  // cigar ids expanded in the tree (showing sources)
let _treeInitialized = false;     // whether collapsedCats has been set for current brand

// ── Toast ──────────────────────────────────────────────────────────────────────
function showToast(text, ok = true) {{
  const el = document.getElementById('toast');
  el.textContent = text;
  el.style.background = ok ? '#1d1d1f' : '#ff3b30';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2500);
}}

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {{
  activeTab = tab;
  document.getElementById('tab-cigars').className    = 'tab' + (tab === 'cigars'    ? ' active' : '');
  document.getElementById('tab-unmatched').className = 'tab' + (tab === 'unmatched' ? ' active' : '');
  document.getElementById('pane-cigars').style.display    = tab === 'cigars'    ? '' : 'none';
  document.getElementById('pane-unmatched').style.display = tab === 'unmatched' ? '' : 'none';
}}

// ── Brand loading ─────────────────────────────────────────────────────────────
async function loadBrand(value, brandName) {{
  const leftPanel  = document.getElementById('left-panel');
  const newCatBtn  = document.getElementById('new-cat-btn');

  if (value === '__unmatched__') {{
    currentBrandId   = '__unmatched__';
    currentBrandName = '';
    leftPanel.style.opacity  = '0.4';
    leftPanel.style.pointerEvents = 'none';
    newCatBtn.style.display  = 'none';
    categories = []; cigars = [];
    renderTree(); filterCigars();
    await loadUnmatched('');
    switchTab('unmatched');
    return;
  }}

  if (!value) return;
  currentBrandId   = parseInt(value);
  currentBrandName = brandName;
  leftPanel.style.opacity  = '1';
  leftPanel.style.pointerEvents = '';
  newCatBtn.style.display  = '';
  pendingChanges.clear();
  updateSaveBar();
  _treeInitialized = false;  // reset so new brand gets fresh collapsed state
  await loadCategories();
  await loadCigars();
  await loadUnmatched(brandName);
}}

// ── Categories ────────────────────────────────────────────────────────────────
async function loadCategories() {{
  const r = await fetch(`/admin-tools/catalog/api/brands/${{currentBrandId}}/categories`);
  categories = await r.json();
  if (!_treeInitialized) {{
    // First load for this brand: collapse every category (all start as ▶)
    collapsedCats = new Set(categories.map(c => c.id));
    _treeInitialized = true;
  }}
  renderTree();
  renderParentSelect();
  populateCategoryFilter();
}}

function countCigarsInCat(catId) {{
  let count = cigars.filter(c => c.category_id === catId).length;
  // factor in pending changes
  pendingChanges.forEach(v => {{
    if (v.newCatId === catId && v.oldCatId !== catId) count++;
    if (v.oldCatId === catId && v.newCatId !== catId) count--;
  }});
  const childCats = categories.filter(c => c.parent_id === catId);
  return count + childCats.reduce((s, ch) => s + countCigarsInCat(ch.id), 0);
}}

function buildTreeHtml(parentId, depth) {{
  const kids = categories.filter(c => (c.parent_id ?? null) === parentId)
                         .sort((a, b) => a.sort_order - b.sort_order);
  if (!kids.length) return '';
  return kids.map(c => {{
    const indent      = `indent-${{Math.min(depth, 4)}}`;
    const count       = countCigarsInCat(c.id);
    const badge       = count > 0
      ? `<span style="font-size:11px;background:#e8f0fe;color:#0071e3;border-radius:10px;padding:1px 7px;flex-shrink:0">${{count}}</span>`
      : `<span style="font-size:11px;color:#c8c8cc;flex-shrink:0">0</span>`;
    const hasKids     = categories.some(ch => ch.parent_id === c.id);
    const hasToggle   = hasKids || count > 0;  // show toggle if has sub-cats OR direct cigars
    const isCollapsed = collapsedCats.has(c.id);
    const toggleBtn   = hasToggle
      ? `<span class="cat-toggle" onclick="toggleCat(${{c.id}},event)" title="${{isCollapsed?'展开':'折叠'}}">${{isCollapsed ? '▶' : '▼'}}</span>`
      : `<span class="cat-toggle-ph"></span>`;
    // cigars directly in this category (using effective cat id to reflect pending changes)
    const directCigars = isCollapsed ? [] : cigars.filter(c2 => effectiveCatId(c2) === c.id);
    const sortedCigars = directCigars.slice().sort((a,b) => (a.sort_order||0)-(b.sort_order||0));
    const cigarListHtml = sortedCigars.map(c2 => {{
      const cigarIndent = 22 + depth * 20;
      const srcIndent   = cigarIndent + 18;
      const hasSrc      = c2.sources && c2.sources.length > 0;
      const isExp       = expandedCigars.has(c2.id);
      const toggleIcon  = hasSrc ? (isExp ? '▼' : '▶') : '';
      const sourcesHtml = (hasSrc && isExp) ? c2.sources.map(s => {{
        const px = s.price_single != null ? `${{s.currency}} ${{s.price_single.toFixed(2)}}` : '';
        const bx = s.price_box    != null ? `盒${{s.currency}} ${{s.price_box.toFixed(2)}}${{s.box_count ? '/'+s.box_count+'支' : ''}}` : '';
        const priceStr = [px, bx].filter(Boolean).join(' · ') || '暂无价格';
        const dot  = `<span class="in-stock-dot" style="background:${{s.in_stock ? '#22c55e' : '#d1d5db'}}"></span>`;
        const link = s.url ? `<a href="${{s.url}}" target="_blank" style="color:inherit;text-decoration:none" title="打开链接">↗</a>` : '';
        return `<div class="tree-source-row" style="margin-left:${{srcIndent}}px"
                     onclick="openDetail(${{c2.id}},event)">
          ${{dot}}<span style="flex:1;overflow:hidden;text-overflow:ellipsis">${{s.name}}</span>
          <span class="tree-source-price">${{priceStr}}</span>
          <span class="tree-source-id">#${{s.price_id}}</span>
          ${{link}}
        </div>`;
      }}).join('') : '';
      return `<div class="tree-cigar" data-cigar-id="${{c2.id}}" data-cat-id="${{c.id}}"
                   style="margin-left:${{cigarIndent}}px" title="${{c2.name}}"
                   draggable="false"
                   ondragstart="treeCigarReorderStart(${{c2.id}},${{c.id}},event)"
                   ondragend="treeCigarReorderEnd(event)"
                   ondragover="treeCigarDragOver(${{c.id}},event)"
                   ondragleave="treeCigarDragLeave(event)"
                   ondrop="treeCigarDrop(${{c.id}},event)">
          <span class="tree-cigar-handle" onmousedown="this.parentElement.draggable=true" title="拖拽排序">⠿</span>
          <span class="tree-cigar-toggle" onclick="toggleCigar(${{c2.id}},event)">${{toggleIcon}}</span>
          <span style="cursor:pointer;flex:1;word-break:break-word" onclick="openDetail(${{c2.id}},event)">${{c2.name}}</span>
          <span style="font-size:10px;color:#aaa;flex-shrink:0;margin-left:4px">#${{c2.id}}</span>
        </div>${{sourcesHtml}}`;
    }}).join('');
    const childHtml = (hasKids && !isCollapsed) ? buildTreeHtml(c.id, depth + 1) : '';
    const nameClick = hasToggle
      ? `onclick="toggleCat(${{c.id}},event)" ondblclick="startInlineRename(${{c.id}},event)"`
      : `ondblclick="startInlineRename(${{c.id}},event)"`;
    return `<div class="tree-item ${{indent}}" draggable="false"
        ondragstart="catDragStart(${{c.id}},event)"
        ondragend="catDragEnd(event);this.draggable=false"
        ondragover="catDragOver(${{c.id}},event)"
        ondragleave="catDragLeave(event)"
        ondrop="catDrop(${{c.id}},event)">
        <span class="drag-handle" title="拖拽移动" onmousedown="this.parentElement.draggable=true">⠿</span>
        ${{toggleBtn}}<span class="name" ${{nameClick}} title="双击更名">${{c.name}}</span>${{badge}}
        <span class="cat-add-btn" onclick="startInlineAdd(${{c.id}},event)" title="新建子分类">＋</span>
        <span class="cat-edit-btn" onclick="editCategory(${{c.id}})" title="编辑分类">✎</span>
      </div>${{cigarListHtml}}${{childHtml}}`;
  }}).join('');
}}

// ── Drag-and-drop (categories + cigars) ──────────────────────────────────────
let dragCatId         = null;
let dragCigarId       = null;
let dragUnmatchedId   = null;
let dragTreeCigarId   = null;   // cigar being reordered inside tree
let dragTreeCigarCat  = null;   // its current catId
let dragExpandTimer   = null;

function _dragReset() {{
  dragCatId = null; dragCigarId = null; dragUnmatchedId = null;
  dragTreeCigarId = null; dragTreeCigarCat = null;
  clearExpandTimer();
}}

function clearExpandTimer() {{
  if (dragExpandTimer) {{ clearTimeout(dragExpandTimer); dragExpandTimer = null; }}
}}

// Cigar drag (right panel → left tree)
function cigarDragStart(cigarId, event) {{
  _dragReset(); dragCigarId = cigarId;
  event.dataTransfer.effectAllowed = 'move';
  setTimeout(() => event.target.style.opacity = '0.45', 0);
}}
function cigarDragEnd(event) {{
  event.target.style.opacity = '';
  clearDropIndicators(); dragCigarId = null;
}}

// Unmatched drag (unmatched tab → left tree)
function unmatchedDragStart(unmatchedId, event) {{
  _dragReset(); dragUnmatchedId = unmatchedId;
  event.dataTransfer.effectAllowed = 'move';
  setTimeout(() => event.target.style.opacity = '0.45', 0);
}}
function unmatchedDragEnd(event) {{
  event.target.style.opacity = '';
  clearDropIndicators(); dragUnmatchedId = null;
}}

// Category drag (reorder / reparent)
function catDragStart(catId, event) {{
  _dragReset(); dragCatId = catId;
  event.dataTransfer.effectAllowed = 'move';
  setTimeout(() => event.target.style.opacity = '0.4', 0);
}}
function catDragEnd(event) {{
  event.target.style.opacity = '';
  clearDropIndicators(); clearExpandTimer();
}}

function catDragLeave(event) {{
  event.currentTarget.classList.remove('drop-before', 'drop-after', 'drop-into');
  clearExpandTimer();
}}

// ── Tree-cigar 排序拖拽 ────────────────────────────────────────────────────────
function treeCigarReorderStart(cigarId, catId, event) {{
  _dragReset();
  dragTreeCigarId  = cigarId;
  dragTreeCigarCat = catId;
  event.dataTransfer.effectAllowed = 'move';
  setTimeout(() => event.target.style.opacity = '0.45', 0);
}}

function treeCigarReorderEnd(event) {{
  event.currentTarget.style.opacity = '';
  event.currentTarget.draggable = false;
  clearTreeCigarIndicators();
  dragTreeCigarId = null; dragTreeCigarCat = null;
}}

function clearTreeCigarIndicators() {{
  document.querySelectorAll('.tree-cigar.drop-before,.tree-cigar.drop-after')
    .forEach(el => el.classList.remove('drop-before','drop-after'));
}}

// 拖入叶节点（tree-cigar 行）→ 分配到该 cigar 所属的同一 category（右面板拖入）
// 或在树内上下排序（dragTreeCigarId 设置时）
function treeCigarDragOver(catId, event) {{
  if (dragTreeCigarId !== null) {{
    event.preventDefault(); event.stopPropagation();
    clearTreeCigarIndicators();
    const half = event.currentTarget.getBoundingClientRect().height / 2;
    const pos  = (event.clientY - event.currentTarget.getBoundingClientRect().top) < half ? 'before' : 'after';
    event.currentTarget.classList.add('drop-' + pos);
    return;
  }}
  if (dragCigarId === null && dragUnmatchedId === null) return;
  event.preventDefault();
  event.stopPropagation();
  event.dataTransfer.dropEffect = 'move';
  clearDropIndicators();
  event.currentTarget.classList.add('highlighted');
}}

function treeCigarDragLeave(event) {{
  event.currentTarget.classList.remove('highlighted','drop-before','drop-after');
}}

async function treeCigarDrop(catId, event) {{
  event.stopPropagation();

  // ── 树内排序 ──────────────────────────────────────────────
  if (dragTreeCigarId !== null) {{
    const fromId  = dragTreeCigarId;
    const fromCat = dragTreeCigarCat;
    dragTreeCigarId = null; dragTreeCigarCat = null;

    const el  = event.currentTarget;
    const pos = el.classList.contains('drop-before') ? 'before' : 'after';
    clearTreeCigarIndicators();
    el.style.opacity = '';

    const targetId = parseInt(el.dataset.cigarId);
    if (fromId === targetId) return;

    // If cross-category, update the cigar's category first (stage it)
    if (fromCat !== catId) stageCigarChange(fromId, String(catId));

    // Build new order for this category (use effective catId to reflect pending)
    const catCigars = cigars
      .filter(c => effectiveCatId(c) === catId)
      .sort((a, b) => (a.sort_order||0) - (b.sort_order||0));
    const fromCigar = cigars.find(c => c.id === fromId);
    if (!fromCigar) return;

    // Remove from current position (may not be in catCigars if cross-cat)
    const fromIdx = catCigars.findIndex(c => c.id === fromId);
    if (fromIdx !== -1) catCigars.splice(fromIdx, 1);

    // Insert before/after target
    const targetIdx = catCigars.findIndex(c => c.id === targetId);
    const insertAt  = pos === 'before' ? targetIdx : targetIdx + 1;
    catCigars.splice(insertAt < 0 ? catCigars.length : insertAt, 0, fromCigar);

    // Persist new sort_order
    const r = await fetch(`/admin-tools/catalog/api/categories/${{catId}}/reorder`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ cigar_ids: catCigars.map(c => c.id) }}),
    }});
    if (!r.ok) {{ showToast('排序保存失败', false); return; }}

    // Update local sort_order so renderTree reflects new order immediately
    catCigars.forEach((c, i) => {{
      const obj = cigars.find(x => x.id === c.id);
      if (obj) obj.sort_order = i;
    }});
    renderTree();
    return;
  }}

  // ── 右面板拖入 ────────────────────────────────────────────
  event.currentTarget.classList.remove('highlighted');
  await catDrop(catId, event);
}}

function catDragOver(catId, event) {{
  const isCigarOrUnmatched = (dragCigarId !== null || dragUnmatchedId !== null || dragTreeCigarId !== null);
  if (isCigarOrUnmatched) {{
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    clearDropIndicators();
    event.currentTarget.classList.add('drop-into');
    // Auto-expand collapsed category after 600ms hover
    if (collapsedCats.has(catId)) {{
      clearExpandTimer();
      dragExpandTimer = setTimeout(() => {{
        collapsedCats.delete(catId);
        renderTree();
      }}, 600);
    }}
    return;
  }}
  if (!dragCatId || dragCatId === catId) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
  clearDropIndicators();
  const pos = getDropPos(event, event.currentTarget);
  event.currentTarget.classList.add('drop-' + pos);
  // Auto-expand if hovering "into" a collapsed category
  if (pos === 'into' && collapsedCats.has(catId)) {{
    clearExpandTimer();
    dragExpandTimer = setTimeout(() => {{
      collapsedCats.delete(catId);
      renderTree();
    }}, 600);
  }} else {{
    clearExpandTimer();
  }}
}}

function getDropPos(event, el) {{
  const rect = el.getBoundingClientRect();
  const y = event.clientY - rect.top;
  const h = rect.height;
  if (y < h * 0.28) return 'before';
  if (y > h * 0.72) return 'after';
  return 'into';
}}

function clearDropIndicators() {{
  document.querySelectorAll('.drop-before,.drop-after,.drop-into')
    .forEach(el => el.classList.remove('drop-before', 'drop-after', 'drop-into'));
}}

async function catDrop(targetCatId, event) {{
  event.preventDefault();
  clearDropIndicators();

  clearExpandTimer();

  // ── Cigar (right panel) → Category drop ───────────────
  if (dragCigarId !== null) {{
    stageCigarChange(dragCigarId, String(targetCatId));
    dragCigarId = null;
    return;
  }}

  // ── Tree-cigar → Category header drop (cross-cat move) ─
  if (dragTreeCigarId !== null) {{
    const cid = dragTreeCigarId;
    dragTreeCigarId = null; dragTreeCigarCat = null;
    stageCigarChange(cid, String(targetCatId));
    return;
  }}

  // ── Unmatched → Category drop (quick-create) ───────────
  if (dragUnmatchedId !== null) {{
    const uid = dragUnmatchedId;
    dragUnmatchedId = null;
    const vitola     = (document.getElementById(`um-vt-${{uid}}`)?.value  || '').trim() || null;
    const length_mm  = parseFloat(document.getElementById(`um-len-${{uid}}`)?.value) || null;
    const ring_gauge = parseFloat(document.getElementById(`um-rg-${{uid}}`)?.value)  || null;
    const r = await fetch(`/admin-tools/catalog/api/unmatched/${{uid}}/quick-create`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{category_id: targetCatId, vitola, length_mm, ring_gauge}}),
    }});
    if (!r.ok) {{ showToast('创建失败', false); return; }}
    const row = document.getElementById(`um-${{uid}}`);
    if (row) row.remove();
    const idx = unmatched.findIndex(x => x.id === uid);
    if (idx !== -1) unmatched.splice(idx, 1);
    document.getElementById('tc-unmatched').textContent = unmatched.length;
    await loadCigars();
    showToast('✓ 已创建并分类');
    return;
  }}

  // ── Category → Category drop ───────────────────────────
  if (!dragCatId || dragCatId === targetCatId) return;

  const pos     = getDropPos(event, event.currentTarget);
  const dragged = categories.find(c => c.id === dragCatId);
  const target  = categories.find(c => c.id === targetCatId);
  if (!dragged || !target) return;

  let updates = [];

  if (pos === 'into') {{
    // Check not circular
    let p = target;
    while (p) {{
      if (p.id === dragCatId) {{ showToast('不能移入自身的子节点', false); return; }}
      p = categories.find(c => c.id === p.parent_id);
    }}
    const kids = categories.filter(c => c.parent_id === targetCatId && c.id !== dragCatId);
    updates = [{{ id: dragCatId, parent_id: targetCatId, sort_order: kids.length }}];
    collapsedCats.delete(targetCatId);  // expand target
  }} else {{
    const newParentId = target.parent_id ?? null;
    // Build new sibling order (excluding dragged, then insert at correct position)
    const siblings = categories
      .filter(c => (c.parent_id ?? null) === newParentId && c.id !== dragCatId)
      .sort((a, b) => a.sort_order - b.sort_order);
    const targetIdx = siblings.findIndex(c => c.id === targetCatId);
    const insertIdx = pos === 'before' ? targetIdx : targetIdx + 1;
    siblings.splice(insertIdx, 0, dragged);
    updates = siblings.map((c, i) => ({{
      id: c.id,
      parent_id: c.id === dragCatId ? newParentId : (c.parent_id ?? null),
      sort_order: i,
    }}));
  }}

  const results = await Promise.all(updates.map(u =>
    fetch(`/admin-tools/catalog/api/categories/${{u.id}}`, {{
      method: 'PATCH',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ parent_id: u.parent_id, sort_order: u.sort_order }}),
    }})
  ));

  dragCatId = null;
  if (results.some(r => !r.ok)) {{ showToast('移动失败', false); return; }}
  await loadCategories();
  filterCigars();
  showToast('✓ 已移动');
}}

function toggleCat(catId, event) {{
  event.stopPropagation();
  if (collapsedCats.has(catId)) collapsedCats.delete(catId);
  else collapsedCats.add(catId);
  renderTree();
  applyCigarVisibility();
}}

async function deleteCigar(cigarId, cigarName, event) {{
  event.stopPropagation();
  if (!confirm(`确认删除「${{cigarName}}」？将同时删除所有价格记录和别名，无法恢复。`)) return;
  const r = await fetch(`/admin-tools/catalog/api/cigars/${{cigarId}}`, {{ method: 'DELETE' }});
  if (!r.ok) {{ showToast('删除失败', false); return; }}
  showToast('已删除');
  await loadCigars();
}}

// ── Tree-cigar expand / detail panel ──────────────────────────────────────────
function toggleCigar(cigarId, event) {{
  event.stopPropagation();
  if (expandedCigars.has(cigarId)) expandedCigars.delete(cigarId);
  else expandedCigars.add(cigarId);
  renderTree();
}}

async function openDetail(cigarId, event) {{
  event.stopPropagation();
  const cigar = cigars.find(c => c.id === cigarId);
  if (!cigar) return;
  document.getElementById('pane-cigars').style.display    = 'none';
  document.getElementById('pane-unmatched').style.display = 'none';
  document.getElementById('pane-detail').classList.add('active');
  const r = await fetch(`/admin-tools/catalog/api/cigars/${{cigarId}}/aliases`);
  const aliases = r.ok ? await r.json() : [];
  renderDetailPanel(cigar, aliases);
}}

async function triggerScraper(slug, btn) {{
  btn.disabled = true;
  btn.textContent = '…';
  try {{
    const r = await fetch(`/scraper-admin/trigger/${{slug}}`, {{ method: 'POST' }});
    if (r.ok) {{
      btn.textContent = '✓';
      btn.style.color = '#16a34a';
    }} else {{
      btn.textContent = '✗';
      btn.style.color = '#dc2626';
      btn.disabled = false;
    }}
  }} catch (e) {{
    btn.textContent = '✗';
    btn.style.color = '#dc2626';
    btn.disabled = false;
  }}
}}

function closeDetail() {{
  document.getElementById('pane-detail').classList.remove('active');
  document.getElementById('pane-cigars').style.display    = activeTab === 'cigars'    ? '' : 'none';
  document.getElementById('pane-unmatched').style.display = activeTab === 'unmatched' ? '' : 'none';
}}

function renderDetailPanel(cigar, aliases) {{
  const srcRows = (cigar.sources || []).map(s => {{
    const dot = `<span class="in-stock-dot" style="background:${{s.in_stock ? '#22c55e' : '#d1d5db'}}"></span>`;
    const px  = s.price_single != null ? `${{s.currency}} ${{s.price_single.toFixed(2)}}` : '—';
    const bx  = s.price_box    != null
      ? `${{s.currency}} ${{s.price_box.toFixed(2)}}${{s.box_count ? '/'+s.box_count+'支' : ''}}`
      : '—';
    const link = s.url
      ? `<a href="${{s.url}}" target="_blank" style="color:#0071e3;text-decoration:none">↗</a>` : '';
    const triggerBtn = `<button
        onclick="triggerScraper('${{s.slug}}', this)"
        title="触发爬取 ${{s.slug}}"
        style="margin-left:4px;padding:1px 5px;font-size:10px;cursor:pointer;
               border:1px solid #d1d5db;border-radius:3px;background:#f9fafb;color:#374151;
               line-height:1.4;vertical-align:middle">▶</button>`;
    return `<tr>
      <td>${{dot}} ${{s.name}}${{triggerBtn}}</td>
      <td>${{px}}</td>
      <td>${{bx}}</td>
      <td style="color:#aaa;font-size:11px">${{s.scraped_at || ''}}</td>
      <td><span style="font-size:10px;color:#bbb">#${{s.price_id}}</span> ${{link}}</td>
    </tr>`;
  }}).join('');

  const aliasRows = aliases.length
    ? aliases.map(a => `<div class="detail-alias-row">
        <span class="detail-alias-src">${{a.source_slug}}</span>
        <span style="flex:1">${{a.raw_name}}</span>
        <span style="font-size:10px;color:#bbb">#${{a.id}}</span>
      </div>`).join('')
    : '<div class="detail-alias-row" style="color:#aaa">暂无别名</div>';

  const specParts = [];
  if (cigar.vitola)     specParts.push(cigar.vitola);
  if (cigar.length_mm)  specParts.push(cigar.length_mm + ' mm');
  if (cigar.ring_gauge) specParts.push('× ' + cigar.ring_gauge);

  document.getElementById('detail-content').innerHTML = `
    <div class="detail-title">${{cigar.name}}
      <span style="font-size:13px;font-weight:400;color:#aaa">#${{cigar.id}}</span>
    </div>
    <div class="detail-meta">${{specParts.join(' · ') || '暂无规格信息'}}</div>
    ${{cigar.sources && cigar.sources.length ? `
    <div class="detail-section">价格来源</div>
    <table class="detail-price-table">
      <thead><tr><th>站点</th><th>单支</th><th>整盒</th><th>抓取时间</th><th>ID/链接</th></tr></thead>
      <tbody>${{srcRows}}</tbody>
    </table>` : '<div style="color:#aaa;font-size:13px;padding:8px 0">暂无价格数据</div>'}}
    <div class="detail-section">爬虫别名</div>
    <div>${{aliasRows}}</div>
  `;
}}

function scrollToCigar(cigarId) {{
  // Switch to cigar tab if needed
  if (activeTab !== 'cigars') switchTab('cigars');
  const row = document.getElementById(`cr-${{cigarId}}`);
  if (!row) return;
  // Make sure it's visible (un-collapse parent if needed)
  row.style.display = '';
  row.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  row.classList.add('highlighted');
  setTimeout(() => row.classList.remove('highlighted'), 1500);
}}

function getHiddenCatIds() {{
  // A collapsed cat hides: itself (its direct cigars) + all descendants
  const hidden = new Set();
  function markDescendants(id) {{
    categories.filter(c => c.parent_id === id).forEach(c => {{
      hidden.add(c.id);
      markDescendants(c.id);
    }});
  }}
  collapsedCats.forEach(id => {{
    hidden.add(id);        // hide direct cigars of this cat
    markDescendants(id);   // hide all descendant cats' cigars
  }});
  return hidden;
}}

function applyCigarVisibility() {{
  const hidden = getHiddenCatIds();
  document.querySelectorAll('[id^="cr-"]').forEach(row => {{
    const cid   = parseInt(row.id.slice(3));
    const cigar = cigars.find(c => c.id === cid);
    if (!cigar) return;
    const effCat = effectiveCatId(cigar);
    row.style.display = (effCat && hidden.has(effCat)) ? 'none' : '';
  }});
}}

function renderTree() {{
  const el = document.getElementById('tree-container');
  el.innerHTML = categories.length ? buildTreeHtml(null, 1)
    : '<p class="empty">暂无分类，点击下方新建</p>';
}}

function renderParentSelect() {{
  const sel = document.getElementById('cat-parent');
  const val = sel.value;
  sel.innerHTML = '<option value="">（顶级）</option>';
  // flat list in tree order; exclude self and own descendants when editing
  function getDescendants(catId) {{
    const ids = new Set([catId]);
    categories.filter(c => c.parent_id === catId).forEach(c => {{
      getDescendants(c.id).forEach(id => ids.add(id));
    }});
    return ids;
  }}
  const excluded = editingCatId ? getDescendants(editingCatId) : new Set();
  function addOpts(parentId, depth) {{
    categories.filter(c => (c.parent_id ?? null) === parentId && !excluded.has(c.id))
              .sort((a, b) => a.sort_order - b.sort_order)
              .forEach(c => {{
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = '\u00a0'.repeat(depth * 3) + c.name;
      sel.appendChild(opt);
      addOpts(c.id, depth + 1);
    }});
  }}
  addOpts(null, 0);
  sel.value = val;
}}

function populateCategoryFilter() {{
  const sel = document.getElementById('cigar-filter-cat');
  sel.innerHTML = '<option value="">全部</option><option value="__uncat__">未分类</option>';
  function addOpts(parentId, depth) {{
    categories.filter(c => (c.parent_id ?? null) === parentId)
              .sort((a, b) => a.sort_order - b.sort_order)
              .forEach(c => {{
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = '\u00a0'.repeat(depth * 2) + c.name;
      sel.appendChild(opt);
      addOpts(c.id, depth + 1);
    }});
  }}
  addOpts(null, 0);
}}

// ── Category CRUD (immediate save) ────────────────────────────────────────────
function newCategory() {{
  editingCatId = null;
  document.getElementById('cat-form-title').textContent = '新建分类';
  document.getElementById('cat-name').value  = '';
  document.getElementById('cat-parent').value = '';
  document.getElementById('cat-order').value  = '0';
  document.getElementById('cat-delete-btn').style.display = 'none';
  document.getElementById('cat-form-card').style.display  = '';
}}

let editingCatId = null;
function editCategory(id) {{
  const cat = categories.find(c => c.id === id);
  if (!cat) return;
  editingCatId = id;
  document.getElementById('cat-form-title').textContent  = '编辑：' + cat.name;
  document.getElementById('cat-name').value   = cat.name;
  document.getElementById('cat-parent').value = cat.parent_id ?? '';
  document.getElementById('cat-order').value  = cat.sort_order;
  document.getElementById('cat-delete-btn').style.display = '';
  document.getElementById('cat-form-card').style.display  = '';
}}

function cancelCatForm() {{
  editingCatId = null;
  document.getElementById('cat-form-card').style.display = 'none';
}}

async function saveCategory() {{
  const name = document.getElementById('cat-name').value.trim();
  if (!name) {{ showToast('名称不能为空', false); return; }}
  const parent_id  = document.getElementById('cat-parent').value || null;
  const sort_order = parseInt(document.getElementById('cat-order').value) || 0;
  const body = {{ name, parent_id: parent_id ? parseInt(parent_id) : null, sort_order }};
  const url    = editingCatId
    ? `/admin-tools/catalog/api/categories/${{editingCatId}}`
    : `/admin-tools/catalog/api/brands/${{currentBrandId}}/categories`;
  const method = editingCatId ? 'PATCH' : 'POST';
  const r = await fetch(url, {{ method, headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(body) }});
  if (!r.ok) {{ showToast('保存失败: ' + (await r.text()), false); return; }}
  showToast('分类已保存');
  const wasNew = !editingCatId;
  const savedParentId = body.parent_id ?? null;
  cancelCatForm();
  if (wasNew && savedParentId !== null) collapsedCats.delete(savedParentId);  // expand parent so new child is visible
  await loadCategories();
  filterCigars();  // refresh dropdowns in cigar list
}}

async function deleteCategory() {{
  if (!editingCatId) return;
  if (!confirm('确认删除？其下雪茄将变为未分类，子分类提升到父级。')) return;
  const r = await fetch(`/admin-tools/catalog/api/categories/${{editingCatId}}`, {{ method: 'DELETE' }});
  if (!r.ok) {{ showToast('删除失败', false); return; }}
  showToast('已删除');
  cancelCatForm();
  await loadCategories();
  await loadCigars();
}}

// ── Inline rename（双击分类名） ─────────────────────────────────────────────────
function startInlineRename(id, event) {{
  event.stopPropagation();
  const span = event.currentTarget;
  const cat = categories.find(c => c.id === id);
  if (!cat) return;
  const input = document.createElement('input');
  input.className = 'cat-inline-input';
  input.value = cat.name;
  span.replaceWith(input);
  input.focus(); input.select();
  let done = false;
  const finish = async (save) => {{
    if (done) return; done = true;
    const newName = input.value.trim();
    if (save && newName && newName !== cat.name) {{
      const r = await fetch(`/admin-tools/catalog/api/categories/${{id}}`, {{
        method: 'PATCH',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{name: newName, parent_id: cat.parent_id, sort_order: cat.sort_order}}),
      }});
      if (!r.ok) {{ showToast('保存失败', false); done = false; renderTree(); return; }}
      await loadCategories(); filterCigars();
    }} else {{
      renderTree();
    }}
  }};
  input.addEventListener('keydown', e => {{
    if (e.key === 'Enter') {{ e.preventDefault(); finish(true); }}
    if (e.key === 'Escape') {{ finish(false); }}
  }});
  input.addEventListener('blur', () => finish(true));
}}

// ── Inline add child（点 ＋ 按钮） ─────────────────────────────────────────────
function catDepth(catId) {{
  let d = 0, cur = categories.find(c => c.id === catId);
  while (cur?.parent_id) {{ d++; cur = categories.find(c => c.id === cur.parent_id); }}
  return d;
}}

function startInlineAdd(parentId, event) {{
  event.stopPropagation();
  document.getElementById('inline-add-row')?.remove();
  const treeItem = event.currentTarget.closest('.tree-item');
  if (!treeItem) return;
  const indent = (catDepth(parentId) + 1) * 20 + 22;
  const row = document.createElement('div');
  row.id = 'inline-add-row';
  row.className = 'inline-add-row';
  row.style.paddingLeft = indent + 'px';
  row.innerHTML = `<span style="color:#22c55e;font-size:13px;font-weight:700">＋</span>
    <input id="inline-add-input" class="cat-inline-input" placeholder="新子分类名…" style="width:150px">
    <span class="inline-add-hint">Enter 确认 · Esc 取消</span>`;
  treeItem.insertAdjacentElement('afterend', row);
  const input = document.getElementById('inline-add-input');
  input.focus();
  let done = false;
  input.addEventListener('keydown', async e => {{
    if (e.key === 'Enter') {{
      e.preventDefault();
      if (done) return; done = true;
      const name = input.value.trim();
      if (!name) {{ row.remove(); return; }}
      const sortOrder = categories.filter(c => c.parent_id === parentId).length;
      const r = await fetch(`/admin-tools/catalog/api/brands/${{currentBrandId}}/categories`, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{name, parent_id: parentId, sort_order: sortOrder}}),
      }});
      row.remove();
      if (!r.ok) {{ showToast('创建失败', false); return; }}
      collapsedCats.delete(parentId);
      await loadCategories(); filterCigars();
    }}
    if (e.key === 'Escape') {{ row.remove(); }}
  }});
  input.addEventListener('blur', () => {{ if (!done) setTimeout(() => row.remove(), 120); }});
}}

// ── Cigars ────────────────────────────────────────────────────────────────────
async function loadCigars() {{
  const r = await fetch(`/admin-tools/catalog/api/brands/${{currentBrandId}}/cigars`);
  cigars = await r.json();
  document.getElementById('tc-cigars').textContent = cigars.length;
  filterCigars();
  renderTree();
}}

function getCatMap() {{
  const m = {{}};
  categories.forEach(c => m[c.id] = c);
  return m;
}}

function effectiveCatId(cigar) {{
  // return pending value if exists, else original
  return pendingChanges.has(cigar.id) ? pendingChanges.get(cigar.id).newCatId : cigar.category_id;
}}

function filterCigars() {{
  const q          = document.getElementById('cigar-search').value.toLowerCase();
  const catFilter  = document.getElementById('cigar-filter-cat').value;
  const catMap     = getCatMap();
  const filtered   = cigars.filter(c => {{
    const nameMatch  = !q || c.name.toLowerCase().includes(q);
    const effCat     = effectiveCatId(c);
    let   catMatch   = true;
    if (catFilter === '__uncat__') catMatch = !effCat;
    else if (catFilter)            catMatch = String(effCat) === String(catFilter);
    return nameMatch && catMatch;
  }});
  renderCigars(filtered, catMap);
}}

function renderCigars(list, catMap) {{
  const el = document.getElementById('cigar-list');
  if (!list.length) {{ el.innerHTML = '<p class="empty">暂无结果</p>'; return; }}
  el.innerHTML = list.map(c => {{
    const effCat   = effectiveCatId(c);
    const cat      = effCat ? catMap[effCat] : null;
    const isPending = pendingChanges.has(c.id);
    const tagCls   = cat ? 'ctag has' : 'ctag none';
    const tagText  = cat ? cat.name : '未分类';

    // category select options
    const selOpts  = buildCatSelectOpts(effCat);

    // source icon links
    const srcHtml  = (c.sources || []).map(s =>
      s.url ? `<a class="src-icon" href="${{s.url}}" target="_blank" title="${{s.name}}">` +
              s.abbr + `</a>` : ''
    ).filter(Boolean).join('');

    // specs line: vitola + length + ring_gauge (click to edit)
    const specParts = [];
    if (c.vitola)     specParts.push(c.vitola);
    if (c.length_mm)  specParts.push(c.length_mm + ' mm');
    if (c.ring_gauge) specParts.push('× ' + c.ring_gauge);
    const specText = specParts.join(' · ') || '—';
    const specsLine = `<div class="cv" id="specs-${{c.id}}" onclick="editSpecs(${{c.id}})"
        title="点击编辑长度/环径">${{specText}} <span class="edit-hint">✎</span></div>`;

    return `<div class="cigar-row${{isPending ? ' pending' : ''}}" id="cr-${{c.id}}"
      draggable="false"
      ondragstart="cigarDragStart(${{c.id}},event)"
      ondragend="cigarDragEnd(event);this.draggable=false">
      <span class="drag-handle" title="拖至左侧分类" onmousedown="this.parentElement.draggable=true">⠿</span>
      <div class="cigar-name">
        <div class="cn">${{c.name}} <span style="font-size:11px;color:#aaa;font-weight:400">#${{c.id}}</span></div>
        ${{specsLine}}
      </div>
      <div class="source-links">${{srcHtml}}</div>
      <span class="${{tagCls}}" id="ct-${{c.id}}">${{tagText}}</span>
      <select class="cat-select" id="sel-${{c.id}}" onchange="stageCigarChange(${{c.id}}, this.value)">
        ${{selOpts}}
      </select>
      <span class="cigar-del-btn" onclick="deleteCigar(${{c.id}}, '${{c.name.replace(/'/g,"\\'")}}', event)" title="删除雪茄">🗑</span>
    </div>`;
  }}).join('');
  applyCigarVisibility();
}}

function buildCatSelectOpts(selectedCatId) {{
  let html = `<option value="">— 未分类 —</option>`;
  function addOpts(parentId, depth) {{
    categories.filter(c => (c.parent_id ?? null) === parentId)
              .sort((a, b) => a.sort_order - b.sort_order)
              .forEach(c => {{
      const sel = String(selectedCatId) === String(c.id) ? 'selected' : '';
      html += `<option value="${{c.id}}" ${{sel}}>${{'\u00a0'.repeat(depth*2)}}${{c.name}}</option>`;
      addOpts(c.id, depth + 1);
    }});
  }}
  addOpts(null, 0);
  return html;
}}

// ── Staging ───────────────────────────────────────────────────────────────────
function stageCigarChange(cigarId, newCatIdStr) {{
  const newCatId  = newCatIdStr ? parseInt(newCatIdStr) : null;
  const cigar     = cigars.find(c => c.id === cigarId);
  if (!cigar) return;
  const original  = cigar.category_id;

  if (pendingChanges.has(cigarId)) {{
    const existing = pendingChanges.get(cigarId);
    if (newCatId === existing.oldCatId) {{
      pendingChanges.delete(cigarId);  // reverted to original
    }} else {{
      existing.newCatId = newCatId;
    }}
  }} else {{
    if (newCatId !== original) {{
      pendingChanges.set(cigarId, {{ oldCatId: original, newCatId }});
    }}
  }}

  // Update row visuals
  const row = document.getElementById(`cr-${{cigarId}}`);
  if (row) row.className = 'cigar-row' + (pendingChanges.has(cigarId) ? ' pending' : '');

  // Update tag
  const catMap = getCatMap();
  const tag = document.getElementById(`ct-${{cigarId}}`);
  if (tag) {{
    const cat = newCatId ? catMap[newCatId] : null;
    tag.textContent = cat ? cat.name : '未分类';
    tag.className = cat ? 'ctag has' : 'ctag none';
  }}

  updateSaveBar();
  renderTree();
}}

function updateSaveBar() {{
  const bar  = document.getElementById('save-bar');
  const info = document.getElementById('save-info');
  const n    = pendingChanges.size;
  info.textContent = `有 ${{n}} 项雪茄分配未保存`;
  bar.className = 'save-bar' + (n > 0 ? ' visible' : '');
}}

async function saveAllChanges() {{
  if (!pendingChanges.size) return;
  const payload = [];
  pendingChanges.forEach((v, cigarId) => {{
    payload.push({{ cigar_id: cigarId, category_id: v.newCatId }});
  }});
  const r = await fetch(`/admin-tools/catalog/api/brands/${{currentBrandId}}/cigar-assignments`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(payload),
  }});
  if (!r.ok) {{ showToast('保存失败', false); return; }}
  // Commit pending to cigar local data
  pendingChanges.forEach((v, cigarId) => {{
    const c = cigars.find(x => x.id === cigarId);
    if (c) c.category_id = v.newCatId;
  }});
  pendingChanges.clear();
  updateSaveBar();
  filterCigars();
  renderTree();
  showToast(`✓ 已保存 ${{payload.length}} 项`);
}}

function discardChanges() {{
  // Restore select elements and tags to original values
  pendingChanges.forEach((v, cigarId) => {{
    const sel = document.getElementById(`sel-${{cigarId}}`);
    if (sel) sel.value = v.oldCatId ?? '';
    const tag = document.getElementById(`ct-${{cigarId}}`);
    const catMap = getCatMap();
    if (tag) {{
      const cat = v.oldCatId ? catMap[v.oldCatId] : null;
      tag.textContent = cat ? cat.name : '未分类';
      tag.className = cat ? 'ctag has' : 'ctag none';
    }}
    const row = document.getElementById(`cr-${{cigarId}}`);
    if (row) row.className = 'cigar-row';
  }});
  pendingChanges.clear();
  updateSaveBar();
  renderTree();
  showToast('已放弃更改');
}}

// ── Cigar specs inline edit ───────────────────────────────────────────────────
function editSpecs(cigarId) {{
  const cigar = cigars.find(c => c.id === cigarId);
  if (!cigar) return;
  const el = document.getElementById(`specs-${{cigarId}}`);
  if (!el || el.querySelector('input')) return;  // already editing
  el.innerHTML = `<span class="specs-inputs">
    <input id="sp-vt-${{cigarId}}" type="text"
           value="${{cigar.vitola ?? ''}}" placeholder="规格名" style="width:110px">
    <input id="sp-len-${{cigarId}}" type="number" step="0.1" min="0"
           value="${{cigar.length_mm ?? ''}}" placeholder="长度 mm">
    <input id="sp-rg-${{cigarId}}" type="number" step="0.5" min="0"
           value="${{cigar.ring_gauge ?? ''}}" placeholder="环径">
    <button onclick="saveSpecs(${{cigarId}})">✓</button>
    <button onclick="cancelSpecs(${{cigarId}})">✕</button>
  </span>`;
  const inp = document.getElementById(`sp-vt-${{cigarId}}`);
  if (inp) inp.focus();
  el.querySelectorAll('input').forEach(i => {{
    i.addEventListener('keydown', e => {{
      if (e.key === 'Enter') saveSpecs(cigarId);
      if (e.key === 'Escape') cancelSpecs(cigarId);
    }});
  }});
}}

async function saveSpecs(cigarId) {{
  const vtEl  = document.getElementById(`sp-vt-${{cigarId}}`);
  const lenEl = document.getElementById(`sp-len-${{cigarId}}`);
  const rgEl  = document.getElementById(`sp-rg-${{cigarId}}`);
  if (!lenEl) return;
  const vitola     = vtEl.value.trim() || null;
  const length_mm  = lenEl.value !== '' ? parseFloat(lenEl.value) : null;
  const ring_gauge = rgEl.value  !== '' ? parseFloat(rgEl.value)  : null;
  const r = await fetch(`/admin-tools/catalog/api/cigars/${{cigarId}}/specs`, {{
    method: 'PATCH',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{vitola, length_mm, ring_gauge}}),
  }});
  if (!r.ok) {{ showToast('保存失败', false); return; }}
  const cigar = cigars.find(c => c.id === cigarId);
  if (cigar) {{ cigar.vitola = vitola; cigar.length_mm = length_mm; cigar.ring_gauge = ring_gauge; }}
  renderSpecsDisplay(cigarId);
  showToast('✓ 已保存');
}}

function cancelSpecs(cigarId) {{ renderSpecsDisplay(cigarId); }}

function renderSpecsDisplay(cigarId) {{
  const cigar = cigars.find(c => c.id === cigarId);
  const el = document.getElementById(`specs-${{cigarId}}`);
  if (!cigar || !el) return;
  const parts = [];
  if (cigar.vitola)     parts.push(cigar.vitola);
  if (cigar.length_mm)  parts.push(cigar.length_mm + ' mm');
  if (cigar.ring_gauge) parts.push('× ' + cigar.ring_gauge);
  el.innerHTML = (parts.join(' · ') || '—') + ' <span class="edit-hint">✎</span>';
}}

// ── Unmatched ─────────────────────────────────────────────────────────────────
async function loadUnmatched(brandName) {{
  const url = brandName
    ? `/admin-tools/catalog/api/unmatched?brand=${{encodeURIComponent(brandName)}}`
    : `/admin-tools/catalog/api/unmatched`;
  const r   = await fetch(url);
  unmatched = await r.json();
  document.getElementById('tc-unmatched').textContent = unmatched.length;
  populateSourceFilter();
  filterUnmatched();
  loadIgnored();
}}

function populateSourceFilter() {{
  const sources = [...new Set(unmatched.map(u => u.source_slug))].sort();
  const sel = document.getElementById('um-filter-source');
  sel.innerHTML = '<option value="">全部来源</option>' +
    sources.map(s => `<option value="${{s}}">${{s}}</option>`).join('');
}}

function filterUnmatched() {{
  const q   = document.getElementById('um-search').value.toLowerCase();
  const src = document.getElementById('um-filter-source').value;
  const filtered = unmatched.filter(u => {{
    const nameMatch = !q   || u.raw_name.toLowerCase().includes(q);
    const srcMatch  = !src || u.source_slug === src;
    return nameMatch && srcMatch;
  }});
  renderUnmatched(filtered);
}}

function renderUnmatched(list) {{
  const el = document.getElementById('unmatched-list');
  if (!list.length) {{ el.innerHTML = '<p class="empty">暂无未匹配条目</p>'; return; }}
  el.innerHTML = list.slice(0, 200).map(u => {{
    const price = u.price_single
      ? `${{u.currency}} ${{u.price_single.toFixed(2)}}/支` : '';
    const bestCand = u.best_candidate
      ? `≈ ${{u.best_candidate}}` : '';
    const linkIcon = u.product_url
      ? `<a href="${{u.product_url}}" target="_blank" class="src-icon" title="${{u.source_slug}}"
           style="margin-right:4px">${{u.source_slug.slice(0,4).toUpperCase()}}</a>`
      : `<span class="src-icon" style="opacity:.45;margin-right:4px">${{u.source_slug.slice(0,4).toUpperCase()}}</span>`;
    // 从页面品牌选择器读取所有品牌选项
    const brandOptEls = Array.from(document.querySelectorAll('#brand-select option'))
      .filter(o => o.value && o.value !== '__unmatched__');
    const brandOpts = brandOptEls.map(o =>
      `<option value="${{o.value}}">${{o.textContent.trim()}}</option>`
    ).join('');

    return `<div class="cigar-row" id="um-${{u.id}}" style="align-items:flex-start;flex-wrap:wrap;gap:6px"
      draggable="false"
      ondragstart="unmatchedDragStart(${{u.id}},event)"
      ondragend="unmatchedDragEnd(event);this.draggable=false">
      <span class="drag-handle" title="拖至左侧分类" onmousedown="this.parentElement.draggable=true">⠿</span>
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;gap:6px">
          ${{linkIcon}}
          <span style="font-weight:600;font-size:15px">${{u.raw_name}}</span>
          <span style="font-size:11px;color:#aaa">#${{u.id}}</span>
          <span class="um-ignore-btn" title="移入垃圾箱" onclick="ignoreUnmatched(${{u.id}})">🗑</span>
        </div>
        <div class="um-meta" style="margin-top:3px">
          ${{price ? price + ' &nbsp;·&nbsp; ' : ''}}${{bestCand || '暂无候选'}}
        </div>
        <div class="specs-inputs" style="margin-top:6px">
          <input id="um-vt-${{u.id}}"  type="text"   placeholder="规格名" style="width:100px">
          <input id="um-len-${{u.id}}" type="number" step="0.1" min="0" placeholder="长度 mm" style="width:72px">
          <input id="um-rg-${{u.id}}"  type="number" step="0.5" min="0" placeholder="环径"   style="width:56px">
        </div>
        <div class="um-link-row">
          <input id="um-link-${{u.id}}" type="text" placeholder="关联已有雪茄…"
                 autocomplete="off"
                 oninput="umLinkSearch(${{u.id}}, this.value)"
                 list="um-dl-${{u.id}}">
          <datalist id="um-dl-${{u.id}}"></datalist>
          <button class="um-link-btn" onclick="doLinkUnmatched(${{u.id}})">关联</button>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;margin-top:4px;min-width:160px">
        <select class="cat-select" style="width:100%"
          onchange="umBrandChange(${{u.id}}, this.value)">
          <option value="">— 选品牌 —</option>
          ${{brandOpts}}
        </select>
        <select id="um-cat-${{u.id}}" class="cat-select" style="width:100%"
          onchange="quickCreateFromUnmatched(${{u.id}}, this.value, this)" disabled>
          <option value="">— 再选分类 —</option>
        </select>
      </div>
    </div>`;
  }}).join('');
  if (list.length > 200) {{
    el.innerHTML += `<p class="empty">仅显示前 200 条，请使用搜索缩小范围</p>`;
  }}
}}

const _umCreating = new Set();  // 防止同一条目并发提交

async function quickCreateFromUnmatched(unmatchedId, catId, selectEl) {{
  if (!catId) return;
  if (_umCreating.has(unmatchedId)) return;  // 已在处理中，忽略

  _umCreating.add(unmatchedId);
  selectEl.disabled = true;

  const vitola     = (document.getElementById(`um-vt-${{unmatchedId}}`)?.value  || '').trim() || null;
  const length_mm  = parseFloat(document.getElementById(`um-len-${{unmatchedId}}`)?.value) || null;
  const ring_gauge = parseFloat(document.getElementById(`um-rg-${{unmatchedId}}`)?.value)  || null;

  function _removeRow() {{
    const row = document.getElementById(`um-${{unmatchedId}}`);
    if (row) row.remove();
    const idx = unmatched.findIndex(x => x.id === unmatchedId);
    if (idx !== -1) unmatched.splice(idx, 1);
    document.getElementById('tc-unmatched').textContent = unmatched.length;
  }}

  try {{
    const r = await fetch(`/admin-tools/catalog/api/unmatched/${{unmatchedId}}/quick-create`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{category_id: parseInt(catId), vitola, length_mm, ring_gauge}}),
    }});
    const data = await r.json();

    if (r.status === 404) {{
      // 已被 batch-match 自动处理，静默移除
      _removeRow();
      _umCreating.delete(unmatchedId);
      return;
    }}
    if (!r.ok) {{
      showToast('创建失败：' + (data.error || r.status), false);
      selectEl.disabled = false;
      selectEl.value = '';
      _umCreating.delete(unmatchedId);
      return;
    }}
    _removeRow();
    _umCreating.delete(unmatchedId);
    await loadCigars();
    const msg = data.auto_matched > 0
      ? `✓ 已创建（自动匹配 ${{data.auto_matched}} 条）`
      : '✓ 已创建';
    showToast(msg);
  }} catch(e) {{
    showToast('网络错误：' + e.message, false);
    selectEl.disabled = false;
    selectEl.value = '';
    _umCreating.delete(unmatchedId);
  }}
}}
// ── 未匹配行：品牌切换 → 加载该品牌分类 ─────────────────────────────────────
async function umBrandChange(uid, brandId) {{
  const catSel = document.getElementById(`um-cat-${{uid}}`);
  if (!catSel) return;
  catSel.innerHTML = '<option value="">加载中…</option>';
  catSel.disabled = true;
  if (!brandId) {{
    catSel.innerHTML = '<option value="">— 再选分类 —</option>';
    return;
  }}
  try {{
    const r = await fetch(`/admin-tools/catalog/api/brands/${{brandId}}/categories`);
    const cats = await r.json();
    // Build nested options
    function buildOpts(parentId, depth) {{
      let html = '';
      cats.filter(c => (c.parent_id ?? null) === parentId)
          .sort((a, b) => (a.sort_order||0) - (b.sort_order||0))
          .forEach(c => {{
            html += `<option value="${{c.id}}">${{'\u00a0'.repeat(depth*2)}}${{c.name}}</option>`;
            html += buildOpts(c.id, depth + 1);
          }});
      return html;
    }}
    catSel.innerHTML = '<option value="">— 选择分类 —</option>' + buildOpts(null, 0);
    catSel.disabled = false;
  }} catch(e) {{
    catSel.innerHTML = '<option value="">加载失败</option>';
  }}
}}

// ── 关联已有雪茄 ──────────────────────────────────────────────────────────────
let _umLinkTimer = null;
let _umLinkCache = {{}};  // query → [{{id, name}}]

async function umLinkSearch(uid, query) {{
  const q = query.trim();
  const dl = document.getElementById(`um-dl-${{uid}}`);
  if (!dl) return;
  if (!q) {{ dl.innerHTML = ''; return; }}

  // Use cache if available
  if (_umLinkCache[q]) {{
    dl.innerHTML = _umLinkCache[q].map(c => `<option value="${{c.name}}" data-id="${{c.id}}">`).join('');
    return;
  }}

  clearTimeout(_umLinkTimer);
  _umLinkTimer = setTimeout(async () => {{
    try {{
      const r = await fetch(`/admin-tools/catalog/api/cigars/search?q=${{encodeURIComponent(q)}}`);
      if (!r.ok) return;
      const results = await r.json();
      _umLinkCache[q] = results;
      dl.innerHTML = results.map(c => `<option value="${{c.name}}" data-id="${{c.id}}">`).join('');
    }} catch(e) {{}}
  }}, 250);
}}

async function doLinkUnmatched(uid) {{
  const input = document.getElementById(`um-link-${{uid}}`);
  if (!input) return;
  const val = input.value.trim();
  if (!val) {{ showToast('请输入雪茄名称', false); return; }}

  // Find cigar id from cache
  let cigarId = null;
  for (const results of Object.values(_umLinkCache)) {{
    const match = results.find(c => c.name.toLowerCase() === val.toLowerCase());
    if (match) {{ cigarId = match.id; break; }}
  }}

  if (!cigarId) {{
    // Try a direct search
    try {{
      const r = await fetch(`/admin-tools/catalog/api/cigars/search?q=${{encodeURIComponent(val)}}`);
      const results = await r.json();
      const exact = results.find(c => c.name.toLowerCase() === val.toLowerCase());
      if (exact) cigarId = exact.id;
    }} catch(e) {{}}
  }}

  if (!cigarId) {{ showToast('未找到匹配雪茄，请确认名称', false); return; }}

  const btn = input.nextElementSibling?.nextElementSibling || input.parentElement.querySelector('.um-link-btn');
  if (btn) btn.disabled = true;
  try {{
    const r = await fetch(`/admin-tools/catalog/api/unmatched/${{uid}}/link-alias`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{cigar_id: cigarId}}),
    }});
    const data = await r.json();
    if (r.status === 404) {{
      // 爬虫重跑后旧 id 已失效，静默移除
      const row = document.getElementById(`um-${{uid}}`);
      if (row) row.remove();
      const idx = unmatched.findIndex(x => x.id === uid);
      if (idx !== -1) unmatched.splice(idx, 1);
      document.getElementById('tc-unmatched').textContent = unmatched.length;
      showToast('条目已过期，请刷新页面获取最新列表', false);
      return;
    }}
    if (!r.ok) {{
      showToast('关联失败：' + (data.error || r.status), false);
      if (btn) btn.disabled = false;
      return;
    }}
    const row = document.getElementById(`um-${{uid}}`);
    if (row) row.remove();
    const idx = unmatched.findIndex(x => x.id === uid);
    if (idx !== -1) unmatched.splice(idx, 1);
    document.getElementById('tc-unmatched').textContent = unmatched.length;
    showToast(`✓ 已关联到 ${{data.cigar_name}}`);
  }} catch(e) {{
    showToast('网络错误：' + e.message, false);
    if (btn) btn.disabled = false;
  }}
}}

// ── Panel resizer ─────────────────────────────────────────────────────────────
(function() {{
  let dragging = false, startX = 0, startW = 0;
  window.resizerMouseDown = function(e) {{
    dragging = true;
    startX   = e.clientX;
    startW   = document.getElementById('left-panel').offsetWidth;
    document.getElementById('resizer').classList.add('is-dragging');
    document.body.style.cursor     = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }};
  document.addEventListener('mousemove', e => {{
    if (!dragging) return;
    const w = Math.max(160, Math.min(640, startW + e.clientX - startX));
    document.getElementById('left-panel').style.width = w + 'px';
  }});
  document.addEventListener('mouseup', () => {{
    if (!dragging) return;
    dragging = false;
    document.getElementById('resizer').classList.remove('is-dragging');
    document.body.style.cursor     = '';
    document.body.style.userSelect = '';
  }});
}})();

// ── 垃圾箱 ────────────────────────────────────────────────────────────────────
let ignoredItems = [];

async function ignoreUnmatched(uid) {{
  const row = document.getElementById(`um-${{uid}}`);
  const r = await fetch(`/admin-tools/catalog/api/unmatched/${{uid}}/ignore`, {{method: 'POST'}});
  if (!r.ok) {{ showToast('操作失败', false); return; }}
  if (row) row.remove();
  const idx = unmatched.findIndex(x => x.id === uid);
  if (idx !== -1) unmatched.splice(idx, 1);
  document.getElementById('tc-unmatched').textContent = unmatched.length;
  showToast('已移入垃圾箱');
  await loadIgnored();
}}

async function loadIgnored() {{
  const r = await fetch('/admin-tools/catalog/api/ignored');
  ignoredItems = await r.json();
  const badge = document.getElementById('tc-ignored');
  if (ignoredItems.length > 0) {{
    badge.textContent = ignoredItems.length;
    badge.style.display = '';
  }} else {{
    badge.style.display = 'none';
  }}
  const listEl = document.getElementById('trash-list');
  if (listEl.classList.contains('open')) renderIgnored();
}}

function renderIgnored() {{
  const listEl = document.getElementById('trash-list');
  if (!ignoredItems.length) {{
    listEl.innerHTML = '<p class="empty" style="font-size:12px;padding:4px 0">垃圾箱为空</p>';
    return;
  }}
  listEl.innerHTML = ignoredItems.map(i => `
    <div class="trash-row" id="ig-${{i.id}}">
      <span class="trash-src">${{i.source_slug}}</span>
      <span class="trash-name">${{i.raw_name}}</span>
      <button class="trash-restore-btn" onclick="restoreIgnored(${{i.id}})">↩ 恢复</button>
    </div>`).join('');
}}

function toggleTrashBin() {{
  const listEl   = document.getElementById('trash-list');
  const toggleEl = document.getElementById('trash-toggle');
  const open = listEl.classList.toggle('open');
  toggleEl.classList.toggle('open', open);
  if (open) renderIgnored();
}}

async function restoreIgnored(ignoredId) {{
  const r = await fetch(`/admin-tools/catalog/api/ignored/${{ignoredId}}`, {{method: 'DELETE'}});
  if (!r.ok) {{ showToast('恢复失败', false); return; }}
  const row = document.getElementById(`ig-${{ignoredId}}`);
  if (row) row.remove();
  ignoredItems = ignoredItems.filter(x => x.id !== ignoredId);
  const badge = document.getElementById('tc-ignored');
  if (ignoredItems.length > 0) {{
    badge.textContent = ignoredItems.length;
  }} else {{
    badge.style.display = 'none';
  }}
  showToast('已恢复，下次加载未匹配列表时将重新出现');
}}
</script>
</body>
</html>"""
    return HTMLResponse(html)


# ── JSON API ───────────────────────────────────────────────────────────────────

@router.get("/api/brands/{brand_id}/categories")
async def get_categories(brand_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Category)
            .where(Category.brand_id == brand_id)
            .order_by(Category.sort_order, Category.id)
        )
        cats = result.scalars().all()
    return [
        {"id": c.id, "brand_id": c.brand_id, "parent_id": c.parent_id,
         "name": c.name, "slug": c.slug, "sort_order": c.sort_order}
        for c in cats
    ]


@router.get("/api/brands/{brand_id}/cigars")
async def get_cigars(brand_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        # Load cigars with series
        cigars_r = await db.execute(
            select(Cigar, Series)
            .join(Series, Cigar.series_id == Series.id)
            .where(Series.brand_id == brand_id)
            .order_by(Cigar.sort_order, Cigar.name)
        )
        rows = cigars_r.all()

        if not rows:
            return []

        cigar_ids = [c.id for c, _ in rows]

        # Load prices + sources for these cigars
        prices_r = await db.execute(
            select(Price, Source)
            .join(Source, Price.source_id == Source.id)
            .where(Price.cigar_id.in_(cigar_ids))
            .where(Price.product_url.isnot(None))
        )
        price_rows = prices_r.all()

    # Group sources by cigar_id
    cigar_sources: dict[int, list[dict]] = {}
    for price, source in price_rows:
        if price.cigar_id not in cigar_sources:
            cigar_sources[price.cigar_id] = []
        # Abbreviate source name: take first letter of each Chinese word segment or first 3 chars of slug
        abbr = source.slug[:4].upper()
        cigar_sources[price.cigar_id].append({
            "slug":         source.slug,
            "name":         source.name,
            "abbr":         abbr,
            "url":          price.product_url,
            "price_id":     price.id,
            "price_single": price.price_single,
            "price_box":    price.price_box,
            "box_count":    price.box_count,
            "currency":     price.currency,
            "in_stock":     price.in_stock,
            "scraped_at":   price.scraped_at.strftime("%Y-%m-%d %H:%M") if price.scraped_at else None,
        })

    return [
        {
            "id":          c.id,
            "name":        c.name,
            "slug":        c.slug,
            "vitola":      c.vitola,
            "length_mm":   c.length_mm,
            "ring_gauge":  c.ring_gauge,
            "category_id": c.category_id,
            "sort_order":  c.sort_order,
            "sources":     cigar_sources.get(c.id, []),
        }
        for c, _ in rows
    ]


@router.get("/api/cigars/{cigar_id}/aliases")
async def get_cigar_aliases(cigar_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        r = await db.execute(
            select(ScraperNameAlias).where(ScraperNameAlias.cigar_id == cigar_id)
        )
        aliases = r.scalars().all()
    return [{"id": a.id, "source_slug": a.source_slug, "raw_name": a.raw_name} for a in aliases]


@router.get("/api/unmatched")
async def get_unmatched(request: Request, brand: str = ""):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        # 获取全局忽略列表 key set
        ignored_r = await db.execute(select(IgnoredRawName))
        ignored_keys = {(r.source_slug, r.raw_name) for r in ignored_r.scalars().all()}

        q = select(UnmatchedItem).order_by(UnmatchedItem.id.desc())
        if brand:
            q = q.where(UnmatchedItem.raw_name.ilike(f"%{brand}%"))
        result = await db.execute(q.limit(2000))
        items = result.scalars().all()
    return [
        {
            "id":            u.id,
            "raw_name":      u.raw_name,
            "source_slug":   u.source_slug,
            "price_single":  u.price_single,
            "price_box":     u.price_box,
            "currency":      u.currency,
            "product_url":   u.product_url,
            "match_score":   u.match_score,
            "best_candidate": u.best_candidate,
        }
        for u in items
        if (u.source_slug, u.raw_name) not in ignored_keys
    ]


@router.post("/api/unmatched/{item_id}/ignore")
async def ignore_unmatched(item_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(UnmatchedItem).where(UnmatchedItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            return JSONResponse({"error": "not found"}, status_code=404)
        # 幂等：已存在则跳过
        exists_r = await db.execute(
            select(IgnoredRawName).where(
                IgnoredRawName.source_slug == item.source_slug,
                IgnoredRawName.raw_name    == item.raw_name,
            )
        )
        if not exists_r.scalar_one_or_none():
            db.add(IgnoredRawName(source_slug=item.source_slug, raw_name=item.raw_name))
            await db.commit()
    return {"ok": True}


@router.get("/api/ignored")
async def get_ignored(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(IgnoredRawName).order_by(IgnoredRawName.ignored_at.desc()))
        items = r.scalars().all()
    return [
        {
            "id":          i.id,
            "source_slug": i.source_slug,
            "raw_name":    i.raw_name,
            "ignored_at":  i.ignored_at.isoformat(),
        }
        for i in items
    ]


@router.delete("/api/ignored/{ignored_id}")
async def restore_ignored(ignored_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(IgnoredRawName).where(IgnoredRawName.id == ignored_id))
        item = r.scalar_one_or_none()
        if not item:
            return JSONResponse({"error": "not found"}, status_code=404)
        await db.delete(item)
        await db.commit()
    return {"ok": True}


@router.post("/api/brands/{brand_id}/cigar-assignments")
async def batch_save_assignments(brand_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()  # [{cigar_id, category_id}]
    async with AsyncSessionLocal() as db:
        for item in data:
            r = await db.execute(select(Cigar).where(Cigar.id == item["cigar_id"]))
            cigar = r.scalar_one_or_none()
            if cigar:
                cigar.category_id = item.get("category_id")
        await db.commit()
    return {"ok": True, "saved": len(data)}


@router.post("/api/brands/{brand_id}/categories")
async def create_category(brand_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    parent_id  = data.get("parent_id")
    sort_order = int(data.get("sort_order") or 0)
    async with AsyncSessionLocal() as db:
        slug = await _unique_cat_slug(db, _slugify(name))
        cat  = Category(brand_id=brand_id, parent_id=parent_id,
                        name=name, slug=slug, sort_order=sort_order)
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
    return {"id": cat.id, "slug": cat.slug}


@router.patch("/api/categories/{cat_id}")
async def update_category(cat_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    async with AsyncSessionLocal() as db:
        r   = await db.execute(select(Category).where(Category.id == cat_id))
        cat = r.scalar_one_or_none()
        if not cat:
            return JSONResponse({"error": "not found"}, status_code=404)
        if "name" in data and data["name"]:
            cat.name = data["name"].strip()
        if "parent_id" in data:
            cat.parent_id = data["parent_id"]
        if "sort_order" in data:
            cat.sort_order = int(data["sort_order"])
        await db.commit()
    return {"ok": True}


@router.delete("/api/categories/{cat_id}")
async def delete_category(cat_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        r   = await db.execute(select(Category).where(Category.id == cat_id))
        cat = r.scalar_one_or_none()
        if cat:
            # Clear cigar assignments for this category
            cigars_r = await db.execute(select(Cigar).where(Cigar.category_id == cat_id))
            for c in cigars_r.scalars().all():
                c.category_id = None
            # Promote children to parent
            children_r = await db.execute(select(Category).where(Category.parent_id == cat_id))
            for child in children_r.scalars().all():
                child.parent_id = cat.parent_id
            await db.delete(cat)
        await db.commit()
    return {"ok": True}


@router.patch("/api/cigars/{cigar_id}/specs")
async def update_cigar_specs(cigar_id: int, request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Cigar).where(Cigar.id == cigar_id))
        cigar = r.scalar_one_or_none()
        if not cigar:
            return JSONResponse({"error": "not found"}, status_code=404)
        if "vitola" in data:
            cigar.vitola = data["vitola"] or None
        if "length_mm" in data:
            cigar.length_mm = float(data["length_mm"]) if data["length_mm"] is not None else None
        if "ring_gauge" in data:
            cigar.ring_gauge = float(data["ring_gauge"]) if data["ring_gauge"] is not None else None
        await db.commit()
    return {"ok": True}


@router.delete("/api/cigars/{cigar_id}")
async def delete_cigar(cigar_id: int, request: Request):
    """删除雪茄及其所有价格记录和别名（仅管理员）"""
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Cigar).where(Cigar.id == cigar_id))
        cigar = r.scalar_one_or_none()
        if not cigar:
            return JSONResponse({"error": "not found"}, status_code=404)
        # Delete associated prices, price history, aliases
        await db.execute(_sql("DELETE FROM prices WHERE cigar_id = :cid"), {"cid": cigar_id})
        await db.execute(_sql("DELETE FROM price_history WHERE cigar_id = :cid"), {"cid": cigar_id})
        await db.execute(_sql("DELETE FROM scraper_name_aliases WHERE cigar_id = :cid"), {"cid": cigar_id})
        await db.delete(cigar)
        await db.commit()
    return {"ok": True}


@router.post("/api/categories/{cat_id}/reorder")
async def reorder_cigars(cat_id: int, request: Request):
    """按传入的 cigar_ids 顺序更新各雪茄的 sort_order"""
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    cigar_ids: list[int] = data.get("cigar_ids", [])
    async with AsyncSessionLocal() as db:
        for i, cid in enumerate(cigar_ids):
            r = await db.execute(select(Cigar).where(Cigar.id == cid))
            cigar = r.scalar_one_or_none()
            if cigar:
                cigar.sort_order = i
        await db.commit()
    return {"ok": True}


@router.post("/api/unmatched/{item_id}/quick-create")
async def quick_create_from_unmatched(item_id: int, request: Request):
    """
    从未匹配条目一键创建雪茄：
      1. 找到 UnmatchedItem
      2. 找到分类对应的主要 series（按已有雪茄 category_id 分布推断）
      3. 创建 Cigar（name=raw_name, series_id, category_id）
      4. 创建 ScraperNameAlias（source_slug + raw_name → new cigar）
      5. 删除 UnmatchedItem
    """
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    category_id = data.get("category_id")
    if not category_id:
        return JSONResponse({"error": "category_id required"}, status_code=400)

    async with AsyncSessionLocal() as db:
        # Load unmatched item
        r = await db.execute(select(UnmatchedItem).where(UnmatchedItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            return JSONResponse({"error": "unmatched item not found"}, status_code=404)

        # Load category to get brand_id
        r2 = await db.execute(select(Category).where(Category.id == category_id))
        cat = r2.scalar_one_or_none()
        if not cat:
            return JSONResponse({"error": "category not found"}, status_code=404)

        # Find dominant series_id for this category
        series_row = await db.execute(
            _sql("""
                SELECT series_id, COUNT(*) as cnt
                FROM cigars
                WHERE category_id = :cat_id
                GROUP BY series_id
                ORDER BY cnt DESC
                LIMIT 1
            """),
            {"cat_id": category_id},
        )
        series_hit = series_row.fetchone()

        if series_hit:
            series_id = series_hit[0]
        else:
            # Fall back: first series of this brand
            sr = await db.execute(
                select(Series).where(Series.brand_id == cat.brand_id).order_by(Series.id).limit(1)
            )
            sr_obj = sr.scalar_one_or_none()
            if not sr_obj:
                return JSONResponse({"error": "no series found for brand"}, status_code=400)
            series_id = sr_obj.id

        # ── 查重：同品牌下是否已存在同名雪茄 ────────────────────────
        existing_r = await db.execute(
            select(Cigar)
            .join(Series, Cigar.series_id == Series.id)
            .where(
                Series.brand_id == cat.brand_id,
                func.lower(Cigar.name) == func.lower(item.raw_name),
            )
            .limit(1)
        )
        existing_cigar = existing_r.scalar_one_or_none()

        if existing_cigar:
            # 已存在同名雪茄 → 复用，只补全 category_id（若未设置）
            cigar = existing_cigar
            if not cigar.category_id:
                cigar.category_id = category_id
            is_new = False
        else:
            # 全新雪茄 → 生成唯一 slug 并创建
            vitola     = data.get("vitola")     or None
            length_mm  = data.get("length_mm")  or None
            ring_gauge = data.get("ring_gauge") or None
            base_slug = _slugify(item.raw_name)[:120]
            slug = base_slug
            i = 2
            while True:
                chk = await db.execute(select(Cigar).where(Cigar.slug == slug))
                if not chk.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{i}"; i += 1
            cigar = Cigar(
                name=item.raw_name,
                slug=slug,
                series_id=series_id,
                category_id=category_id,
                vitola=vitola,
                length_mm=float(length_mm)  if length_mm  is not None else None,
                ring_gauge=float(ring_gauge) if ring_gauge is not None else None,
            )
            db.add(cigar)
            is_new = True
        await db.flush()  # ensure cigar.id is available

        # ── 建立当前条目的 alias ──────────────────────────────────
        dup = await db.execute(
            select(ScraperNameAlias).where(
                ScraperNameAlias.source_slug == item.source_slug,
                ScraperNameAlias.raw_name   == item.raw_name,
            )
        )
        if not dup.scalar_one_or_none():
            db.add(ScraperNameAlias(
                source_slug=item.source_slug,
                raw_name=item.raw_name,
                cigar_id=cigar.id,
            ))

        # ── 扫描同来源未匹配条目，批量为相似名称建 alias ──────────
        others_r = await db.execute(
            select(UnmatchedItem).where(
                UnmatchedItem.source_slug == item.source_slug,
                UnmatchedItem.id != item.id,
            )
        )
        others = others_r.scalars().all()
        auto_count = 0
        for other in others:
            if similarity(other.raw_name, item.raw_name) > 0.75:
                dup2 = await db.execute(
                    select(ScraperNameAlias).where(
                        ScraperNameAlias.source_slug == other.source_slug,
                        ScraperNameAlias.raw_name   == other.raw_name,
                    )
                )
                if not dup2.scalar_one_or_none():
                    db.add(ScraperNameAlias(
                        source_slug=other.source_slug,
                        raw_name=other.raw_name,
                        cigar_id=cigar.id,
                    ))
                await db.delete(other)
                auto_count += 1

        # Write price data from the unmatched item into prices table
        if item.price_single is not None or item.price_box is not None:
            src_r = await db.execute(
                select(Source).where(Source.slug == item.source_slug)
            )
            source = src_r.scalar_one_or_none()
            if source:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                # Upsert current price (prices has unique constraint on cigar_id+source_id)
                existing_price = await db.execute(
                    select(Price).where(
                        Price.cigar_id == cigar.id,
                        Price.source_id == source.id,
                    )
                )
                price_row = existing_price.scalar_one_or_none()
                if price_row:
                    price_row.price_single = item.price_single
                    price_row.price_box    = item.price_box
                    price_row.currency     = item.currency
                    price_row.product_url  = item.product_url
                    price_row.in_stock     = True
                    price_row.scraped_at   = now
                else:
                    db.add(Price(
                        cigar_id     = cigar.id,
                        source_id    = source.id,
                        price_single = item.price_single,
                        price_box    = item.price_box,
                        currency     = item.currency,
                        product_url  = item.product_url,
                        in_stock     = True,
                        scraped_at   = now,
                    ))
                # Also append to price history
                db.add(PriceHistory(
                    cigar_id     = cigar.id,
                    source_id    = source.id,
                    price_single = item.price_single,
                    price_box    = item.price_box,
                    currency     = item.currency,
                    scraped_at   = now,
                ))

        # Delete unmatched item
        await db.delete(item)
        await db.commit()

    return {
        "ok": True,
        "cigar_id": cigar.id,
        "is_new": is_new,
        "auto_matched": auto_count,
    }


@router.get("/api/cigars/search")
async def search_cigars(request: Request, q: str = ""):
    """全库雪茄名称搜索（供未匹配条目关联使用）。"""
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as db:
        stmt = select(Cigar).order_by(Cigar.name)
        if q:
            stmt = stmt.where(Cigar.name.ilike(f"%{q}%"))
        r = await db.execute(stmt.limit(30))
        cigars = r.scalars().all()
    return [{"id": c.id, "name": c.name} for c in cigars]


@router.post("/api/unmatched/{item_id}/link-alias")
async def link_unmatched_to_cigar(item_id: int, request: Request):
    """
    将未匹配条目关联到已有雪茄：
      1. 建立 ScraperNameAlias（source_slug + raw_name → cigar_id）
      2. 将价格写入 Price / PriceHistory
      3. 删除 UnmatchedItem
    """
    if not _require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    cigar_id = data.get("cigar_id")
    if not cigar_id:
        return JSONResponse({"error": "cigar_id required"}, status_code=400)

    async with AsyncSessionLocal() as db:
        item = await db.get(UnmatchedItem, item_id)
        if not item:
            return JSONResponse({"error": "unmatched item not found"}, status_code=404)
        cigar = await db.get(Cigar, cigar_id)
        if not cigar:
            return JSONResponse({"error": "cigar not found"}, status_code=404)

        # Create alias (ignore if already exists)
        dup = await db.execute(
            select(ScraperNameAlias).where(
                ScraperNameAlias.source_slug == item.source_slug,
                ScraperNameAlias.raw_name   == item.raw_name,
            )
        )
        if not dup.scalar_one_or_none():
            db.add(ScraperNameAlias(
                source_slug=item.source_slug,
                raw_name=item.raw_name,
                cigar_id=cigar_id,
            ))

        # Write price
        if item.price_single is not None or item.price_box is not None:
            from datetime import datetime, timezone
            src_r = await db.execute(select(Source).where(Source.slug == item.source_slug))
            source = src_r.scalar_one_or_none()
            if source:
                now = datetime.now(timezone.utc)
                existing_price = await db.execute(
                    select(Price).where(
                        Price.cigar_id == cigar_id,
                        Price.source_id == source.id,
                    )
                )
                price_row = existing_price.scalar_one_or_none()
                if price_row:
                    price_row.price_single = item.price_single
                    price_row.price_box    = item.price_box
                    price_row.currency     = item.currency
                    price_row.product_url  = item.product_url
                    price_row.in_stock     = True
                    price_row.scraped_at   = now
                else:
                    db.add(Price(
                        cigar_id    = cigar_id,
                        source_id   = source.id,
                        price_single= item.price_single,
                        price_box   = item.price_box,
                        currency    = item.currency,
                        product_url = item.product_url,
                        in_stock    = True,
                        scraped_at  = now,
                    ))
                db.add(PriceHistory(
                    cigar_id    = cigar_id,
                    source_id   = source.id,
                    price_single= item.price_single,
                    price_box   = item.price_box,
                    currency    = item.currency,
                    scraped_at  = now,
                ))

        await db.delete(item)
        await db.commit()

    return {"ok": True, "cigar_id": cigar_id, "cigar_name": cigar.name}
