"""Blind hold-out 3: queries for the gaps the 29 researched files (kb_*) were written to fill.

Written and labelled from the files' HEADINGS only, BEFORE any retrieval was run on them (split="holdout3").
Free-form intents are written in English, Hindi and Hinglish with one gold; chart-derived intents use each real
engine chart's own dasha pair, house lords, planet houses, Sade Sati state and yogas.
"""

from __future__ import annotations

G = lambda f, h=None, g=2, c=None: {"file": f, "h": h, "c": c, "g": g}  # noqa: E731
AD, MD, SS, YG, HL, PH = ("kb_dasha_antardasha_combinations", "kb_dasha_mahadasha_effects", "kb_dasha_sade_sati_dhaiya",
                          "kb_chart_yogas_catalogue", "kb_chart_house_lords_in_houses", "kb_chart_planets_in_houses_vedic")
AK, DO, GL, LC = ("kb_match_ashtakoota_guna_milan", "kb_match_doshas_and_cancellations", "kb_lang_glossary_hi_en",
                  "kb_lang_core_topics_hi")

GAP_INTENTS = [
    ("n-ashtakoota-score", "matching", "vedic",
     {"en": "How is the Ashtakoota score out of 36 points calculated?",
      "hi": "अष्टकूट मिलान में 36 में से गुण कैसे गिने जाते हैं?",
      "hg": "Ashtakoota milan mein 36 mein se points kaise gine jaate hain?"},
     [G(AK, r"Overview|Reading the Total"), G(LC, r"कुंडली मिलान", 1)]),
    ("n-bhakoot", "matching", "vedic",
     {"en": "What is Bhakoot dosha and when is it cancelled?",
      "hi": "भकूट दोष क्या है और यह कब निरस्त होता है?",
      "hg": "Bhakoot dosh kya hota hai aur kab cancel hota hai?"},
     [G(DO, r"Bhakoot Dosha"), G(AK, r"Bhakoot \(Rasi\) Koota", 1)]),
    ("n-nadi", "matching", "vedic",
     {"en": "What is Nadi dosha in kundli matching?",
      "hi": "कुंडली मिलान में नाड़ी दोष क्या होता है?",
      "hg": "Kundli milan mein Nadi dosh kya hota hai?"},
     [G(DO, r"Nadi Dosha"), G(AK, r"Nadi Koota", 1)]),
    ("n-gana", "matching", "vedic",
     {"en": "What do Deva, Manushya and Rakshasa gana mean for compatibility?",
      "hi": "देव, मनुष्य और राक्षस गण का मिलान में क्या अर्थ है?",
      "hg": "Deva, Manushya aur Rakshasa gan ka matching mein kya matlab hai?"},
     [G(AK, r"Gana Koota"), G(DO, r"Gana Dosha", 1)]),
    ("n-manglik-cancel", "matching", "vedic",
     {"en": "Under what conditions is Manglik dosha cancelled?",
      "hi": "किन स्थितियों में मांगलिक दोष का परिहार हो जाता है?",
      "hg": "Kin conditions mein Manglik dosh ka pariharan ho jata hai?"},
     [G(DO, r"Manglik .*cancellations"), G(DO, r"Manglik .*rule", 1)]),
    ("n-relationship-types", "matching", "vedic",
     {"en": "Can Ashtakoota matching be used for friends or business partners?",
      "hi": "क्या अष्टकूट मिलान दोस्तों या बिज़नेस पार्टनर के लिए इस्तेमाल हो सकता है?",
      "hg": "Kya Ashtakoota matching friends ya business partners ke liye use ho sakti hai?"},
     [G("kb_match_relationship_types", r"Limits of Ashtakoota|Business partnership|Friendship")]),
    ("n-upapada", "matching", "vedic",
     {"en": "What is Upapada Lagna in marriage analysis?",
      "hi": "विवाह विश्लेषण में उपपद लग्न क्या होता है?",
      "hg": "Marriage analysis mein Upapada Lagna kya hota hai?"},
     [G("kb_match_beyond_36_points", r"Upapada")]),
    ("n-tithi", "panchang", "vedic",
     {"en": "What is a tithi and how is it calculated?",
      "hi": "तिथि क्या होती है और इसकी गणना कैसे होती है?",
      "hg": "Tithi kya hoti hai aur uski calculation kaise hoti hai?"},
     [G("kb_panchang_five_limbs", r"Tithi: the lunar day")]),
    ("n-rahu-kaal", "panchang", "vedic",
     {"en": "How is Rahu Kaal calculated and what should be avoided during it?",
      "hi": "राहु काल की गणना कैसे होती है और उस समय क्या नहीं करना चाहिए?",
      "hg": "Rahu Kaal ka calculation kaise hota hai aur us time kya avoid karna chahiye?"},
     [G("kb_panchang_daily_timings", r"Rahu Kaal")]),
    ("n-abhijit", "panchang", "vedic",
     {"en": "What is Abhijit Muhurta and why is it considered auspicious?",
      "hi": "अभिजीत मुहूर्त क्या है और इसे शुभ क्यों माना जाता है?",
      "hg": "Abhijit Muhurta kya hai aur ise shubh kyun mana jata hai?"},
     [G("kb_panchang_daily_timings", r"Abhijit")]),
    ("n-new-business-muhurta", "panchang", "vedic",
     {"en": "Which day and time is good for starting a new business?",
      "hi": "नया व्यापार शुरू करने के लिए कौन सा दिन और समय शुभ होता है?",
      "hg": "Naya business shuru karne ke liye kaun sa din aur time shubh hota hai?"},
     [G("kb_panchang_muhurta_basics", r"By activity"), G("kb_panchang_muhurta_basics", r"layered method", 1)]),
    ("n-panchak", "panchang", "vedic",
     {"en": "What is Panchak and what should be avoided during it?",
      "hi": "पंचक क्या होता है और उसमें क्या नहीं करना चाहिए?",
      "hg": "Panchak kya hota hai aur usme kya avoid karna chahiye?"},
     [G("kb_panchang_muhurta_basics", r"Panchaka")]),
    ("n-ekadashi", "panchang", "vedic",
     {"en": "What is Ekadashi and how is the fast observed?",
      "hi": "एकादशी क्या है और इसका व्रत कैसे रखा जाता है?",
      "hg": "Ekadashi kya hai aur iska vrat kaise rakha jata hai?"},
     [G("kb_panchang_eclipses_and_special_days", r"Ekadashi")]),
    ("n-eclipse-sutak", "panchang", "vedic",
     {"en": "How do eclipses and sutak affect auspicious timing?",
      "hi": "ग्रहण और सूतक का शुभ मुहूर्त पर क्या असर पड़ता है?",
      "hg": "Grahan aur sutak ka shubh muhurat par kya asar padta hai?"},
     [G("kb_panchang_eclipses_and_special_days", r"Eclipses"), G("kb_panchang_muhurta_basics", r"Eclipses", 1)]),
    ("n-gochara-moon", "gochara", "vedic",
     {"en": "From which houses of the natal Moon is a Saturn transit favourable?",
      "hi": "जन्म चंद्र से शनि का गोचर किन भावों में शुभ माना जाता है?",
      "hg": "Janam Moon se Saturn ka gochar kin houses mein shubh mana jata hai?"},
     [G("kb_panchang_gochara_transit_rules", r"Favourable houses|Saturn"), G("kb_dasha_gochara_and_dasha_interplay", r"Gochara from the Moon", 1)]),
    ("n-vedha", "gochara", "vedic",
     {"en": "What is Vedha, the obstruction of a favourable gochara?",
      "hi": "गोचर में वेध यानी शुभ गोचर की रुकावट क्या होती है?",
      "hg": "Gochar mein Vedha yaani shubh gochar ki rukawat kya hoti hai?"},
     [G("kb_panchang_gochara_transit_rules", r"Vedha"), G("kb_dasha_gochara_and_dasha_interplay", r"Vedha", 1)]),
    ("n-double-transit", "gochara", "vedic",
     {"en": "What is the double transit of Jupiter and Saturn?",
      "hi": "गुरु और शनि का दोहरा गोचर (डबल ट्रांज़िट) क्या होता है?",
      "hg": "Jupiter aur Saturn ka double transit kya hota hai?"},
     [G("kb_dasha_gochara_and_dasha_interplay", r"Double transit")]),
    ("n-sade-sati-phases", "sade_sati", "vedic",
     {"en": "What are the three phases of Sade Sati?",
      "hi": "साढ़ेसाती के तीन चरण कौन से होते हैं?",
      "hg": "Sade sati ke teen phases kaun se hote hain?"},
     [G(SS, r"three phases"), G(SS, r"What Sade Sati is", 1)]),
    ("n-dhaiya", "sade_sati", "vedic",
     {"en": "What is Dhaiya or Kantaka Shani?",
      "hi": "ढैया या कंटक शनि क्या होता है?",
      "hg": "Dhaiya ya Kantak Shani kya hota hai?"},
     [G(SS, r"Ashtama Shani and Kantaka")]),
    ("n-antardasha-length", "dashas", "vedic",
     {"en": "How are antardasha lengths calculated within a Vimshottari mahadasha?",
      "hi": "विंशोत्तरी महादशा में अंतर्दशा की अवधि कैसे निकाली जाती है?",
      "hg": "Vimshottari mahadasha mein antardasha ki duration kaise nikalte hain?"},
     [G("kb_dasha_vimshottari_foundations", r"Antardasha proportions")]),
    ("n-dasha-balance", "dashas", "vedic",
     {"en": "What is the balance of the first dasha at birth?",
      "hi": "जन्म के समय पहली दशा की शेष अवधि क्या होती है?",
      "hg": "Birth ke time pehli dasha ka balance kya hota hai?"},
     [G("kb_dasha_vimshottari_foundations", r"Balance of the first dasha")]),
    ("n-yogini", "dashas", "vedic",
     {"en": "What is Yogini dasha and how is it different from Vimshottari?",
      "hi": "योगिनी दशा क्या है और यह विंशोत्तरी से कैसे अलग है?",
      "hg": "Yogini dasha kya hai aur Vimshottari se kaise alag hai?"},
     [G("kb_dasha_alternative_systems", r"Yogini dasha")]),
    ("n-dignity-degrees", "dignity", "vedic",
     {"en": "At what degrees are the planets exalted and debilitated in Vedic astrology?",
      "hi": "वैदिक ज्योतिष में ग्रह किन अंशों पर उच्च और नीच के होते हैं?",
      "hg": "Vedic astrology mein planets kin degrees par exalted aur debilitated hote hain?"},
     [G("kb_chart_planets_in_signs_dignity", r"Exaltation and debilitation")]),
    ("n-moolatrikona", "dignity", "vedic",
     {"en": "What is moolatrikona and which sign ranges does each planet use?",
      "hi": "मूलत्रिकोण क्या है और हर ग्रह की कौन सी राशि सीमा होती है?",
      "hg": "Moolatrikona kya hai aur har planet ka kaun sa sign range hota hai?"},
     [G("kb_chart_planets_in_signs_dignity", r"Moolatrikona")]),
    ("n-combustion", "dignity", "vedic",
     {"en": "What is combustion (asta) of a planet?",
      "hi": "ग्रह का अस्त होना यानी दहन क्या होता है?",
      "hg": "Planet ka asta hona yaani combustion kya hota hai?"},
     [G("kb_chart_planets_in_signs_dignity", r"Combustion")]),
    ("n-functional-libra", "chart", "vedic",
     {"en": "Which planets are functional benefics and malefics for Libra lagna?",
      "hi": "तुला लग्न के लिए कौन से ग्रह कारक और कौन से मारक होते हैं?",
      "hg": "Tula lagna ke liye kaun se planets functional benefic aur malefic hote hain?"},
     [G("kb_chart_functional_nature_by_lagna", r"Libra \(Tula\) lagna"), G("kb_chart_functional_nature_by_lagna", r"Summary table", 1)]),
    ("n-d10", "chart", "vedic",
     {"en": "What does the Dashamsa D10 chart show about career?",
      "hi": "दशमांश D10 कुंडली करियर के बारे में क्या दिखाती है?",
      "hg": "Dashamsa D10 chart career ke baare mein kya dikhata hai?"},
     [G("kb_chart_divisional_charts", r"D10 Dashamsa")]),
    ("n-vargottama", "chart", "vedic",
     {"en": "What is Vargottama and why does it strengthen a planet?",
      "hi": "वर्गोत्तम क्या होता है और इससे ग्रह मज़बूत क्यों होता है?",
      "hg": "Vargottama kya hota hai aur isse planet strong kyun hota hai?"},
     [G("kb_chart_divisional_charts", r"Vargottama")]),
    ("n-karakas", "chart", "vedic",
     {"en": "What are the Jaimini chara karakas such as Atmakaraka and Darakaraka?",
      "hi": "जैमिनी के चर कारक जैसे आत्मकारक और दारकारक क्या हैं?",
      "hg": "Jaimini ke chara karaka jaise Atmakaraka aur Darakaraka kya hain?"},
     [G("kb_chart_karakas_and_arudha", r"Jaimini chara")]),
    ("n-moon-nak-no-time", "chart", "vedic",
     {"en": "What can be said from my Moon sign and nakshatra when I do not know my birth time?",
      "hi": "जन्म समय पता न हो तो चंद्र राशि और नक्षत्र से क्या कहा जा सकता है?",
      "hg": "Birth time pata na ho to Moon sign aur nakshatra se kya bola ja sakta hai?"},
     [G("kb_chart_nakshatra_pada_and_ascendant_notes", r"What can be said with Moon sign")]),
    ("n-saturn-mahadasha", "dashas", "vedic",
     {"en": "What does the Saturn Mahadasha usually bring?",
      "hi": "शनि की महादशा आमतौर पर क्या फल देती है?",
      "hg": "Shani ki mahadasha aam taur par kya phal deti hai?"},
     [G(MD, r"Saturn Mahadasha"), G(AD, r"Saturn Mahadasha", 1)]),
    ("n-jup-mer-pair", "dashas", "vedic",
     {"en": "Jupiter Mahadasha with Mercury Antardasha: what is the result?",
      "hi": "गुरु महादशा में बुध की अंतर्दशा का क्या फल होता है?",
      "hg": "Guru mahadasha mein Budh ki antardasha ka kya result hota hai?"},
     [G(AD, r"Jupiter Mahadasha", c=r"\*\*Jupiter-Mercury\*\*")]),
    ("n-7th-lord-12th", "houses", "vedic",
     {"en": "What happens when the 7th lord is placed in the 12th house?",
      "hi": "सातवें भाव का स्वामी बारहवें भाव में हो तो क्या फल होता है?",
      "hg": "7th lord 12th house mein ho to kya result hota hai?"},
     [G(HL, r"7th lord in each house")]),
    ("n-moon-7th", "houses", "vedic",
     {"en": "What is the result of the Moon in the 7th house?",
      "hi": "चंद्रमा सातवें भाव में हो तो क्या फल मिलता है?",
      "hg": "Moon 7th house mein ho to kya phal milta hai?"},
     [G(PH, r"Moon in the 7th house")]),
    ("n-gajakesari", "yogas", "vedic",
     {"en": "What is Gajakesari yoga and when does it form?",
      "hi": "गजकेसरी योग क्या है और यह कब बनता है?",
      "hg": "Gajakesari yog kya hai aur kab banta hai?"},
     [G(YG, r"Gajakesari Yoga")]),
    ("n-kaal-sarp", "yogas", "vedic",
     {"en": "What is Kaal Sarp dosha and how serious is it?",
      "hi": "कालसर्प दोष क्या है और यह कितना गंभीर होता है?",
      "hg": "Kaal Sarp dosh kya hai aur kitna serious hota hai?"},
     [G(YG, r"Kaal Sarp Dosha")]),
    ("n-mantra-japa", "remedies", "vedic",
     {"en": "How should planetary mantra japa be done?",
      "hi": "ग्रहों के मंत्र का जप कैसे करना चाहिए?",
      "hg": "Grahon ke mantra ka jap kaise karna chahiye?"},
     [G("kb_remedy_traditional_remedies", r"Mantra \(japa\)")]),
    ("n-gemstone-rules", "remedies", "vedic",
     {"en": "What are the classical rules and cautions for wearing gemstones?",
      "hi": "रत्न पहनने के शास्त्रीय नियम और सावधानियां क्या हैं?",
      "hg": "Ratna pehenne ke classical rules aur savdhaniyan kya hain?"},
     [G("kb_remedy_traditional_remedies", r"Gemstones \(ratna\)")]),
    ("n-remedy-red-flags", "remedies", "vedic",
     {"en": "Which remedies should an astrologer never recommend?",
      "hi": "ज्योतिषी को कौन से उपाय कभी नहीं बताने चाहिए?",
      "hg": "Astrologer ko kaun se upay kabhi recommend nahi karne chahiye?"},
     [G("kb_remedy_traditional_remedies", r"Red flags"), G("kb_remedy_lifestyle_and_ethics", r"Hard boundaries", 1)]),
    ("n-hindi-12-bhav", "language", "vedic",
     {"en": "What are the twelve bhavas called in Hindi and what does each mean?",
      "hi": "बारह भावों के नाम और उनके अर्थ क्या हैं?",
      "hg": "Barah bhavon ke naam aur unke matlab kya hain?"},
     [G(LC, r"बारह भाव"), G(GL, r"The 12 Bhavas", 1)]),
    ("n-hindi-dasha-words", "language", "vedic",
     {"en": "What do the Hindi words mahadasha and antardasha mean?",
      "hi": "महादशा और अंतर्दशा शब्दों का क्या मतलब है?",
      "hg": "Mahadasha aur antardasha words ka kya matlab hota hai?"},
     [G(GL, r"Dasha vocabulary"), G(LC, r"विंशोत्तरी दशा", 1)]),
    ("n-lagna-vs-moon", "language", "vedic",
     {"en": "What is the difference between my lagna and my Moon sign?",
      "hi": "मेरे लग्न और चंद्र राशि में क्या फ़र्क है?",
      "hg": "Mere lagna aur Moon sign mein kya farak hai?"},
     [G(LC, r"लग्न और चंद्र राशि"), G("kb_chart_nakshatra_pada_and_ascendant_notes", r"Moon-sign", 1)]),
]

# HOLD-OUT 4: written AFTER the retrieval fixes made against holdout 3 were frozen; no retrieval was run on these before
# this file was committed. The honest generalisation estimate for the new corpus.
HOLDOUT4 = [
    ("p-pitra-dosha", "yogas", "vedic",
     {"en": "What is Pitra dosha and how is it understood in Jyotish?",
      "hi": "पितृ दोष क्या है और ज्योतिष में इसे कैसे समझा जाता है?",
      "hg": "Pitra dosh kya hai aur Jyotish mein ise kaise samjha jata hai?"},
     [G(YG, r"Pitra Dosha")]),
    ("p-chandra-mangala", "yogas", "vedic",
     {"en": "What does Chandra-Mangala yoga mean?",
      "hi": "चंद्र-मंगल योग का क्या अर्थ है?",
      "hg": "Chandra-Mangal yog ka kya matlab hota hai?"},
     [G(YG, r"Chandra-Mangala")]),
    ("p-kemadruma", "yogas", "vedic",
     {"en": "What is Kemadruma yoga and is it always harmful?",
      "hi": "केमद्रुम योग क्या है और क्या यह हमेशा हानिकारक होता है?",
      "hg": "Kemadruma yog kya hai aur kya ye hamesha harmful hota hai?"},
     [G(YG, r"Kemadruma")]),
    ("p-ashtottari", "dashas", "vedic",
     {"en": "What is the Ashtottari dasha system of 108 years?",
      "hi": "108 वर्ष की अष्टोत्तरी दशा पद्धति क्या है?",
      "hg": "108 saal ki Ashtottari dasha system kya hai?"},
     [G("kb_dasha_alternative_systems", r"Ashtottari dasha")]),
    ("p-pushkara", "dignity", "vedic",
     {"en": "What is Pushkara navamsa and Pushkara bhaga?",
      "hi": "पुष्कर नवांश और पुष्कर भाग क्या होते हैं?",
      "hg": "Pushkara navamsa aur Pushkara bhaga kya hote hain?"},
     [G("kb_chart_planets_in_signs_dignity", r"Pushkara"), G("kb_chart_divisional_charts", r"Pushkara", 1)]),
    ("p-graha-yuddha", "dignity", "vedic",
     {"en": "What is planetary war (graha yuddha) between two planets?",
      "hi": "दो ग्रहों के बीच ग्रह युद्ध क्या होता है?",
      "hg": "Do planets ke beech graha yuddha kya hota hai?"},
     [G("kb_chart_planets_in_signs_dignity", r"Planetary war")]),
    ("p-chaturmas", "panchang", "vedic",
     {"en": "What is Chaturmas and which activities are avoided in it?",
      "hi": "चातुर्मास क्या है और इसमें कौन से कार्य वर्जित माने जाते हैं?",
      "hg": "Chaturmas kya hai aur isme kaun se kaam avoid kiye jate hain?"},
     [G("kb_panchang_muhurta_basics", r"Chaturmas")]),
    ("p-adhika-masa", "panchang", "vedic",
     {"en": "What is Adhika masa, the extra month?",
      "hi": "अधिक मास यानी अतिरिक्त महीना क्या होता है?",
      "hg": "Adhik maas yaani extra month kya hota hai?"},
     [G("kb_panchang_muhurta_basics", r"Adhika masa")]),
    ("p-rudraksha", "remedies", "vedic",
     {"en": "What is Rudraksha and how is it used traditionally?",
      "hi": "रुद्राक्ष क्या है और परंपरा में इसका उपयोग कैसे किया जाता है?",
      "hg": "Rudraksha kya hai aur traditionally ise kaise use kiya jata hai?"},
     [G("kb_remedy_traditional_remedies", r"Rudraksha")]),
    ("p-yantra", "remedies", "vedic",
     {"en": "What are yantras in planetary remedies?",
      "hi": "ग्रह उपायों में यंत्र क्या होते हैं?",
      "hg": "Planetary remedies mein yantra kya hote hain?"},
     [G("kb_remedy_traditional_remedies", r"Yantra")]),
    ("p-pradosha", "panchang", "vedic",
     {"en": "What is Pradosha and when is it observed?",
      "hi": "प्रदोष क्या है और यह कब मनाया जाता है?",
      "hg": "Pradosh kya hai aur ye kab manaya jata hai?"},
     [G("kb_panchang_eclipses_and_special_days", r"Pradosha")]),
    ("p-karana", "panchang", "vedic",
     {"en": "What is a karana in the panchang?",
      "hi": "पंचांग में करण क्या होता है?",
      "hg": "Panchang mein karan kya hota hai?"},
     [G("kb_panchang_five_limbs", r"Karana")]),
    ("p-hora", "panchang", "vedic",
     {"en": "How are planetary hours (hora) calculated through the day?",
      "hi": "दिनभर की ग्रह होरा की गणना कैसे की जाती है?",
      "hg": "Din bhar ki planetary hora ki calculation kaise hoti hai?"},
     [G("kb_panchang_daily_timings", r"Hora")]),
    ("p-vimshottari-order", "dashas", "vedic",
     {"en": "In what order do the Vimshottari dasha lords follow and for how many years?",
      "hi": "विंशोत्तरी दशा के स्वामी किस क्रम में आते हैं और कितने वर्षों के होते हैं?",
      "hg": "Vimshottari dasha ke lords kis order mein aate hain aur kitne saal ke hote hain?"},
     [G("kb_dasha_vimshottari_foundations", r"The order and years")]),
]

ORD = {1: "1st", 2: "2nd", 3: "3rd"}
ORDS = {i: ORD.get(i, f"{i}th") for i in range(1, 13)}
HI_ORD = {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पांचवें", 6: "छठे", 7: "सातवें", 8: "आठवें", 9: "नौवें", 10: "दसवें",
          11: "ग्यारहवें", 12: "बारहवें"}
LANGS = ["en", "hi", "hg"]
VEDIC_CHARTS = ["delhi_1994", "mumbai_1988", "chennai_1992_notime", "kolkata_1969", "bengaluru_2003", "london_1975",
                "newyork_2001", "sydney_1990"]


def chart_gap_queries(charts: dict) -> list[dict]:
    """Chart-derived queries from each real chart's own engine output."""
    out: list[dict] = []
    for ci, name in enumerate(VEDIC_CHARTS):
        c = charts[name]
        v = c["vedic"]
        approx = bool(c["metadata"].get("approximate_time"))

        def add(kind, lang, text, gold, topic):
            out.append({"id": f"{name}:{kind}:{lang}", "source": "chart", "split": "holdout3", "chart": name, "lang": lang,
                        "text": text, "topic": topic, "system": "vedic", "gold": gold})

        # a. current Mahadasha / Antardasha pair
        md, ad = v["dasha"]["maha_dasha"]["current"], v["dasha"]["antar_dasha"]["current"]
        lg = LANGS[ci % 3]
        txt = {"en": f"I am in {md} Mahadasha and {ad} Antardasha. What does this combination mean?",
               "hi": f"मेरी {md} महादशा में {ad} की अंतर्दशा चल रही है, इस संयोजन का क्या अर्थ है?",
               "hg": f"Meri {md} mahadasha mein {ad} ki antardasha chal rahi hai, iska kya matlab hai?"}[lg]
        add("dasha-pair", lg, txt, [G(AD, rf"{md} Mahadasha", c=rf"\*\*{md}-{ad}\*\*"), G(MD, rf"{md} Mahadasha", 1)], "dashas")
        # b. house lord placement (engine house_lords)
        if not approx:
            hl = next((x for x in v.get("house_lords", []) if x["house"] == 7), None)
            if hl:
                lg = LANGS[(ci + 1) % 3]
                n = hl["lord_in_house"]
                txt = {"en": f"My 7th lord {hl['lord']} is placed in the {ORDS[n]} house. What does that mean?",
                       "hi": f"मेरे सातवें भाव के स्वामी {hl['lord']} {HI_ORD[n]} भाव में हैं, इसका क्या अर्थ है?",
                       "hg": f"Mere 7th lord {hl['lord']} {ORDS[n]} house mein hain, iska kya matlab hai?"}[lg]
                add("seventh-lord", lg, txt, [G(HL, r"7th lord in each house")], "houses")
            # c. a planet in its house (Vedic whole-sign house from engine)
            sat = next((p for p in v["planets"] if p.get("english") == "Saturn" and p.get("house")), None)
            if sat:
                lg = LANGS[(ci + 2) % 3]
                h = int(sat["house"])
                txt = {"en": f"What does Saturn in the {ORDS[h]} house mean for me?",
                       "hi": f"शनि का {HI_ORD[h]} भाव में होना मेरे लिए क्या अर्थ रखता है?",
                       "hg": f"Saturn ka {ORDS[h]} house mein hona mere liye kya matlab rakhta hai?"}[lg]
                add("saturn-house", lg, txt, [G(PH, rf"Saturn in the {ORDS[h]} house")], "houses")
        # d. Sade Sati
        lg = LANGS[ci % 3]
        add("sade-sati", lg, {"en": "Is Sade Sati really bad, and how should I handle it?",
                              "hi": "क्या साढ़ेसाती सच में बुरी होती है और इसे कैसे संभालें?",
                              "hg": "Kya Sade Sati sach mein buri hoti hai aur ise kaise handle karein?"}[lg],
            [G(SS, None)], "sade_sati")
        # e. an engine-detected yoga
        yg = next((y["name"] for y in v.get("yogas", []) if y.get("present")), None)
        if yg:
            lg = LANGS[(ci + 1) % 3]
            add("yoga", lg, {"en": f"My chart has {yg}. What does it indicate?",
                             "hi": f"मेरी कुंडली में {yg} है, यह क्या संकेत देता है?",
                             "hg": f"Meri kundli mein {yg} hai, ye kya indicate karta hai?"}[lg],
                [G(YG, re_escape(yg))], "yogas")
    return out


def re_escape(s: str) -> str:
    import re

    return re.escape(s)


def gap_free_queries() -> list[dict]:
    out = []
    for split, intents in (("holdout3", GAP_INTENTS), ("holdout4", HOLDOUT4)):
      for iid, topic, system, texts, gold in intents:
        for lang in LANGS:
            out.append({"id": f"{iid}:{lang}", "source": "free", "split": split, "chart": None, "lang": lang,
                        "text": texts[lang], "topic": topic, "system": system, "gold": gold})
    return out


# Corpus growth: for these OLD intents the new files are now the exact home of the answer. Extra matchers are
# appended to `gold`; the original gold is kept as `gold_strict` so the old-set number stays comparable.
EXTRA_GOLD = {
    "dasha-vimshottari": [G("kb_dasha_vimshottari_foundations", r"The order and years|What the system is", 1)],
    "yogas-raja-dhana": [G(YG, r"Raja Yoga|Dhana Yoga", 2)],
    "sade-sati": [G(SS, r"What Sade Sati is|three phases", 2)],
    "remedies-saturn": [G("kb_remedy_traditional_remedies", r"Planet-by-planet|Mantra|Charity|Fasting", 2)],
    "compat-kundli-milan": [G(AK, r"Overview", 2), G(LC, r"कुंडली मिलान", 1)],
    "mangal-dosha": [G(DO, r"Manglik", 2), G(YG, r"Mangal Dosha", 1)],
    "jaimini-atmakaraka": [G("kb_chart_karakas_and_arudha", r"Jaimini chara", 2)],
    "navamsa-d9": [G("kb_chart_divisional_charts", r"D9 Navamsa", 2)],
    "h-dasha-results": [G("kb_dasha_vimshottari_foundations", r"Reading a dasha with chart context", 2)],
    "h-gem-jupiter": [G("kb_remedy_traditional_remedies", r"Gemstones", 2)],
    "g-karakamsha": [G("kb_chart_karakas_and_arudha", r"Karakamsa", 2)],
    "g-fasting": [G("kb_remedy_traditional_remedies", r"Fasting", 2)],
    "g-empty-8th": [G(PH, r"in the 8th house", 1)],
    "g-avasthas": [G("kb_chart_planets_in_signs_dignity", r"avasthas", 1)],
    "h-pancha-mahapurusha": [G(YG, r"Ruchaka|Bhadra|Hamsa|Malavya|Sasa", 2)],
}
EXTRA_CHART_GOLD = {   # chart-derived old kinds
    "dasha": lambda md: [G(MD, rf"{md} Mahadasha", 2), G(AD, rf"{md} Mahadasha", 1)],
    "saturn-house": lambda h: [G(PH, rf"Saturn in the {ORDS[h]} house", 2)],
}
