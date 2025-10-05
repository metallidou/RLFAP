import sys
import os
import time
import multiprocessing

from csp import CSP
from csp2 import backtracking_search
from csp2 import fc_cbj_search

from csp2 import forward_checking
from csp2 import mac
from csp import lcv

from csp import min_conflicts
from csp2 import dom_wdeg_heuristic

# ________________________________________________________________________________________________________________________________________________
#

# Rlfap is a class that holds information about the problem,
# such as instance, variables, domains, neighbors and constraints,
# after processing the corresponding files
class Rlfap():

    def __init__(self, instance):
        self.instance = instance
        self.variables = dict()
        self.set_variables()
        self.domains = dict()
        self.set_domains()
        self.constraints = dict()
        self.set_constraints()
        self.neighbors = dict()
        self.set_neighbors()
        self.constraint_checks = 0

    def get_var_file(self):
        return self.get_instance_file("../instances/var")

    def get_dom_file(self):
        return self.get_instance_file("../instances/dom")

    def get_ctr_file(self):
        return self.get_instance_file("../instances/ctr")

    # This method returns the instance file path of type var, dom or ctr
    def get_instance_file(self, directory):
        if self.instance == "11":
            return str(directory + "/" + directory[-3:] + "11.txt")
        for root, _, files in os.walk(directory):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if self.instance in file_name:
                    return file_path
        return None

    # This method sets self.variables, a dict of {var:dom, ...}
    # after reading var file
    def set_variables(self):
        var = self.get_var_file()
        with open(var, 'r') as file:
            file.readline()
            lines = file.readlines()
            for line in lines:
                numbers = line.split()
                self.variables[int(numbers[0])] = int(numbers[1])

    # This method sets self.domains, a dict of {var:[value1,value2,...]}
    # after reading dom file
    def set_domains(self):
        dom = self.get_dom_file()
        with open(dom, 'r') as file:
            file.readline()
            lines = file.readlines()
            for line in lines:
                numbers = line.split()
                d = int(numbers[0])
                for key in self.variables.keys():
                    domain = self.variables[key]
                    if domain == d:
                        self.domains[key] = [int(value) for value in numbers[2:]]

    # This method sets self.constraints, a dict of {var1:{var2:[op,constr]},...}
    # after reading ctr file
    def set_constraints(self):
        ctr = self.get_ctr_file()
        with open(ctr, 'r') as file:
            file.readline()
            lines = file.readlines()
            for line in lines:
                numbers = line.split()
                var1 = int(numbers[0])
                var2 = int(numbers[1])
                op = numbers[2]
                constr = int(numbers[3])
                if not self.constraints.get(var1):
                    self.constraints[var1] = dict()
                if not self.constraints[var1].get(var2):
                    self.constraints[var1][var2] = []
                self.constraints[var1][var2].append((op, constr))
                if not self.constraints.get(var2):
                    self.constraints[var2] = dict()
                if not self.constraints[var2].get(var1):
                    self.constraints[var2][var1] = []
                self.constraints[var2][var1].append((op, constr))

    # This method sets self.neighbors, using self.constraints
    def set_neighbors(self):
        for var1 in self.variables.keys():
            n = []
            if self.constraints.get(var1):
                for var2 in self.constraints[var1]:
                    n.append(var2)
            self.neighbors[var1] = n.copy()

# ________________________________________________________________________________________________________________________________________________
#


def f(A: int, a: int, B: int, b: int):
    rlfap.constraint_checks += 1
    constraint = rlfap.constraints[A][B][0]
    op, k = constraint

    if op == '>':
        return abs(a - b) > k
    elif op == '=':
        return abs(a - b) == k
    return False


# This function solves an individual csp problem, which is user defined
def individual(instance, algorithm):
    global rlfap
    rlfap = Rlfap(instance)
    csp = CSP(list(rlfap.variables.keys()), rlfap.domains, rlfap.neighbors, f)
    result, time, constraint_checks, assigns = solve(csp, algorithm)
    print_result(algorithm, instance, result, True, time, constraint_checks, assigns)


# This function solves all csp problems that can be created with the instances and algorithms above
def all():
    instances = {0: "2-f24", 1: "2-f25", 2: "3-f10", 3: "3-f11",
                 4: "6-w2", 5: "7-w1-f4", 6: "7-w1-f5", 7: "8-f10",
                 8: "8-f11", 9: "11", 10: "14-f27", 11: "14-f28"}

    algorithms = {0: "fc-bt", 1: "mac-bt", 2: "fc-cbj", 3: "min"}

    for a in range(len(algorithms)):
        for i in range(len(instances)):
            global rlfap
            rlfap = Rlfap(instances[i])
            csp = CSP(list(rlfap.variables.keys()), rlfap.domains, rlfap.neighbors, f)
            result, time, constraint_checks, assigns = solve(csp, algorithms[a])
            print_result(algorithms[a], instances[i], result, False, time,
                         constraint_checks.value, assigns.value)


# Main solving function
def solve(csp, algorithm):
    start_time = time.time()
    # Method 'Manager' is imported from multiprocessing
    # to keep solution data after process is killed
    manager = multiprocessing.Manager()
    result = manager.dict()
    constraint_checks = manager.Value('i', 0)
    assigns = manager.Value('i', 0)
    # To keep track of time trying to solve csp,
    # we assume solve_problem function to be a process
    p = multiprocessing.Process(target=solve_csp, name="solve_csp",
                                args=(csp, algorithm, result, constraint_checks, assigns))
    p.start()
    # Process has a running limit of 500 sec before it is killed
    p.join(500)
    # Then process exceeded 500 sec, so timeout
    if p.is_alive():
        p.terminate()
        elapsed_time = 500
    # Process was killed in time
    else:
        # Mark down ending time
        end_time = time.time()
        elapsed_time = end_time - start_time
        result = result[0]
    return result, elapsed_time, constraint_checks, assigns


# This function solves a problem using a csp search algorithm
def solve_csp(csp, algorithm, result, constraint_checks, assigns):
    if algorithm == "FC-BT" or algorithm == "fc-bt":
        result[0] = backtracking_search(csp, dom_wdeg_heuristic, lcv, forward_checking)
    elif algorithm == "MAC-BT" or algorithm == "mac-bt":
        result[0] = backtracking_search(csp, dom_wdeg_heuristic, lcv, mac)
    elif algorithm == "FC-CBJ" or algorithm == "fc-cbj":
        result[0] = fc_cbj_search(csp, dom_wdeg_heuristic, lcv)
    elif algorithm == "MIN" or algorithm == "min":
        result[0] = min_conflicts(csp, )
    else:
        print("Invalid argument")
        result[0] = None
        exit()
    constraint_checks.value = rlfap.constraint_checks
    assigns.value = csp.nassigns


# Writes down a brief or analytic result
def print_result(algorithm, instance, result, analytic: bool,
                 elapsed_time, constraint_checks, assigns):
    # Function is being called for the first time, empty file
    if not hasattr(print_result, 'first_call'):
        print_result.first_call = True
        with open(algorithm + ".txt", "w") as file:
            file.truncate(0)
    # Open corresponding file to write down results
    with open(algorithm + ".txt", "a") as file:
        file.write(instance + "\n")
        if elapsed_time == 500:
            file.write("Timeout\n")
        else:
            file.write(f"Elapsed time: {elapsed_time} seconds\n")
            file.write(f"Constraint checks: {constraint_checks}\n")
            file.write(f"Number of assignments: {assigns}\n")
            if result:
                file.write("Result found\n")
                # Then print all final value assignments
                if analytic:
                    with open("result.txt", "w") as result_file:
                        result_file.write(instance + "\t" + algorithm)
                        result_file.write("\n")
                        for var in sorted(result.keys()):
                            result_file.write(f"{var} : {result[var]}\n")
            else:
                file.write("No result found\n")
        file.write("\n")


if __name__ == '__main__':
    # Then solve all csp problems, with all instances and algorithms
    if sys.argv[1] == "all":
        all()
    # Invalid input
    elif len(sys.argv) < 3:
        print("Usage: python script.py <file_type> <directory>")
        exit()
    # Then solve an individual csp problem
    else:
        individual(sys.argv[1], sys.argv[2])
