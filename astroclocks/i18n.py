"""Small translation table for AstroClocks UI strings."""

LANGUAGE_OPTIONS = (
    ("en", "English"),
    ("fr", "Français"),
)

LANGUAGE_NAMES = dict(LANGUAGE_OPTIONS)

TRANSLATIONS = {
    "en": {
        "app.subtitle": "Civil time, sidereal time, JNow coordinates and real-time local horizon",
        "button.settings": "Settings",
        "button.about": "About",
        "button.quit": "Quit",
        "button.fullscreen": "Full Screen (F11)",
        "button.search": "Search",
        "button.set": "Set",
        "button.default": "Default",
        "button.cancel": "Cancel",
        "button.apply": "Apply",
        "button.close": "Close",
        "settings.instrument": "Instrument display",
        "settings.hour_angle_offset": "T1m hour angle vernier (+6h East circle)",
        "settings.declination_offset": "T1m declination vernier (+90deg)",
        "about.title": "About AstroClocks",
        "about.version": "Version",
        "about.year": "Year",
        "about.author": "Author",
        "about.email": "Email",
        "about.phone": "Phone",
        "frame.site": "Observing site",
        "frame.search": "Find coordinates of an object",
        "frame.sky": "Local horizon",
        "frame.local_time": "Local Time ({timezone})",
        "frame.utc": "UTC",
        "frame.alpha": "Alpha JNow (h m s)",
        "frame.delta": "Delta JNow (d m s)",
        "frame.gmst": "Greenwich Sidereal Time",
        "frame.lst": "Local Sidereal Time",
        "frame.hour_angle": "Hour Angle{suffix}",
        "frame.hour_angle_offset_suffix": " (EAST circle +6h)",
        "frame.declination": "Declination{suffix}",
        "frame.declination_offset_suffix": " (+90deg)",
        "object_type.Asteroid": "Asteroid",
        "object_type.Comet": "Comet",
        "object_type.Dwarf Planet": "Dwarf Planet",
        "object_type.Planet": "Planet",
        "object_type.Natural Satellite": "Natural Satellite",
        "object_type.Star, Deep Sky Object": "Star, Deep Sky Object",
        "settings.title": "AstroClocks Settings",
        "settings.preset": "Known place",
        "settings.site_name": "Site name",
        "settings.custom_site": "Custom site",
        "settings.language": "Language",
        "settings.latitude": "Latitude",
        "settings.longitude": "Longitude",
        "settings.aladin_fov": "Aladin field",
        "settings.hint": "Latitude [-90, 90], longitude [-180, 180], Aladin field in degrees.",
        "settings.invalid_title": "Invalid settings",
        "site.latitude": "Latitude  : {value}",
        "site.longitude": "Longitude : {value}",
        "button.aladin": "Aladin {value:.2f}\N{DEGREE SIGN}",
        "error.must_be_number": "{label} must be a number.",
        "error.out_of_range": "{label} must be between {minimum} and {maximum}.",
        "sky.zenith": "Zenith",
        "sky.horizon_latitude": "Local horizon | Latitude {latitude:+.3f}\N{DEGREE SIGN}",
        "sky.target": "Target",
        "sky.pointer": "Pointer",
        "sky.target_set": "Target set from map",
        "sky.target_set_star": "Target set from map: {name}",
        "sky.above_horizon": "above horizon",
        "sky.below_horizon": "below horizon",
        "sky.status": (
            "LST {lst} | Target HA {hour_angle:+.2f}h | "
            "Alt {altitude:+.1f}\N{DEGREE SIGN} Az {azimuth:.0f}\N{DEGREE SIGN}\n"
            "Local horizon JNow: {note} | {count} named stars visible"
        ),
        "sky.unavailable": "Sky map unavailable: {error}",
        "result.target_coordinates": "{label}\nRA JNow: {ra}\nDec JNow: {dec}",
        "result.aladin_unavailable": "Interactive sky view unavailable. Check internet connection.",
        "result.aladin_opened": (
            "Opened interactive sky view (ICRS): RA {ra_deg:.6f}\N{DEGREE SIGN} "
            "Dec {dec_deg:+.6f}\N{DEGREE SIGN} | FOV {fov:.2f}\N{DEGREE SIGN}"
        ),
        "result.ephemerides_error": "An error occurred while retrieving the ephemerides.",
        "result.object_type_error": "Please select the right object type!",
        "result.no_object_type": "Please select an object type.",
        "result.object_not_found": (
            "Object not found!\nPlease enter a valid name\n(ex: M13, HIP114971, Sirius, ...)"
        ),
        "result.imcce_coordinates": (
            "ICRS coordinates from IMCCE:\nAlpha: {ra}\nDelta: {dec}"
        ),
        "result.sesame_coordinates": (
            "ICRS coordinates from Sesame:\nRA (Alpha): {ra}\nDec (Delta): {dec}"
        ),
    },
    "fr": {
        "app.subtitle": "Temps civil, temps sidéral, coordonnées JNow et horizon local en temps réel",
        "button.settings": "Paramètres",
        "button.about": "À propos",
        "button.quit": "Quitter",
        "button.fullscreen": "Plein écran (F11)",
        "button.search": "Rechercher",
        "button.set": "Valider",
        "button.default": "Défaut",
        "button.cancel": "Annuler",
        "button.apply": "Appliquer",
        "button.close": "Fermer",
        "settings.instrument": "Affichage instrument",
        "settings.hour_angle_offset": "Vernier angle horaire T1m (+6h cercle Est)",
        "settings.declination_offset": "Vernier déclinaison T1m (+90°)",
        "about.title": "À propos d'AstroClocks",
        "about.version": "Version",
        "about.year": "Année",
        "about.author": "Auteur",
        "about.email": "Email",
        "about.phone": "Téléphone",
        "frame.site": "Site d'observation",
        "frame.search": "Trouver les coordonnées d'un objet",
        "frame.sky": "Horizon local",
        "frame.local_time": "Temps local ({timezone})",
        "frame.utc": "UTC",
        "frame.alpha": "Alpha JNow (h m s)",
        "frame.delta": "Delta JNow (d m s)",
        "frame.gmst": "Temps sidéral de Greenwich",
        "frame.lst": "Temps sidéral local",
        "frame.hour_angle": "Angle horaire{suffix}",
        "frame.hour_angle_offset_suffix": " (cercle EST +6h)",
        "frame.declination": "Déclinaison{suffix}",
        "frame.declination_offset_suffix": " (+90°)",
        "object_type.Asteroid": "Astéroïde",
        "object_type.Comet": "Comète",
        "object_type.Dwarf Planet": "Planète naine",
        "object_type.Planet": "Planète",
        "object_type.Natural Satellite": "Satellite naturel",
        "object_type.Star, Deep Sky Object": "Étoile, objet du ciel profond",
        "settings.title": "Paramètres AstroClocks",
        "settings.preset": "Lieu connu",
        "settings.site_name": "Nom du site",
        "settings.custom_site": "Site personnalisé",
        "settings.language": "Langue",
        "settings.latitude": "Latitude",
        "settings.longitude": "Longitude",
        "settings.aladin_fov": "Champ Aladin",
        "settings.hint": "Latitude [-90, 90], longitude [-180, 180], champ Aladin en degrés.",
        "settings.invalid_title": "Paramètres invalides",
        "site.latitude": "Latitude  : {value}",
        "site.longitude": "Longitude : {value}",
        "button.aladin": "Aladin {value:.2f}\N{DEGREE SIGN}",
        "error.must_be_number": "{label} doit être un nombre.",
        "error.out_of_range": "{label} doit être entre {minimum} et {maximum}.",
        "sky.zenith": "Zénith",
        "sky.horizon_latitude": "Horizon local | Latitude {latitude:+.3f}\N{DEGREE SIGN}",
        "sky.target": "Cible",
        "sky.pointer": "Pointeur",
        "sky.target_set": "Cible définie depuis la carte",
        "sky.target_set_star": "Cible définie depuis la carte : {name}",
        "sky.above_horizon": "au-dessus de l'horizon",
        "sky.below_horizon": "sous l'horizon",
        "sky.status": (
            "LST {lst} | HA cible {hour_angle:+.2f}h | "
            "Alt {altitude:+.1f}\N{DEGREE SIGN} Az {azimuth:.0f}\N{DEGREE SIGN}\n"
            "Horizon local JNow : {note} | {count} étoiles nommées visibles"
        ),
        "sky.unavailable": "Carte du ciel indisponible : {error}",
        "result.target_coordinates": "{label}\nRA JNow : {ra}\nDéc JNow : {dec}",
        "result.aladin_unavailable": "Vue du ciel interactive indisponible. Vérifiez la connexion internet.",
        "result.aladin_opened": (
            "Vue du ciel interactive ouverte (ICRS) : RA {ra_deg:.6f}\N{DEGREE SIGN} "
            "Déc {dec_deg:+.6f}\N{DEGREE SIGN} | champ {fov:.2f}\N{DEGREE SIGN}"
        ),
        "result.ephemerides_error": "Une erreur est survenue pendant la récupération des éphémérides.",
        "result.object_type_error": "Veuillez sélectionner le bon type d'objet.",
        "result.no_object_type": "Veuillez sélectionner un type d'objet.",
        "result.object_not_found": (
            "Objet introuvable !\nVeuillez saisir un nom valide\n(ex : M13, HIP114971, Sirius, ...)"
        ),
        "result.imcce_coordinates": (
            "Coordonnées ICRS depuis IMCCE :\nAlpha : {ra}\nDelta : {dec}"
        ),
        "result.sesame_coordinates": (
            "Coordonnées ICRS depuis Sesame :\nRA (Alpha) : {ra}\nDéc (Delta) : {dec}"
        ),
    },
}


def translate(language, key, **values):
    catalog = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    template = catalog.get(key, TRANSLATIONS["en"].get(key, key))
    return template.format(**values)
