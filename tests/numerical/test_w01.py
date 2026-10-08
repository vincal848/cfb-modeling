from cfb.evaluation.w01 import windy_counts


def test_windy_counts_skip_domes_and_missing_wind():
    w = [{"id": 1, "gameIndoors": False, "windSpeed": 16}, {"id": 2, "gameIndoors": True, "windSpeed": 30},
         {"id": 3, "gameIndoors": False, "windSpeed": 14.9}, {"id": 4, "gameIndoors": False, "windSpeed": None},
         {"id": 5, "gameIndoors": False, "windSpeed": 15}]
    assert windy_counts(w, {1, 3}) == {"outdoor_with_wind": 3, "windy": 2, "windy_with_total": 1}
