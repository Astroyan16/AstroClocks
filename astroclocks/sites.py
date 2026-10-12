"""Preset observing locations, including indicative elevations in metres.

Elevation estimates at the preset WGS84 coordinates were retrieved on 2026-10-12
from Copernicus DEM 2021 GLO-90 via Open-Meteo (90 m horizontal resolution):
https://open-meteo.com/en/docs/elevation-api
https://doi.org/10.5270/ESA-c5d3d65
They are not surveyed telescope heights and remain editable by the user.

Published site elevations take precedence for Meudon, Nice, Pic du Midi and OHP:
https://observatoiredeparis.psl.eu/acces-au-campus-de-meudon.html
https://www.oca.eu/fr/histoire-et-patrimoine/presentation/histoire
https://www.n-py.com/en/node/6920
https://lidar.jpl.nasa.gov/ndacc/sites/ohp.php
"""

OBSERVATORIES_FRANCE = [
    ("France 92", "Observatoire de Meudon - T1m", 48.8050, 2.2301, 162),
    ("France 92", "Observatoire de Meudon - T60", 48.80667, 2.23012, 162),
    ("France 75", "Observatoire de Paris", 48.8366, 2.3369, 64),
    ("France 06", "Observatoire de Nice", 43.7279, 7.2995, 375),
    ("France 65", "Observatoire du Pic du Midi", 42.9369, 0.1426, 2877),
    ("France 04", "Observatoire de Haute-Provence", 43.9317, 5.7122, 650),
    ("France 67", "Observatoire de Strasbourg", 48.5839, 7.7681, 142),
    ("France 33", "Observatoire de Bordeaux", 44.8350, -0.5270, 71),
    ("France 18", "Station de radioastronomie de Nançay", 47.3800, 2.1960, 142),
]

EUROPEAN_CAPITALS = [
    ("Albanie", "Tirana", 41.3275, 19.8187, 110),
    ("Allemagne", "Berlin", 52.5200, 13.4050, 37),
    ("Andorre", "Andorre-la-Vieille", 42.5063, 1.5218, 1025),
    ("Autriche", "Vienne", 48.2082, 16.3738, 179),
    ("Belgique", "Bruxelles", 50.8503, 4.3517, 26),
    ("Biélorussie", "Minsk", 53.9006, 27.5590, 212),
    ("Bosnie-Herzégovine", "Sarajevo", 43.8563, 18.4131, 543),
    ("Bulgarie", "Sofia", 42.6977, 23.3219, 548),
    ("Chypre", "Nicosie", 35.1856, 33.3823, 130),
    ("Croatie", "Zagreb", 45.8150, 15.9819, 142),
    ("Danemark", "Copenhague", 55.6761, 12.5683, 10),
    ("Espagne", "Madrid", 40.4168, -3.7038, 666),
    ("Estonie", "Tallinn", 59.4370, 24.7536, 10),
    ("Finlande", "Helsinki", 60.1699, 24.9384, 8),
    ("France", "Paris", 48.8566, 2.3522, 36),
    ("Grèce", "Athènes", 37.9838, 23.7275, 92),
    ("Hongrie", "Budapest", 47.4979, 19.0402, 113),
    ("Irlande", "Dublin", 53.3498, -6.2603, 11),
    ("Islande", "Reykjavik", 64.1466, -21.9426, 7),
    ("Italie", "Rome", 41.9028, 12.4964, 58),
    ("Kosovo", "Pristina", 42.6629, 21.1655, 599),
    ("Lettonie", "Riga", 56.9496, 24.1052, 17),
    ("Liechtenstein", "Vaduz", 47.1410, 9.5209, 464),
    ("Lituanie", "Vilnius", 54.6872, 25.2797, 111),
    ("Luxembourg", "Luxembourg", 49.6116, 6.1319, 316),
    ("Macédoine du Nord", "Skopje", 41.9981, 21.4254, 251),
    ("Malte", "La Valette", 35.8989, 14.5146, 48),
    ("Moldavie", "Chisinau", 47.0105, 28.8638, 41),
    ("Monaco", "Monaco", 43.7384, 7.4246, 74),
    ("Monténégro", "Podgorica", 42.4304, 19.2594, 46),
    ("Norvège", "Oslo", 59.9139, 10.7522, 21),
    ("Pays-Bas", "Amsterdam", 52.3676, 4.9041, 5),
    ("Pologne", "Varsovie", 52.2297, 21.0122, 113),
    ("Portugal", "Lisbonne", 38.7223, -9.1393, 66),
    ("Roumanie", "Bucarest", 44.4268, 26.1025, 72),
    ("Royaume-Uni", "Londres", 51.5074, -0.1278, 16),
    ("Russie", "Moscou", 55.7558, 37.6173, 140),
    ("Saint-Marin", "Saint-Marin", 43.9356, 12.4473, 662),
    ("Serbie", "Belgrade", 44.8125, 20.4612, 114),
    ("Slovaquie", "Bratislava", 48.1486, 17.1077, 157),
    ("Slovénie", "Ljubljana", 46.0569, 14.5058, 299),
    ("Suède", "Stockholm", 59.3293, 18.0686, 24),
    ("Suisse", "Berne", 46.9480, 7.4474, 554),
    ("Tchéquie", "Prague", 50.0755, 14.4378, 251),
    ("Turquie", "Ankara", 39.9334, 32.8597, 883),
    ("Ukraine", "Kiev", 50.4501, 30.5234, 155),
    ("Vatican", "Vatican", 41.9029, 12.4534, 50),
]

FRENCH_METROPOLITAN_PREFECTURES = [
    ("France 01", "Bourg-en-Bresse", 46.2052, 5.2255, 231),
    ("France 02", "Laon", 49.5633, 3.6246, 179),
    ("France 03", "Moulins", 46.5667, 3.3333, 228),
    ("France 04", "Digne-les-Bains", 44.0920, 6.2356, 606),
    ("France 05", "Gap", 44.5586, 6.0786, 739),
    ("France 06", "Nice", 43.7102, 7.2620, 29),
    ("France 07", "Privas", 44.7353, 4.5994, 305),
    ("France 08", "Charleville-Mézières", 49.7625, 4.7244, 144),
    ("France 09", "Foix", 42.9639, 1.6058, 393),
    ("France 10", "Troyes", 48.2973, 4.0744, 113),
    ("France 11", "Carcassonne", 43.2130, 2.3491, 122),
    ("France 12", "Rodez", 44.3494, 2.5750, 641),
    ("France 13", "Marseille", 43.2965, 5.3698, 6),
    ("France 14", "Caen", 49.1829, -0.3707, 21),
    ("France 15", "Aurillac", 44.9300, 2.4440, 638),
    ("France 16", "Angoulême", 45.6484, 0.1562, 105),
    ("France 17", "La Rochelle", 46.1603, -1.1511, 12),
    ("France 18", "Bourges", 47.0810, 2.3988, 157),
    ("France 19", "Tulle", 45.2678, 1.7723, 219),
    ("France 2A", "Ajaccio", 41.9192, 8.7386, 9),
    ("France 2B", "Bastia", 42.6973, 9.4509, 15),
    ("France 21", "Dijon", 47.3220, 5.0415, 250),
    ("France 22", "Saint-Brieuc", 48.5142, -2.7658, 90),
    ("France 23", "Guéret", 46.1700, 1.8717, 455),
    ("France 24", "Périgueux", 45.1840, 0.7211, 111),
    ("France 25", "Besançon", 47.2378, 6.0241, 255),
    ("France 26", "Valence", 44.9334, 4.8924, 137),
    ("France 27", "Évreux", 49.0270, 1.1510, 64),
    ("France 28", "Chartres", 48.4439, 1.4890, 160),
    ("France 29", "Quimper", 47.9960, -4.1020, 16),
    ("France 30", "Nîmes", 43.8367, 4.3601, 57),
    ("France 31", "Toulouse", 43.6047, 1.4442, 153),
    ("France 32", "Auch", 43.6465, 0.5860, 170),
    ("France 33", "Bordeaux", 44.8378, -0.5792, 16),
    ("France 34", "Montpellier", 43.6110, 3.8767, 58),
    ("France 35", "Rennes", 48.1173, -1.6778, 44),
    ("France 36", "Châteauroux", 46.8114, 1.6868, 152),
    ("France 37", "Tours", 47.3941, 0.6848, 58),
    ("France 38", "Grenoble", 45.1885, 5.7245, 215),
    ("France 39", "Lons-le-Saunier", 46.6744, 5.5539, 264),
    ("France 40", "Mont-de-Marsan", 43.8911, -0.5006, 39),
    ("France 41", "Blois", 47.5861, 1.3359, 76),
    ("France 42", "Saint-Étienne", 45.4397, 4.3872, 526),
    ("France 43", "Le Puy-en-Velay", 45.0437, 3.8853, 655),
    ("France 44", "Nantes", 47.2184, -1.5536, 19),
    ("France 45", "Orléans", 47.9029, 1.9093, 116),
    ("France 46", "Cahors", 44.4475, 1.4400, 137),
    ("France 47", "Agen", 44.2031, 0.6164, 53),
    ("France 48", "Mende", 44.5180, 3.5000, 736),
    ("France 49", "Angers", 47.4784, -0.5632, 41),
    ("France 50", "Saint-Lô", 49.1150, -1.0900, 43),
    ("France 51", "Châlons-en-Champagne", 48.9567, 4.3631, 85),
    ("France 52", "Chaumont", 48.1110, 5.1396, 323),
    ("France 53", "Laval", 48.0707, -0.7734, 57),
    ("France 54", "Nancy", 48.6921, 6.1844, 207),
    ("France 55", "Bar-le-Duc", 48.7727, 5.1611, 186),
    ("France 56", "Vannes", 47.6582, -2.7608, 30),
    ("France 57", "Metz", 49.1193, 6.1757, 179),
    ("France 58", "Nevers", 46.9896, 3.1590, 200),
    ("France 59", "Lille", 50.6292, 3.0573, 27),
    ("France 60", "Beauvais", 49.4295, 2.0807, 71),
    ("France 61", "Alençon", 48.4329, 0.0913, 146),
    ("France 62", "Arras", 50.2910, 2.7775, 75),
    ("France 63", "Clermont-Ferrand", 45.7772, 3.0870, 416),
    ("France 64", "Pau", 43.2951, -0.3708, 214),
    ("France 65", "Tarbes", 43.2329, 0.0781, 314),
    ("France 66", "Perpignan", 42.6887, 2.8948, 41),
    ("France 67", "Strasbourg", 48.5734, 7.7521, 142),
    ("France 68", "Colmar", 48.0794, 7.3585, 196),
    ("France 69", "Lyon", 45.7640, 4.8357, 184),
    ("France 70", "Vesoul", 47.6206, 6.1550, 223),
    ("France 71", "Mâcon", 46.3069, 4.8287, 191),
    ("France 72", "Le Mans", 48.0061, 0.1996, 70),
    ("France 73", "Chambéry", 45.5646, 5.9178, 286),
    ("France 74", "Annecy", 45.8992, 6.1294, 449),
    ("France 75", "Paris", 48.8566, 2.3522, 36),
    ("France 76", "Rouen", 49.4432, 1.0993, 16),
    ("France 77", "Melun", 48.5399, 2.6608, 54),
    ("France 78", "Versailles", 48.8049, 2.1204, 144),
    ("France 79", "Niort", 46.3237, -0.4648, 27),
    ("France 80", "Amiens", 49.8941, 2.2958, 36),
    ("France 81", "Albi", 43.9298, 2.1480, 177),
    ("France 82", "Montauban", 44.0221, 1.3520, 102),
    ("France 83", "Toulon", 43.1242, 5.9280, 14),
    ("France 84", "Avignon", 43.9493, 4.8055, 29),
    ("France 85", "La Roche-sur-Yon", 46.6705, -1.4264, 72),
    ("France 86", "Poitiers", 46.5802, 0.3404, 120),
    ("France 87", "Limoges", 45.8336, 1.2611, 271),
    ("France 88", "Épinal", 48.1744, 6.4512, 329),
    ("France 89", "Auxerre", 47.7982, 3.5738, 119),
    ("France 90", "Belfort", 47.6380, 6.8628, 364),
    ("France 91", "Évry-Courcouronnes", 48.6298, 2.4418, 80),
    ("France 92", "Nanterre", 48.8924, 2.2153, 53),
    ("France 93", "Bobigny", 48.9086, 2.4397, 45),
    ("France 94", "Créteil", 48.7904, 2.4556, 38),
    ("France 95", "Pontoise", 49.0510, 2.1006, 58),
]


def preset_country(category):
    return "France" if category.startswith("France") else category


def _make_preset(category, name, latitude, longitude, altitude_m):
    return {
        "category": category,
        "country": preset_country(category),
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "altitude_m": altitude_m,
    }


LOCATION_PRESETS = [
    _make_preset(*site)
    for group in (OBSERVATORIES_FRANCE, EUROPEAN_CAPITALS, FRENCH_METROPOLITAN_PREFECTURES)
    for site in group
]


def preset_label(preset):
    return f"{preset['category']} - {preset['name']}"
