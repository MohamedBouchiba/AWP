# Meldingen — delivered

Everything in *Change Requests Nacalculatie* is live.
189 projects synced · 123 alerts, 19 of them project-level.

| Request | Live |
|---|---|
| Three phase thresholds, each firing exactly once | One alert per threshold crossed. A phase at 120% carries three, at 85% one. |
| 80% → "Fase X nadert het budget" | Yes |
| 100% → "Fase X heeft het budget bereikt" | Yes |
| 115% → "Fase X is X% over budget" | Yes |
| No repeat while the same threshold holds | A sync with the same figure changes nothing |
| Next threshold → new alert | Yes. Falling back drops only the thresholds no longer crossed |
| Alert shows project no., name, phase, %, owner | Yes, plus the underlying hours |
| Project alerts at 80 / 90 / 100% of cumulative hours | Yes, each once. Denominator = **all** phases, including those not started |
| Project alerts visually distinct | 📊 icon, coloured edge, "Project" tag |
| Phase thresholds = the configurable colour thresholds | The same ones. Editing them now recalculates immediately |
| Project thresholds configurable | New card in Beheer, default 80 / 90 / 100 |
| Remove "dempen" | Removed entirely |
| Default view = my projects | Yes |
| Tick off what is handled | Per alert; never returns. "Toon afgehandelde" to retrieve, with reopen |
| Admin view of all alerts | "Alle meldingen" tab |
| One alert = one mail | Once ever, grouped per owner. In test mode until we have SMTP + addresses |

**Notes**

1. Alerts follow hours worked vs hours budgeted — the same measure as the project status, so the two can never disagree. Overhead phases and phases without an hours budget raise nothing.
2. The project figure counts all phases, so it differs from the status badge, which weighs only started phases. That is deliberate: "80% used while phases are still to come" cannot be said otherwise.
3. The personal view needs one account per owner and an address filled in per owner in Beheer. Today: one account, one address out of six. Unlinked accounts see everything, with a banner explaining why.

**One thing to fix on your side.** Several projects carry placeholder hour budgets of 1.0u — A384 has 164.6 hours booked against 9.0u budgeted, hence "1828% of its hours budget". The maths is right, the budget is not; the raw hours now sit next to every percentage so this reads as a missing budget. Six of the 17 project alerts exceed 200% for this reason. Since the status also runs on these budgets now, filling in the budgeted hours per phase in Teamleader is the most valuable step available to you.
