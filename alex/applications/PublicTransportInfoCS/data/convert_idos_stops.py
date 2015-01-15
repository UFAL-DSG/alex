#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Convert stops gathered from the IDOS portal into structures accepted by the
PublicTransportInfoCS application.

Usage:

./convert_idos_stops.py cities.txt idos_stops.tsv stops.txt cites_stops.tsv idos_map.tsv

Input:
    cities.txt = list of all cities
    idos_stops.tsv = stops gathered from IDOS (format: "list_id<\\t>abbrev_stop")

List ID is the name of the city for city public transit, "vlak" for trains and "bus" for
buses.

Output:
    stops.txt = list of all stops (unabbreviated)
    cities_stops.tsv = city-to-stop mapping
    idos_map.tsv = mapping from (city, stop) pairs into (list_id, abbrev_stop) used by IDOS

"""

from __future__ import unicode_literals
import codecs
import sys
import re
from add_cities_to_stops import load_list, get_city_for_stop
from alex.utils.various import remove_dups_stable
from alex.components.nlg.tools.cs import word_for_number
if __name__ == '__main__':
    import autopath


# a regex to strip weird stop name suffixes (request stop etc.)
CLEAN_RULE = (r'(?: +[O#]|;( *([wvx§\(\)\{\}ABP#]|MHD|WC|CLO))*|[\(-] *HR\.TARIF\.ZÓNY.*)$', r'')

# regexes for abbreviation expansion (will be applied in this order)
ABBREV_RULES = [
    # spacing around punctuation
    (r'\.([^0-9 ])', r'. \1'),
    (r'([A-ZÁČĎĚÉÍŇÓŘŠŤŮÚŽa-záčďěéíňóřšťůúž])\.([0-9])', r'\1. \2'),
    (r',+', r','),
    (r',([^ ])', r', \1'),
    (r';([^ ])', r'; \1'),
    # expanding various abbreviations
    (r'n\. Vlt\.', r'nad Vltavou'),
    (r'n\. Orl\.', r'nad Orlicí'),
    (r'n\. Sáz\.', r'nad Sázavou'),
    (r'n\. Jiz\.', r'nad Jizerou'),
    (r'n\. Svit\.', r'nad Svitavou'),
    (r'n\. Osl\.', r'nad Oslavou'),
    (r'n\. L\.', r'nad Labem'),
    (r'n\. Doubr\.', r'nad Doubravou'),
    (r'n\. Dřev\.', r'nad Dřevnicí'),
    (r'n\. Pl\.', r'nad Ploučnicí'),
    (r'n\. Bystř\.', r'nad Bystřicí'),
    (r'n\. Met\.', r'nad Metují'),
    (r'n\. Bud\.', r'nad Budišovkou'),
    (r'n\. Pern\.', r'nad Pernštejnem'),
    (r'n\. Pernšt\.', r'nad Pernštejnem'),
    (r'p\. Host\.', r'pod Hostýnem'),
    (r'p\. Prad\.', r'pod Pradědem'),
    (r'n\. Radb\.', r'nad Radbuzou'),
    (r'p\. Bezd\.', r'pod Bezdězem'),
    (r'n\. Cidl\.', r'nad Cidlinou'),
    (r'n\. Mor\.', r'nad Moravou'),
    (r'n\. Luž\.', r'nad Lužnicí'),
    (r'n\. Ost\.', r'nad Ostravicí'),
    (r'n\. Ostr\.', r'nad Ostravicí'),
    (r'n\. Jev\.', r'nad Jevišovkou'),
    (r'n\. Jeviš\.', r'nad Jevišovkou'),
    (r'n\. Úhl\.', r'nad Úhlavou'),
    (r'n\. Rok\.', r'nad Rokytnou'),
    (r'n\. Des\.', r'nad Desnou'),
    (r'n\. Pop\.', r'nad Popelkou'),
    (r'n\. Č\. l\.', r'nad Černými lesy'),
    (r'Heřm\. Městce', r'Heřmanova Městce'),
    (r'Heř\. Městce', r'Heřmanova Městce'),
    (r'n\. Než\.', r'nad Nežárkou'),
    (r'Městec n\. Děd\.', r'Městec nad Dědinou'),
    (r'Klášter n\. Děd\.', r'Klášter nad Dědinou'),
    (r'Ronova n\. D\.', r'Ronova nad Dyjí'),
    (r'Ronova n\. D\.', r'Ronova nad Doubravou'),
    (r'v Orl\. h\.', r'v Orlických horách'),
    (r'n\. Zdob\.', r'nad Zdobnicí'),
    (r'n\. Kněž\.', r'nad Kněžnou'),
    (r'n\. Ondř\.', r'nad Ondřejnicí'),
    (r'n\. Blan\.', r'nad Blanicí'),
    (r'n\. Vol\.', r'nad Volyňkou'),
    (r'([^.]) n\. ', r'\1 nad '),
    (r'p\. Tř\.', r'pod Třemšínem'),
    (r'p\. Radh\.', r'pod Radhoštěm'),
    (r'v Podkr\.', r'v Podkrkonoší'),
    (r'p\. Sv\.', r'pod Svatým'),
    (r'p\. Lop\.', r'pod Lopeníkem'),
    (r'p\. Čerch\.', r'pod Čerchovem'),
    (r'p\. Koz\.', r'pod Kozákovem'),
    (r'p\. Sv\.', r'pod Svatým '),
    (r'p\. Tr\.', r'pod Troskami'),
    (r'p\. Land\.', r'pod Landštejnem'),
    (r'p\. Oreb\.', r'pod Orebem'),
    (r'p\. Ondřej\.', r'pod Ondřejníkem'),
    (r' p\. (?=[^ ])', r' pod '),
    (r' v Jiz\. h\.', r' v Jizerských horách'),
    (r'Vel\. Těšany', r'Velké Těšany'),
    (r'([^ ])-([^ ])', r'\1 - \2'),
    (r'St\. Bol\.', r'Stará Boleslav'),
    (r'Ml\. Boleslavi', r'Mladé Boleslavi'),
    (r'Pr\. Suchá', r'Prostřední Suchá'),
    (r'Anděl\. Hora', r'Andělská Hora'),
    (r'K\. Varů', r'Karlových Varů'),
    (r'u Bech\.', r'u Bechyně'),
    (r'Sv\. Kateřiny', r'Svaté Kateřiny'),
    (r'Sv\. Šebestiána', r'Svatého Šebestiána'),
    (r'([Ss])v\. Václava', r'\1vatého Václava'),
    (r'Sv\. Antonína', r'Svatého Antonína'),
    (r'Sv\. Kříže', r'Svatého Kříže'),
    (r'Sv\. Maří', r'Svaté Maří'),
    (r'([Ss])v\. Matouš(?=[;, ])', r'Svatý Matouš'),
    (r'Vrch\. Orlice', r'Vrchní Orlice'),
    (r'Svob\. Hory', r'Svobodné Hory'),
    (r'N\. Dědina', r'Nová Dědina'),
    (r'M\. Beranov', r'Malý Beranov'),
    (r'V\. Beranov', r'Velký Beranov'),
    (r'Mar\. Údolí', r'Mariánské Údolí'),
    (r'u Mor\. Budějovic', r'u Moravských Budějovic'),
    (r'St\. Paky', r'Staré Paky'),
    (r'Sl\. Předm\.', r'Slezské Předměstí'),
    (r'Jablonec nad J\.', r'Jablonec nad Jizerou'),
    (r'Jablonec nad N\.', r'Jablonec nad Nisou'),
    (r'u Č\. Bud\.', r'u Českých Budějovic'),
    (r'v Podj\.', r'v Podještědí'),
    (r'na Mor\.', r'na Moravě'),
    (r'Mar\. Lázní', r'Mariánských Lázní'),
    (r'Mn\. Hradiště', r'Mnichova Hradiště'),
    (r'u Vel\. Meziříčí', r'u Velkého Meziříčí'),
    (r'u Val\. Meziříčí', r'u Valašského Meziříčí'),
    (r'Rudoltic v Č\.', r'Rudoltic v Čechách'),
    (r'Kruš\. horách', r'Krušných horách'),
    (r'Orl\. horami', r'Orlickými horami'),
    (r'Horní Heřm\.', r'Horní Heřmanice'),
    (r'Orl\. horách', r'Orlických horách'),
    (r'Červ\. Voda', r'Červená Voda'),
    (r'Valš\. Důl', r'Valšův Důl'),
    (r'Břez\. Hory', r'Březové Hory'),
    (r'Smetan\. sady', r'Smetanovy sady'),
    (r'Mar\. Hory', r'Mariánské Hory'),
    (r'Hor\. Měcholupy', r'Horní Měcholupy'),
    (r'Roudnice nad Labem - Hrach\.', r'Roudnice nad Labem - Hracholusky'),
    (r'u Jabl\. n\. Nisou', r'u Jablonce nad Nisou'),
    (r'u Čes\. Lípy', r'u České Lípy'),
    (r'u Č\. Budějovic', r'u Českých Budějovic'),
    (r'u Čes\. Těšína', r'u Českého Těšína'),
    (r'u Vys\. Mýta', r'u Vysokého Mýta'),
    (r'Vys\. Chvojno', r'Vysoké Chvojno'),
    (r'u Uh\. Hrad\.', r'u Uherského Hradiště'),
    (r'u Kar\. Varů', r'u Karlových Varů'),
    (r'Zahr\. Město', r'Zahradní Město'),
    (r'Dl\. louka', r'Dlouhá louka'),
    (r'zám\. zahrada', r'zámecká zahrada'),
    (r' již\. z(ast)?\.', r' jižní zastávka'),
    (r' sev\. z(ast)?\.', r' severní zastávka'),
    (r' h(or)?\. z(ast)?\.', r' horní zastávka'),
    (r' d(ol)?\. z(ast)?\.', r' dolní zastávka'),
    (r' z(ast)?\.', r' zastávka'),
    (r'm(\.|ístní) n\.', r'místní nádraží'),
    (r' předm\.', r' předměstí'),
    (r' bažant\.', r' bažantnice'),
    (r' hl\. n(ádr\.|ádraží|\.)', r' hlavní nádraží'),
    (r' dol(\.|ní) n\.', r' dolní nádraží'),
    (r' horní n\.', r' horní nádraží'),
    (r' hor\.', r' horní'),
    (r'Hor\.', r'Horní'),
    (r' dol\.', r' dolní'),
    (r'Dol\.', r'Dolní'),
    (r' sev\. n\.', r' severní nádraží'),
    (r' k nádr\.', r' k nádraží'),
    (r' nad $', r' nádraží'),
    (r' m\. $', r' město'),
    (r' [kK]ult\. dům', r' kulturní dům'),
    (r' [kK]ult\. domu', r' kulturního domu'),
    (r' žel\. přejezdu', r' železničního přejezdu'),
    (r' žel\. přejezd(?=[;, ])', r' železniční přejezd '),
    (r' rozc\.([0-9])', r' rozcestí \1'),
    (r' ([Rr])ozc\.', r' \1ozcestí'),
    (r' aut\. st\.(?=[;, ])', [r' autobusové stanoviště', r' autobusová stanice',
                               r' autobusové nádraží']),
    (r' ([Aa])ut\. stanoviště ', r' \1utobusové stanoviště '),
    (r' k žel\. st\. ', r' k železniční stanici '),
    (r' žel\. st(\.|anice)', r' železniční stanice'),
    (r' žel\. zastávka', r' železniční zastávka'),
    (r' křiž\.', r' křižovatka'),
    (r' nám\.([0-9])', r' náměstí \1'),
    (r' ([nN])ám\.', r' \1áměstí'),
    (r'([ -])vrát\.', r'\1vrátnice'),
    (r' obch\. dům(?=[;, ])', r' obchodní dům'),
    (r' obch\. ([dD])omy', r' obchodní domy'),
    (r' obch\. stř\.', r' obchodní středisko'),
    (r' zdrav\. stř\.', [r' zdravotní středisko', r' zdravotnické středisko']),
    (r' čerp\. st\.', r' čerpací stanice'),
    (r' spín\. st\.', r' spínací stanice'),
    (r' pož\. zbroj\.', r' požární zbrojnice'),
    (r' has\. zbroj\.', r' hasičská zbrojnice'),
    (r' \([vV]\)álc\. pl\.', r' \1álcovny plechu'),
    (r' u aut\. nádr(\.|aží)', r' u autobusového nádraží'),
    (r' ([aA])ut\. nádr(\.|aží)', r' \1utobusové nádraží'),
    (r' nádr\.', r' nádraží'),
    (r' háj\.', r' hájovna'),
    (r' host\.', r' hostinec'),
    (r' nem\. areál', r' nemocniční areál'),
    (r' peč\. služby', r' pečovatelské služby'),
    (r' nem(oc)?\.', r' nemocnice'),
    (r' koup\.', r' koupaliště'),
    (r' žel\. mostu', r' železničního mostu'),
    (r' br\. pokladna', r' bratrská pokladna'),
    (r' zahr\. kolonie', r' zahrádkářská kolonie'),
    (r' rest\.', r' restaurace'),
    (r' sídl\.', r' sídliště'),
    (r' chat\. obl(\.|ast )', r' chatová oblast'),
    (r' odb\.', r' odbočka'),
    (r' ch\.', r' chata'),
    (r' ul\.', r' ulice'),
    (r' park\.', r' parkoviště'),
    (r' ŽD vrát\.', r' ŽD vrátnice'),
    (r' Kop\. myslivna', r' Kopce myslivna'),
    (r' keramické záv\.', r' keramické závody'),
    (r' stř\. ZD', r' středisko ZD'),
    (r' rekr\. stř\.', r' rekreační středisko'),
    (r' ([tT])ř\.', r' \1řída'),
    (r'(Branišovice.*)st\. silnice', r'\1státní silnice'),
    (r'Domin\. Paseky', r'Dominikální Paseky'),
    (r' SLEZSKÉ PŘ\. ', r' Slezské Předměstí '),
    (r'Mor\. (Chrastová|Ostrava)', r'Moravská \1'),
    (r'Sl\. Ostrava', r'Slezská Ostrava'),
    (r'Marián\. údolí', r'Mariánské údolí'),
    (r'\bobch\. ([dD]omy)', r'obchodní \1'),
    (r'St\. Oldřůvky', r'Staré Oldřůvky'),
    (r'Vel\. Albrechticím', r'Velkým Albrechticím'),
    (r'Červ\. Lhota', r'Červená Lhota'),
    (r'Sv\. Václav(?=[;, ])', r'Svatý Václav'),
    (r'\b([sS])v\. (Anny|Trojice)', r'\1vaté \2'),
    (r'\b([sS])v\. (Kateřina|Barbora)', r'\1vatá \2'),
    (r'\b([sS])v\. (J[aá]na|Mořice|Tomáše)', r'\1vatého \2'),
    (r'\b([sS])v\. J([áa])nem', r'\1vatým J\2nem'),
    (r'\b([sS])v\. (J[aá]n|Duch|Hubert|Tomáš)', r'\1vatý \2'),
    (r'u ryb\.', r'u rybníka'),
    (r' ryb\.', r' rybník'),
    (r' st\. hr\.', r' státní hranice'),
    (r' čist\. st\.', r' čisticí stanice'),
    (r' šlecht\. st\.', r' šlechtitelská stanice'),
    (r' nákup\. stř\.', r' nákupní středisko'),
    (r'Bělk. údolí rozcestí', r'Bělkovice údolí rozcestí'),
    (r' křiž\.', r' křižovatka'),
    (r'N\. Ves', r'Nová Ves'),
    (r'Albrechtice u Rým\.', r'Albrechtice u Rýmařova'),
    (r'Martinice v Krk\.', r'Martinice v Krkonoších'),
    (r'záv\. klub', r'závodní klub'),
    (r'starý záv\.', r'starý závod'),
    (r'čs\. kostela', r'československého kostela'),
    (r'hasič\. stanice', r'hasičská stanice'),
    (r'u transf\.', r'u transformátoru'),
    (r' transf\.', r' transformátor'),
    (r'Lhota u Chr\.', r'Lhota u Chroustovic'),
    (r' u N\. Města', r' u Nového Města'),
    (r' u Ml\. Vožice', r' u Mladé Vožice'),
    (r'N\. Herštejn', r'Nový Herštejn'),
    (r'Hluboká u Bor\.', r'Hluboká u Borovan'),
    (r'Vích\. Lhota', r'Víchovská Lhota'),
    (r'Přer\. stroj\.', r'Přerovské strojírny'),
    (r'prům\. oblast', r'průmyslová oblast'),
    (r' hl\. sil\.', r' hlavní silnice'),
    (r' hl\. (vstup|vchod|trať|vrátnice|brána|zastávka|silnice|přístav)', r' hlavní \1'),
    (r' st\. č\.', r' stanoviště číslo'),
    (r' sil\. č(\.|íslo)', r' silnice číslo'),
    (r' sil\.', r' silnice'),
    (r' č\. ([0-9])', r' číslo \1'),
    (r' ([pP])sych\. léčebna', r' \1sychiatrická léčebna'),
    (r' ([dD])om\. důch\.', r' \1omov důchodců'),
    (r' obch\. centrum', r' obchodní centrum'),
    (r' ([tT])ech\. služby', r' \1echnické služby'),
    (r' ([tT])ech\. škola', r' \1echnická škola'),
    (r' obch\. akademie', r' obchodní akademie'),
    (r' zem\. škola', r' zemědělská škola'),
    (r' zem\. podnik', r' zemědělský podnik'),
    (r' zem\. stavby', r' zemědělské stavby'),
    (r' zem\. dům', r' zemský dům'),
    (r' ([nN])ábř\.', r' \1ábřeží'),
    (r' pom\.', r' pomník'),
    (r'\bprov\.', r'provozovna'),
    (r' k sanat\.', r' k sanatoriu'),
    (r' sanat\.', r' sanatorium'),
    (r' děts\. psych\. nemocnice', r' dětská psychiatrická nemocnice'),
    (r' automobilové záv\.', r' automobilové závody'),
    (r' ([cC])hem\. závody', r' \1hemické závody'),
    (r' záv\.', r' závod'),
    (r' stroj\. závod', r' strojírenský závod'),
    (r' výzk\. ústav', r' výzkumný ústav'),
    (r' st\. statek', r' státní statek'),
    (r' prům\. zóna', r' průmyslová zóna'),
    (r' [Čč][Ss]\. (armády|brigády) ', r' Československé \1 '),
    (r' hot\.', r' hotel'),
    (r'Bílá hora', r'Bílá Hora'), # has different casing in different cities
    # titles
    (r'Dr\. Malíka', r'Doktora Malíka'),
    (r'Dr\. E(\.|dvarda) Beneše', r'Doktora Edvarda Beneše'),
    (r'Dr\. Oetker', r'Doktor Oetker'),
    (r'Dr\. Janského', r'Doktora Janského'),
    (r'Dr\. Malého', r'Doktora Malého'),
    (r'Dr\. Znojemského', r'Doktora Znojemského'),
    (r'Dr\. Horákové', r'Doktorky Horákové'),
    (r'Dr\. M(\.|ilady) Horákové', r'Doktorky Milady Horákové'),
    (r'M\. J(\.|ana) Husa', r'Mistra Jana Husa'),
    (r'([Kk])pt\. Jaroše', r'\1apitána Jaroše'),
    (r'([gG])en\. Pattona', r'\1enerála Pattona'),
    # names
    (r'A\. Dvořáka', r'Antonína Dvořáka'),
    (r'A\. Kratochvíla', r'Augusta Kratochvíla'),
    (r'Alb\. Krejčího', r'Alberta Krejčího'),
    (r'A\. Škváry', r'Antonína Škváry'),
    (r'B\. Martinů', r'Bohuslava Martinů'),
    (r'B\. Němcové', r'Boženy Němcové'),
    (r'C\. Boudy', r'Cyrila Boudy'),
    (r'E\. Krásnohorské', r'Elišky Krásnohorské'),
    # (r'I\. P\. Pavlova', r'Ivana Petroviče Pavlova'),
    # (r'J\. A\. Alise', r'Jana Antonína Alise'),
    # (r'J\. A\. Bati', r'Jana Antonína Bati'),
    (r'J\. Gagarina', r'Jurije Gagarina'),
    (r'J\. Hory', r'Josefa Hory'),
    (r'J\. Kociána', r'Jaroslava Kociána'),
    (r'J\. Kotase', r'Josefa Kotase'),
    (r'J\. Koziny', r'Jana Koziny'),
    (r'J\. Masaryka', r'Jana Masaryka'),
    (r'J\. Moláka', r'Josefa Moláka'),
    (r'J\. z Poděbrad', r'Jiřího z Poděbrad'),
    (r'J\. Skupy', r'Josefa Skupy'),
    (r'J\. Vrchlického', r'Jaroslava Vrchlického'),
    (r'J\. K\. Tyla', r'Josefa Kajetána Tyla'),
    (r'J\. Žižky', r'Jana Žižky'),
    (r'K\. Pobudy', r'Karla Pobudy'),
    (r'K\. H\. Máchy', r'Karla Hynka Máchy'),
    (r'L\. Zápotockého', r'Ladislava Zápotockého'),
    (r'L\. Vojtěcha', r'Ludvíka Vojtěcha'),
    (r'M\. Gorkého', r'Maxima Gorkého'),
    (r'M\. Hážové', r'Mileny Hážové'),
    (r'M\. Kopeckého', r'Matěje Kopeckého'),
    (r'M\. Majerové', r'Marie Majerové'),
    (r'P\. Holého', r'Prokopa Holého'),
    (r'P\. Hrubého', r'Petra Hrubého'),
    # (r'R\. A\. Dvorského', r'Rudolfa Antonína Dvorského')
    (r'R\. Filipa', r'Rudolfa Filipa'),
    # (r'S\. K\. Neumanna', r'Stanislava Kostky Neumanna')
    (r'S(v|vat)?\. Čecha', r'Svatopluka Čecha'),
    (r'T\. G\. M(?:asaryka|\.)', [r'T. G. Masaryka', r'Tomáše Garriguea Masaryka', r'T. G. M.']),
    (r'T\. Novákové', r'Terézy Novákové'),
    (r'V\. Lanny', r'Vojtěcha Lanny'),
    (r'V\. Nezvala', r'Vítězslava Nezvala'),
    # IDOS probably won't handle these
    (r'ObÚ', r'obecní úřad'),
    (r' dílny DP ', [r' dílny dopravního podniku ', r' dílny DP ']),
    (r' ZŠ(?=[,; ])', [r' ZŠ', r' základní škola']),
    (r' MŠ(?=[,; ])', [r' MŠ', r' mateřská škola']),
    (r' VŠ koleje', r' vysokoškolské koleje'),
    (r' VŠ(?=[,; ])', [r' VŠ', r' vysoká škola']),
    (r' SPŠ(?=[,; ])', [r' SPŠ', r' střední průmyslová škola']),
    (r' SOU(?=[,; ])', [r' SOU', r' střední odborné učiliště']),
    (r' 1\. [mM]áje', r' Prvního máje'),
    (r' 3\. ([Kk]větna) ', r' Třetího \1 '),
    (r' 4\. ([Kk]větna) ', r' Čtvrtého \1 '),
    (r' 5\. [Kk]větna', r' Pátého května'),
    (r' 6\. ([Kk]větna) ', r' Šestého \1 '),
    (r' 8\. ([Kk]větna) ', r' Osmého \1 '),
    (r' 9\. [Kk]větna', r' Devátého května'),
    (r' 17\. [Ll]istopadu', r' Sedmnáctého listopadu'),
    (r' 22\. [Dd]ubna', [r' Dvacátého druhého dubna', r' Dvaadvacátého dubna']),
    (r' 28\. ([Dd]ubna|[Řř]íjna) ', [r' Dvacátého osmého \1 ', r' Osmadvacátého \1 ']),
    (r' 29\. [Dd]ubna', [r' Dvacátého devátého dubna', r' Devětadvacátého dubna']),
    (r' 1\. (ZŠ|základní škola|náměstí|[čČ]eskoslovenské|BS|díl)', r' První \1'),
    (r' 2\. (ZŠ|základní škola|etapa) ', r' Druhá \1 '),
    (r' 3\. (ZŠ|základní škola|vrátnice)', r' Třetí \1'),
    (r' 4\. (ZŠ|základní škola|vrátnice)', r' Čtvrtá \1'),
    (r' 5\. ([Kk]věten) ', r' Pátý \1 '),
    (r' 6\. (ZŠ|základní škola)', r' Šestá \1'),
    (r' 7\. ([uU]lice)', r' Sedmá \1 '),
    (r' 8\. ([uU]lice|ZŠ|základní škola)', r' Osmá \1 '),
    (r' 14\. (ZŠ|základní škola)', r' Čtrnáctá \1'),
    (r' 18\. (ZŠ|základní škola)', r' Osmnáctá \1'),
    (r' Karla IV. ', r' Karla Čtvrtého '),
    (r' I\. (ZŠ|základní škola|brána|poliklinika|vrátnice) ', r' První \1 '),
    (r' I\.?(?=,| (?:$|-|náměstí|rozcestí|lázně))', [r' jedna', r' římská jedna']),
    (r' II\. (?:pásmo|p\.?) $', r' druhé pásmo '),
    (r' II\. (ZŠ|základní škola|brána|poliklinika|vrátnice) ', r' Druhá \1 '),
    (r' II\.?(?=[ ,])', [r' dvě', r' římská dvě']),
    (r' II\. (odboje) ', r' Druhého \1 '),
    (r' III\. (ZŠ|základní škola|brána|poliklinika|vrátnice) ', r' Třetí \1 '),
    (r' III\.?(?=[ ,])', [r' tři', r' římská tři']),
    (r' IV\.?(?=[ ,])', [r' čtyři', r' římská čtyři']),
    (r' V\.?(?=,| (?:$|-|náměstí|rozcestí|lázně))', [r' pět', r' římská pět']),
    (r' VI\.?(?=[ ,])', [r' šest', r' římská šest']),
    (r' VII\. (ZŠ|základní škola|brána|poliklinika|vrátnice) ', r' Sedmá \1 '),
    (r' VII\.?(?=[ ,])', [r' sedm', r' římská sedm']),
    (r' VIII\. (ZŠ|základní škola|brána|poliklinika|vrátnice) ', r' Osmá \1 '),
    (r' VIII\.?(?=[ ,])', [r' osm', r' římská osm']),
    (r' IX\.? $', [r' devět', r' římská devět']),
    (r' X\.?(?=[ ,])$', [r' deset', r' římská deset']),
    (r' XI\.?(?=[ ,])$', [r' jedenáct', r' římská jedenáct']),
    (r' XII\.?(?=[ ,])$', [r' dvanáct', r' římská dvanáct']),
    (r' XVII\.?(?=[ ,])$', [r' sedmnáct', r' římská sedmnáct']),
    (r' D2 ', r' D Dvě '),
    (r' D3 ', r' D Tři '),
    (r' D8 ', r' D Osm '),
    (r' G2 ', r' G Dvě '),
    (r' Metra 2,', r'Metra dvě,'),
    (r' 1\)', r' jedna)'),
    (r' 2\)', r' dvě)'),
    # TODO this creates ambiguity in some cases
    (r' ((?:rozcestí|křižovatka|odbočka)(?: .*)?) [0-9]+\.[0-9]', r' \1'),
    (r' [0-9]+\.[0-9] $', r' '),
    (r' \([A-Z]{2}\) $', r''), # strip county abbreviations
    # fixing spacing
    (r' ,', r','),
    (r'-([^ ])', r'- \1'),
    (r'([^ ])-', r'\1 -'),
    (r' +', r' '),
    # this is just to be sure: eliminate any stray ';' in data since it is the field separator
    (r';', r','),
]

# compile all regexes
CLEAN_RULE = (re.compile(CLEAN_RULE[0]), CLEAN_RULE[1])
ABBREV_RULES = [(re.compile(pattern), repl) for pattern, repl in ABBREV_RULES]

NUM_FINDER = re.compile(' [0-9]+ ')
NUM_TOKEN = re.compile('^[0-9]+$')


def expand_numbers(stop_name):
    """Spell out all numbers that appear as separate tokens in the word (separated by spaces)."""
    tokens = []
    for token in stop_name.split(' '):
        if NUM_TOKEN.match(token):
            try:
                num_word = word_for_number(int(token), 'F1')
                if token.startswith('0') and len(token) > 1:
                    tokens.append('nula')
                tokens.append(num_word)
            except:
                tokens.append(token)
        else:
            tokens.append(token)
    return ' '.join(tokens)


def expand_abbrevs(stop_name):
    """Apply all abreviation expansions to the given stop name, all resulting variant names,
    starting with the 'main' variant."""
    # add spaces to have simpler regexes
    variants = [' ' + stop_name + ' ']
    # process all regexes
    for regex, repls in ABBREV_RULES:
        try:
            # replacement variants
            if type(repls) == list:
                variants = list(remove_dups_stable([regex.sub(repl, var)
                                                    for repl in repls for var in variants]))
            # just a single replacement
            else:
                variants = [regex.sub(repls, var) for var in variants]
        except Exception as e:
            print >> sys.stderr, unicode(regex.pattern).encode('utf-8')
            raise e
    # keep the first variant as "canonical", to be used in SLU, DM, and NLG
    stop_name = variants[0]
    # process numbers in variants
    if NUM_FINDER.search(stop_name):
        variants = [expand_numbers(var) for var in variants]
    # remove the added spaces
    stop_name = stop_name.strip()
    variants = [var.strip() for var in variants]
    # return the result
    return stop_name, variants


UNIF_MAP = {}
UNIF_RULES = [(r'[\.,;\-–\(\)\[\]\{\}]', r' '),
              (r' +', r' ')]
UNIF_RULES = [(re.compile(pattern), repl) for pattern, repl in UNIF_RULES]


def unify_casing_and_punct(stop_name):
    """Unify casing of a stop name (if a second stop of the same name is encountered, let it
    have the same casing as the first one)."""
    # unify punctuation
    unif_name = stop_name
    for pattern, repl in UNIF_RULES:
        unif_name = pattern.sub(repl, unif_name)
    # unify casing, uppercase first character by default
    return UNIF_MAP.setdefault(unif_name.lower(), stop_name.upper()[0] + stop_name[1:])


# '>' = add to the end, '<' = add to the beginning
ADDITIONS = {'bus': ['>(bus)', '>autobus',
                     '<zastávka autobusu', '<stanice autobusu',
                     '>autobusová zastávka', '>autobusová stanice'],
             'vlak': ['>(vlak)', '>nádraží', '<nádraží', '>vlakové nádraží'],
             'MHD': ['>(MHD)', '<zastávka MHD']}


def unambig_variants(variants, idos_list):
    """Create 'unambiguos' variants for a stop name that equals a city name, depending
    on the type of the stop (bus, train or city public transit)."""
    # get the right additions list
    additions = ADDITIONS.get(idos_list, ADDITIONS['MHD'])
    if len(variants) > 1:  # this should never happen, but if it does, issue a warning
        print >> sys.stderr, ('Discarded variants of %s: %s' %
                              (variants[0], '; '.join(variants[1:]))).encode('utf-8')
    # create the final list of variants
    stop_name = variants[0]
    return [stop_name + ' ' + add[1:] if add[0] == '>' else add[1:] + ' ' + stop_name
            for add in additions]


def main():
    # initialize
    files = sys.argv[1:]
    if len(files) != 5:
        sys.exit(__doc__)
    file_in_cities, file_in_stops, file_out_stops, file_out_cs, file_out_map = files
    stderr = codecs.getwriter('UTF-8')(sys.stderr)

    # cities = set(load_list(file_in_cities, suppress_comments=True))
    cities = set(load_list(file_in_cities))
    in_stops = load_list(file_in_stops, cols=2)
    out_list = []
    exp_idos_lists = {}

    # process the input
    for idos_list, idos_stop in in_stops:
        # clean rubbish suffixes and expand all abbreviations,
        # resulting in one "canonical" name and all surface forms (not yet inflected)
        idos_stop = CLEAN_RULE[0].sub(CLEAN_RULE[1], idos_stop)
        stop, forms = expand_abbrevs(idos_stop)
        if idos_list not in exp_idos_lists:
            exp_idos_lists[idos_list] = expand_abbrevs(idos_list)[0]
        # get the correct city (provide default for city transit only)
        city = get_city_for_stop(cities, stop,
                                 exp_idos_lists[idos_list]
                                 if idos_list not in ['vlak', 'bus'] else None)
        # print any errors encountered
        if not city:
            print >> stderr, 'Could not resolve:', stop
            continue
        # make stop names that equal city names unambiguous
        if stop == city:
            forms = unambig_variants(forms, idos_list)
        # strip city name from stop name for city transit
        if stop.startswith(exp_idos_lists[idos_list] + ','):
            # we assume there are no variants within the city name itself
            stop = stop[len(exp_idos_lists[idos_list]):].strip(', ')
            forms = [var[len(exp_idos_lists[idos_list]):].strip(', ') for var in forms]
        # normalize casing and punctuation
        stop = unify_casing_and_punct(stop)
        forms = [unify_casing_and_punct(form) for form in forms]

        if stop in set(['Nová','Praga','Metra','Konečná','Nádraží',]):
            continue

        # add the result to the output list
        out_list.append((idos_list, idos_stop, city, stop, forms))

    # write list of (unique) stops, including all forms
    stops_map = {stop: forms for _, _, _, stop, forms in out_list}
    with codecs.open(file_out_stops, 'w', 'UTF-8') as fh_out:
        for stop in sorted(stops_map.keys()):
            print >> fh_out, stop + "\t" + '; '.join(stops_map[stop])
    # write city-stop mapping
    city_stop_map = {}
    for _, _, city, stop, _ in out_list:
        entry = city_stop_map.get(city, set())
        entry.add(stop)
        city_stop_map[city] = entry
    with codecs.open(file_out_cs, 'w', 'UTF-8') as fh_out:
        for city in sorted(city_stop_map.keys()):
            for stop in sorted(city_stop_map[city]):
                print >> fh_out, city + "\t" + stop
    # write normal-to-IDOS mapping
    norm_idos_map = {}
    for idos_list, idos_stop, city, stop, _ in out_list:
        norm_idos_map[(city, stop)] = (idos_list, idos_stop)
    with codecs.open(file_out_map, 'w', 'UTF-8') as fh_out:
        for (city, stop), (idos_list, idos_stop) in sorted(norm_idos_map.iteritems()):
            print >> fh_out, "\t".join((city, stop, idos_list, idos_stop))

if __name__ == '__main__':
    main()
