import logging
import asyncio
import time
from websockets import client
from websockets.typing import Data
from protocol.TileMapUpdate import TileMapUpdate

# Constants
NUM_WORKERS = 2  # Number of workers to create
NUM_CONNECTIONS_PER_WORKER = 100  # Number of connections per worker
DURATION = 3  # Duration of the stress test in seconds
SLEEP_TIME = 0.1  # Sleep time between each message in seconds
TILE_X = 1000

# WebSocket server URL
SERVER_URL = "ws://localhost:8081/tile"

# Performance measurement variables
stop = False

msg_dict = []
def find_byte_sequence(arr, sequence):
    import numpy as np
    arr_bytes = arr.astype(np.uint8).tobytes()
    index = arr_bytes.find(sequence)
    return index 

async def worker(worker_id, msg):
    import random
    import datetime
    start = datetime.datetime.now()
    # 16mb frames
    connection = await client.connect(SERVER_URL, max_size=2**24)

    check = []
    while True:
        if (datetime.datetime.now() - start).total_seconds() * 1000 >= DURATION * 1000:
            await connection.close()
            return
        send, to_check = msg[random.randint(0, len(msg) - 1)]
        print("send", send)
        await connection.send(send)
        check.append(to_check)
        check[-1]["acked"] = False
        recv_data = await connection.recv()
        # TODO: Better acking
        if isinstance(recv_data, str):
            # set last check item to acked, not well impl
            check[-1]["acked"] = True 
            print(recv_data)
        elif isinstance(recv_data, bytes):
            # check the data is correct, take x * y as offset and check for 4
            # bytes matching the color
            print("recveid bytes")
            tile = TileMapUpdate.GetRootAsTileMapUpdate(recv_data, 0)
            tile_map = tile.TilesAsNumpy()
            print(f"Recieved {tile.X()}: {tile.Y()} tile, tile size {tile_map.shape}")
            for check_tile in check:
                if check_tile["acked"] == False:
                    continue
                # offset in bytes
                offset = (check_tile["x"] + (check_tile["y"] * TILE_X)) * 4
                byte_data = check_tile["color"].to_bytes(4, byteorder="little")
                found_in = find_byte_sequence(tile_map, byte_data)

                if found_in != offset:
                    print("Data mismatch")
                    print(f"Expected {byte_data} at {check_tile['x']}, {check_tile['y']}(offset {offset})")
                    print(f"Received {tile_map[offset:offset + 4]}")
                    print(f"but found at {found_in}")
                    # find byte_data in recv_data
                    await connection.close()
                    return
            check = []
        else:
            print("Unknown data type")

        await asyncio.sleep(SLEEP_TIME)


def random_msg():
    """adds random messages to the msg_dict in JSON {x: int, y: int, color: int} format"""
    import random
    import json
    global msg_dict
    msg_dict=[]
    for _i in range(10000):
        x=random.randint(0, 999)
        y=random.randint(0, 999)
        color=random.randint(0, 10000)
        msg_dict.append(
            (json.dumps({"x": x, "y": y,
                         "color": color}),
             {"x": x, "y": y, "color": color}
             )
        )


def coroutine(i, msg):
    asyncio.run(worker(i, msg))


def main():
    global msg_dict
    random_msg()
    coroutine(0, msg_dict)


if __name__ == "__main__":
    logging.basicConfig(
        format = "%(asctime)s %(message)s",
        level = logging.INFO,
    )
    main()