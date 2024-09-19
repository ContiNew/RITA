import pandas as pd
import os  
import re
from enum import Enum

class OSU:
    def __init__(self,filename:str, encode:str='utf-8') -> None:
        ''' 생성자 함수, OSU 파일을 열고 메타데이터를 저장 '''
        try:
            self.file = open(filename, "rt", encoding=encode)
        except UnicodeDecodeError:
            self.file = open(filename, "rt", encoding='shift-jis')

        self.isRead = False

        
        pass
    
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