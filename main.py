from datetime import datetime, timedelta
from Web_chat.CustomLogger import CustomLogger
import platform
import argparse
import logging
import asyncio
import json


from aiofile import async_open
import aiohttp


DEFAULT_EXCHANGE_RATES = ["USD", "EUR"]


logger = CustomLogger("Error.log")


parser = argparse.ArgumentParser(description="Currency_Info")
parser.add_argument("--days", "-d", help="Days ago", required=True)
parser.add_argument(
    "--addCurrency",
    "-c",
    help="Add one more currency to the final list (comma-separated). Example USD,EUR,KZT,CAD,CNY",
    default=None,
)


logger.log(parser.parse_args())
args = vars(parser.parse_args())
logger.log(args)
days_ago = args.get("days")


try:
    added_currencies = args.get("addCurrency")
    if added_currencies:
        added_currencies = added_currencies.split(",")
        added_currencies = [currency.upper() for currency in added_currencies]
        DEFAULT_EXCHANGE_RATES.extend(added_currencies)
        logger.log(added_currencies)
except Exception as ex:
    logger.log(ex, level=logging.ERROR)


class HttpError(Exception):
    pass


async def parsing_data(data: dict, date: str) -> dict:
    """
    Parse the exchange rate data and return a dictionary.

    Parameters:
    - data (dict): Raw exchange rate data.
    - date (str): Date of the exchange rates.

    Returns:
    dict: Parsed exchange rates.
    """
    await asyncio.sleep(0)

    data_exchange_rates = {}

    for exchange_rate in data.get("exchangeRate", []):
        if exchange_rate["currency"] in DEFAULT_EXCHANGE_RATES:
            currency: str = exchange_rate["currency"]
            sale_rate: float = exchange_rate.get("saleRate", 0.0)
            purchase_rate: float = exchange_rate.get("purchaseRate", 0.0)

            existing_date_entry: dict = data_exchange_rates.get(date, {})
            existing_date_entry[currency] = {"Sale": sale_rate, "Buy": purchase_rate}
            data_exchange_rates[date] = existing_date_entry

    return data_exchange_rates


async def request_to(url: str = None, date: str = None) -> dict:
    """
    Make an asynchronous HTTP request.

    Parameters:
    - url (str): URL for the HTTP request.
    - date (str): Date for which to retrieve exchange rates.

    Returns:
    dict: Parsed exchange rates.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return await parsing_data(result, date)
                else:
                    raise HttpError(
                        f"Error code raised: {response.status} on url: {url}"
                    )
        except aiohttp.ClientConnectorError as e:
            raise HttpError(f"Connection error: {url}", {e})
        except aiohttp.InvalidURL as e:
            raise HttpError(f"Invalid URL: {url}", {e})


async def main(days_ago: int) -> None:
    """
    The main function for processing.

    Parameters:
    - days_ago (int): Number of days ago for which to retrieve exchange rates.
    """
    if days_ago > 10:
        logger.log(
            f"Entered days - {days_ago}.\nSorry but script can only provide data not more than 10 days ago."
        )
        days_ago = 0

    tasks: list[asyncio.Task] = []
    for day in range(days_ago, -1, -1):
        date: str = (datetime.now() - timedelta(days=day)).strftime("%d.%m.%Y")
        task: asyncio.Task = asyncio.create_task(
            request_to(
                f"https://api.privatbank.ua/p24api/exchange_rates?json&date={date}",
                date,
            )
        )
        tasks.append(task)

    try:
        results: list[dict] = await asyncio.gather(*tasks)
        async with async_open("data.json", "w+", encoding="utf-8") as afh:
            await afh.write(json.dumps(results, indent=4))
    except HttpError as e:
        logger.log(e, level=logging.ERROR)
        return None


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        args = parser.parse_args()
        logger.log(args)
        asyncio.run(main(int(args.days)))
    except ValueError:
        logger.log(
            f"Not valid entered data <{args.days}>. You must enter a number. Try again later!"
        )
    except Exception as e:
        logger.log(f"An unexpected error occurred: {e}", level=logging.ERROR)
