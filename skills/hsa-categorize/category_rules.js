// Generated from category_rules.json by tools/make_rules_js.py. Do not edit; change the JSON and run the tool.
window.CATEGORY_RULES = {
 "version": 1,
 "about": "One rules file for the review page and the Python tools. Title-word categories are a guess from the product type at the start of the title; Amazon's own category path wins when a product has one. Suggestions only: they sort and fold, and never set a status. See eligibility_reference.md.",
 "title_head": {
  "pattern": "\\s(?:for|with|captures)\\s|\\s[-–—|]\\s|,",
  "flags": "i"
 },
 "title_categories": [
  {
   "pattern": "refund issued|your refund|refund will|cancelled|return is complete|return request|replacement is complete|your replacement|in transit",
   "flags": "i",
   "icon": "↩️",
   "name": "Refunded or cancelled"
  },
  {
   "pattern": "gift card|egift",
   "flags": "i",
   "icon": "🎁",
   "name": "Gift card"
  },
  {
   "pattern": "psyllium|probiotic|supplement|vitamin|multivitamin|multi-vitamin|magnesium|\\biron\\b|tribiotic",
   "flags": "i",
   "icon": "💊",
   "name": "Vitamins and supplements"
  },
  {
   "pattern": "lactaid|fexofenadine|allergy|antacid|menstrual|panty liner|liners|band-?aid|bandage|curad|first.?aid|mosquito|bug bite|bite relief|debrox|earwax|covid|\\bflu\\b|massager|eye mask|thermometer|\\bpills?\\b|medicine",
   "flags": "i",
   "icon": "💊",
   "name": "Health and OTC"
  },
  {
   "pattern": "purifier|humidifier",
   "flags": "i",
   "icon": "🌿",
   "name": "Home and garden"
  },
  {
   "pattern": "\\bdogs?\\b|\\bcats?\\b|\\bpet (food|toy|bed|supplies|treats?)|bacon|treats|chicken|ball launcher|chuckit",
   "flags": "i",
   "icon": "🐶",
   "name": "Pet"
  },
  {
   "pattern": "shoe|sneaker|crocs|clog|running|glove|shorts|shirt|pants|goggles|swim|fins|\\bhat\\b|costume|sock|jacket|waist tr|brabic",
   "flags": "i",
   "icon": "👟",
   "name": "Clothing and shoes"
  },
  {
   "pattern": "\btoy\b|fidget|cube|squish|sensory|spinner|speedcube|toy gun",
   "flags": "i",
   "icon": "🧸",
   "name": "Toys and games"
  },
  {
   "pattern": "book|novel|guide|hobbit|smash|kart|violin|piano|abeka|arithmetic|math|study|slam|who knew|manga",
   "flags": "i",
   "icon": "📚",
   "name": "Books and games"
  },
  {
   "pattern": "\\bpens?\\b|pencil|marker|highlighter|notebook|notepad|binder|ruler|folder|label maker|sheet protector|divider|journal|planner|calculator|stapler|school|thank you card",
   "flags": "i",
   "icon": "📎",
   "name": "Office and school"
  },
  {
   "pattern": "ramen|ramyun|noodle|\\brice\\b|coffee|\\btea\\b|snack|cookie|pretzel|soup|sauce|seasoning|flour|sugar|gummi|candy|drink|gatorade|spam|cracker|goldfish|sparkling|omelette|ketchup|tofu",
   "flags": "i",
   "icon": "🍜",
   "name": "Food and drink"
  },
  {
   "pattern": "dish|laundry|detergent|sanitizer|cleaner|cleaning|lysol|method|bleach|descal|sponge|duster|broom|mop|paper towel|toilet paper|bath tissue|napkin|wax paper|trash bag|dryer|lint",
   "flags": "i",
   "icon": "🧽",
   "name": "Cleaning and paper"
  },
  {
   "pattern": "\\bpan\\b|skillet|waffle|kettle|coffee maker|food scale|juicer|lunch box|bento|\\bcups?\\b|\\bplates?\\b|spoon|springform|bowl|cling|foil|mailer|cutlery",
   "flags": "i",
   "icon": "🍳",
   "name": "Kitchen"
  },
  {
   "pattern": "router|cable|adapter|charger|usb|\\btv\\b|fire stick|remote|microphone|\\bmic\\b|memory card|microsd|keyboard|mouse|tripod|speaker|camera|\\bled\\b|bulb|toner|cartridge|battery|smart lock|thermostat|vacuum|drone|walkie|phone|monitor|printer|fuse|dash|joystick|screen",
   "flags": "i",
   "icon": "🔌",
   "name": "Electronics"
  },
  {
   "pattern": "cosmetic|shadow|palette|polish|makeup|lotion|cream|shampoo|body wash|soap|cetaphil|la roche|bobbi|opi|clio|toothpaste|sensodyne|colgate|therabreath|floss|mouthwash|\\bgum\\b|xylitol|shaver",
   "flags": "i",
   "icon": "🧴",
   "name": "Personal care"
  },
  {
   "pattern": "garden|hose|weed|pest|raid|insect|wasp|fertilizer|plant|miracle|pvc|fitting|caulk|washer|allen|wrench|chainsaw|deck belt|faucet|shower|drain|gutter|\\btool\\b|velcro|putty|mount|table|desk|chair|furniture|laminate|dollhouse|brick|mortar|shelf|sign|filter|purifier|humidifier|fuel|wd-40|sprayer|candle|decor",
   "flags": "i",
   "icon": "🌿",
   "name": "Home and garden"
  }
 ],
 "amazon_categories": [
  {
   "pattern": "Household Supplies",
   "flags": "",
   "icon": "🧽",
   "name": "Cleaning and paper"
  },
  {
   "pattern": "Vitamins|Dietary Supplements",
   "flags": "",
   "icon": "💊",
   "name": "Vitamins and supplements"
  },
  {
   "pattern": "^Baby",
   "flags": "",
   "icon": "🍼",
   "name": "Baby"
  },
  {
   "pattern": "^Pet Supplies",
   "flags": "",
   "icon": "🐶",
   "name": "Pet"
  },
  {
   "pattern": "^Health & Household",
   "flags": "",
   "icon": "💊",
   "name": "Health and OTC"
  },
  {
   "pattern": "Kitchen & Dining",
   "flags": "",
   "icon": "🍳",
   "name": "Kitchen"
  },
  {
   "pattern": "^Beauty & Personal Care",
   "flags": "",
   "icon": "🧴",
   "name": "Personal care"
  },
  {
   "pattern": "^(Electronics|Cell Phones|Musical Instruments)",
   "flags": "",
   "icon": "🔌",
   "name": "Electronics"
  },
  {
   "pattern": "^Books",
   "flags": "",
   "icon": "📚",
   "name": "Books and games"
  },
  {
   "pattern": "^Toys & Games",
   "flags": "",
   "icon": "🧸",
   "name": "Toys and games"
  },
  {
   "pattern": "^Clothing, Shoes",
   "flags": "",
   "icon": "👟",
   "name": "Clothing and shoes"
  },
  {
   "pattern": "^Grocery",
   "flags": "",
   "icon": "🍜",
   "name": "Food and drink"
  },
  {
   "pattern": "^Office Products",
   "flags": "",
   "icon": "📎",
   "name": "Office and school"
  },
  {
   "pattern": "^Gift Cards",
   "flags": "",
   "icon": "🎁",
   "name": "Gift card"
  },
  {
   "pattern": "^(Home & Kitchen|Patio|Tools & Home)",
   "flags": "",
   "icon": "🌿",
   "name": "Home and garden"
  }
 ],
 "medical_words": {
  "pattern": "brace|support|compression|thermometer|blood pressure|monitor|bandage|first aid|hearing|cpap|contact lens|reading glasses|pump|ointment|medicine|allergy|antacid|test kit|covid|patch",
  "flags": "i"
 },
 "drug_words": {
  "pattern": "ketoconazole|hydrocortisone|ibuprofen|acetaminophen|antifungal|medicated",
  "flags": "i"
 },
 "health_category": "Health and OTC",
 "unlikely_categories": [
  "Personal care",
  "Vitamins and supplements",
  "Baby",
  "Clothing and shoes",
  "Home and garden",
  "Food and drink"
 ],
 "tiers": {
  "badge": {
   "n": 4,
   "label": "Highly likely"
  },
  "likely": {
   "n": 3,
   "label": "Likely"
  },
  "unlikely": {
   "n": 2,
   "label": "Unlikely"
  },
  "highly_unlikely": {
   "n": 1,
   "label": "Highly unlikely"
  }
 }
};
