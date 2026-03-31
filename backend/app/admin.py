"""
SQLAdmin 后台管理界面
访问地址：/admin
账号密码在 .env 中配置（ADMIN_USERNAME / ADMIN_PASSWORD）
"""
import re

from markupsafe import Markup
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings
from app.db import AsyncSessionLocal, engine
from app.models.user import User, UserPriceAlert
from app.models.price import Price
from app.models.cigar import Cigar
from app.models.brand import Brand
from app.models.series import Series
from app.models.source import Source
from app.models.scraper_run import ScraperRun, UnmatchedItem
from app.models.exchange_rate import ExchangeRate
from app.models.alias import ScraperNameAlias


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ── 认证 ──────────────────────────────────────────────────────────────────────

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if (
            form.get("username") == settings.admin_username
            and form.get("password") == settings.admin_password
        ):
            request.session["admin"] = True
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin", False)


# ── 用户管理 ──────────────────────────────────────────────────────────────────

class UserAdmin(ModelView, model=User):
    name = "用户"
    name_plural = "用户管理"
    icon = "fa-solid fa-users"

    column_list = [
        User.id, User.email, User.nickname,
        User.subscription_status, User.subscription_expires_at,
        User.registered_at, User.last_login_at,
    ]
    column_searchable_list = [User.email, User.nickname, User.subscription_status]
    column_sortable_list = [User.id, User.registered_at, User.subscription_status]

    # 可编辑字段（手动开通 PRO 等）
    form_include_pk = False
    form_columns = [
        User.nickname, User.subscription_status,
        User.subscription_expires_at, User.is_email_verified,
    ]

    can_create = False
    can_delete = False


class UserAlertAdmin(ModelView, model=UserPriceAlert):
    name = "价格提醒"
    name_plural = "用户提醒"
    icon = "fa-solid fa-bell"

    column_list = [
        UserPriceAlert.id, UserPriceAlert.user_id,
        UserPriceAlert.cigar_id, UserPriceAlert.alert_type,
        UserPriceAlert.target_price, UserPriceAlert.currency,
        UserPriceAlert.is_active, UserPriceAlert.created_at,
        UserPriceAlert.last_triggered_at,
    ]
    column_sortable_list = [UserPriceAlert.created_at, UserPriceAlert.last_triggered_at]
    column_searchable_list = [UserPriceAlert.alert_type]

    can_create = False
    can_delete = True


# ── 爬虫监控 ──────────────────────────────────────────────────────────────────

class ScraperRunAdmin(ModelView, model=ScraperRun):
    name = "爬虫记录"
    name_plural = "爬虫运行记录"
    icon = "fa-solid fa-spider"

    column_list = [
        ScraperRun.id, ScraperRun.source_slug,
        ScraperRun.started_at, ScraperRun.finished_at,
        ScraperRun.status,
        ScraperRun.items_scraped, ScraperRun.items_matched, ScraperRun.items_unmatched,
        ScraperRun.error_msg,
    ]
    column_sortable_list = [ScraperRun.started_at, ScraperRun.source_slug, ScraperRun.status]
    column_searchable_list = [ScraperRun.source_slug, ScraperRun.status]

    can_create = False
    can_edit = False
    can_delete = True


class UnmatchedItemAdmin(ModelView, model=UnmatchedItem):
    name = "未匹配条目"
    name_plural = "未匹配条目"
    icon = "fa-solid fa-triangle-exclamation"

    column_list = [
        UnmatchedItem.id, UnmatchedItem.source_slug,
        UnmatchedItem.raw_name,
        UnmatchedItem.match_score, UnmatchedItem.best_candidate,
        UnmatchedItem.price_single, UnmatchedItem.price_box, UnmatchedItem.currency,
        UnmatchedItem.product_url, UnmatchedItem.run_id,
        "trigger_btn",
    ]
    column_labels = {"trigger_btn": "触发爬虫"}
    column_searchable_list = [UnmatchedItem.raw_name, UnmatchedItem.source_slug]
    column_sortable_list = [UnmatchedItem.id, UnmatchedItem.source_slug]

    column_formatters = {
        "product_url": lambda m, a: Markup(
            f'<a href="{m.product_url}" target="_blank" rel="noopener">🔗 打开</a>'
        ) if m.product_url else "",
        "raw_name": lambda m, a: Markup(m.raw_name),
        "trigger_btn": lambda m, a: Markup(f"""
<button class="btn btn-sm btn-outline-primary"
        onclick="triggerOne('{m.source_slug}',this)">⚡ 触发</button>
<script>(function(){{
  if(window._unmatchedTriggerInit)return; window._unmatchedTriggerInit=true;
  async function triggerOne(slug,btn){{
    btn.disabled=true; btn.textContent='运行中…'; btn.className='btn btn-sm btn-warning';
    try{{
      const r=await fetch('/admin-tools/trigger/'+slug,{{method:'POST'}});
      if(r.ok){{btn.textContent='✓ 已触发';btn.className='btn btn-sm btn-success';}}
      else{{btn.textContent='✗ 失败';btn.className='btn btn-sm btn-danger';}}
    }}catch(e){{btn.textContent='✗ 失败';btn.className='btn btn-sm btn-danger';}}
  }}
  window.triggerOne=triggerOne;
}})();</script>"""),
    }

    can_create = False
    can_edit = False
    can_delete = True


class ScraperNameAliasAdmin(ModelView, model=ScraperNameAlias):
    name = "名称别名"
    name_plural = "爬虫名称别名"
    icon = "fa-solid fa-link"

    column_list = [
        ScraperNameAlias.id, ScraperNameAlias.source_slug,
        ScraperNameAlias.raw_name, ScraperNameAlias.cigar_id,
        ScraperNameAlias.created_at,
    ]
    column_searchable_list = [ScraperNameAlias.source_slug, ScraperNameAlias.raw_name]
    column_sortable_list = [ScraperNameAlias.id, ScraperNameAlias.source_slug, ScraperNameAlias.created_at]

    form_columns = [ScraperNameAlias.source_slug, ScraperNameAlias.raw_name, ScraperNameAlias.cigar_id]

    can_create = True
    can_edit = True
    can_delete = True


# ── 数据维护 ──────────────────────────────────────────────────────────────────

class BrandAdmin(ModelView, model=Brand):
    name = "品牌"
    name_plural = "品牌管理"
    icon = "fa-solid fa-copyright"

    column_list = [Brand.id, Brand.name, Brand.slug, Brand.country, Brand.image_url]
    column_searchable_list = [Brand.name, Brand.slug]
    column_sortable_list = [Brand.id, Brand.name]

    form_columns = [Brand.name, Brand.slug, Brand.country, Brand.image_url]

    can_create = True
    can_edit = True
    can_delete = False

    async def after_model_change(self, data, model, is_created, request) -> None:
        """品牌 slug 变更后，级联更新所有下属系列的 slug。"""
        if is_created:
            return
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Series).where(Series.brand_id == model.id)
            )
            series_list = result.scalars().all()
            for s in series_list:
                s.slug = _slugify(f"{model.slug}-{s.name}")
            await db.commit()


class SeriesAdmin(ModelView, model=Series):
    name = "系列"
    name_plural = "系列管理"
    icon = "fa-solid fa-layer-group"

    column_list = [Series.id, Series.brand_id, Series.name, Series.slug]
    column_searchable_list = [Series.name, Series.slug]
    column_sortable_list = [Series.id, Series.brand_id, Series.name]

    form_columns = [Series.brand_id, Series.name, Series.slug]

    can_create = True
    can_edit = True
    can_delete = False


class CigarAdmin(ModelView, model=Cigar):
    name = "雪茄"
    name_plural = "雪茄列表"
    icon = "fa-solid fa-box"

    column_list = [
        Cigar.id, Cigar.name, Cigar.slug,
        Cigar.series_id, Cigar.vitola,
        Cigar.length_mm, Cigar.ring_gauge,
        Cigar.edition_type, Cigar.edition, Cigar.parent_cigar_id,
    ]
    column_searchable_list = [Cigar.name, Cigar.slug, Cigar.edition_type]
    column_sortable_list = [Cigar.id, Cigar.name, Cigar.series_id, Cigar.edition_type]

    form_columns = [
        Cigar.series_id, Cigar.name, Cigar.slug,
        Cigar.vitola, Cigar.length_mm, Cigar.ring_gauge,
        Cigar.edition_type, Cigar.edition, Cigar.parent_cigar_id,
    ]

    can_create = True
    can_edit = True
    can_delete = False


class SourceAdmin(ModelView, model=Source):
    name = "来源站点"
    name_plural = "爬虫站点管理"
    icon = "fa-solid fa-globe"

    column_list = [
        Source.id, Source.name, Source.slug,
        Source.base_url, Source.currency, Source.active,
        "trigger_btn",
    ]
    column_labels  = {"trigger_btn": "操作"}
    column_searchable_list = [Source.name, Source.slug]
    column_sortable_list = [Source.id, Source.name, Source.active]

    form_columns = [Source.name, Source.base_url, Source.currency, Source.active]

    can_create = False
    can_delete = False

    column_formatters = {
        "trigger_btn": lambda m, a: Markup(f"""
<button class="btn btn-sm btn-outline-primary"
        onclick="triggerOne('{m.slug}',this)">⚡ 触发</button>
<script>(function(){{
  if(window._scraperInit)return; window._scraperInit=true;
  async function triggerOne(slug,btn){{
    btn.disabled=true; btn.textContent='运行中…'; btn.className='btn btn-sm btn-warning';
    try{{
      const r=await fetch('/admin-tools/trigger/'+slug,{{method:'POST'}});
      if(r.ok){{btn.textContent='✓ 已触发';btn.className='btn btn-sm btn-success';}}
      else{{btn.textContent='✗ 失败';btn.className='btn btn-sm btn-danger';}}
    }}catch(e){{btn.textContent='✗ 失败';btn.className='btn btn-sm btn-danger';}}
  }}
  window.triggerOne=triggerOne;
  async function triggerAll(btn){{
    if(!confirm('确认触发全站爬取？通常需要数分钟，请勿重复点击。'))return;
    btn.disabled=true; btn.textContent='⏳ 全站触发中…';
    try{{
      const r=await fetch('/admin-tools/trigger',{{method:'POST'}});
      if(r.ok){{btn.textContent='✓ 全站已触发';btn.classList.replace('btn-warning','btn-success');}}
      else{{btn.textContent='✗ 失败';btn.classList.replace('btn-warning','btn-danger');}}
    }}catch(e){{btn.textContent='✗ 失败';}}
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    const anchor=document.querySelector('.page-pretitle')||document.querySelector('h2');
    if(!anchor)return;
    const wrap=anchor.closest('.col,.col-auto')||anchor.parentElement;
    const btn=document.createElement('button');
    btn.className='btn btn-warning ms-3';
    btn.textContent='⚡ 触发全站爬取';
    btn.onclick=function(){{triggerAll(this);}};
    wrap.appendChild(btn);
  }});
}})();</script>"""),
    }


class PriceAdmin(ModelView, model=Price):
    name = "当前价格"
    name_plural = "价格总览"
    icon = "fa-solid fa-tag"

    column_list = [
        Price.id, Price.cigar_id, Price.source_id,
        Price.price_single, Price.price_box, Price.currency,
        Price.in_stock, Price.scraped_at,
    ]
    column_sortable_list = [Price.scraped_at, Price.cigar_id, Price.source_id]
    column_searchable_list = [Price.currency]

    can_create = False
    can_edit = False
    can_delete = False


class ExchangeRateAdmin(ModelView, model=ExchangeRate):
    name = "汇率"
    name_plural = "汇率表"
    icon = "fa-solid fa-money-bill-transfer"

    column_list = [ExchangeRate.currency, ExchangeRate.rate_to_usd, ExchangeRate.updated_at]
    column_sortable_list = [ExchangeRate.currency, ExchangeRate.updated_at]

    can_create = False
    can_delete = False


# ── 工厂函数（在 main.py 里调用）────────────────────────────────────────────

def create_admin(app) -> Admin:
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret_key)
    admin = Admin(
        app,
        engine=engine,
        authentication_backend=authentication_backend,
        title="🍁 雪茄比价 — 管理后台",
        base_url="/admin",
    )

    admin.add_view(UserAdmin)
    admin.add_view(UserAlertAdmin)
    admin.add_view(ScraperRunAdmin)
    admin.add_view(UnmatchedItemAdmin)
    admin.add_view(ScraperNameAliasAdmin)
    admin.add_view(BrandAdmin)
    admin.add_view(SeriesAdmin)
    admin.add_view(CigarAdmin)
    admin.add_view(SourceAdmin)
    admin.add_view(PriceAdmin)
    admin.add_view(ExchangeRateAdmin)

    return admin
