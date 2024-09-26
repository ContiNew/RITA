import ChartFormat.osu as osu
import numpy as np
import pandas as pd

class ChartMatrix:
    def __init__(self, chart:osu.OSU):
        self.NUM_OF_LANE = chart.LANES
        self.LANE_ORDER = [x for x in range(self.NUM_OF_LANE) ]
        self.chartMatrix, self.min_dist = self.chartToMatrix(chart)
        self.numpy = self.chartMatrix.to_numpy() #넘파이 배열로 변환저장
        
    def chartToMatrix(self,chart:osu.OSU)-> tuple[pd.DataFrame, float]:
        '''채보를 행렬로 바꿔줌 (기준은 minimum beat distance)'''
        df = chart.extractToPandas()
        beatstamps = df['beatstamp'].sort_values().unique()
        beatstampsEnds = df['endbeat'].sort_values().unique()
        maxOfLNBeat = 0 if np.nanmax(beatstampsEnds) is None else np.nanmax(beatstampsEnds)


        min_diff = np.diff(beatstamps).min() # 노트간 최소 비트 거리

        min_beatstamp = beatstamps.min() 
        max_beatstamp = beatstamps.max() \
            if beatstamps.max() >= maxOfLNBeat\
            else maxOfLNBeat

        beatstamp_points = np.arange(min_beatstamp, max_beatstamp + min_diff, min_diff)
        # 비트 스탬프 그리드를 위한 Point 생성

        grid = pd.DataFrame(beatstamp_points, columns=['beatstamp'])
        for lane in df['lane'].unique(): grid[lane] = 0.0
        # 포인트로 그리드 생성 및 그리드 완성

        for index, row in df.iterrows():
            start_stamp = row['beatstamp']
            lane = row['lane']
            if row['isLongNote']:
                end_stamp = row['endbeat'] if not pd.isna(row['endbeat']) else start_stamp
                # 그리드에서 해당 범위에 값 기록
                grid.loc[(grid['beatstamp'] == start_stamp), lane] = 1  # 시작점 1
                grid.loc[(grid['beatstamp'] == end_stamp), lane] = 1    # 끝점 1
                grid.loc[(grid['beatstamp'] > start_stamp) & (grid['beatstamp'] < end_stamp), lane] = 0.5  # 중간 값 0.5
            else:
                grid.loc[(grid['beatstamp'] == start_stamp), lane] = 1  # 단일 노트 1 기록

        grid = grid.drop(columns=['beatstamp'])
        return (grid, min_diff)
    
def is_equal_pattern_in_list(l:list, target_pattern:np.ndarray)->bool:
    '''리스트 안에 추출한 패턴과 같은 모양의 패턴이 있는지 확인하는 함수'''
    res = False
    for i in range(len(l)):
        if np.array_equal(l[i]["pattern"],target_pattern): 
            res = True; 
            l[i]['appearance'] += 1
            break
    return res
    

def extract_patterns_from_note_start_w_flex_window(cm:ChartMatrix,pHeight:int=4, externalList:list=None)->list[dict]:
    matrix = cm.numpy.copy()
    if externalList is None : sub_matrice = []
    else: sub_matrice = externalList
    ps = 0 # pattern start
    while ps < len(matrix):
        c_matrix = matrix[ps:ps+pHeight].copy() # 후보 매트릭스 추출
        left_boader = {"lane": 0, "modified": False}
        right_boader = {"lane": cm.NUM_OF_LANE-1, "modified": False} # 보더 정보 갱신

        for laneNo in range(cm.NUM_OF_LANE): 
            if left_boader["modified"]== False:
                for rowNo in range(len(c_matrix)): # 후보 매트릭스의 행수 만큼 확인
                    if c_matrix[rowNo, laneNo] != 0:
                        left_boader["lane"] = laneNo
                        left_boader["modified"] = True
            if right_boader["modified"]== False:
                for rowNo in range(len(c_matrix)): # 후보 매트릭스의 행수 만큼 확인
                    if c_matrix[rowNo, (cm.NUM_OF_LANE-1)-laneNo] != 0:
                        right_boader["lane"] = (cm.NUM_OF_LANE-1)-laneNo
                        right_boader["modified"] = True
            if right_boader["modified"] and left_boader["modified"]: break
    
        row_begin = left_boader["lane"];  row_end = right_boader["lane"]
        c_matrix = c_matrix[:,row_begin:row_end+1]

        if not is_equal_pattern_in_list(sub_matrice, c_matrix):
            sub_matrice.append({'pattern':c_matrix,'appearance':1})

        while ps < len(matrix):
            ps += 1
            if ps >= len(matrix) or np.any(matrix[ps, :] == 1):
                break

    sub_matrice = sorted(sub_matrice, key=lambda x:x["appearance"], reverse=True)
    return sub_matrice