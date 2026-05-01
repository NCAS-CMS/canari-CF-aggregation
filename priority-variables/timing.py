import matplotlib.pyplot as plt
import numpy as np

t=np.genfromtxt('./timing.txt')

plt.plot(np.arange(len(t))+1,t/(24*60))
plt.grid()
plt.title('Number of years aggregated vs. time taken [hours]')


plt.savefig('./timing.png')
plt.show()