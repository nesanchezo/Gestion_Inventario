import pandas as pd
import numpy as np
import geopandas as gdp
import json
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st


#---------------------------------#
# Page layout
## Page expands to full width
st.set_page_config(layout="wide")
#---------------------------------#

st.write("""
# ***Planeación Materiales Expansión y Reposición ***!
""")

#---------------------------------#
# About
expander_bar = st.beta_expander("About")
expander_bar.markdown("""
SE PUEDE PONER INFORMACION DE INTERES
""")

materiales = pd.read_csv('materiales.csv')
materiales.dropna(subset=['CODIGO JDE'],inplace=True)
materiales['CODIGO JDE']=materiales['CODIGO JDE'].astype('int')
materiales['PROG']=materiales['PROG'].astype('str')

# ----------SE CARGAN LOS MATERIALES QUE SE ENCUENTRAN EN BODEGA, AÑADIR FILTROS
inventario = pd.read_csv('inventario.csv')
#Limpiar los datos

#-----------MERGE tablas-----------------------------------------
consolidado=materiales.merge(inventario, how='left', left_on='CODIGO JDE', right_on='CODIGO OW')
#Limpiar los datos
consolidado.dropna(subset=['CODIGO OW'],inplace=True)
consolidado['CODIGO OW']=consolidado['CODIGO OW'].astype(int)
consolidado.MUNICIPIO=consolidado.MUNICIPIO.str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
consolidado.loc[consolidado['MUNICIPIO']=='VILLA MARIA', 'MUNICIPIO']='VILLAMARIA'
consolidado.loc[consolidado['MUNICIPIO']=='SANTA ROSA', 'MUNICIPIO']='SANTA ROSA DE CABAL'

#----------------evaluar el inventario con respecto a las necesidades --------------
#se solicitan los nodos a revisar
sequence_input = 'N43041,N43033'
Sorted_Nodos = sorted(consolidado.NODO.unique())
sequence = st.text_input('Nodos', sequence_input)
sequence = sequence.split(',')

cantidades = consolidado[consolidado.NODO.isin(sequence)]
#cantidades2=cantidades[(cantidades.PROG==2019) | (cantidades.PROG==2020)]
cantidades_total=consolidado[consolidado.NODO.isin(sequence)]
Total_Historico=pd.pivot_table(cantidades_total,values='CANTIDAD',index=['CODIGO JDE'],columns=['PROG'],aggfunc=np.sum,fill_value=0)
cantidades=cantidades[cantidades.PROG=='2021']
cantidades_pedido=cantidades.groupby(['CODIGO JDE','NOMBRE','UNIDAD'],as_index=False)[['CANTIDAD','SALDO EN INVENTARIO']].sum()
cantidades_pedido['FALTANTE']=cantidades_pedido['CANTIDAD']-cantidades_pedido['SALDO EN INVENTARIO']
cantidades_pedido['solicitar']=[x*1.1 if x>0 else 0 for x in cantidades_pedido['FALTANTE']]
cantidades_pedido['solicitar']=[int(x) if y=='UND' else x for x,y in zip(cantidades_pedido['solicitar'],cantidades_pedido['UNIDAD'])]
cantidades_pedido['CANTIDAD']=[int(x) if y=='UND' else x for x,y in zip(cantidades_pedido['CANTIDAD'],cantidades_pedido['UNIDAD'])]
cantidades_pedido['Saldo']=[-x if x<0 else 0 for x in cantidades_pedido['FALTANTE']]
cantidades_pedido['Saldo']=[int(x) if y=='UND' else x for x,y in zip(cantidades_pedido['Saldo'],cantidades_pedido['UNIDAD'])]
cantidades_pedido['disponible inventario (%)']=cantidades_pedido.Saldo*100/cantidades_pedido['SALDO EN INVENTARIO']
cantidades_pedido['disponible inventario (%)']=cantidades_pedido['disponible inventario (%)'].fillna(0)
cantidades_pedido['disponible inventario (%)']=cantidades_pedido['disponible inventario (%)'].astype(int)
Total=cantidades_pedido[['CODIGO JDE','NOMBRE','UNIDAD', 'CANTIDAD', 'SALDO EN INVENTARIO','solicitar', 'Saldo', 'disponible inventario (%)']]
Total=Total.rename(columns={'SALDO EN INVENTARIO':'Inventario','disponible inventario (%)':'disponible (%)'})

Total=Total.round(2)
st.write('Data Dimension: ' + str(Total.shape[0]) + ' rows and ' + str(Total.shape[1]) + ' columns.')
st.dataframe (Total)

with open('mapa.geojson') as file:
		geojson=json.load(file)
df=cantidades.groupby(['MUNICIPIO'],as_index=False).NODO.nunique()
municipios=consolidado['MUNICIPIO'].unique()
data=pd.DataFrame(municipios,columns=['MUNICIPIO'])
df2=data.merge(df,how='left',on='MUNICIPIO')
df2=df2.fillna(0)

col1, col2 = st.beta_columns(2)

col1.dataframe (df)
#-----------------------MAPA choroplet que muestra la cantidad de material necesario por municipio ---------------------
col1.header('Map')
fig = px.choropleth(df2, geojson=geojson, color="NODO",locations="MUNICIPIO", featureidkey="properties.MPIO_CNMBR",projection="mercator",hover_data=['MUNICIPIO'])
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
col1.plotly_chart(fig)
#-----------------------MAPA choroplet que muestra los Nodos por municipio ---------------------
col2.dataframe (Total_Historico)
Hist=cantidades_total.groupby('PROG',as_index=False).CANTIDAD.sum()
fig2 = px.bar(Hist, x='PROG', y='CANTIDAD',title="Historico pedidos",labels={'PROG':'Año','CANTIDAD':'cantidad total'})
