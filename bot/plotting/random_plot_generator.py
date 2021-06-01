import pybamm
import random
from plotting.plot_graph import plot_graph
from models.model_solver import model_solver
from utils.chemistry_generator import chemistry_generator
from utils.single_point_decimal import single_decimal_point
from experiment.experiment_generator import experiment_generator
from experiment.experiment_solver import experiment_solver
from plotting.summary_variables import generate_summary_variables


def random_plot_generator(
    testing=False,
    provided_choice=None,
    provided_number_of_comp=None,
    plot_summary_variables=True
):
    """
    Generates a random plot.
    Parameters:
        testing: bool
            default: None
        provided_choice: numerical
            default: None
        provided_number_of_comp: numerical
            default: None
        plot_summary_variables: bool
            default: True
    Returns:
        model: pybamm.BaseModel
        parameter_values: pybamm.ParameterValues
        time: numerical (seconds) or None
        chemistry: dict
        solver: pybamm.BaseSolver
        is_experiment: bool
        cycle: list
        number: numerical
        is_comparison: bool
    """

    while True:

        try:

            models = [
                pybamm.lithium_ion.DFN(),
                pybamm.lithium_ion.SPM(),
                pybamm.lithium_ion.SPMe(),
            ]

            model_num = random.randint(0, len(models) - 1)
            model = models[model_num]

            chemistries = [
                # pybamm.parameter_sets.Ai2020,
                pybamm.parameter_sets.Chen2020,
                pybamm.parameter_sets.Marquis2019,
                # pybamm.parameter_sets.Ecker2015,
                # pybamm.parameter_sets.Ramadass2004,
            ]

            chem_num = random.randint(0, len(chemistries) - 1)
            chemistry = chemistries[chem_num]

            solvers = [
                pybamm.CasadiSolver(mode="safe"),
                pybamm.CasadiSolver(mode="fast with events"),
            ]

            solver_num = random.randint(0, len(solvers) - 1)
            solver = solvers[solver_num]

            lower_voltage = chemistry_generator(chemistry)

            choice = random.randint(0, 2)
            if testing is True and provided_choice is not None:
                choice = provided_choice

            if choice == 0:

                c_rate = random.randint(0, 3)
                (parameter_values, sim, solution) = model_solver(
                    model=model,
                    chemistry=chemistry,
                    solver=solver,
                    c_rate=c_rate,
                    lower_voltage=lower_voltage,
                )

                time = plot_graph(solution, sim)

                return (
                    model,
                    parameter_values,
                    time,
                    chemistry,
                    solver,
                    False,
                    None,
                    None,
                    False,
                )

            elif choice == 1:
                (
                    cycle_received,
                    number,
                ) = experiment_generator()
                if testing:
                    number = 10
                if number > 3 and plot_summary_variables:

                    experiment = pybamm.Experiment(
                        cycle_received * number, termination="80% capacity"
                    )
                    (
                        sim,
                        solution,
                        parameter_values
                    ) = experiment_solver(
                        model=model,
                        experiment=experiment,
                        chemistry=chemistry,
                        solver=solver
                    )
                    generate_summary_variables(solution)
                    return (
                        model,
                        parameter_values,
                        None,
                        chemistry,
                        solver,
                        True,
                        cycle_received,
                        number,
                        False,
                    )
                if testing:
                    number = 1
                experiment = pybamm.Experiment(cycle_received * number)
                (sim, solution, parameter_values) = experiment_solver(
                    model, experiment, chemistry, solver
                )
                time = plot_graph(solution, sim)
                return (
                    model,
                    parameter_values,
                    time,
                    chemistry,
                    solver,
                    True,
                    cycle_received,
                    number,
                    False,
                )

            elif choice == 2:

                number_of_comp = random.randint(1, 3)
                random.shuffle(models)
                models_for_comp = models[:number_of_comp]
                models_for_comp = dict(list(enumerate(models_for_comp)))
                params = pybamm.ParameterValues(chemistry=chemistry)
                parameter_values_for_comp = dict(list(enumerate([params])))

                if (
                    number_of_comp == 1
                    or (
                        testing
                        and provided_number_of_comp == 1
                    )
                ):
                    param_list = []
                    diff_params = random.randint(2, 3)
                    for i in range(0, diff_params):
                        param_list.append(params.copy())
                        param_list[i][
                            "Current function [A]"
                        ] = single_decimal_point(2, 7, 0.1)
                    parameter_values_for_comp = dict(
                        list(enumerate(param_list))
                    )

                s = pybamm.BatchStudy(
                    models=models_for_comp,
                    parameter_values=parameter_values_for_comp,
                    permutations=True,
                )

                s.solve([0, 3700])

                time = plot_graph(sim=s.sims)

                return (
                    models_for_comp,
                    params,
                    time,
                    chemistry,
                    None,
                    False,
                    None,
                    None,
                    True,
                )
        except Exception as e: # noqa
            print(e)
