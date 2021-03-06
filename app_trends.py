from pytrends.request import TrendReq
import pandas as pd
import time
import streamlit as st

st.set_page_config(
    page_title='Trends | Vocento',
)



def trends():
  with st.form(key='my_form'):
    st.header('Configuración email')
    frecuenciaEmail = st.number_input('Frecuencia email (minutos)',value=120)
    emails = st.text_area('emails de destino (uno por línea)')
    asunto = st.text_input('asunto del email',value='Tendencias - app dinámica')
    lista_emails = emails.split('\n')
    st.header('Configuración consultas')
    aumentoPuntual = st.number_input('Filtro Aumento Puntual', value=1500)
    lista_geolocalizacion = ["ES", "ES-AN", "ES-AR", "ES-AS", "ES-CN", "ES-CB", "ES-CM", "ES-CL", "ES-CT", "ES-EX", "ES-GA", "ES-IB", "ES-RI", "ES-MD", "ES-MC", "ES-NC", "ES-PV", "ES-V"]
    geolocalizacion = st.selectbox('Selecciona ubicación', lista_geolocalizacion,index=0)
    lista_intervaloTiempo = ["today 3-m", "today 2-m", "today 1-m", "now 7-d", "now 1-d", "now 1-H", "now 4-H"]
    intervaloTiempo = st.selectbox('Selecciona el intervalo de tiempo', lista_intervaloTiempo, index=6)
    st.header('Consultas')
    consultas = st.text_area('Introduce una consulta por línea') #Creamos el text area en el sidebar
    submit_button = st.form_submit_button(label='Iniciar')


  #si el text area está vacío paramos el código
  if consultas == '':
      st.stop()

  kw_list = consultas.split("\n") #almacenamos en una lista cada consulta ingresada por línea en el text area
  kw_lists=[] #creamos una lista para incluir dentro de ella otra lista por cada consulta.

  #bucle para crear las lista de cada consulta e incluirla en la kw_lists
  for i in range(len(kw_list)):
    kw_lists.append([])
    for j in range(1):
      kw_lists[i].append(kw_list[i])	

  txt="" #creamos una variable de texto vacia para mostrar la lista de consultas limpia (sin corchetes).

  #Hacemos un bucle para limpiar cada valor de la lista y añadir una coma y un "y" antes de la última y "." al final.
  for kw in range (len(kw_lists)):
    if kw+1 == len(kw_lists):
      txt= txt + "{}.".format(*kw_lists[kw])
    elif kw+1 == len(kw_lists)-1:
      txt= txt + "{} y ".format(*kw_lists[kw])
    else:
      txt= txt + " {}, ".format(*kw_lists[kw])

  st.header('Lista de consultas realizadas')
  st.write(txt)

  #creamos una lista vacia para añadir posteriormente todos los dataframes con los resultados de cada término consultado en google trends
  listaFinal = []

  for j in range (len(kw_list)):

    pytrends = TrendReq(hl='es-ES', tz=60, timeout=(10,25),retries=2)

    pytrends.build_payload(kw_lists[j], cat=0, timeframe=intervaloTiempo, geo=geolocalizacion, gprop='')

    df = pytrends.related_queries()

    for i in range (len(kw_lists[j])):
      #Extraemos del dataframe principal solo el dato de aumento de las consultas relacionadas de la consulta principal definida anteriormente.
      dfRising = df[kw_lists[j][i]]['rising']
      #Si la consulta devuelve datos filtramos el dataframe, de lo contrario creamos un dataframe vacío con las columnas de query y value
      if dfRising is not None:
        #nos quedamos solo con aquellas filas que superen el valor que definimos a continuación, en un principio será para aquellas que superen el valor de aumentoPuntual
        dfRisingClear = dfRising.drop(dfRising[dfRising['value']<aumentoPuntual].index)
      else:
        dfRisingClear = pd.DataFrame(columns=['query','value'])

      #para dividir estéticamente las tablas por consulta      
      dfRisingClear.insert(0,'Término', "",True) #añadimos columna "Consulta"
      dfRisingClear.columns = ['Término', 'Consultas relacionadas', 'Aumento puntual'] #renombramos las columnas del dataframe
      dfRisingClear.loc[-1]=[kw_list[j],"",""] #añadimos el término que estamos consultando a la primera columna 
      dfRisingClear.index = dfRisingClear.index + 1 #sumamos uno al indice
      dfRisingClear = dfRisingClear.sort_index() #reordenamos el indice para que el término que estamos consultando aparezca el primero

      #si el dataframe está vacío no lo añadimos al dataframe final.
      if len(dfRisingClear) > 1:
        listaFinal.append(dfRisingClear)

  #Si listaFinal está vacío creamos el dataframe dfConcatenados vacío, si no concatenamos en un dataframe todos los df almacenados en la lista
  if len(listaFinal) > 0:
    dfConcatenados = pd.concat(listaFinal,axis=0, ignore_index=True)#concatenamos en un Dataframe todos los dataframe añadidos a la lista listaFinal
  else:
    dfConcatenados = pd.DataFrame()

  #Enviamos los resultados en un email
  from email.mime.text import MIMEText
  from email.mime.application import MIMEApplication
  from email.mime.multipart import MIMEMultipart
  from smtplib import SMTP
  import smtplib
  import sys

  recipients = lista_emails
  emaillist = [elem.strip().split(',') for elem in recipients]
  msg = MIMEMultipart()
  msg['Subject'] = asunto
  msg['From'] = st.secrets["email_remitente"]
  password = st.secrets["password_email_remitente"]

  #En el HTML lo que está entre {} es la variable del contenido que queremos mostrar. El valor de dichas variables se define en .format
  html = """\
  <html>
    <head></head>
    <body>
      <p>
      Tendencia de consultas relacionadas de las siguientes consultas:
      </p>
      {kw_list}
      <h2>
      Resultado:
      </h2>
      {dfResultado}
    </body>
  </html>
  """.format(kw_list=txt, 
            dfResultado=dfConcatenados.to_html(index=False, border=0, justify='left'),
            )

  part1 = MIMEText(html, 'html')
  msg.attach(part1)

  server = smtplib.SMTP('smtp.gmail.com', 587)
  server.starttls()
  server.login(msg['From'], password)
  server.sendmail(msg['From'], emaillist , msg.as_string())

  st.text('Email enviado')
    
  #Generamos cuenta atrás hasta próximo rastreo
  import time
  with st.empty():
    t= frecuenciaEmail*60
    while t:
      mins, secs = divmod(t, 60)
      timeformat = '{:02d}:{:02d}'.format(mins, secs)
      st.write('Tiempo restante hasta el próximo envío: ' + timeformat)
      time.sleep(1)
      t-=1
  st.experimental_rerun()

trends()
