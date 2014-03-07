"""
Created on Tue Mar  4 16:06:39 2014

@author: nabobalis
"""

from __future__ import division, absolute_import
import numpy as np
import matplotlib.pyplot as plt
import pycwt as wavelet

from pycwt.helpers import find
from matplotlib.image import NonUniformImage

def boxpdf(x):
    """
    Forces the probability density function of the input data to have
    a boxed distribution.

    PARAMETERS
        x (array like) :
            Input data

    RETURNS
        X (array like) :
            Boxed data varying between zero and one.
        Bx, By (array like) :
            Data lookup table

    """
    x = np.asarray(x)
    n = x.size

    # Kind of 'unique'
    i = np.argsort(x)
    d = (np.diff(x[i]) != 0)
    I = find(np.concatenate([d, [True]]))
    X = x[i][I]

    I = np.concatenate([[0], I+1])
    Y = 0.5 * (I[0:-1] + I[1:]) / n
    bX = np.interp(x, X, Y)

    return bX, X, Y

data1 = dict(
    name = 'Arctic Oscillation',
    nick = 'AO',
    file = 'jao.dat',
)
data2 = dict(
    name = 'Baltic Sea ice extent',
    nick = 'BMI',
    file='jbaltic.dat',
)
mother = 'morlet'

# Loads the data to be analysed.
t1, s1 = np.loadtxt(data1['file'], unpack=True)
t2, s2 = np.loadtxt(data2['file'], unpack=True)
dt = np.diff(t1)[0]
n1 = t1.size
n2 = t2.size
n = min(n1, n2)

# Change the probablity density function (PDF) of the data. The time series
# of Baltic Sea ice extent is highly bi-modal and we therefore transform the
# timeseries into a series of percentiles. The transformed series probably
# reacts 'more linearly' to climate.
s2, _, _ = boxpdf(s2)

# Calculates the standard deviation of each time series for later
# normalization.
std1 = s1.std()
std2 = s2.std()

# Calculate the CWT of both normalized time series. The function wavelet.cwt
# returns a a list with containing [wave, scales, freqs, coi, fft, fftfreqs]
# variables.

slevel = 0.95                        # Significance level
dj = 1/12                            # Twelve sub-octaves per octaves
s0 = -1#2 * dt                      # Starting scale, here 6 months
J = -1#7 / dj                      # Seven powers of two with dj sub-octaves
#alpha1 = alpha2 = 0.0                          # Lag-1 autocorrelation for white noise
alpha1, _, _ = wavelet.ar1(s1) # Lag-1 autocorrelation for red noise
alpha2, _, _ = wavelet.ar1(s2) # Lag-1 autocorrelation for red noise

mother = wavelet.Morlet(6)           # Morlet mother wavelet with m=6

# The following routines perform the wavelet transform and siginificance
# analysis for two data sets.

W1, scales1, freqs1, coi1, fft1, fftfreqs1 = wavelet.cwt(s1/std1, dt, dj, s0,
                                                         J,mother)
signif1, fft_theor1 = wavelet.significance(1.0, dt, scales1, 0, alpha1,
                                           significance_level=slevel,
                                           wavelet=mother)
W2, scales2, freqs2, coi2, fft2, fftfreqs2 = wavelet.cwt(s2/std2, dt, dj, s0,
                                                         J,mother)
signif2, fft_theor2 = wavelet.significance(1.0, dt, scales2, 0, alpha2,
                                           significance_level=slevel,
                                           wavelet=mother)

power1 = (np.abs(W1)) ** 2             # Normalized wavelet power spectrum
power2 = (np.abs(W2)) ** 2             # Normalized wavelet power spectrum
period1 = 1/freqs1
period2 = 1/freqs2
sig95_1 = np.ones([1, n1]) * signif1[:, None]
sig95_1 = power1 / sig95_1                # Where ratio > 1, power is significant
sig95_2 = np.ones([1, n2]) * signif2[:, None]
sig95_2 = power2 / sig95_2                # Where ratio > 1, power is significant


# First plot is of both CWT
fig, (ax1, ax2) = plt.subplots(nrows=2,ncols=1, sharex=True)

extent1 = [t1.min(),t1.max(),0,max(period1)]
extent2 = [t2.min(),t2.max(),0,max(period2)]

#        if rectify:
#            cf = ax.contourf(t, (period), power / scales, levels,
#                extend=extend)
im1 = NonUniformImage(ax1, interpolation='bilinear', extent=extent1)
im1.set_data(t1, period1, power1)
ax1.images.append(im1)
ax1.contour(t1, period1, sig95_1, [-99, 1], colors='k', linewidths=2, extent=extent1)
ax1.fill(np.concatenate([t1, t1[-1:]+dt, t1[-1:]+dt,t1[:1]-dt, t1[:1]-dt]),
        (np.concatenate([coi1,[1e-9], period1[-1:], period1[-1:], [1e-9]])),
        'k', alpha=0.3,hatch='x')

im2 = NonUniformImage(ax2, interpolation='bilinear', extent=extent2)
im2.set_data(t2, period2, power2)
ax2.images.append(im2)
ax2.contour(t2, period2, sig95_2, [-99, 1], colors='k', linewidths=2, extent=extent2)
ax2.fill(np.concatenate([t2, t2[-1:]+dt, t2[-1:]+dt,t2[:1]-dt, t2[:1]-dt]),
        (np.concatenate([coi2,[1e-9], period2[-1:], period2[-1:], [1e-9]])),
        'k', alpha=0.3,hatch='x')

# Due to the difference in the time series, the second signal has to be trimmed
# for the XWT process.
s2 = s2[np.argwhere(t2==min(t1)):-2]

# Calculate the cross wavelet transform (XWT). The XWT finds regions in time
# frequency space where the time series show high common power. Torrence and
# Compo (1998) state that the percent point function -- PPF (inverse of the
# cumulative distribution function) of a chi-square distribution at 95%
# confidence and two degrees of freedom is Z2(95%)=3.999. However, calculating
# the PPF using chi2.ppf gives Z2(95%)=5.991. To ensure similar significance
# intervals as in Grinsted et al. (2004), one has to use confidence of 86.46%.
W12, cross_coi, freq, signif = wavelet.xwt(s1, s2, dt, dj=1/12, s0=-1, J=-1,
                                     significance_level=0.8646, wavelet='morlet',
                                     normalize=True)

cross_power = np.abs(W12)**2
cross_sig = np.ones([1, n]) * signif[:, None]
cross_sig = cross_power / cross_sig # power is significant where ratio > 1
cross_period = 1/freq

# Calculate the wavelet coherence (WTC). The WTC finds regions in time
# frequency space where the two time seris co-vary, but do not necessarily have
# high power.
WCT, aWCT, corr_coi, freq, sig = wavelet.wct(s1, s2, dt, dj=1/12, s0=-1, J=-1,
                                        significance_level=0.8646, wavelet='morlet',
                                        normalize=True)

cor_sig = np.ones([1, n]) * sig[:, None]
cor_sig = np.abs(WCT) / cor_sig # power is significant where ratio > 1
cor_period = 1/freq

# Calculates the phase between both time series. The phase arrows in the
# cross wavelet power spectrum rotate clockwise with 'north' origin.
# The relative phase relationship convention is the same as adopted
# by Torrence and Webster (1999), where in phase signals point
# upwards (N), anti-phase signals point downwards (S). If X leads Y,
# arrows point to the right (E) and if X lags Y, arrow points to the
# left (W).

angle = 0.5 * np.pi - aWCT
u, v = np.cos(angle), np.sin(angle)

fig, (ax1, ax2) = plt.subplots(nrows=2,ncols=1, sharex=True, sharey=True)

extent_cross = [t1.min(),t1.max(),0,max(cross_period)]
extent_corr =  [t1.min(),t1.max(),0,max(cor_period)]
im1 = NonUniformImage(ax1, interpolation='bilinear', extent=extent_cross)
im1.set_data(t1, cross_period, cross_power)
ax1.images.append(im1)
ax1.contour(t1, cross_period, cross_sig, [-99, 1], colors='k', linewidths=2, extent=extent_cross)
ax1.fill(np.concatenate([t1, t1[-1:]+dt, t1[-1:]+dt,t1[:1]-dt, t1[:1]-dt]),
        (np.concatenate([cross_coi,[1e-9], cross_period[-1:], cross_period[-1:], [1e-9]])),
        'k', alpha=0.3,hatch='x')
ax1.set_title('Cross-Wavelet')
ax1.quiver(t1[::3], cross_period[::3], u[::3, ::3],
          v[::3, ::3], units='width', angles='uv', pivot='mid',
          linewidth=1.5, edgecolor='k', headwidth=10, headlength=10,
          headaxislength=5, minshaft=2, minlength=5)

im2 = NonUniformImage(ax2, interpolation='bilinear', extent=extent_corr)
im2.set_data(t1, cor_period, WCT)
ax2.images.append(im2)
ax2.contour(t1, cor_period, cor_sig, [-99, 1], colors='k', linewidths=2, extent=extent_corr)
ax2.fill(np.concatenate([t1, t1[-1:]+dt, t1[-1:]+dt,t1[:1]-dt, t1[:1]-dt]),
        (np.concatenate([corr_coi,[1e-9], cor_period[-1:], cor_period[-1:], [1e-9]])),
        'k', alpha=0.3,hatch='x')
ax2.set_title('Cross-Correlation')
ax2.quiver(t1[::3], cor_period[::3], u[::3,::3], v[::3,::3],
           units='height', angles='uv', pivot='mid',linewidth=1.5, edgecolor='k',
           headwidth=10, headlength=10, headaxislength=5, minshaft=2, minlength=5)
ax2.set_ylim(2,35)
plt.show()