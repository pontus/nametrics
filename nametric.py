#!/usr/bin/env python3

import prometheus_client
import json
import yaml
import requests
import typing
import time
import logging
import logging.handlers

logger = logging.getLogger()
Gauge = prometheus_client.Gauge


class Token(typing.TypedDict):
    expire_at: float
    expire_in: float
    access_token: str


class Metrics(typing.TypedDict):
    nafirmware: Gauge
    nareachable: Gauge
    nabattery_vp: Gauge
    nabattery_percent: Gauge
    nawifi_status: Gauge
    narf_status: Gauge
    nalast_seen: Gauge
    narain: Gauge
    nanoise: Gauge
    nahumidity: Gauge
    naco2: Gauge
    natemperature: Gauge
    naguststrength: Gauge
    nawgustangle: Gauge
    napressure: Gauge
    naabsolutepressure: Gauge
    nawindstrength: Gauge
    nawindangle: Gauge

class Meter:
    token: typing.Union[Token, None] = None

    def __init__(self) -> None:
        with open("config.yaml") as f:
            self.naconfig = yaml.safe_load(f)

        self.get_netatmo_token()

        self.metrics = Metrics(
            nafirmware=Gauge("nafirmware", "Netatmo firmware reported", ["name", "id"]),
            nareachable=Gauge(
                "nareachable", "Netatmo device is reachable", ["name", "id"]
            ),
            nabattery_vp=Gauge(
                "nabattery_vp", "Netatmo reported battery level (vp)", ["name", "id"]
            ),
            nabattery_percent=Gauge(
                "nabattery_percent",
                "Netatmo reported battery level (percent)",
                ["name", "id"],
            ),
            nawifi_status=Gauge(
                "nawifi_status",
                "Netatmo reported wifi status",
                ["name", "id"],
            ),
            narf_status=Gauge(
                "narf_status", "Netatmo reported RF status", ["name", "id"]
            ),
            nalast_seen=Gauge(
                "nalast_seen", "Timestamp of device last seen", ["name", "id"]
            ),
            nawindstrength=Gauge(
                "nawindstrength", "Wind strength reported by Netatmo", ["name", "id"]
            ),
            nawindangle=Gauge(
                "nawindangle", "Wind angle reported by Netatmo", ["name", "id"]
            ),
            naguststrength=Gauge(
                "naguststrength", "Gust strength reported by Netatmo", ["name", "id"]
            ),
            nawgustangle=Gauge(
                "nagustangle", "Gust angle reported by Netatmo", ["name", "id"]
            ),
            narain=Gauge("narain", "Rain reported by by Netatmo", ["name", "id"]),
            nahumidity=Gauge(
                "nahumidity", "Humidity reported by by Netatmo", ["name", "id"]
            ),
            nanoise=Gauge("nanoise", "Noise reported by by Netatmo", ["name", "id"]),
            naco2=Gauge("naco2", "CO2 reported by by Netatmo", ["name", "id"]),
            natemperature=Gauge(
                "natemperature", "Temperature reported by by Netatmo", ["name", "id"]
            ),
            napressure=Gauge(
                "napressure", "Pressure reported by by Netatmo", ["name", "id"]
            ),
            naabsolutepressure=Gauge(
                "naabsolutepressure",
                "Absolute pressure reported by by Netatmo",
                ["name", "id"],
            ),
        )

    def refresh_all_meters(self) -> None:
        token = self.get_netatmo_token()
        r = requests.request(
            method="GET",
            url="https://api.netatmo.com/api/getstationsdata",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )

        if not r.ok:
            logger.error("Request to neatmo failed")
            return

        data = r.json()
        for p in data["body"]["devices"]:

            name = "Some module"
            if not "module_name" in p and "id" in p:
                name = "Id" + p["_id"]

            id = p["_id"]
            self.metrics["nalast_seen"].labels(name=name, id=id).set(
                p["last_status_store"]
            )
            self.metrics["nawifi_status"].labels(name=name, id=id).set(p["wifi_status"])
            self.metrics["nareachable"].labels(name=name, id=id).set(p["reachable"])

            if "dashboard_data" in p:
                d = p["dashboard_data"]

                self.metrics["nahumidity"].labels(name=name, id=id).set(d["Humidity"])
                self.metrics["natemperature"].labels(name=name, id=id).set(
                    d["Temperature"]
                )
                self.metrics["nanoise"].labels(name=name, id=id).set(d["Noise"])
                self.metrics["napressure"].labels(name=name, id=id).set(d["Pressure"])
                self.metrics["naabsolutepressure"].labels(name=name, id=id).set(
                    d["AbsolutePressure"]
                )
                self.metrics["naco2"].labels(name=name, id=id).set(d["CO2"])

            for m in p["modules"]:
                name = m["module_name"]
                id = m["_id"]

                self.metrics["nalast_seen"].labels(name=name, id=id).set(m["last_seen"])
                self.metrics["nareachable"].labels(name=name, id=id).set(m["reachable"])
                self.metrics["narf_status"].labels(name=name, id=id).set(m["rf_status"])
                self.metrics["nafirmware"].labels(name=name, id=id).set(m["firmware"])

                if not "dashboard_data" in m:
                    continue

                d = m["dashboard_data"]

                if "CO2" in d:
                    self.metrics["naco2"].labels(name=name, id=id).set(d["Humidity"])
                if "Humidity" in d:
                    self.metrics["nahumidity"].labels(name=name, id=id).set(
                        d["Humidity"]
                    )
                if "Temperature" in d:
                    self.metrics["natemperature"].labels(name=name, id=id).set(
                        d["Temperature"]
                    )
                if "Noise" in d:
                    self.metrics["nanoise"].labels(name=name, id=id).set(d["Noise"])
                if "Pressure" in d:
                    self.metrics["napressure"].labels(name=name, id=id).set(
                        d["Pressure"]
                    )
                if "AbsolutePressure" in d:
                    self.metrics["naabsolutepressure"].labels(name=name, id=id).set(
                        d["AbsolutePressure"]
                    )

    def get_netatmo_token(self) -> Token:
        if self.token and self.token["expire_at"] > time.time():
            return self.token

        t = time.time()

        d = {
            "grant_type": "refresh_token",
            "refresh_token": self.naconfig["refreshtoken"],
            "client_id": self.naconfig["clientid"],
            "client_secret": self.naconfig["clientsecret"],
        }

        r = requests.request(
            method="POST",
            url="https://api.netatmo.com/oauth2/token",
            headers={
                "Content-type": "application/x-www-form-urlencoded",
            },
            data=d,
        )

        if not r.ok:
            raise SystemError("Failed to refresh token")

        token: Token = r.json()
        token["expire_at"] = t + token["expire_in"]

        self.token = token
        return token


def setup_logger(
    console_level: int = logging.DEBUG,
    file_level: int = logging.DEBUG,
    filename: str = "nametrics.log",
) -> None:
    h = logging.StreamHandler()
    h.setLevel(console_level)
    logger.addHandler(h)
    f = logging.handlers.TimedRotatingFileHandler(
        filename, when="midnight", backupCount=30
    )
    f.setFormatter(logging.Formatter("{asctime} - {levelname} - {message}", style="{"))
    f.setLevel(file_level)
    logger.addHandler(f)

    logger.setLevel(min(file_level, console_level))


def serve() -> None:
    setup_logger()

    meter = Meter()
    prometheus_client.start_http_server(8012)
    meter.refresh_all_meters()

    while True:
        time.sleep(60)
        meter.refresh_all_meters()


if __name__ == "__main__":
    serve()
