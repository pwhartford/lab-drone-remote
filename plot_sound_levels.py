import numpy as np
import matplotlib.pyplot as plt

M = np.loadtxt('sound_levels_v2.txt', delimiter=',', skiprows=1)        #charge le fichier resultat et ignore la 1ere ligne

fig = plt.figure(1)

time=list(np.arange(0,10.000,0.001))            #converti le temps en secondes


plt.grid()
plt.xlabel('Temps (s)')
plt.ylabel('Tension (V)')
plt.title('Tension mesuree')
plt.xticks(np.arange(0, max(time)+1,1))         #graduer toutes les secondes

plt.plot(time, M[:,0])
