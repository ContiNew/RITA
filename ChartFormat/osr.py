import struct
import lzma
import pandas as pd

class OSUReplay:
    def __init__(self,path:str) -> None:
        with open(path, "+rb") as file:
            # 게임 모드 (byte)
            game_mode = struct.unpack('B', file.read(1))[0]
            # osu! 버전 (int32)
            version = struct.unpack('<i', file.read(4))[0]
            # 비트맵 MD5 해시 (string)
            beatmap_hash = read_osr_string(file)
            # 플레이어 이름 (string)
            player_name = read_osr_string(file)
            # 리플레이 MD5 해시 (string)
            replay_hash = read_osr_string(file)
            # 300/100/50/미스 카운트 (각각 int16)
            count_300 = struct.unpack('<h', file.read(2))[0]
            count_100 = struct.unpack('<h', file.read(2))[0]
            count_50 = struct.unpack('<h', file.read(2))[0]
            count_max_300 = struct.unpack('<h', file.read(2))[0]
            count_200 = struct.unpack('<h', file.read(2))[0]
            count_miss = struct.unpack('<h', file.read(2))[0]
            score = struct.unpack('<i', file.read(4))[0]
            # 최대 콤보 (int16)
            max_combo = struct.unpack('<h', file.read(2))[0]
            full_combo = struct.unpack('B', file.read(1))[0]
            # 사용된 모드
            mod_used = struct.unpack('<i', file.read(4))[0]
            # 라이프바의 상태 기록
            life_bar_report = read_osr_string(file).split(',')[:-1]
            life_bar_report = [{ "ms" : int(p.split('|')[0]), "life": float(p.split('|')[1])} for p in life_bar_report]
            # 타임 스탬프
            timestamp = struct.unpack('<q', file.read(8))[0]
            # 리플레이 데이터 파싱
            len_of_replay =  struct.unpack('<i', file.read(4))[0]
            compressed_replay = file.read(len_of_replay)
            replay_data = lzma.decompress(compressed_replay).decode().split(',')[:-1]
            replay_data = [{ "w" : int(row.split('|')[0]), "x": float(row.split('|')[1]), "y": float(row.split('|')[2]), "z": int(row.split('|')[3])} for row in replay_data]
            # 온라인 스코어 ID
            online_id = struct.unpack('<q', file.read(8))[0]
            
            self.content = {
            'game_mode': game_mode,
            'version': version,
            'beatmap_hash': beatmap_hash,
            'player_name': player_name,
            'replay_hash': replay_hash,
            'count_300': count_300,
            'count_100': count_100,
            'count_50': count_50,
            'count_max_300': count_max_300,
            'count_200': count_200,
            'count_miss': count_miss,
            'max_combo': max_combo,
            'full_combo': full_combo,
            'score': score,
            'life_bar_report':life_bar_report,
            'mod_used': mod_used,
            'timestamp': timestamp,
            'replay_data': replay_data,
            'online_replay_id': online_id,
            }
    def getLifeBarReport(self):
        return pd.DataFrame(self.content["life_bar_report"])
    def getReplayData(self):
        return pd.DataFrame(self.content["replay_data"])


def read_uleb128(file):
    """Reads a ULEB128-encoded integer from the file."""
    result = 0
    shift = 0

    while True:
        byte = ord(file.read(1))
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7

    return result

def read_osr_string(file):
    """Reads a string from the file according to the osu! replay format."""
    prefix = file.read(1)
    if prefix == b'\x00':  # String not present
        return None
    elif prefix == b'\x0b':  # String present
        length = read_uleb128(file)  # Length of the UTF-8 string
        return file.read(length).decode('utf-8')
    return None



