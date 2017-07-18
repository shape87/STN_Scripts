# import numpy as np
# import scipy.io
# 
# p = scipy.io.loadmat('p.mat')
# f = scipy.io.loadmat('f.mat')
# 
# print p['p'][0][:10], f['f'][0][:10]
# 
# avg = np.sqrt(np.trapz(p['p'][0] * f['f'][0]**0, x=f['f'][0]) / np.trapz(p['p'][0] * f['f'][0]**2, x=f['f'][0]))
# 
# avg2 = np.sqrt(np.trapz(p['p'][0] * f['f'][0]**0, x=f['f'][0]) / np.trapz(p['p'][0] * f['f'][0]**1, x=f['f'][0]))
# 
# 
# 
# print int(avg * 4), int(avg2*4)