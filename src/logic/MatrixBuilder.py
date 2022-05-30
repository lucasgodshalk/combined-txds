import math
from scipy.sparse import csc_matrix
import numpy as np
from lib.settings import Settings

class MatrixBuilder:
    def __init__(self, settings: Settings, size_Y) -> None:
        self.settings = settings
        self._row = []
        self._col = []
        self._val = []
        self._index = 0
        self._max_index = 0
        self.size_Y = size_Y

    def stamp(self, row, column, value):
        if math.isnan(value) or value == None:
            raise Exception("Invalid value")

        if self._index == self._max_index:
            self._row.append(row)
            self._col.append(column)
            self._val.append(value)
            self._index += 1
            self._max_index += 1
            return

        self._row[self._index] = row
        self._col[self._index] = column
        self._val[self._index] = value
        self._index += 1
        
    def clear(self, retain_idx = 0):
        self._index = retain_idx

    def to_matrix(self):
        if self.settings.debug and self._max_index != self._index:
            raise Exception("Solver was not fully utilized. Garbage data remains")

        if self.settings.use_sparse:
            matrix = csc_matrix((self._val, (self._row, self._col)))
        else:
            matrix = np.zeros((self.size_Y, self.size_Y))

            for idx in range(self._max_index):
                matrix[self._row[idx], self._col[idx]] += self._val[idx]

        return matrix

    def assert_valid(self, check_zeros=False):
        if not self.settings.debug:
            return

        if max(self._row) != max(self._col):
            raise Exception("Matrix is not square")
        
        if not check_zeros:
            return

        matrix = csc_matrix((self._val, (self._row, self._col))).todense()

        for row_idx in range(matrix.shape[0]):
            all_zeros = True
            for col_idx in range(matrix.shape[1]):
                if matrix[row_idx, col_idx] != 0:
                    all_zeros = False
            
            if all_zeros:
                raise Exception(f'Row {row_idx} is invalid')

        for col_idx in range(matrix.shape[1]):
            all_zeros = True
            for row_idx in range(matrix.shape[0]):
                if matrix[row_idx, col_idx] != 0:
                    all_zeros = False
            
            if all_zeros:
                raise Exception(f'Column {col_idx} is invalid')

    def get_usage(self):
        return self._index