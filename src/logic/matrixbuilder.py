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

        matrix = csc_matrix((self._val, (self._row, self._col)))

        if not np.all(matrix.getnnz(1)>0):
            zero_rows = np.where(matrix.getnnz(1)==0)
            raise Exception(f'Row {zero_rows} is invalid')

        if not np.all(matrix.getnnz(0)>0):
            zero_cols = np.where(matrix.getnnz(0)==0)
            raise Exception(f'Column {zero_cols} is invalid')

    def get_usage(self):
        return self._index