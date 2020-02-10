# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

from ..ecg import ecg_process
from ..rsp import rsp_process
from ..eda import eda_process
from ..emg import emg_process
from ..misc import sanitize_input


def bio_process(ecg=None, rsp=None, eda=None, emg=None, keep=None, sampling_rate=1000):
    """Automated processing of bio signals.

    Wrapper for other bio processing functions of
    electrocardiography signals (ECG), respiration signals (RSP),
    electrodermal activity (EDA) and electromyography signals (EMG).

    Parameters
    ----------
    data : DataFrame
        The DataFrame containing all the respective signals
        (e.g., ecg, rsp, Photosensor etc.). If provided,
        there is no need to fill in the other arguments
        denoting the channel inputs. Defaults to None.
    ecg : list, array or Series
        The raw ECG channel.
    rsp : list, array or Series
        The raw RSP channel (as measured, for instance, by a
        respiration belt).
    eda : list, array or Series
        The raw EDA channel.
    emg : list, array or Series
        The raw EMG channel.
    keep : DataFrame
        Dataframe or channels to add by concatenation
        to the processed dataframe (for instance, the Photosensor channel).
    sampling_rate : int
        The sampling frequency of the signals (in Hz, i.e., samples/second).
        Defaults to 1000.

    Returns
    ----------
    bio_df : DataFrame
        DataFrames of the following processed bio features:
        - *"ECG"*: the raw signal, the cleaned signal,
        the heart rate, and the R peaks indexes.
        Also generated by `ecg_process`.
        - *"RSP"*: the raw signal, the cleaned signal,
        the rate, and the amplitude. Also generated by `rsp_process`.
        - *"EDA"*: the raw signal, the cleaned signal,
        the tonic component, the phasic component,
        indexes of the SCR onsets, peaks, amplitudes,
        and half-recovery times. Also generated by `eda_process`.
        - *"EMG"*: the raw signal, the cleaned signal,
        and amplitudes. Also generated by `emg_process`.
    bio_info : dict
        A dictionary containing the samples of peaks,
        troughs, amplitudes, onsets, offsets, periods of activation,
        recovery times of the respective processed signals.


    See Also
    ----------
    ecg_process, rsp_process, eda_process, emg_process

    Example
    ----------
    >>> import neurokit2 as nk
    >>>
    >>> ecg = nk.ecg_simulate(duration=30, sampling_rate=250)
    >>> rsp = nk.rsp_simulate(duration=30, sampling_rate=250)
    >>> eda = nk.eda_simulate(duration=30, sampling_rate=250, n_scr=3)
    >>> emg = nk.emg_simulate(duration=30, sampling_rate=250, n_bursts=3)
    >>>
    >>> bio_df, bio_info = nk.bio_process(ecg=ecg,
                                          rsp=rsp,
                                          eda=eda,
                                          emg=emg,
                                          sampling_rate=250)
    >>>
    >>> # Visualize all signals
    >>> nk.standardize(bio_df).plot(subplots=True)
    """
    bio_info = {}
    bio_df = pd.DataFrame({})

    # Error check if first argument is a Dataframe.
    if ecg is not None:
        if isinstance(ecg, pd.DataFrame):
            data = ecg.copy()
            if "RSP" in data.keys():
                rsp = data["RSP"]
            else:
                rsp = None
            if "EDA" in data.keys():
                eda = data["EDA"]
            else:
                eda = None
            if "EMG" in data.keys():
                emg = data["EMG"]
            else:
                emg = None
            if "ECG" in data.keys():
                ecg = data["ECG"]
            elif "EKG" in data.keys():
                ecg = data["EKG"]
            else:
                ecg = None
            cols = ["ECG", "EKG", "RSP", "EDA", "EMG"]
            keep_keys = [key for key in data.keys() if key not in cols]
            if len(keep_keys) != 0:
                keep = data[keep_keys]
            else:
                keep = None
        elif isinstance(ecg, np.ndarray):
            ecg = ecg

    # Set warning message for sanitize input
    message = "NeuroKit error: bio_process(): we expect the user to provide a vector, i.e., a one-dimensional array (such as a list of values)."

    # ECG
    if ecg is not None:
        ecg = sanitize_input(ecg, message=message)
        ecg_signals, ecg_info = ecg_process(ecg, sampling_rate=sampling_rate)
        bio_info.update(ecg_info)
        bio_df = pd.concat([bio_df, ecg_signals], axis=1)

    # RSP
    if rsp is not None:
        rsp = sanitize_input(rsp, message=message)
        rsp_signals, rsp_info = rsp_process(rsp, sampling_rate=sampling_rate)
        bio_info.update(rsp_info)
        bio_df = pd.concat([bio_df, rsp_signals], axis=1)

    # EDA
    if eda is not None:
        eda = sanitize_input(eda, message=message)
        eda_signals, eda_info = eda_process(eda, sampling_rate=sampling_rate)
        bio_info.update(eda_info)
        bio_df = pd.concat([bio_df, eda_signals], axis=1)

    # EMG
    if emg is not None:
        emg = sanitize_input(emg, message=message)
        emg_signals, emg_info = emg_process(emg, sampling_rate=sampling_rate)
        bio_info.update(emg_info)
        bio_df = pd.concat([bio_df, emg_signals], axis=1)

    # Additional channels to keep
    if keep is not None:
        keep = keep.reset_index(drop=True)
        bio_df = pd.concat([bio_df, keep], axis=1)

    return bio_df, bio_info
