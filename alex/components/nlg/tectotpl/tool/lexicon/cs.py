#!/usr/bin/env python
# coding=utf-8
#
# Czech lexicon related functions
#
from __future__ import unicode_literals

import re
import codecs
from treex.core.resource import get_data

NUMBER_FOR_NUMERAL = {
        'nula': 0, 'jedna': 1, 'jeden': 1, 'dva': 2, 'tři': 3, 'čtyři': 4,
        'pět': 5, 'šest': 6, 'sedm': 7, 'osm': 8, 'devět': 9, 'deset': 10,
        'jedenáct': 11, 'dvanáct': 12, 'třináct': 13, 'čtrnáct': 14,
        'patnáct': 15, 'šestnáct': 16, 'sedmnáct': 17, 'osmnáct': 18,
        'devatenáct': 19, 'dvacet': 20, 'třicet': 30, 'čtyřicet': 40,
        'padesát': 50, 'šedesát': 60, 'sedmdesát': 70, 'osmdesát': 80,
        'devadesát': 90, 'sto': 100, 'tisíc': 1000, 'milión': 1000000,
        'milion': 1000000, 'miliarda': 1000000000,

        # fractions
        'půl': 1.0 / 2, 'polovina': 1.0 / 2, 'třetina': 1.0 / 3,
        'čtvrt': 1.0 / 4, 'čtvrtina': 1.0 / 4, 'pětina': 1.0 / 5,
        'šestina': 1.0 / 6, 'sedmina': 1.0 / 7, 'osmina': 1.0 / 8,
        'devítina': 1.0 / 9, 'desetina': 1.0 / 10, 'jedenáctina': 1.0 / 11,
        'dvanáctina': 1.0 / 12, 'třináctina': 1.0 / 13, 'čtrnáctina': 1.0 / 14,
        'patnáctina': 1.0 / 15, 'šestnáctina': 1.0 / 16,
        'sedmnáctina': 1.0 / 17, 'osmnáctina': 1.0 / 18,
        'devatenáctina': 1.0 / 19, 'dvacetina': 1.0 / 20,
        'třicetina': 1.0 / 30, 'čtyřicetina': 1.0 / 40, 'padesátina': 1.0 / 50,
        'šedesátina': 1.0 / 60, 'sedmdesátina': 1.0 / 70,
        'osmdesátina': 1.0 / 80, 'devadesátina': 1.0 / 90,
        'setina': 1.0 / 100, 'tisícina': 1.0 / 1000,
        'milióntina': 1.0 / 1000000, 'miliontina': 1.0 / 1000000,

        # other
        'tucet': 12, 'kopa': 60, 'veletucet': 144,
        }

INDEFINITE_NUMERALS = r'^((ne|pře)?mnoho|(ně|bůhví|kdoví|nevím)?kolik' + \
                      r'|tolik|méně|míň|více?|moc|málo|hodně)$'

SYNTH_FUTURE = r'^(běžet|být|hrnout|jet|jít|letět|lézt|nést|růst|téci|vézt)$'

# endings of by/aby/kdyby for different number and person
CONDITIONAL_INFLECT = {('S', '1'): 'ch',
                       ('S', '2'): 's',
                       ('P', '1'): 'chom',
                       ('P', '2'): 'ste'}

# list of verbs that use expletives in 'že'-clauses
EXPLETIVE_VERBS = {'upozorňovat': 'na_to',
                   'zdůvodňovat': 'tím',
                   'uvažovat': 'o_tom',
                   'pochybovat': 'o_tom',
                   'poukazovat': 'na_to',
                   'spočívat': 'v_tom',
                   'nasvědčovat': 'tomu',
                   'vést': 'k_tomu',
                   'argumentovat': 'tím',
                   'souhlasit': 's_tím',
                   'rozhodnout': 'o_tom',
                   'mluvit': 'o_tom',
                   'shodnout_se': 'na_tom',
                   'zdůvodnit': 'tím',
                   'dojít': 'k_tomu',
                   #    'věřit': 'tomu',
                   #    'tajit': 'tím',
                   'přesvědčit': 'o_tom',
                   'přesvědčit_se': 'o_tom',
                   'vycházet': 'z_toho',
                   'trvat': 'na_tom',
                   'počítat': 's_tím',
                   'shodovat_se': 'v_tom',
                   'dopustit_se': 'tím',
                    #    'jít': 'o_to',
                    'hovořit': 'o_tom',
                    #    'moci': 'to',
                    'svědčit': 'o_tom'}

COORD_CONJS = {
        'a': 'N', 'ale': 'Y', 'ani': 'Y', 'anebo': 'N', 'nebo': 'N',
        'buď': 'N', 'avšak': 'Y', 'však': 'Y', 'dokonce': 'Y',
        'jenže': 'Y', 'či': 'N', 'proto': 'Y', 'neboť': 'Y',
        'totiž': 'Y', 'vždyť': 'Y', 'sice': 'N', 'tudíž': 'Y'
        }

NAMED_ENTITY_LABELS = {
        'agentura': 'I', 'automobil': 'I', 'bar': 'I', 'brožura': 'I',
        'cup': 'I', 'Cup': 'I', 'časopis': 'I', 'dílo': 'I', 'divize': 'I',
        'dům': 'I', 'film': 'I', 'firma': 'I', 'fond': 'I', 'fotka': 'I',
        'foto': 'I', 'fotografie': 'I', 'hit': 'I', 'informace': 'I',
        'kancelář': 'I', 'kauza': 'I', 'klub': 'I', 'kniha': 'I',
        'konference': 'I', 'kraj': 'I', 'lázně': 'I', 'model': 'I',
        'motel': 'I', 'motocykl': 'I', 'nakladatelství': 'I', 'noviny': 'I',
        'obrázek': 'I', 'oddělení': 'I', 'okres': 'I', 'palác': 'I',
        'penzión': 'I', 'píseň': 'I', 'písnička': 'I', 'počítač': 'I',
        'podnik': 'I', 'rádio': 'I', 'rotačka': 'I', 'rubrika': 'I',
        'řada': 'I', 'seriál': 'I', 'série': 'I', 'skladba': 'I',
        'skupina': 'I', 'snímek': 'I', 'software': 'I', 'soutěž': 'I',
        'spis': 'I', 'společnost': 'I', 'stadion': 'I', 'stanice': 'I',
        'symfonie': 'I', 'sympózium': 'I', 'telenovela': 'I', 'televize': 'I',
        'třída': 'I', 'úřad': 'I', 'ústav': 'I', 'vůz': 'I', 'výstava': 'I',
        'výstaviště': 'I', 'veletrh': 'I', 'vydavatelství': 'I',
        'zařízení': 'I', 'závod': 'I', 'hora': 'C', 'hrad': 'C', 'hrádek': 'C',
        'kopec': 'C', 'legenda': 'C', 'městečko': 'C', 'město': 'C',
        'metropole': 'C', 'obec': 'C', 'osobnost': 'C', 'řeka': 'C',
        'ves': 'C', 'vesnice': 'C', 'vesnička': 'C', 'víska': 'C'
        }

PERSONAL_ROLES = set([
        'abbé', 'absolvent', 'absolventka', 'adresa', 'advokát',
        'advokátka', 'agent', 'agentura', 'akademik', 'aktivista',
        'amatér', 'analytička', 'analytik', 'anděl', 'archeolog',
        'architekt', 'arcibiskup', 'asistence', 'asistent',
        'asistentka', 'astronom', 'atlet', 'auditor', 'automechanik',
        'autor', 'autorka', 'baba', 'babička', 'banjista', 'banka',
        'bankéř', 'baron', 'barytonista', 'basista', 'basketbalista',
        'baskytarista', 'básník', 'básnířka', 'beran', 'běžec',
        'bibliofil', 'biochemik', 'biolog', 'biskup', 'blokařka', 'bohemista',
        'bojovník', 'botanik', 'boxer', 'brácha', 'branka', 'brankář',
        'bratr', 'bratranec', 'bratříček', 'bubeník', 'budovatel',
        'car', 'čaroděj', 'cellista', 'černoch', 'cestovatel', 'chargé',
        'chemik', 'chirurg', 'chirurgie', 'chlap', 'chlapec',
        'choreograf', 'choť', 'chudák', 'činovník', 'císař', 'číšník',
        'cizinec', 'člen', 'členka', 'člověk', 'čtenář', 'čtyřhra',
        'cvičitelka', 'cyklista', 'dáma', 'dcera', 'dealer', 'dědeček',
        'dědic', 'dědička', 'dějepisec', 'děkan', 'delegát', 'dělník',
        'desetibojař', 'diplomat', 'dirigent', 'divadelník', 'divák',
        'dívka', 'dobrodruh', 'docent', 'dodavatel', 'dohoda', 'doktor',
        'doktorka', 'dopisovatel', 'dozorce', 'dramatička', 'dramatik',
        'dramaturg', 'dramaturgyně', 'držitel', 'držitelka',
        'důchodce', 'důchodkyně', 'důstojník', 'dvojice', 'edice', 'editor',
        'ekolog', 'ekonom', 'ekonomka', 'elektrotechnik', 'emigrant'
        'epidemiolog', 'estetik', 'etnograf', 'etnolog', 'exmanželka',
        'exministr', 'expert', 'expozice', 'expremiér', 'farář', 'farářka',
        'farmář', 'favorit', 'filolog', 'filozof', 'finalista',
        'finalistka', 'flétnista', 'fořt', 'fotbalista', 'fotograf',
        'fotografka', 'frontman', 'funkcionář', 'fyzik', 'garant',
        'generál', 'generálmajor', 'génius', 'geograf', 'geolog',
        'gólman', 'grafik', 'guvernér', 'gynekolog', 'harfenistka', 'herec',
        'historička', 'historik', 'hlasatel', 'hlava', 'hoch',
        'hokejista', 'horník', 'horolezec', 'hospodář', 'hospodyně', 'host',
        'hostinský', 'houslista', 'houslistka', 'hraběnka', 'hráč',
        'hráčka', 'hrdina', 'hrdinka', 'hudebník', 'hvězda', 'hygienik',
        'idol', 'ikona', 'ilustrátor', 'imitátor', 'iniciátor', 'inspektor',
        'instalatér', 'internista', 'investor', 'inženýr', 'jednatel',
        'jednatelka', 'jezdec', 'jinoch', 'kacíř', 'kadeřnice', 'kamarád',
        'kamelot', 'kameník', 'kamera', 'kameraman', 'kancelář',
        'kancléř', 'kandidát', 'kandidátka', 'kanoista', 'kanonýr',
        'kapelník', 'kapitán', 'kaplan', 'kardinál', 'kardiolog', 'kat',
        'keramik', 'kladivář', 'klasik', 'klávesista', 'klavírista',
        'klavíristka', 'kluk', 'kněz', 'kněžna', 'knihovník', 'kočí', 'kolega',
        'kolegyně', 'komentátor', 'komik', 'komisař', 'komisařka',
        'komisionář', 'komorník', 'komunista', 'konstruktér',
        'kontrabasista', 'konzultant', 'koordinátor', 'koordinátorka',
        'koproducent', 'kosmonaut', 'kostelník', 'kouč', 'koulař',
        'kovář', 'krajina', 'krajkářka', 'král', 'královna', 'krejčí',
        'kreslíř', 'křesťan', 'kritik', 'kuchař', 'kuchařka', 'kulak',
        'kurátor', 'kurátorka', 'kvestor', 'kytarista', 'láma', 'laureát',
        'laureátka', 'lazar', 'leader', 'legionář', 'lékař', 'lékařka',
        'lektor', 'lesák', 'lesník', 'lidovec', 'lídr', 'likvidátor',
        'lingvista', 'literát', 'literatura', 'lord', 'loutkář', 'lukostřelec',
        'majitel', 'majitelka', 'major', 'makléř', 'malíř', 'malířka',
        'máma', 'maminka', 'manažer', 'manažerka', 'manžel',
        'manželka', 'markýz', 'maršál', 'masér', 'matematik', 'matka',
        'mecenáš', 'medik', 'meteorolog', 'metropolita',
        'mezzosopranistka', 'miláček', 'milenec', 'milenka', 'milionář',
        'milovník', 'mim', 'ministr', 'ministryně', 'miss',
        'místopředseda', 'místopředsedkyně', 'místostarosta', 'místostarostka',
        'mistr', 'mistryně', 'mladík', 'mluvčí', 'mnich', 'modelka',
        'moderátor', 'moderátorka', 'mořeplavec', 'mučedník', 'muslim',
        'muž', 'mužík', 'muzikant', 'muzikolog', 'myslitel', 'myslivec',
        'náčelnice', 'náčelník', 'nacista', 'nadace', 'náhradnice',
        'náhradník', 'nájemce', 'nájemník', 'nakladatel', 'náměstek',
        'náměstkyně', 'námořník', 'nástupce', 'navrátilec', 'návrhář',
        'návštěvník', 'nestor', 'neteř', 'nositel', 'nositelka'
        'nováček', 'novinář', 'novinářka', 'novinka', 'občan', 'obchodník',
        'obdivovatel', 'oběť', 'obhájce', 'obhájkyně', 'objevitel',
        'obránce', 'obuvník', 'obyvatel', 'ochránce', 'odborář',
        'odbornice', 'odborník', 'odchovanec', 'operace', 'organizátor',
        'ošetřovatelka', 'osobnost', 'oštěpař', 'otec', 'pamětník',
        'pan', 'pán', 'paní', 'panna', 'papež', 'papoušek', 'partner',
        'pastýř', 'páter', 'patriarcha', 'patron', 'pedagog', 'pekař',
        'perkusista', 'pěvec', 'pěvkyně', 'pianista', 'pilot', 'písničkář',
        'plavkyně', 'playboy', 'plukovník', 'pochop', 'podnikatel'
        'podnikatelka', 'pokladník', 'pokračovatel', 'policajt',
        'policista', 'politik', 'politolog', 'pomocník', 'pořadatel',
        'poradce', 'poradkyně', 'poručík', 'poslanec', 'poslankyně',
        'posluchač', 'posluchačka', 'postava', 'potomek', 'poutník',
        'pověřenec', 'pozorovatel', 'pracovnice', 'pracovník',
        'právník', 'pravnuk', 'předák', 'předchůdce', 'přednosta',
        'předseda', 'předsedkyně', 'představitel', 'představitelka',
        'překážkář', 'překladatel', 'překladatelka', 'premiér',
        'přemožitel', 'prezident', 'prezident', 'prezidentka', 'příbuzný',
        'primář', 'primářka', 'primátor', 'princ', 'princezna', 'principál',
        'příručí', 'příslušník', 'přítel', 'privatizace', 'příznivec'
        'prodavač', 'prodavačka', 'prodejna', 'proděkan', 'producent',
        'producentka', 'profesionál', 'profesor', 'profesorka', 'programátor',
        'projektant', 'prokurista', 'proletář', 'propagátor', 'prorok',
        'protagonista', 'protagonistka', 'provozovatel', 'provozovatelka',
        'prozaik', 'průkopník', 'průmyslník', 'průvodce', 'průvodkyně',
        'psychiatr', 'psycholog', 'publicista', 'publicistka',
        'purkrabí', 'rada', 'rádce', 'radikál', 'radní', 'radnice', 'redaktor',
        'redaktorka', 'ředitel', 'ředitelka', 'referent', 'referentka',
        'rekordman', 'rektor', 'reportér', 'reprezentant', 'reprezentantka',
        'republikán', 'restaurátor', 'režisér', 'režisérka', 'řezník',
        'řidič', 'rodák', 'rodič', 'rolník', 'rozehrávač', 'rozhodčí',
        'rybář', 'rytíř', 'šašek', 'saxofonista', 'sběratel', 'sbormistr',
        'scenárista', 'scenáristka', 'scénograf', 'sedlák', 'šéf',
        'šéfdirigent', 'šéfka', 'šéfkuchař', 'šéfredaktor',
        'šéfredaktorka', 'šéftrenér', 'sekretář', 'sekretářka',
        'semifinalistka', 'senátor', 'senátorka', 'šerif', 'seržant',
        'sestra', 'sestřenice', 'sexuolog', 'signatář', 'sir', 'skaut',
        'skinhead', 'skladatel', 'skladba', 'skupina', 'slávista', 'slečna',
        'sluha', 'smečařka', 'sněmovna', 'sochař', 'sochařka',
        'socialista', 'sociolog', 'sólista', 'sólistka', 'sopranistka',
        'soudce', 'soudruh', 'soukromník', 'soupeř', 'sourozenec',
        'soused', 'soutěž', 'specialista', 'specialistka', 'spisovatel',
        'spisovatelka', 'spojenec', 'spojka', 'společník', 'spoluautor',
        'spoluautorka', 'spoluhráč', 'spolujezdec', 'spolumajitel',
        'spolumajitelka', 'spolupracovnice', 'spolupracovník', 'spolutvůrce',
        'spolužák', 'spoluzakladatel', 'sponzor', 'správce',
        'starosta', 'statkář', 'státník', 'stavbyvedoucí', 'stavitel',
        'stoper', 'stoupenec', 'stratég', 'strážce', 'střelec', 'strůjce',
        'strýc', 'student', 'studentka', 'stvořitel', 'superhvězda',
        'surrealista', 'švagr', 'švec', 'svědek', 'svoboda', 'symfonie', 'syn',
        'synovec', 'tajemnice', 'tajemník', 'tanečnice', 'tanečník',
        'táta', 'tatínek', 'tchán', 'teatrolog', 'technik',
        'technolog', 'tenista', 'tenistka', 'tenor', 'tenorista',
        'tenorsaxofonista', 'teolog', 'teoretik', 'tesař', 'teta',
        'textař', 'tlumočnice', 'tlumočník', 'továrník', 'trenér', 'trenérka',
        'trojskokanka', 'trombonista', 'truhlář', 'trumpetista',
        'tvůrce', 'účastnice', 'účastník', 'učenec', 'účetní',
        'učitel', 'učitelka', 'uhlíř', 'uklízečka', 'umělec', 'úprava',
        'uprchlík', 'úřednice', 'úředník', 'útočník', 'varhaník',
        'vdova', 'vědec', 'vedoucí', 'velitel', 'velmistr', 'velvyslanec',
        'velvyslankyně', 'verbíř', 'veterán', 'veteránka', 'vévoda',
        'vězeň', 'vibrafonista', 'viceguvernér', 'vicemistr',
        'vicepremiér', 'viceprezident', 'viceprezidentka', 'violista',
        'violoncellista', 'vítěz', 'vítězka', 'vladyka', 'vlastník',
        'vnuk', 'voják', 'vrah', 'vrátný', 'vrstevník', 'vůdce', 'výčepní',
        'vychovatelka', 'vydavatel', 'vyjednavač', 'vynálezce',
        'výrobce', 'vyšetřovatel', 'vyslanec', 'výstava', 'výtvarnice',
        'výtvarník', 'vyznavač', 'vzpoura', 'zahradník', 'žák', 'zakladatel',
        'zakladatelka', 'žákyně', 'záložník', 'zámečník',
        'zaměstnanec', 'zapisovatel', 'zapisovatelka', 'zastánce', 'zástupce',
        'zástupkyně', 'závodník', 'zedník', 'železničář', 'zemědělec',
        'žena', 'žid', 'živnostník', 'zločinec', 'zloděj', 'zmocněnec',
        'znalec', 'známý', 'zoolog', 'zpěvák', 'zplnomocněnec',
        ])


def number_for(numeral):
    "Given a Czech numeral, returns the corresponding number."
    if re.match(r'^\d+$', numeral):
        return int(numeral)
    return NUMBER_FOR_NUMERAL.get(numeral)


def is_incongruent_numeral(numeral):
    """Return True if the given lemma belongs to a Czech numeral
    that takes a genitive attribute instead of being an attribute itself"""
    re.sub('[_\s]', '', numeral)
    # check whole numbers and numbers written as words
    number = number_for(numeral)
    if number is not None and (number < 1 or number > 4):
        return True
    # check decimal point numbers and indefinite numerals
    if re.match('^\d+[,.]\d+$', numeral) or \
            re.match(INDEFINITE_NUMERALS, numeral):
        return True
    return False

# read the possessive-adjective-to-noun conversion file
# and save it to the database
POSSESSIVE_FOR_NOUN = {}
with codecs.open(get_data('lexicon/cs/possessive_adjectives.tsv'),
                 'r', 'UTF-8') as handle:
    for line in handle:
        line = line.rstrip('\r\n')
        # skip comments
        if '##' in line:
            continue
        try:
            adj_lemma, count = line.split('\t')
            if int(count) < 2:
                continue
            # match long Czech possessive adjective lemma
            match = re.search('^([^_]+)_.*\/(\(.+\)\_)?\((\^UV)?\*(\d+)(.*)\)',
                              adj_lemma)
            # divide it into parts
            adj, chars_to_del, new_suffix = \
                    match.group(1), match.group(4), match.group(5)
            # create the corresponding noun lemma
            noun = adj[:-int(chars_to_del)] + new_suffix
            adj = re.sub(r'-.+', r'', adj)
            noun = re.sub(r'-.+', r'', noun)
            # store it into dictionary
            POSSESSIVE_FOR_NOUN[noun] = adj
        except:
            continue


def get_possessive_adj_for(noun_lemma):
    """Given a noun lemma, this returns a possessive adjective if it's in the
    database"""
    return POSSESSIVE_FOR_NOUN.get(noun_lemma)


def has_synthetic_future(verb_lemma):
    """Returns True if the verb builds a synthetic future tense form
    with the prefix 'po-'/'pů-'."""
    verb_lemma = re.sub(r'_s[ei]$', '', verb_lemma)
    if re.match(SYNTH_FUTURE, verb_lemma):
        return True
    return False


def inflect_conditional(lemma, number, person):
    "Return inflected form of a conditional particle/conjunction"
    ending = CONDITIONAL_INFLECT.get((number, person), '')
    return lemma + ending


def has_expletive(lemma):
    """Return an expletive for a 'že'-clause that this verb governs, or False.
    Lemmas must include reflexive particles for reflexiva tantum."""
    return EXPLETIVE_VERBS.get(lemma, False)


def is_coord_conj(lemma):
    """Return 'Y'/'N' if the given lemma is a coordinating conjunction
    (depending on whether one should write a comma directly in front)."""
    return COORD_CONJS.get(lemma, False)


def is_personal_role(lemma):
    "Return true if the given lemma is a personal role."
    return lemma in PERSONAL_ROLES


def is_named_entity_label(lemma):
    """Return 'I'/'C' if the given lemma is a named entity label
    (used as congruent/incongruent attribute)."""
    return NAMED_ENTITY_LABELS.get(lemma, False)
