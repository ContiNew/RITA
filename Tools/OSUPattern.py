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
        min_diff = np.diff(beatstamps).min() # 노트간 최소 비트 거리

        min_beatstamp = beatstamps.min()
        max_beatstamp = beatstamps.max()
        beatstamp_points = np.arange(min_beatstamp, max_beatstamp + min_diff, min_diff)
        # 비트 스탬프 그리드를 위한 Point 생성

        grid = pd.DataFrame(beatstamp_points, columns=['beatstamp'])
        for lane in df['lane'].unique(): grid[lane] = 0
        # 포인트로 그리드 생성 및 그리드 완성

        df = df.pivot_table(index='beatstamp', columns='lane', aggfunc='size', fill_value=0).reset_index()
        # 차트 데이터 프레임을 그리드와 합치기 위한 Form으로 바꿔줌
        merged_df = pd.merge(grid, df, on='beatstamp', how='left').fillna(0)
        
        for col in merged_df.filter(like='_x').columns:
            merged_df[col.replace('_x', '')] = merged_df[col.replace('_x', '_y')]
            merged_df.drop([col, col.replace('_x', '_y')], axis=1, inplace=True)

        merged_df.set_index('beatstamp', inplace=True)
        merged_df = merged_df.astype(int)
        try:
            merged_df = merged_df[self.LANE_ORDER] # 인게임에서의 순서대로 열정렬.
        except KeyError:
            missed_cols = [col for col in self.LANE_ORDER if col not in merged_df.columns]
            for col in missed_cols:
                merged_df[col] = 0  # 해당 열을 추가하고 0으로 채움

        merged_df[merged_df>=2]=1

        return (merged_df, min_diff)
    
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
        right_boader = {"lane": 7, "modified": False} # 보더 정보 갱신

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
            if ps >= len(matrix) or not (matrix[ps, :] == 0).all():
                break

    sub_matrice = sorted(sub_matrice, key=lambda x:x["appearance"], reverse=True)
    return sub_matrice