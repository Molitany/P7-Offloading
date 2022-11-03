import pytest
import numpy as np

class TestMatrixMultiplication:

    #arrange
    @pytest.fixture
    def test_input():
        return np.array([[1,2,3],[4,5,6],[7,8,9],[10,12,14]])
    
    @pytest.fixture
    def test_input_second():
        return np.array([[1,2,3,10],[4,5,6,10],[7,8,9,10]])
    
    def test_matrix_multiplication(test_input, test_input_second):
        #act
        vector_pairs, array_to_be_filled = split_matrix(test1, test2)
        dot_products = calc_split_matrix(vector_pairs)
        dot_product_matrix = np.array(fill_array(dot_products, array_to_be_filled))
        #assert
        assert dot_product_matrix == np.matmul(matrix0, matrix1).tolist


    # def test_split_matrix():
    #     vector_pairs, array_to_be_filled = split_matrix(test1, test2)
    #     assert vector_pairs == 0
    #     assert array_to_be_filled == 0

    # def test_fill_array():
    #     assert fill_array() == dot_product_array

    # def test_calc_split_matrix():
    #     assert calc_split_matrix() == dot_products