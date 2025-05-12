#vengono importate le librerie necessarie

#Gestione dati
import pandas as pd
import ast

#ML
from sklearn.feature_extraction.text import CountVectorizer
from nltk.stem.porter import PorterStemmer
from sklearn.metrics.pairwise import cosine_similarity

#CSP
from constraint import Problem

#import dei dataset
ds_movies = pd.read_csv('tmdb_5000_movies.csv')
ds_credits = pd.read_csv('tmdb_5000_credits.csv')

#merge dei due in uno
ds_movies = ds_movies.merge(ds_credits, on='title')

"""# **Pulizia e preparazione dei dati**"""

#si eliminano dal dataframe da colonne che non abbiamo bisogno, anche quelle con valori null come "homepage"
movies = ds_movies[['id', 'title', 'genres', 'overview', 'keywords', 'release_date', 'runtime', 'budget', 'revenue', 'vote_average', 'vote_count', 'popularity', 'cast', 'crew']].copy()

#si eliminano le righe con i valori null
movies.dropna(inplace=True)

#si eliminano le righe con valori duplicati mantenendo la prima occorrenza
movies.drop_duplicates(subset='id', keep='first',inplace=True)
movies.drop_duplicates(subset='title', keep='first',inplace=True)

#si eliminano le righe con dati inconsistenti
#ad esempio le righe con runtime=0
indexes_drop = movies[movies['runtime'] == 0].index
movies.drop(indexes_drop, inplace=True)

#si sostituisce la data di uscita con l'anno di uscita
movies['release_date'] = pd.to_datetime(movies['release_date'])
movies['release_date'] = movies['release_date'].dt.year
movies.rename(columns={'release_date': 'release'}, inplace=True)

#attraverso questa funzione, si prendono esclusivamente i generi e le keywords di ogni film
#e si inseriscono in una lista
def convert(text):
    L=[]
    for i in ast.literal_eval(text):
        L.append(i['name'])
    return L

movies['genres'] = movies['genres'].apply(convert)
movies['keywords'] = movies['keywords'].apply(convert)

#attraverso questa funzione, si prende il nome dei primi 3 attori (i più significativi) di ogni film
#e si inseriscono in una lista
def convert3(text):
    L = []
    counter = 0
    for i in ast.literal_eval(text):
        if counter < 3:
            L.append(i['name'])
        counter+=1
    return L

movies['cast'] = movies['cast'].apply(convert3)
movies['cast'] = movies['cast'].apply(lambda x:x[0:3])

#attraverso questa funzione, si prende il nome del regista (il più significativo della crew) di ogni film
#e si inserisce in una lista
def fetch_director(text):
    L = []
    for i in ast.literal_eval(text):
        if i['job'] == 'Director':
            L.append(i['name'])
    return L

movies['crew']=movies['crew'].apply(fetch_director)

#si eliminano eventuali spazi dai campi "overview", "cast", "crew", "genres", "keywords"
#per facilitare il lavoro del modello di ML

movies['overview'] = movies['overview'].apply(lambda x:x.split())

#per i restanti vieni costruita una funzione dedicata perchè sono liste
def collapse(L):
    L1 = []
    for i in L:
        L1.append(i.replace(" ",""))
    return L1

movies['cast'] = movies['cast'].apply(collapse)
movies['crew'] = movies['crew'].apply(collapse)
movies['genres'] = movies['genres'].apply(collapse)
movies['keywords'] = movies['keywords'].apply(collapse)

"""# **Modello ML**"""

#si crea un dataframe dedicato per il modello di Machine Learning
#che presenta 3 feature, dove in particolare nell'ultima si inseriscono tutte le feature su cui si baserà il suo funzionamento
df_movies = movies[['id', 'title']].copy()
df_movies.loc[:, 'tags'] = movies['overview'] + movies['genres'] + movies['keywords'] + movies['cast'] + movies['crew']

#Avendo concatenato più liste, difficili da gestire, si trasforma il campo "tags" in Stringa e
#per facilitare il match, si eliminano dalla stringa tutti i caratteri in Maiuscolo
df_movies['tags'] = df_movies['tags'].apply(lambda x: " ".join(x))
df_movies['tags'] = df_movies['tags'].apply(lambda x:x.lower())

#con CountVectorizer si effettua la feature extraction, convertendo il testo in una matrice di conteggi di token
#impostando max_features a 5000 per limitare il numero di parole da considerare
#e ‘english’ come stop words per rimuovere le parole comuni in inglese che non aggiungono significato al testo
cv = CountVectorizer(max_features=5000,stop_words='english')
vectors = cv.fit_transform(df_movies['tags']).toarray()

#Si applica al campo tags l'algoritmo di stemming
#per rimuovere i suffissi comuni delle parole, riducendole alla radice
ps=PorterStemmer()
def stem(text):
    Y=[]
    for i in text.split():
        Y.append(ps.stem(i))

    return " ".join(Y)
df_movies['tags']=df_movies['tags'].apply(stem)

#per effettuare Recommendation basandosi sul contenuto, attraverso la metrica della similarità del coseno
#viene istanziata una matrice di similarità che stabilisce quanto un film sia simile ad un altro
#in una scala da 0(meno simile) a 1(più simile)
similarity = cosine_similarity(vectors)


"""# **ML + CSP**"""

#si definisce la funzione di recommend che integra ML e CSP
def recommendML_CSP(movie, genre=None, year=None, runtime=None):

    #funzione "recommend" basata sul ML
    index=movies[movies['title']==movie].index[0]
    distances=similarity[index]
    mlist=sorted(list(enumerate(distances)),reverse=True,key=lambda x:x[1])[1:1000]
    recommended_movies = [movies.iloc[i[0]].title for i in mlist]

    #se non si fornisce alcun filtro, vengono restituiti direttamente i primi 5 film senza aver bisogno di creare un problema CSP e risolverlo
    if genre is None and year is None and runtime is None:
       return recommended_movies[:5]

    #Si crea il problema CSP
    CSPmovie = Problem()

    #Si aggiungono le variabili al problema
    for movie in recommended_movies:
        CSPmovie.addVariable(movie, [True, False])

    #Si aggiungono i constraint in base ai "filtri" forniti alla funzione
    for movie in recommended_movies:
        m_genres = movies.loc[movies['title'] == movie, 'genres'].values[0]
        m_release_year = movies.loc[movies['title'] == movie, 'release'].values[0]
        m_runtime = movies.loc[movies['title'] == movie, 'runtime'].values[0]

        if genre is not None:
            if year is not None:
                if runtime is not None:
                    CSPmovie.addConstraint(lambda x, g=m_genres, ry=m_release_year, rt=m_runtime:
                                              x if all(gen in g for gen in genre) and
                                                   ry >= year and
                                                   rt >= runtime else not x, [movie])
                else:  # runtime is None
                    CSPmovie.addConstraint(lambda x, g=m_genres, ry=m_release_year:
                                              x if all(gen in g for gen in genre) and
                                                   ry >= year else not x, [movie])
            else:  # year is None
                if runtime is not None:
                    CSPmovie.addConstraint(lambda x, g=m_genres, rt=m_runtime:
                                           x if all(gen in g for gen in genre) and
                                                rt >= runtime else not x, [movie])
                else:  # runtime is None
                    CSPmovie.addConstraint(lambda x, g=m_genres:
                                              x if all(gen in g for gen in genre) else not x, [movie])
        else:  # genre = None
            if year is not None:
                if runtime is not None:
                    CSPmovie.addConstraint(lambda x, ry=m_release_year, rt=m_runtime:
                                           x if ry >= year and
                                                rt >= runtime else not x, [movie])
                else:  # runtime = None
                    CSPmovie.addConstraint(lambda x, ry=m_release_year:
                                           x if ry >= year else not x, [movie])
            else:  # year = None
                if runtime is not None:
                    CSPmovie.addConstraint(lambda x, rt=m_runtime:
                                           x if rt >= runtime else not x, [movie])

    #Si ottengono le soluzioni del problema
    solutions = CSPmovie.getSolutions()

    #Si ricavano solo i film selezionati
    selected_movies = [movie for solution in solutions for movie, selected in solution.items() if selected]

    #Ordinamento:
    #siccome il CSP ritorna soluzioni in ordine alfabetico, verranno ordinati per la feature "score" basata sulla metrica "imDB":
    #ovvero una media ponderata tra media voto del film, e quanti voti ha ricevuto

    #per ordinare per "score", vi è il bisogno di un nuovo dataset con la nuova feature
    c = movies['vote_average'].mean()   #la media di tutte le medie dei film
    m = movies['vote_count'].quantile(0.9)  #minimo numero di voti richiesti affinche film sia elencato
    qualified_movies = movies.copy().loc[movies['vote_count'] >= m]
    qualified_movies['score'] = qualified_movies.apply(lambda x:
                            (x['vote_count'] / (x['vote_count'] + m) * x['vote_average']) +
                            (m / (x['vote_count'] + m) * c), axis=1)

    #Si prendono i film del dataframe "qualified_movies" che corrispondono alle soluzioni CSP
    #si concatenano in una lista di film ordinata per "score"
    #Per infine riportare i primi 5 film della lista
    #NB: se un film è presente nelle soluzioni CSP, ma non è presente in "qualified_movies", gli verrà assegnato allo score un punteggio di "-inf",
    #il che significa che verrà posizionato alla fine dell’elenco.
    rec_movies = sorted(selected_movies, key=lambda movie: qualified_movies.loc[qualified_movies['title'] == movie, 'score'].values[0]
                        if movie in qualified_movies['title'].values else float('-inf'), reverse=True)
    return rec_movies[0:5]