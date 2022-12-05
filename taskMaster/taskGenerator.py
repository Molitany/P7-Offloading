from collections import deque
import numpy
import random


def _average(lst):
    return sum(lst) / len(lst)


def generate_tasks(amount=5, min_mat_shape=75, max_mat_shape=125, min_deadline=10, max_deadline=75, fixed_seed=True, offloading_parameters={}) -> deque[dict]:
    '''
    Generates matrix pairs with the given parameters.\n
    The pairs have a deadline_seconds, max_reward and max_shape_number, fine and offloading_parameters.
    '''
    if fixed_seed:
        random.seed(69)

    matrix_array = deque()
    for i in range(0, amount):
        shape_numbers = random.choices(
            range(min_mat_shape, max_mat_shape+1), k=3)
        mat1 = numpy.random.rand(shape_numbers[0], shape_numbers[1])
        mat2 = numpy.random.rand(shape_numbers[1], shape_numbers[2])
        deadline_seconds = random.uniform(min_deadline, max_deadline)

        a: list = list()
        b: list = list()
        for i in range(len(mat1)):
            a.append(list(mat1[i]))
        for i in range(len(mat2)):
            b.append(list(mat2[i]))

        deadline_difference = max_deadline - deadline_seconds if max_deadline - deadline_seconds > 0 else max_deadline
        offloading_parameters['deadline_seconds'] = deadline_seconds
        offloading_parameters['max_reward'] = deadline_difference * _average(shape_numbers)
        offloading_parameters['fines'] = offloading_parameters.get('max_reward') * 2 if offloading_parameters.get('fines') else 0

        pair = {
            'mat1': a,
            'mat2': b,
            'max_shape_number': max(shape_numbers),
            'offloading_parameters': offloading_parameters
        }
        matrix_array.append(pair)
    return matrix_array
