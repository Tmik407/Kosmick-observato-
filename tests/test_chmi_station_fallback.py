import importlib.util
import pathlib
import unittest
from unittest.mock import patch

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "update_chmi_stations.py"
spec = importlib.util.spec_from_file_location("update_chmi_stations", MODULE_PATH)
chmi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chmi)


class TestStationFallback(unittest.TestCase):
    def test_automated_station_prefers_now_then_recent(self):
        station = {"id": "0-20000-0-11406", "name": "Test"}
        live = {"id": station["id"], "data_source": "now"}
        with patch.object(chmi, "fetch_station", side_effect=[(None, None), (live, None)]) as fetch:
            result, error = chmi.fetch_station_with_fallback(station, "20261126", "20261125")
        self.assertIsNone(error)
        self.assertEqual(result, live)
        self.assertEqual(fetch.call_args_list[0].args, (station, "20261126", chmi.NOW_BASE))
        self.assertEqual(fetch.call_args_list[1].args, (station, "20261126", chmi.BASE))

    def test_now_uses_flat_data_directory(self):
        station = {"id": "0-20000-0-11406", "name": "Test"}
        payload = {"data": {"data": {"values": []}}}
        with patch.object(chmi, "get_json", return_value=payload) as get_json:
            chmi.fetch_station(station, "20261126", chmi.NOW_BASE)
        url = get_json.call_args.args[0]
        self.assertIn("/now/data/10m-0-20000-0-11406-20261126.json", url)
        self.assertNotIn("/now/data/10min/", url)

    def test_partner_station_also_prefers_now_when_available(self):
        station = {"id": "0-203-0-11401", "name": "Test"}
        live = {"id": station["id"], "data_source": "now"}
        with patch.object(chmi, "fetch_station", return_value=(live, None)) as fetch:
            result, error = chmi.fetch_station_with_fallback(station, "20261126", "20261125")
        self.assertIsNone(error)
        self.assertEqual(result, live)
        self.assertEqual(fetch.call_args_list[0].args, (station, "20261126", chmi.NOW_BASE))

    def test_missing_today_file_falls_back_to_previous_day(self):
        station = {"id": "0-203-0-11401", "name": "Test"}
        archived = {"id": station["id"], "data_source": "recent"}
        with patch.object(chmi, "fetch_station", side_effect=[(None, None), (None, None), (archived, None)]) as fetch:
            result, error = chmi.fetch_station_with_fallback(station, "20261126", "20261125")
        self.assertIsNone(error)
        self.assertEqual(result, archived)
        self.assertEqual(fetch.call_args_list[0].args, (station, "20261126", chmi.NOW_BASE))
        self.assertEqual(fetch.call_args_list[2].args, (station, "20261125", chmi.BASE))


if __name__ == "__main__":
    unittest.main()
