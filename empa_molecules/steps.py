import ipywidgets as ipw
import traitlets
import aiidalab_widgets_base as awb

from aiida import engine, orm, plugins

from .widgets import NodeViewWidget

StructureData = plugins.DataFactory("structure")
GaussianSpinWorkChain = plugins.WorkflowFactory('nanotech_empa.gaussian.spin')


class StructureSelectionStep(ipw.VBox, awb.WizardAppWidgetStep):
    """Integrated widget for the selection of structures from different sources."""

    confirmed_structure = traitlets.Instance(StructureData, allow_none=True)

    def __init__(self, description=None, **kwargs):
        self.manager = awb.StructureManagerWidget(
            importers=[
                awb.StructureUploadWidget(title="From computer"),
                awb.OptimadeQueryWidget(embedded=True),
                awb.StructureBrowserWidget(title="AiiDA database"),
                awb.SmilesWidget(title="SMILES")
            ],
            editors = [
                awb.BasicStructureEditor(title="Edit structure"),
                ],
            node_class='StructureData',
        )
        self.manager.observe(self._update_state, ["structure_node"])

        if description is None:
            description = ipw.HTML(
                """
                <p>Select a structure from one of the following sources and then click
                "Confirm" to go to the next step.
                """
            )
        self.description = description


        self.confirm_button = ipw.Button(
            description="Confirm",
            tooltip="Confirm the currently selected structure and go to the next step.",
            button_style="success",
            icon="check-circle",
            disabled=True,
            layout=ipw.Layout(width="auto"),
        )
        self.confirm_button.on_click(self.confirm)

        super().__init__(
            children=[
                self.description,
                self.manager,
                self.confirm_button,
            ],
            **kwargs
        )

    @traitlets.default("state")
    def _default_state(self):
        return self.State.READY

    def _update_state(self, _=None):
        if self.manager.structure_node is None:
            if self.confirmed_structure is None:
                self.state = self.State.READY
            else:
                self.state = self.State.SUCCESS
        else:
            if self.confirmed_structure is None:
                self.state = self.State.CONFIGURED
            else:
                self.state = self.State.SUCCESS

    @traitlets.observe("confirmed_structure")
    def _observe_confirmed_structure(self, _):
        with self.hold_trait_notifications():
            self._update_state()

    @traitlets.observe("state")
    def _observe_state(self, change):
        with self.hold_trait_notifications():
            state = change["new"]
            self.confirm_button.disabled = state != self.State.CONFIGURED
            self.manager.disabled = state is self.State.SUCCESS

    def confirm(self, _=None):
        self.manager.store_structure()
        self.confirmed_structure = self.manager.structure_node

    def can_reset(self):
        return self.confirmed_structure is not None

    def reset(self):  # unconfirm
        self.confirmed_structure = None
        self.manager.structure = None
        
class ConfigureGaussianCalculationStep(ipw.VBox, awb.WizardAppWidgetStep):
    """Widget to prepare gaussian inputs."""


    inputs = traitlets.Dict()
    input_structure = traitlets.Instance(StructureData, allow_none=True)

    def __init__(self, **kwargs):

        self.dft_functional = ipw.Dropdown(
            description="DFT functional:",
            value='B3LYP',
            options=[
                ('B3LYP', 'B3LYP'),
                ('PBE', 'PBEPBE'),
                ('PBE0', 'PBE1PBE'),
                ('HSE06', 'HSEH1PBE'),
                ('BLYP', 'BLYP'),
                ('wB97XD', 'wB97XD'),
            ],
            style={'description_width':'initial'}
        )
        self.empirical_dispersion = ipw.Dropdown(
            description="Empirical dispersion:",
            value='GD3',
            options=[('GD2', 'GD2'), ('GD3', 'GD3'), ('GD3BJ', 'GD3BJ') , ('None', '')],
            style={'description_width':'initial'}
        )
        basis_sets = ['STO-3G', "3-21G", "6-21G", "6-31G", "6-311G", '6-311G**',
                      "6-311+G", '6-311+G**', 'Def2SVP', 'Def2TZVP', 'Def2QZVP', 'Def2TZVPP']
        self.basis_set_opt = ipw.Dropdown(
            description="Basis set for optimization:",
            options=basis_sets,
            style={'description_width':'initial'}
        )
        self.basis_set_scf = ipw.Dropdown(
            description="Basis set for SCF:",
            options=basis_sets,
            style={'description_width':'initial'}
        )
        self.multiplicity_list = ipw.Text(description="Multiplicity list:", value="1", style={'description_width':'initial'})

        self.observe(self._update_state, ["inputs", "input_structure"])
        
        self.confirm_button = ipw.Button(
            description="Confirm",
            tooltip="Confirm the currently selected structure and go to the next step.",
            button_style="success",
            icon="check-circle",
            disabled=False,
            layout=ipw.Layout(width="auto"),
        )
        self.confirm_button.on_click(self.confirm)

        super().__init__([self.dft_functional, self.empirical_dispersion, self.basis_set_opt, self.basis_set_scf, self.multiplicity_list, self.confirm_button], **kwargs)
        
    def reset(self):
        self.inputs = {}

    def _update_state(self, _=None):
        "Update the step's state based on the order status and configuration traits."
        if self.input_structure:  # the order can be submitted
            self.state = self.State.READY
        else:
            self.state = self.State.INIT

    def confirm(self, _=None):
        self.inputs = dict(
            functional = orm.Str(self.dft_functional.value),
            empirical_dispersion = orm.Str(self.empirical_dispersion.value),
            basis_set_opt = orm.Str(self.basis_set_opt.value),
            basis_set_scf = orm.Str(self.basis_set_scf.value),
            multiplicity_list = orm.List(list=list(map(int, self.multiplicity_list.value.split()))),
            structure = self.input_structure
        )
        self.state = self.State.SUCCESS
    
    @traitlets.default("state")
    def _default_state(self):
        return self.State.INIT


class SubmitGaussianCalculationStep(ipw.VBox, awb.WizardAppWidgetStep):
    """Integrated widget for the selection of structures from different sources."""


    # We use traitlets to connect the different steps.
    # Note that we can use dlinked transformations, they do not need to be of the same type.
    inputs = traitlets.Dict()
    process = traitlets.Instance(orm.ProcessNode, allow_none=True)

    def __init__(self, **kwargs):
        self.configuration_label = ipw.HTML("Specify computational resources.")
        
        # Codes.
        self.gaussian_code_dropdown = awb.ComputationalResourcesWidget(description="Gaussian", input_plugin='gaussian')
        self.gaussian_code_dropdown.observe(self._update_state, ["value"])
        self.cubegen_code_dropdown = awb.ComputationalResourcesWidget(description="Cubegen", input_plugin='gaussian.cubegen')
        self.cubegen_code_dropdown.observe(self._update_state, ["value"])
        self.formchk_code_dropdown = awb.ComputationalResourcesWidget(description="Formchk", input_plugin='gaussian.formchk')
        self.formchk_code_dropdown.observe(self._update_state, ["value"])

        
        # Resournces.
        self.n_mpi_tasks_widget = ipw.IntText(description="# MPI tasks", value=1, min=1, style={"description_width": "100px"})
        self.memory_widget = ipw.IntText(description="Memory (Mb)", value=300, step=100, min=0, style={"description_width": "100px"})
        self.run_time_widget = ipw.IntText(description="Runtime (mins)", value=120, min=0, style={"description_width": "100px"})

        # We update the step's state whenever there is a change to the configuration or the order status.
        self.observe(self._update_state, ["inputs"])
        
        self.btn_submit_mol_opt = awb.SubmitButtonWidget(GaussianSpinWorkChain, input_dictionary_function=self.prepare_spin_calc)
        self.btn_submit_mol_opt.btn_submit.disabled = True
        traitlets.dlink((self.btn_submit_mol_opt, 'process'), (self, 'process'))

        super().__init__([ipw.HBox([ipw.VBox([self.gaussian_code_dropdown,
                          self.cubegen_code_dropdown,
                          self.formchk_code_dropdown]), ipw.VBox([self.n_mpi_tasks_widget, self.memory_widget, self.run_time_widget])]), self.btn_submit_mol_opt], **kwargs)
        
    def reset(self):
        self.inputs ={}
        self.state = self.State.INIT

    def _update_state(self, _=None):
        "Update the step's state based on the order status and configuration traits."
        if self.inputs:

            # All codes are provided.
            if self.gaussian_code_dropdown.value and self.cubegen_code_dropdown.value and self.formchk_code_dropdown.value:
                self.state = self.State.CONFIGURED
                self.btn_submit_mol_opt.btn_submit.disabled = False
            else:
                self.state = self.State.READY
                self.btn_submit_mol_opt.btn_submit.disabled = True

        else:
            self.state = self.State.INIT
            self.btn_submit_mol_opt.btn_submit.disabled = True
    
    def prepare_spin_calc(self):
        builder = GaussianSpinWorkChain.get_builder()
        

        # Input nodes.
        for key, value in self.inputs.items():
            builder[key] = value

        # Codes.
        builder.gaussian_code = self.gaussian_code_dropdown.value
        builder.formchk_code = self.formchk_code_dropdown.value
        builder.cubegen_code = self.cubegen_code_dropdown.value
        
        # Resources.
        builder.options =  orm.Dict(dict={
            "resources": {
                "num_machines": 1,
                "tot_num_mpiprocs": self.n_mpi_tasks_widget.value,
                },
            "max_memory_kb": int(1.25 * self.memory_widget.value) * 1024,
            "max_wallclock_seconds": 60 * self.run_time_widget.value,
            })
        
        
        self.state = self.State.SUCCESS

        return builder

class ViewGaussianWorkChainStatusAndResultsStep(ipw.VBox, awb.WizardAppWidgetStep):

    process = traitlets.Instance(orm.ProcessNode, allow_none=True)

    def __init__(self, **kwargs):
        self.process_tree = awb.ProcessNodesTreeWidget()
        ipw.dlink((self, "process"), (self.process_tree, "process"))

        self.node_view = NodeViewWidget(layout={"width": "auto", "height": "auto"})
        ipw.dlink(
            (self.process_tree, "selected_nodes"),
            (self.node_view, "node"),
            transform=lambda nodes: nodes[0] if nodes else None,
        )
        self.process_status = ipw.VBox(children=[self.process_tree, self.node_view])

        # Setup process monitor
        self.process_monitor = awb.ProcessMonitor(
            timeout=0.2,
            callbacks=[
                self.process_tree.update,
                self._update_state,
            ],
        )
        ipw.dlink((self, "process"), (self.process_monitor, "process"))

        super().__init__([self.process_status], **kwargs)

    def can_reset(self):
        "Do not allow reset while process is running."
        return self.state is not self.State.ACTIVE

    def reset(self):
        self.process = None

    def _update_state(self):
        if self.process is None:
            self.state = self.State.INIT
        else:
            process_state = self.process.process_state
            if process_state in (
                engine.ProcessState.CREATED,
                engine.ProcessState.RUNNING,
                engine.ProcessState.WAITING,
            ):
                self.state = self.State.ACTIVE
            elif process_state in (engine.ProcessState.EXCEPTED, engine.ProcessState.KILLED):
                self.state = self.State.FAIL
            elif process_state is engine.ProcessState.FINISHED:
                self.state = self.State.SUCCESS

    @traitlets.observe("process")
    def _observe_process(self, change):
        self._update_state()