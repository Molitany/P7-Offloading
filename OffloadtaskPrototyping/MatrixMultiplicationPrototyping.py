from cgi import test
import numpy as np

#TEST DATA, would come in from the phone
test1 = np.array([[1,2,3],
                  [4,5,6], 
                  [7,8,9],
                  [10,12,14]])

test2 = np.array([[1,2,3,10],
                  [4,5,6,10], 
                  [7,8,9,10]])

print(np.matmul(test1, test2))


#SERVER CODE
def split_matrix(a,b):
    array_to_be_filled = np.zeros((np.shape(a)[0], np.shape(b)[1]))
    vector_pairs= []
    if(np.shape(a)[1] == np.shape(b)[0]):
        for i in range(0,np.shape(a)[0]):
            for j in range(0, np.shape(b)[1]):
                vector_pairs.append({'vector' : [a[i, :].tolist(), b[:, j].tolist()],
                                     'cell' : [i,j]})
    else:
        print('illegal vector multiplication')
    return vector_pairs, array_to_be_filled

def fill_array(dot_products, array_to_be_filled):
    for dot_product in dot_products:
        array_to_be_filled[dot_product['cell'][0]][dot_product['cell'][1]] = dot_product['dot_product']
    return array_to_be_filled.tolist()



#LOCAL MACHINE CODE
def calc_split_matrix(vector_pairs):
    dot_products = []
    for pair in vector_pairs:
        dot_products.append({'dot_product' : np.dot(pair['vector'][0], pair['vector'][1]),
                             'cell' : pair['cell']})
    return dot_products


#EXECUTION ORDER

#First the server splits the incoming matrices into vectors
vector_pairs, array_to_be_filled = split_matrix(test1, test2)

#This is then sent to local machines who each calculate their portion of the vector pairs, resulting in a list of dot products that is returned to the server
dot_products = calc_split_matrix(vector_pairs)

#The server than takes the lists of dot products and fills them into their appropriate cells
dot_product_array = fill_array(dot_products, array_to_be_filled)

#This would then be sent back to the local machine
print(np.array(dot_product_array))
test = np.array([[ 30,36,42,60],
 [ 66,81,96,150],
 [102,126,151,240],
 [156,192,228,360]])
print(test == np.matmul(test1, test2))