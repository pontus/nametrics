#!/usr/bin/env python3

import prometheus_client
import json
import yaml
import requests
import typing
import time


class Meter:
    metrics : typing.Dict = {}
    token : typing.Union[typing.Dict,None]= None

    def __init__(self):
        with open("config.yaml") as f:
            self.naconfig = yaml.safe_load(f)

        self.get_netatmo_token()

        metrics = self.metrics

        metrics["nafirmware"] = prometheus_client.Gauge(
            "nafirmware", "Netatmo firmware reported", ["name", "id"]
        )

        metrics["nareachable"] = prometheus_client.Gauge(
            "nareachable", "Netatmo device is reachable", ["name", "id"]
        )
        metrics["nabattery_vp"] = prometheus_client.Gauge(
            "nabattery_vp", "Netatmo reported battery level (vp)", ["name", "id"]
        )
        metrics["nabattery_percent"] = prometheus_client.Gauge(
            "nabattery_percent",
            "Netatmo reported battery level (percent)",
            ["name", "id"],
        )

        metrics["nawifi_status"] = prometheus_client.Gauge(
            "nawifi_status",
            "Netatmo reported wifi status",
            ["name", "id"],
        )

        metrics["narf_status"] = prometheus_client.Gauge(
            "narf_status",
            "Netatmo reported RF status",
            ["name", "id"],
        )

        metrics["nalast_seen"] = prometheus_client.Gauge(
            "nalast_seen", "Timestamp of device last seen", ["name", "id"]
        )
        metrics["nawindstrength"] = prometheus_client.Gauge(
            "nawindstrength", "Wind strength reported by Netatmo", ["name", "id"]
        )
        metrics["nawindangle"] = prometheus_client.Gauge(
            "nawindangle", "Wind angle reported by Netatmo", ["name", "id"]
        )
        metrics["naguststrength"] = prometheus_client.Gauge(
            "naguststrength", "Gust strength reported by Netatmo", ["name", "id"]
        )
        metrics["nawgustangle"] = prometheus_client.Gauge(
            "nagustangle", "Gust angle reported by Netatmo", ["name", "id"]
        )
        metrics["narain"] = prometheus_client.Gauge(
            "narain", "Rain reported by by Netatmo", ["name", "id"]
        )
        metrics["nahumidity"] = prometheus_client.Gauge(
            "nahumidity", "Humidity reported by by Netatmo", ["name", "id"]
        )
        metrics["nanoise"] = prometheus_client.Gauge(
            "nanoise", "Noise reported by by Netatmo", ["name", "id"]
        )
        metrics["naco2"] = prometheus_client.Gauge(
            "naco2", "CO2 reported by by Netatmo", ["name", "id"]
        )
        metrics["natemperature"] = prometheus_client.Gauge(
            "natemperature", "Temperature reported by by Netatmo", ["name", "id"]
        )
        metrics["napressure"] = prometheus_client.Gauge(
            "napressure", "Pressure reported by by Netatmo", ["name", "id"]
        )
        metrics["naabsolutepressure"] = prometheus_client.Gauge(
            "naabsolutepressure", "Absolute pressure reported by by Netatmo", ["name", "id"]
        )



    def refresh_all_meters(self):
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
            name = p["module_name"]
            id = p["_id"]
            self.metrics["nalast_seen"].labels(name=name, id=id).set(
                p["last_status_store"]
            )
            self.metrics["nawifi_status"].labels(name=name, id=id).set(p["wifi_status"])
            self.metrics["nareachable"].labels(name=name, id=id).set(p["reachable"])

            if not 'dashboard_data' in p:
                d = p["dashboard_data"]

                self.metrics["nahumidity"].labels(name=name, id=id).set(d["Humidity"])
                self.metrics["natemperature"].labels(name=name, id=id).set(d["Temperature"])
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

                if not 'dashboard_data' in m:
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

    def get_netatmo_token(self):
        if self.token and self.token["expire_at"] < time.time():
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

        token = r.json()
        token["expire_at"] = t + token["expire_in"]

        self.token = token
        return token


def serve():
    meter = Meter()
    prometheus_client.start_http_server(8012)
    meter.refresh_all_meters()

    while True:
        time.sleep(60)
        meter.refresh_all_meters()


if __name__ == "__main__":
    serve()
