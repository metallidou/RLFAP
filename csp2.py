import math

from csp import first_unassigned_variable
from csp import unordered_domain_values
from csp import no_inference
from csp import partition
from csp import dom_j_up

conflict_set = dict()
weight = dict()


# ________________________________________________________________________________________________________
# Forward Checking

# Similar to forward_checking in csp.py
# Just adds to conflict set and increases variable weights when domain wipeout occurs
def forward_checking(csp, var, value, assignment, removals):
    """Prune neighbor values inconsistent with var=value."""
    csp.support_pruning()
    for B in csp.neighbors[var]:
        if B not in assignment:
            for b in csp.curr_domains[B][:]:
                if not csp.constraints(var, value, B, b):
                    csp.prune(B, b, removals)
            # Domain wipeout
            if not csp.curr_domains[B]:
                # Then fc-cbj is used
                if conflict_set != {}:
                    conflict_set[B].add(var)
                # Then dom/wdeg heuristic is used
                if weight != {}:
                    weight[(var, B)] += 1
                    weight[(B, var)] += 1
                return False
    return True

# ________________________________________________________________________________________________________
# Maintain Arc Consistency


def AC3(csp, queue=None, removals=None, arc_heuristic=dom_j_up):
    """[Figure 6.3]"""
    if queue is None:
        queue = {(Xi, Xk) for Xi in csp.variables for Xk in csp.neighbors[Xi]}
    csp.support_pruning()
    queue = arc_heuristic(csp, queue)
    checks = 0
    while queue:
        (Xi, Xj) = queue.pop()
        revised, checks = revise(csp, Xi, Xj, removals, checks)
        if revised:
            if not csp.curr_domains[Xi]:
                return False, checks  # CSP is inconsistent
            for Xk in csp.neighbors[Xi]:
                if Xk != Xj:
                    queue.add((Xk, Xi))
    return True, checks  # CSP is satisfiable


def revise(csp, Xi, Xj, removals, checks=0):
    """Return true if we remove a value."""
    revised = False
    for x in csp.curr_domains[Xi][:]:
        # If Xi=x conflicts with Xj=y for every possible y, eliminate Xi=x
        # if all(not csp.constraints(Xi, x, Xj, y) for y in csp.curr_domains[Xj]):
        conflict = True
        for y in csp.curr_domains[Xj]:
            if csp.constraints(Xi, x, Xj, y):
                conflict = False
            checks += 1
            if not conflict:
                break
        if conflict:
            csp.prune(Xi, x, removals)
            revised = True
    # Then domain wipeout
    if not csp.curr_domains[Xi]:
        weight[(Xi, Xj)] += 1
        weight[(Xj, Xi)] += 1
    return revised, checks


def mac(csp, var, value, assignment, removals, constraint_propagation=AC3):
    """Maintain arc consistency."""
    return constraint_propagation(csp, {(X, var) for X in csp.neighbors[var]}, removals)

# ________________________________________________________________________________________________________
# Backtracking


def backtracking_search(csp, select_unassigned_variable=first_unassigned_variable,
                        order_domain_values=unordered_domain_values, inference=no_inference):
    """[Figure 6.5]"""

    def backtrack(assignment):
        if len(assignment) == len(csp.variables):
            return assignment
        var = select_unassigned_variable(assignment, csp)
        for value in order_domain_values(var, assignment, csp):
            if 0 == csp.nconflicts(var, value, assignment):
                csp.assign(var, value, assignment)
                removals = csp.suppose(var, value)
                if inference(csp, var, value, assignment, removals):
                    result = backtrack(assignment)
                    if result is not None:
                        return result
                csp.restore(removals)
        csp.unassign(var, assignment)
        return None

    result = backtrack({})
    assert result is None or csp.goal_test(result)
    conflict_set.clear()
    weight.clear()
    return result

# ________________________________________________________________________________________________________
# Forward Checking - Constraint Backjumping


def fc_cbj_search(csp, select_unassigned_variable=first_unassigned_variable,
                        order_domain_values=unordered_domain_values):
    # Conflict set is of type dict = {var: set(), ...}
    for v in csp.variables:
        conflict_set[v] = set()
    # A dict that holds order of assignments
    var_order = {var: 0 for var in csp.variables}
    # Set of visited variables
    visited = set()
    # A counter
    i = 0

    # This function basically implements the main FC-CBJ procedure
    def fc_cbj(assignment):
        # Static i
        nonlocal i
        if len(assignment) == len(csp.variables):
            return assignment, None
        var = select_unassigned_variable(assignment, csp)
        # The current var to be assigned gets an index indicating its order
        var_order[var] = i
        # For next assignment
        i += 1
        for value in order_domain_values(var, assignment, csp):
            if 0 == csp.nconflicts(var, value, assignment):
                csp.assign(var, value, assignment)
                removals = csp.suppose(var, value)
                if forward_checking(csp, var, value, assignment, removals):
                    # u is used in case of a backjumping procedure
                    result, u = fc_cbj(assignment)
                    # Then a result is found so no backjumping needed
                    if result is not None:
                        return result, None
                    # Then no result is found, but a backjumping needs to be done
                    # u is the last conflict var had with
                    elif var in visited and var != u:
                        # Go back to u and erase var data
                        conflict_set[var].clear()
                        visited.discard(var)
                        csp.restore(removals)
                        csp.unassign(var, assignment)
                        return None, u
                csp.restore(removals)
        csp.unassign(var, assignment)
        visited.add(var)
        # A value for var was not found, so we need to detect its last conflict
        u = None
        max_order = 0
        if conflict_set[var]:
            # To get var's last conflict we detect the variable conflict with the highest order
            for v in conflict_set[var]:
                if var_order[v] > max_order:
                    max_order = var_order[v]
                    u = v
            # Then no solution, because backjumping cannot be done on first variable
            if u is None:
                return None, u
            # Its new conflict set is: conf(Xi) = conf(Xi) U conf(Xj) - {Xi}
            conflict_set[u] |= conflict_set[var] - {u}
        return None, u

    result, _ = fc_cbj({})
    conflict_set.clear()
    weight.clear()
    assert result is None or csp.goal_test(result)
    return result

# ________________________________________________________________________________________________________
# Dom/wdeg heuristic


def dom_wdeg_heuristic(assignment, csp):

    if weight == {}:
        for v in csp.variables:
            for u in csp.neighbors[v]:
                weight[(v,u)] = 1
                weight[(u,v)] = 1

    # This is an evaluation function that chooses the best variable to be assigned next
    def dom_wdeg():
        wdeg = dict()
        w = float('inf')
        var = None
        # Search through all variables
        for v in csp.variables:
            # Then var has already been assigned, so next
            wdeg[v] = 1
            if v in assignment:
                continue
            # Search through all neighbors of variable
            for u in csp.neighbors[v]:
                # wdeg = sum(weight(neighbors[v]))
                wdeg[v] += weight[(v,u)]
            # a_wdeg = (number of domains)/(wdeg)
            if csp.curr_domains is not None:
                a_wdeg = float(len(csp.curr_domains[v])/wdeg[v])
            else:
                a_wdeg = float(len(csp.domains[v]) / wdeg[v])
            # To get variable with min a_wdeg score
            if a_wdeg < w:
                w = a_wdeg
                var = v
        return var

    return dom_wdeg()
