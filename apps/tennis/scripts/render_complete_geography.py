"""Render the frozen calibration and loss comparison; no model fitting."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('data/tennis/historical_geography_complete_20261018/comparison')
fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
for row,(name,title) in enumerate([('main','Muestra principal: 3.215 partidos'),('without_coarse_references','Sin referencias mayores de 1 km: 3.043 partidos')]):
 r=json.loads((root/(name+'_report.json')).read_text())
 ax=axs[row,0];ax.plot([0,1],[0,1],color='#a9adb5',linestyle='--',label='Calibración ideal')
 for variant,label,color in [('base','Base','#1c6cab'),('base_plus_spatial','Base + espaciales','#c16b1f')]:
  bins=[b for b in r['metrics'][variant]['calibration'] if b['n']]
  ax.plot([b['mean_probability'] for b in bins],[b['observed_rate'] for b in bins],marker='o',markersize=4,label=label,color=color)
 ax.set(xlabel='Probabilidad predicha',ylabel='Frecuencia observada',xlim=(0,1),ylim=(0,1),title=title);ax.grid(alpha=.18);ax.legend(fontsize=8)
 ax=axs[row,1];pair=r['paired'];delta=pair['log_loss_spatial_minus_base'];lo,hi=pair['log_loss_ci95']
 ax.axvline(0,color='#777',linestyle='--');ax.errorbar([delta],[0],xerr=[[delta-lo],[hi-delta]],fmt='o',capsize=6,color='#1c6cab')
 ax.set(xlabel='Δ Log-Loss: espaciales − base',yticks=[],ylim=(-1,1),title='Diferencia e intervalo del 95 % por competición')
 ax.text(.5,.18,'El intervalo incluye cero',transform=ax.transAxes,ha='center',color='#555');ax.grid(axis='x',alpha=.18);ax.ticklabel_format(axis='x',style='sci',scilimits=(-3,3))
fig.suptitle('Tenis · evaluación retrospectiva exploratoria 2025',fontsize=16,fontweight='bold')
fig.text(.5,-.015,'Entrenamiento: 2024 · Protocolo fijo · 10 intervalos de calibración · Sin validación financiera ni selección de modelo',ha='center',fontsize=9,color='#555')
for ext in ['png','svg']:fig.savefig(root/('calibration_comparison.'+ext),dpi=160,bbox_inches='tight')
print('Calibration figures saved')
