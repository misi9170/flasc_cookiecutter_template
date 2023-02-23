# Copyright 2021 NREL

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.


import matplotlib.pyplot as plt
import os
import pandas as pd

from floris.utilities import wrap_360

from flasc.energy_ratio import energy_ratio_suite
from flasc.dataframe_operations import dataframe_manipulations as dfm
from flasc import floris_tools as fsatools

from {{cookiecutter.project_slug}}.models import load_floris


def load_data():
    # Load the data
    print("Loading .ftr data. This may take a minute or two...")
    root_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(root_path, "..", "raw_data_processing", "postprocessed")
    f = os.path.join(data_path, "df_scada_data_600s_filtered_and_northing_calibrated.ftr")
    if os.path.exists(f):
        df_scada = pd.read_feather(f)
    else:
        raise UserWarning("Please run the scripts in 'raw_data_processing' first.")

    return df_scada


if __name__ == "__main__":
    # Load data and floris object
    df = load_data()
    fi = load_floris()

    # Visualize layout
    fig, ax = plt.subplots()
    ax.plot(fi.layout_x, fi.layout_y, 'ko')
    for ti in range(len(fi.layout_x)):
        ax.text(fi.layout_x[ti], fi.layout_y[ti], "T{:02d}".format(ti))
    ax.axis("equal")
    ax.grid(True)
    ax.set_xlabel("x-direction (m)")
    ax.set_ylabel("y-direction (m)")

    # We first need to define a wd against which we plot the energy ratios
    # In this example, we set the wind direction to be equal to the mean
    # wind direction between all turbines
    df = dfm.set_wd_by_all_turbines(df)

    # We also need to define a reference wind speed and a reference power
    # production against to normalize the energy ratios with. In this
    # example, we set the wind speed equal to the mean wind speed
    # of all upstream turbines. The upstream turbines are automatically
    # derived from the turbine layout and the wind direction signal in
    # the dataframe, df['wd']. The reference power production is set
    # as the average power production of all upstream turbines.
    df_upstream = fsatools.get_upstream_turbs_floris(fi, wd_step=5.0)
    df = dfm.set_ws_by_upstream_turbines(df, df_upstream)
    df = dfm.set_pow_ref_by_upstream_turbines(df, df_upstream)

    # Now we generate a copy of the original dataframe and shift the
    # reference wind direction measurement upward by 7.5 degrees.
    df2 = df.copy()
    df2['wd'] = wrap_360(df2['wd'] + 7.5)

    # Initialize the energy ratio suite object and add each dataframe
    # separately. We will import the original data and the manipulated
    # dataset.
    fsc = energy_ratio_suite.energy_ratio_suite()
    fsc.add_df(df, 'Original data')
    fsc.add_df(df2, 'Data with wd bias of 7.5 degrees')

    # We now assign turbine names in the class. This can be useful when
    # working with SCADA data in which the turbine names are not simple
    # integer numbers from 0 to num_turbs - 1.
    fsc.set_turbine_names(['WTG_%03d' % ti for ti in range(len(fi.layout_x))])

    # Print the dataframes to see if everything is imported properly
    fsc.print_dfs()

    # Now we mask the datasets to a specific wind direction subset, e.g.,
    # to 20 deg to 90 deg.
    fsc.set_masks(wd_range=[20., 90.])

    # Calculate the energy ratios for test_turbines = [1] for the masked
    # datasets with uncertainty quantification using 50 bootstrap samples
    fsc.get_energy_ratios(
        test_turbines=[1],
        wd_step=2.0,
        ws_step=1.0,
        N=50,
        percentiles=[5., 95.],
        verbose=False
    )
    fsc.plot_energy_ratios(superimpose=True)

    # Look at another test turbine with the same masked datasets
    fsc.get_energy_ratios(
        test_turbines=[3],
        wd_step=2.0,
        ws_step=1.0,
        N=50,
        percentiles=[5., 95.],
        verbose=False)
    fsc.plot_energy_ratios(superimpose=True)
    plt.show()
