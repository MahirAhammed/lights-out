# Time conversion to seconds
HOUR  = 3600
DAY   = 86400
WEEK  = 604800
MONTH = 2592000

CACHE_TTL = {
    "schedule":               WEEK,
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
    "red_bull":         "#4781D7",
    "mclaren":          "#F47600",
    "ferrari":          "#ED1131",
    "mercedes":         "#00D7B6",
    "aston_martin":     "#229971",
    "alpine":           "#00A1E8",
    "haas":             "#9C9FA2",
    "rb":               "#6C98FF",
    "williams":         "#1868DB",
    "audi":             "#F50537",
    "cadillac":         "#909090"
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