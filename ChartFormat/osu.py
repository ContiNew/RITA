import pandas as pd
import numpy as np
import re
import math

EPSILON = 1e-9  # 허용 오차
#time,beatLength,meter,sampleSet,sampleIndex,volume,uninherited,effects
# uninherited의 경우 슬라이더 속도에만 영향을 끼치므로 무시.
#x,y,time,type,hitSound,objectParams,hitSample

class OSU:
    def __init__(self,filename:str, encode:str='utf-8', key_only:int|None=None) -> None:
        ''' 생성자 함수, OSU 파일을 열고 메타데이터를 저장 '''
        try:
            self.file = open(filename, "rt", encoding=encode)
        except UnicodeDecodeError:
            self.file = open(filename, "rt", encoding='shift-jis')
        self.LANES = self.getLanes()
        self.AUDIO_LEAD_IN = self.getAudioLeadIn()
        self.timingInfo = self.getTimingInfo()
        if not key_only is None and self.LANES != key_only:  raise NotSupportedException # 특정 키만을 수집하는 경우
        if self.checkBPMChange() : raise NotSupportedException # 변속 미지원
        self.noteInfo = self.getNoteInfo()

    def extractToPandas(self)->pd.DataFrame|None:
        '''수집된 데이터를 판다스 데이터 프레임으로 변환'''
        sortedNoteInfoList = sorted(self.noteInfo,key=lambda l:l["timestamp"]) #timestamp 순으로 오름차 정렬
        dataframe = pd.DataFrame(sortedNoteInfoList,columns=("timestamp","beatstamp", "lane"))
        return dataframe

    def getAudioLeadIn(self):
        """ 음악이 시작되기전의 ms를 가져오는 함수 """
        curTxt = self.seekRow("AudioLeadIn")
        self.file.seek(0) 
        if curTxt is None:
            return None
        audioLeadIn = int(curTxt.split(":")[1])
        return audioLeadIn
    
    def getLanes(self)->int:
        """레인 정보를 들고옴"""
        curTxt = self.seekRow("CircleSize")
        self.file.seek(0) 
        if curTxt is None:
            return None
        Lanes = int(curTxt.split(":")[1])
        return Lanes

    def getTimingInfo(self)->list:
        """ 타이밍 정보를 가져오는 함수 """
        info_list = []
        curTxt = self.seekRow("[TimingPoints]") # 타이밍 포인트까지 오프셋을 당기고
        while True:
            curTxt = self.file.readline().strip()
            if curTxt=="": break
            curTxt = curTxt.split(",")
            if int(curTxt[-2]) == 0: continue #uninherit 여부 검증
            begin_ms = int(curTxt[0]) # 섹션 시작 지점
            sec_per_beat = float(curTxt[1]) # 섹션 내 박자당 초
            meter = int(curTxt[2]) # 마디당 박자수
            item = {"begin":begin_ms, "spb":sec_per_beat, "meter":meter}
            info_list.append(item)                             
        return info_list
    
    def getNoteInfo(self)->list:
        """ 노트들의 정보를 가져오는 함수"""
        info_list = []
        curTxt = self.seekRow("[HitObjects]") # 히트 오브젝트까지 당기고 시작
        while True:
            curTxt = self.file.readline().strip()
            if curTxt=="": break
            curTxt = curTxt.split(",")
            info_list.append(self.makeNoteInfoItem(curTxt))
        return info_list
    
    def makeNoteInfoItem(self,row:list)->list[dict]:
        """ 노트 행을 분리하여 정리하는 함수 """
        x = math.floor(int(row[0]) * self.LANES / 512) # 레인 정보를 가져옴
        time = int(row[2]) # 공백을 배재하고 보자.
        return {"timestamp":time, "beatstamp":self.getBeatStamp(time),"lane":x }

    def getBeatStamp(self,time:int, unit:float=0.0625)->float: #최소그리드 단위는 64분음표(1: 4분음표 기준)
        """ 비트스탬프를 가져오는 함수 """
        time = time-self.timingInfo[0]["begin"] # 박자가 없는 공백을 기준으로 생각한다.
        beatstamp = time/self.timingInfo[0]["spb"] # 어차피 변속을 볼 수 없으므로
        beatstamp = round(beatstamp/unit)*unit # 가장 가까운 64분 음표 지점으로 보정한다.
        return beatstamp
    
    def checkBPMChange(self)->bool:
        """ 변속이 있는지 체크함 """
        prev_spb = None
        for item in self.timingInfo:
            if prev_spb is None: prev_spb = item["spb"]
            if abs(prev_spb - item["spb"]) > EPSILON: return True #오차범위 보다 큰 경우 참을 리턴
        return False 
    

    def seekRow(self, targetTxt:str, exceptionTxt:str = '', 
                curTxt:None|str = None, seekAfterInit:bool = False)->str|None:
        ''' 특정 Row로 이동하는 함수 [리턴] : 찾은 행의 텍스트'''
        if seekAfterInit: self.file.seek(0) # 초기화후 Row를 찾는 경우
        if curTxt is None: # Curtxt를 넘겨주지 않은 경우 새롭게 readline
            curTxt = self.file.readline()
        while(not curTxt.startswith(targetTxt)):
            if(curTxt==exceptionTxt): return None
            curTxt = self.file.readline() # 해당 텍스트가 나오기까지 오프셋을 미룬다.
        return curTxt # 찾은 row의 텍스트를 리턴한다 
    
    def seekRowRE(self, targetPattern:str|re.Pattern[str], exceptionTxt:str = '', 
                curTxt:None|str = None, seekAfterInit:bool = False)->str|None:
        ''' 특정 조건의 Row로 이동하는 함수(정규식 활용) [리턴] : 찾은 행의 텍스트'''
        if seekAfterInit: self.file.seek(0) # 초기화후 Row를 찾는 경우
        if curTxt is None: # Curtxt를 넘겨주지 않은 경우 새롭게 readline
            curTxt = self.file.readline()
        while(not re.match(targetPattern, curTxt)):
            if(curTxt==exceptionTxt): return None
            curTxt = self.file.readline() # 해당 텍스트가 나오기까지 오프셋을 미룬다
        return curTxt # 찾은 row의 텍스트를 리턴한다 
    

class NotSupportedException(Exception):  # 처리불가능한 BMS 파일 처리용
    def __str__(self) -> str:
        return "Not supported OSU File"