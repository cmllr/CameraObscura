import requests
from core.logging import LogEntry, Webhook
from core.config import get_configuration_value


class Discord(Webhook):
    KNOWN_IPS_RUNTIME = {}
    def __init__(self, target) -> None:
        super().__init__(target)

    def do(self, entry: LogEntry):
        sensor_name = get_configuration_value("honeypot", "sensor")
        data = {"username": sensor_name}
        data["embeds"] = [
            {
                "description": entry.message,
                "title": entry.eventId,
                "color": 888164 if not entry.isError else 9243963
            }
        ]

        if entry.src_ip:
            # Recieve origin data
            # check if the origin data is already known
            origin_data = None
            was_cached = False
            if entry.src_ip in Discord.KNOWN_IPS_RUNTIME:
                was_cached = True
                origin_data = Discord.KNOWN_IPS_RUNTIME[entry.src_ip]
            else:
                got = requests.get(f"http://ip-api.com/json/{entry.src_ip}")
                if got.status_code != 200:
                    origin_data = f"API returned {got.status_code}."
                else:
                    api_response = got.json()
                    try:
                        origin_data = f"IP: {entry.src_ip}\nCountry: {api_response["country"]}\nRegion: {api_response["regionName"]}\nCity: {api_response["city"]}\nLat: {api_response["lat"]}\nLon: {api_response["lon"]}\nTimezone: {api_response["timezone"]}\nAS: {api_response["as"]}\nISP: {api_response["isp"]}"
                    except Exception as e:
                        origin_data = f"Exception while polling location {e}"

                Discord.KNOWN_IPS_RUNTIME[entry.src_ip] = origin_data

            data["embeds"].append( 
            {
                "title": "Origin" + (" (cached)" if was_cached else ""),
                "description": origin_data
            })

        result = requests.post(self._target, json=data)

        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            # silent fail
            pass
