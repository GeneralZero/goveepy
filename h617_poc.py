import asyncio
from bleak import BleakScanner, BleakClient

# UUIDs for the target device characteristics
NOTIFY_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"
WRITE_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
TARGET_NAME = "Govee_H617A"

scenes = {
    "Sunrise":      "00",
    "Sunset":       "01",
    "Nightlight":   "02",
    "Movie":        "04",
    "Dating":       "05",
    "Romantic":     "07",
    "Blinking":     "08",
    "Candlelight":  "09",
    "Snowflake":    "0f",
    "Illumination": "3f",
    "Cheerful":     "40",
}

#Commands for H617A
command_list = {
    #Write Commands
    "turn_on":        "330101",
    "turn_on2":       "3301ff",
    "turn_off":       "330100",
    "turn_off2":      "3301f0",

    "set_brightness": "3304", #01-64

    "set_scene": "330504", # Scene number
    "set_color": "33051501",  #00-Fe red, 00-Fe green, 00-Fe blue
    "set_music_mode": "3305130663",

    #"set_color":      "33050d", #00-Fe red, 00-Fe green, 00-Fe blue

    "set_auth":       "33b2",

    #Read Commands
    "is_on":                  "aa01", # Padding, checkbyte
    "get_brightness":         "aa04",
    "get_rgb":                "aa0501",
    "get_device_fw_version":  "aa06",
    "hw_version":             "aa0703",
    "get_auth_key":           "aab1",

    #Multi Command
    "getinfo":   "818a8b",
}

async def notification_handler(sender, data):
    """Callback for handling notifications."""
    hex_data = data.hex()
    resp = None
    current_command = "Unknown"

    for command, hex_info in command_list.items():
        if hex_data.startswith(hex_info):
            current_command = command
            resp = hex_data[len(hex_info):]
            break

    if current_command != "is_on":
        print(f"Notify[2b10]: {current_command} {resp}")

def finalze_message(message):
    #Do checksum math
    check = 0
    bmessage = bytearray.fromhex(message)

    for x in bmessage:
        check ^= int(x)

    #Pad Data untill its 19 bytes lone
    return bmessage.ljust(19, b"\x00") + check.to_bytes(1, 'little')

def segemnts2num(seg_array):
    out = 0
    #Set Segments by Binary

    for x in seg_array:
        out |= (1 << x)

    return (out & 0xff7f).to_bytes(2, 'little').hex()


async def write_loop(client, timeout=2):
    """Send data to the write characteristic every 2 seconds."""
    while client.is_connected :
        try:
            await client.write_gatt_char(WRITE_UUID, finalze_message(command_list["is_on"]))
            #print(f"Sending Keep Alive payload to {WRITE_UUID}: {KEEP_ALIVE_MESSAGE}")
        except Exception as e:
            print(f"Error sending Keep Alive payload: {e}")
            break
        await asyncio.sleep(timeout)

async def write_and_read(client, data):
    try:
        full_message = finalze_message(data)
        # Write the payload to the characteristic
        print(f"TX[2b11]: {full_message.hex()}")
        await client.write_gatt_char(WRITE_UUID, full_message)

        #response = await client.read_gatt_char(WRITE_UUID)
        #print(f"RX[2b11] data: {response.hex()}")
        #return response
    except Exception as e:
        print(f"Error in write_and_read: {e}")
        #return None

async def bruteforce_commands(start1=0, end1=256, start2=0, end2=256):
	## 33ff Unknown Empty Response
	
	#66 Unknown Empty Response
	#aa04
	#aa05
	#aa06
	#aa0e
	#aa0f
	#aa11
	#aa12
	#aa23
	#aa40
	#aaa3
	#aaa5
	#aab1
	#aac0
	#...

	#b000 - b00f  Unknown Empty Response
	#b040 - b04f  Unknown Empty Response
	#b0c0 - b0cf  Unknown Empty Response

	#b300,b304,b308  Unknown Empty Response
	#b340,b344,b348,b34c  Unknown Empty Response
	#b380,b384,b388,b38c  Unknown Empty Response
	#b3c0,b3c4,b3c8,b3cc  Unknown Empty Response

	#b400,b401,b402,b403,b408,b409,b40a,b40b Unknown Empty Response
	#b440,b441,b442,b443,b448,b449,b44a,b44b Unknown Empty Response
	#b480,b481,b482,b483,b488,b489,b48a,b48b Unknown Empty Response
	#b4c0,b4c1,b4c2,b4c3,b4c8,b4c9,b4ca,b4cb Unknown Empty Response

	#start = bytearray.fromhex("ff")[0]

	for x in range(start1, end1):
		for y in range(start2, end2):
			await asyncio.sleep(sleep_time)
			await write_and_read(client, f"{x.to_bytes(1, 'little').hex()}{y.to_bytes(1, 'little').hex()}")

async def find_and_subscribe():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()

    # Search for the target device
    target_device = next((d for d in devices if TARGET_NAME in d.name), None)

    if not target_device:
        print(f"No device found with name containing '{TARGET_NAME}'")
        return

    #print(target_device)

    async with BleakClient(target_device.address, timeout=30) as client:
        try:
            print(f"Connected to {target_device.name} ({target_device.address})")

            # Check if the notify characteristic exists
            services = client.services

            # Correct way to get characteristics
            characteristics = []
            for service in services:
                characteristics.extend(service.characteristics)

            # Check for required characteristics
            characteristic_uuids = [char.uuid for char in characteristics]
            if NOTIFY_UUID not in characteristic_uuids or WRITE_UUID not in characteristic_uuids:
                print(f"Required characteristics not found in device services.")
                return

            # Subscribe to notifications
            print(f"Subscribing to notifications on {NOTIFY_UUID}...")
            await client.start_notify(NOTIFY_UUID, notification_handler)

            # Start write loop in parallel
            print(f"Starting Keep Alive Loop to {WRITE_UUID}...")
            write_task = asyncio.create_task(write_loop(client))

            await write_and_read(client, command_list["get_brightness"])
            await write_and_read(client, command_list["set_brightness"] + "01")
            #await write_and_read(client, command_list["set_scene"] + scenes["Romantic"])
            #33 051501 6496c8 0000000000 3200 00000000002a
            #          RRGGBB            SEG
            #                            ff7f = all segments

            # sleep_time = 5
            # await asyncio.sleep(sleep_time)
            # await asyncio.sleep(sleep_time)
            # #Set all to white
            # await write_and_read(client, command_list["set_color"] + "FFFFFF" + "0000000000" + "ff7f")
            # #Set 0th segment of 6 LEDs to red
            # await asyncio.sleep(sleep_time)
            # await write_and_read(client, command_list["set_color"] + "FF0000" + "0000000000" + segemnts2num([0]))
            # await asyncio.sleep(sleep_time)
            # #Set 1th and last segment of 6 LEDs to green
            # await write_and_read(client, command_list["set_color"] + "00FF00" + "0000000000" + segemnts2num([1,14]))
            # await asyncio.sleep(sleep_time)
            sleep_time = 2




            print("Running. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("Stopping...")
        except Exception as e:
            print(f"Error during operation: {e}")
        finally:
            print("Cleaning up...")
            if client.is_connected:
                try:
                    await client.stop_notify(NOTIFY_UUID)
                except Exception as e:
                    print(f"Error stopping notifications: {e}")
            print("Disconnected.")

# Run the async function
try:
    asyncio.run(find_and_subscribe())
except KeyboardInterrupt:
    print("Program stopped by user.")
