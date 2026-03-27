"""
初始化所有来源网站到数据库。
运行：python -m app.scrapers.sources_seed
"""
import asyncio
from sqlalchemy.dialects.postgresql import insert
from app.db import AsyncSessionLocal
from app.models import Source

SOURCES = [
    # ── 德国 LCDH ────────────────────────────────────────────────────────────
    {"name": "德国小杜 LCDH",       "slug": "selected-cigars",     "base_url": "https://selected-cigars.com",              "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国科隆 LCDH",       "slug": "peterheinrichs",      "base_url": "http://www.peterheinrichs.de",             "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国大胡子 LCDH",     "slug": "tecon",               "base_url": "https://www.tecon-gmbh.de",               "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国汉堡 LCDH",       "slug": "thecigarsmoker",      "base_url": "http://www.thecigarsmoker.com",           "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国斯图加特 LCDH",   "slug": "casadelhabano-stgt",  "base_url": "http://www.casadelhabano-stuttgart.de",   "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国莱比锡 LCDH",     "slug": "tabak-kontor",        "base_url": "http://www.tabak-kontor.de",              "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国波恩 LCDH",       "slug": "lcdh-bonn",           "base_url": "https://www.lcdh-bonn.de",               "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国多米尼克 LCDH",   "slug": "dominiquelondon-de",  "base_url": "https://www.dominiquelondon.de",          "currency": "EUR", "group": "de_lcdh"},
    {"name": "德国科布伦茨 LCDH",   "slug": "lcdh-koblenz",        "base_url": "https://la-casa-del-habano-koblenz.de",   "currency": "EUR", "group": "de_lcdh"},
    # ── 荷兰 LCDH ────────────────────────────────────────────────────────────
    {"name": "荷兰海牙 LCDH",       "slug": "lcdh-thehague",       "base_url": "https://lacasadelhabano-thehague.com",    "currency": "EUR", "group": "nl_lcdh"},
    {"name": "荷兰阿姆斯特丹 LCDH", "slug": "lcdh-amsterdam",      "base_url": "http://lcdh-amsterdam.com",              "currency": "EUR", "group": "nl_lcdh"},
    # ── 瑞士 LCDH ────────────────────────────────────────────────────────────
    {"name": "瑞士卢加诺 LCDH",     "slug": "cigarmust",           "base_url": "https://cigarmust.com/en/",              "currency": "CHF", "group": "ch_lcdh"},
    {"name": "瑞士尼翁 LCDH",       "slug": "lcdh-nyon",           "base_url": "https://la-casa-del-habano-nyon.com/zh/","currency": "CHF", "group": "ch_lcdh"},
    {"name": "瑞士楚格 LCDH",       "slug": "siglomundo",          "base_url": "https://siglomundo.ch",                  "currency": "CHF", "group": "ch_lcdh"},
    {"name": "瑞士萨姆纳恩 LCDH",   "slug": "lcdh-samnaun",        "base_url": "https://lcdh-samnaun.ch/",               "currency": "CHF", "group": "ch_lcdh"},
    {"name": "瑞士圣加伦 LCDH",     "slug": "portmanntabak",       "base_url": "https://lcdh.portmanntabak.ch/",         "currency": "CHF", "group": "ch_lcdh"},
    {"name": "瑞士日内瓦 LCDH",     "slug": "lcdh-geneve",         "base_url": "https://lacasadelhabano-geneve.com",     "currency": "CHF", "group": "ch_lcdh"},
    # ── 英国 LCDH ────────────────────────────────────────────────────────────
    {"name": "英国 HAVANA LCDH",    "slug": "havahavana",          "base_url": "http://www.havahavana.com",              "currency": "GBP", "group": "uk_lcdh"},
    {"name": "英国 C.G LCDH",       "slug": "cgarsltd",            "base_url": "http://www.cgarsltd.co.uk",             "currency": "GBP", "group": "uk_lcdh"},
    {"name": "英国狐狸 LCDH",       "slug": "jjfox",               "base_url": "http://jjfox.co.uk",                    "currency": "GBP", "group": "uk_lcdh"},
    # ── 其他欧行 ─────────────────────────────────────────────────────────────
    {"name": "俄罗斯 LCDH",         "slug": "cigarday",            "base_url": "https://cigarday.ru/",                  "currency": "RUB", "group": "eu_other"},
    {"name": "巴斯特尔 LCDH",       "slug": "lcdh-kn",             "base_url": "https://www.lacasadelhabano.kn",        "currency": "EUR", "group": "eu_other"},
    {"name": "多米尼克比利时 LCDH", "slug": "lcdh-be",             "base_url": "https://www.lacasadelhabano-dl.be",     "currency": "EUR", "group": "eu_other"},
    {"name": "贝鲁特 LCDH",         "slug": "beirutdutyfree",      "base_url": "https://cigars.beirutdutyfree.com/",    "currency": "USD", "group": "eu_other"},
    {"name": "加拿大 CS LCDH",      "slug": "cubancigar-shop",     "base_url": "https://www.cubancigar-shop.com/",      "currency": "CAD", "group": "eu_other"},
    {"name": "多米尼克西班牙 LCDH", "slug": "dominiquelondon-es",  "base_url": "https://www.dominiquelondon.es",        "currency": "EUR", "group": "eu_other"},
    {"name": "布鲁塞尔 LCDH",       "slug": "lcdh-brussels",       "base_url": "https://lacasadelhabano.brussels",      "currency": "EUR", "group": "eu_other"},
    # ── 德国大师 HS ───────────────────────────────────────────────────────────
    {"name": "德国法库姆 HS",        "slug": "falkum",              "base_url": "https://www.falkum.de",                 "currency": "EUR", "group": "de_hs"},
    {"name": "德国烟屋 HS",          "slug": "pipehouse",           "base_url": "https://pipehouse.de",                  "currency": "EUR", "group": "de_hs"},
    {"name": "德国波恩 HS",          "slug": "pfeife-tabak",        "base_url": "https://www.pfeife-tabak-zigarre.de",   "currency": "EUR", "group": "de_hs"},
    {"name": "德国明斯特 HS",        "slug": "tabak-traeber",       "base_url": "https://www.tabak-traeber.de",          "currency": "EUR", "group": "de_hs"},
    {"name": "德国C茄 HS",           "slug": "c-cigars",            "base_url": "https://c-cigars.de",                   "currency": "EUR", "group": "de_hs"},
    {"name": "瑞士维拉斯 HS",        "slug": "cigarviu",            "base_url": "https://cigarviu.com/",                 "currency": "CHF", "group": "de_hs"},
    {"name": "瑞士蒙特勒 HS",        "slug": "tabashop",            "base_url": "https://tabashop.ch/",                  "currency": "CHF", "group": "de_hs"},
    # ── 欧水站 ───────────────────────────────────────────────────────────────
    {"name": "瑞士 Coc 站",          "slug": "cigars-of-cuba",      "base_url": "https://www.cigars-of-cuba.com/",       "currency": "CHF", "group": "eu_water"},
    {"name": "瑞士 One 站",          "slug": "cigarone",            "base_url": "https://www.cigarone.com/",             "currency": "CHF", "group": "eu_water"},
    {"name": "瑞士 Top 站",          "slug": "topcubans",           "base_url": "https://www.topcubans.com/",            "currency": "CHF", "group": "eu_water"},
    {"name": "瑞士 Vip 站",          "slug": "vipcigars",           "base_url": "http://www.vipcigars.com",              "currency": "CHF", "group": "eu_water"},
    {"name": "西站",                  "slug": "cigarshopworld",      "base_url": "https://cigarshopworld.com/",           "currency": "EUR", "group": "eu_water"},
    {"name": "格鲁吉亚站-2",          "slug": "egmcigars",           "base_url": "http://egmcigars.com",                  "currency": "USD", "group": "eu_water"},
    {"name": "格鲁吉亚站-1",          "slug": "hitcigars",           "base_url": "http://hitcigars.com",                  "currency": "USD", "group": "eu_water"},
    {"name": "TheCigar",              "slug": "thecigar",            "base_url": "https://thecigar.com/",                 "currency": "EUR", "group": "eu_water"},
    {"name": "德国雪茄世界",           "slug": "cigarworld",          "base_url": "https://www.cigarworld.de/",            "currency": "EUR", "group": "eu_water"},
    {"name": "瑞士补漏站",            "slug": "tabaklaedeli",        "base_url": "https://www.tabaklaedeli.ch/",          "currency": "CHF", "group": "eu_water"},
    {"name": "蒙特站",                "slug": "montefortuna",        "base_url": "https://www.montefortunacigars.com/",   "currency": "EUR", "group": "eu_water"},
    # ── 港站 ─────────────────────────────────────────────────────────────────
    {"name": "COH 站",               "slug": "cohcigars",           "base_url": "https://www.cohcigars.com/",            "currency": "HKD", "group": "hk"},
    {"name": "CH 站",                "slug": "cigarhome",           "base_url": "https://www.cigarhome.org/",            "currency": "HKD", "group": "hk"},
    {"name": "HP 站",                "slug": "hyhpuro",             "base_url": "https://hyhpuro.com/",                  "currency": "HKD", "group": "hk"},
    {"name": "NEXT 站",              "slug": "nextcigar",           "base_url": "https://www.nextcigar.cn/",             "currency": "HKD", "group": "hk"},
    {"name": "SO 站",                "slug": "timecigar",           "base_url": "http://www.timecigar.com/",             "currency": "HKD", "group": "hk"},
    # ── 非古站 ───────────────────────────────────────────────────────────────
    {"name": "美国70 站",            "slug": "70cigar",             "base_url": "http://www.70cigar.com/",               "currency": "USD", "group": "us"},
    {"name": "美国SP 站",            "slug": "smokingpipes",        "base_url": "http://www.smokingpipes.com/",          "currency": "USD", "group": "us"},
    {"name": "大西洋站",              "slug": "atlanticcigar",       "base_url": "http://www.atlanticcigar.com/",         "currency": "USD", "group": "us"},
    {"name": "BUS 站",               "slug": "cigarbus",            "base_url": "http://www.cigarbus.com",               "currency": "USD", "group": "us"},
    {"name": "CP 站",                "slug": "cigarplace",          "base_url": "http://www.cigarplace.biz/",            "currency": "USD", "group": "us"},
    {"name": "怪兽站",               "slug": "cigarmonster",        "base_url": "https://www.cigarmonster.com/",         "currency": "USD", "group": "us"},
    {"name": "NICE 站",              "slug": "niceash",             "base_url": "https://www.niceashcigars.com/",        "currency": "USD", "group": "us"},
    {"name": "OL 站",                "slug": "oltimes",             "base_url": "https://www.oltimescigars.com/",        "currency": "USD", "group": "us"},
    {"name": "哼站",                  "slug": "cigar4u",             "base_url": "https://cigar4u.org/",                  "currency": "USD", "group": "us"},
]


async def seed():
    async with AsyncSessionLocal() as db:
        for s in SOURCES:
            stmt = insert(Source).values(
                name=s["name"],
                slug=s["slug"],
                base_url=s["base_url"],
                currency=s["currency"],
                active=True,
                scraper_config={"group": s["group"]},
            ).on_conflict_do_nothing(index_elements=["slug"])
            await db.execute(stmt)
        await db.commit()
    print(f"Seeded {len(SOURCES)} sources.")


if __name__ == "__main__":
    asyncio.run(seed())
