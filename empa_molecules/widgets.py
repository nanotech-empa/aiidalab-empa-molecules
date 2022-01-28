import datetime
import threading
from dataclasses import dataclass

import aiida_nanotech_empa.utils.gaussian_wcs_postprocess as pp
import aiidalab_widgets_base as awb
import ipywidgets as ipw
import traitlets
from aiida import engine, orm
from aiida.cmdline.utils.query.calculation import CalculationQueryBuilder
from IPython.display import clear_output, display


class NodeViewWidget(ipw.VBox):

    node = traitlets.Instance(orm.Node, allow_none=True)

    def __init__(self, **kwargs):
        self._output = ipw.Output()
        super().__init__(children=[self._output], **kwargs)

    @traitlets.observe("node")
    def _observe_node(self, change):
        if change["new"] != change["old"]:
            with self._output:
                clear_output()
                if change["new"]:
                    display(awb.viewer(change["new"]))


class WorkChainSelectorWidget(ipw.HBox):

    # The PK of a 'aiida.workflows:quantumespresso.pw.bands' WorkChainNode.
    value = traitlets.Int(allow_none=True)

    # When this trait is set to a positive value, the work chains are automatically
    # refreshed every `auto_refresh_interval` seconds.
    auto_refresh_interval = traitlets.Int()  # seconds

    # Indicate whether the widget is currently updating the work chain options.
    busy = traitlets.Bool(read_only=True)

    # Note: We use this class as a singleton to reset the work chains selector
    # widget to its default stage (no work chain selected), because we cannot
    # use `None` as setting the widget's value to None will lead to "no selection".
    _NO_PROCESS = object()

    FMT_WORKCHAIN = "{wc.pk:6}{wc.ctime:>10}\t{wc.state:<16}\t{wc.formula}"

    def __init__(self, **kwargs):
        self.work_chains_prompt = ipw.HTML("<b>Select workflow or start new:</b>&nbsp;")
        self.work_chains_selector = ipw.Dropdown(
            options=[("New workflow...", self._NO_PROCESS)],
            layout=ipw.Layout(min_width="300px", flex="1 1 auto"),
        )
        ipw.dlink(
            (self.work_chains_selector, "value"),
            (self, "value"),
            transform=lambda pk: None if pk is self._NO_PROCESS else pk,
        )

        self.refresh_work_chains_button = ipw.Button(description="Refresh")
        self.refresh_work_chains_button.on_click(self.refresh_work_chains)

        self._refresh_lock = threading.Lock()
        self._refresh_thread = None
        self._stop_refresh_thread = threading.Event()
        self._update_auto_refresh_thread_state()

        super().__init__(
            children=[
                self.work_chains_prompt,
                self.work_chains_selector,
                self.refresh_work_chains_button,
            ],
            **kwargs,
        )

    @dataclass
    class WorkChainData:
        pk: int
        ctime: str
        state: str
        formula: str

    @classmethod
    def find_work_chains(cls):
        builder = CalculationQueryBuilder()
        filters = builder.get_filters(
            process_label="GaussianSpinWorkChain",
        )
        query_set = builder.get_query_set(
            filters=filters,
            order_by={"ctime": "desc"},
        )
        projected = builder.get_projected(
            query_set, projections=["pk", "ctime", "state"]
        )

        for process in projected[1:]:
            pk = process[0]
            formula = orm.load_node(pk).inputs.structure.get_formula()
            yield cls.WorkChainData(formula=formula, *process)

    @traitlets.default("busy")
    def _default_busy(self):
        return True

    @traitlets.observe("busy")
    def _observe_busy(self, change):
        for child in self.children:
            child.disabled = change["new"]

    def refresh_work_chains(self, _=None):
        with self._refresh_lock:
            try:
                self.set_trait("busy", True)  # disables the widget

                with self.hold_trait_notifications():
                    # We need to restore the original value, because it may be reset due to this issue:
                    # https://github.com/jupyter-widgets/ipywidgets/issues/2230
                    original_value = self.work_chains_selector.value

                    self.work_chains_selector.options = [
                        ("New calculation...", self._NO_PROCESS)
                    ] + [
                        (self.FMT_WORKCHAIN.format(wc=wc), wc.pk)
                        for wc in self.find_work_chains()
                    ]

                    self.work_chains_selector.value = original_value
            finally:
                self.set_trait("busy", False)  # reenable the widget

    def _auto_refresh_loop(self):
        while True:
            self.refresh_work_chains()
            if self._stop_refresh_thread.wait(timeout=self.auto_refresh_interval):
                break

    def _update_auto_refresh_thread_state(self):
        if self.auto_refresh_interval > 0 and self._refresh_thread is None:
            # start thread
            self._stop_refresh_thread.clear()
            self._refresh_thread = threading.Thread(target=self._auto_refresh_loop)
            self._refresh_thread.start()

        elif self.auto_refresh_interval <= 0 and self._refresh_thread is not None:
            # stop thread
            self._stop_refresh_thread.set()
            self._refresh_thread.join(timeout=30)
            self._refresh_thread = None

    @traitlets.default("auto_refresh_interval")
    def _default_auto_refresh_interval(self):
        return 10  # seconds

    @traitlets.observe("auto_refresh_interval")
    def _observe_auto_refresh_interval(self, change):
        if change["new"] != change["old"]:
            self._update_auto_refresh_thread_state()

    @traitlets.observe("value")
    def _observe_value(self, change):
        if change["old"] == change["new"]:
            return

        new = self._NO_PROCESS if change["new"] is None else change["new"]

        if new not in {pk for _, pk in self.work_chains_selector.options}:
            self.refresh_work_chains()

        self.work_chains_selector.value = new


@awb.register_viewer_widget("process.workflow.workchain.WorkChainNode.")
class WorkChainViewer(ipw.VBox):
    def __init__(self, node, **kwargs):
        if node.process_label != "GaussianSpinWorkChain":
            raise KeyError(str(node.node_type))

        self.node = node

        self.title = ipw.HTML(
            f"""
            <hr style="height:2px;background-color:#2097F3;">
            <h4>Gaussian Spin Work Chain (pk: {self.node.pk}) &mdash;
                {self.node.inputs.structure.get_formula()}
            </h4>
            """
        )

        self._output = ipw.Output()

        with self._output:
            clear_output()
            if node.process_state in (
                engine.ProcessState.CREATED,
                engine.ProcessState.RUNNING,
                engine.ProcessState.WAITING,
            ):
                display(
                    ipw.HTML("Simulation is still running, no results shown (yet).")
                )
            elif node.process_state in (
                engine.ProcessState.EXCEPTED,
                engine.ProcessState.KILLED,
            ):
                display(ipw.HTML("Simulation couldn't be completed, sorry."))
            elif node.process_state is engine.ProcessState.FINISHED:
                if node.exit_status == 0:
                    tab = ipw.Tab()
                    tab.set_title(0, "Summary")
                    tab.set_title(1, "Images")
                    out1 = ipw.Output()
                    with out1:
                        pp.make_report(node, nb=True)
                    out2 = ipw.Output()
                    with out2:
                        pp.plot_cube_images(node.outputs.gs_cube_images)
                    tab.children = [out1, out2]

                    display(tab)
                else:
                    display(
                        ipw.HTML(
                            "Simulation is completed, but has a non-zero exit status."
                        )
                    )

        super().__init__(
            children=[self.title, self._output],
            **kwargs,
        )


class SearchCompletedWidget(ipw.VBox):

    pks = traitlets.List(allow_none=True)

    def __init__(self, workchain_class, fields=None):

        # search UI
        self.workchain_class = workchain_class
        style = {"description_width": "150px"}
        layout = ipw.Layout(width="600px")
        inp_pks = ipw.Text(
            description="PKs",
            placeholder="e.g. 4062 4753 (space separated)",
            layout=layout,
            style=style,
        )
        pks_wrong_syntax = ipw.HTML(
            value="""<i class="fa fa-times" style="color:red;font-size:2em;" ></i> wrong syntax""",
            layout={"visibility": "hidden"},
        )

        def observe_inp_pks(_=None):
            try:
                pks_list = list(map(int, inp_pks.value.strip().split()))
                self.pks = pks_list or None
            except ValueError:
                pks_wrong_syntax.layout.visibility = "visible"
                return
            pks_wrong_syntax.layout.visibility = "hidden"

        inp_pks.observe(observe_inp_pks, names="value")

        self.inp_formula = ipw.Text(
            description="Formulas:",
            placeholder="e.g. C44H16 C36H4",
            layout=layout,
            style=style,
        )
        self.text_description = ipw.Text(
            description="Calculation Name: ",
            placeholder="e.g. keywords",
            layout=layout,
            style=style,
        )

        # ---------
        # date selection
        dt_now = datetime.datetime.now()
        dt_from = dt_now - datetime.timedelta(days=20)
        self.date_start = ipw.Text(
            value=dt_from.strftime("%Y-%m-%d"),
            description="From: ",
            style={"description_width": "60px"},
            layout={"width": "225px"},
        )

        self.date_end = ipw.Text(
            value=dt_now.strftime("%Y-%m-%d"),
            description="To: ",
            style={"description_width": "60px"},
            layout={"width": "225px"},
        )

        self.date_text = ipw.HTML(value="<p>Select the date range:</p>", width="150px")
        # ---------

        search_crit = [
            ipw.HBox([inp_pks, pks_wrong_syntax]),
            self.inp_formula,
            self.text_description,
            ipw.HBox([self.date_text, self.date_start, self.date_end]),
        ]

        button = ipw.Button(description="Search")

        self.results = ipw.HTML()
        self.info_out = ipw.Output()

        def on_click(b):
            with self.info_out:
                clear_output()
                self.search()

        button.on_click(on_click)

        self.show_comments_check = ipw.Checkbox(
            value=False, description="show comments", indent=False
        )

        buttons_hbox = ipw.HBox([button, self.show_comments_check])

        app = ipw.VBox(
            children=search_crit + [buttons_hbox, self.results, self.info_out]
        )

        # self.search()
        super(SearchCompletedWidget, self).__init__([app])

        # display(app)

    def search(self):

        self.results.value = "searching..."
        self.value = "searching..."

        # html table header
        html = "<style>#aiida_results td,th {padding: 2px}</style>"
        html += '<table border=1 id="aiida_results" style="margin:0px"><tr>'
        html += "<th>PK</th>"
        html += "<th>Creation Time</th>"
        html += "<th >Formula</th>"
        html += "<th>Calculation name</th>"
        html += "<th>Energy(eV)</th>"
        html += "</tr>"

        # query AiiDA database

        qb = orm.QueryBuilder()
        qb.append(self.workchain_class, filters=self.prepare_query_filters())
        qb.order_by({self.workchain_class: {"ctime": "desc"}})

        for node in qb.all(flat=True):
            thumbnail = ""
            try:
                thumbnail = node.extras["thumbnail"]
            except KeyError:
                pass
            description = node.description
            opt_structure = node.outputs.output_structure
            out_params = node.outputs.output_parameters

            # append table row
            html += "<tr>"
            html += "<td>%d</td>" % node.pk
            html += "<td>%s</td>" % node.ctime.strftime("%Y-%m-%d %H:%M")
            try:
                html += (
                    "<td>%s</td>" % node.extras["formula"]
                )  # opt_structure.get_formula()
            except KeyError:
                html += "<td>%s</td>" % opt_structure.get_formula()
            html += "<td>%s</td>" % node.description
            html += "<td>%.4f</td>" % (float(out_params["energy"]))
            # image with a link to structure export
            html += (
                '<td><a target="_blank" href="./export_structure.ipynb?uuid=%s">'
                % opt_structure.uuid
            )
            html += (
                '<img width="100px" src="data:image/png;base64,%s" title="PK%d: %s">'
                % (thumbnail, opt_structure.pk, description)
            )
            html += "</a></td>"

            if self.show_comments_check.value:
                comment_area = "<div id='wrapper' style='overflow-y:auto; height:100px; line-height:1.5;'>"
                comment_area += (
                    '<a target="_blank" href="./comments.ipynb?pk=%s">add/view</a><br>'
                    % node.pk
                )
                for comment in node.get_comments():
                    comment_area += (
                        "<hr style='padding:0px; margin:0px;' />"
                        + comment.content.replace("\n", "<br>")
                    )
                comment_area += "</div>"
                html += "<td>%s</td>" % (comment_area)

            html += "</td>"
            html += "</tr>"

        html += "</table>"
        html += "Found %d matching entries.<br>" % qb.count()

        self.results.value = html

    def prepare_query_filters(self):
        filters = {}

        filters["attributes.exit_status"] = 0

        if self.pks:
            filters["id"] = {"in": self.pks}

        formula_list = self.inp_formula.value.strip().split()
        if self.inp_formula.value:
            filters["extras.formula"] = {"in": formula_list}

        if len(self.text_description.value) > 1:
            filters["description"] = {
                "like": "%{}%".format(self.text_description.value)
            }

        try:  # If the date range is valid, use it for the search
            start_date = datetime.datetime.strptime(self.date_start.value, "%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                self.date_end.value, "%Y-%m-%d"
            ) + datetime.timedelta(hours=24)
        except ValueError:  # Otherwise revert to the standard (i.e. last 10 days)
            pass

        filters["ctime"] = {"and": [{"<=": end_date}, {">": start_date}]}

        return filters
