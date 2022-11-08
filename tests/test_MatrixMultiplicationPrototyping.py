import pytest
import numpy as np
from OffloadtaskPrototyping import MatrixMultiplicationPrototyping as M

class TestMatrixMultiplication:
    def test_matrix_multiplication(self):
         #arrange
        data1 = np.array([[1,2,3],[4,5,6],[7,8,9],[10,12,14]])
        data2 = np.array([[1,2,3,10],[4,5,6,10],[7,8,9,10]])

        #act
        vector_pairs, array_to_be_filled = M.split_matrix(data1, data2)
        dot_products = M.calc_split_matrix(vector_pairs)
        dot_product_matrix = np.array(M.fill_array(dot_products, array_to_be_filled))
        #assert
        assert (np.array(dot_product_matrix) == np.matmul(data1, data2)).all()