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
        data["embeds"] = []

        try:
            field_data = []
            if entry.src_ip:
                # Recieve origin data
                # check if the origin data is already known
                if entry.src_ip in Discord.KNOWN_IPS_RUNTIME:
                    field_data = Discord.KNOWN_IPS_RUNTIME[entry.src_ip]
                else:
                    got = requests.get(f"http://ip-api.com/json/{entry.src_ip}")

                    if got.status_code != 200 or got.json()["status"] == "fail":
                        field_data = [
                            {
                                "name": f"API returned error",
                                "value": f"Something went wrong. Status Code was {got.status_code}",
                            }
                        ]
                    else:
                        api_response = got.json()

                        field_data = []
                        field_keys = {
                            "Country": "country",
                            "Region": "regionName",
                            "City": "city",
                            "Lat": "lat",
                            "Lon": "lon",
                            "AS": "as",
                            "ISP": "isp",
                        }
                        debug = bool(str(get_configuration_value("honeypot", "debug")))
                        if debug:
                            field_data.append(
                                {
                                    "value": "THE IP IS RANDOM",
                                    "name": "IN DEBUG MODE"
                                }
                            )
                        for key, value in field_keys.items():
                            field_data.append(
                                {"name": key, "value": f"{api_response[value]}"}
                            )
                        Discord.KNOWN_IPS_RUNTIME[entry.src_ip] = field_data
            data["embeds"].append(
                {
                    "title": entry.eventId,
                    "description": f"{entry.message}",
                    "color": 888164 if not entry.isError else 9243963,
                    "fields": field_data,  # type: ignore
                }
            )

            result = requests.post(self._target, json=data)
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            # silent fail
            pass
