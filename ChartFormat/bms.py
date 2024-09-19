import pandas as pd
import os  
import re
from enum import Enum

class Lane(Enum):
    ONE = 11
    TWO = 12
    THREE = 13
    FOUR = 14
    FIVE = 15
    SCRATCH = 16
    SIX = 18
    SEVEN = 19


class BMS:
    def __init__(self,filename:str, encode:str='utf-8'):
        ''' 생성자 함수, BMS 파일을 열고 메타데이터를 저장 '''
        try:
            self.file = open(filename, "rt", encoding=encode)
        except UnicodeDecodeError:
            self.file = open(filename, "rt", encoding='shift-jis')

        self.isRead = False

        self.findUnableRow(";")
        self.findUnableRow("#LNTYPE")
        self.findUnableRow("#LNOBJ")
        self.findUnableRow("#RANDOM")
        # 미지원 패턴 정보 확인 확인

        curTxt = self.seekRow("#BPM") 
        self.BPM = float(curTxt.split(" ")[1]) # BPM 저장
        self.SPB = (1/(self.BPM/60)) # 1 박자당(4분 음표)소요 되는 시간 계산
        self.DEFAULT_MEASURE = 4 # 마디당 박자는 2번 채널을 쓰지 않았을 경우 4/4 이므로
        self.measure_list = [4] # 변박을 담아두기 위한 리스트
        self.noteInfoList = [] # 노트 정보리스트 세팅

        flag = self.seekRow("*---------------------- MAIN DATA FIELD",seekAfterInit=True)
        if flag is None : raise NotSupportedException

    def extractToPandas(self)->pd.DataFrame|None:
        '''수집된 데이터를 판다스 데이터 프레임으로 변환'''
        if not self.isRead: return None
        sortedNoteInfoList = sorted(self.noteInfoList,key=lambda l:l[0]) #timestamp 순으로 오름차 정렬
        dataframe = pd.DataFrame(sortedNoteInfoList,columns=("timestamp","beatstamp", "barNum", "location", "laneInfo", "measure","note"))
        return dataframe

    def readAll(self):
        ''' 마디 전체를 읽는 함수 '''
        prevBar=0
        while True:
            read_res = self.readOneBar(prevBar)
            if read_res is None:
                break 
            prevBar = read_res["bar"]     
        self.isRead = True
        self.close()
    
    def readOneBar(self,prevBar:int)->dict|None:
        ''' 마디 하나를 읽는 함수 '''
        IsNoteAdded = False
        measure = self.findMeasureChange() # 우선 박자가 바뀌었는지를 체크
        curRow = self.seekRowRE(r"^#[0-9]+:")
        if curRow is None: return None # 이 이상 읽을 수 없으므로
        else: curBar = self.getBarFromRow(curRow)
        self.fillSkipedBeats(prevBar,curBar) # 스킵된 마디에 대해 박자삽입
        self.measure_list.append(measure) # 알아낸 박자를 삽입
        while re.match(r"^#[0-9]+:", curRow): # 마디가 바뀌기 전까지 수행
            flag = self.extractInfoFromRow(curBar,curRow)
            if flag == True: IsNoteAdded = True
            curRow = self.file.readline()
        return {"bar":curBar, "noteAdded": IsNoteAdded}  

    def extractInfoFromRow(self,curBar:int,row:str):
        '''   해당 마디의 한 행의 정보를 열람해 가공하는 함수   '''
        rowHeader, rowContents = row.split(":")
        laneInfo = int(rowHeader[4:6])
        notesInRow = []
        if laneInfo in  [l.value for l in Lane]: #레인에 대한 정보라면
            for i in range(0, len(rowContents[:-1]),2):
                notesInRow.append(rowContents[:-1][i:i+2]) #일단 2개씩 도막내서 저장
            grid = len(notesInRow)
            elem_count = 0
            for note in notesInRow:
                if note != "00":
                    location = elem_count/grid # 노트의 상대위치
                    timestamp = 0
                    for bar in range(curBar): timestamp += self.SPB*self.measure_list[bar] 
                    # 먼저 해당 마디 전까지의 타임 스템프를 쌓는다.
                    timestamp += location * self.measure_list[curBar]* self.SPB
                    #  타임 스탬프 = 마디내 위치 * 마디당 박자 * 박자당 시간 
                    beatstamp = sum(self.measure_list[:-1]) + self.measure_list[curBar]*location
                    #  비트 스탬프 = 이전 마디까지의 총 박자수 + 현재 마디의 박자 * 마디내 위치
                    noteInfo = [timestamp*1000,beatstamp,curBar, location, laneInfo, self.measure_list[curBar], note]
                    # 타임스탬프(ms 변환 1s = 1000ms), 마디번호, 노트의 마디내 상대적 위치, 레인번호, 박자,  노트 심볼(키음) 
                    self.noteInfoList.append(noteInfo)
                elem_count += 1
            return True
        else:
            return False
        
    def fillSkipedBeats(self,prevBar:int,curBar:int):
        '''아예 언급이 없는 마디의 경우 마지막으로 기록된 박자로 대신 기록해주는 함수'''
        skip_count = curBar-prevBar
        if skip_count > 1:
            lastBeat = self.measure_list[-1]
            for _ in range(skip_count-1): self.measure_list.append(lastBeat) 
    
    def getBarFromRow(self,row:str)->int:
        return int(row[1:4])

    def findMeasureChange(self)->None|int:
        ''' 박자 변동을 찾는 함수, 없으면 기본, 있으면 변동치 리턴, 에러시 None 리턴'''
        offset = self.file.tell()
        curRow = self.seekRowRE(r"^#[0-9]+:")
        if curRow is None: return None # 현단계에서는 찾을수가 없으므로 
        else: curBar = int(curRow[1:4])
        measureRow = self.seekRowRE(r"#\d{3}02:\d+(\.\d+)?")
        if measureRow is None or curBar != int(measureRow[1:4]):
            self.file.seek(offset)
            return self.DEFAULT_MEASURE # 지금 단계에서는 박자가 바뀌지 않음 기본치 리턴
        
        newMeasure = float(measureRow.split(':')[1])
        newMeasure *= self.DEFAULT_MEASURE
        self.file.seek(offset)
        return newMeasure #변동이 있으므로 변동치 리턴
    
    def seekRow(self, targetTxt:str, exceptionTxt:str = '', 
                curTxt:None|str = None, seekAfterInit:bool = False)->str|None:

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
    
    def findUnableRow(self, targetTxt:str, exitTxt:str = '', curTxt:None|str = None,
                       seekAfterInit:bool = False, offsetReturn:None|int=None)->int:
        ''' 문제가 있는 Row를 찾는 함수 [리턴]: 돌아갈 오프셋(없을 경우 맨 앞 오프셋)'''
        if seekAfterInit: self.file.seek(0) # 초기화후 Row를 찾는 경우
        if curTxt is None: # Curtxt를 넘겨주지 않은 경우 새롭게 readline
            curTxt = self.file.readline()
        while(not curTxt.startswith(targetTxt)):
            curTxt = self.file.readline() # 해당 텍스트가 나오기까지 오프셋을 미룬다.
            if(curTxt==exitTxt): #탈출 텍스트를 만난 경우 돌아갈 오프셋을 리턴 
                if offsetReturn is None : self.file.seek(0); offsetReturn = self.file.tell()
                return offsetReturn
        raise NotSupportedException
    
    def close(self):
        self.file.close()

            
class NotSupportedException(Exception):  # 처리불가능한 BMS 파일 처리용
    def __str__(self) -> str:
        return "Not supported BMS File"