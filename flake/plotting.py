"""Notebook figures with a consistent publication-style appearance."""
from contextlib import contextmanager
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patheffects as effects
from matplotlib.patches import Polygon
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D
from .profiles import temperature_profiles,open_water_season

BLUE='#087e8b'
RED='#b23b43'
SNOW='#c58a24'
STYLE={'font.family':'sans-serif','font.sans-serif':['Liberation Sans','DejaVu Sans'],
       'font.size':13,'font.weight':'bold','axes.labelsize':14,'axes.labelweight':'bold',
       'axes.titlesize':16,'axes.titleweight':'bold','axes.edgecolor':'black','axes.linewidth':1.6,
       'axes.labelcolor':'black','text.color':'black','xtick.color':'black','ytick.color':'black',
       'xtick.labelsize':12,'ytick.labelsize':12,'xtick.major.width':1.4,'ytick.major.width':1.4,
       'xtick.major.size':5,'ytick.major.size':5,'figure.facecolor':'white','axes.facecolor':'white',
       'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':300}


def _axis(ax):
    for spine in ax.spines.values():spine.set_visible(True);spine.set_color('black');spine.set_linewidth(1.6)
    ax.tick_params(direction='out',colors='black',width=1.4)
    for label in ax.get_xticklabels()+ax.get_yticklabels():label.set_fontweight('bold');label.set_color('black')
    ax.set_axisbelow(True)


def _months(ax,start,end):
    ax.set_xlim(pd.Timestamp(start),pd.Timestamp(end))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))


def _project(longitude,latitude):
    """Spherical Lambert conformal map, standard parallels 43° and 49°."""
    phi1,phi2=np.deg2rad([43.,49.])
    phi0,lon0=np.deg2rad([46.,-94.])
    n=np.log(np.cos(phi1)/np.cos(phi2))/np.log(np.tan(np.pi/4+phi2/2)/np.tan(np.pi/4+phi1/2))
    F=np.cos(phi1)*np.tan(np.pi/4+phi1/2)**n/n
    rho=6371*F/np.tan(np.pi/4+np.deg2rad(np.asarray(latitude))/2)**n
    rho0=6371*F/np.tan(np.pi/4+phi0/2)**n
    theta=n*(np.deg2rad(np.asarray(longitude))-lon0)
    return rho*np.sin(theta),rho0-rho*np.cos(theta)


def location_map(catalogue,selected,root):
    """Uncrowded location map with explicit depth and lake-area bands."""
    from .map_style import DEPTH_BOUNDS, DEPTH_CMAP, DEPTH_NORM, AREA_SIZES, AREA_LABELS, symbol_sizes
    with plt.rc_context(STYLE):
        fig=plt.figure(figsize=(7.2,6.7),facecolor='white')
        ax=fig.add_axes([.045,.055,.78,.86])
        cax=fig.add_axes([.855,.19,.025,.57])
        geo=json.loads((Path(root)/'assets/region_states.geojson').read_text())
        ax.set_facecolor('#f5f8fa')
        for f in geo['features']:
            geom=f['geometry'];polys=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
            is_mn=f['properties']['name']=='Minnesota'
            for poly in polys:
                xy=np.asarray(poly[0]);x,y=_project(xy[:,0],xy[:,1])
                ax.add_patch(Polygon(np.column_stack([x,y]),fc='#fffefa' if is_mn else '#e9eef1',
                    ec='#485f6c' if is_mn else '#a9b4ba',lw=1.05 if is_mn else .65,zorder=1))
        # Large lakes first; small lakes remain visible rather than being buried.
        ordered=catalogue.sort_values('area_km2',ascending=False)
        x,y=_project(ordered.longitude,ordered.latitude)
        pts=ax.scatter(x,y,c=ordered.mean_depth_m,cmap=DEPTH_CMAP,norm=DEPTH_NORM,
            s=symbol_sizes(ordered.area_km2),ec='#233841',lw=.22,alpha=.92,zorder=4)
        row=catalogue.loc[catalogue.lake_id==selected].iloc[0]
        x,y=_project(row.longitude,row.latitude)
        ax.scatter([x],[y],s=190,c='white',ec='none',zorder=7)
        ax.scatter([x],[y],marker='*',s=155,c='#e96744',ec='#722e24',lw=.65,zorder=8)
        ax.annotate(str(row['name']),(x,y),xytext=(24,12),textcoords='offset points',
            fontsize=12,color='#172f3e',fontweight='bold',
            bbox=dict(fc='white',ec='#b6c2c9',lw=.6,alpha=.97,boxstyle='round,pad=.3'),
            arrowprops=dict(arrowstyle='-',color='#415968',lw=.9),zorder=9)
        for lon,lat,label in [(-95.7,49.22,'CANADA'),(-90.7,45.6,'WISCONSIN'),(-94.5,43.25,'IOWA')]:
            tx,ty=_project(lon,lat);ax.text(tx,ty,label,fontsize=8.5,color='#71808a',ha='center',zorder=2)
        edge_x,edge_y=_project(np.array([-97.55,-89.35,-97.55,-89.35]),np.array([43.15,43.15,49.48,49.48]))
        ax.set_xlim(edge_x.min(),edge_x.max());ax.set_ylim(edge_y.min(),edge_y.max());ax.set_aspect('equal')
        ax.set_xticks([]);ax.set_yticks([])
        ax.set_title('Minnesota lake locations',loc='left',pad=12,fontsize=17)
        cb=fig.colorbar(pts,cax=cax,orientation='vertical',ticks=DEPTH_BOUNDS,spacing='uniform')
        cb.ax.set_yticklabels(['{:g}'.format(v) for v in DEPTH_BOUNDS]);cb.ax.tick_params(labelsize=10,width=1)
        cb.set_label('Mean depth (m)',fontsize=11,labelpad=8)
        cb.outline.set_linewidth(.9)
        handles=[Line2D([],[],marker='o',ls='',markersize=np.sqrt(size),markerfacecolor='#687e8b',
            markeredgecolor='#233841',markeredgewidth=.3,label=label) for size,label in zip(AREA_SIZES,AREA_LABELS)]
        legend=ax.legend(handles=handles,title='Lake area (km²)',loc='lower right',bbox_to_anchor=(.985,.17),
            frameon=True,facecolor='white',edgecolor='#d2dce1',framealpha=.96,fontsize=9,title_fontsize=10,
            handletextpad=.55,borderpad=.65,labelspacing=.5)
        legend.set_zorder(10)
        xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim();bx=xmax-125;by=ymin+38
        ax.plot([bx,bx+100],[by,by],c='#233841',lw=1.8,zorder=5)
        ax.text(bx+50,by+12,'100 km',ha='center',fontsize=9,color='#233841')
        ax.annotate('N',xy=(.95,.94),xytext=(.95,.85),xycoords='axes fraction',ha='center',fontsize=10,
            arrowprops=dict(arrowstyle='-|>',color='#233841',lw=1.2))
        for spine in ax.spines.values():spine.set_color('#526771');spine.set_linewidth(1)
    return fig

def forcing_plot(meteo,lake,year=2012):
    d=meteo.loc[pd.to_datetime(meteo.date).dt.year==int(year)]
    if d.empty:raise ValueError('Year is outside the meteorological record.')
    with plt.rc_context(STYLE):
        fig,axes=plt.subplots(2,2,figsize=(12,6.4),sharex=True,constrained_layout=True)
        for ax,col,title,unit,color in zip(axes.flat,
          ['air_temperature_c','wind_speed_m_s','shortwave_w_m2','longwave_w_m2'],
          ['(a) Air temperature','(b) Wind speed','(c) Incoming shortwave','(d) Incoming longwave'],
          ['Temperature (°C)','Wind speed (m s⁻¹)','Radiation (W m⁻²)','Radiation (W m⁻²)'],[RED,BLUE,SNOW,BLUE]):
            ax.plot(d.date,d[col],lw=1.5,c=color);ax.set_title(title,loc='left');ax.set_ylabel(unit)
            _months(ax,f'{year}-01-01',f'{year}-12-31');_axis(ax)
        fig.suptitle(f'{lake.name} | Meteorological inputs, {year}',fontsize=18,fontweight='bold')
    return fig


def _section(ax,simulation,d,vmax,panel=''):
    depths,temp=temperature_profiles(simulation,d)
    image=ax.contourf(mdates.date2num(pd.to_datetime(d.date)),depths,temp,levels=np.linspace(0,vmax,71),cmap=('turbo' if 'turbo' in plt.colormaps() else 'jet'),vmin=0,vmax=vmax,zorder=-1)
    ax.set_rasterization_zorder(0)
    line,=ax.plot(pd.to_datetime(d.date),d.mixed_layer_depth_m,c='black',lw=1.0,label='Mixed-layer depth')
    line.set_path_effects([effects.Stroke(linewidth=2.0,foreground='white'),effects.Normal()])
    ice=d.ice_thickness_m.to_numpy(float)>=.01
    transitions=np.diff(np.r_[False,ice,False].astype(int))
    for begin,finish in zip(np.flatnonzero(transitions==1),np.flatnonzero(transitions==-1)):
        left=pd.Timestamp(d.date.iloc[begin]);right=pd.Timestamp(d.date.iloc[finish-1])+pd.Timedelta(days=1)
        ax.axvspan(left,right,facecolor='#d5e2ed',alpha=.13,zorder=3)
        ax.plot([left,right],[1,1],transform=ax.get_xaxis_transform(),lw=5,c='#657b8a',solid_capstyle='butt',zorder=6)
        if (right-left).days>=14:
            ax.text(left+(right-left)/2,.975,'Ice cover',transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=9,
                    bbox=dict(fc='white',ec='none',alpha=.8),zorder=7)
    ax.set_ylim(simulation.lake.mean_depth_m,0)
    ax.set_ylabel('Depth (m)')
    if panel:ax.set_title(panel,loc='left',pad=10)
    handles,labels=ax.get_legend_handles_labels()
    if ice.any():
        handles.append(Line2D([0],[0],color='#657b8a',lw=4));labels.append('Ice cover (top edge)')
    ax.legend(handles,labels,loc='lower left',frameon=True,facecolor='white',edgecolor='black',fontsize=10,framealpha=.9)
    _axis(ax)
    return image


def thermal_figure(simulation,year=2012,view='open_water'):
    if view not in ['open_water','full_year']:raise ValueError('Choose open_water or full_year.')
    d=open_water_season(simulation,year) if view=='open_water' else simulation.daily.loc[pd.to_datetime(simulation.daily.date).dt.year==int(year)]
    if d.empty:raise ValueError('Year is outside the simulation.')
    vmax=max(30,5*np.ceil(d.mixed_layer_temperature_c.max()/5))
    with plt.rc_context(STYLE):
        fig,ax=plt.subplots(figsize=(12,5.4),constrained_layout=True)
        image=_section(ax,simulation,d,vmax)
        cb=fig.colorbar(image,ax=ax,pad=.025,shrink=.96)
        cb.set_ticks(np.arange(0,vmax+.1,5));cb.set_label('Temperature (°C)')
        _months(ax,d.date.iloc[0],d.date.iloc[-1]);_axis(ax)
        ax.set_xlabel(str(year))
        ax.set_title(f"{simulation.lake.name} | {'Open-water season' if view=='open_water' else 'Full year'}, {year}",loc='center',fontsize=18,pad=14)
    return fig


def _winter_data(simulation,ending_year):
    y=int(ending_year);start,end=pd.Timestamp(y-1,7,1),pd.Timestamp(y,6,30)
    d=simulation.daily
    if d.date.min()>start or d.date.max()<end:raise ValueError('Choose a complete July–June winter within the simulation.')
    window=d.loc[d.date.between(start,end)]
    cover=window.loc[(window.ice_thickness_m>=.01)|(window.snow_thickness_m>1e-5)]
    if not cover.empty:
        start=max(start,pd.Timestamp(cover.date.min())-pd.Timedelta(days=10))
        end=min(end,pd.Timestamp(cover.date.max())+pd.Timedelta(days=10))
    return window.loc[window.date.between(start,end)],start,end


def _cover(upper,lower,d,start,end,snow_limit,ice_limit,ending_year=None):
    upper.fill_between(d.date,0,d.snow_thickness_m*100,color=SNOW,alpha=.35)
    upper.plot(d.date,d.snow_thickness_m*100,c=SNOW,lw=2)
    lower.fill_between(d.date,0,d.ice_thickness_m*100,color=BLUE,alpha=.28)
    lower.plot(d.date,d.ice_thickness_m*100,c=BLUE,lw=2)
    upper.set_ylim(0,snow_limit);lower.set_ylim(ice_limit,0)
    upper.yaxis.set_major_locator(MaxNLocator(nbins=4,prune='lower'))
    lower.yaxis.set_major_locator(MaxNLocator(nbins=6))
    upper.set_ylabel('Snow thickness (cm)');lower.set_ylabel('Ice thickness (cm)')
    upper.tick_params(labelbottom=False)
    for ax in [upper,lower]:
        ax.set_xlim(start,end);_axis(ax)
        ax.xaxis.set_major_locator(mdates.MonthLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    season_year=int(ending_year) if ending_year is not None else end.year
    lower.set_xlabel('')


def winter_figure(simulation,ending_year=2014):
    d,start,end=_winter_data(simulation,ending_year)
    snow_limit=max(5,float(d.snow_thickness_m.max()*100)*1.12)
    ice_limit=max(10,float(d.ice_thickness_m.max()*100)*1.10)
    with plt.rc_context(STYLE):
        fig,axes=plt.subplots(2,1,figsize=(12,6.6),sharex=True,gridspec_kw={'height_ratios':[1,2],'hspace':0})
        _cover(*axes,d,start,end,snow_limit,ice_limit,ending_year=ending_year)
        axes[0].set_title(f'{simulation.lake.name} | Snow and ice',loc='center',fontsize=18,pad=14)
        fig.subplots_adjust(left=.12,right=.98,top=.89,bottom=.12)
    return fig


def compare_temperature(first,second,year=2012,view='open_water'):
    if view not in ['open_water','full_year']:raise ValueError('Choose open_water or full_year.')
    seasons=[open_water_season(r,year) for r in [first,second]]
    start=min(d.date.min() for d in seasons) if view=='open_water' else pd.Timestamp(int(year),1,1)
    end=max(d.date.max() for d in seasons) if view=='open_water' else pd.Timestamp(int(year),12,31)
    ds=[r.daily.loc[pd.to_datetime(r.daily.date).between(start,end)] for r in [first,second]]
    vmax=max(30,5*np.ceil(max(d.mixed_layer_temperature_c.max() for d in ds)/5))
    start=min(d.date.min() for d in ds);end=max(d.date.max() for d in ds)
    with plt.rc_context(STYLE):
        fig,axes=plt.subplots(1,2,figsize=(13,5.1),constrained_layout=True)
        for i,(ax,r,d) in enumerate(zip(axes,[first,second],ds)):
            im=_section(ax,r,d,vmax,f'({chr(97+i)}) {r.lake.name} — {r.lake.mean_depth_m:.1f} m')
            _months(ax,start,end);ax.set_xlabel(str(year))
        cb=fig.colorbar(im,ax=list(axes),shrink=.92,pad=.025);cb.set_ticks(np.arange(0,vmax+.1,5));cb.set_label('Temperature (°C)')
        fig.suptitle(f"Thermal structure | {'Open-water-season window' if view=='open_water' else 'Full year'}, {year}",fontsize=18,fontweight='bold')
    return fig


def compare_winter(first,second,ending_year=2014):
    triples=[_winter_data(r,ending_year) for r in [first,second]]
    common_start=min(t[1] for t in triples);common_end=max(t[2] for t in triples)
    triples=[(r.daily.loc[r.daily.date.between(common_start,common_end)],common_start,common_end) for r in [first,second]]
    snow=max(5,max(float(d.snow_thickness_m.max()*100) for d,_,_ in triples)*1.12)
    ice=max(10,max(float(d.ice_thickness_m.max()*100) for d,_,_ in triples)*1.10)
    with plt.rc_context(STYLE):
        fig,axes=plt.subplots(2,2,figsize=(13,6.5),sharex='col',sharey='row',gridspec_kw={'height_ratios':[1,2],'hspace':0,'wspace':.2})
        for i,(r,(d,start,end)) in enumerate(zip([first,second],triples)):
            _cover(axes[0,i],axes[1,i],d,start,end,snow,ice,ending_year=ending_year)
            axes[0,i].set_title(f'({chr(97+i)}) {r.lake.name}',loc='left',pad=12)
            if i:axes[0,i].set_ylabel('');axes[1,i].set_ylabel('')
        fig.suptitle(f'Snow and ice | Winter {int(ending_year)-1}–{int(ending_year)}',fontsize=18,fontweight='bold',y=.98)
        fig.subplots_adjust(left=.09,right=.98,top=.87,bottom=.12)
    return fig
