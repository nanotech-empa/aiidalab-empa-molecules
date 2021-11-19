# -*- coding: utf-8 -*-

import ipywidgets as ipw

template = """
<table>
<tr>
  <td valign="top"><ul>
    <li><a href="{appbase}/spin_calculation.ipynb" target="_blank">Spin calculations</a></li>
  </ul></td>
</tr>
</table>
"""


def get_start_widget(appbase, jupbase, notebase):
    html = template.format(appbase=appbase, jupbase=jupbase, notebase=notebase)
    return ipw.HTML(html)


# EOF
