# All data comes from the JSON API behind the new TSETMC website
# (https://www.tsetmc.com). The old website (old.tsetmc.com) and its
# endpoints were shut down on 30 Azar 1405 (issue #280).
#
# The comment above every endpoint says which page of www.tsetmc.com calls
# it and how to reach it, so it can be checked in the browser's network tab
# when the API changes again. (Checked with Chrome on 1405/08/26.)
#
# {insCode} (also called "index" in this package) is the instrument code,
# e.g. 46348559193224090 for فولاد. Dates are Gregorian YYYYMMDD.
#
# How to reach the pages named below:
# - instInfo (page of a symbol), https://www.tsetmc.com/instInfo/{insCode}:
#   top bar icon "جستجو" (search) > type the symbol > click the result.
#   Its tabs: در یک نگاه, سابقه, حقیقی-حقوقی, سهامداران, معرفی, ...
# - History (one trading day of a symbol),
#   https://www.tsetmc.com/History/{insCode}/{date}: instInfo > tab
#   "در یک نگاه" > box "سابقه معاملات" > click a date, or instInfo > tab
#   "سابقه" > double click a day.
# - IndexInfo (page of a financial index),
#   https://www.tsetmc.com/IndexInfo/{insCode}: home page > box
#   "شاخص های منتخب" > click an index. It has no tabs, only sections.
# - Market watch, https://www.tsetmc.com/marketwatchnew: not linked from
#   the menus of the new site (the "دیده بان بازار" icon still opens the old
#   site); type the address, or sign in at /login which redirects to it.

# Market overview of the stock exchange (flow 1). marketActivityDEven is the
# last trading day of the market.
# Page: https://www.tsetmc.com/ (home), tab "در یک نگاه", box
# "بازار نقدی بورس در یک نگاه". Also polled by the "نمای کلی از بازار" box
# at the top of instInfo and History pages.
TSE_GET_LAST_TRADE_DAY = (
    "https://cdn.tsetmc.com/api/MarketData/GetMarketOverview/1"
)

# Daily price history of an instrument, newest first. The last path part is
# the number of days, 0 means the whole history.
# Page: instInfo, tab "سابقه" (history). The box "سابقه معاملات" of tab
# "در یک نگاه" calls it with 12 instead of 0.
TSE_TICKER_EXPORT_DATA_ADDRESS = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{}/0"
)

# The same daily price history, only the last 12 days.
# Page: instInfo, tab "در یک نگاه" (opens with the page), box
# "سابقه معاملات" (trade history), loaded with the page. Ticker uses it to
# check whether a saved history csv is up to date.
TSE_TICKER_RECENT_DAYS_URL = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{}/12"
)

# Daily history of a financial index: close, low and high per day.
# Page: IndexInfo, section "سابقه شاخص", loaded with the page.
TSE_FINANCIAL_INDEX_EXPORT_DATA_ADDRESS = (
    "https://cdn.tsetmc.com/api/Index/GetIndexB2History/{}"
)

# Intraday values of a financial index for the last trading day.
# Page: IndexInfo, section "سابقه شاخص روز جاری", loaded with the page.
FINANCIAL_INDEX_EXPORT_INTRADAY_URL = (
    "https://cdn.tsetmc.com/api/Index/GetIndexB1LastDay/{}"
)

# Companies (instruments) that make up a financial index.
# Page: IndexInfo, section "شرکت های موجود در شاخص", loaded with the page.
FINANCIAL_INDEX_COMPANIES_URL = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetIndexCompany/{}"
)

# Page of a ticker on the website, returned by Ticker.url. Not an API.
TSE_TICKER_ADDRESS = "https://www.tsetmc.com/instInfo/{}"

# Instrument information: sector, EPS, P/E, PSR, price thresholds,
# week/year min and max, total shares, base volume, flow, ISIN...
# Page: instInfo, loaded with the page (tab "در یک نگاه": title, EPS and
# P/E box, تعداد سهام, حجم مبنا, سهام شناور, میانگین حجم ماه, گروه).
TSE_INSTRUMENT_INFO = (
    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentInfo/{}"
)

# Live prices of an instrument for the current day: last trade, closing
# price, first, high, low, yesterday, count, volume, value and state.
# Page: instInfo, tab "در یک نگاه", the price box (آخرین معامله, قیمت
# پایانی, ...). Loaded with the page and polled every 4 to 5 seconds.
TSE_CLOSING_PRICE_INFO_URL = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{}"
)

# Live order book (best 5 bid and ask levels) of an instrument.
# Page: instInfo, tab "در یک نگاه", the order box (خرید / فروش). Polled
# together with TSE_CLOSING_PRICE_INFO_URL.
TSE_BEST_LIMITS_URL = "https://cdn.tsetmc.com/api/BestLimits/{}"

# Live individual/corporate (حقیقی / حقوقی) buy and sell totals of an
# instrument for the current day.
# Page: instInfo, tab "در یک نگاه", the "حقیقی / حقوقی" box. The page calls
# it with "/1/0" and polls it together with TSE_CLOSING_PRICE_INFO_URL.
TSE_CLIENT_TYPE_URL = (
    "https://cdn.tsetmc.com/api/ClientType/GetClientType/{}/1/0"
)

# NAV of an exchange traded fund (ETF): pRedTran is the redemption NAV
# (قیمت ابطال), pSubTran the subscription NAV (قیمت صدور). Returns HTTP 500
# for instruments that are not funds.
# Page: instInfo of a fund (e.g. ياقوت, 1438514795814416), tab
# "در یک نگاه", rows "NAV ابطال" and "زمان اعلام"; polled every 60 seconds.
# Funds are listed at home > tab "بورس اوراق بهادار تهران" >
# "صندوق های قابل معامله".
TSE_ETF_URL = "https://cdn.tsetmc.com/api/Fund/GetETFByInsCode/{}"

# Company introduction from codal (معرفی), includes financialYear
# (سال مالی) as "MM/DD". Takes the symbol (e.g. فولاد), not the insCode.
# Returns HTTP 500 for some funds.
# Page: instInfo, tab "معرفی".
TSE_TICKER_INTRODUCTION_URL = (
    "https://cdn.tsetmc.com/api/Codal/GetCodalPublisherBySymbol/{}"
)

# Daily history of individual/corporate (حقیقی / حقوقی) trades of an
# instrument, newest first.
# Page: instInfo, tab "حقیقی-حقوقی".
TSE_CLIENT_TYPE_DATA_URL = (
    "https://cdn.tsetmc.com/api/ClientType/GetClientTypeHistory/{}"
)

# Symbol search (جستجوی نماد). Returns every instrument (active and
# deleted/old, lastDate 1 or 0) whose symbol or name matches the query.
# Page: any page, top bar icon "جستجو" (search, shortcut "/"), then type
# at least 2 letters; sent on every key press.
TSE_SYMBOL_ID_URL = (
    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{}"
)

# All trades of an instrument in the current trading day.
# Page: instInfo, loaded with the page (intraday chart of tab
# "در یک نگاه", refreshed every 5 minutes). The same data is shown by the
# header button "اطلاعات تکمیلی" > "معاملات" > "ریز معاملات".
TSE_TRADE_DETAIL_URL = "https://cdn.tsetmc.com/api/Trade/GetTrade/{}"

# Latest list of major shareholders of an instrument.
# Page: instInfo, tab "سهامداران" (سهامداران/دارندگان در پایان روز).
TSE_SHAREHOLDERS_URL = (
    "https://cdn.tsetmc.com/api/Shareholder/GetInstrumentShareHolderLast/{}"
)

# Daily closing prices of every instrument for the last ~60 trading days
# (insCode, dEven, prices; about 55 MB, 5 MB gzipped). Unlike the market
# watch it also has instruments that are suspended (نماد متوقف), so it is
# used to find symbols the market watch does not show.
# Page: market watch, toolbar "تنظیمات دیده بان" > "اطلاعات تکمیلی" >
# button "تاریخچه قیمت ها"; also sent when a filter (فیلتر نویسی) that
# uses [ih] is applied.
CLOSING_PRICE_DAILY_ALL_INST_URL = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyAllInst"
)

# Every financial index of a market with its last value. The last path part
# is the flow (market): 1 for the stock exchange (بورس), 2 for fara bourse
# (فرابورس). The page calls it with "SelectedIndexes" for the short list
# and "All" for every index.
# Page: https://www.tsetmc.com/ (home), tab "در یک نگاه". In the
# "بورس اوراق بهادار تهران" box (flow 1) or the "فرابورس ایران" box
# (flow 2), click the "شاخص های منتخب" header; the window that opens lists
# every index of that market.
INDICES_LIST_URL = "https://cdn.tsetmc.com/api/Index/GetIndexB1LastAll/All/{}"

# Major shareholders of an instrument on a given day (before the session).
# Page: History, tab "در یک نگاه", box "سهامداران" (قبل از آغاز معاملات).
SYMBOL_DAY_INFO_SHAREHOLDERS_DATA = (
    "https://cdn.tsetmc.com/api/Shareholder/{index}/{date}"
)

# Instrument information (total shares, base volume...) on a given day.
# Page: History, loaded with the page (header of the page).
SYMBOL_DAY_INSTRUMENT_INFO_URL = (
    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentHistory/{index}/{date}"
)

# Statistics of every instrument (InstValue, the old آمارهای کلیدی): one
# row per instrument and statistic, dataType is the statistic id (see
# ticker_statisticals/key_stats.py), dataValue its value. About 28 MB.
# Page: no page sends it today. The site code has it for the market watch
# filters (getInstStatsForFilter) but the "آمارهای کلیدی" button of market
# watch > "تنظیمات دیده بان" > "اطلاعات تکمیلی" does not call it yet. The
# same statistics for one symbol are on instInfo, tab "آمارها"
# (MarketData/GetInstrumentStatistic/{insCode}).
KEY_STATS_URL = (
    "https://cdn.tsetmc.com/api/MarketData/GetInstValueAllInstAllParam"
)

# Market watch (دیده بان بازار): one row per instrument with prices,
# volumes, EPS, P/E, thresholds and the 5 best bid/ask levels (blDs).
# Page: market watch, loaded with the page. The page calls it with these
# parameters plus hEven=0&RefID=0, then polls it with the last hEven and
# RefID to get only the changes.
MARKET_WATCH_URL = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch"
    "?market=0&industrialGroup="
    "&paperTypes[0]=1&paperTypes[1]=2&paperTypes[2]=3&paperTypes[3]=4"
    "&paperTypes[4]=5&paperTypes[5]=6&paperTypes[6]=7&paperTypes[7]=8"
    "&paperTypes[8]=9&showTraded=false&withBestLimits=true"
)

# Order book (best limits) history of an instrument on a given day.
# Page: History, tab "در یک نگاه", box "خرید / فروش" that follows the time
# slider (زمان).
TICKER_ORDER_BOOK = "https://cdn.tsetmc.com/api/BestLimits/{index}/{date}"

# Every trade of an instrument on a given day, canceled ones included
# (canceled == 1). The last path part must be "false": with "true" (used by
# the chart of the page) the api returns only a part of the trades.
# Page: History, tab "معاملات" (trades, canceled ones are struck through).
TICKER_TRADE_DETAILS = (
    "https://cdn.tsetmc.com/api/Trade/GetTradeHistory/{index}/{date}/false"
)

# Individual/corporate (حقیقی / حقوقی) totals of every instrument for the
# current trading day.
# Page: market watch, toolbar "تنظیمات دیده بان" > "اطلاعات تکمیلی" >
# button "حقیقی و حقوقی"; also sent when a filter (فیلتر نویسی) that uses
# (ct) is applied.
CLIENT_TYPES_URL = "https://cdn.tsetmc.com/api/ClientType/GetClientTypeAll"

DATE_FORMAT = "%Y%m%d"
MIN_DATE = 20010321

# Headers sent with every API request; the API answers JSON to browser-like
# requests coming from the website.
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.tsetmc.com",
    "Referer": "https://www.tsetmc.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
}
