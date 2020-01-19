# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from ..signal.signal_from_indices import _signals_from_peakinfo


def rsp_findpeaks(rsp_cleaned, method="khodadad2018", outlier_threshold=0.3):
    """Identify extrema in a respiration (RSP) signal.

    Identify inhalation peaks and exhalation troughs in a preprocessed
    respiration signal using different sets of parameters, such as:

    - `Khodadad et al. (2018)
    <https://iopscience.iop.org/article/10.1088/1361-6579/aad7e6/meta>`_
    - `BioSPPy
    <https://github.com/PIA-Group/BioSPPy/blob/master/biosppy/signals/resp.py>`_

    Parameters
    ----------
    rsp_cleaned : list, array or Series
        The cleaned respiration channel as returned by `rsp_clean()`.
    method : str
        The processing pipeline to apply. Can be one of "khodadad2018"
        (default) or "biosppy".
    outlier_threshold : float
        Only applies if method is "khodadad2018". Extrema that have a vertical
        distance smaller than (outlier_threshold * average vertical distance)
        to any direct neighbour are removed as false positive outliers. I.e.,
        outlier_threshold should be a float with positive sign (the default is
        0.3). Larger values of outlier_threshold correspond to more
        conservative thresholds (i.e., more extrema removed as outliers).

    Returns
    -------
    signals : DataFrame
        A DataFrame of same length as the input signal in which occurences of
        inhalation peaks and exhalation troughs are marked as "1" in lists of
        zeros with the same length as `rsp_cleaned`. Accessible with the keys
        "RSP_Peaks" and "RSP_Troughs" respectively.
    info : dict
        A dictionary containing additional information, in this case the
        samples at which inhalation peaks and exhalation troughs occur,
        accessible with the keys "RSP_Peaks", and "RSP_Troughs", respectively.

    See Also
    --------
    rsp_clean, rsp_rate, rsp_amplitude, rsp_process, rsp_plot

    Examples
    --------
    >>> import neurokit2 as nk
    >>>
    >>> rsp = nk.rsp_simulate(duration=30, respiratory_rate=15)
    >>> cleaned = nk.rsp_clean(rsp, sampling_rate=1000)
    >>> signals, info = nk.rsp_findpeaks(cleaned)
    >>> nk.events_plot([info["RSP_Peaks"], info["RSP_Troughs"]], cleaned)
    """
    # Try retrieving correct column
    if isinstance(rsp_cleaned, pd.DataFrame):
        try:
            rsp_cleaned = rsp_cleaned["RSP_Clean"]
        except NameError:
            try:
                rsp_cleaned = rsp_cleaned["RSP_Raw"]
            except NameError:
                rsp_cleaned = rsp_cleaned["RSP"]

    cleaned = np.array(rsp_cleaned)

    # Find peaks
    method = method.lower()  # remove capitalised letters
    if method in ["khodadad", "khodadad2018"]:
        info = _rsp_findpeaks_khodadad(cleaned, outlier_threshold)
    elif method == "biosppy":
        info = _rsp_findpeaks_biosppy(cleaned)
    else:
        raise ValueError("NeuroKit error: rsp_findpeaks(): 'method' should be "
                         "one of 'khodadad2018' or 'biosppy'.")

    # Prepare output
    signals = _signals_from_peakinfo(info, peak_indices=info["RSP_Peaks"], length=len(rsp_cleaned))

    # Add respiration phase
    signals["RSP_Inspiration"] = _rsp_findpeaks_phase(signals)

    return signals, info






# =============================================================================
# Methods
# =============================================================================
def _rsp_findpeaks_biosppy(rsp_cleaned):
    return _rsp_findpeaks_khodadad(rsp_cleaned, outlier_threshold=0)



def _rsp_findpeaks_khodadad(rsp_cleaned, outlier_threshold=0.3):

    extrema = _rsp_findpeaks_extrema(rsp_cleaned)
    extrema, amplitudes = _rsp_findpeaks_outliers(rsp_cleaned, extrema,
                                                  outlier_threshold=outlier_threshold)
    peaks, troughs = _rsp_findpeaks_sanitize(extrema, amplitudes)

    info = {"RSP_Peaks": peaks,
            "RSP_Troughs": troughs}
    return info









# =============================================================================
# Internals
# =============================================================================
def _rsp_findpeaks_phase(signals):
    inspiration = np.full(len(signals), np.nan)
    inspiration[np.where(signals["RSP_Peaks"] == 1)] = 0.0
    inspiration[np.where(signals["RSP_Troughs"] == 1)] = 1.0

    last_element = np.where(~np.isnan(inspiration))[0][-1]  # Avoid filling beyond the last peak/trough
    inspiration[0:last_element] = pd.Series(inspiration).fillna(method="pad").values[0:last_element]

    return inspiration





def _rsp_findpeaks_extrema(rsp_cleaned):
    # Detect zero crossings (note that these are zero crossings in the raw
    # signal, not in its gradient).
    greater = rsp_cleaned > 0
    smaller = rsp_cleaned < 0
    risex = np.where(np.bitwise_and(smaller[:-1], greater[1:]))[0]
    fallx = np.where(np.bitwise_and(greater[:-1], smaller[1:]))[0]

    if risex[0] < fallx[0]:
        startx = "rise"
    elif fallx[0] < risex[0]:
        startx = "fall"

    allx = np.concatenate((risex, fallx))
    allx.sort(kind="mergesort")

    # Find extrema by searching minima between falling zero crossing and
    # rising zero crossing, and searching maxima between rising zero
    # crossing and falling zero crossing.
    extrema = []
    for i in range(len(allx) - 1):

        # Determine whether to search for minimum or maximum.
        if startx == "rise":
            if (i + 1) % 2 != 0:
                argextreme = np.argmax
            else:
                argextreme = np.argmin
        elif startx == "fall":
            if (i + 1) % 2 != 0:
                argextreme = np.argmin
            else:
                argextreme = np.argmax

        # Get the two zero crossings between which the extreme will be
        # searched.
        beg = allx[i]
        end = allx[i + 1]

        extreme = argextreme(rsp_cleaned[beg:end])
        extrema.append(beg + extreme)

    extrema = np.asarray(extrema)
    return extrema


def _rsp_findpeaks_outliers(rsp_cleaned, extrema, outlier_threshold=0.3):

    # Only consider those extrema that have a minimum vertical distance to
    # their direct neighbor, i.e., define outliers in absolute amplitude
    # difference between neighboring extrema.
    vertical_diff = np.abs(np.diff(rsp_cleaned[extrema]))
    average_diff = np.mean(vertical_diff)
    min_diff = np.where(vertical_diff > (average_diff * outlier_threshold))[0]
    extrema = extrema[min_diff]

    # Make sure that the alternation of peaks and troughs is unbroken. If
    # alternation of sign in extdiffs is broken, remove the extrema that
    # cause the breaks.
    amplitudes = rsp_cleaned[extrema]
    extdiffs = np.sign(np.diff(amplitudes))
    extdiffs = np.add(extdiffs[0:-1], extdiffs[1:])
    removeext = np.where(extdiffs != 0)[0] + 1
    extrema = np.delete(extrema, removeext)
    amplitudes = np.delete(amplitudes, removeext)

    return extrema, amplitudes


def _rsp_findpeaks_sanitize(extrema, amplitudes):
    # To be able to consistently calculate breathing amplitude, make sure that
    # the extrema always start with a trough and end with a peak, since
    # breathing amplitude will be defined as vertical distance between each
    # peak and the preceding trough. Note that this also ensures that the
    # number of peaks and troughs is equal.
    if amplitudes[0] > amplitudes[1]:
        extrema = np.delete(extrema, 0)
    if amplitudes[-1] < amplitudes[-2]:
        extrema = np.delete(extrema, -1)
    peaks = extrema[1::2]
    troughs = extrema[0:-1:2]

    return peaks, troughs