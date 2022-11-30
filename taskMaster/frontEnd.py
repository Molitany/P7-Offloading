from flask import Flask
from collections import deque
from matrixGenerator import generate_matrices
from globals import task_queue 
app = Flask(__name__)

@app.route("/", methods=["GET"])
def receive_task():
    '''Generate matrix when this endpoint is hit.'''
    task_queue.extend(generate_matrices(amount=7, min_mat_shape=300, max_mat_shape=300, fixed_seed=False))
    return 'ok'

def start_frontend():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)