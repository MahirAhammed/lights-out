# Time conversion to seconds
HOUR  = 3600
DAY   = 86400
WEEK  = 604800
MONTH = 2592000

CACHE_TTL = {
    "schedule":               MONTH,
    "current_race_weekend":   WEEK,
    "driver_standings":       WEEK,
    "constructor_standings":  WEEK,
}

# Hours to wait after session START time before fetching results
SESSION_RESULT_OFFSET = {
    "Sprint":      HOUR * 2,
    "Qualifying":  HOUR * 2,
    "Race":        HOUR * 3,
}

FLAGS = {
    "British":      "🇬🇧", "Dutch":        "🇳🇱", "Monegasque":   "🇲🇨",
    "Spanish":      "🇪🇸", "Australian":   "🇦🇺", "Mexican":      "🇲🇽",
    "Finnish":      "🇫🇮", "French":       "🇫🇷", "Canadian":     "🇨🇦",
    "German":       "🇩🇪", "Thai":         "🇹🇭", "Japanese":     "🇯🇵",
    "American":     "🇺🇸", "Chinese":      "🇨🇳", "Danish":       "🇩🇰",
    "Italian":      "🇮🇹", "Argentine":    "🇦🇷", "Brazilian":    "🇧🇷",
    "Austrian":     "🇦🇹", "Belgian":      "🇧🇪", "New Zealander":"🇳🇿",
    "Swiss":        "🇨🇭", "Polish":       "🇵🇱", "Swedish":      "🇸🇪",
}

CONSTRUCTOR_COLOURS = {
    "red_bull":         "#25487A",
    "mclaren":          "#FF8800",
    "ferrari":          "#E8002D",
    "mercedes":         "#75F1D3",
    "aston_martin":     "#229971",
    "alpine":           "#FF87BC",
    "haas":             "#F5F5F5",
    "rb":               "#6692FF",
    "williams":         "#005CAA",
    "audi":             "#5D615D",
    "cadillac":         "#BE991E"
}

NATIONAL_FLAGS = {
    "United Kingdom": "🇬🇧", "Netherlands":    "🇳🇱", "Monaco":         "🇲🇨",
    "Spain":          "🇪🇸", "Australia":      "🇦🇺", "Mexico":         "🇲🇽",
    "Finland":        "🇫🇮", "France":         "🇫🇷", "Canada":         "🇨🇦",
    "Germany":        "🇩🇪", "Thailand":       "🇹🇭", "Japan":          "🇯🇵",
    "United States":  "🇺🇸", "China":          "🇨🇳", "Denmark":        "🇩🇰",
    "Italy":          "🇮🇹", "Argentina":      "🇦🇷", "Brazil":         "🇧🇷",
    "Austria":        "🇦🇹", "Belgium":        "🇧🇪", "New Zealand":    "🇳🇿",
    "Switzerland":    "🇨🇭", "Poland":         "🇵🇱", "Sweden":         "🇸🇪",
    "United Arab Emirates" : "🇦🇪", "Qatar": "🇶🇦", "Singapore": "🇸🇬",
    "Azerbaijan": "🇦🇿", "Hungary": "🇭🇺",
}