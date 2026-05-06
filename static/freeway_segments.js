// 國道路段定義 (依據國道里程表簡化)
var FREEWAY_SEGMENTS = {
    "NH1": {
        "name": "國道一號",
        "segments": [
            {"id": "NH1-N-1", "name": "基隆-台北", "dir": "north", "start": 0, "end": 27},
            {"id": "NH1-N-2", "name": "台北-桃園", "dir": "north", "start": 27, "end": 49},
            {"id": "NH1-N-3", "name": "桃園-新竹", "dir": "north", "start": 49, "end": 99},
            {"id": "NH1-N-4", "name": "新竹-台中", "dir": "north", "start": 99, "end": 178},
            {"id": "NH1-N-5", "name": "台中-台南", "dir": "north", "start": 178, "end": 327},
            {"id": "NH1-N-6", "name": "台南-高雄", "dir": "north", "start": 327, "end": 373},
            {"id": "NH1-S-1", "name": "高雄-台南", "dir": "south", "start": 373, "end": 327},
            {"id": "NH1-S-2", "name": "台南-台中", "dir": "south", "start": 327, "end": 178},
            {"id": "NH1-S-3", "name": "台中-新竹", "dir": "south", "start": 178, "end": 99},
            {"id": "NH1-S-4", "name": "新竹-桃園", "dir": "south", "start": 99, "end": 49},
            {"id": "NH1-S-5", "name": "桃園-台北", "dir": "south", "start": 49, "end": 27},
            {"id": "NH1-S-6", "name": "台北-基隆", "dir": "south", "start": 27, "end": 0}
        ]
    },
    "NH3": {
        "name": "國道三號",
        "segments": [
            {"id": "NH3-N-1", "name": "基隆-台北", "dir": "north", "start": 0, "end": 31},
            {"id": "NH3-N-2", "name": "台北-新竹", "dir": "north", "start": 31, "end": 100},
            {"id": "NH3-N-3", "name": "新竹-台中", "dir": "north", "start": 100, "end": 191},
            {"id": "NH3-N-4", "name": "台中-台南", "dir": "north", "start": 191, "end": 357},
            {"id": "NH3-N-5", "name": "台南-屏東", "dir": "north", "start": 357, "end": 431},
            {"id": "NH3-S-1", "name": "屏東-台南", "dir": "south", "start": 431, "end": 357},
            {"id": "NH3-S-2", "name": "台南-台中", "dir": "south", "start": 357, "end": 191},
            {"id": "NH3-S-3", "name": "台中-新竹", "dir": "south", "start": 191, "end": 100},
            {"id": "NH3-S-4", "name": "新竹-台北", "dir": "south", "start": 100, "end": 31},
            {"id": "NH3-S-5", "name": "台北-基隆", "dir": "south", "start": 31, "end": 0}
        ]
    }
};