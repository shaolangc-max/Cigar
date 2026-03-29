"""
SQLAdmin 后台管理界面
访问地址：/admin
账号密码在 .env 中配置（ADMIN_USERNAME / ADMIN_PASSWORD）
"""
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings
from app.db import engine
from app.models.user import User, UserPriceAlert
from app.models.price import Price
from app.models.cigar import Cigar
from app.models.source import Source
from app.models.scraper_run import ScraperRun, UnmatchedItem
from app.models.exchange_rate import ExchangeRate


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
    column_searchable_list = [User.email, User.nickname]
    column_sortable_list = [User.id, User.registered_at, User.subscription_status]
    column_filters = [User.subscription_status]

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
    column_filters = [UserPriceAlert.alert_type, UserPriceAlert.is_active]

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
    column_searchable_list = [ScraperRun.source_slug]
    column_filters = [ScraperRun.status, ScraperRun.source_slug]

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
        UnmatchedItem.price_single, UnmatchedItem.price_box, UnmatchedItem.currency,
        UnmatchedItem.product_url, UnmatchedItem.run_id,
    ]
    column_searchable_list = [UnmatchedItem.raw_name, UnmatchedItem.source_slug]
    column_sortable_list = [UnmatchedItem.id, UnmatchedItem.source_slug]
    column_filters = [UnmatchedItem.source_slug]

    can_create = False
    can_edit = False
    can_delete = True


# ── 数据维护 ──────────────────────────────────────────────────────────────────

class CigarAdmin(ModelView, model=Cigar):
    name = "雪茄"
    name_plural = "雪茄列表"
    icon = "fa-solid fa-box"

    column_list = [
        Cigar.id, Cigar.name, Cigar.slug,
        Cigar.series_id, Cigar.vitola,
        Cigar.length_mm, Cigar.ring_gauge,
    ]
    column_searchable_list = [Cigar.name, Cigar.slug]
    column_sortable_list = [Cigar.id, Cigar.name, Cigar.series_id]

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
    ]
    column_searchable_list = [Source.name, Source.slug]
    column_sortable_list = [Source.id, Source.name, Source.active]
    column_filters = [Source.active]

    form_columns = [Source.name, Source.base_url, Source.currency, Source.active]

    can_create = False
    can_delete = False


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
    column_filters = [Price.in_stock, Price.currency]

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
    admin.add_view(CigarAdmin)
    admin.add_view(SourceAdmin)
    admin.add_view(PriceAdmin)
    admin.add_view(ExchangeRateAdmin)

    return admin
