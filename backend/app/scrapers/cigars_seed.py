"""
初始化古巴雪茄品牌 / 系列 / 规格数据。
运行：python -m app.scrapers.cigars_seed
"""
import asyncio
import re
from sqlalchemy.dialects.postgresql import insert
from app.db import AsyncSessionLocal
from app.models import Brand, Series, Cigar

# ──────────────────────────────────────────────────────────────────────────────
# 数据定义
# ──────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[àáâãäå]", "a", s)
    s = re.sub(r"[èéêë]", "e", s)
    s = re.sub(r"[ìíîï]", "i", s)
    s = re.sub(r"[òóôõö]", "o", s)
    s = re.sub(r"[ùúûü]", "u", s)
    s = re.sub(r"[ñ]", "n", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# 品牌列表：(英文名, 国家)
BRANDS = [
    ("Bolivar",             "Cuba"),
    ("Cohiba",              "Cuba"),
    ("Cuaba",               "Cuba"),
    ("Diplomaticos",        "Cuba"),
    ("El Rey del Mundo",    "Cuba"),
    ("Fonseca",             "Cuba"),
    ("H. Upmann",           "Cuba"),
    ("Hoyo de Monterrey",   "Cuba"),
    ("Jose L. Piedra",      "Cuba"),
    ("Juan Lopez",          "Cuba"),
    ("La Gloria Cubana",    "Cuba"),
    ("Montecristo",         "Cuba"),
    ("Partagas",            "Cuba"),
    ("Por Larranaga",       "Cuba"),
    ("Punch",               "Cuba"),
    ("Quai d'Orsay",        "Cuba"),
    ("Rafael Gonzalez",     "Cuba"),
    ("Ramon Allones",       "Cuba"),
    ("Romeo y Julieta",     "Cuba"),
    ("Saint Luis Rey",      "Cuba"),
    ("Sancho Panza",        "Cuba"),
    ("Trinidad",            "Cuba"),
    ("Vegas Robaina",       "Cuba"),
    ("Vegueros",            "Cuba"),
    ("Flor de Cano",        "Cuba"),
    ("Guantanamera",        "Cuba"),
    ("Quintero",            "Cuba"),
    ("Combinaciones",       "Cuba"),
]

# 每个品牌的核心系列和规格
# 格式: brand_slug -> [(series_name, [(cigar_name, vitola, length_mm, ring_gauge), ...])]
CATALOG: dict[str, list] = {
    "cohiba": [
        ("Cohiba Linea Clasica", [
            ("Cohiba Lanceros",         "Lancero",       192, 38),
            ("Cohiba Coronas Especiales","Corona Especial",152, 38),
            ("Cohiba Esplendidos",       "Churchill",     178, 47),
            ("Cohiba Robustos",          "Robusto",       124, 50),
            ("Cohiba Siglo I",           "Perla",         102, 40),
            ("Cohiba Siglo II",          "Corona",        129, 42),
            ("Cohiba Siglo III",         "Laguito No.3",  155, 42),
            ("Cohiba Siglo IV",          "Corona Extra",  143, 46),
            ("Cohiba Siglo V",           "Laguito No.1",  170, 40),
            ("Cohiba Siglo VI",          "Gran Corona",   150, 52),
        ]),
        ("Cohiba Behike", [
            ("Cohiba Behike BHK 52",    "Laguito Especial",  152, 52),
            ("Cohiba Behike BHK 54",    "Laguito Especial",  160, 54),
            ("Cohiba Behike BHK 56",    "Laguito Especial",  168, 56),
        ]),
        ("Cohiba Short", [
            ("Cohiba Short",            "Cigarillo",      82,  27),
            ("Cohiba Club",             "Cigarillo",      80,  26),
            ("Cohiba Exquisitos",       "Seoane",         125, 36),
            ("Cohiba Panetelas",        "Panetela",       115, 26),
            ("Cohiba Maduros 5 Magicos","Robusto",        124, 50),
            ("Cohiba Maduros 5 Genios", "Piramides",      140, 52),
            ("Cohiba Maduros 5 Magicos Secretos", "Secretos", 127, 40),
        ]),
    ],
    "montecristo": [
        ("Montecristo Clasicos", [
            ("Montecristo No.1",        "Laguito No.1",  165, 42),
            ("Montecristo No.2",        "Piramides",     156, 52),
            ("Montecristo No.3",        "Corona",        142, 42),
            ("Montecristo No.4",        "Mareva",        129, 42),
            ("Montecristo No.5",        "Perla",         102, 40),
            ("Montecristo Especial",    "Laguito No.1",  192, 38),
            ("Montecristo Especial No.2","Laguito No.2", 152, 38),
            ("Montecristo Media Corona","Media Corona",   102, 42),
            ("Montecristo Open Eagle",  "Piramides Extra",185, 54),
            ("Montecristo Open Junior", "Short Robusto",  110, 50),
            ("Montecristo Open Master", "Edmundo",        135, 52),
        ]),
        ("Montecristo Edmundo", [
            ("Montecristo Edmundo",     "Edmundo",        135, 52),
            ("Montecristo Petit Edmundo","Petit Edmundo",  110, 52),
        ]),
    ],
    "partagas": [
        ("Partagas Clasicos", [
            ("Partagas Serie D No.4",   "Robusto",        124, 50),
            ("Partagas Serie D No.5",   "Robusto Extra",  110, 50),
            ("Partagas Serie E No.2",   "Piramides Extra",150, 54),
            ("Partagas Serie P No.2",   "Piramides",      156, 52),
            ("Partagas Lusitanias",     "Double Corona",  194, 49),
            ("Partagas 8-9-8 Varnished","Lonsdale",       170, 43),
            ("Partagas Mille Fleurs",   "Panetela",       129, 38),
            ("Partagas Shorts",         "Demi Tasse",      110, 42),
            ("Partagas Chicos",         "Cigarillo",       100, 29),
            ("Partagas Presidentes",    "Double Corona",   194, 47),
        ]),
    ],
    "romeo-y-julieta": [
        ("Romeo y Julieta Clasicos", [
            ("Romeo y Julieta Churchill",       "Churchill",    178, 47),
            ("Romeo y Julieta Wide Churchill",  "Double Churchill",124,55),
            ("Romeo y Julieta Short Churchill", "Robusto Extra", 124, 50),
            ("Romeo y Julieta Mille Fleurs",    "Panetela",     129, 38),
            ("Romeo y Julieta No.1",            "Lonsdale",     165, 42),
            ("Romeo y Julieta No.2",            "Corona",       129, 42),
            ("Romeo y Julieta No.3",            "Petit Corona",  117, 40),
            ("Romeo y Julieta Cedros de Luxe No.1","Lonsdale",  165, 42),
            ("Romeo y Julieta Cedros de Luxe No.2","Corona",    129, 42),
            ("Romeo y Julieta Cedros de Luxe No.3","Petit Corona",117,40),
        ]),
    ],
    "bolivar": [
        ("Bolivar Clasicos", [
            ("Bolivar Belicosos Finos",  "Piramides",    140, 52),
            ("Bolivar Coronas Extra",    "Corona Extra", 143, 44),
            ("Bolivar Coronas Gigantes", "Double Corona",185, 49),
            ("Bolivar Petit Coronas",    "Petit Corona", 129, 42),
            ("Bolivar Royal Coronas",    "Robusto",      124, 50),
            ("Bolivar Tubos No.1",       "Lonsdale Tubos",165,42),
            ("Bolivar Tubos No.2",       "Corona Tubos", 142, 42),
            ("Bolivar Tubos No.3",       "Mareva Tubos", 129, 42),
        ]),
    ],
    "h-upmann": [
        ("H. Upmann Clasicos", [
            ("H. Upmann No.2",           "Piramides",     156, 52),
            ("H. Upmann No.2 Tubos",     "Piramides",     156, 52),
            ("H. Upmann Magnum 46",      "Robusto Extra", 124, 46),
            ("H. Upmann Magnum 54",      "Edmundo",       135, 54),
            ("H. Upmann Royal Coronas",  "Robusto",       124, 50),
            ("H. Upmann Coronas Major",  "Dalias",        170, 43),
            ("H. Upmann Connoisseur No.1","Hermoso No.4", 127, 48),
            ("H. Upmann Sir Winston",    "Julieta No.2",  178, 47),
            ("H. Upmann Half Corona",    "Half Corona",    94, 44),
        ]),
    ],
    "hoyo-de-monterrey": [
        ("Hoyo de Monterrey Clasicos", [
            ("Hoyo de Monterrey Epicure No.1","Robusto Extra",143,46),
            ("Hoyo de Monterrey Epicure No.2","Robusto",      124,50),
            ("Hoyo de Monterrey Double Corona","Double Corona",194,49),
            ("Hoyo de Monterrey Le Hoyo de Rio Seco","Almuerzo",109,50),
            ("Hoyo de Monterrey Le Hoyo des Dieux","Corona Gorda",143,46),
            ("Hoyo de Monterrey Le Hoyo de Monterrey","Corona",142,42),
            ("Hoyo de Monterrey Le Hoyo du Prince","Almuerzo",127,40),
            ("Hoyo de Monterrey Palmas Extra","Lonsdale",165,42),
            ("Hoyo de Monterrey Short Hoyo Coronas","Mareva",117,40),
        ]),
    ],
    "trinidad": [
        ("Trinidad Clasicos", [
            ("Trinidad Coloniales",      "Corona Extra",  132, 44),
            ("Trinidad Fundadores",      "Laguito No.1",  192, 40),
            ("Trinidad Media Luna",      "Hermoso No.3",  110, 46),
            ("Trinidad Reyes",           "Petit Corona",  110, 40),
            ("Trinidad Robustos Extra",  "Robusto Extra", 155, 50),
            ("Trinidad Vigia",           "Mareva",        110, 40),
        ]),
    ],
    "ramon-allones": [
        ("Ramon Allones Clasicos", [
            ("Ramon Allones Allones Extra",     "Corona Extra",   143, 44),
            ("Ramon Allones Allones Superiores","Double Corona",  194, 49),
            ("Ramon Allones Club Allones",      "Robusto Extra",  133, 50),
            ("Ramon Allones Gigantes",          "Double Corona",  185, 49),
            ("Ramon Allones Petit Coronas",     "Petit Corona",   129, 42),
            ("Ramon Allones Small Club Coronas","Mareva",         110, 42),
            ("Ramon Allones Specially Selected","Robusto",        124, 50),
        ]),
    ],
    "punch": [
        ("Punch Clasicos", [
            ("Punch Churchill",         "Churchill",      178, 47),
            ("Punch Coronations",       "Corona",         142, 42),
            ("Punch Double Coronas",    "Double Corona",  194, 49),
            ("Punch Punch",             "Corona Extra",   143, 44),
            ("Punch Royal Coronations", "Corona Grande",  143, 42),
            ("Punch Petit Coronations", "Petit Corona",   129, 42),
        ]),
    ],
    "vegas-robaina": [
        ("Vegas Robaina Clasicos", [
            ("Vegas Robaina Don Alejandro","Double Corona",194,49),
            ("Vegas Robaina Famosos",      "Robusto",      124,50),
            ("Vegas Robaina Unicos",       "Piramides",    157,52),
        ]),
    ],
    "diplomaticos": [
        ("Diplomaticos Clasicos", [
            ("Diplomaticos No.2",       "Piramides",     156, 52),
            ("Diplomaticos No.3",       "Corona",        142, 42),
            ("Diplomaticos No.4",       "Mareva",        129, 42),
        ]),
    ],
    "san-cristobal-de-la-habana": [],
    "cuaba": [
        ("Cuaba Clasicos", [
            ("Cuaba Diademas",          "Diademas Extra",233, 55),
            ("Cuaba Distinguidos",      "Corona",        143, 44),
            ("Cuaba Divinos",           "Laguito No.1",  152, 43),
            ("Cuaba Exclusivos",        "Laguito No.3",  178, 46),
            ("Cuaba Generosos",         "Robusto",       132, 42),
            ("Cuaba Salomones",         "Gran Piramide",  184,57),
            ("Cuaba Tradicionales",     "Corona Extra",  143, 44),
        ]),
    ],
    "guantanamera": [
        ("Guantanamera Clasicos", [
            ("Guantanamera Cristales",  "Cristales",     132, 36),
            ("Guantanamera Decimos",    "Decimos",       100, 26),
            ("Guantanamera Minutos",    "Minutos",       110, 38),
            ("Guantanamera Nacionales", "Nacionales",    130, 45),
            ("Guantanamera Puritos",    "Puritos",       120, 32),
        ]),
    ],
    "vegueros": [
        ("Vegueros Clasicos", [
            ("Vegueros Entretiempos",   "Entretiempos",  127, 38),
            ("Vegueros Mananitas",      "Mananitas",     127, 33),
            ("Vegueros Tainos",         "Robusto",       124, 50),
        ]),
    ],
    "la-gloria-cubana": [
        ("La Gloria Cubana Clasicos", [
            ("La Gloria Cubana Serie D No.4","Robusto",  124, 50),
            ("La Gloria Cubana Medaille d'Or No.1","Laguito No.1",192,38),
            ("La Gloria Cubana Medaille d'Or No.2","Laguito No.2",155,43),
            ("La Gloria Cubana Medaille d'Or No.4","Seoane",125,32),
            ("La Gloria Cubana Tapados",   "Double Corona",185,49),
        ]),
    ],
    "el-rey-del-mundo": [
        ("El Rey del Mundo Clasicos", [
            ("El Rey del Mundo Choix Supreme","Robusto Extra",124,52),
            ("El Rey del Mundo Gran Corona",  "Gran Corona",  155,52),
            ("El Rey del Mundo Grandes de Espana","Double Corona",155,52),
            ("El Rey del Mundo Lunch Club",   "Mareva",       110,42),
            ("El Rey del Mundo Tainos",        "Taino",       177,54),
        ]),
    ],
    "por-larranaga": [
        ("Por Larranaga Clasicos", [
            ("Por Larranaga Montecarlos", "Lonsdale", 165, 42),
            ("Por Larranaga Picadores",   "Picadores", 150, 36),
        ]),
    ],
    "sancho-panza": [
        ("Sancho Panza Clasicos", [
            ("Sancho Panza Belicosos",  "Piramides",    140, 52),
            ("Sancho Panza Double Naturales","Double Corona",194,49),
            ("Sancho Panza Extra",      "Julieta No.2", 178, 47),
        ]),
    ],
    "flor-de-cano": [
        ("Flor de Cano Clasicos", [
            ("Flor de Cano Selectos",   "Lonsdale",     165, 42),
            ("Flor de Cano Short Churchill","Robusto Extra",124,50),
        ]),
    ],
    "rafael-gonzalez": [
        ("Rafael Gonzalez Clasicos", [
            ("Rafael Gonzalez Coronas Extra","Corona Extra",143,44),
            ("Rafael Gonzalez Lonsdale",     "Lonsdale",    165,42),
            ("Rafael Gonzalez Mille Fleurs", "Panetela",    129,38),
            ("Rafael Gonzalez Perlas",       "Perla",       102,40),
            ("Rafael Gonzalez Slenderellas", "Laguito No.1",192,38),
        ]),
    ],
    "juan-lopez": [
        ("Juan Lopez Clasicos", [
            ("Juan Lopez Seleccion No.1","Robusto Extra",    143, 46),
            ("Juan Lopez Seleccion No.2","Hermoso No.4",     127, 48),
        ]),
    ],
    "quintero": [
        ("Quintero Clasicos", [
            ("Quintero Churchill",      "Churchill",     178, 47),
            ("Quintero Media Corona",   "Mareva",        110, 42),
            ("Quintero Nacionales",     "Nacionales",    130, 40),
            ("Quintero Petit Quintero", "Petit Coronas", 129, 38),
        ]),
    ],
    "fonseca": [
        ("Fonseca Clasicos", [
            ("Fonseca Cosaccos",        "Cosaccos",      110, 42),
            ("Fonseca Delicias",        "Petit Coronas", 130, 40),
            ("Fonseca No.1",            "Laguito No.1",  155, 40),
        ]),
    ],
    "saint-luis-rey": [
        ("Saint Luis Rey Clasicos", [
            ("Saint Luis Rey Churchill",  "Churchill",    178, 47),
            ("Saint Luis Rey Regios",     "Robusto Extra",143, 46),
            ("Saint Luis Rey Series A",   "Piramides Extra",154,54),
            ("Saint Luis Rey Double Coronas","Double Corona",194,49),
        ]),
    ],
    "jose-l-piedra": [
        ("Jose L. Piedra Clasicos", [
            ("Jose L. Piedra Cazadores",   "Cazadores",   162, 42),
            ("Jose L. Piedra Conservas",   "Conservas",   127, 46),
            ("Jose L. Piedra Petit Cazadores","Mareva",   110, 42),
        ]),
    ],
    "combinaciones": [
        ("Combinaciones", [
            ("Combinaciones Seleccion", "Varied Box",     0,   0),
        ]),
    ],
}


async def seed():
    async with AsyncSessionLocal() as db:
        # 先插入 Brand
        brand_ids: dict[str, int] = {}
        for brand_name, country in BRANDS:
            slug = slugify(brand_name)
            stmt = insert(Brand).values(
                name=brand_name, slug=slug, country=country
            ).on_conflict_do_update(
                index_elements=["slug"],
                set_={"name": brand_name, "country": country},
            ).returning(Brand.id)
            result = await db.execute(stmt)
            brand_ids[slug] = result.scalar_one()

        await db.commit()

        # 插入 Series 和 Cigar
        series_count = 0
        cigar_count  = 0

        for brand_slug, series_list in CATALOG.items():
            if brand_slug not in brand_ids:
                continue
            brand_id = brand_ids[brand_slug]

            for series_name, cigars in series_list:
                series_slug = slugify(series_name)
                stmt = insert(Series).values(
                    brand_id=brand_id, name=series_name, slug=series_slug
                ).on_conflict_do_update(
                    index_elements=["slug"],
                    set_={"name": series_name, "brand_id": brand_id},
                ).returning(Series.id)
                result = await db.execute(stmt)
                series_id = result.scalar_one()
                series_count += 1

                for cigar_name, vitola, length_mm, ring_gauge in cigars:
                    cigar_slug = slugify(cigar_name)
                    stmt = insert(Cigar).values(
                        series_id  = series_id,
                        name       = cigar_name,
                        slug       = cigar_slug,
                        vitola     = vitola or None,
                        length_mm  = length_mm or None,
                        ring_gauge = ring_gauge or None,
                    ).on_conflict_do_update(
                        index_elements=["slug"],
                        set_={
                            "name":       cigar_name,
                            "vitola":     vitola or None,
                            "length_mm":  length_mm or None,
                            "ring_gauge": ring_gauge or None,
                        },
                    )
                    await db.execute(stmt)
                    cigar_count += 1

        await db.commit()

    print(f"Seeded {len(BRANDS)} brands, {series_count} series, {cigar_count} cigars.")


if __name__ == "__main__":
    asyncio.run(seed())
