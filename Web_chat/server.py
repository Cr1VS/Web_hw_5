from datetime import datetime, timedelta
from CustomLogger import CustomLogger
import asyncio
import logging


from websockets.exceptions import ConnectionClosedOK
from websockets import WebSocketServerProtocol
from aiofile import async_open
from aiopath import AsyncPath
import websockets
import aiohttp
import names


DEFAULT_EXCHANGE_RATES = ["USD", "EUR"]


logger = CustomLogger("Error.log")


class HttpError(Exception):
    pass


async def logging_request():
    apath = AsyncPath("log.txt")
    date = datetime.now().strftime("%d.%m.%Y")

    parametr = "a" if await apath.exists() else "w"
    async with async_open(apath, parametr) as afp:
        await afp.write(f"{date} - command exchange was executed\n")


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


async def asunc_requests() -> None:
    """
    The asunc_requests function for processing.

    Parameters:
    - days_ago (int): Number of days ago for which to retrieve exchange rates.
    """

    tasks: list[asyncio.Task] = []
    for day in range(3, -1, -1):
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
        return results
    except HttpError as e:
        logger.log(e, level=logging.ERROR)
        return None


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


async def get_exchange():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    logger.log(f"Exited with code: {response.status} on p24api.")
        except:
            logger.log(
                f"Exited with code: {response.status} on p24api.", level=logging.ERROR
            )


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logger.log(f"{ws.remote_address} connects")

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logger.log(f"{ws.remote_address} disconnects")

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message == "exchange":
                await logging_request()
                exchange = await get_exchange()
                for item in exchange:
                    await self.send_to_clients(
                        f"{item['ccy']} to {item['base_ccy']}: Buy - {item['buy']}, Sale - {item['sale']}"
                    )

            elif message == "exchange 2":
                await logging_request()

                try:
                    result = await asunc_requests()
                    for item in result:
                        for date, currency in item.items():
                            await self.send_to_clients(f"Date: {date}")
                            for currency, rate in currency.items():
                                await self.send_to_clients(
                                    f"{currency}: Sale - {rate['Sale']}, Buy - {rate['Buy']}"
                                )
                except Exception as ex:
                    await self.send_to_clients(ex)
            else:
                await self.send_to_clients(f"{ws.name}: {message}")


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, "localhost", 8080):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
