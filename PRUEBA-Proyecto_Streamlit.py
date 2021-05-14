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
* **Python libraries:** base64, pandas, streamlit, numpy, matplotlib, seaborn, BeautifulSoup, requests, json, time
* **Data source:** [CoinMarketCap](http://coinmarketcap.com).
* **Credit:** Web scraper adapted from the Medium article *[Web Scraping Crypto Prices With Python](https://towardsdatascience.com/web-scraping-crypto-prices-with-python-41072ea5b5bf)* written by [Bryan Feng](https://medium.com/@bryanf).
""")

materiales = pd.read_csv('materiales.csv')
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
Sorted_Nodos = sorted(consolidado.NODO.unique())
sequence = st.multiselect('Nodos', Sorted_Nodos,default = ['W35714'])
cantidades = consolidado[consolidado.NODO.isin(sequence)]
#Filtro por código-------------------------------
Sorted_Codigos = sorted(cantidades['CODIGO JDE'].unique())
container = st.sidebar.beta_container()
all = st.sidebar.checkbox("Select all") 
if all:
    selected_options = container.multiselect('Codigos', Sorted_Codigos, Sorted_Codigos)
else:
    selected_options =  container.multiselect('Codigos', Sorted_Codigos,Sorted_Codigos)
cantidades=cantidades[cantidades['CODIGO JDE'].isin(selected_options)]

cantidades_total=consolidado[consolidado.NODO.isin(sequence)]
cantidades_total=cantidades_total[cantidades_total['CODIGO JDE'].isin(selected_options)]
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

st.write('Cantidad de material:')
col1, col2 ,col3 = st.beta_columns((1,1,2))

col2.dataframe (df)
col1.dataframe (Total_Historico)
#-----------------------MAPA choroplet que muestra la cantidad de material necesario por municipio ---------------------
#col2.header('Map')
fig = px.choropleth(df2, geojson=geojson, color="NODO",locations="MUNICIPIO", featureidkey="properties.MPIO_CNMBR",projection="mercator",hover_data=['MUNICIPIO'],color_continuous_scale=px.colors.sequential.Greens)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
col3.plotly_chart(fig)
#-----------------------MAPA choroplet que muestra los Nodos por municipio ---------------------
st.write('Historico de la cantidad total de material solicitado por código')
Hist=cantidades_total.groupby(['PROG','CODIGO JDE'],as_index=False).CANTIDAD.sum()
Hist['CODIGO JDE']=Hist['CODIGO JDE'].astype('str')
fig2 = px.bar(Hist, x='CODIGO JDE', y='CANTIDAD',color='PROG',barmode="group",title="Historico pedidos",labels={'PROG':'Año','CANTIDAD':'cantidad total'}, color_discrete_sequence=px.colors.qualitative.G10)
st.plotly_chart(fig2,use_container_width=True)
