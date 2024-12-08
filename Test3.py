import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

async def connect_to_wss(socks5_proxy, user_id):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Generated Device ID: {device_id}")

    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            
            custom_headers = {"User-Agent": random_user_agent}
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname, extra_headers=custom_headers) as websocket:

                async def send_ping():
                    while True:
                        try:
                            if websocket.open:
                                send_message = json.dumps(
                                    {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                                logger.debug(f"Sending PING: {send_message}")
                                await websocket.send(send_message)
                            await asyncio.sleep(5)  # Interval between pings
                        except websockets.exceptions.ConnectionClosedError as e:
                            logger.error(f"WebSocket connection closed during PING: {e}")
                            break
                        except Exception as e:
                            logger.error(f"Unexpected error in send_ping: {e}")
                            break

                # Start the ping task in the background
                asyncio.create_task(send_ping())

                while True:
                    try:
                        response = await websocket.recv()
                        message = json.loads(response)
                        logger.info(f"Received message: {message}")

                        if message.get("action") == "AUTH":
                            auth_response = {
                                "id": message["id"],
                                "origin_action": "AUTH",
                                "result": {
                                    "browser_id": device_id,
                                    "user_id": user_id,
                                    "user_agent": custom_headers['User-Agent'],
                                    "timestamp": int(time.time()),
                                    "device_type": "desktop",
                                    "version": "4.29.0",
                                }
                            }
                            logger.debug(f"Sending AUTH response: {auth_response}")
                            await websocket.send(json.dumps(auth_response))

                        elif message.get("action") == "PONG":
                            pong_response = {"id": message["id"], "origin_action": "PONG"}
                            logger.debug(f"Sending PONG response: {pong_response}")
                            await websocket.send(json.dumps(pong_response))

                    except websockets.exceptions.ConnectionClosedError as e:
                        logger.error(f"Connection closed unexpectedly: {e}")
                        break
                    except Exception as e:
                        logger.error(f"Unexpected error in WebSocket loop: {e}")
                        break
        except Exception as e:
            logger.error(f"Error with proxy {socks5_proxy}: {e}")
            await asyncio.sleep(5)  # Reconnect delay

async def main():
    _user_id = input('Please Enter your user ID: ')
    try:
        with open('proxies.txt', 'r') as file:
            proxies = file.read().splitlines()

        tasks = [asyncio.create_task(connect_to_wss(proxy, _user_id)) for proxy in proxies]
        await asyncio.gather(*tasks)

    except FileNotFoundError:
        logger.error("The 'proxies.txt' file was not found.")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")

if __name__ == '__main__':
    asyncio.run(main())
