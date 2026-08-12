# Antwoord op de terugkoppeling nacalculatie

Dag,

Bedankt voor de heel concrete terugkoppeling. Alles wat jullie opsommen is
verwerkt. Ik overloop het punt per punt, en begin met A346 — want daar zat het
belangrijkste inzicht, en het antwoord is niet wat we allebei vermoedden.

---

## Eerst: waarom A346 "over budget" stond

Ik heb de ruwe cijfers van A346 rechtstreeks uit jullie Teamleader gehaald.

| Fase | budget € | "verbruikt" € | oud % | kostprijs € | nieuw % | uren | begroot |
|---|---|---|---|---|---|---|---|
| 1. ADMINISTRATIE | 249,90 | 120,00 | 48,0 | 100,00 | 40,0 | 1,3 | 2,9 |
| 2. SCHETSONTWERP | 5 124,65 | 2 401,25 | 46,9 | 1 412,50 | 27,6 | 28,3 | 60,3 |
| **3. VOORONTWERP** | 10 245,90 | 13 717,42 | **133,9** | 8 994,73 | **87,8** | 158,9 | 120,5 |
| 4. BOUWAANVRAAG | 15 620,45 | 10 750,25 | 68,8 | 5 876,25 | 37,6 | 126,4 | 183,8 |
| **5. UITVOERINGSDOSSIER** | 9 372,10 | 23 485,21 | **250,6** | 14 235,27 | **151,9** | 272,4 | 110,3 |
| 6. COMPLETE WERFOPVOLGING | 9 372,10 | 6 620,35 | 70,6 | 5 810,71 | 62,0 | 77,5 | 110,3 |
| 7. NAZORG | 6 247,50 | 0 | 0 | — | — | 0 | 73,5 |
| 8. MEERWERKEN | 0 | 1 380,68 | — | 1 211,58 | — | 16,2 | 1,0 |
| 9. BOUWCOÖRDINATIE | 6 247,50 | 345,00 | 5,5 | 287,50 | 4,6 | 3,8 | 73,5 |

**1. Nee, "gefactureerd" is niet de trigger.** Dat was onze eerste gedachte, maar
het klopt niet. Het veld dat de status bepaalde is Teamleader's *verbruikt
budget*. Deel je dat door de gepresteerde uren van elke fase, dan kom je telkens
uit op **85 à 90 €/uur** — met andere woorden: Teamleader waardeert jullie uren
aan het **verkooptarief**, niet aan wat ze jullie kosten. Facturatie speelt er
geen enkele rol in. Ter bevestiging: op alle negen fases van A346 is het veld
`amount_billed` leeg. Facturen die buiten Teamleader vertrokken zijn, kunnen
deze status dus onmogelijk beïnvloed hebben.

**2. Het echte probleem met "uren onder budget".** 684,8 gepresteerde uren op
736,1 begrote uren = 93 %, dus onder budget. Maar in die 736,1 uur zitten NAZORG
(73,5 u) en BOUWCOÖRDINATIE (73,5 u) — **twee fases waar nog geen uur op geboekt
is**. Reken je enkel op de fases die effectief gestart zijn, dan wordt het
668,5 u op 661,6 u, oftewel **101 %**. Het overzicht had dus gelijk; de urenbalk
gaf een te rooskleurig beeld. Dat is nu rechtgezet.

**3. Wat we voortaan vergelijken.** Zoals jullie zelf voorstelden bij de analyse:
per fase vergelijken we nu **kostprijs bureau tegenover het geofferteerde
budget**. Dat is trouwens exact de berekening die Teamleader zelf gebruikt voor
zijn eigen margeveld. Voor A346 betekent dat: VOORONTWERP zakt van 133,9 % naar
87,8 % (dus van "fors over" naar "dreigt over"), en UITVOERINGSDOSSIER van
250,6 % naar 151,9 %. **Het dossier blijft over budget** — de overschrijding is
reëel, ze werd alleen overdreven voorgesteld. We poetsen niets weg.

De oude berekening blijft beschikbaar via één instelling in Beheer, mocht je ze
willen vergelijken.

---

## Projectoverzicht

**Selectie laatste maand / 3 maanden / jaar / alles** — toegevoegd bovenaan het
overzicht. Belangrijk: ook de vier cijfers bovenaan (lopende projecten, over
budget, dreigt over, totale marge) volgen die selectie. Anders lees je totalen
van dossiers die niet in beeld staan.

**Selectie op verantwoordelijke** — toegevoegd, naast de periodekeuze. Combineert
met alle bestaande filters.

**Administratie telt niet meer mee** — precies zoals jullie schrijven: op die
fase wordt amper iets geregistreerd, en met een budget van 249,90 € volstond één
uur om ze rood te maken en het hele dossier mee te trekken. Administratie blijft
gewoon zichtbaar, met haar cijfers, maar bepaalt de status niet meer en genereert
ook geen melding meer. In Beheer kunnen jullie zelf aanvinken welke fases als
overhead gelden.

**Werfbezoeken en besprekingen** — staan nu bovenaan de detailfiche, naast de
uren, in plaats van helemaal onderaan. Geen scrollwerk meer.

**Facturen buiten Teamleader** — een beheerder kan per dossier het bedrag invullen
dat buiten Teamleader gefactureerd werd. De marge en alle grafieken rekenen er
onmiddellijk mee. Die waarde wordt nooit overschreven door een synchronisatie.

**Mails bij "dreigt over" en "over budget"** — gebouwd, met jullie
spam-bezorgdheid als uitgangspunt. Drie beveiligingen:

1. één **samenvattende mail per verantwoordelijke**, niet één per fase;
2. **hoogstens één keer per dag** — een tijdregistratie kan nooit een mail
   uitlokken;
3. een knop **"Dempen"** per dossier op de meldingenpagina: na een budgetanalyse
   zet je de herinneringen 14 dagen stil. De melding zelf blijft gewoon staan.

Wat we nog van jullie nodig hebben: een SMTP-adres om vanaf te verzenden, en per
verantwoordelijke een e-mailadres. Teamleader koppelt namelijk geen adres aan het
veld "1. Verantw." — dat is vrije tekst. Die lijst vul je in Beheer in. Tot dat
gebeurd is staat de functie in testmodus: de mails worden wel opgesteld maar niet
verzonden, zodat we samen kunnen nakijken wie wat zou krijgen.

---

## Analyse

**Fasenamen samenvoegen** — "Schetsontwerp/haalbaarheid" en "Schetsontwerp"
tellen nu als dezelfde fase, net als "Aanbestedingsdossier" en "Aanbesteding".
Hoofdletters en het nummer vooraan spelen geen rol meer (vroeger waren
"Voorontwerp" en "VOORONTWERP" twee aparte balken). Er is ook het knopje dat
jullie vroegen: **"Optimaliseer fasenamen"** stelt automatisch samenvoegingen én
een volgorde voor op basis van wat er vandaag in Teamleader staat. Je kan alles
achteraf nog aanpassen. **Teamleader zelf hoeft hiervoor niet aangepast te
worden.**

**Chronologische volgorde** — alle grafieken per fase staan nu in de volgorde van
jullie offerte in plaats van gerangschikt op percentage. Ze lijnen bovendien op
elkaar uit, zodat je ze naast elkaar kan lezen.

**Afgeronde dossiers** — hier hebben we een vaststelling die verder gaat dan de
tool. **Alle 187 projecten staan in Teamleader op "open".** Er is er geen enkel
afgesloten; ik heb dat expliciet nagekeken met de filter op afgesloten dossiers,
die nul resultaten geeft. Het statusveld bevat dus geen bruikbare informatie.

Als tussenoplossing beschouwt het dashboard een dossier als **afgerond wanneer er
3 maanden lang geen uur meer op geboekt is** (die termijn is instelbaar), met per
dossier een handmatige correctie als de automatische regel ernaast zit. Je kan nu
filteren op "enkel lopende" of "enkel afgeronde", zowel in de analyse als in de
Excel-export.

De propere oplossing ligt bij jullie: **sluit afgewerkte dossiers af in
Teamleader**. Zodra dat gebeurt neemt het dashboard die status automatisch over,
zonder aanpassing van de tool.

**"Analyse 2" — geofferteerd vs kostprijs** — precies zoals jullie voorstelden,
als aparte pagina naast de bestaande analyse, met vijf grafieken en **zonder één
enkel facturatiecijfer**:

1. kostprijs vs geofferteerd budget per fase
2. gepresteerde vs begrote uren per fase
3. marge per fase (geofferteerd − kostprijs)
4. rendabiliteit per categorie (offerte − kost)
5. rendabiliteit per contracttype (offerte − kost)

Jullie vroegen mijn mening over die opzet. **Ik denk dat jullie gelijk hebben, en
dat Analyse 2 voorlopig de betrouwbaarste van de twee is.** De reden is concreet:
op A346 is de offerte ingevuld (63 860,78 €) terwijl het gefactureerde bedrag per
fase overal leeg is. De grafieken op basis van facturatie hebben op vandaag dus
weinig te tonen. Analyse 2 draait volledig op cijfers die wél ingevuld zijn.

Ik heb de oude analysepagina bewust laten staan in plaats van ze te vervangen:
zodra alles via Teamleader gefactureerd wordt, wordt die de interessantste van de
twee, en dan kan Analyse 2 in één handeling verdwijnen. De filters, de export en
de berekeningen zijn gedeeld, dus het is geen dubbel onderhoud.

---

## Wat helpt aan jullie kant

Jullie schreven het zelf al — Teamleader op punt zetten. Concreet, in volgorde
van impact:

1. **Sluit afgewerkte dossiers af.** Dan wordt "afgerond" exact in plaats van
   afgeleid, en worden de analyses op afgewerkte dossiers pas echt betrouwbaar.
2. **Koppel de facturen aan de projecten.** Dat is de enige weg naar een correcte
   marge en naar de facturatiegrafieken. Zolang dat niet gebeurt, is Analyse 2
   het juiste instrument.
3. **Gebruik één vaste set fasenamen** bij het aanmaken van nieuwe projecten. De
   samenvoegingen die we nu instelden vangen het verleden op; ze zijn niet nodig
   voor de toekomst.
4. **Vul een tijdsbudget in per fase.** Voor een aantal fases ontbreekt dat, en
   dan valt de urenvergelijking terug op de uren uit de offerte.

Laat gerust weten wat jullie ervan vinden, en of jullie de mails willen
activeren — dan bezorgen jullie mij de adressen per verantwoordelijke.

Met vriendelijke groeten
