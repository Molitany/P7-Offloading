import time
import numpy as np

# Generate two random 1000x1000 matrices
matrix1 = np.random.rand(1000, 1000)
matrix2 = np.random.rand(1000, 1000)

# Record the start time
start_time = time.time()

# Use NumPy to multiply the matrices
result = np.matmul(matrix1, matrix2)
print(result)
print(result.shape)
# Record the end time
end_time = time.time()

# Calculate the elapsed time
elapsed_time = end_time - start_time

# Print the elapsed time
print(f"Elapsed time: {elapsed_time} seconds")
