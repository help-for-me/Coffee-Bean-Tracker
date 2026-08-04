# Reference vocabulary used to steer extraction (embedded in the prompt so
# the model has known terms to check ambiguous label text against) and to
# lightly correct near-typos after extraction. None of these lists are
# exhaustive - real labels use plenty of valid terms outside them - so
# nothing here should ever be used to reject or force-fit a value, only to
# disambiguate and to catch small spelling slips.

KNOWN_PROCESSES = [
    "Washed",
    "Natural",
    "Honey",
    "Black Honey",
    "Red Honey",
    "Yellow Honey",
    "White Honey",
    "Anaerobic",
    "Anaerobic Natural",
    "Anaerobic Washed",
    "Carbonic Maceration",
    "Double Fermentation",
    "Wet-Hulled",
    "Pulped Natural",
    "Semi-Washed",
]

KNOWN_VARIETIES = [
    "Bourbon",
    "Typica",
    "Caturra",
    "Catuai",
    "Castillo",
    "Colombia",
    "Pacamara",
    "Pacas",
    "Geisha",
    "Gesha",
    "SL28",
    "SL34",
    "Sudan Rume",
    "Tabi",
    "Maragogype",
    "Villa Sarchi",
    "Java",
    "Mundo Novo",
    "Kent",
    "Heirloom",
]

KNOWN_REGIONS = [
    # Colombia
    "Huila", "Nariño", "Cauca", "Tolima", "Antioquia", "Quindío", "Risaralda",
    "Caldas", "Valle del Cauca", "Santander",
    # Ethiopia
    "Yirgacheffe", "Sidamo", "Guji", "Harrar", "Limu",
    # Kenya
    "Nyeri", "Kirinyaga", "Muranga",
    # Costa Rica
    "Tarrazú", "West Valley", "Central Valley",
    # Guatemala
    "Antigua", "Huehuetenango", "Atitlán",
    # Panama
    "Boquete", "Volcán",
    # Brazil
    "Cerrado", "Sul de Minas", "Mogiana",
]
