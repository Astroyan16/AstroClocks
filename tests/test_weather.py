import datetime
import unittest
import datetime
from unittest.mock import patch

from astroclocks import weather


class WeatherTests(unittest.TestCase):
    def setUp(self):
        weather._METEOFRANCE_STATIONS_CACHE.clear()
        weather._METEOFRANCE_STATIONS_CACHE.update(
            {"value": None, "expires_at": None, "credential": None}
        )
        weather._METEOFRANCE_OBSERVATION_CACHE.clear()

    def test_nearest_metar_stations_filters_and_sorts_candidates(self):
        stations = [
            {
                "icaoId": "FAR1",
                "site": "Far",
                "lat": 49.0,
                "lon": 2.0,
                "siteType": ["METAR"],
            },
            {
                "icaoId": "NEAR",
                "site": "Near",
                "lat": 48.81,
                "lon": 2.23,
                "siteType": ["METAR"],
            },
            {
                "icaoId": "NOMET",
                "site": "No METAR",
                "lat": 48.81,
                "lon": 2.23,
                "siteType": [],
            },
        ]
        with patch("astroclocks.weather._read_json_url", return_value=stations):
            nearest = weather.nearest_metar_stations(
                48.805,
                2.23006,
                limit=2,
                max_distance_km=200,
            )

        self.assertEqual([station["icaoId"] for _distance, station in nearest], ["NEAR", "FAR1"])

    def test_nearest_metar_station_options_formats_three_ui_choices(self):
        stations = [
            (1.2, {"icaoId": "ONE", "site": "One", "lat": 48.8, "lon": 2.2, "elev": 100}),
            (3.4, {"icaoId": "TWO", "site": "Two", "lat": 48.9, "lon": 2.3, "elev": 120}),
            (5.6, {"icaoId": "THR", "site": "Three", "lat": 49.0, "lon": 2.4, "elev": 140}),
        ]

        with patch("astroclocks.weather.nearest_metar_stations", return_value=stations):
            options = weather.nearest_metar_station_options(48.805, 2.23006, limit=3)

        self.assertEqual([option["station_id"] for option in options], ["ONE", "TWO", "THR"])
        self.assertEqual(options[0]["station_name"], "One")
        self.assertEqual(options[0]["distance_km"], 1.2)

    def test_nearest_metar_pressure_station_options_skips_stations_without_qnh(self):
        stations = [
            (1.0, {"icaoId": "MISS", "site": "Missing", "lat": 48.8, "lon": 2.2}),
            (2.0, {"icaoId": "ONE", "site": "One", "lat": 48.9, "lon": 2.3}),
            (3.0, {"icaoId": "TWO", "site": "Two", "lat": 49.0, "lon": 2.4}),
            (4.0, {"icaoId": "THR", "site": "Three", "lat": 49.1, "lon": 2.5}),
        ]

        def pressure(station):
            if station["station_id"] == "MISS":
                return None
            return {
                "station_id": station["station_id"],
                "station_name": station["station_name"],
                "distance_km": station["distance_km"],
                "pressure_hpa": 1014.0,
                "temperature_c": 12,
                "report_time": "2026-07-09T16:30:00.000Z",
            }

        with patch("astroclocks.weather.nearest_metar_stations", return_value=stations):
            with patch("astroclocks.weather.fetch_metar_pressure_for_station", side_effect=pressure):
                options = weather.nearest_metar_pressure_station_options(
                    48.805,
                    2.23006,
                    limit=3,
                    now_utc=datetime.datetime(
                        2026,
                        7,
                        9,
                        17,
                        tzinfo=datetime.timezone.utc,
                    ),
                )

        self.assertEqual([option["station_id"] for option in options], ["ONE", "TWO", "THR"])
        self.assertTrue(all("pressure_hpa" in option for option in options))

    def test_fetch_metar_pressure_for_station_reads_selected_station(self):
        station = {
            "station_id": "GOOD",
            "station_name": "Good station",
            "distance_km": 2.0,
        }
        with patch(
            "astroclocks.weather.fetch_metar_observation",
            return_value={
                "name": "Good station",
                "altim": 1014,
                "temp": 12,
                "relh": 73,
            },
        ):
            result = weather.fetch_metar_pressure_for_station(station)

        self.assertEqual(result["station_id"], "GOOD")
        self.assertEqual(result["pressure_hpa"], 1014.0)
        self.assertEqual(result["distance_km"], 2.0)
        self.assertEqual(result["humidity_percent"], 73.0)

    def test_nearest_pressure_station_options_keeps_recent_metar_only(self):
        metar_stations = [
            (4.0, {"icaoId": "LFPV", "site": "Villacoublay", "lat": 48.77, "lon": 2.205}),
            (15.0, {"icaoId": "LFPO", "site": "Orly", "lat": 48.717, "lon": 2.384}),
        ]

        def metar_pressures(stations):
            return {
                station["station_id"]: {
                    "source": "METAR",
                    "station_id": station["station_id"],
                    "station_name": station["station_name"],
                    "distance_km": station["distance_km"],
                    "pressure_hpa": 1015.0,
                    "temperature_c": 31,
                    "report_time": "2026-07-09T16:30:00.000Z",
                }
                for station in stations
            }

        with patch("astroclocks.weather.nearest_metar_stations", return_value=metar_stations):
            with patch("astroclocks.weather.metar_pressures_for_stations", side_effect=metar_pressures):
                with patch("astroclocks.weather.nearest_meteofrance_stations", return_value=[]):
                    options = weather.nearest_pressure_station_options(
                        48.805,
                        2.23006,
                        limit=3,
                        now_utc=datetime.datetime(2026, 7, 9, 17, 0, tzinfo=datetime.timezone.utc),
                    )

        self.assertEqual(
            [(option["source"], option["station_id"]) for option in options],
            [("METAR", "LFPV"), ("METAR", "LFPO")],
        )

    def test_load_meteofrance_stations_parses_dynamic_station_list(self):
        csv_text = (
            "id_station;nom;latitude;longitude;altitude\n"
            "75114001;PARIS-MONTSOURIS PARC;48.821667;2.337778;75\n"
            "78621002;TRAPPES;48,7745;2,0093;168\n"
        )

        with patch("astroclocks.weather.load_meteofrance_application_id", return_value="api-key"):
            with patch("astroclocks.weather._read_text_request", return_value=csv_text):
                stations = weather.load_meteofrance_stations()

        self.assertEqual([station["station_id"] for station in stations], ["75114001", "78621002"])
        self.assertEqual(stations[0]["station_name"], "PARIS-MONTSOURIS PARC")
        self.assertAlmostEqual(stations[1]["longitude"], 2.0093)

    def test_load_meteofrance_stations_uses_hourly_cache(self):
        csv_text = "id_station;nom;latitude;longitude\n75114001;PARIS;48.8;2.3\n"

        with patch("astroclocks.weather.load_meteofrance_application_id", return_value="api-key"):
            with patch("astroclocks.weather._read_text_request", return_value=csv_text) as read_text:
                first = weather.load_meteofrance_stations()
                second = weather.load_meteofrance_stations()

        self.assertEqual(first, second)
        self.assertEqual(read_text.call_count, 1)

    def test_nearest_meteofrance_stations_uses_dynamic_station_list(self):
        stations = [
            {
                "source": "METEOFRANCE",
                "station_id": "FAR",
                "station_name": "Far",
                "latitude": 50.0,
                "longitude": 2.0,
            },
            {
                "source": "METEOFRANCE",
                "station_id": "NEAR",
                "station_name": "Near",
                "latitude": 48.806,
                "longitude": 2.231,
            },
        ]

        with patch("astroclocks.weather.load_meteofrance_stations", return_value=stations):
            nearest = weather.nearest_meteofrance_stations(
                48.805,
                2.23006,
                limit=2,
                max_distance_km=200,
            )

        self.assertEqual([station["station_id"] for _distance, station in nearest], ["NEAR", "FAR"])

    def test_fetch_meteofrance_pressure_for_station_reads_latest_dpobs_row(self):
        station = {
            "source": "METEOFRANCE",
            "station_id": "75114001",
            "station_name": "PARIS-MONTSOURIS PARC",
            "distance_km": 8.1,
        }
        payload = {
            "features": [
                {
                    "properties": {
                        "validity_time": "2026-07-09T16:24:00Z",
                        "pmer": 101420,
                        "t": 305.15,
                    }
                },
                {
                    "properties": {
                        "validity_time": "2026-07-09T16:30:00Z",
                        "pmer": 101430,
                        "t": 306.15,
                        "u": 64,
                    }
                },
            ]
        }

        with patch("astroclocks.weather.load_meteofrance_application_id", return_value="api-key"):
            with patch("astroclocks.weather._read_json_request", return_value=payload):
                result = weather.fetch_meteofrance_pressure_for_station(station)

        self.assertEqual(result["source"], "METEOFRANCE")
        self.assertEqual(result["station_id"], "75114001")
        self.assertAlmostEqual(result["pressure_hpa"], 1014.3)
        self.assertAlmostEqual(result["temperature_c"], 33.0)
        self.assertAlmostEqual(result["humidity_percent"], 64.0)
        self.assertEqual(result["report_time"], "2026-07-09T16:30:00Z")

    def test_fetch_meteofrance_pressure_for_station_uses_short_observation_cache(self):
        station = {
            "source": "METEOFRANCE",
            "station_id": "75114001",
            "station_name": "PARIS-MONTSOURIS PARC",
            "distance_km": 8.1,
        }
        payload = {
            "features": [
                {
                    "properties": {
                        "validity_time": "2026-07-09T16:30:00Z",
                        "pmer": 101430,
                        "t": 306.15,
                    }
                },
            ]
        }

        with patch("astroclocks.weather.load_meteofrance_application_id", return_value="api-key"):
            with patch("astroclocks.weather._read_json_request", return_value=payload) as read_json:
                first = weather.fetch_meteofrance_pressure_for_station(station)
                station_at_other_distance = {**station, "distance_km": 12.0}
                second = weather.fetch_meteofrance_pressure_for_station(
                    station_at_other_distance
                )

        self.assertEqual(read_json.call_count, 1)
        self.assertAlmostEqual(first["pressure_hpa"], 1014.3)
        self.assertAlmostEqual(second["distance_km"], 12.0)

    def test_meteofrance_authorization_uses_api_key_directly(self):
        with patch("astroclocks.weather.load_meteofrance_application_id", return_value="api-key"):
            headers = weather._meteofrance_authorization_headers()

        self.assertEqual(headers["apikey"], "api-key")
        self.assertEqual(headers["accept"], "application/json")

    def test_meteofrance_api_key_test_reports_climatology_only_key(self):
        with patch(
            "astroclocks.weather.load_meteofrance_stations",
            side_effect=ValueError("Météo-France HTTP 403: Resource forbidden"),
        ):
            with patch(
                "astroclocks.weather.load_meteofrance_application_id",
                return_value="api-key",
            ):
                with patch(
                    "astroclocks.weather._read_json_request",
                    return_value=[{"id": "75114001", "nom": "PARIS-MONTSOURIS PARC"}],
                ):
                    result = weather.test_meteofrance_api_key()

        self.assertFalse(result["observations_available"])
        self.assertTrue(result["climatology_available"])
        self.assertEqual(result["station_count"], 1)
        self.assertIn("Resource forbidden", result["observation_error"])

    def test_nearest_pressure_station_options_stops_after_limit_is_filled(self):
        meteofrance_stations = [
            (
                float(index),
                {
                    "source": "METEOFRANCE",
                    "station_id": f"MF{index}",
                    "station_name": f"Station {index}",
                    "latitude": 48.8,
                    "longitude": 2.3,
                },
            )
            for index in range(8)
        ]

        def meteofrance_pressure(station):
            if station["station_id"] in {"MF0", "MF2"}:
                return None
            return {
                "source": "METEOFRANCE",
                "station_id": station["station_id"],
                "station_name": station["station_name"],
                "distance_km": station["distance_km"],
                "pressure_hpa": 1014.0,
                "temperature_c": 20.0,
                "report_time": "2026-07-09T16:36:00Z",
            }

        with patch("astroclocks.weather.nearest_metar_stations", return_value=[]):
            with patch("astroclocks.weather.metar_pressures_for_stations", return_value={}):
                with patch(
                    "astroclocks.weather.nearest_meteofrance_stations",
                    return_value=meteofrance_stations,
                ) as nearest_meteofrance:
                    with patch(
                        "astroclocks.weather.fetch_meteofrance_pressure_for_station",
                        side_effect=meteofrance_pressure,
                    ) as fetch_pressure:
                        options = weather.nearest_pressure_station_options(
                            48.805,
                            2.23006,
                            limit=3,
                            scan_limit=10,
                            now_utc=datetime.datetime(
                                2026,
                                7,
                                9,
                                17,
                                0,
                                tzinfo=datetime.timezone.utc,
                            ),
                        )

        self.assertEqual(nearest_meteofrance.call_args.kwargs["limit"], 10)
        self.assertEqual(fetch_pressure.call_count, 5)
        self.assertEqual(len(options), 3)
        self.assertEqual(
            [option["station_id"] for option in options],
            ["MF1", "MF3", "MF4"],
        )

    def test_nearest_pressure_station_options_skips_meteofrance_when_metar_fills_limit(self):
        metar_stations = [
            (1.0, {"icaoId": "ONE", "site": "One", "lat": 48.8, "lon": 2.2}),
            (2.0, {"icaoId": "TWO", "site": "Two", "lat": 48.9, "lon": 2.3}),
            (3.0, {"icaoId": "THR", "site": "Three", "lat": 49.0, "lon": 2.4}),
        ]

        def metar_pressures(stations):
            return {
                station["station_id"]: {
                    "source": "METAR",
                    "station_id": station["station_id"],
                    "station_name": station["station_name"],
                    "distance_km": station["distance_km"],
                    "pressure_hpa": 1015.0,
                    "temperature_c": 31,
                    "report_time": "2026-07-09T16:30:00Z",
                }
                for station in stations
            }

        with patch("astroclocks.weather.nearest_metar_stations", return_value=metar_stations):
            with patch("astroclocks.weather.metar_pressures_for_stations", side_effect=metar_pressures):
                with patch("astroclocks.weather.nearest_meteofrance_stations") as nearest_meteofrance:
                    with patch("astroclocks.weather.fetch_meteofrance_pressure_for_station") as fetch_pressure:
                        options = weather.nearest_pressure_station_options(
                            48.805,
                            2.23006,
                            limit=3,
                            now_utc=datetime.datetime(
                                2026,
                                7,
                                9,
                                17,
                                0,
                                tzinfo=datetime.timezone.utc,
                            ),
                        )

        nearest_meteofrance.assert_called_once()
        fetch_pressure.assert_not_called()
        self.assertEqual([option["station_id"] for option in options], ["ONE", "TWO", "THR"])

    def test_nearest_pressure_station_options_merges_meteofrance_without_hardcoded_station(self):
        metar_stations = [
            (4.0, {"icaoId": "LFPV", "site": "Villacoublay", "lat": 48.77, "lon": 2.205}),
        ]
        meteofrance_stations = [
            (
                2.0,
                {
                    "source": "METEOFRANCE",
                    "station_id": "12345678",
                    "station_name": "Dynamic station",
                    "latitude": 48.82,
                    "longitude": 2.34,
                },
            )
        ]

        def metar_pressures(stations):
            return {
                "LFPV": {
                    "source": "METAR",
                    "station_id": "LFPV",
                    "station_name": "Villacoublay",
                    "distance_km": 4.0,
                    "pressure_hpa": 1015.0,
                    "temperature_c": 31,
                    "report_time": "2026-07-09T16:30:00Z",
                }
            }

        def meteofrance_pressure(station):
            return {
                "source": "METEOFRANCE",
                "station_id": station["station_id"],
                "station_name": station["station_name"],
                "distance_km": station["distance_km"],
                "pressure_hpa": 1014.2,
                "temperature_c": 32,
                "report_time": "2026-07-09T16:36:00Z",
            }

        with patch("astroclocks.weather.nearest_metar_stations", return_value=metar_stations):
            with patch("astroclocks.weather.nearest_meteofrance_stations", return_value=meteofrance_stations):
                with patch("astroclocks.weather.metar_pressures_for_stations", side_effect=metar_pressures):
                    with patch(
                        "astroclocks.weather.fetch_meteofrance_pressure_for_station",
                        side_effect=meteofrance_pressure,
                    ):
                        options = weather.nearest_pressure_station_options(
                            48.805,
                            2.23006,
                            limit=3,
                            now_utc=datetime.datetime(
                                2026,
                                7,
                                9,
                                17,
                                0,
                                tzinfo=datetime.timezone.utc,
                            ),
                        )

        self.assertEqual(
            [(option["source"], option["station_id"]) for option in options],
            [("METEOFRANCE", "12345678"), ("METAR", "LFPV")],
        )

    def test_nearest_pressure_station_options_respects_search_radius(self):
        meteofrance_stations = [
            (
                8.0,
                {
                    "source": "METEOFRANCE",
                    "station_id": "NEAR",
                    "station_name": "Near station",
                    "latitude": 48.82,
                    "longitude": 2.34,
                },
            )
        ]

        def nearest_meteofrance(_latitude, _longitude, limit=20, max_distance_km=150):
            return [
                (distance, station)
                for distance, station in meteofrance_stations
                if distance <= max_distance_km
            ][:limit]

        def meteofrance_pressure(station):
            return {
                "source": "METEOFRANCE",
                "station_id": station["station_id"],
                "station_name": station["station_name"],
                "distance_km": station["distance_km"],
                "pressure_hpa": 1014.2,
                "temperature_c": 32,
                "report_time": "2026-07-09T16:36:00Z",
            }

        with patch("astroclocks.weather.nearest_metar_stations", return_value=[]):
            with patch("astroclocks.weather.metar_pressures_for_stations", return_value={}):
                with patch(
                    "astroclocks.weather.nearest_meteofrance_stations",
                    side_effect=nearest_meteofrance,
                ):
                    with patch(
                        "astroclocks.weather.fetch_meteofrance_pressure_for_station",
                        side_effect=meteofrance_pressure,
                    ):
                        inside = weather.nearest_pressure_station_options(
                            48.805,
                            2.23006,
                            limit=3,
                            max_distance_km=10,
                            now_utc=datetime.datetime(
                                2026,
                                7,
                                9,
                                17,
                                0,
                                tzinfo=datetime.timezone.utc,
                            ),
                        )
                        outside = weather.nearest_pressure_station_options(
                            48.805,
                            2.23006,
                            limit=3,
                            max_distance_km=5,
                            now_utc=datetime.datetime(
                                2026,
                                7,
                                9,
                                17,
                                0,
                                tzinfo=datetime.timezone.utc,
                            ),
                        )

        self.assertEqual([option["station_id"] for option in inside], ["NEAR"])
        self.assertEqual(outside, [])

    def test_fetch_nearest_metar_pressure_uses_first_station_with_pressure(self):
        stations = [
            (1.0, {"icaoId": "MISS", "site": "Missing pressure"}),
            (2.0, {"icaoId": "GOOD", "site": "Good station"}),
        ]

        def observation(station_id, timeout=15):
            if station_id == "MISS":
                return {"name": "Missing pressure"}
            return {
                "name": "Good station",
                "altim": 1014,
                "temp": 12,
                "reportTime": "2026-07-09T16:30:00.000Z",
            }

        with patch("astroclocks.weather.nearest_metar_stations", return_value=stations):
            with patch("astroclocks.weather.fetch_metar_observation", side_effect=observation):
                result = weather.fetch_nearest_metar_pressure(48.805, 2.23006)

        self.assertEqual(result["station_id"], "GOOD")
        self.assertEqual(result["pressure_hpa"], 1014.0)
        self.assertEqual(result["temperature_c"], 12)

    def test_fetch_nearest_metar_pressure_returns_none_without_pressure(self):
        stations = [(1.0, {"icaoId": "MISS", "site": "Missing pressure"})]
        with patch("astroclocks.weather.nearest_metar_stations", return_value=stations):
            with patch("astroclocks.weather.fetch_metar_observation", return_value={}):
                result = weather.fetch_nearest_metar_pressure(48.805, 2.23006)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
