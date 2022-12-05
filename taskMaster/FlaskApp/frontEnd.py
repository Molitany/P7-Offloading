from enum import Enum
from flask import Flask, render_template, request
from globals import client_inputs
app = Flask(__name__)

class Frequency(Enum):
    '''Enum to handle frequency'''
    Slow = 1
    Medium = 5
    Fast = 10
    No_Limit = -1

def get_offloading_parameters(form):
    '''Get the offloading parameters for the offloading from the front end.'''
    offloading_parameters = {}

    # print("""What type of offloading to use?
    # Auction (default) 
    # Contract (not implemented)
    # First come, first server (FCFS) (not implemented)\n""") #We could just define our 4 types here, normal, with fines, with max_reward, both and save some enter
    offloading_parameters["offloading_type"] = "Auction"

    if offloading_parameters["offloading_type"] == "Auction" or offloading_parameters["offloading_type"] == "auction":
        # print("""What auction type to use?
        # Second Price Sealed Bid (SPSB) (default)
        # First Price Sealed Bid (FPSB)\n""")
        offloading_parameters["auction_type"] = form.get('auction_type', "SPSB") #input() or "SPSB"

    # print("""Do the tasks have deadlines?
    # No (Default)
    # Yes \n""")
    offloading_parameters["deadlines"] = bool(request.form.get('deadlines') == 'on' if True else False) #input() or "No"

    # print("""Are there fines for abandoning a job or going over a possible deadline?
    # No (default)
    # Yes \n""")
    offloading_parameters["fines"] = bool(request.form.get('fines') == 'on' if True else False) #input() or "No"

    # print("""Is there a max reward for the tasks?
    # No (Default) 
    # Yes \n""")
    offloading_parameters["max_reward"] = bool(request.form.get('max_reward') == 'on' if True else False) #input() or "No"

    #Simply add more cases to each of these or more categories
    #Handling of types is later and on the machines
    #Stuff likes this can also be split into seperate functions or its own file if needed

    return offloading_parameters

@app.route('/add-tasks', methods=['POST'])
def add_tasks():
    if request.form:
        client_inputs.append({
            'amount': int(request.form.get('amount')),
            'min_mat_shape': int(request.form.get('min_mat_shape')), 
            'max_mat_shape': int(request.form.get('max_mat_shape')),
            'min_deadline': float(request.form.get('min_deadline')),
            'max_deadline': float(request.form.get('max_deadline')),
            'task_frequency': Frequency[request.form.get('task_frequency', "Medium")].value,
            'fixed_seed': bool(request.form.get('fixed_seed') == 'on' if True else False),
            'offloading_parameters': get_offloading_parameters(request.form)
        })
        return 'Task received'

@app.route("/", methods=["GET"])
def receive_task():
    return render_template('index.html')



def start_frontend():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)