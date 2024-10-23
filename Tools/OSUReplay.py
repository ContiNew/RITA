import ChartFormat.osr as osr
import ChartFormat.osu as osu
import pandas as pd
from enum import Enum

class Judgement(Enum):
    PERFECT = 16
    GREAT = 64 
    GOOD = 97 
    OK = 127 
    BAD = 151 

WAITING_DELAY = 200 # 공식문서에는 안나와있는데 대충 user를 기다리는 딜레이가 이정도 되는듯 함.

SEC_PER_FRAME = 1000/60

def is_bit_set(number, position):
    # 주어진 정수 number에서 position 자리에 해당하는 비트가 1인지 확인
    return (number & (1 << position)) != 0


class ReplayTable:
    def __init__(self, osr:osr.OSUReplay):
        self.table = denoiseReplay(osr.getReplayData())
        self.lifeBarReport = osr.getLifeBarReport()
    def getReducedTable(self):
        return self.table[self.table['note_pos']!=0].drop("time_interval" ,axis=1) # 빈칸과 타임 인터벌이 빠진 테이블 리턴
    
def denoiseReplay(replayDf:pd.DataFrame)->pd.DataFrame:
    replayDf = replayDf[replayDf['w']>= 0] # 먼저 음의 값을 가진 행을 쳐낸다
    replayDf = replayDf[replayDf['y']>= 0] # 먼저 음의 값을 가진 행을 쳐낸다
    replayDf = replayDf[["w","x"]] # 레인 정보와 상대적 타임스템프만을 가져온다.
    replayDf["t"] = replayDf['w'].cumsum() # 절대적 타임스템프로 바꾼다

    replayDf = replayDf.rename(columns={"w":"time_interval","x":"note_pos","t":"timestamp"}) # 이름 변경
    replayDf = replayDf[['timestamp','time_interval','note_pos']].reset_index(drop=True) # 열 순서 바꾸고 인덱스 리셋
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
            closest_record = ReplayAnalyzer.getClosestRecord(row,records,\
                                                             audioLeadIn=chart.AUDIO_LEAD_IN,\
                                                                overallDifficulty= chart.OVERALL_DIFFICULTY)
            mathced_pairs.append({"target_timestamp":row["timestamp"]+chart.AUDIO_LEAD_IN, \
                                  "recorded_timestamp":closest_record[1], \
                                  "r_timestamp_without_wating_delay":closest_record[1]-WAITING_DELAY,\
                                  "interval": row["timestamp"]+chart.AUDIO_LEAD_IN-closest_record[1]-WAITING_DELAY,\
                                  "lane":row["lane"], "judgement":closest_record[2]})
        return pd.DataFrame(mathced_pairs)

    @staticmethod
    def getClosestRecord(targetNote, records:pd.DataFrame,audioLeadIn=0,overallDifficulty=0.0):
        #To do: 채보의 타임스탬프를 고려해서 매칭되는 레코드듣을 수집하자.
        candidate = []
        for idx, row in records.iterrows():
            if row["timestamp"]-WAITING_DELAY > targetNote["timestamp"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: break
            # 완전 나가버리는 경우에는 해당 노트에 대한 기록이 아니므로(쓸모없는 연산은 더 하지않는다.)
            if row["timestamp"]-WAITING_DELAY <= targetNote["timestamp"]+(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn and\
               row["timestamp"]-WAITING_DELAY >= targetNote["timestamp"]-(Judgement.BAD.value-3*overallDifficulty)+audioLeadIn: 
                # 판정 범위에 들어오는지 확인.
                target_lane = targetNote["lane"]
                flag = is_bit_set(row["note_pos"],target_lane) # 레인 위치가 맞는지 확인
                if flag :  
                    candidate.append((idx,row["timestamp"],ReplayAnalyzer.getRecordJudgement(targetNote,row,audioLeadIn,overallDifficulty)))
        if len(candidate) == 0: result = (-1,-1,"MISS")
        else : result = sorted(candidate, key=lambda x: x[1])[0] # 수집된 레코드중에서 가장 빠른 레코드를 저장.
        return result
    
    @staticmethod
    def getRecordJudgement(targetNote, record,audioLeadIn=0,overallDifficulty=0.0):
        #레코드의 판정이 어떤지 판정하고 리턴함.
        targetPoint = targetNote["timestamp"]
        recordedPoint = record["timestamp"]-WAITING_DELAY
        if recordedPoint < targetPoint + Judgement.PERFECT.value+audioLeadIn\
            and recordedPoint > targetPoint - Judgement.PERFECT.value+audioLeadIn:
            return "PERFECT"
        if recordedPoint < targetPoint + (Judgement.GREAT.value-3*overallDifficulty)+audioLeadIn\
            and recordedPoint > targetPoint - (Judgement.GREAT.value-3*overallDifficulty)+audioLeadIn:
            return "GREAT"
        if recordedPoint < targetPoint + (Judgement.GOOD.value-3*overallDifficulty)+audioLeadIn\
            and recordedPoint > targetPoint - (Judgement.GOOD.value-3*overallDifficulty)+audioLeadIn:
            return "GOOD"
        if recordedPoint < targetPoint + (Judgement.OK.value-3*overallDifficulty)+audioLeadIn\
            and recordedPoint > targetPoint - (Judgement.OK.value-3*overallDifficulty)+audioLeadIn:
            return "OK"
        if recordedPoint < targetPoint + (Judgement.BAD.value-3*overallDifficulty)+audioLeadIn\
            and recordedPoint > targetPoint - (Judgement.BAD.value-3*overallDifficulty)+audioLeadIn:
            return "BAD"
        return "MISS"
                
                
        