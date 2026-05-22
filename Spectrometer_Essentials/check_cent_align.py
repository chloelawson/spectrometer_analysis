#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 19 14:04:22 2026

@author: chloelawson
"""

#computation libraries
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

#import data types to handle spectrum data
from phase_control_essentials.spectrum import Spectrum 

#for connecting to spectrometer
from concurrent.futures import ThreadPoolExecutor

from base_core.framework.concurrency import task_runner
from base_core.framework.events import EventBus
from base_core.framework.json.json_endpoint import JsonlSubprocessEndpoint
from phase_control_essentials.buffer import FrameBuffer
from phase_control_essentials.service import SpectrometerService
from spm_002.config import PYTHON32_PATH
from spm_002.spectrometer_server import SpectrometerServer




############################################################################################
#defining fittig functions

class fitting:
    
    def gaussian(x, a, x0, sigma, c):
        return a * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2)) + c
    
    def skew_gaussian(x, a, loc, scale, b, c):
        y= b*skewnorm.pdf(x,a,loc=loc,scale=scale) + c
        return y

############################################################################################
# helper functios

class helpers:
    
    def __init__(self):
        self.fit= fitting()
        
    def find_troughs(x, y, smooth_window, prominence):
        
        """
        finds the troughs in oscillating data by inverting the signam and then finding oeaks with scipy.
        
        PARAMETERS
        ----------
        x,y: array type 
            data points
            
        smooth_window: number
            Required minimal horizontal distance (>= 1) in samples between neighbouring peaks. 
            Smaller peaks are removed first until the condition is fulfilled for all remaining peaks.
        
        prominence: number or ndarray or sequence, optional
            Required prominence of peaks. Either a number, None, an array matching x or a 2-element
            sequence of the former. The first element is always interpreted as the minimal and the 
            second, if supplied, as the maximal required prominence.
            
        """
        
        #invert signal to find minima as peaks
        y_inv = -y
    
        peaks, _ = find_peaks(y_inv, prominence=prominence, distance=smooth_window)
    
        x_min = x[peaks]
        y_min = y[peaks]
        
        return x_min,y_min
    
    
    def fit_to_gaussian(self, x, y, smooth_window=20, prominence=0.5,skew=False,trough=True):
        """
        Estimate bottom envelope of centillatting signal using skewed gaussian fit
        on local minima
        
        PARAMETERS
        ---------
        x: array 
            Wavelength values.
        y: array 
            Intensity values.
        
        smooth_window: number
            Required minimal horizontal distance (>= 1) in samples between neighbouring peaks. 
            Smaller peaks are removed first until the condition is fulfilled for all remaining peaks.
        
        prominence: number or ndarray or sequence, optional
            Required prominence of peaks. Either a number, None, an array matching x or a 2-element
            sequence of the former. The first element is always interpreted as the minimal and the 
            second, if supplied, as the maximal required prominence.
            
        skew: Boolean, 
            If true uses skewed gaussian if false uses normal gaussian 
            trough: if true uses troughs to fit 
        
        RETURNS
        -------
        envelope:
        params:
        x_min:
        y_min: 
        """
    
        if trough==True:
            x_min,y_min = self.find_troughs(x, y, smooth_window, prominence)
        
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
            
            params, _ = curve_fit(self.fit.gaussian, x_min, y_min, p0=p0, maxfev=10000)
    
            envelope = self.fit.gaussian(x_min, *params)
            
        elif skew==True:
    
            #initial guess (skew gaussian)
            a0= 0
            loc0=x_min[np.argmin(y_min)]
            scale0= np.std(x_min) if len(x_min) > 1 else (x[-1] - x[0]) / 4
            b0= 1000
            c0= np.min(y_min)
            
            
            p0=[a0,loc0,scale0,b0,c0]
            
        
            #fit
            params, _ = curve_fit(self.fit.skew_gaussian, x_min, y_min, p0=p0, maxfev=10000)
        
            envelope = self.fit.skew_gaussian(x_min, *params)
    
        return envelope, params, x_min, y_min
    
    def match_dataset_by_x(x1, y1, x2, y2):
        """
        Reduce dataset 2 so its points align as closely as possible
        to the x-values in dataset 1.
    
        Parameters
        ----------
        x1, y1 : list or array of floats
            Smaller reference dataset
        x2, y2 : list or array of floats
            Larger dataset to resample/match
    
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

############################################################################################
# analyze spectrum 
class analyze:
    
    def __init__(self):
        self.help=helpers()
        self.fit=fitting()

    def estimated_envelope_from_spectrum(self,spectrum_data: Spectrum, plot=False):
        """
        estimates gaussian envelope from spectrum data 
            
        """
        
        x = Spectrum.wavelengths
        y= Spectrum.intensity
        
        env, params, xm, ym = self.help.fit_to_gaussian(x,y)
    
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
    
    
    def avg_diff_spectrum_data(self,cent_spectrum: Spectrum, arm_spectrum: Spectrum, use_fit=False, plot=False, generate=False):
        """
        computes the average difference between two curves, does average because each data set is going 
        to have a different number of troughs that are found. 
    
        """
        
        #get data for armrifuge
        if generate== True:
            x_arm,y_arm=self.help.generate_test_data()
        
        else:
            x_arm = arm_spectrum.wavelengths
            y_arm = arm_spectrum.intensity
    
        #get data from centillating signal
        x_cent= cent_spectrum.wavelengths
        y_cent= cent_spectrum.intensity
        
        #fit to gaussian/find troughs
        env_cent, params_cent, xm_cent, ym_cent = self.help.fit_to_gaussian(x_cent,y_cent)
        env_arm, params_arm, xm_arm, ym_arm = self.help.fit_to_gaussian(x_arm,y_arm,trough=False)
            
        
        if use_fit== True:
            y_cent_clean=env_cent
            y_arm_clean=env_arm
        
        elif use_fit==False:
            y_cent_clean=ym_cent
            y_arm_clean=ym_arm
            
            
        #match data points
        x_arm_matched, y_arm_matched = self.help.match_dataset_by_x(xm_cent,y_cent_clean,xm_arm,y_arm_clean)
        
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
        return self.help.avg_diff(xm_cent,y_cent_clean,y_arm_matched)
    
    
#diff= avg_diff_spectrum_data('test_data.xls','generate',use_fit=True,plot=True)
    
#print('average difference between curves =', round(diff,3))
    


        
        

    
        
    
        
        
    
        
        
    


