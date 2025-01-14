import os
import sys

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.templated_simulation import TemplatedSimulations
from idmtools.entities.experiment import Experiment

from emodpy.collections_utils import deep_set
from emodpy.emod_task import EMODTask


CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(CURRENT_DIRECTORY, "inputs")
BIN_PATH = os.path.join("..", "inputs", "bin")

expname = 'example_sweep_demographics'

demo_files = [os.path.join(INPUT_PATH, "demographics.json"),
              os.path.join(INPUT_PATH, "PFA_rates_overlay.json"),
              os.path.join(INPUT_PATH, "pfa_simple.json"),
              os.path.join(INPUT_PATH, "uniform_demographics.json")]


def replace_pfa_with_custom(simulation, pfa_informal_rate):
    """
    This function shows how to edit demographics coming from the experiment.
    The trick here is that the experiment demographics passed to the simulation are immutable (they are part of the
    experiment's collection).
    Therefore, the only way to edit them is to remove them and recreate a modified version.

    You will notice that the `PFA_rates_overlay.json` is still present in the experiment asset (unused) but the
    PFA_rates_overlay_modified.json is in the simulation working directory and is used in config.json
    """
    # We cannot edit the demographics coming from the experiment but we can replace it
    # Pop the PFA_Rates_overlay.json
    demographic_asset = simulation.task.demographics.pop(filename="PFA_rates_overlay.json")
    demographic_content = demographic_asset.content

    # Modify what we need
    deep_set(demographic_content,
             "Defaults.Society.INFORMAL.Pair_Formation_Parameters.Formation_Rate_Constant",
             pfa_informal_rate)

    # Add it to our simulation
    simulation.task.simulation_demographics.add_demographics_from_dict(demographic_content, "PFA_rates_overlay_modified.json")
    # return our tags
    return dict(pfa_rate=pfa_informal_rate)


# this is not working cause we can not find demographics.json in working dir
def sweep_on_demographics_param() -> 'TemplatedSimulations':
    task = EMODTask.from_files(eradication_path=os.path.join(BIN_PATH, "Eradication.exe"),
                               config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"), demographics_paths=demo_files)

    ts = TemplatedSimulations(base_task=task)
    b = SimulationBuilder()
    b.add_sweep_definition(replace_pfa_with_custom, (.1, .2, .5, .7))
    ts.add_builder(b)
    ts.__setattr__('name', 'sweep_on_demographics_param')
    return ts


def change_demog_overlay(simulation, demog_overlay):
    """
    This function shows how to assign a different demographics overlay for each simulation.
    We are assuming that all the overlays are present in the experiment assets and we want to only select one and
    discard the others based on the parameter passed to this function.
    """
    # delete all overlays that we do not want to use
    to_delete = [d for d in simulation.task.demographics if d.filename != f"demographics_{demog_overlay}.json"]
    for demog in to_delete:
        simulation.task.demographics.remove(asset=demog)
    return {"demog_overlay": demog_overlay}


def sweep_on_demographics_files() -> 'TemplatedSimulations':
    task = EMODTask.from_files(config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               demographics_paths=os.path.join(INPUT_PATH, "demographics.json"),
                               eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # For the need of this example, we are reusing the default demographics to create 5 identical versions
    # with different names
    demog = task.demographics.pop()

    for i in range(1, 6):
        task.demographics.add_demographics_from_dict(content=demog.content, filename=f"demographics_{i}.json")

    ts = TemplatedSimulations(base_task=task)
    b = SimulationBuilder()
    b.add_sweep_definition(change_demog_overlay, range(1, 6))
    ts.add_builder(b)
    ts.__setattr__('name', 'sweep_on_demographics_files')
    return ts


if __name__ == "__main__":
    platform = Platform('COMPS2')

    # Gather all the functions available for experiment creation
    #available_funcs = (sweep_on_demographics_files, sweep_on_demographics_param)
    available_funcs = [sweep_on_demographics_files]
    # For each of them create a sweep on the seed and run
    for experiment_func in available_funcs:
        ts = experiment_func()
        experiment = Experiment.from_template(ts, name=os.path.split(sys.argv[0])[1] + "-" + ts.name)
        platform.run_items(experiment)
        platform.wait_till_done(experiment)
