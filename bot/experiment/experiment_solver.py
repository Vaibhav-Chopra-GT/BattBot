import pybamm


def experiment_solver(
    model,
    experiment,
    chemistry,
    solver,
    param_values,
    degradation_parameter
):
    """
    This function simulates and solves experiments with a given model,
    chemistry.
    Parameters:
        model: pybamm.BaseModel
        experiment: pybamm.Experiment
        chemistry: dict
        solver: pybamm.BaseSolver
        param_values: list
            Varied values of degradation_parameter
        degradation_parameter: str
            Parameter to be varied
    Returns:
        sim: pybamm.Simulation
        solutions_and_labels: list
    """

    parameter_values = pybamm.ParameterValues(chemistry=chemistry)

    solutions_and_labels = []
    param_list = []
    for i in range(0, len(param_values)):
        # copy the original values and append them in the list
        param_list.append(parameter_values.copy())

        # change a parameter value
        param_list[i][
            degradation_parameter
        ] = param_values[i]

        sim = pybamm.Simulation(
            model=model,
            experiment=experiment,
            parameter_values=param_list[i],
            solver=solver,
        )
        if chemistry == pybamm.parameter_sets.Ai2020:
            sim.solve(calc_esoh=False)
        else:
            sim.solve()
        solution = sim.solution
        solutions_and_labels.append([
            solution, degradation_parameter + ": " + str(param_values[i])
        ])
    return sim, solutions_and_labels
