import ChartFormat.osr as osr
import pandas as pd

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
    