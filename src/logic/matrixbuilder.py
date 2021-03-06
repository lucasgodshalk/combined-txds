import math
from scipy.sparse import csc_matrix
import numpy as np
from sympy import Matrix
from logic.powerflowsettings import PowerFlowSettings

class MatrixBuilder:
    def __init__(self, settings: PowerFlowSettings) -> None:
        self.settings = settings
        self._row = []
        self._col = []
        self._val = []
        self._index = 0
        self._max_index = 0

    def stamp(self, row, column, value):
        if value == 0:
            return

        if self.settings.debug:
            if type(row) != int or row < 0:
                raise Exception("Invalid row index")
            elif type(column) != int or column < 0:
                raise Exception("Invalid column index")
            elif math.isnan(value) or value == None or (type(value) != int and type(value) != float and type(value) != np.float64):
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

    def to_matrix(self) -> csc_matrix:
        if self.settings.debug and self._max_index != self._index:
            raise Exception("Solver was not fully utilized. Garbage data remains")

        return csc_matrix((self._val, (self._row, self._col)), dtype=np.float64)

    def get_row(self, row_idx):
        for idx in range(self._index):
            row = self._row[idx]
            if row == row_idx:
                yield (self._col[idx], self._val[idx])

    def get_col(self, col_idx):
        for idx in range(self._index):
            col = self._col[idx]
            if col == col_idx:
                yield (self._row[idx], self._val[idx])

    def to_symbolic_matrix(self):
        rows = []
        for _ in range(max(self._row) + 1):
            rows.append([0] * (max(self._col) + 1))
        for (row, col, value) in zip(self._row, self._col, self._val):
            rows[row][col] += value
        return Matrix(rows)

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