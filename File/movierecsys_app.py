import streamlit as st
import requests
from movierecsys import recommendML_CSP, movies


#tramite API, si ottiene la copertina di un film dal sito di tmDB, attraverso il suo ID
def fetch_poster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=c7ec19ffdd3279641fb606d19ceb9bb1&language=en-US".format(
        movie_id)
    data = requests.get(url)
    data = data.json()
    poster_path = data['poster_path']
    full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
    return full_path

#si inizializza la lista dei film e dei generi
movies_list = movies['title'].values
genres_list = (movies['genres'].explode().unique()).tolist()

#si inizializza i filtri a None, in modo che se non vengono impostati viene effettuata raccomandazione senza filtri
selected_year = None
selected_genre = None
selected_runtime = None

st.header("Movie Recommender System")
selected_movie = st.selectbox('Scegli un film', movies_list)

hcol1, hcol2, hcol3, hcol4 = st.columns(4)
with hcol1:
    st.markdown("Filtri:")
with hcol2:
    #filtro genere
    if st.toggle('Genere'):
        selected_genre = st.multiselect(" ",genres_list)
with hcol3:
    #filtro anno di uscita
    if st.toggle('Anno di uscita'):
        year_list = list(range(1900, 2017))
        year_list.sort(reverse=True)
        selected_year = st.selectbox(" ",year_list)
with hcol4:
    # filtro durata
    if st.toggle('Durata (minuti)'):
        selected_runtime = st.number_input(" ",min_value=0, max_value=250, step=30)


#funzione "core" dell'interfaccia grafica che, attraverso la funzione dichiarata nel file sorgente principale
#restituisce lista di film raccomandati e copertine
def recommend(movie, genre=None, release=None, runtime=None):   
    mlist = recommendML_CSP(movie,genre,release,runtime)
    recommend_movies = []
    recommend_poster = []
    for mov in mlist:
        movies_id = movies[movies['title'] == mov].id.values[0]
        recommend_movies.append(mov)
        recommend_poster.append(fetch_poster(movies_id))
    return recommend_movies, recommend_poster

#funzione che ottiene il link alla homepage del film sul sito tmDB, attraverso il suo nome
def movie_link(movie_name):
    movie_id = movies[movies['title'] == movie_name].id
    id = movie_id.values[0]
    movie = movie_name.lower()
    movie = movie.replace(" ", "-")
    link = f"https://www.themoviedb.org/movie/{id}-{movie}?language=it-IT"
    # esempio link: https://www.themoviedb.org/movie/19995-avatar?language=it-IT
    return link


if st.button('Mostra i film consigliati'):
    movie_name, movie_poster = recommend(selected_movie,selected_genre,selected_year,selected_runtime)
    #si considera il caso che non trova risultati
    if not movie_name:
        st.markdown("Nessun risultato trovato, riprova con altri filtri")
    else:
    #si considera il caso in cui il film potrebbero essere meno di 5
        col = st.columns(5)
        for i in range(len(movie_name)):
            with col[i]:
                link = movie_link(movie_name[i])
                st.page_link(link, label="Info")
                st.image(movie_poster[i])
                st.markdown(f"<p style='text-align: center'>{movie_name[i]}</p>", unsafe_allow_html=True)


#vengono consigliati i film con più incassi al cinema
def recommend_revenue():
    movies_rev = movies.sort_values('revenue', ascending=False)
    mlist_rev = (list(enumerate(movies_rev['id'])))[0:5]
    recommend_rev_movies = []
    recommend_rev_poster = []
    for i in mlist_rev:
        movies_id = movies_rev.iloc[i[0]].id
        recommend_rev_movies.append(movies_rev.iloc[i[0]].title)
        recommend_rev_poster.append(fetch_poster(movies_id))
    return recommend_rev_movies, recommend_rev_poster

st.header("I film più visti al cinema")
movie_rev_name, movie_rev_poster = recommend_revenue()
rcol = st.columns(5)
for i in range(len(movie_rev_name)):
    with rcol[i]:
        link = movie_link(movie_rev_name[i])
        st.page_link(link, label="Info")
        st.image(movie_rev_poster[i])
        st.markdown(f"<p style='text-align: center'>{movie_rev_name[i]}</p>", unsafe_allow_html=True)

#vengono consigliati i film con indice di popolarità più alto
def recommend_popularity():
    movies_pop = movies.sort_values('popularity', ascending=False)
    mlist_pop = (list(enumerate(movies_pop['id'])))[0:5]
    recommend_pop_movies = []
    recommend_pop_poster = []
    for i in mlist_pop:
        movies_id = movies_pop.iloc[i[0]].id
        recommend_pop_movies.append(movies_pop.iloc[i[0]].title)
        recommend_pop_poster.append(fetch_poster(movies_id))
    return recommend_pop_movies, recommend_pop_poster

st.header("I film più popolari")
movie_pop_name, movie_pop_poster = recommend_popularity()
pcol = st.columns(5)
for i in range(len(movie_pop_name)):
    with pcol[i]:
        link = movie_link(movie_pop_name[i])
        st.page_link(link, label="Info")
        st.image(movie_pop_poster[i])
        st.markdown(f"<p style='text-align: center'>{movie_pop_name[i]}</p>", unsafe_allow_html=True)

#vengono consigliati i film più recenti
def recommend_new():
    movies_new = movies.sort_values('release', ascending=False)
    mlist_new = (list(enumerate(movies_new['id'])))[0:5]
    recommend_new_movies = []
    recommend_new_poster = []
    for i in mlist_new:
        movies_id = movies_new.iloc[i[0]].id
        recommend_new_movies.append(movies_new.iloc[i[0]].title)
        recommend_new_poster.append(fetch_poster(movies_id))
    return recommend_new_movies, recommend_new_poster

st.header("Nuove uscite")
movie_new_name, movie_new_poster = recommend_new()
pcol = st.columns(5)
for i in range(len(movie_pop_name)):
    with pcol[i]:
        link = movie_link(movie_new_name[i])
        st.page_link(link, label="Info")
        st.image(movie_new_poster[i])
        st.markdown(f"<p style='text-align: center'>{movie_new_name[i]}</p>", unsafe_allow_html=True)
