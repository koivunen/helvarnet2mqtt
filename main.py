#!/usr/bin/env python3

"""Queries all devices for their inputs,
    and starts polling the devices that had inputs,
    then publishes input state changes to MQTT.

WARNING: Polling happens every second for every device
    so it may slow down the router or do other unwanted things
    if ran on a large installation!
"""

import asyncio
import json
import os
from datetime import datetime, timezone

import aiohelvar.exceptions
import aiomqtt
import structlog
from aiodebug.log_slow_callbacks import enable as enable_slow_callbacks
from aiohelvar.router import Router
from dotenv import load_dotenv

load_dotenv()

POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2.0"))
ROUTER_IP = os.getenv("ROUTER_IP", "10.254.1.1")
ROUTER_PORT = int(os.getenv("ROUTER_PORT", "50000"))
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_PREFIX = os.getenv("MQTT_PREFIX", "helvar")

logger = structlog.get_logger()


async def polling_loop(
    mqtt_client: aiomqtt.Client,
    router: Router,
    device_state: dict,
) -> None:
    loop = asyncio.get_running_loop()
    while True:
        device_state_loop = list(device_state.items())
        count = len(device_state_loop)

        if count == 0:
            logger.warning("no_queryable_devices")
            return

        interval = POLL_INTERVAL / count
        start_time = loop.time()

        for i, (device, state) in enumerate(device_state_loop):
            try:
                new_state = await router.devices.query_inputs(device)
                if new_state != state:
                    topic = f"{MQTT_PREFIX}/device/{device.address}/input"
                    payload = json.dumps(
                        {
                            "device": device.name,
                            "address": device.address,
                            "new_state": str(new_state),
                            "old_state": str(state),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    await mqtt_client.publish(topic, payload)
                    logger.info(
                        "input_state_changed",
                        device=device.name,
                        address=device.address,
                        new_state=str(new_state),
                        old_state=str(state),
                    )
                    device_state[device] = new_state
            except aiohelvar.exceptions.PropertyDoesNotExistError:
                logger.warning(
                    "device_lost_queryable_inputs",
                    device=device.name,
                )
                device_state.pop(device, None)

            next_start = start_time + ((i + 1) * interval)
            now = loop.time()
            delay = next_start - now
            if delay > 0:
                await asyncio.sleep(delay)



async def main() -> None:
    enable_slow_callbacks(slow_duration=0.1)

    logger.info("connecting_to_mqtt", broker=MQTT_BROKER, port=MQTT_PORT)
    async with aiomqtt.Client(
        MQTT_BROKER,
        port=MQTT_PORT,
        username=MQTT_USERNAME if MQTT_USERNAME else None,
        password=MQTT_PASSWORD if MQTT_PASSWORD else None,
    ) as mqtt_client:
        logger.info("connected_to_mqtt_broker")

        logger.info("connecting_to_router", address=ROUTER_IP)
        router = Router(ROUTER_IP, ROUTER_PORT)
        await router.connect()
        logger.info("connected_to_router", workgroup=router.workgroup_name)

        await router.initialize()

        logger.info("router_initialized", device_count=len(router.devices.devices))
        await asyncio.sleep(1)

        devices_with_type = [d for d in router.devices.devices.values() if d.type]

        logger.info("querying_inputs", device_count=len(devices_with_type))
        device_state = {}
        for device in router.devices.devices.values():
            if not device.type:
                continue

            logger.info("querying_device", device=device.name, device_type=device.type)

            try:
                response = await router.devices.query_inputs(device)
                if response:
                    logger.info(
                        "device_query_response",
                        device=device.name,
                        response=str(response),
                    )
                    device_state[device] = response
                else:
                    logger.warning("device_no_response", device=device.name)
            except aiohelvar.exceptions.PropertyDoesNotExistError:
                logger.info("device_query_not_applicable", device=device.name)

        logger.info(
            "starting_polling",
            queryable_devices=len(device_state),
            poll_interval=POLL_INTERVAL,
        )

        async with asyncio.TaskGroup() as tg:
            tg.create_task(polling_loop(mqtt_client, router, device_state))


asyncio.run(main())
