import logging
import random
from datetime import datetime
from pytz import timezone

import kronos
import requests as requests

from pseparser import utils
from pseparser.models import Company, Sector, Subsector, Index, StockPrice

COMPANY_LISTING_URL = "http://www.pse.com.ph/stockMarket/companyInfoSecurityProfile.html?method=getListedRecords&common=no&ajax=true"
STOCK_PRICES_URL = "http://pse.com.ph/stockMarket/home.html?method=getSecuritiesAndIndicesForPublic&ajax=true"
SECTOR_LISTING_URL = "http://www.pse.com.ph/stockMarket/companyInfoSecurityProfile.html?method=getSectors&ajax=true"
SUBSECTOR_LISTING_URL = "http://www.pse.com.ph/stockMarket/companyInfoSecurityProfile.html?method=getSubsectors&ajax=true"
COMPANY_EXTRA_INFO_URL = "http://www.pse.com.ph/stockMarket/companyInfo.html?method=getSecuritiesByCompany&ajax=true&company=%s&security=%s"
COMPANY_EXTRA_PRICES_URL = "http://www.pse.com.ph/stockMarket/companyInfo.html?method=fetchHeaderData&ajax=true&company=%s&security=%s"

LOGGER = logging.getLogger(__name__)


@kronos.register('0 0 * * *')
def complain():
    complaints = [
        "I forgot to migrate our applications's cron jobs to our new server! Darn!",
        "I'm out of complaints! Damnit!"
    ]

    print(random.choice(complaints))
    LOGGER.info("[INFO]" + random.choice(complaints))
    LOGGER.debug("[DEBUG]" + random.choice(complaints))
    LOGGER.error("[ERROR]" + random.choice(complaints))


@kronos.register('31 9 * * *')
def run_initial():
    fetch_stocks()
    fetch_companies()
    fetch_companies_extra_info()
    fetch_sectors()
    fetch_subsectors()
    return


@kronos.register('*/1 9-16 * * *')
def fetch_stocks():
    STOCK_PRICES = "http://phisix-api2.appspot.com/stocks.json"

    STOCK_PRICES2 = "http://api.pse.tools/api/stocks"
    response = requests.get(STOCK_PRICES2)
    json_response = response.json()
    list_length = len(json_response)

    indices = Index.objects.all()
    stocks = json_response['data']

    datetime = json_response['timestamp'].split(" ")


    # response = requests.get(STOCK_PRICES)
    # json_response = response.json()
    # list_length = len(json_response)

    # indices = Index.objects.all()

    # stocks = json_response['stock']
    # datetime = json_response['as_of'].split("T")
    date = datetime[0]

    # for stock in stocks:
    #     symbol = stock['symbol']
    #     volume = stock['volume']
    #     percent_change = stock['percent_change'] 

    #     if percent_change > 0:
    #         indicator="U"
    #     elif percent_change < 0:
    #         indicator="D"
    #     else:
    #         indicator="N"

    #     for index in indices:
    #         if index.security_symbol == symbol:
    #             index.total_volume = volume
    #             index.percentage_change_close = percent_change
    #             index.indicator = indicator

    #             index.save()
    #             LOGGER.info("updating index")



    for stock in stocks:
        symbol = stock['symbol']
        
        open_price = stock['open']
        high_price = stock['high']
        low_price = stock['low']

        last_price = stock['last']
        percent_change = float(stock['change'])
        volume = stock['volume']
        company = Company.objects.filter(symbol=symbol).first()

        if company is not None:

            stockpricetoday = StockPrice.objects.filter(company=company, date_details=date).first()

            if percent_change > 0:
                indicator="U"
            elif percent_change < 0:
                indicator="D"
            else:
                indicator="N"

            if stockpricetoday is None:

                StockPrice.objects.create(
                    company=company,
                    date_details=date,
                    open_price = open_price,
                    low_price = low_price,
                    high_price = high_price,
                    indicator = indicator,
                    percentage_change_close = percent_change,
                    total_volume = volume,
                    last_traded_price = last_price
                )

                print ("adding new date for")

            else:
                stockpricetoday.total_volume = volume
                stockpricetoday.indicator = indicator
                stockpricetoday.last_traded_price = last_price
                stockpricetoday.percentage_change_close = percent_change

                stockpricetoday.low_price = low_price
                stockpricetoday.high_price = high_price
                

                LOGGER.info("updating price")

                print ("updating")


                stockpricetoday.save()

    # for stock in stocks:
    #     symbol = stock['symbol']
    #     price = stock['price']
    #     price_amount = price['amount']
    #     percent_change = stock['percent_change'] 
    #     volume = stock['volume']
    #     company = Company.objects.filter(symbol=symbol).first()

    #     print (symbol)
    #     if company is not None:

    #         stockpricetoday = StockPrice.objects.filter(company=company, date_details=date).first()

    #         if percent_change > 0:
    #             indicator="U"
    #         elif percent_change < 0:
    #             indicator="D"
    #         else:
    #             indicator="N"

    #         if stockpricetoday is None:

    #             StockPrice.objects.create(
    #                 company=company,
    #                 date_details=date,
    #                 open_price = price_amount,
    #                 low_price = price_amount,
    #                 high_price = price_amount,
    #                 indicator = indicator,
    #                 percentage_change_close = percent_change,
    #                 total_volume = volume,
    #                 last_traded_price = price_amount
    #             )

    #             print ("adding new date")
    #             LOGGER.info("adding new date")

    #         else:

    #             print ("updating stockprices")

    #             stockpricetoday.total_volume = volume
    #             stockpricetoday.indicator = indicator
    #             stockpricetoday.last_traded_price = price_amount
    #             stockpricetoday.percentage_change_close = percent_change

    #             previous_low = float(stockpricetoday.low_price)
    #             previous_high = float(stockpricetoday.high_price)
    #             compare = float(price_amount)

    #             if compare < previous_low:
    #                 stockpricetoday.low_price = price_amount
    #             else:
    #                 print ("no new low")

    #             if compare > previous_high:
    #                 stockpricetoday.previous_high = price_amount
    #             else:
    #                 print ("no new high")

    #             LOGGER.info("updating price")


    #             stockpricetoday.save()


@kronos.register('1 9 * * *')
def fetch_companies():
    response = requests.get(COMPANY_LISTING_URL)
    json_response = response.json()
    count = json_response['count']
    company_records = json_response['records']

    for record in company_records:
        symbol = record['securitySymbol']
        company = Company.objects.filter(symbol=symbol).first()
        if company is None:
            LOGGER.info("creating company with alias: %s " % (symbol))
            try:
                Company.objects.create(
                    symbol=symbol,
                    symbol_id=record['securitySymbolId'],
                    company_id=record['companyId'],
                    security_name=record['securityName'],
                    company_name=record['companyName'],
                    security_status=record['securityStatus'],
                    listing_date=utils.get_datetime_companylistingjson(record['listingDate']),
                    security_type=record['securityType'],
                    subsector=record['subsectorName'],
                )
            except Exception:
                LOGGER.exception("Cannot create company due to SYMBOL conflict")
                symbol_id = record['securitySymbolId']
                company = Company.objects.filter(symbol_id=symbol_id).first()
                LOGGER.info("updating symbol Id of company: " + company.company_name)
                if company is not None:
                    company.symbol = record['securitySymbol']
                    company.company_name = record['companyName']
                    company.security_name = record['securityName']
                    company.save()
                else:
                    LOGGER.error("Error updating")
                pass
        else:
            LOGGER.info("company already exist [%s]" % (symbol))


@kronos.register('0 0 * * *')
def fetch_companies_extra_info():
    companies = Company.objects.all()

    for company in companies:
        response = requests.get(COMPANY_EXTRA_INFO_URL % (company.company_id, company.symbol_id))
        try:
            data = response.json()['records'][0]
            LOGGER.info("Updating info for company: %s" % (company.company_name))
        except IndexError:
            LOGGER.exception("No data found for company: %s" % (company.company_name))
            continue
        except Exception:
            LOGGER.exception("unknown error for company: %s" % (company.company_name))
            continue
        try:
            # print('foreign_limit', end=" ")
            company.foreign_limit = data['foreignLimit']
            company.save()
            # print('OK')
        except Exception as e:
            # print('FAIL')
            # print("unknown error:", e, "for company", company.company_name)
            pass
        try:
            # print('listed_shares', end=" ")
            company.listed_shares = data['listedShares']
            company.save()
            # print('OK')
        except Exception as e:
            # print('FAIL')
            # print("unknown error:", e, "for company", company.company_name)
            pass
        try:
            # print('free_float_level', end=" ")
            company.free_float_level = data['freeFloatLevel']
            company.save()
            # print('OK')
        except Exception as e:
            # print('FAIL')
            # print("unknown error:", e, "for company", company.company_name)
            pass
        try:
            # print('security_ISIN', end=" ")
            company.security_ISIN = data['securityISIN']
            company.save()
            # print('OK')
        except Exception as e:
            # print('FAIL')
            # print("unknown error:", e, "for company", company.company_name)
            pass
        try:
            # print('par_value', end=" ")
            company.par_value = data['parValue']
            company.save()
            # print('OK')
        except Exception as e:
            # print('FAIL')
            # print("unknown error:", e, "for company", company.company_name)
            pass
        try:
            # print('board_lot', end=" ")
            company.board_lot = data['boardLot']
            company.save()
            # print('OK')
        except Exception as e:
            # print('FAIL')
            # print("unknown error:", e, "for company", company.company_name)
            pass
        try:
            # print('outstanding_shares', end=" ")
            company.outstanding_shares = data['outstandingShares']
            company.save()
            # print('OK')
        except Exception as e:
            # print('FAIL')
            # print("unknown error:", e, "for company", company.company_name)
            pass
            # foreignLimit
            # listedShares
            # freeFloatLevel
            # securityISIN
            # parValue
            # boardLot
            # outstandingShares


@kronos.register('0 0 * * *')
def fetch_sectors_and_subsectors():
    fetch_sectors()
    fetch_subsectors()
    return


def fetch_sectors():
    response = requests.get(SECTOR_LISTING_URL)
    json_response = response.json()
    count = json_response['count']
    sector_listing = json_response['records']

    for sector in sector_listing:
        id_index = sector['indexId']
        if Sector.objects.filter(id_index=id_index).first() is None:
            LOGGER.info("Creating sector with index id: %s" % (id_index))
            Sector.objects.create(
                id_index=id_index,
                is_sectoral=(sector['isSectoral'] == "Y"),
                sort_order=sector['sortOrder'],
                name=sector['indexName'],
                abbreviation=sector['indexAbb']
            )
        else:
            LOGGER.info("sector already exists with index id: %s" % (id_index))


def fetch_subsectors():
    response = requests.get(SUBSECTOR_LISTING_URL)
    json_response = response.json()
    count = json_response['count']
    subsector_listing = json_response['records']

    for subsector in subsector_listing:
        id = subsector['subsectorID']
        if Subsector.objects.filter(id=id).first() is None:
            LOGGER.info("Creating subsector with index id: %s" % (id))
            subsector_new = Subsector.objects.create(
                id=id,
                name=subsector['subsectorName']
            )

            try:
                id_index = subsector['indexId']
                subsector_new.sector = Sector.objects.filter(id_index=subsector['indexId']).first()
                subsector_new.save()
            except KeyError:
                LOGGER.info("No index Id was found for subsector with id: %s" % (id))

        else:
            LOGGER.info("subsector already exists with index id: %s" % (id))
