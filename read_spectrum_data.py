#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 19 14:04:22 2026

@author: chloelawson
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from scipy.stats import skewnorm
from bisect import bisect_left
import csv
import random
import math


def read_photon_control_spectrum(filename):
    """
    Read a Photon Control spectrum file and return wavelength and intensity arrays.

    Parameters
    ----------
    filename : str
        Path to the spectrum file.

    Returns
    -------
    wavelength : numpy.ndarray
        Wavelength values.
    intensity : numpy.ndarray
        Intensity values.
    """

    try:
        #Trye reading as an excel file, the test data was .xls but it was actually csv format
        data_raw = pd.read_excel(
            filename,
            usecols=[0, 1],
            skiprows=6,
            header=None,
            engine='xlrd')
        data=data_raw.to_numpy()

    except Exception:
        #if excel format reading fails, read as csv 
        data_raw = pd.read_csv(filename, sep="\t", skiprows=6)
        data= data_raw.to_numpy()
    
    except Exception:
        print("File cannot be read as excel or csv format")

    wavelength = data[:, 0]
    intensity = data[:, 1]

    return wavelength, intensity

def find_closest_index(value, array):
    """
    Return the index of the element in `array` closest to `value`.
    """
    array = np.asarray(array)
    return np.abs(array - value).argmin()


def elim_offset_photon_control_spectrum(x, y):
    """
    Remove offset from Photon Control spectrum data

    Parameters
    ----------
    x: array Wavelength values.
    y: array Intensity values.

    Returns
    -------
    wavelength: numpy.ndarray, cropped wavelength range.
    intensity: numpy.ndarray, offset-corrected intensity values
    """

    lambda_min = 740   # min of spectrometer (nm)
    lambda_1 = 745     # intermediate value used to compute average offset
    lambda_max = 860   # max of spectrometer

    idx_min = find_closest_index(lambda_min, x)
    idx_1 = find_closest_index(lambda_1, x)
    idx_max = find_closest_index(lambda_max, x)

    # MATLAB uses inclusive indexing, so add +1 to the upper bound
    offset_intensity = np.mean(y[idx_min:idx_1 + 1])

    wavelength = x[idx_min:idx_max + 1]
    intensity = y[idx_min:idx_max + 1] - offset_intensity

    return wavelength, intensity

def plot_clean_data(filename,plot=False):
    """
    plots data from excel or csv file after removing offset from spectrometer
    
    Parameters
    ----------
    filename: Name of file if in same folder as code, otherwise full file path 
    plot: True will produce a plot of the cleaned data, False will not make plot
    
    Returns
    -------
    wavelength: numpy.ndarray, cropped wavelength range.
    intensity: numpy.ndarray, offset-corrected intensity values
    
    """
    
    wavelength_offset, intensity_offset = read_photon_control_spectrum(filename)
    wavelength,intensity = elim_offset_photon_control_spectrum(wavelength_offset, intensity_offset)
    
    if plot==True:
        plt.figure(figsize=(10,5))
        plt.plot(wavelength,intensity)
        plt.x_label('Wavelength(nm)')
        plt.y_label("intensity arb.")
        plt.show()
    elif plot!=True:
        pass
    
    return wavelength,intensity


def gaussian(x, a, x0, sigma, c):
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2)) + c

def skew_gaussian(x, a, loc, scale, b, c):
    y= b*skewnorm.pdf(x,a,loc=loc,scale=scale) + c
    return y

def find_troughs(x, y, smooth_window, prominence):
    
    #invert signal to find minima as peaks
    y_inv = -y

    peaks, _ = find_peaks(y_inv, prominence=prominence, distance=smooth_window)

    x_min = x[peaks]
    y_min = y[peaks]
    
    return x_min,y_min


def fit_to_gaussian(x, y, smooth_window=20, prominence=0.5,skew=False,trough=True):
    """
    Estimate bottom envelope of centillatting signal using skewed gaussian fit
    on local minima
    
    Prameters
    ---------
    x: array Wavelength values.
    y: array Intensity values.
    
    smooth_window:
    prominence:
        
    skew: Boolean, If true uses skewed gaussian if false uses normal gaussian 
    trough: if true uses troughs to fit 
    
    Returns
    -------
    
    """

    if trough==True:
        x_min,y_min = find_troughs(x, y, smooth_window, prominence)
    
    if trough==False:
        y_min=y
        x_min=x
    
    if skew==False:

    #initial guess (gaussian)
        a0 = np.min(y_min) - np.max(y_min)
        x0 = x_min[np.argmin(y_min)]
        sigma0 = np.std(x_min) if len(x_min) > 1 else (x[-1] - x[0]) / 4
        c0 = np.min(y_min)
        
        p0=[a0,x0,sigma0,c0]
        
        params, _ = curve_fit(gaussian, x_min, y_min, p0=p0, maxfev=10000)

        envelope = gaussian(x_min, *params)
        
    elif skew==True:

        #initial guess (skew gaussian)
        a0= 0
        loc0=x_min[np.argmin(y_min)]
        scale0= np.std(x_min) if len(x_min) > 1 else (x[-1] - x[0]) / 4
        b0= 1000
        c0= np.min(y_min)
        
        
        p0=[a0,loc0,scale0,b0,c0]
        
    
        #fit
        params, _ = curve_fit(skew_gaussian, x_min, y_min, p0=p0, maxfev=10000)
    
        envelope = skew_gaussian(x_min, *params)

    return envelope, params, x_min, y_min

def estimated_envelope_from_file(filename,plot=False):
    """
    Takes filename and estimates the bottom envelope, plots the data and returns fit data
    
    Parameters
    ----------
    filename: Name of file if in same folder as code, otherwise full file path 
    plot: Boolean, True will produce a plot of the cleaned data, False will not make plot
    
    Returns
    -------
    env: 
    params:
        
    """
    
    x,y = plot_clean_data(filename,plot=False)
    env, params, xm, ym = fit_to_gaussian(x,y)

    if plot==True:
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, label="Signal", alpha=0.5)
        plt.plot(x, env, color='fuchsia',label="Estimated bottom envelope", linewidth=2)
        plt.scatter(xm, ym, color="darkslateblue", s=10, label="Detected minima")
        plt.xlabel('Wavelength(nm)')
        plt.ylabel("intensity arb.")
        plt.legend()
        plt.title("Bottom Envelope Estimation")
        plt.show()
    
    elif plot!=True:
        pass
    
    
    return env, params


#estimated_envelope_from_file('test_data.xls',plot=True)

def match_dataset_by_x(x1, y1, x2, y2):
    """
    Reduce dataset 2 so its points align as closely as possible
    to the x-values in dataset 1.

    Parameters
    ----------
    x1, y1 : list or array of floats
        Smaller reference dataset.
    x2, y2 : list or array of floats
        Larger dataset to resample/match.

    Returns
    -------
    new_x2, new_y2 : lists
        Dataset 2 reduced to the same number of points as dataset 1,
        with x-values chosen to be as close as possible to x1.
    """

    if len(x1) != len(y1):
        raise ValueError("x1 and y1 must have the same length")

    if len(x2) != len(y2):
        raise ValueError("x2 and y2 must have the same length")

    if len(x2) == 0:
        return [], []

    #Ensure dataset 2 is sorted by x
    sorted_pairs = sorted(zip(x2, y2), key=lambda p: p[0])
    x2_sorted, y2_sorted = zip(*sorted_pairs)

    new_x2 = []
    new_y2 = []

    used_indices = set()

    for target_x in x1:
        # Find insertion position
        idx = bisect_left(x2_sorted, target_x)

        candidates = []

        if idx > 0:
            candidates.append(idx - 1)

        if idx < len(x2_sorted):
            candidates.append(idx)

        # Pick closest unused point
        best_idx = None
        best_dist = float("inf")

        for c in candidates:
            if c in used_indices:
                continue

            dist = abs(x2_sorted[c] - target_x)

            if dist < best_dist:
                best_dist = dist
                best_idx = c

        # Fallback: search globally if nearby points already used
        if best_idx is None:
            for c in range(len(x2_sorted)):
                if c in used_indices:
                    continue

                dist = abs(x2_sorted[c] - target_x)

                if dist < best_dist:
                    best_dist = dist
                    best_idx = c

        used_indices.add(best_idx)

        new_x2.append(x2_sorted[best_idx])
        new_y2.append(y2_sorted[best_idx])

    return new_x2, new_y2

def avg_diff(x,y1,y2):
    """
    computes average difference between data sets, assumes that they might be different lengths
    x1,y1 is shorter/ less inclusive data set 
    """
    
    integral = 0
    
    for i in range(len(x)):
        integral+= np.abs(y2[i]-y1[i])
        
    avg= integral/(len(x))
    
    return avg

def generate_test_data():

    #data parameters
    wavelength_start = 740
    wavelength_end = 860
    num_points = 1000
    baseline_intensity = 0
    baseline_noise = 0.5
    
    #Gaussian peak parameters
    gaussian_armer = 795
    gaussian_amplitude = 19
    gaussian_sigma = 11
    gaussian_noise = 1
    
    wavelengths = np.linspace(wavelength_start, wavelength_end, num_points)
    
    intensities = []
    
    for wl in wavelengths:

        #Flat random baseline
        baseline = baseline_intensity + random.uniform(
                -baseline_noise,
                baseline_noise
            )
    
        #Gaussian peak
        gaussian = gaussian_amplitude * math.exp(-((wl - gaussian_armer) ** 2) / (2 * gaussian_sigma ** 2))
    
        #Add Gaussian noise
        gaussian += random.uniform(
                -gaussian_noise,
                gaussian_noise)
    
        intensity = baseline + gaussian
    
            
        intensities.append(round(intensity,6))
            
        lam_array=np.array(wavelengths)
        ints_array=np.array(intensities)
            
        
    return lam_array,ints_array

def avg_diff_spectrum_data_from_files(file_cent,file_arm, use_fit=False, plot=False):
    """
    computes the average difference between two curves, does average because each data set is going 
    to have a different number of troughs that are found. 

    Parameters
    ----------
    file_cent:
    
    file_arm:
        
    use_fit: Boolean, if True uses best fit skewed gaussian curves for the data sets

    Returns
    -------
    None.

    """
    
    #get data for armrifuge
    if file_arm == "generate":
        x_arm,y_arm=generate_test_data()
    
    else:
        x_arm,y_arm = plot_clean_data(file_arm,plot=False)

    #get data from centillating signal
    x_cent,y_cent = plot_clean_data(file_cent,plot=False)
    
    #fit to gaussian/find troughs
    env_cent, params_cent, xm_cent, ym_cent = fit_to_gaussian(x_cent,y_cent)
    env_arm, params_arm, xm_arm, ym_arm = fit_to_gaussian(x_arm,y_arm,trough=False,skew=False)
        
    
    if use_fit== True:
        y_cent_clean=env_cent
        y_arm_clean=env_arm
    
    elif use_fit==False:
        y_cent_clean=ym_cent
        y_arm_clean=ym_arm
        
        
    #match data points
    x_arm_matched, y_arm_matched = match_dataset_by_x(xm_cent,y_cent_clean,xm_arm,y_arm_clean)
    
    #plot
    if plot ==True:
        if use_fit== True:
            plt.figure(figsize=(10,6))
            plt.plot(xm_cent,env_cent,color='darkslateblue',label='fitted trough data from centillating dataset')
            plt.plot(xm_arm,env_arm,color='fuchsia',label='fitted data from armrifuge')
            plt.fill_between(xm_cent,env_cent,y_arm_matched,color='royalblue', alpha=0.2,interpolate=True)
            plt.xlabel('Wavelength(nm)')
            plt.ylabel('Intensity arb.')
            plt.legend()
            plt.show()
        
        elif use_fit==False:
            plt.figure(figsize=(10,6))
            plt.scatter(xm_cent,ym_cent,color='darkslateblue',label='trough data from centillating dataset')
            plt.scatter(x_arm_matched,y_arm_matched,color='fuchsia',label='data from armrifuge')
            plt.fill_between(xm_cent,y_arm_matched,ym_cent,color='royalblue', alpha=0.2)
            plt.xlabel('Wavelength(nm)')
            plt.ylabel('Intensity arb.')
            plt.legend()
            plt.show()
            
    elif plot==False:
        pass
    
    #return the average difference in the cleaned,matched data sets   
    return avg_diff(xm_cent,y_cent_clean,y_arm_matched)



diff= avg_diff_spectrum_data_from_files('test_data.xls','generate',use_fit=True,plot=True)

print('average difference between curves =', round(diff,3))



        
        

    
        
    
        
        
    
        
        
    


