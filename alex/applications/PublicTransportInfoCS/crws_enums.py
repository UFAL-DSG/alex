#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Various enums, semi-automatically adapted from the CHAPS CRWS enum list written in C#.

Comments come originally from the CRWS description and are in Czech.
"""


def enum(**enums):
    return type('Enum', (), enums)


# priznaky pozadavku na podrobnosti vracenych dat
TTDETAILS = enum(
    # vracet pevne kody
    FIXED_CODES=1L << 0,
    # vracet u pevnych kodu take pole sDescExt
    FIXED_CODES_DESC_EXT=1L << 1 | 1L << 0,
    # u datumovych poznamek davat omezeni od zacatku platnosti jizdniho radu, tj. nikoli od dneska
    REM_DATE_ALL=1L << 2,
    # pri vypoctu datumove poznamky sloucit varianty vlaku na useku (viz take REM_DISJOINT_VARIANTS)
    REM_MERGE_VARIANTS=1L << 3,
    # vracet k jedn. poznamkam i legendu znacek pouzitych v poznamkach (pro tisk)
    REM_LEGEND=1L << 4,
    # vracet hlavickove info o vlacich (TrainInfo - cislo, nazev, typ, ..)
    TRAIN_INFO=1L << 5,
    # vracet URL informacni soubory stanic (viz StationInfo.sInfoFile)
    INFO_FILES=1L << 6,
    # vracet informace pro rezervace (rezervacni klice, priznak moznosti predrezervace)
    RESERV=1L << 7,
    # vracet souradnice
    COOR=1L << 8,
    # vracet plne nazvy stanic vcetne statu a okresu (REG.ALWAYS)
    ST_NAMES_REG_ALWAYS=1L << 9,
    # misto informacniho souboru stanice davat text s linkami na zastavce (jen u JR autobusu a MHD)
    ST_LINES=1L << 10,
    # vracet vsechny stanice na trase spojeni (nejen prestupni) (zahrnuje i ROUTE_CHANGE)
    ROUTE_USED=1L << 11,
    # vracet stanice nastupu a vystupu (prestupni stanice)
    ROUTE_CHANGE=1L << 22,
    # vracet pocatecni a koncovou stanici kazdeho pouziteho spoje
    ROUTE_FROMTO=1L << 12,
    # vracet celou trasu pouzitych spoju (zahrnuje i ROUTE_USED a ROUTE_FROMTO)
    ROUTE_FULL=1L << 13,
    # vracet celou trasu pouzitych spoju jen v pripade, ze jizdni rad je vlakovy, jinak se ridi dle vlajek ROUTE_USED, ROUTE_CHANGE, ROUTE_FROMTO a ROUTE_FULL
    ROUTE_FULL_TRAIN=1L << 14,
    # vracet na draze take zalamane vedeni (TrainRouteInfo.adCoorX a TrainRouteInfo.adCoorY)
    ROUTE_COOR=1L << 15,
    # vracet poznamky k celemu spojeni; funguje bez ohledu na REMMASK
    # (nema vliv na poznamky k jednotlivym vlakum spojeni - ty se ridi parametrem iRemMask, viz enum REMMASK)
    # v poznamkach vsak mohou byt pouzity znacky TT; pro tisk pak je uzitecna legenda (RemarksList.aoLegend)
    REMARKS=1L << 16,
    # vracet i poznamku "jede denne"? (je ucinne pouze, pokud je soucasne zapnute REMARKS)
    REMARKS_DAILY=1L << 17,
    # vracet i seznam dopravcu? (je ucinne pouze, pokud je soucasne zapnute REMARKS, vyjimkou je pole DepartureTrain.sOwner)
    REMARKS_OWNERS=1L << 18,
    # nevracet v ramci poznamek ke spojeni datumove omezeni nikdy (souvisi se soucasne zapnutym REMARKS)
    REMARKS_SKIPDATE=1L << 19,
    # vracet v ramci poznamek ke spojeni take data o vylukach a mimoradnostech,
    #  viz take REMMASK.EXCLUSION_DATA a REMMASK.EXCEPTION_DATA (souvisi se soucasne zapnutym REMARKS)
    REMARKS_EXCLUSION_DATA=1L << 24,
    # vratit v poznamkach ke spojeni take umelou poznamku typu REMMASK.DATE_FLAGS s priznaky jizdy (souvisi se soucasne zapnutym REMARKS)
    DATE_FLAGS=1L << 20,
    # vracet priznak moznosti polohy vlaku (viz take DELAY_CD_ONLY, DELAY_ARRDEP)
    DELAY=1L << 21,
    # pro odjezdove/prijezdove tabule: rezim CD: natvrdo davat smerovani dle pozadavku CD (max. 3 stanice) a vytvorit sestavu na 24 hodin
    DEP_TABLE_CD=1 << 23,
    # vracet sumarni legendu znacek na urovni celkoveho seznamu spojeni (pro tisk, obsahuje znacky pouzite v poznamkach i u stanic/spoju)
    LEGEND_ALL=1L << 25,
    # ma smysl jen ve spojeni s LEGEND_ALL, indikuje omezeni zahrnuti pevnych kodu jen na nastupni a vystupni stanici
    LEGEND_FROMTO_ONLY=1L << 26,
    # ma smysl jen ve spojeni s LEGEND_ALL, prikazuje pridat do legendy i znacky, ktere nejsou v TT fontu, resp. nejsou substituovany do ikony
    # kody na draze, ktere obsahuji cislo (typicky nastupiste a tar. pasma) se ale nezahrnuji
    LEGEND_ADD_NON_TT=1L << 27,
    # ma smysl jen ve spojeni s LEGEND_ALL, prikazuje nepridavat do legendy pevne kody hlavicky spoje 
    LEGEND_SKIP_TRAIN=1L << 29,
    # v parametru iStation je ve skutecnosti na vstupu klic stanice (uplatni se ve funkci GetTrainDataInfo)
    KEY_IN_STATION=1L << 28,
    # nezahrnovat ve vystupu prime vozy (vyhledani spoje dle masky, odjezdy/prijezdy, spojeni)
    NO_CARS=1L << 30,
    # nezahrnovat ve vystupu spoje soukromych dopravcu, kteri nemaji smlouvu s CD (vyhledani spoje dle masky, odjezdy/prijezdy)
    CD_ONLY=1L << 31,
    # nevracet jednotlive spoje, ale od kazde linky jen jednoho reprezentanta
    SEARCH_LINES=1L << 32,
    # vracet v TrainInfo.sInfo informaci o lince/vedeni spoje
    LINE_IN_INFO=1L << 33,
    # vracet spoje po kazde variante smerovani dle ZJR (jen JR typu MHD)
    ZJR_DIRS=1L << 34,
    # vracet ve StationInfo take aiTrTypeID (viz take obdobny priznak v TTINFODETAILS)
    TRTYPEID_STATION=1L << 35,
    # nedavat duplicitni spoje (kontroluje se jen sNum1)
    TRAININFO_SKIPDUP=1L << 36,
    # cisla stanovist (ArrDepTrainInfo.sStand a DepartureTrain.sStand/sTrack)
    STANDS=1L << 37,
    # linky IDS pro vlaky (ArrDepTrainInfo.sIDSLine a DepartureTrain.sIDSLine)
    IDS_LINES=1L << 38,
    # ceny (jizdne)
    PRICES=1L << 39, # obe ceny i s detaily (zahrnuje i PRICE2)
    PRICE1=1L << 40, # pouze jedna cena do ConnectionInfo.sPrice, jen jako string (bez detailu - useku), jen je-li uplna (za celou trasu)
    PRICE2=1L << 41, # celkova cena formatovana jako pro www (bez detailu - useku)
    #                      - je-li soucasne zapnuto PRICE1 i PRICE2, pak se vraci celkova cena formatovana jako pro www, ale jen pokud je znama za celou trasu  
    # vracet u spojeni take cilovou obec?
    DEST_CITY=1L << 42,
    # vracet u jednotlivych spojeni ID kombinace (ma smysl, jen pokud se muze u spojeni lisit)
    CONN_COMBID=1L << 43,
    # v pripade volani funkce SearchConnectionInfo2 pro spojeni s prestupy bez zadanych prestupnich mist zkusit nejprve otipovat prestupy
    CONN2_SET_CHANGE=1L << 44,
    # pri hledani spoje (linky) akceptovat jen presnou shodu s maskou, tj. neakceptovat podretezec 
    MATCH_EXACT=1L << 45,
    # vracet v ramci ZJRInfo take pole aoAltDirections s alternativnimi smery ZJR
    ZJR_ALT_DIR=1L << 46,
    # vracet v ramci ZJRInfo davat smery i ze vsech zastavek uzlu
    MERGE_ST=1L << 47,
    # vracet spoje po kazde variante smerovani linky
    LINE_DIRS=1L << 48,
    # vracet priznak moznosti polohy vlaku a zpozdeni jen pro vlaky dopravce CD (plati jen soucasne s DELAY)
    DELAY_CD_ONLY=1L << 49,
    # pri vyhledani N odjezdu/prijezdu do budoucna zahrnout na zacatek i zpozdene spoje (plati jen soucasne s DELAY)
    DELAY_ARRDEP=1L << 50,
    # pri vypoctu datumove poznamky davat omezeni u variant vlaku disjunktne (potlacuje REM_MERGE_VARIANTS)
    REM_DISJOINT_VARIANTS=1L << 51,
)

# priznaky pozadavku na podrobnosti k objektu typu TimetableObjectInfo
TTINFODETAILS = enum(
    ITEM=1 << 0, # vratit pole oItem
    STATIONS=1 << 1, # vratit pole aoStations
    LINES_ITEM=1 << 2, # vratit sumar linek v sLines (jen pro JR typu MHD a Bus)
    LINES_STATION=1 << 3, # vratit sumar linek ve StationInfo.sInfoFile (jen pro JR typu MHD a Bus)
    TRTYPEID_ITEM=1 << 4, # vratit sumar ID druhu prostredku u polozky
    TRTYPEID_STATION=1 << 5, # vratit sumar ID druhu prostredku u stanic
    COOR=1 << 6, # vratit souradnice
    STCOUNT=1 << 7, # vratit pocet fyzickych stanic objektu
    STATE_ITEM=1 << 8, # vratit vysvetleni statu v sState
    STATE_ITEM_ALWAYS=1 << 9, # vratit vysvetleni statu v sState, i kdyz neni primo v nazvu objektu uveden
    REGION_ITEM=1 << 10, # vratit vysvetleni okresu v sRegion
    REGION_ITEM_ALWAYS=1 << 11, # vratit vysvetleni okresu v sRegion, i kdyz neni primo v nazvu objektu uveden
    REGION_DELETE=1 << 12, # vymazat data o regionu z nazvu objektu/adresy, idealne kombinovat s iRegMode:=REG.NONE
    LINES_BRIEF=1 << 13, # zkraceny sumar linek (jen ve spojitosti s LINES_ITEM a LINES_STATION)
    TYPE_ITEM=1 << 14, # vratit typ objektu v sType
    LINES_ITEM_MHD=1 << 15, # vratit sumar linek v sLines jen pro objekty z JR typu MHD (jen ve spojitosti s LINES_ITEM)
    REGION_NEEDED=1 << 16, # vratit v bRegion priznak, zdali je region pro rozliseni objektu nutny (jen ve spojitosti s REGION_ITEM_ALWAYS)
    TR_CATEGORY=1 << 17, # vratit v sTrCategory druhy dopravy (aplikuje se jen na kombinacich, ktere zahrnuji vlaky i busy)
    STATIONSEXT=1 << 18 | 1 << 1 # vratit pole aoStations jen pokud se vraci prvky seznamu stanic (LISTID.STATIONSEXT)
)

# kategorie dopravy
TRCAT = enum(
    ALL=0, # nerozliseno
    TRAIN=1, # vlaky
    BUS=2, # linkove autobusy
    CITY=3, # MHD
    AIR=4, # letadla
    SHIP=5        # lode
)

# podkategorie dopravy (jen vybrane, rozsiruje se prubezne dle potreby)
TRSUBCAT = enum(
    ALL=0,
    PRAHA=1,
    BRNO=2,
    OSTRAVA=3,
    CESBUD=4
)

# jazyky
TTLANG = enum(
    CZECH=0,
    ENGLISH=1,
    GERMAN=2,
    SLOVAK=3,
    POLISH=4,
    COUNT=5,
)

# ID zakladnich virtualnich seznamu
LISTID = enum(
    CITY=1, # mesta a obce
    CITYPART=2, # mestske casti
    STATIONSEXT=3, # vsechny stanice + nejaka rozsireni (realne byva dekorovan cislem kategorie a podkategorie, viz iListID)
    ADDRESS=8, # symbolicky seznam adres: ve skutecnosti neni soucasti JR, ale je obsluhovan serverem adres  
    STATIONS=9         # symbolicky seznam fyzickych stanic: nelze jej pouzit ke globalnimu vyhledavani!
    #                      - lze jej pouzit pouze na pozici GlobalListItemInfo.iListID, 
    #                        v tomto pripade musi klient nastavit do GlobalListItemInfo.iItem index stanice dle StationInfo.iStation   
)

# kody vyjimek, ktere posila primo jadro (jizdni rad)
TTERR = enum(
    # pri nacitani dat doslo k chybe
    LOAD=1,
    # pri nacitani dat doslo k vyjimce
    LOAD_EX=2,
    # pri paralelnim nacitani jizdnich radu se nektery nenacetl
    LOAD_MULTI=3,
    # nacitani dat prave probiha, nelze jej spustit soucasne znovu
    LOAD_RUNNING=4,
    # chybný index stanice
    BAD_ST_INDEX=5,
    # chybný index spoje
    BAD_TR_INDEX=6,
    # chybný index jizdniho radu
    BAD_TT_INDEX=7,
    # chybný index seznamu
    BAD_VIRT_LIST_INDEX=8,
    # chybny index objektu
    BAD_VIRT_LIST_ITEM_INDEX=9,
    # chybný index poznamky spoje
    BAD_TR_REM_INDEX=10,
    # substituce s ID nebyla nalezena
    BAD_SUBST_ID=11,
    # ocekava se 32-mista unikatni identifikace kombinace
    COMB_GUID_EXPECTED=12,
    # prazdne ID kombinace
    COMB_ID_EXPECTED=13,
    # chybný index globalniho seznamu
    BAD_GLOBAL_LIST_INDEX=14,
    # chybny index polozky globalniho seznamu
    BAD_GLOBAL_LIST_ITEM_INDEX=15,
    # pri pokusu o nacteni konfiguracniho souboru doslo k vyjimce
    TT_CONFIG=16,
    # kombinace pro zadane absolutni ID nebyla nalezena
    COMB_GUID_NOT_FOUND=17,
    # kombinace pro zadane ID nebyla nalezena
    COMB_NOT_FOUND=18,
    # chybna hlavicka datoveho souboru
    BAD_DATA_FILE_HEADER=19,
    # chyba CRC datoveho souboru
    BAD_DATA_FILE_CRC=20,
    # neplatny handle seznamu spojeni
    CONN_HANDLE_BAD=21,
    # seznam spojeni jiz  byl uvolnen, provedte nove hledani
    CONN_HANDLE_RELEASED=22,
    # k seznamu spojeni s danym handle se prave pristupuje, zkuste to za chvili
    CONN_HANDLE_LOCKED=23,
    # jako cilovy seznam pro kopirovani spojeni nelze zadat bezny seznam (pouze kosik spojeni)
    CONN_HANDLE_STANDARD=24,
    # handle seznamu spojeni neodpovida pracovnimu procesu
    CONN_HANDLE_WORKER_BAD=25,
    # spojeni se zadanym ID nebylo nalezeno
    BAD_CONN_ID=26,
    # kombinaci nelze pro dany ucel pouzit
    BAD_COMB_USAGE=27,
    # chybne datum
    BAD_DATE=28,
    # chybny popis
    BAD_AUX_DESC=29,
    # chybny popis spoje nebo spoj nenalezen
    BAD_AUX_DESC2=30,
    # chybny parametr funkce
    BAD_FUNC_PARAM=31,

)

# kody klientskych vyjimek CRWS
CLIENTEXCEPTION_CODE = enum(
    # Neplatné ID uživatele (GUID)
    INVALIDUSERID=1000,
    # Neplatný přístupový kód (handle) seznamu spojení (evidentne spatny - napr. neni kladny nebo neodpovida absolutnimu ID kombinace)
    INVALIDCONNHANDLE=1001,
    # Neplatné ID kombinace (GUID)
    INVALIDCOMBGUID=1002,
    # Přístupový kód (handle) seznamu spojení již není platný, proveďte nové hledání spojení
    CONNHANDLETIMEOUT=1003,
    # Nepovolená kombinace "{0}". (nema na ni prava nebo zadal nesmysl)
    INVALIDCOMBID=1005,
    # Nemáte nastavena práva na žádnou kombinaci.
    NOCOMBINATIONENABLED=1006,
    # Právě probíhá restart serveru jízdních řádů. Zopakujte prosím požadavek později.
    APPRESTART=1007,
    # (zjištění polohy vlaku:) Informace o vlaku {0} nejsou k dispozici. {1}
    NOINFO=1010,
    # (zjištění polohy spoje:) Informace o spoji {0} nejsou k dispozici. {1}
    NOBUSINFO=1011,
    # (zjištění polohy vlaku:) Poloha vlaku není k dispozici. Zkuste to prosím později.
    TRAINPOSITION=1012,
    # (zjištění polohy spoje:) Poloha spoje není k dispozici. Zkuste to prosím později.
    BUSPOSITION=1013,
    # (zjištění polohy spoje:) Chybný řetězec pro zjištění polohy spoje ({0}).
    DELAYQUERYSOURCE=1016,
    # (zjištění polohy spoje:) Prázdný řetězec pro zjištění polohy spoje.
    DELAYQUERYSOURCEEMPTY=1017,
    # (info o mimořádnosti nebo výluce:) Chybný řetězec pro zjištění informace o mimořádnosti nebo výluce ({0}).
    EXCLUSIONQUERYSOURCE=1030,
    # (info o mimořádnosti nebo výluce:) Prázdný řetězec pro zjištění informace o mimořádnosti nebo výluce.
    EXCLUSIONQUERYSOURCEEMPTY=1031,
    # (info o mimořádnosti nebo výluce:) Informace o mimořádnosti nebo výluce {0} nejsou k dispozici. {1}
    NOEXCLUSIONINFO=1032,
    # (info o mimořádnosti nebo výluce:) Informace o mimořádnosti nebo výluce nejsou k dispozici. Zkuste to prosím později.
    EXCLUSIONINFO=1033,
    # obecna chyba, zkuste pozdeji
    TRYLATER=1020,
)

# bitove priznaky ke stanicim
ST = enum(
    CHANGE=0x1, # prestupni stanice
    INTL=0x2, # zahranicni stanice
    REG=0x4, # vkladat region do nazvu
    STATE=0x8, # vkladat stat do nazvu
    RESERV=0x10, # ve stanici pojizdi vlak s rezervacemi
    EXTERNLINK=0x20, # obsahuje externi hrany
    PREFCHANGE=0x40, # preferovany prestupni bod
    CAPITAL=0x80, # je v hlavnim meste statu
    REGION2=0x100, # je v krajskem meste
    REGION3=0x200, # je v okresnim meste
    LOWDECK=0x400, # bezbarierova
    TERM=0x800, # konecna
    SKIP_CITY=0x1000, # nezahrnovat do obce
    PPS=0x2000, # vlakova PPS
    GC=0x4000, # ma garantovane prestupy
    LOWDECK_CHANGE=0x8000 # bezbarierova pro prestup
)

# rezimy vkladani regionu (stat,okres) do nazvu
REG = enum(
    SMART=0, # vkladat regiony dle potreby
    ALWAYS=1, # vkladat regiony i staty vzdy
    NO=2, # nevkladat nikdy
    ALWAYS_SMART=3, # vkladat regiony vzdy, jsou-li k dispozici
    ALWAYS_REDUCED=4      # vkladat regiony vzdy, staty skryvat vzdy, je-li region k dispozici
)

# priznaky kombinace jizdnich radu
COMBFLAGS = enum(
    # krajske mesto
    REGION=1 << 0,
    # IDS
    IDS=1 << 1,
    # pouzit jako vychozi nazev kombinace zkracenou verzi
    BRIEF_NAME=1 << 2,
    # nenabizet v panelu nabidek
    HIDE=1 << 3,
    # lze pozadovat zadani adresy
    HAS_ADDRESS=1 << 4,
    # nahrat kombinaci, i kdyz je prosla
    LOAD_OLD=1 << 5,
    # pripravit dopredu graf site pro pokryti
    BUILD_GRAPH=1 << 6
)

# priznaky jednotliveho jizdniho radu
TIMETABLE_FLAGS = enum(
    # k dispozici jsou data o souradnicich zastavek
    HAS_MAP=1 << 0,
    # k dispozici jsou data o vedeni spoju mezi zastavkami (z priznaku vyplyva i HAS_MAP)
    HAS_ARCS=1 << 1,
    # k dispozici je graf pokryti site (z priznaku vyplyva i HAS_ARCS)
    HAS_COVER=1 << 2,
)

# zpusob hledani v globalnim seznamu objektu
SEARCHMODE = enum(
    NONE=0, # prazdny priznak
    EXACT=1 << 0, # vracet pri presne shode jen ji
    CITY_AND_PART=1 << 1, # navic pri presne shode obce hledat jeste presnou shodu casti (plati jen ve spojeni s EXACT)
    SCAN_ALL_LISTS=1 << 2, # prochazet vsechny seznamy do vycerpani max. poctu
    NO_ADD_EQUAL=1 << 3, # nepridavat objekt z dalsiho seznamu, pokud se mapuje do stejnych zastavek 
    #                                   jako jiz pridany se stejnym jmenem z drivejsiho seznamu
    SCAN_ALL_LEVELS=1 << 4, # hledat shodu se zadanou maskou od zacatku, 
    #                                   pokud nenaplnim pozadovany pocet, tak od druheho slova, atd.
    SORT_LIST_ID=1 << 5, # tridit po seznamech (plati jen ve spojeni s SCAN_ALL_LEVELS) 
    #                                   normalne je shoda na nultem slove ve vsech seznamech, pak na prvnim slove ve vsech seznamech, atd.
    SKIP_CITY_ALIAS=1 << 6, # pokud je to mozne, nezarazovat aliasy obci a casti obci
    ALLOW_ADDRESS=1 << 7, # je-li konfigurovan pristup k serveru adres, zkus na zaver resit jeste jako adresu
    #                                   aplikuje se jen v pripade, ze se hleda bez omezeni na konkretni seznam nebo s omezenim na seznam LISTID.ADDRESS
    #                                   a soucasne prislusna kombinace JR adresy pripousti 
    USE_PRIORITY=1 << 8, # pouzit prioritni nabidku (aplikuje se jen pri hledani, ktere neni omezeno na jeden seznam, tj. iListID==0)
    FORCE_ADDRESS_REG=1 << 9, # pozadovat od serveru adres, aby okres daval za nazvem obce nebo casti vzdy a nikoli jen v pripade nejednoznacnosti nazvu
    #                                   - je to nutnost v pripade pouziti priznaku TTINFODETAILS.REGION_ITEM_ALWAYS
    #                                   - nasledne lze ovsem okres vymazat pomoci TTINFODETAILS.REGION_DELETE
    #                                   - server adres vraci v tomto pripade zavazne okresy a velkymi pismeny a nezavazne malymi
    CHECK_UNIQUE_ONLY=1 << 10, # ma smysl jen ve spojeni s vyhledavanim do ObjectsInfo, je-li zapnuto, tak se
    #                                   - v pripade, za masce hovi vice moznosti, vrati se v ObjectsInfo.aoMasks hodnota null a v iStatus se vrati STATUS_NOT_UNIQUE
    #                                   - dale pak v pripade, ze maska je jednoznacna a iTTInfoDetails je nenulove, vyplni take ObjectsInfo.oTimetableObject 
    NO_ADD_EQUAL_NAME=1 << 11, # nepridavat objekt z dalsiho seznamu se stejnym nazvem 
    USE_COOR_VICINITY=1 << 12     # vracet body v blizkosti souradnice
    #                                   - souradnice pro hledani se zadava jako soucast masky za znakem §
    #                                   - interni priznak, jeho nastaveni na vstupu se ignoruje
)

# masky poznamek ke spojum
REMMASK = enum(
    NONE=0, # prazdna maska
    LINE_NAME=0x1, # nazev linky
    OWNER=0x2, # dopravce
    DATE=0x4, # datumove omezeni
    INFO=0x8, # informacni poznamka
    INFO_IMPORTANT=0x10, # dulezita informacni poznamka
    LINE=0x20, # informacni poznamka k lince
    RESERV=0x40, # poznamka o povinne rezervaci
    RESERV2=0x80, # poznamka o volitelne rezervaci
    DIRECTCARS=0x100, # poznamka o primem voze
    OWNER_WWW=0x200, # je-li zadana (a soucasne i OWNER), 
    #                          tak se do nazvu dopravce nageneruje link na www dopravce
    DATE_FLAGS=0x400, # vratit take umelou poznamku z datumovych vlajek
    #                          je nezavisla na ostatnich maskach 
    OWNER_NUM=0x800, # je-li zadana (a soucasne i OWNER), 
    #                          tak se misto nazvu dopravce nageneruje jeho cislo
    EXCLUSION=0x1000, # informace o vyluce
    EXCLUSION_DATA=0x2000, # informace o vyluce jako data
    #                          polozky oddelene znakem pipe:
    #                              0 - trat
    #                              1 - usek
    #                              2 - priznak, ze vyluka je PRED spojenim (0 nebo 1)
    #                              3 - index pocatecni stanice do drahy spoje nebo -1 u spojeni
    #                              4 - index koncove stanice do drahy spoje nebo -1 u spojeni
    #                              5 - ID vyluky, ID opatreni, datum - parametry pro ziskani podrobnosti o vyluce (oddelovac carka)
    EXCEPTION_DATA=0x4000, # informace o mimoradnosti jako data
    #                          polozky odde)lene znakem pipe:
    #                              0 - trat
    #                              1 - usek
    #                              2 - pricina
    #                              3 - datum a cas platnosti od
    #                              4 - datum a cas platnosti do
    #                              5 - datum a cas aktualizace zaznamu o mimoradnosti
    #                              6 - priznak, ze mimoradnost je PRED spojenim (0 nebo 1)
    #                              7 - index pocatecni stanice do drahy spoje nebo -1 u spojeni
    #                              8 - index koncove stanice do drahy spoje nebo -1 u spojeni
    #                              9 - ID mimoradnosti - parametr pro ziskani podrobnosti o mimoradnosti
    DELAY_QUERY=0x8000, # dotaz na polohu vlaku pro nasledne volani funkce DelayQuery
    AUX_DESC=0x10000, # popis vlaku pro nasledne volani funkce MapTrainDataInfoAuxDesc nebo MapConnectionAuxDesc
    #                          (vlozi se referencni usek dle dotazu)
    AUX_DESC_FULL=0x20000, # popis vlaku pro nasledne volani funkce MapTrainDataInfoAuxDesc nebo MapConnectionAuxDesc
    #                          (vlozi se usek za celou drahu vlaku)


    # veskere informacni poznamky
    ALLINFO=0x8 | 0x10 | 0x20 | 0x40 | 0x80 | 0x100 | 0x1000,
    # ...navic nazev linky, doprace a datumove omezeni
    ALL=0x1 | 0x2 | 0x4 | 0x8 | 0x10 | 0x20 | 0x40 | 0x80 | 0x100 | 0x1000,

)

# priznaky typu spoje (viz. TrainInfo.iFlags)
# (mohou byt pouzity i dalsi bity, zde jsou vyvedeny vybrane staticke hodnoty)
VF = enum(
    INTLONLY=0x80000000, # vnitrostatni preprava vyloucena
    INTL=0x40000000, # mezinarodni spoj (ne ciste domaci)
    VAR=0x10000000, # varianta vlaku
    CARS=0x8000000, # primy vuz
    HASBEDS=0x2000000, # veze take lehatka nebo luzka
    HASONLYBEDS=0x1000000, # veze jen lehatka nebo luzka
    RESERV=0x800000, # je predmetem rezervace
    NOLINEDIR=0x400000, # nepouzivat pro generovani vedeni linky
    LINEDIRBACK=0x200000, # jede smerem ZPET
    LOWDECK=0x100000                 # nizkopodlazni spoj (bezbarierovy pristup)
)

# priznaky na draze
ROUTE_FLAGS = enum(
    EMPTY=0, # prazdna hodnota
    NO_EXIT=1 << 0, # neni vystup
    NO_ENTER=1 << 1, # neni nastup
    PARA=1 << 2, # priznak paragraf
    ZOLL=1 << 3, # hranicni bod (zde v zasade jen indikuje, ze neni nastup ani vystup)
    CHANGE_INFO=1 << 4, # priznak, ze k zastaveni se vaze omezeni prestupu
    REMARK=1 << 5, # priznak, za k zastaveni je poznamka
    PPS=1 << 6           # vlakova pohranicni prechodova stanice (zastaveni je neverejne a tedy by se nemelo zobrazovat)
)

# absolutni pevne kody pro hledani spojeni
FCS = enum(
    WHEELCHAIR=1, # pro cestující na vozíku 
    CHILDREN=2, # pro cestující s dětmi 
    BIKE=3, # pro cestující s kolem 
    CD=4, # vlak Českých drah 
    NOT_HISTORICAL=5, # není zvláštní historický vlak
    CD_ONLY=6, # vlak ČD a smluvních dopravců                
    NOT_RESERVE=7        # vlak bez povinne rezervace
)

# souradnicove systemy pro vzajemnou konverzi
COOR = enum(
    EMPTY= -1,
    S42=0,
    JTSK=1,
    UTM=2,
    WGS84=3, # svetove souradnice v radianech (jako X je zde zem. delka a jako Y pak sirka)
    WGS84_D=4, # svetove souradnice ve stupnich (jako X je zde zem. sirka a jako Y pak delka)
    MERCATOR=5,
    PUWG_2000=6,

    DEFAULT=4             # souradny system, v kterem jsou drzena data v pameti
)

# navratovy typ pro hledani spojeni/odjezdu/ZJR (hodnota iResult)
EXFUNCTIONRESULT = enum(
    OK=0, # vyhledane objekty byly unikatni a postoupilo se tedy ke hledani spojeni/odjezdu/ZJR a ziskaly se nejake vysledky
    NOT_FOUND=1 << 0, # vyhledane objekty byly unikatni a postoupilo se tedy ke hledani spojeni/odjezdu/ZJR, avsak nic se nenaslo
    DATE_OUT_OF_RANGE=1 << 1, # datum pro hledani je mimo pripustny rozsah
    FROM_TO_OVERLAP=1 << 4, # prekryti Z/Pres/Do (stejne objekty)
    FROM_ERROR=1 << 5, # chyba hledani Z (masce neodpovida zadny objekt)
    FROM_NOT_UNIQUE=1 << 6, # vyhledany nejake objekty Z, ale zadani neni jednoznacne
    FROM_MISSING=1 << 7, # Z chybi a dle kontextu by melo byt pritomne
    FROM_BAD=1 << 8, # k Z nebyly nalezeny zadne pouzitelne stanice, viz ObjectsInfo.iStatus
    TO_ERROR=1 << 10, # chyba hledani Do (masce neodpovida zadny objekt)
    TO_NOT_UNIQUE=1 << 11, # vyhledany nejake objekty Do, ale zadani neni jednoznacne
    TO_MISSING=1 << 12, # Do chybi a dle kontextu by melo byt pritomne
    TO_BAD=1 << 13, # k Do nebyly nalezeny zadne pouzitelne stanice, viz ObjectsInfo.iStatus
    VIA_ERROR=1 << 15, # chyba hledani Pres (masce neodpovida zadny objekt)
    VIA_NOT_UNIQUE=1 << 16, # vyhledany nejake objekty Pres, ale zadani neni jednoznacne
    VIA_MISSING=1 << 17, # Pres chybi a dle kontextu by melo byt pritomne
    VIA_BAD=1 << 18, # k Pres nebyly nalezeny zadne pouzitelne stanice, viz ObjectsInfo.iStatus
    CHANGE_ERROR=1 << 20, # chyba hledani Prestup (masce neodpovida zadny objekt)
    CHANGE_NOT_UNIQUE=1 << 21, # vyhledany nejake objekty Prestup, ale zadani neni jednoznacne
    CHANGE_MISSING=1 << 22, # Prestup chybi a dle kontextu by melo byt pritomne
    CHANGE_BAD=1 << 23, # k Prestup nebyly nalezeny zadne pouzitelne stanice, viz ObjectsInfo.iStatus
)

# typ odchylky od nejkratsi cesty
DELTAMAX = enum(
    NO=0, # nezadana
    PERCENT=1, # v procentech
    METERS=2    # v metrech
)

# priznak pouziti lehatek/luzek
BEDS = enum(
    USEANY=0, # pouzivat bez omezeni
    ONLYBEDS=1, # cestovat pouze s lehatkem/luzkem
    NOBEDS=2     # pouze mista k sezeni
)

# stav reseni objektu v ObjectsInfo
OBJECT_STATUS = enum(
    # objekt je v poradku
    OK=0,
    # zadny objekt dle masky nebyl nalezen
    NOT_FOUND=1,
    # indikuje, ze nabidka objektu neni jednoznacna
    NOT_UNIQUE=2,
    # indikuje, ze k prislusne souradnici nejsou v blizkosti zastavky pro hledani spojeni
    COOR_BAD=3,
    # indikuje, ze k prislusnemu objektu nejsou zastavky pro hledani spojeni
    # (mozne priciny - jizdni rad v dany den jizdy neplati 
    #                  nebo nesplnuji omezeni na bezbarierovy pristup
    #                  nebo bylo zadano omezeni na dopravni prostredky a zadne na objektu nestoji)
    OBJECT_BAD=4
)

# globalni priznak k napocitanemu jizdnemu
TTGP = enum(
    ALL_OK=0, # cena je k dispozici pro cely usek
    PART_OK=1, # cena je k dispozici pro cast cesty
    MISSING=2  # cena chybi
)

# vycet stavu pro sluzbu poloha spoje
SVCSTATE = enum(
    CRSERVER= -1, # vraci primo CRServer
    CZ=0,
    SK=1,
    TELMAX1=2,

    MAX=1        # jen pro pohodli kodu
)

# priznaky odjezdove tabule
DEP_TABLE = enum(
    SHOW_STAND=1 << 0, # zobrazovat pole pro nastupiste/stanoviste (i kdyz v konkretnim vystupu nemusi byt zadano)
    SHOW_TRACK=1 << 1, # zobrazovat pole pro kolej (i kdyz v konkretnim vystupu nemusi byt zadana)
    BUILT_FROM_TT=1 << 2, # vyrobena na zaklade jizdniho radu (nebyla primo importovana)
    POS_USED=1 << 3        # pri sestaveni byly pro prislusny jizdni rad k dispozici polohy (zpozdeni) spoju
    #                          (tento priznak muze byt pouzit jen soucasne s BUILT_FROM_TT)
)


# ruzne konstanty
class CRCONST:
    # zdroje zpozdeni
    # Ceske drahy
    DELAY_CD = "CD:"
    # ZSR
    DELAY_ZSR = "ZSR:"
    # TELMAX
    DELAY_TELMAX1 = "TELMAX1:"
    # interni zpozdeni (vklada se take kategorie a podkategorie)
    DELAY_INTERN = "X{0}_{1}:"
    # rozsirene interni zpozdeni (vklada se take kategorie a podkategorie),
    # zde se daji oproti DELAY_INTERN nasledne zadat i rozsirene masky, odelovac mezi polozkami je vzdy carka
    DELAY_INTERN_EXT = "Y{0}_{1}:"

    # zdroje vyluk a mimoradnosti
    # Ceske drahy
    EXCEPTIONEXCLUSION_CD = "CD:"
