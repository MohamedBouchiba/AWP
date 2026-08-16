# Meldingen — oplevering

Alles uit *Change Requests Nacalculatie* staat live. Hieronder punt per punt wat
er nu in productie draait.

**In cijfers:** 189 dossiers gesynchroniseerd · 123 meldingen, waarvan 19 op
projectniveau · drempels instelbaar in Beheer · dempen verwijderd.

---

## 1. Meldingen per fase

| Gevraagd | Live |
|---|---|
| Drie drempels, elk **exact één keer** per fase per project | Eén melding per **overschreden drempel**. Een fase op 120% draagt er drie (80, 100, 115), een fase op 85% precies één. |
| 80% → "Fase X nadert het budget" | Zo geformuleerd. |
| 100% → "Fase X heeft het budget bereikt" | Zo geformuleerd. |
| 115% → "Fase X is X% over budget" | Zo geformuleerd, met het werkelijke percentage. |
| Zolang dezelfde drempel overschreden blijft: geen nieuwe melding of mail | Een synchronisatie met hetzelfde cijfer verandert niets — niet de melding, niet de datum, niet de mailstatus. |
| Pas bij de volgende drempel volgt een nieuwe melding | Ja. Zakt een fase terug, dan verdwijnen enkel de drempels die ze niet meer haalt. |

**Acceptatiecriteria**

- ✅ Eén melding en één mail per drempel per fase per project.
- ✅ Verdere urenregistratie binnen dezelfde drempelzone: geen herhaling.
- ✅ De melding bevat projectnummer, projectnaam, fase, percentage en
  verantwoordelijke — plus de onderliggende uren (zie punt 6).

De meldingen volgen de **gepresteerde uren tegenover de begrote uren**, dezelfde
maatstaf als de status van het dossier. De melding op het scherm kan dus nooit
iets anders zeggen dan het label in het overzicht.

Overheadfasen (administratie) en fasen zonder urenbudget geven geen melding —
dat volgt uit jullie eerdere vraag om administratie buiten de budgetstatus te
houden.

## 2. Meldingen op projectniveau

| Gevraagd | Live |
|---|---|
| Drie meldingen op het cumulatief verbruikte urenbudget | 80%, 90% en 100%, elk één keer. |
| Over **alle** fases | De noemer telt álle fases mee, ook die nog niet gestart zijn — anders kan je niet zeggen "80% verbruikt terwijl er nog fases moeten komen". Dit cijfer verschilt dus bewust van de status in het overzicht, die enkel de gestarte fases weegt. |
| Visueel onderscheiden van fasemeldingen | Eigen icoon 📊, een gekleurde rand, en het label "Project" naast de projectnaam. |

## 3. Drempels instelbaar in Beheer

| Gevraagd | Live |
|---|---|
| Fasedrempels = dezelfde instelbare waarden als de kleurcodering | Klopt: het zijn letterlijk dezelfde. Eén kaart "Drempels (% van de begrote uren)". Een wijziging herberekent nu meteen. |
| Projectdrempels bestaan nog niet, toe te voegen | Nieuwe kaart "Drempels op projectniveau", standaard 80 / 90 / 100, vrij aanpasbaar. |

## 4. Het meldingenscherm

| Gevraagd | Live |
|---|---|
| Dempen mag verwijderd worden | Volledig weg: knop, opslag en achterliggende code. |
| Standaard je eigen meldingen zien | Standaardweergave = de dossiers waarvan jij verantwoordelijke bent. |
| Afvinken wat behandeld is | Knop per melding. Ze verlaat je lijst en komt niet terug, ook niet na een synchronisatie. Via "Toon afgehandelde" vind je ze terug, met een knop om te heropenen. |
| Beheerder: tweede weergave met alle meldingen | Tabblad "Alle meldingen". |

De teller naast *Meldingen* in het menu telt voortaan de **openstaande**
meldingen in plaats van de ongelezen — dat is wat telt zodra je ze kan afvinken.

**Voorwaarde om de eigen lijst te laten werken:** de koppeling loopt via de
e-mailadressen per verantwoordelijke in Beheer. Vandaag heeft één van de zes
verantwoordelijken een adres, en er is één dashboardaccount. Zolang een account
aan geen enkele verantwoordelijke gekoppeld is, ziet die alle meldingen, met een
melding bovenaan die uitlegt waarom — beter dan een leeg scherm.

## 5. Mails

Elke melding vertrekt **exact één keer**, gebundeld per verantwoordelijke: één
bericht met alle nieuwe meldingen van die persoon, niet één mail per fase. De
functie staat nu in testmodus — de berichten worden opgesteld en gelogd, niet
verstuurd — tot we een verzendadres en de adressen per verantwoordelijke hebben.

## 6. Eén vaststelling die aandacht vraagt

Verschillende dossiers dragen **placeholderbudgetten van 1,0 uur** per fase. Op
A384 bijvoorbeeld staat 1,0u op zes fases en 2,0u op één, terwijl er 164,6 uur
op geboekt is. Dat geeft meldingen als "1828% van het urenbudget verbruikt".

De berekening klopt; het budget niet. Daarom staan de onderliggende uren nu naast
elk percentage — "164,6 / 9,0u" — zodat zo'n cijfer meteen leesbaar is als een
ontbrekend budget in plaats van een ontspoord dossier.

Van de 17 projectmeldingen ligt de mediaan op 133%, maar zes overschrijden 200%
om exact deze reden.

Dit raakt niet alleen de meldingen: sinds de status op uren draait, steunt ook
het label van het dossier op diezelfde budgetten. **De begrote uren per fase
invullen in Teamleader is op dit moment de meest waardevolle ingreep aan jullie
kant** — vóór het afsluiten van afgewerkte dossiers en het koppelen van de
facturen.
