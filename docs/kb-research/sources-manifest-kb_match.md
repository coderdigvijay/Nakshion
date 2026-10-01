# Sources manifest, prefix kb_match_ (Vedic marriage and compatibility)

Date: 2026-10-01. No source files were saved to `backend/knowledge_sources/` by this task. All material was read in place through the WebFetch / WebSearch tools and summarised in original words. Table values (numbers) are facts and are reproduced with attribution; no prose passages were copied.

| Item | Author / publisher | URL | Licence / PD basis | Used for |
|---|---|---|---|---|
| Asta Koota pages (Varna, Vashya, Dina, Yoni, Gana, Rasi, Nadi, Rajju) | Saravali / Maitreya 8 documentation | https://saravali.github.io/astrology/astakoota.html and koota_*.html | CC BY-SA 4.0 (per engine docstring) | Tables, rules, caveats |
| Brihat Parashara Hora Shastra English edition (169 pages, Santhanam additions) | Parashara; edition by R. Santhanam / uploader | http://vedic-astro.s3.amazonaws.com/books/bhrihat_parasara_hora_shastra.pdf | Text of Parashara is classical, but this English edition is a modern translation whose copyright status is unclear. Read once through the fetch tool; NOT stored in the project; quoted only in paraphrase | Verification of Mars/Kuja verses (female horoscopy chapter, v.46 to 49) and Kalatra Bhava verses (7th house, timing) |
| Mangal Dosha cancellation pages | Jagannath Hora; Ashish Desai (jyotish-research.com) | https://jagannathhora.com/mangal-dosha-cancellation-rules/ ; https://www.jyotish-research.com/mangal-dosh-cancellation-rules/ | Web pages, read only | Cancellation lists, Jataka Chandrika table |
| Bhakoot / Nadi / Gana guides | Jagannath Hora; Hora Sarvam blog | https://jagannathhora.com/bhakoot-dosha-complete-guide/ ; /nadi-dosha-complete-guide/ ; /gana-koot-deva-manushya-rakshasa/ ; https://horasarvam.blogspot.com/2026/09/exceptions-to-gana-koota-dosha-and.html | Web pages, read only | Dosha and cancellation notes |
| Yoni / Vashya / Gana / Varna tables on portals | AstroSaxena, FreeHoroscopesOnline, AAPS, mohitmrinal.com, Steve Hora, AnytimeAstro, Sahita Vivaha, Muhurat Choghadiya | see ashtakoota-verification.md | Web pages, read only | Cross-check of engine tables |
| Compatibility essays | Roeland de Looff (dirah.org); BAVA | https://www.dirah.org/compatib.htm ; https://www.bava.org/articles/relationship-compatibility-and-astrological-counselling/ | Web pages, read only | Beyond-36 and counselling framing |
| Navamsa, Upapada, Tarabala, 10 Porutham pages | Jagannath Hora; shrifreedom.org; indianastrologysoftware.com; vijayalur.com; others | cited in front-matter of the kb_match files | Web pages, read only | Beyond-36 and relationship-type notes |
| Wikipedia, Astrological compatibility; Manglik | Wikipedia contributors | https://en.wikipedia.org/wiki/Astrological_compatibility ; https://en.wikipedia.org/wiki/Manglik | CC BY-SA | Orientation only |

## Download attempts

- GitHub projects with open Ashtakoota code (Shevadesuyash/Kundali, MIT; vrushabhabib/jyotish; Shubhamnnp/ai-jyotish-app) were identified as possible table cross-checks. A request to fetch one raw file with curl was declined by the environment's permission classifier (untrusted code integration) and was not retried or worked around. Those repositories were therefore not used.
- Muhurta Chintamani scans on archive.org (Sanskrit/Hindi, several marked CC0) were located (e.g. https://archive.org/details/muhurta-chintamani-hindi) but not downloaded: the Vivaha prakarana text is in Sanskrit/Hindi and the task did not need the raw scan. Recommended follow-up if a direct classical check of the koota tables is wanted.
- Prokerala and Drik Panchang pages published no extractable koota tables, so provider conventions remain unverified.
