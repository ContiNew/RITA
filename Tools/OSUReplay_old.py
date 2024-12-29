import ChartFormat.osr as osr
import ChartFormat.osu as osu
import pandas as pd
from enum import Enum
import hashlib
import os

def calculate_file_hash(file_path, hash_algorithm="md5"):
    hash_func = hashlib.new(hash_algorithm) #해시 함수를 불러옴
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def find_file_by_hash(target_hash, directory, hash_algorithm="md5"):
    """
    주어진 해시 값과 일치하는 파일을 찾고 파일 경로를 반환합니다.
    일치하는 파일이 없으면 None을 반환합니다.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if calculate_file_hash(file_path, hash_algorithm) == target_hash:
                return file_path  # 일치하는 파일 경로 반환
    return None  # 일치하는 파일이 없는 경우

class Judgement(Enum):
    PERFECT = 16
    GREAT = 64 
    GOOD = 97 
    OK = 127 
    BAD = 151 

SEC_PER_FRAME = 1000/60

def is_bit_set(number, position):
    # 주어진 정수 number에서 position 자리에 해당하는 비트가 1인지 확인
    return (number & (1 << position)) != 0

def find_matched_beatmap(songfolder:str, targetHash, hashAlgorithm='md5')->str|None:
    return find_file_by_hash(targetHash, songfolder, hashAlgorithm)


class ReplayTable:
    def __init__(self, osr:osr.OSUReplay):
        self.table = denoiseReplay(osr.getReplayData())
        self.lifeBarReport = osr.getLifeBarReport()
        self.paired_beatmap_hash = osr.content["beatmap_hash"]
    def getReducedTable(self):
        return self.table[self.table['note_pos']!=0].drop("time_interval" ,axis=1) # 빈칸과 타임 인터벌이 빠진 테이블 리턴
    
    
def denoiseReplay(replayDf:pd.DataFrame)->pd.DataFrame:

    wating_delay = replayDf.loc[2, 'w'] # 리플레이 기록시의 딜레이 시간을 저장. 
    
    replayDf = replayDf[replayDf['w']>= 0] # 먼저 음의 값을 가진 행을 쳐낸다
    replayDf = replayDf[replayDf['y']>= 0] # 먼저 음의 값을 가진 행을 쳐낸다

    replayDf = replayDf[["w","x"]] # 레인 정보와 상대적 타임스템프만을 가져온다.
    replayDf["t"] = replayDf['w'].cumsum() # 절대적 타임스템프로 바꾼다

    replayDf = replayDf.rename(columns={"w":"time_interval","x":"note_pos","t":"timestamp"}) # 이름 변경
    replayDf = replayDf[['timestamp','time_interval','note_pos']].reset_index(drop=True) # 열 순서 바꾸고 인덱스 리셋
    
    replayDf["timestamp"] = replayDf['timestamp'] + wating_delay # 리플레이 딜레이를 쳐낸다.(음수로 주어지므로 합치면 됨.)
    replayDf["note_pos"] = replayDf["note_pos"].astype(int) # 노트 포지션은 정수로 바꿔 비트와이즈 연산이 가능토록 바꾼다
    replayDf["note_pos_bin"] = replayDf["note_pos"].apply(lambda x:bin(x)[2:]) # 이진 형태로 저장하는 열을 만들어 형태를 확인 할 수 있도록 함.
    return replayDf

class ReplayAnalyzer:
    @staticmethod
    def matchNotesToReplay(rp:ReplayTable, chart:osu.OSU): # 리플레이의 기록을 실제 노트와 매칭해주는 함수
        records = rp.getReducedTable()
        chart_df = chart.extractToPandas()
        mathced_pairs = []
        for idx, row in chart_df.iterrows():
            if row["isLongNote"]==True:
                closest_record = ReplayAnalyzer.getClosestRecordLN(row,records,\
                                                                audioLeadIn=chart.AUDIO_LEAD_IN,\
                                                                    overallDifficulty= chart.OVERALL_DIFFICULTY)
                mathced_pairs.append({"target_timestamp":row["timestamp"]+chart.AUDIO_LEAD_IN, \
                                "recorded_timestamp":closest_record[0][1], \
                                "interval": row["timestamp"]+chart.AUDIO_LEAD_IN-closest_record[0][1],\
                                "lane":row["lane"], "judgement":closest_record[0][2], "isLN":1})
                if len(closest_record) > 1:
                    mathced_pairs.append({"target_timestamp":row["endtime"]+chart.AUDIO_LEAD_IN, \
                                "recorded_timestamp":closest_record[1][1], \
                                "interval": row["endtime"]+chart.AUDIO_LEAD_IN-closest_record[1][1],\
                                "lane":row["lane"], "judgement":closest_record[1][2], "isLN":2})
            else:
                closest_record = ReplayAnalyzer.getClosestRecord(row,records,\
                                                                audioLeadIn=chart.AUDIO_LEAD_IN,\
                                                                    overallDifficulty= chart.OVERALL_DIFFICULTY)
                mathced_pairs.append({"target_timestamp":row["timestamp"]+chart.AUDIO_LEAD_IN, \
                                "recorded_timestamp":closest_record[1], \
                                "interval": row["timestamp"]+chart.AUDIO_LEAD_IN-closest_record[1],\
                                "lane":row["lane"], "judgement":closest_record[2],"isLN":0})
        mathced_records = pd.DataFrame(mathced_pairs)
        return mathced_records
    
    @staticmethod
    def statFromMatchedRecords(matched_records:pd.DataFrame, overallDifficulty=0.0):
        intervals = matched_records["interval"]
        mean = intervals.mean() # 평균
        sd = intervals.std() # 분산
        median = intervals.median()# 중앙값
        n_of_fasts = (intervals < -Judgement.PERFECT.value+3*overallDifficulty).sum()
        n_of_slows = (intervals > Judgement.PERFECT.value-3*overallDifficulty).sum()
        n_of_critical_fast = (intervals <= -Judgement.GOOD.value+3*overallDifficulty).sum()
        n_of_critical_slow = (intervals > Judgement.GOOD.value-3*overallDifficulty).sum()

        # 변수들을 딕셔너리로 묶기
        data = {
            'mean': [mean],
            'std': [sd],
            'median': [median],
            'n_of_fasts': [n_of_fasts],
            'n_of_slows': [n_of_slows],
            'n_of_critical_fast': [n_of_critical_fast],
            'n_of_critical_slow': [n_of_critical_slow]
        }

        # 딕셔너리를 데이터프레임으로 변환
        result = pd.DataFrame(data)
        return result


    @staticmethod
    def getClosestRecord(targetNote, records:pd.DataFrame,audioLeadIn=0,overallDifficulty=0.0):
        #To do: 채보의 타임스탬프를 고려해서 매칭되는 레코드듣을 수집하자.
        candidate = []
        for idx, row in records.iterrows():
            if row["timestamp"] > targetNote["timestamp"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: break
            # 완전 나가버리는 경우에는 해당 노트에 대한 기록이 아니므로(쓸모없는 연산은 더 하지않는다.)
            if row["timestamp"] <= targetNote["timestamp"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn and\
               row["timestamp"] >= targetNote["timestamp"]-(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: 
                # 판정 범위에 들어오는지 확인.
                target_lane = targetNote["lane"]
                flag = is_bit_set(row["note_pos"],target_lane) # 레인 위치가 맞는지 확인
                if flag :  
                    candidate.append((idx,row["timestamp"],ReplayAnalyzer.getRecordJudgement(targetNote,row,audioLeadIn,overallDifficulty)))
        if len(candidate) == 0: result = (-1,-1,"MISS")
        else : result = sorted(candidate, key=lambda x: x[1])[0] # 수집된 레코드중에서 가장 빠른 레코드를 저장.
        return result
    
    @staticmethod
    def getClosestRecordLN(targetNote, records:pd.DataFrame,audioLeadIn=0,overallDifficulty=0.0):
        #To do: 채보의 타임스탬프를 고려해서 매칭되는 레코드듣을 수집하자.
        candidate_s = []
        candidate_e = []
        for idx, srow in records.iterrows():
             if srow["timestamp"] > targetNote["timestamp"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: break
             if srow["timestamp"] <= targetNote["timestamp"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn and\
               srow["timestamp"] >= targetNote["timestamp"]-(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: 
                 #판정범위 안에 들어오는지 확인.
                for idx, erow in records.iterrows():
                    if erow["timestamp"] > targetNote["endtime"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: break
                    if erow["timestamp"] <= targetNote["endtime"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn and\
                    erow["timestamp"] >= targetNote["endtime"]-(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: 
                        target_lane = targetNote["lane"]
                        sflag = is_bit_set(srow["note_pos"],target_lane) # 레인 위치가 맞는지 확인
                        eflag = is_bit_set(srow["note_pos"],target_lane) # 레인 위치가 맞는지 확인
                        if sflag and eflag:
                           judgement = ReplayAnalyzer.getRecordJudgementLN(targetNote,srow, erow, audioLeadIn,overallDifficulty)
                           candidate_s.append((idx,srow["timestamp"],judgement))
                           candidate_e.append((idx,erow["timestamp"],judgement))
        if len(candidate_s) == 0 or len(candidate_e)==0: result = ((-1,-1,"MISS"),)
        else : result = (sorted(candidate_s, key=lambda x: x[1])[0] ,sorted(candidate_e, key=lambda x: x[1])[0])# 수집된 레코드중에서 가장 빠른 레코드를 저장.
        return result
    
    @staticmethod
    def getRecordJudgement(targetNote, record,audioLeadIn=0,overallDifficulty=0.0):
        #레코드의 판정이 어떤지 판정하고 리턴함.
        targetPoint = targetNote["timestamp"]+audioLeadIn
        recordedPoint = record["timestamp"]
        error = abs(targetPoint-recordedPoint)
        if error <= Judgement.PERFECT.value:
            return "PERFECT"
        if error <=  (Judgement.GREAT.value-3*overallDifficulty):
            return "GREAT"
        if error <=   (Judgement.GOOD.value-3*overallDifficulty):
            return "GOOD"
        if error <=   (Judgement.OK.value-3*overallDifficulty):
            return "OK"
        if error <=    (Judgement.BAD.value-3*overallDifficulty):
            return "BAD"
        return "MISS"
    

    @staticmethod
    def getRecordJudgementLN(targetNote, s_record, e_record, audioLeadIn=0,overallDifficulty=0.0):
        #레코드의 판정이 어떤지 판정하고 리턴함.(롱노트용 )
        s_target = targetNote["timestamp"]+audioLeadIn
        e_target = targetNote["endtime"]+audioLeadIn

        s_recorded = s_record["timestamp"]
        e_recorded = e_record["timestamp"]

        head_error = abs(s_target-s_recorded)
        combined_error = head_error + abs(e_target-e_recorded)

        if head_error <= Judgement.PERFECT.value* 1.2 and combined_error <= Judgement.PERFECT.value* 2.4:
            return "PERFECT"
        if head_error <=  (Judgement.GREAT.value-3*overallDifficulty)*1.1\
            and combined_error <= (Judgement.GREAT.value-3*overallDifficulty)*2.2:
            return "GREAT"
        if head_error <=  (Judgement.GOOD.value-3*overallDifficulty)\
            and combined_error <= (Judgement.GOOD.value-3*overallDifficulty)*2:
            return "GOOD"
        if head_error <=  (Judgement.OK.value-3*overallDifficulty)\
            and combined_error <= (Judgement.OK.value-3*overallDifficulty)*2:
            return "OK"
        """
        if head_error <=  (Judgement.BAD.value-3*overallDifficulty)\
            and combined_error <= (Judgement.BAD.value-3*overallDifficulty)*2:
            return "BAD"
        """
        if s_recorded < e_target-(Judgement.BAD.value-3*overallDifficulty) and \
            s_recorded > e_target+(Judgement.OK.value-3*overallDifficulty) :
            return "MISS"
        return "BAD"
                
        